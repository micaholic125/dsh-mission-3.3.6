#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 D:\\Default Project\\config\\unit_names_cn*.json 合并成本工作区的一份中文名总表。

用途：用户报中文单位名时，用它反查 rulesmo.ini 里的节点 ID。
输出：unit_names_cn_merged.json  {"units": {...}, "weapons": {...}, "sources": [...]}
"""
from __future__ import annotations

import json
from pathlib import Path

SRC = Path(r"D:\Default Project\config")
DEST = Path(r"D:\AIWORK\DSH mission\3.3.6\unit_names_cn_merged.json")


def main() -> int:
    files = sorted(SRC.glob("unit_names_cn*.json"))
    if not files:
        print(f"ERROR: {SRC} 下没有 unit_names_cn*.json")
        return 1

    units: dict[str, str] = {}
    weapons: dict[str, str] = {}
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8-sig"))
        except Exception as e:  # noqa: BLE001
            print(f"跳过 {f.name}: {e}")
            continue
        u = data.get("units") or {}
        w = data.get("weapons") or {}
        units.update(u)
        weapons.update(w)
        print(f"  {f.name:32} units={len(u):5} weapons={len(w):4}")

    out = {"units": units, "weapons": weapons, "sources": [f.name for f in files]}
    DEST.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n合并完成: units={len(units)}  weapons={len(weapons)}  -> {DEST}")

    # 抽样验证：凡是中文名里带“悖论”的
    hits = [(k, v) for k, v in units.items() if "悖论" in str(v)]
    print(f"\n含「悖论」的单位 ({len(hits)}):")
    for k, v in hits[:15]:
        print(f"  {k:16} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
