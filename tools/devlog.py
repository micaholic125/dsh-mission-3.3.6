#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""创建/补全当天的开发日志（devlog/YYYY-MM-DD.md）。

用法:
  python tools/devlog.py              # 创建今天的日志（已存在则不动）
  python tools/devlog.py --force      # 已存在也重建（会覆盖！）
  python tools/devlog.py --append "完成|做了某事"

模板四段必填：完成 / 代办 / 风险 / 下一步（见 devlog/README.md）。
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
DEVLOG = WORK / "devlog"

TEMPLATE = """# {date} 开发日志

## 完成
- 

## 代办
- 

## 风险
- 

## 下一步
- 
"""


def today_path() -> Path:
    return DEVLOG / f"{datetime.date.today():%Y-%m-%d}.md"


def main(argv: list[str]) -> int:
    DEVLOG.mkdir(parents=True, exist_ok=True)
    path = today_path()

    if "--append" in argv and len(argv) > argv.index("--append") + 1:
        entry = argv[argv.index("--append") + 1]
        if not path.is_file():
            path.write_text(TEMPLATE.format(date=datetime.date.today()), encoding="utf-8")
        text = path.read_text(encoding="utf-8")
        stamp = datetime.datetime.now().strftime("%H:%M")
        text = text.replace("## 完成\n", f"## 完成\n- [{stamp}] {entry}\n", 1)
        path.write_text(text, encoding="utf-8")
        print(f"已追加到 {path.name}: {entry}")
        return 0

    if path.is_file() and "--force" not in argv:
        print(f"已存在，未覆盖: {path}")
        return 0

    path.write_text(TEMPLATE.format(date=datetime.date.today()), encoding="utf-8")
    print(f"已创建: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
