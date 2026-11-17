#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公共路径解析：仓库根目录 + 《心灵终结 3.3.6》游戏目录定位。

所有工具都从这里取路径，保证「从任意工作目录（cwd）调用」都能正确工作：

- **仓库根目录**：由本文件位置推导（`tools/` 的上一级），与当前 cwd 无关；
- **游戏目录**：`--game-dir` > 环境变量 `MO_GAME_DIR` > 自动探测常见安装位置。
  公开仓库不含任何游戏数据（`.mix` / `.exe`），游戏目录只在使用者本机上由工具定位。

本模块不依赖第三方库，可被任何 Python 3.8+ 直接导入。
"""
from __future__ import annotations

import os
from pathlib import Path

#: 仓库根目录（`tools/` 的上一级），永远与 cwd 无关
REPO_ROOT = Path(__file__).resolve().parents[1]

#: MO 3.3.6 规则包文件名（内含 rulesmo.ini 等全部规则文件，公开仓库不分发）
MIX_NAME = "expandmo99.mix"

#: 外置覆盖文件名（部署目标 / 回滚删除对象）
OVERRIDE_NAME = "rulesmo.ini"

#: 指定游戏目录的环境变量名
GAME_ENV = "MO_GAME_DIR"

#: 自动探测用的常见安装子目录（与盘符组合；仅作候选，始终可被 --game-dir / MO_GAME_DIR 覆盖）
GAME_SUBDIRS = (
    "Mental Omega",
    "Mental Omega 3.3.6",
    "MentalOmega",
    "Games/Mental Omega",
    "Games/MentalOmega",
    "Program Files/Mental Omega",
    "Program Files (x86)/Mental Omega",
    "Program Files/Mental Omega 3.3.6",
    "Program Files (x86)/Mental Omega 3.3.6",
)

#: 兜底盘符（`os.listdrives()` 不可用时才用）
_FALLBACK_DRIVES = tuple("CDEFGHIJKLMNOPQRSTUVWXYZ")


def repo_path(value: str | os.PathLike[str]) -> Path:
    """把用户传入的路径转成绝对路径：相对路径一律按**仓库根目录**解析。

    这样无论从哪个 cwd 调用脚本，`--out _tmp/x.ini` 都落在同一个地方。
    """
    p = Path(value).expanduser()
    return p if p.is_absolute() else (REPO_ROOT / p)


def looks_like_game_dir(path: Path) -> bool:
    """目录存在且含 expandmo99.mix 才算「像 MO 3.3.6 安装目录」。"""
    try:
        return path.is_dir() and (path / MIX_NAME).is_file()
    except OSError:
        return False


def _drive_roots() -> list[Path]:
    """返回本机真实存在的盘符根目录（如 C:/、D:/）。"""
    try:
        drives = list(os.listdrives())  # Python 3.12+ Windows
    except (AttributeError, OSError):
        drives = [f"{d}:\\" for d in _FALLBACK_DRIVES]
    roots: list[Path] = []
    for d in drives:
        try:
            p = Path(d)
            if p.is_dir():
                roots.append(p)
        except OSError:
            continue
    return roots


def _ancestors(start: Path, depth: int) -> list[Path]:
    """从 start 起向上取 depth 层目录（含 start）。"""
    out: list[Path] = []
    p = start
    for _ in range(depth):
        out.append(p)
        if p.parent == p:
            break
        p = p.parent
    return out


def candidate_game_dirs() -> list[Path]:
    """按优先级列出所有候选游戏目录（已去重，未做存在性过滤）。"""
    cands: list[Path] = []
    seen: set[str] = set()

    def add(p: Path) -> None:
        try:
            key = str(p.resolve()).lower()
        except OSError:
            key = str(p).lower()
        if key not in seen:
            seen.add(key)
            cands.append(p)

    env = os.environ.get(GAME_ENV, "").strip()
    if env:
        add(Path(env).expanduser())

    # 1) 当前工作目录及其上层：玩家可能就在游戏目录里运行
    try:
        for p in _ancestors(Path.cwd(), 3):
            add(p)
    except OSError:
        pass

    # 2) 仓库目录及其上层：玩家可能把仓库 clone 在游戏目录里
    for p in _ancestors(REPO_ROOT, 3):
        add(p)

    # 3) 各盘符下的常见安装位置
    for root in _drive_roots():
        for sub in GAME_SUBDIRS:
            add(root / sub)

    return cands


def find_game_dir(cli_value: str | None = None) -> tuple[Path | None, str]:
    """定位游戏目录。

    返回 `(目录, 来源说明)`；找不到时返回 `(None, 失败来源)`。
    来源说明取值：`--game-dir` / `环境变量 MO_GAME_DIR` / `自动探测`，
    失败时用于生成对应的中文提示（见 :func:`game_dir_hint`）。

    优先级：`--game-dir` > 环境变量 `MO_GAME_DIR` > 自动探测。
    显式指定（命令行/环境变量）只要求目录存在；自动探测则要求目录里真有
    `expandmo99.mix`，避免误认。
    """
    if cli_value:
        p = Path(cli_value).expanduser()
        if p.is_dir():
            return p.resolve(), "--game-dir"
        return None, "--game-dir"

    env = os.environ.get(GAME_ENV, "").strip()
    if env:
        p = Path(env).expanduser()
        if p.is_dir():
            return p.resolve(), f"环境变量 {GAME_ENV}"
        return None, f"环境变量 {GAME_ENV}"

    for p in candidate_game_dirs():
        if looks_like_game_dir(p):
            return p.resolve(), "自动探测"
    return None, ""


def game_dir_hint(cli_value: str | None = None, source: str = "") -> str:
    """生成面向玩家的中文「找不到游戏目录」提示（不抛异常，直接可 print）。"""
    lines = ["", "【未找到《心灵终结 3.3.6》游戏目录】"]
    if source == "--game-dir" and cli_value:
        lines.append(f"  你指定的目录不存在：{cli_value}")
    elif source.startswith("环境变量") and os.environ.get(GAME_ENV):
        lines.append(f"  环境变量 {GAME_ENV} 指向的目录不存在：{os.environ.get(GAME_ENV)}")
    else:
        lines.append("  自动探测没有找到（已在各盘符的 Mental Omega / Games\\Mental Omega 等常见位置查找）")
    lines += [
        "",
        "请用下面任一方式告诉工具游戏装在哪（目录里应有 expandmo99.mix）：",
        '  1) 命令行加参数：  --game-dir "D:/Mental Omega"',
        f'  2) 设置环境变量：  set {GAME_ENV}=D:\\Mental Omega',
        "",
        "游戏目录示例（常见安装位置）：",
        r'  D:\Mental Omega\expandmo99.mix',
        "",
        "提示：本工具只读取游戏文件，不会修改 .mix / .exe。",
    ]
    return "\n".join(lines)
