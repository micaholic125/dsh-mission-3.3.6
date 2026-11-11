#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 [节] + 键 语义比对两份 RA2/MO 风格 INI，忽略注释与空白差异。

用法: python ini_compare.py 基准.ini 对比.ini [最多输出条数]
输出: SECTION_ADDED / SECTION_REMOVED / KEY_ADDED / KEY_REMOVED / CHANGED
"""
from __future__ import annotations

import re
import sys
from collections import OrderedDict

SECTION_RE = re.compile(r"^\[([^\]]+)\]")


def decode(path: str) -> str:
    data = open(path, "rb").read()
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    raise ValueError(f"无法解码: {path}")


def load(path: str) -> "OrderedDict[str, OrderedDict[str, str]]":
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


def main() -> int:
    if len(sys.argv) < 3:
        print("用法: python ini_compare.py 基准.ini 对比.ini [行数上限]")
        return 2
    base_path, cmp_path = sys.argv[1], sys.argv[2]
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 200

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
    for kind, sec, key, val in diffs[:limit]:
        if key:
            print(f"{kind:15} [{sec}] {key} = {val}")
        else:
            print(f"{kind:15} [{sec}]")
    if len(diffs) > limit:
        print(f"... 其余 {len(diffs) - limit} 条已省略")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
