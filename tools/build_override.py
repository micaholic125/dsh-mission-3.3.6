#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从基准文件生成覆盖用 rulesmo.ini，并强制校验改动合集。

流程：
  1. 复制 rulesmo_original.ini -> 目标文件
  2. 逐条应用 changes/*.json
  3. 用语义比对独立复核：差异条数必须 == 清单条数，且每条的节/键/新值一致
  4. 任何不一致 -> 报错退出，不产出可用文件

用法：
  python tools/build_override.py changes/batch1.json
  python tools/build_override.py changes/batch1.json --out rulesmo.ini
  python tools/build_override.py changes/batch1.json --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK / "tools"))

from ini_edit import add_key_in_text, parse, read_text, set_key_in_text, write_atomic  # noqa: E402

BASE = WORK / "rulesmo_original.ini"


def sha1(p: Path) -> str:
    return hashlib.sha1(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("changes", nargs="+", help="一个或多个变化清单 JSON，按给出顺序叠加")
    ap.add_argument("--out", default="rulesmo.ini")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    changes = []
    labels = []
    seen_targets = {}
    for cfile in args.changes:
        spec = json.loads((WORK / cfile).read_text(encoding="utf-8"))
        labels.append(spec.get("batch", cfile))
        for c in spec["changes"]:
            tgt = (c["section"], c["key"])
            if tgt in seen_targets:
                print(f"ERROR: 同一目标被重复定义 {tgt}（{seen_targets[tgt]} 与 {cfile}）")
                return 1
            seen_targets[tgt] = cfile
            changes.append(c)
    print(f"加载清单: {', '.join(labels)}  合计 {len(changes)} 项")
    out_path = WORK / args.out

    if not BASE.is_file():
        print(f"ERROR: 基准文件不存在 {BASE}")
        return 1

    text, enc = read_text(BASE)
    base_secs = parse(text)

    # ---------- 1. 前置校验 ----------
    problems = []
    n_set = n_add = 0
    for c in changes:
        sec, key = c["section"], c["key"]
        if sec not in base_secs:
            problems.append(f"  节不存在 [{sec}]")
        elif c.get("mode") == "add":
            if key in base_secs[sec]:
                problems.append(f"  [{sec}] 键已存在，禁止重复新增: {key}")
            else:
                n_add += 1
        else:
            if key not in base_secs[sec]:
                problems.append(f"  [{sec}] 键不存在 {key}")
            else:
                n_set += 1
    if problems:
        print("ERROR: 前置校验失败，未生成文件：")
        print("\n".join(problems))
        return 1
    print(f"前置校验通过：{len(changes)} 项（改值 {n_set} 项 / 新增键 {n_add} 项）")

    # ---------- 2. 应用 ----------
    applied = []
    for c in changes:
        if c.get("mode") == "add":
            text, old = add_key_in_text(text, c["section"], c["key"], str(c["value"]))
        else:
            text, old = set_key_in_text(text, c["section"], c["key"], str(c["value"]))
        applied.append((c["section"], c["key"], old, str(c["value"])))

    # ---------- 3. 独立复核 ----------
    new_secs = parse(text)
    diffs = []
    adds = {(c["section"], c["key"]) for c in changes if c.get("mode") == "add"}
    for sec, key, old, new in applied:
        got = new_secs.get(sec, {}).get(key)
        if got != new:
            diffs.append(f"  [{sec}] {key} 期望 {new} 实际 {got}")
    # 反向：不能有清单之外的改动
    for sec in base_secs:
        for key, val in base_secs[sec].items():
            if new_secs.get(sec, {}).get(key) != val:
                if not any(s == sec and k == key for s, k, _, _ in applied):
                    diffs.append(f"  [{sec}] {key} 出现了清单之外的改动")
    # 反向：不能有清单之外的新增键，且新增总数要对得上
    added_actual = 0
    for sec, kv in new_secs.items():
        base_kv = base_secs.get(sec, {})
        for key in kv:
            if key not in base_kv:
                added_actual += 1
                if (sec, key) not in adds:
                    diffs.append(f"  [{sec}] {key} 出现了清单之外的新增键")
    if added_actual != len(adds):
        diffs.append(f"  新增键总数不符：期望 {len(adds)} 实际 {added_actual}")

    if diffs:
        print("ERROR: 复核失败，改动与清单不符：")
        print("\n".join(diffs[:30]))
        return 1
    print(f"独立复核通过：实际改动 {len(applied)} 项，与清单一致，无多余改动")

    # ---------- 4. 体积变化核对 ----------
    delta = len(text.encode(enc, errors="replace")) - BASE.stat().st_size
    print(f"文件体积变化：{delta:+d} 字节")

    if args.dry_run:
        print("\n[dry-run] 未写入文件。改动明细：")
        for sec, key, old, new in applied:
            print(f"  [{sec}] {key}: {old} -> {new}")
        return 0

    write_atomic(out_path, text, enc)
    print(f"\n已生成：{out_path}")
    print(f"  sha1: {sha1(BASE)[:12]} -> {sha1(out_path)[:12]}")
    print(f"  大小: {BASE.stat().st_size:,} -> {out_path.stat().st_size:,} 字节")
    print("\n改动明细：")
    for sec, key, old, new in applied:
        print(f"  [{sec}] {key}: {old} -> {new}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
