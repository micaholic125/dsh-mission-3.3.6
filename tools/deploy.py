#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部署 / 回滚 rulesmo.ini 到游戏目录，带进程检查、强制备份与校验。

游戏目录**不再写死作者本机路径**，按以下顺序解析（任一方式都行）：

1. 命令行：``--game-dir "D:/Mental Omega"``
2. 环境变量：``set MO_GAME_DIR=D:\\Mental Omega``
3. 自动探测：各盘符下的 ``Mental Omega`` / ``Games\\Mental Omega`` 等常见安装位置

用法::

    python tools/deploy.py check     [--game-dir ...]   # 只体检：游戏是否运行、当前有无覆盖文件
    python tools/deploy.py deploy    [--game-dir ...]   # 备份 + 部署 + 校验
    python tools/deploy.py rollback  [--game-dir ...]   # 回滚（删除覆盖文件）并校验
    python tools/deploy.py drill     [--game-dir ...]   # 回滚演练：部署→删→验→再部署

安全规则（见 docs/05-安全规范.md）：

1. 游戏进程运行中，拒绝部署/回滚
2. 部署前必须备份：已有覆盖文件则复制；无则留 NO_EXISTING_FILE.txt
3. 备份目录名 YYYYMMDD_HHMMSS，含 sha1_manifest.txt
4. 部署后读回校验 sha1

本脚本只读取游戏目录里的 ``expandmo99.mix`` / ``gamemd.exe`` 等文件用于留证，
**不会修改** MIX 与可执行文件；回滚只删除游戏目录下的外置 ``rulesmo.ini``。
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mo_paths import (  # noqa: E402
    GAME_ENV,
    MIX_NAME,
    OVERRIDE_NAME,
    REPO_ROOT,
    find_game_dir,
    game_dir_hint,
)

WORK = REPO_ROOT
OVERRIDE = OVERRIDE_NAME
WORK_OVERRIDE = WORK / OVERRIDE
BASE = WORK / "rulesmo_original.ini"
BACKUP_ROOT = WORK / "backup"

GAME_PROCS = ("gamemd.exe", "MentalOmegaClient.exe")
REF_FILES = (MIX_NAME, "gamemd.exe", "MentalOmegaClient.exe")


def sha1(p: Path) -> str:
    h = hashlib.sha1()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def running_game() -> list[str]:
    try:
        r = subprocess.run(["tasklist", "/FO", "CSV", "/NH"],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=30)
        low = (r.stdout or "").lower()
    except Exception as e:  # noqa: BLE001
        print(f"WARN: 无法执行 tasklist（{e}），跳过进程检查，请自行确认游戏已关闭")
        return []
    return [n for n in GAME_PROCS if n.lower() in low]


def count_diffs(a: Path, b: Path) -> int | None:
    """比对两份 INI 的 [节]+键 级差异数；无法比对返回 None。"""
    if not (a.is_file() and b.is_file()):
        return None
    try:
        from ini_edit import parse, read_text  # 同目录

        sa = parse(read_text(a)[0])
        sb = parse(read_text(b)[0])
    except Exception:
        return None
    n = 0
    for sec, kv in sb.items():
        base_kv = sa.get(sec, {})
        for k, v in kv.items():
            if base_kv.get(k) != v:
                n += 1
        for k in base_kv:
            if k not in kv:
                n += 1
    for sec in sa:
        if sec not in sb:
            n += 1
    return n


def resolve_game(cli_game: str | None, *, quiet: bool = False) -> Path | None:
    """定位游戏目录；失败时打印中文提示并返回 None。"""
    game, source = find_game_dir(cli_game)
    if game is None:
        print(game_dir_hint(cli_game, source))
        return None
    if not quiet:
        print(f"游戏目录: {game}（来源：{source}）")
    return game


def cmd_check(cli_game: str | None) -> int:
    print("=== 体检 ===")
    game, source = find_game_dir(cli_game)
    if game is None:
        print("游戏目录: 未找到")
        print(game_dir_hint(cli_game, source))
    else:
        print(f"游戏目录: {game}（来源：{source}）  存在={game.is_dir()}")
        procs = running_game()
        print(f"游戏进程: {'运行中 -> ' + ', '.join(procs) if procs else '未运行'}")
        tgt = game / OVERRIDE
        if tgt.is_file():
            print(f"已有覆盖文件: 是  大小={tgt.stat().st_size:,}  sha1={sha1(tgt)[:12]}")
            d = count_diffs(BASE, tgt)
            print(f"当前生效改动数: {d if d is not None else '无法比对'} 项（基准 {BASE.name}）")
        else:
            print("已有覆盖文件: 无（当前为原版状态）")

    print(f"待部署文件: {WORK_OVERRIDE}  存在={WORK_OVERRIDE.is_file()}")
    if WORK_OVERRIDE.is_file():
        print(f"         大小={WORK_OVERRIDE.stat().st_size:,}  sha1={sha1(WORK_OVERRIDE)[:12]}")
        if game is not None:
            tgt = game / OVERRIDE
            same = tgt.is_file() and sha1(tgt) == sha1(WORK_OVERRIDE)
            print(f"游戏目录是否已是该版本: {'是（无需重复部署）' if same else '否（可部署）'}")
    if not BASE.is_file():
        print(f"提示：基准文件不存在 {BASE}")
        print("      请先运行：python tools/extract_rules.py --game-dir \"D:/Mental Omega\"")
    if game is None:
        print("\n体检结果：游戏目录未找到，其余项目仅供参考。")
        return 2
    return 0


def make_backup(game: Path, tag: str) -> Path:
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    d = BACKUP_ROOT / f"{stamp}_{tag}"
    d.mkdir(parents=True, exist_ok=False)

    tgt = game / OVERRIDE
    lines = [f"# 备份时间: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}",
             f"# 说明: {tag}",
             f"# 游戏目录: {game}", ""]

    if tgt.is_file():
        shutil.copy2(tgt, d / OVERRIDE)
        (d / "NO_EXISTING_FILE.txt").unlink(missing_ok=True)
        lines.append(f"{OVERRIDE}  {sha1(tgt)}   (部署前的旧覆盖文件，已备份)")
        print(f"已备份旧覆盖文件 -> {d / OVERRIDE}")
    else:
        (d / "NO_EXISTING_FILE.txt").write_text(
            "部署前游戏目录内没有 rulesmo.ini（首次部署）。\n"
            "回滚方式：直接删除游戏目录下的 rulesmo.ini 即可恢复原版。\n",
            encoding="utf-8")
        lines.append(f"{OVERRIDE}  (无旧文件，部署前不存在)")
        print(f"部署前无旧覆盖文件，已记录标记 -> {d / 'NO_EXISTING_FILE.txt'}")

    if BASE.is_file():
        lines.append(f"基准 rulesmo_original.ini  {sha1(BASE)}   (从 MIX 抽出的原版，只读)")
    for name in REF_FILES:
        p = game / name
        if p.is_file():
            lines.append(f"{name}  {sha1(p)}   ({p.stat().st_size:,} 字节，本次不修改，仅留证)")

    (d / "sha1_manifest.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已写清单 -> {d / 'sha1_manifest.txt'}")
    return d


def do_write(game: Path) -> None:
    if not WORK_OVERRIDE.is_file():
        raise SystemExit(f"ERROR: 待部署文件不存在 {WORK_OVERRIDE}\n"
                         "       请先运行 python tools/build_override.py 生成 rulesmo.ini")
    if not game.is_dir():
        raise SystemExit(f"ERROR: 游戏目录不存在 {game}\n"
                         f'       请用 --game-dir 指定，或设置环境变量 {GAME_ENV}')
    shutil.copy2(WORK_OVERRIDE, game / OVERRIDE)


def verify(game: Path, expected: str) -> bool:
    tgt = game / OVERRIDE
    if not tgt.is_file():
        print("  校验失败：目标文件不存在")
        return False
    got = sha1(tgt)
    ok = got == expected
    print(f"  部署后 sha1 = {got[:12]}  期望 {expected[:12]}  {'一致 ✓' if ok else '不一致 ✗'}")
    return ok


def cmd_deploy(cli_game: str | None) -> int:
    game = resolve_game(cli_game)
    if game is None:
        return 2
    if not WORK_OVERRIDE.is_file():
        print(f"待部署文件不存在：{WORK_OVERRIDE}")
        print("请先运行：python tools/build_override.py changes/batch1.json ...")
        return 1
    procs = running_game()
    if procs:
        print(f"拒绝部署：游戏正在运行 -> {', '.join(procs)}")
        print("请完全退出游戏后重试。")
        return 2
    expected = sha1(WORK_OVERRIDE)
    bdir = make_backup(game, "deploy")
    do_write(game)
    ok = verify(game, expected)
    print(f"\n部署完成 -> {game / OVERRIDE}")
    print(f"备份目录 -> {bdir}")
    print("\n回滚命令: python tools/deploy.py rollback")
    print(f"或手工:   删除 {game / OVERRIDE}")
    return 0 if ok else 1


def cmd_rollback(cli_game: str | None) -> int:
    game = resolve_game(cli_game)
    if game is None:
        return 2
    procs = running_game()
    if procs:
        print(f"拒绝回滚：游戏正在运行 -> {', '.join(procs)}")
        return 2
    tgt = game / OVERRIDE
    if not tgt.is_file():
        print("当前没有覆盖文件，已是原版状态。")
        return 0
    make_backup(game, "rollback")  # 回滚前也备份，避免回滚掉不该回滚的东西
    tgt.unlink()
    print(f"已删除 {tgt}")
    print(f"存在性检查: {tgt.exists()}  （应为 False）")
    return 0 if not tgt.exists() else 1


def cmd_drill(cli_game: str | None) -> int:
    """回滚演练：部署 -> 校验 -> 删除 -> 确认 -> 再部署 -> 校验。最终保持已部署。"""
    print("########## 回滚演练开始 ##########")
    game = resolve_game(cli_game)
    if game is None:
        return 2
    if not WORK_OVERRIDE.is_file():
        print(f"待部署文件不存在：{WORK_OVERRIDE}")
        return 1
    procs = running_game()
    if procs:
        print(f"拒绝演练：游戏正在运行 -> {', '.join(procs)}")
        return 2
    expected = sha1(WORK_OVERRIDE)
    tgt = game / OVERRIDE

    print("\n[1/4] 部署")
    bdir = make_backup(game, "drill")
    do_write(game)
    if not verify(game, expected):
        return 1

    print("\n[2/4] 回滚（删除覆盖文件）")
    tgt.unlink()
    gone = not tgt.exists()
    print(f"  删除后存在性 = {tgt.exists()}  {'✓' if gone else '✗'}")
    if not gone:
        return 1

    print("\n[3/4] 确认恢复原版：游戏目录已无 rulesmo.ini，MIX 内原件未被触碰")
    print(f"  基准文件仍在工作区: {BASE.is_file()}")

    print("\n[4/4] 重新部署")
    do_write(game)
    ok = verify(game, expected)
    print("\n########## 回滚演练结束 ##########")
    print(f"备份目录 -> {bdir}")
    print("最终状态：已部署（可随时 python tools/deploy.py rollback 一键还原）")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="deploy.py",
        description="部署 / 回滚 rulesmo.ini 到《心灵终结 3.3.6》游戏目录（带进程检查、强制备份与 sha1 校验）。",
        epilog=(
            "游戏目录解析顺序：--game-dir > 环境变量 " + GAME_ENV + " > 自动探测常见安装位置。\n"
            "示例：\n"
            '  python tools/deploy.py check\n'
            '  python tools/deploy.py check --game-dir "D:/Mental Omega"\n'
            '  set ' + GAME_ENV + '=D:\\Mental Omega  &  python tools/deploy.py deploy'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("action", choices=["check", "deploy", "rollback", "drill"],
                    help="check=只体检 / deploy=备份+部署+校验 / rollback=回滚 / drill=回滚演练")
    ap.add_argument("--game-dir", metavar="目录", default=None,
                    help=f"MO 3.3.6 安装目录（含 {MIX_NAME}）。默认读环境变量 {GAME_ENV}，再自动探测")
    args = ap.parse_args(argv)
    return {"check": cmd_check, "deploy": cmd_deploy,
            "rollback": cmd_rollback, "drill": cmd_drill}[args.action](args.game_dir)


if __name__ == "__main__":
    raise SystemExit(main())
