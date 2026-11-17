#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查版本库里没有游戏数据、没有作者本机绝对路径（CI 步骤 3/3）。

两条硬性规则（对应 README「免责声明」与仓库约定）：
  1. 版本库里不得出现从游戏抽取/生成的文件：rulesmo_original.ini、
     rulesmo.ini、unit 名录、dist/ 成品包、backup/ 快照等。
  2. 版本库里不得出现作者本机绝对路径（个人工作目录、本地工具链安装位置等），
     否则公开仓库会泄露个人环境。

附带只告警、不失败的检查：文本中出现本机用户目录（如系统盘的用户目录）。

用法：
    python .github/scripts/check_tracked.py
退出码：0 = 通过，1 = 有违规。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
SELF = Path(__file__).resolve()

# ── 规则 1：禁止入库的游戏数据 ────────────────────────────────────────
FORBIDDEN_FILES = {
    "rulesmo_original.ini",
    "rulesmo.ini",
    "单位名录.csv",
    "单位名录_自检报告.md",
    "units_inventory.csv",
}
FORBIDDEN_DIRS = ("dist/", "backup/", "_tmp/")
FORBIDDEN_SUFFIXES = (".mix", ".exe", ".dll", ".zip", ".7z", ".rar")

# ── 规则 2：禁止入库的本机绝对路径（大小写不敏感）──────────────────────
# 匹配串由片段拼出：既避免本文件自身命中检查，也不让仓库里再出现完整路径副本。
_SEP = "\\"
_WORK_DIRS = ("AI" + "WORK", "Default " + "Project", "DeepSeek" + "-Harness")
FORBIDDEN_TEXT = [f"D:{_SEP}{d}" for d in _WORK_DIRS] + [f"D:/{d}" for d in _WORK_DIRS]
# 只告警：本机用户目录
WARN_TEXT = [f"C:{_SEP}Users{_SEP}", "C:/Users/"]


def expand(needles: list[str]) -> list[str]:
    """除原样外，再补一份反斜杠转义形式——路径写在 JSON 里会变成双反斜杠。"""
    out: set[str] = set()
    for n in needles:
        out.add(n)
        out.add(n.replace("\\", "\\\\"))
    return sorted(out)


FORBIDDEN_TEXT = expand(FORBIDDEN_TEXT)
WARN_TEXT = expand(WARN_TEXT)

TEXT_SUFFIXES = {
    ".py", ".md", ".json", ".yml", ".yaml", ".toml", ".txt", ".bat", ".cmd",
    ".ps1", ".psm1", ".sh", ".ini", ".csv", ".gitignore", ".gitattributes", "",
}


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        capture_output=True,
        check=True,
    ).stdout
    raw = [p for p in out.decode("utf-8", "surrogateescape").split("\0") if p]
    return raw


def is_text(path: Path) -> bool:
    suffix = path.suffix.lower()
    if path.name in (".gitignore", ".gitattributes", "LICENSE", "Makefile"):
        return True
    return suffix in TEXT_SUFFIXES


def main() -> int:
    try:
        files = tracked_files()
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"[FAIL] 无法读取 git ls-files（CI 里需要 actions/checkout）：{exc}")
        return 1

    print(f"版本库共跟踪 {len(files)} 个文件，开始检查……")

    errors: list[str] = []
    warnings: list[str] = []

    for name in files:
        posix = PurePosixPath(name)
        low = name.lower()

        # 规则 1
        if posix.name in FORBIDDEN_FILES or low in {f.lower() for f in FORBIDDEN_FILES}:
            errors.append(f"{name}: 这是从游戏抽取/生成的数据文件，不应入库")
            continue
        if any(low.startswith(d.lower()) for d in FORBIDDEN_DIRS):
            errors.append(f"{name}: 位于 {FORBIDDEN_DIRS} 下，属于成品/备份，不应入库")
            continue
        if low.endswith(FORBIDDEN_SUFFIXES):
            errors.append(f"{name}: 游戏本体或压缩包，不应入库")
            continue

        # 规则 2
        path = ROOT / name
        if not path.is_file() or not is_text(path):
            continue
        if path.resolve() == SELF:
            continue  # 本脚本自身必然包含这些字面量，跳过以免自我误报
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            warnings.append(f"{name}: 读取失败（{exc}），跳过路径检查")
            continue

        for needle in FORBIDDEN_TEXT:
            if needle in text:
                errors.append(f"{name}: 含本机绝对路径 {needle}")
        for needle in WARN_TEXT:
            if needle in text:
                warnings.append(
                    f"{name}: 含本机用户目录（系统盘的用户目录），"
                    "建议脱敏为 <游戏安装目录> 或相对路径"
                )
                break

    for w in sorted(set(warnings)):
        print(f"[WARN] {w}")
    for e in errors:
        print(f"[FAIL] {e}")

    print()
    if errors:
        print(f"检查未通过：{len(errors)} 处违规。仓库只放代码与文档，游戏数据请用 tools/extract_rules.py 本地生成。")
        return 1

    print(f"检查通过：{len(files)} 个跟踪文件里没有游戏数据、没有作者本机绝对路径"
          f"{'，另有 ' + str(len(set(warnings))) + ' 处告警' if warnings else ''}。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
