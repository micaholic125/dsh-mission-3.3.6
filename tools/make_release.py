#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打包 MO 平衡补丁为可交付版本（别人双击即用）。

产出：
  dist/MO平衡补丁_v<版本>/        目录（可直接发）
  dist/MO平衡补丁_v<版本>.zip     压缩包（推荐发送这个）

内容：
  安装.bat / 恢复原版.bat / 使用说明.txt / 改动清单.md / 平衡公告.md
  _internal/rulesmo.ini + install.ps1 + restore.ps1 + version.txt

用法: python tools/make_release.py [版本号]   # 默认 v1.0.0
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK / "tools"))
from ini_edit import parse, read_text  # noqa: E402

DIST = WORK / "dist"
RELEASE_SRC = WORK / "release"
BASE = WORK / "rulesmo_original.ini"
PAYLOAD = WORK / "rulesmo.ini"
CHANGES = WORK / "changes"

FACTION = [
    ("盟-", "盟军"),
    ("EU-", "欧盟"),
    ("CN-", "中国"),
    ("RU-", "俄罗斯"),
    ("苏-", "苏军"),
    ("厄-", "厄普西隆军"),
    ("焚-", "焚风反抗军"),
]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def faction_of(note: str) -> str:
    for prefix, name in FACTION:
        if note.startswith(prefix):
            return name
    return "其它"


def load_changes() -> list[dict]:
    items: list[dict] = []
    for f in sorted(CHANGES.glob("batch*.json")):
        spec = json.loads(f.read_text(encoding="utf-8"))
        for c in spec["changes"]:
            c["_batch"] = spec.get("batch", f.name)
            items.append(c)
    return items


def gen_change_list(items: list[dict]) -> str:
    text, _ = read_text(BASE)
    base = parse(text)

    lines = [
        "# MO 3.3.6 平衡补丁 v1.0.0 — 改动清单",
        "",
        f"共 **{len(items)}** 项改动。原值取自 MO 3.3.6 原版 `rulesmo.ini`（从 `expandmo99.mix` 抽出）。",
        "",
        "> 「新增键」表示原版没有这个设置项，由本补丁添加。",
        "",
    ]

    grouped: dict[str, list[dict]] = {}
    for c in items:
        grouped.setdefault(faction_of(c.get("note", "")), []).append(c)

    order = [n for _, n in FACTION] + ["其它"]
    for fac in order:
        if fac not in grouped:
            continue
        lines.append(f"## {fac}")
        lines.append("")
        lines.append("| 说明 | 位置 | 原值 → 新值 |")
        lines.append("|---|---|---|")
        for c in grouped[fac]:
            note = c.get("note", "").strip()
            sec, key = c["section"], c["key"]
            if c.get("mode") == "add":
                old = "*(无，新增)*"
            else:
                old = base.get(sec, {}).get(key, "?")
            lines.append(f"| {note} | `[{sec}]` `{key}` | {old} → **{c['value']}** |")
        lines.append("")

    lines += [
        "---",
        "",
        "## 怎么验证生效",
        "",
        "进遭遇战看造价最直观：光棱坦克 1050、雷神炮艇 1500、铁骑兵 350。",
        "",
        "## 回滚",
        "",
        "双击包内「恢复原版.bat」，或手工删除游戏目录下的 `rulesmo.ini`。",
        "MIX 内的原版规则文件从未被修改，删除覆盖文件即完全恢复。",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    version = sys.argv[1] if len(sys.argv) > 1 else "v1.0.0"
    name = f"MO平衡补丁_{version}"
    out = DIST / name
    zip_path = DIST / f"{name}.zip"

    for p in (out,):
        if p.exists():
            shutil.rmtree(p)
    zip_path.unlink(missing_ok=True)
    DIST.mkdir(exist_ok=True)

    for need in (PAYLOAD, BASE, RELEASE_SRC / "install.ps1", RELEASE_SRC / "restore.ps1"):
        if not need.is_file():
            print(f"ERROR: 缺少 {need}")
            return 1

    items = load_changes()
    print(f"版本 {version}  改动 {len(items)} 项")

    internal = out / "_internal"
    internal.mkdir(parents=True)

    # ---- 补丁本体 ----
    shutil.copy2(PAYLOAD, internal / "rulesmo.ini")

    # ---- PowerShell 脚本：必须 UTF-8 BOM，否则 Windows PowerShell 读中文乱码 ----
    for f in ("install.ps1", "restore.ps1"):
        src = (RELEASE_SRC / f).read_text(encoding="utf-8")
        (internal / f).write_text(src, encoding="utf-8-sig")

    (internal / "version.txt").write_text(
        f"{version}\n改动 {len(items)} 项\n生成时间 {__import__('datetime').datetime.now():%Y-%m-%d %H:%M:%S}\n",
        encoding="utf-8")

    # ---- bat（纯 ASCII，避免 cmd 编码问题）----
    for f in ("安装.bat", "恢复原版.bat"):
        shutil.copyfile(RELEASE_SRC / f, out / f)

    # ---- 说明与公告（带 BOM，记事本可正常显示）----
    (out / "使用说明.txt").write_text(
        (RELEASE_SRC / "使用说明.txt").read_text(encoding="utf-8"), encoding="utf-8-sig")

    notice_src = WORK / "公告-定稿.md"
    if notice_src.is_file():
        (out / "平衡公告.md").write_text(notice_src.read_text(encoding="utf-8"), encoding="utf-8-sig")
    else:
        print("WARN: 未找到 公告-定稿.md，跳过")

    (out / "改动清单.md").write_text(gen_change_list(items), encoding="utf-8-sig")

    # ---- 校验清单 ----
    sums = []
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "SHA256SUMS.txt":
            sums.append(f"{sha256(p)}  {p.relative_to(out).as_posix()}")
    (out / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")

    # ---- 打包 zip ----
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(out.rglob("*")):
            if p.is_file():
                z.write(p, Path(name) / p.relative_to(out))

    print(f"\n已生成目录: {out}")
    print(f"已生成压缩包: {zip_path}  ({zip_path.stat().st_size:,} 字节)")
    print(f"补丁 SHA256: {sha256(internal / 'rulesmo.ini')}")
    print("\n包内文件:")
    for p in sorted(out.rglob("*")):
        if p.is_file():
            print(f"  {p.relative_to(out).as_posix():34} {p.stat().st_size:>10,} 字节")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
