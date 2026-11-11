#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MO rulesmo.ini 行级安全编辑器：只改目标行的值，保留注释/空行/换行符/编码。

设计要点（沿用 D:\\Default Project 已验证的做法）：
  1. 改前先确认 [节] 与 键 都存在，避免写错位置
  2. 原子写入：先写 .tmp -> 校验 -> 替换
  3. 改后比对 sha，值没变就报错，防止"以为改了其实没改"
  4. 保留原文件编码（utf-8-sig / utf-8 / latin-1）与 CRLF

用法:
  python ini_edit.py <ini> get   <节> <键>
  python ini_edit.py <ini> set   <节> <键> <新值>
  python ini_edit.py <ini> list  <节>
  python ini_edit.py <ini> apply <变更.json>
  python ini_edit.py <ini> find  <关键字>          # 按节名/Name= 模糊查找

变更.json 格式:
  {"changes": [{"section": "APOC", "key": "Strength", "value": 900}, ...]}
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

SECTION_RE = re.compile(r"^\[([^\]]+)\]\s*$")


# ---------------------------------------------------------------- 编码处理
def read_text(path: Path) -> tuple[str, str]:
    """返回 (文本, 编码)。仅当原文件确有 BOM 时才用 utf-8-sig，避免凭空添加 BOM。"""
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    for enc in ("utf-8", "latin-1"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    raise ValueError(f"无法解码: {path}")


def sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------- 解析
def parse(text: str) -> dict[str, dict[str, str]]:
    """解析为 {节: {键: 值}}，同名键保留第一次出现。"""
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


def find_sections(sections: dict[str, dict[str, str]], query: str, limit: int = 40) -> list[str]:
    """按节名或 Name= 值模糊查找（不区分大小写）。"""
    q = query.strip().lower()
    if not q:
        return []
    hits: list[str] = []
    for sec, kv in sections.items():
        name = (kv.get("Name") or "").lower()
        uiname = (kv.get("UIName") or "").lower()
        if q in sec.lower() or q in name or q in uiname:
            hits.append(f"{sec}\tName={kv.get('Name', '')}\tUIName={kv.get('UIName', '')}")
            if len(hits) >= limit:
                break
    return hits


# ---------------------------------------------------------------- 写入
def set_key_in_text(text: str, section: str, key: str, value: str) -> tuple[str, str]:
    """在文本中定位 [节] 下的 key 行并替换其值，返回 (新文本, 旧值)。"""
    lines = text.splitlines(keepends=True)
    in_target = False
    done = False
    old_value = ""
    out: list[str] = []

    for line in lines:
        body = line.rstrip("\r\n")
        nl = line[len(body):]
        stripped = body.strip()

        m = SECTION_RE.match(stripped)
        if m:
            in_target = (m.group(1) == section)
            out.append(line)
            continue

        if in_target and not done and stripped and not stripped.startswith(";"):
            if "=" in body:
                left, _, right = body.partition("=")
                if left.strip() == key:
                    old_value = right.strip()
                    # 保留 key 原样（大小写/空格），只换值
                    out.append(f"{left}={value}{nl}")
                    done = True
                    continue
        out.append(line)

    if not done:
        raise KeyError(f"[{section}] 下找不到键 {key}（可能被注释或不存在）")
    return "".join(out), old_value


def write_atomic(path: Path, text: str, encoding: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding=encoding, newline="")  # newline="" 保住原 CRLF
    if not tmp.is_file() or tmp.stat().st_size == 0:
        raise IOError("临时文件异常")
    tmp.replace(path)


def cmd_get(path: Path, section: str, key: str) -> int:
    text, _ = read_text(path)
    secs = parse(text)
    if section not in secs:
        print(f"ERROR: 无此节 [{section}]")
        return 1
    if key not in secs[section]:
        print(f"ERROR: [{section}] 无此键 {key}")
        return 1
    print(secs[section][key])
    return 0


def cmd_list(path: Path, section: str) -> int:
    text, _ = read_text(path)
    secs = parse(text)
    if section not in secs:
        print(f"ERROR: 无此节 [{section}]")
        return 1
    for k, v in secs[section].items():
        print(f"{k}={v}")
    return 0


def cmd_find(path: Path, query: str) -> int:
    text, _ = read_text(path)
    secs = parse(text)
    hits = find_sections(secs, query)
    if not hits:
        print("没有匹配的节")
        return 1
    for h in hits:
        print(h)
    return 0


def set_many(path: Path, changes: list[dict]) -> int:
    text, enc = read_text(path)
    secs = parse(text)

    # 先整体校验，任一失败则一个都不写
    problems: list[str] = []
    for c in changes:
        sec, key = c["section"], c["key"]
        if sec not in secs:
            problems.append(f"无此节 [{sec}]")
        elif key not in secs[sec]:
            problems.append(f"[{sec}] 无此键 {key}")
    if problems:
        print("校验失败，未写入任何内容：")
        for p in problems:
            print("  - " + p)
        return 1

    sha_before = sha1(path)
    results = []
    for c in changes:
        text, old = set_key_in_text(text, c["section"], c["key"], str(c["value"]))
        results.append((c["section"], c["key"], old, str(c["value"])))

    write_atomic(path, text, enc)
    sha_after = sha1(path)
    if sha_after == sha_before:
        print("ERROR: 写入前后 sha1 相同，内容未生效")
        return 1

    print(f"已写入 {len(results)} 项  sha1 {sha_before[:10]} -> {sha_after[:10]}")
    for sec, key, old, new in results:
        flag = "  " if old != new else "= "
        print(f"{flag}[{sec}] {key}: {old} -> {new}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    path = Path(argv[1])
    if not path.is_file():
        print(f"ERROR: 文件不存在 {path}")
        return 1
    cmd = argv[2]

    if cmd == "get" and len(argv) >= 5:
        return cmd_get(path, argv[3], argv[4])
    if cmd == "list" and len(argv) >= 4:
        return cmd_list(path, argv[3])
    if cmd == "find" and len(argv) >= 4:
        return cmd_find(path, argv[3])
    if cmd == "set" and len(argv) >= 6:
        return set_many(path, [{"section": argv[3], "key": argv[4], "value": argv[5]}])
    if cmd == "apply" and len(argv) >= 4:
        spec = json.loads(Path(argv[3]).read_text(encoding="utf-8"))
        return set_many(path, spec["changes"])

    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
