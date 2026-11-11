#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单位名录自检：找出"同名不同 ID""玩家版 vs AI 版""数值不一致"等会导致改错对象的问题。

背景：MO 里同一单位常有两条记录，例如
    STARDUSTB  The Paradox Engine        （玩家可造版）
    STARDUST   The Paradox Engine (AI)   （AI 版）
两者数值可以不同。用户报中文名"悖论引擎"时若不加区分就会改错。

产出：
  1. 单位名录_自检报告.md   —— 人读报告
  2. 单位名录.csv           —— 追加「同名ID」「版本判定」两列后重写

用法: python tools/check_catalog.py
"""
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
INI = WORK / "rulesmo_original.ini"
NAMES = WORK / "unit_names_cn_merged.json"
CSV_OUT = WORK / "单位名录.csv"
REPORT = WORK / "单位名录_自检报告.md"

SECTION_RE = re.compile(r"^\[([^\]]+)\]\s*$")
CATS = ["InfantryTypes", "VehicleTypes", "AircraftTypes", "BuildingTypes"]
VALUE_FIELDS = ["Cost", "Strength", "Armor", "Speed", "Sight", "TechLevel"]


# ---------------------------------------------------------------- 解析
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


def norm_name(s: str) -> str:
    """英文名归一：去 (AI)/(Bot)/(NPC)、去标点、小写。"""
    s = s.lower()
    s = re.sub(r"\((?:ai|bot|npc|computer)\)", " ", s)
    s = re.sub(r"\b(?:ai|bot|npc)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def is_ai_like(kv: dict[str, str]) -> bool:
    name = (kv.get("Name") or "").lower()
    if "(ai)" in name or "(bot)" in name or "(npc)" in name:
        return True
    if not (kv.get("Owner") or "").strip():
        return True
    try:
        if int(float(kv.get("TechLevel") or "0")) < 0:
            return True
    except ValueError:
        pass
    return False


# ---------------------------------------------------------------- 主流程
def main() -> int:
    secs = parse(INI.read_bytes().decode("latin-1"))
    names = json.loads(NAMES.read_text(encoding="utf-8-sig"))
    cn: dict[str, str] = dict(names.get("weapons") or {})
    cn.update(names.get("units") or {})

    # 记录每个 ID 属于哪个 ID 列表
    listed_in: dict[str, str] = {}
    danger_missing: list[tuple[str, str]] = []
    total_ids = 0
    for cat in CATS:
        for uid in id_list(secs, cat):
            total_ids += 1
            listed_in[uid] = cat.removesuffix("Types")
            if uid not in secs:
                danger_missing.append((cat, uid))

    # 所有"像单位"的节
    unit_ids = [s for s, kv in secs.items()
                if "Cost" in kv or "Strength" in kv]

    # 分组
    by_name: dict[str, list[str]] = defaultdict(list)
    by_cn: dict[str, list[str]] = defaultdict(list)
    for uid in unit_ids:
        kv = secs[uid]
        n = norm_name(kv.get("Name") or "")
        if n:
            by_name[n].append(uid)
        c = (cn.get(uid) or "").strip()
        if c:
            by_cn[c].append(uid)

    name_groups = {k: v for k, v in by_name.items() if len(v) > 1}
    cn_groups = {k: v for k, v in by_cn.items() if len(v) > 1}

    # 版本判定（四分类，比"AI/非AI"更贴近实际情况）
    def verdict(uid: str) -> str:
        kv = secs[uid]
        listed = uid in listed_in
        name = (kv.get("Name") or "").lower()
        owner = (kv.get("Owner") or "").strip()
        try:
            tech = int(float(kv.get("TechLevel") or "0"))
        except ValueError:
            tech = 0
        if not listed:
            return "脚本/残骸专用(未列ID表)"
        if "(ai)" in name or "(bot)" in name or "(npc)" in name:
            return "AI专用版"
        if not owner:
            return "不可建造(Owner为空)"
        if tech < 0:
            return "不可建造(TechLevel<0)"
        return "玩家版"

    # 同组数值差异
    def diff_fields(ids: list[str]) -> list[str]:
        out = []
        for f in VALUE_FIELDS:
            vals = {secs[u].get(f, "") for u in ids}
            if len(vals) > 1:
                out.append(f)
        return out

    # ---------------- CSV 重写 ----------------
    group_of: dict[str, str] = {}
    for ids in list(name_groups.values()) + list(cn_groups.values()):
        if len(ids) > 1:
            key = " / ".join(sorted(ids))
            for u in ids:
                group_of.setdefault(u, key)

    header = ["中文名", "ID", "类别", "造价Cost", "血量Strength", "装甲Armor",
              "速度Speed", "视野Sight", "主武器Primary", "副武器Secondary",
              "拥有方Owner", "科技等级TechLevel", "前置建筑Prerequisite",
              "英文名Name", "同名ID", "版本判定"]
    rows: list[list[str]] = []
    seen: set[str] = set()
    for cat in CATS:
        for uid in id_list(secs, cat):
            if uid in seen or uid not in secs:
                continue
            seen.add(uid)
            kv = secs[uid]
            others = [x for x in (group_of.get(uid, "").split(" / ") if group_of.get(uid) else []) if x and x != uid]
            rows.append([
                cn.get(uid, ""), uid, cat.removesuffix("Types"),
                kv.get("Cost", ""), kv.get("Strength", ""), kv.get("Armor", ""),
                kv.get("Speed", ""), kv.get("Sight", ""),
                kv.get("Primary", ""), kv.get("Secondary", ""),
                kv.get("Owner", ""), kv.get("TechLevel", ""),
                kv.get("Prerequisite", ""), kv.get("Name", ""),
                ",".join(others), verdict(uid),
            ])
    with CSV_OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

    # ---------------- 报告 ----------------
    L: list[str] = []
    A = L.append
    A("# 单位名录自检报告")
    A("")
    A(f"- 数据源：`{INI.name}`")
    A(f"- 中文名表：`{NAMES.name}`")
    A(f"- 定义条目（有 Cost/Strength 的节）：**{len(unit_ids)}**")
    A(f"- ID 列表引用合计：**{total_ids}** 条")
    A(f"- 可被训练/建造（在 ID 列表中）：**{len(listed_in)}** 个")
    A("")
    A("## 概要")
    A("")
    A("| 检查项 | 数量 |")
    A("|---|---|")
    A(f"| 英文名同名分组（≥2 个 ID） | {len(name_groups)} |")
    A(f"| 中文名冲突分组（≥2 个 ID） | {len(cn_groups)} |")
    A(f"| 定义存在但不在任何 ID 列表 | {sum(1 for u in unit_ids if u not in listed_in)} |")
    A(f"| ⚠️ ID 列表引用了不存在的节（会崩） | {len(danger_missing)} |")
    A("")

    # A. 中文名冲突
    A("## A. 中文名冲突（同一中文名 → 多个 ID）")
    A("")
    A("> **这是最容易改错的地方。** 用户报中文名时，必须先从下表确认要改哪个 ID。")
    A("")
    if not cn_groups:
        A("无。")
    else:
        for cname, ids in sorted(cn_groups.items(), key=lambda kv: -len(kv[1])):
            ids = sorted(ids)
            A(f"### {cname}  （{len(ids)} 个 ID）")
            A("")
            A("| ID | 英文名 | Owner | TechLevel | Cost | Strength | 在ID列表 | 判定 |")
            A("|---|---|---|---|---|---|---|---|")
            for u in ids:
                kv = secs[u]
                A(f"| `{u}` | {kv.get('Name','')} | {kv.get('Owner','') or '*(空)*'} | "
                  f"{kv.get('TechLevel','')} | {kv.get('Cost','')} | {kv.get('Strength','')} | "
                  f"{listed_in.get(u,'否')} | {verdict(u)} |")
            d = diff_fields(ids)
            if d:
                A("")
                A(f"⚠️ 组内数值不一致的字段：**{', '.join(d)}** —— 改玩家版不会同步 AI 版。")
            A("")

    # B. 英文名同名（中文名不同或缺失）
    only_en = {k: v for k, v in name_groups.items()
               if len({(cn.get(u) or "") for u in v}) > 1}
    A("## B. 英文名同名但中文名不同/缺失")
    A("")
    if not only_en:
        A("无。")
    else:
        for n, ids in sorted(only_en.items()):
            ids = sorted(ids)
            A(f"- `{ids[0]}` 的英文名「{secs[ids[0]].get('Name','')}」：")
            for u in ids:
                A(f"  - `{u}` 中文名={cn.get(u,'*(缺)*')} 判定={verdict(u)}")
        A("")

    # C. 定义存在但不在 ID 列表
    unlisted = sorted(u for u in unit_ids if u not in listed_in)
    A("## C. 有定义但不在任何 ID 列表（不可训练 / 脚本或残骸专用）")
    A("")
    A(f"共 **{len(unlisted)}** 个。前 40 个：")
    A("")
    for u in unlisted[:40]:
        kv = secs[u]
        A(f"- `{u}` {cn.get(u,'')} — Name={kv.get('Name','')} Owner={kv.get('Owner','') or '*(空)*'}")
    if len(unlisted) > 40:
        A(f"- …其余 {len(unlisted) - 40} 个")
    A("")

    # D. 断链
    A("## D. ⚠️ ID 列表引用了不存在的节")
    A("")
    if not danger_missing:
        A("无（全部 ID 都能找到对应节，安全）。")
    else:
        A("**这些会导致游戏加载异常，必须排查：**")
        A("")
        for cat, uid in danger_missing[:40]:
            A(f"- `[{cat}]` → `{uid}` 节不存在")
    A("")

    # E. 已知特例确认
    A("## E. 已知特例回归确认")
    A("")
    for uid in ("STARDUSTB", "STARDUST"):
        if uid in secs:
            kv = secs[uid]
            A(f"- `{uid}`：中文名={cn.get(uid,'*(缺)*')}，英文名={kv.get('Name','')}，"
              f"Owner={kv.get('Owner','') or '*(空)*'}，TechLevel={kv.get('TechLevel','')}，"
              f"判定={verdict(uid)}")
    A(f"- 两者是否被正确归入同一「同名分组」："
      f"{'是' if group_of.get('STARDUSTB') == group_of.get('STARDUST') != None else '**否（需排查）**'}")
    A("")
    A("---")
    A("")
    A("## 使用建议")
    A("")
    A("1. 在 `需求.md` 报需求时，**优先写 ID**；只写中文名的话，我按下表规则确认：")
    A("   - 该中文名只有 1 个 ID → 直接用；")
    A("   - 有多个 ID → 我只改「玩家版」（在 ID 列表且 Owner 非空），")
    A("     若 AI 版数值也需要同步，我会额外提一条并等你确认。")
    A("2. 本节报告每次名录更新后重跑：`python tools/check_catalog.py`。")

    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"已生成报告: {REPORT}")
    print(f"已更新名录: {CSV_OUT}  ({len(rows)} 行)")
    print(f"中文名冲突分组: {len(cn_groups)}   英文名同名分组: {len(name_groups)}")
    print(f"不在ID列表: {len(unlisted)}   断链: {len(danger_missing)}")
    print("\n中文名冲突 Top8:")
    for cname, ids in sorted(cn_groups.items(), key=lambda kv: -len(kv[1]))[:8]:
        print(f"  {cname:14} -> {', '.join(sorted(ids))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
