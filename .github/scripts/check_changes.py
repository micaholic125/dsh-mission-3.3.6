#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 changes/*.json 的结构（CI 步骤 2/3，也可本地手动跑）。

规则（见 CONTRIBUTING.md「改动清单格式」）：
  - 顶层是 JSON 对象，含非空数组 "changes"
  - 每条改动必须有 section / key / value 三个字段
  - section、key 必须是非空字符串；value 只允许字符串、整数、浮点数
  - value 不允许布尔、null、数组、对象（规则文件里没有这些形态）
  - 同一文件内不允许出现重复的 section + key（要覆盖请另开一批）
  - "note"（说明）建议填写，缺失只告警不失败
  - "mode": "add" 表示新增键，只允许这个取值

用法：
    python .github/scripts/check_changes.py
退出码：0 = 通过，1 = 有错误。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHANGES_DIR = ROOT / "changes"

ALLOWED_MODES = {None, "add"}


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")


def main() -> int:
    if not CHANGES_DIR.is_dir():
        fail(f"找不到目录：{CHANGES_DIR}")
        return 1

    files = sorted(CHANGES_DIR.glob("*.json"))
    if not files:
        fail("changes/ 下没有任何 .json 改动清单")
        return 1

    errors: list[str] = []
    warnings: list[str] = []
    total = 0

    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            errors.append(f"{rel}: 不是 UTF-8 编码")
            continue
        except json.JSONDecodeError as exc:
            errors.append(f"{rel}: JSON 解析失败（第 {exc.lineno} 行第 {exc.colno} 列）：{exc.msg}")
            continue

        if not isinstance(data, dict):
            errors.append(f"{rel}: 顶层必须是 JSON 对象")
            continue

        if not isinstance(data.get("batch"), str) or not data.get("batch", "").strip():
            warnings.append(f"{rel}: 建议填写 \"batch\"（批次名），便于构建日志追溯")

        changes = data.get("changes")
        if not isinstance(changes, list) or not changes:
            errors.append(f"{rel}: 缺少非空的 \"changes\" 数组")
            continue

        seen: dict[tuple[str, str], int] = {}
        for idx, item in enumerate(changes, 1):
            where = f"{rel} 第 {idx} 条"
            if not isinstance(item, dict):
                errors.append(f"{where}: 必须是 JSON 对象")
                continue

            for field in ("section", "key", "value"):
                if field not in item:
                    errors.append(f"{where}: 缺少必填字段 \"{field}\"")

            section = item.get("section")
            key = item.get("key")
            value = item.get("value")

            if "section" in item:
                if not isinstance(section, str) or not section.strip():
                    errors.append(f"{where}: \"section\" 必须是非空字符串")
                elif section != section.strip() or any(c in section for c in "[]=,;\n\r"):
                    errors.append(f"{where}: section 必须是不带方括号/等号/逗号的节名，如 \"General\"，实际为 {section!r}")

            if "key" in item:
                if not isinstance(key, str) or not key.strip():
                    errors.append(f"{where}: \"key\" 必须是非空字符串")
                elif any(c in key for c in "=[\n\r"):
                    errors.append(f"{where}: key 不能包含等号、方括号或换行，实际为 {key!r}")

            if "value" in item:
                if isinstance(value, bool) or value is None:
                    errors.append(f"{where}: \"value\" 不能是布尔/null（规则文件里请用 'yes'/'no' 或 0/1）")
                elif isinstance(value, (list, dict)):
                    errors.append(f"{where}: \"value\" 不能是数组/对象")
                elif not isinstance(value, (str, int, float)):
                    errors.append(f"{where}: \"value\" 只允许字符串、整数、浮点数，实际类型 {type(value).__name__}")
                elif isinstance(value, str) and ("\n" in value or "\r" in value):
                    errors.append(f"{where}: \"value\" 不能包含换行")

            if "note" in item and not isinstance(item["note"], str):
                errors.append(f"{where}: \"note\" 必须是字符串")
            elif "note" not in item or not str(item.get("note", "")).strip():
                warnings.append(f"{where}: 建议填写 \"note\"（中文说明，供公告与改动清单引用）")

            if item.get("mode") not in ALLOWED_MODES:
                errors.append(f"{where}: \"mode\" 只允许 \"add\"（新增键）或不填")

            pair = (str(section), str(key))
            if pair in seen:
                errors.append(
                    f"{where}: 与第 {seen[pair]} 条重复（{section}.{key}）；"
                    "同一批内不能重复，要覆盖旧值请另开一批"
                )
            else:
                seen[pair] = idx

        total += len(changes)
        print(f"[ OK ] {rel}: {len(changes)} 条")

    for w in warnings:
        print(f"[WARN] {w}")
    for e in errors:
        fail(e)

    print()
    if errors:
        print(f"结构校验未通过：{len(errors)} 处错误 / {len(warnings)} 处告警，共 {len(files)} 个清单文件。")
        return 1

    print(f"结构校验通过：{len(files)} 个清单文件、共 {total} 条改动，{len(warnings)} 处告警。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
