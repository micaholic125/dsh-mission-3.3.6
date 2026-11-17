#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成中文单位名录：把 rulesmo.ini 的数值与 unit_names_cn_merged.json 的中文名连起来。

输出 ``单位名录.csv``（UTF-8 BOM，Excel 可直接打开）。
列：中文名, ID, 类别, 造价Cost, 血量Strength, 装甲Armor, 速度Speed, 视野Sight,
    主武器Primary, 副武器Secondary, 拥有方Owner, 科技等级TechLevel, 前置建筑Prerequisite, 英文名Name

用法::

    python tools/make_unit_catalog.py                       # 用仓库根默认文件，输出 单位名录.csv
    python tools/make_unit_catalog.py --ini _tmp/rules.ini --out _tmp/名录.csv

默认输入/输出都在仓库根目录（由本文件位置推导，与 cwd 无关）；
相对路径按**仓库根目录**解析。中文名表缺失时仍可生成，只是中文名列留空。
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mo_paths import REPO_ROOT, repo_path  # noqa: E402

WORK = REPO_ROOT
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="make_unit_catalog.py",
        description="生成中文单位名录 CSV（中文名 ↔ 节点 ID ↔ 数值）。",
        epilog=(
            "示例：\n"
            "  python tools/make_unit_catalog.py\n"
            "  python tools/make_unit_catalog.py --ini _tmp/rulesmo_original.ini --out _tmp/单位名录.csv\n\n"
            "相对路径按仓库根目录解析。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--ini", metavar="文件", default=None,
                    help="规则文件（默认：仓库根 rulesmo_original.ini）")
    ap.add_argument("--names", metavar="文件", default=None,
                    help="中文名表 JSON（默认：仓库根 unit_names_cn_merged.json）")
    ap.add_argument("--out", metavar="文件", default=None,
                    help="输出 CSV（默认：仓库根 单位名录.csv）")
    args = ap.parse_args(argv)

    ini_path = repo_path(args.ini) if args.ini else INI
    names_path = repo_path(args.names) if args.names else NAMES
    out_path = repo_path(args.out) if args.out else OUT

    if not ini_path.is_file():
        print(f"ERROR: 规则文件不存在 {ini_path}")
        print('       请先运行：python tools/extract_rules.py --game-dir "D:/Mental Omega"')
        return 1

    text = ini_path.read_bytes().decode("latin-1")
    secs = parse(text)

    names: dict = {}
    if names_path.is_file():
        names = json.loads(names_path.read_text(encoding="utf-8-sig"))
    else:
        print(f"提示：中文名表不存在 {names_path}，中文名列将留空（不影响其余列）。")
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

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

    print(f"已生成 {out_path}")
    print(f"条目数: {len(rows)}   有中文名的: {sum(1 for r in rows if r[0])}")
    print("\n抽样:")
    for r in rows[:5]:
        print("  ", r[:6])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
