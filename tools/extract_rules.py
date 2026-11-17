#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从《心灵终结 3.3.6》游戏目录的 expandmo99.mix 中提取原版 rulesmo.ini（基准文件）。

公开仓库**不含任何游戏数据**：每位玩家用自己的游戏文件就能还原出与作者逐字节一致的
基准 `rulesmo_original.ini`，再用它生成补丁。MIX 内的原文件始终只读，不会被修改。

提取原理（详见 docs/02-技术方案.md「提取方法」）：

- MIX 没有加密，每个 INI 都带团队注释横幅，可据此直接切割，无需解析索引表；
- **起点**：注释横幅行首 `;;;;Mental Omega 3.3.6 RULES CONTROL FILE;;;;`
  （横幅前面可能还有上一个文件残留的内容，因此以连续分号的起点为准）；
- **终点**：`END OF RULES FILE` 行末（含该行换行符），紧随其后的纯 `;;;`
  收尾行只作结束哨兵、不计入文件内容（MIX 里它后面紧贴下一个文件的首行，无换行分隔）。

MO 3.3.6 基准（逐字节一致，脚本会自动校验）：

============================  ==========================================
起点偏移                      2,436,130
终点偏移                      4,726,451
文件大小                      2,290,321 字节
sha1                          83d653a6ce70739a17d8fb85c9b38c391fbe6ef6
节 / 键                       4,725 / 108,275
============================  ==========================================

用法::

    python tools/extract_rules.py                       # 自动探测游戏目录，输出到仓库根 rulesmo_original.ini
    python tools/extract_rules.py --game-dir "D:/Mental Omega"
    python tools/extract_rules.py --game-dir "D:/Mental Omega" --out _tmp/check.ini --force
    set MO_GAME_DIR=D:\\Mental Omega  &  python tools/extract_rules.py

相对路径一律按**仓库根目录**解析（因此可从任意 cwd 运行）。
默认输出已存在时不会覆盖：内容一致则跳过，不一致则拒绝并提示加 ``--force``。

退出码：0 成功 / 1 提取或写入失败 / 2 参数或游戏目录问题
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mo_paths import (  # noqa: E402
    GAME_ENV,
    MIX_NAME,
    REPO_ROOT,
    find_game_dir,
    game_dir_hint,
    repo_path,
)

#: 横幅文字（起点定位锚点）
START_BANNER = b"Mental Omega 3.3.6 RULES CONTROL FILE"
#: 横幅整行（文档/日志里展示用）
START_LINE = b";;;;Mental Omega 3.3.6 RULES CONTROL FILE;;;;"
#: 终点定位锚点
END_BANNER = b"END OF RULES FILE"

#: MO 3.3.6 的已知基准（用于自检，不匹配时给出警告）
EXPECTED_SIZE = 2_290_321
EXPECTED_SHA1 = "83d653a6ce70739a17d8fb85c9b38c391fbe6ef6"
EXPECTED_SECTIONS = 4_725
EXPECTED_KEYS = 108_275


class ExtractError(RuntimeError):
    """提取失败（消息为面向玩家的中文说明）。"""


def sha1_bytes(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def locate_rules(data: bytes) -> tuple[int, int, bool]:
    """在 MIX 字节流中定位规则文件范围。

    返回 ``(起点, 终点, 是否找到 ;;; 收尾行)``，区间为左闭右开 ``[起点, 终点)``。

    - 起点：横幅文字第一次出现处，再向左吃掉连续的分号（横幅前面的
      ``;;;;`` 数量可能不止 4 个，且前面可能紧贴上一个文件的内容）；
    - 终点：``END OF RULES FILE`` 所在行的行末（含换行符）。
    """
    pos = data.find(START_BANNER)
    if pos < 0:
        raise ExtractError(
            f"这个 MIX 里找不到规则文件横幅（{START_BANNER.decode('ascii')}）。\n"
            "  可能原因：游戏不是《心灵终结 3.3.6》，或 expandmo99.mix 被其他 MOD 覆盖过。\n"
            "  请确认游戏版本，或用 --mix 指定正确的 expandmo99.mix。"
        )
    start = pos
    while start > 0 and data[start - 1:start] == b";":
        start -= 1

    end_pos = data.find(END_BANNER, start)
    if end_pos < 0:
        raise ExtractError(
            f"规则文件起点之后找不到结束标记（{END_BANNER.decode('ascii')}）。\n"
            "  这个 MIX 可能不完整或不是 3.3.6 原版，请确认游戏文件未被修改。"
        )
    nl = data.find(b"\n", end_pos)
    if nl < 0:
        raise ExtractError("规则文件结束标记之后没有换行符，MIX 可能已损坏。")
    end = nl + 1  # 含该行换行符

    # 校验「紧随的 ;;; 收尾行」：只作结束哨兵，不计入文件内容。
    # 注意：MIX 里这个收尾行后面紧贴着下一个文件的首行（没有换行分隔），
    # 所以只检查它是否以连续的 ; 开头，不能按「整行都是分号」判断。
    has_terminator = data[end:end + 3] == b";;;"
    if end <= start:
        raise ExtractError("定位结果异常：结束偏移不大于起点偏移，MIX 可能已损坏。")
    return start, end, has_terminator


def count_stats(chunk: bytes) -> tuple[int, int]:
    """统计节数 / 键数（与 docs/06-数据参考.md 的口径一致）。"""
    text = chunk.decode("latin-1")
    sections = keys = 0
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith(";"):
            continue
        if s.startswith("[") and "]" in s:
            sections += 1
        elif "=" in s:
            keys += 1
    return sections, keys


def write_atomic(path: Path, data: bytes) -> None:
    """原子写入：先写 .tmp → 校验大小 → 替换。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    if tmp.stat().st_size != len(data):
        tmp.unlink(missing_ok=True)
        raise ExtractError(f"临时文件写入不完整：{tmp}")
    tmp.replace(path)


def resolve_mix(args: argparse.Namespace) -> tuple[Path | None, str]:
    """确定要读取的 MIX 文件，返回 (路径, 来源说明)；失败返回 (None, 中文原因)。"""
    if args.mix:
        mix = repo_path(args.mix)
        if not mix.is_file():
            return None, f"指定的 --mix 文件不存在：{mix}"
        return mix, "--mix"

    game, source = find_game_dir(args.game_dir)
    if game is None:
        return None, game_dir_hint(args.game_dir, source)

    mix = game / MIX_NAME
    if not mix.is_file():
        return None, (
            f"在游戏目录里没有找到 {MIX_NAME}：\n  {game}\n"
            "  请确认这是《心灵终结 3.3.6》的安装目录（不是 3.3.5 或其它 MOD），\n"
            f'  或用 --game-dir 重新指定，例如：--game-dir "D:/Mental Omega"'
        )
    return mix, f"{source}：{game}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="extract_rules.py",
        description="从《心灵终结 3.3.6》的 expandmo99.mix 提取原版 rulesmo.ini（基准文件）。",
        epilog=(
            "示例：\n"
            '  python tools/extract_rules.py --game-dir "D:/Mental Omega"\n'
            '  python tools/extract_rules.py --game-dir "D:/Mental Omega" --out _tmp/check.ini --force\n'
            f"  set {GAME_ENV}=D:\\Mental Omega  &  python tools/extract_rules.py\n\n"
            "相对路径按仓库根目录解析；默认输出已存在时不会覆盖（一致则跳过，不一致需 --force）。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--game-dir", metavar="目录", default=None,
                    help=f"MO 3.3.6 安装目录（含 {MIX_NAME}）。默认读环境变量 {GAME_ENV}，再自动探测常见位置")
    ap.add_argument("--mix", metavar="文件", default=None,
                    help="直接指定 expandmo99.mix 的路径（默认用游戏目录下的那个）")
    ap.add_argument("--out", metavar="文件", default=None,
                    help="输出文件（默认：仓库根 rulesmo_original.ini；相对路径按仓库根解析）")
    ap.add_argument("--force", action="store_true",
                    help="输出文件已存在时强制覆盖（默认拒绝覆盖）")
    ap.add_argument("--strict", action="store_true",
                    help="提取结果与已知 MO 3.3.6 基准（字节数/sha1）不一致时直接报错退出")
    args = ap.parse_args(argv)

    out_path = repo_path(args.out) if args.out else (REPO_ROOT / "rulesmo_original.ini")

    mix, detail = resolve_mix(args)
    if mix is None:
        print(detail, file=sys.stderr)
        return 2

    print("=== 从 MIX 提取原版 rulesmo.ini ===")
    print(f"MIX 文件: {mix}")
    print(f"定位来源: {detail}")

    try:
        data = mix.read_bytes()
    except OSError as exc:
        print(f"\n读取失败：{mix}\n  {exc}\n  请确认文件没有被占用、且当前用户有读取权限。", file=sys.stderr)
        return 1
    print(f"MIX 大小: {len(data):,} 字节")

    try:
        start, end, has_terminator = locate_rules(data)
        chunk = data[start:end]
        sections, keys = count_stats(chunk)
    except ExtractError as exc:
        print(f"\n提取失败：{exc}", file=sys.stderr)
        return 1

    got_sha1 = sha1_bytes(chunk)
    print(f"起点偏移: {start:,}")
    print(f"终点偏移: {end:,}（END OF RULES FILE 行末"
          + ("，不含其后 ;;; 收尾行" if has_terminator else "，未发现 ;;; 收尾行") + "）")
    print(f"提取大小: {len(chunk):,} 字节")
    print(f"节 / 键 : {sections:,} / {keys:,}")
    print(f"sha1    : {got_sha1}")

    match = (len(chunk) == EXPECTED_SIZE and got_sha1 == EXPECTED_SHA1)
    if match:
        print("校验    : 与 MO 3.3.6 基准一致（字节数与 sha1 均匹配）")
    else:
        print("校验    : [警告] 与已知 MO 3.3.6 基准不一致")
        print(f"          期望 {EXPECTED_SIZE:,} 字节 / {EXPECTED_SHA1}")
        print(f"          实际 {len(chunk):,} 字节 / {got_sha1}")
        print("          可能是不同游戏版本、或 MIX 被其它 MOD 改过。")
        if args.strict:
            print("\n--strict 已开启：不一致视为失败，未写入文件。", file=sys.stderr)
            return 1

    # ---- 输出文件保护：默认不覆盖 ----
    if out_path.is_file() and not args.force:
        try:
            old = out_path.read_bytes()
        except OSError:
            old = b""
        if old == chunk:
            print(f"\n输出文件已存在且内容一致，跳过写入：{out_path}")
            print("（如需强制重写，加 --force）")
            return 0
        print(f"\n输出文件已存在，拒绝覆盖：{out_path}")
        print("  如需覆盖请加 --force；或改用 --out 指定其它路径，例如：--out _tmp/rulesmo_original.ini")
        return 1

    try:
        write_atomic(out_path, chunk)
    except (OSError, ExtractError) as exc:
        print(f"\n写入失败：{out_path}\n  {exc}", file=sys.stderr)
        return 1

    print(f"\n已写入: {out_path}")
    print("下一步：")
    print("  python tools/build_override.py changes/batch1.json changes/batch2.json "
          "changes/batch3.json changes/batch4.json")
    print("  python tools/deploy.py check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
