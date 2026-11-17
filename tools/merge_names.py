#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把若干份 ``unit_names_cn*.json`` 合并成一份中文名总表。

⚠️ **这是一次性内部工具**：源数据是作者本机的多份 ``unit_names_cn*.json``，
   不随公开仓库分发。仓库里已经带了合并结果 ``unit_names_cn_merged.json``，
   正常使用（生成名录、反查中文名）**不需要**运行本脚本；
   只有你手上也有同类源文件、想重新合并时才用。

用途：用户报中文单位名时，用它反查 rulesmo.ini 里的节点 ID。
输出：``unit_names_cn_merged.json``，格式 ``{"units": {...}, "weapons": {...}, "sources": [...]}``

用法::

    python tools/merge_names.py --src <含 unit_names_cn*.json 的目录>
    python tools/merge_names.py --src <目录> --out _tmp/names.json
    set MO_NAMES_SRC=<目录>  &  python tools/merge_names.py

相对路径按**仓库根目录**解析；输出默认写到仓库根 ``unit_names_cn_merged.json``。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mo_paths import REPO_ROOT, repo_path  # noqa: E402

NAMES_ENV = "MO_NAMES_SRC"
DEST = REPO_ROOT / "unit_names_cn_merged.json"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="merge_names.py",
        description="合并多份 unit_names_cn*.json 为一份中文名总表（一次性内部工具，源数据不随仓库分发）。",
        epilog=(
            "示例：\n"
            "  python tools/merge_names.py --src ./config\n"
            f"  set {NAMES_ENV}=D:\\my_config  &  python tools/merge_names.py\n\n"
            "相对路径按仓库根目录解析。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--src", metavar="目录", default=None,
                    help=f"含 unit_names_cn*.json 的源目录（默认读环境变量 {NAMES_ENV}）")
    ap.add_argument("--out", metavar="文件", default=None,
                    help="输出文件（默认：仓库根 unit_names_cn_merged.json）")
    args = ap.parse_args(argv)

    src_value = args.src or os.environ.get(NAMES_ENV, "").strip()
    if not src_value:
        print("ERROR: 没有指定源目录。")
        print("  这是**一次性内部工具**，源数据（多份 unit_names_cn*.json）不随仓库分发；")
        print("  仓库里已有合并结果 unit_names_cn_merged.json，一般不需要运行本脚本。")
        print('  如确需合并：python tools/merge_names.py --src "D:/你的目录"')
        print(f"  或设置环境变量：set {NAMES_ENV}=D:\\你的目录")
        return 2

    src = repo_path(src_value)
    if not src.is_dir():
        print(f"ERROR: 源目录不存在：{src}")
        print("  请用 --src 指定包含 unit_names_cn*.json 的目录。")
        return 2

    out_path = repo_path(args.out) if args.out else DEST
    files = sorted(src.glob("unit_names_cn*.json"))
    # 避免把输出文件自己当输入（例如 --src 就是仓库根时）
    try:
        out_key = out_path.resolve()
        files = [f for f in files if f.resolve() != out_key]
    except OSError:
        pass
    if not files:
        print(f"ERROR: {src} 下没有 unit_names_cn*.json")
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
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n合并完成: units={len(units)}  weapons={len(weapons)}  -> {out_path}")

    # 抽样验证：凡是中文名里带“悖论”的
    hits = [(k, v) for k, v in units.items() if "悖论" in str(v)]
    print(f"\n含「悖论」的单位 ({len(hits)}):")
    for k, v in hits[:15]:
        print(f"  {k:16} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
