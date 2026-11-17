#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 [节] + 键 语义比对两份 RA2/MO 风格 INI，忽略注释与空白差异。

用途：复核「实际改动条数 == 改动清单条数」。默认比对仓库根的两份文件：

- 基准：``rulesmo_original.ini``（从 MIX 抽出的原版）
- 对比：``rulesmo.ini``（补丁生成的外置覆盖文件）

用法::

    python tools/ini_compare.py                        # 默认比对上面两份，输出差异总数
    python tools/ini_compare.py 基准.ini 对比.ini       # 指定文件（相对路径先按 cwd、再按仓库根解析）
    python tools/ini_compare.py --limit 50             # 只显示前 50 条明细

输出：SECTION_ADDED / SECTION_REMOVED / KEY_ADDED / KEY_REMOVED / CHANGED
退出码：0 正常比对完成 / 2 参数或文件问题
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mo_paths import REPO_ROOT  # noqa: E402

SECTION_RE = re.compile(r"^\[([^\]]+)\]")


def resolve_input(value: str) -> Path:
    """输入路径解析：绝对路径原样；相对路径先按 cwd，找不到再按仓库根。"""
    p = Path(value).expanduser()
    if p.is_absolute():
        return p
    if p.exists():
        return p.resolve()
    return REPO_ROOT / p


def decode(path: Path) -> str:
    data = path.read_bytes()
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    raise ValueError(f"无法解码: {path}")


def load(path: Path) -> "OrderedDict[str, OrderedDict[str, str]]":
    """解析为 {节: {键: 值}}；同名键取第一次出现，忽略注释行。"""
    sections: "OrderedDict[str, OrderedDict[str, str]]" = OrderedDict()
    cur = None
    for raw in decode(path).splitlines():
        s = raw.strip()
        if not s or s.startswith(";"):
            continue
        m = SECTION_RE.match(s)
        if m:
            cur = m.group(1)
            sections.setdefault(cur, OrderedDict())
            continue
        if cur is None or "=" not in s:
            continue
        key, _, val = s.partition("=")
        key = key.strip()
        if key and key not in sections[cur]:
            sections[cur][key] = val.strip()
    return sections


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="ini_compare.py",
        description="按 [节] + 键 语义比对两份 MO 风格 INI（忽略注释与空白差异），用于复核改动条数。",
        epilog=(
            "示例：\n"
            "  python tools/ini_compare.py\n"
            "  python tools/ini_compare.py rulesmo_original.ini rulesmo.ini --limit 50"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("base", nargs="?", default=None,
                    help="基准 INI（默认：仓库根 rulesmo_original.ini）")
    ap.add_argument("cmp", nargs="?", default=None,
                    help="对比 INI（默认：仓库根 rulesmo.ini）")
    ap.add_argument("--limit", type=int, default=200,
                    help="明细最多输出多少条（默认 200）")
    args = ap.parse_args(argv)

    base_path = resolve_input(args.base) if args.base else (REPO_ROOT / "rulesmo_original.ini")
    cmp_path = resolve_input(args.cmp) if args.cmp else (REPO_ROOT / "rulesmo.ini")

    for p in (base_path, cmp_path):
        if not p.is_file():
            print(f"ERROR: 文件不存在 {p}")
            if p.name == "rulesmo_original.ini":
                print('       基准文件可由你自己的游戏生成：python tools/extract_rules.py --game-dir "D:/Mental Omega"')
            elif p.name == "rulesmo.ini":
                print("       补丁文件可由改动清单生成：python tools/build_override.py changes/batch1.json ...")
            return 2

    base, cmp_ = load(base_path), load(cmp_path)

    diffs: list[tuple[str, str, str, str]] = []

    only_base_sec = [s for s in base if s not in cmp_]
    only_cmp_sec = [s for s in cmp_ if s not in base]
    for s in only_cmp_sec:
        diffs.append(("SECTION_ADDED", s, "", ""))
    for s in only_base_sec:
        diffs.append(("SECTION_REMOVED", s, "", ""))

    for sec, kv in cmp_.items():
        if sec not in base:
            continue
        base_kv = base[sec]
        for k, v in kv.items():
            if k not in base_kv:
                diffs.append(("KEY_ADDED", sec, k, v))
            elif base_kv[k] != v:
                diffs.append(("CHANGED", sec, k, f"{base_kv[k]} -> {v}"))
        for k, v in base_kv.items():
            if k not in kv:
                diffs.append(("KEY_REMOVED", sec, k, v))

    print(f"base={base_path}  ({len(base)} 节)")
    print(f"cmp ={cmp_path}  ({len(cmp_)} 节)")
    print(f"差异总数: {len(diffs)}")
    print("-" * 70)
    kind_count: dict[str, int] = {}
    for kind, *_ in diffs:
        kind_count[kind] = kind_count.get(kind, 0) + 1
    print("按类型: " + ", ".join(f"{k}={v}" for k, v in sorted(kind_count.items())))
    print("-" * 70)
    for kind, sec, key, val in diffs[:args.limit]:
        if key:
            print(f"{kind:15} [{sec}] {key} = {val}")
        else:
            print(f"{kind:15} [{sec}]")
    if len(diffs) > args.limit:
        print(f"... 其余 {len(diffs) - args.limit} 条已省略")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
