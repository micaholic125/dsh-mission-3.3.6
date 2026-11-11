#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成中文单位名录：把 rulesmo.ini 的数值与 config/unit_names_cn*.json 的中文名连起来。

输出 单位名录.csv（UTF-8 BOM，Excel 可直接打开）
列：中文名, ID, 类别, 造价Cost, 血量Strength, 装甲Armor, 速度Speed, 视野Sight,
    主武器Primary, 副武器Secondary, 拥有方Owner, 科技等级TechLevel, 前置建筑Prerequisite, 英文名Name
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

WORK = Path(r"D:\AIWORK\DSH mission\3.3.6")
INI = WORK / "rulesmo_original.ini"
NAMES = WORK / "unit_names_cn_merged.json"
OUT = WORK / "单位名录.csv"

SECTION_RE = re.compile(r"^\[([^\]]+)\]\s*$")
CATS = ["InfantryTypes", "VehicleTypes", "AircraftTypes", "BuildingTypes"]


def parse(text: str) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    cur = None
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith(";"):
            continue
        m = SECTION_RE.match(s)
        if m:
            cur = m.group(1)
            out.setdefault(cur, {})
            continue
        if cur is None or "=" not in s:
            continue
        k, _, v = s.partition("=")
        k = k.strip()
        if k and k not in out[cur]:
            out[cur][k] = v.strip()
    return out


def id_list(secs: dict[str, dict[str, str]], cat: str) -> list[str]:
    """从 [InfantryTypes] 这类表里取出全部单位 ID（按数字键排序，去掉行尾注释）。"""
    if cat not in secs:
        return []
    rows = []
    for k, v in secs[cat].items():
        if not k.isdigit():
            continue
        uid = v.split(";")[0].split("\t")[0].strip()
        if uid:
            rows.append((int(k), uid))
    rows.sort()
    return [uid for _, uid in rows]


def main() -> int:
    text = INI.read_bytes().decode("latin-1")
    secs = parse(text)
    names = json.loads(NAMES.read_text(encoding="utf-8-sig"))
    cn: dict[str, str] = dict(names.get("weapons") or {})
    cn.update(names.get("units") or {})

    header = ["中文名", "ID", "类别", "造价Cost", "血量Strength", "装甲Armor", "速度Speed",
              "视野Sight", "主武器Primary", "副武器Secondary", "拥有方Owner",
              "科技等级TechLevel", "前置建筑Prerequisite", "英文名Name"]

    rows: list[list[str]] = []
    seen: set[str] = set()
    for cat in CATS:
        for uid in id_list(secs, cat):
            if uid in seen:
                continue
            seen.add(uid)
            kv = secs.get(uid)
            if kv is None:
                continue
            rows.append([
                cn.get(uid, ""), uid, cat.removesuffix("Types"),
                kv.get("Cost", ""), kv.get("Strength", ""), kv.get("Armor", ""),
                kv.get("Speed", ""), kv.get("Sight", ""),
                kv.get("Primary", ""), kv.get("Secondary", ""),
                kv.get("Owner", ""), kv.get("TechLevel", ""),
                kv.get("Prerequisite", ""), kv.get("Name", ""),
            ])

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

    print(f"已生成 {OUT}")
    print(f"条目数: {len(rows)}   有中文名的: {sum(1 for r in rows if r[0])}")
    print("\n抽样:")
    for r in rows[:5]:
        print("  ", r[:6])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
