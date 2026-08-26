#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
자리 검사 · 04 DESIGN

03 이 넘긴 것 중 어느 화면에도 안 들어간 것이 있는지 기계로 잰다.
눈으로 세면 매번 다르게 센다.

    python3 자리검사.py {작업폴더} --목록      03 산출물을 훑어 .kb/화면자리.tsv 를 만든다
    python3 자리검사.py {작업폴더} --검사      화면 칸이 빈 줄을 짚는다

--목록 을 다시 돌려도 이미 채운 「화면」 칸은 안 지운다.
03 이 문서를 고쳐서 항목이 늘었을 때 다시 돌리면 된다.

이 스크립트가 하는 판단은 셋뿐이다.
세는 것, 이미 채운 것을 지키는 것, 빈 칸을 짚는 것.
어느 화면에 넣을지는 안 정한다. 그건 04 가 한다.

★ 한 갈래에서 0개가 나오면 조용히 넘어가지 않고 「못 읽었다」고 말한다.
   03 이 문서 모양을 바꾸면 여기가 조용히 헛돌 수 있는 자리다.
"""

import json
import os
import re
import sys
import unicodedata

TSV_HEADER = ["종류", "이름", "화면"]

# 종류 이름. 화면에 그대로 나가는 말이라 한글로 둔다.
KIND_HUB = "큰갈래"
KIND_CLUSTER = "작은갈래"
KIND_POST = "글"
KIND_EMPTY = "비어있는것"
KIND_DOC = "문서"

ALL_KINDS = [KIND_HUB, KIND_CLUSTER, KIND_POST, KIND_EMPTY, KIND_DOC]


def nfc(s):
    """맥에서 한글 파일명이 NFD 로 온다. 안 맞추면 비교가 통째로 헛돈다."""
    return unicodedata.normalize("NFC", s)


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return nfc(f.read())


def table_rows(lines, start):
    """start 줄부터 이어지는 표의 몸통 줄을 돌려준다. 머리줄과 구분선은 뺀다."""
    rows = []
    i = start
    seen_divider = False
    while i < len(lines):
        line = lines[i].strip()
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip("|").split("|")]
        if re.fullmatch(r"[:\- ]+", "".join(cells)):
            seen_divider = True
            i += 1
            continue
        if seen_divider:
            rows.append(cells)
        i += 1
    return rows, i


def strip_md(s):
    """표 칸에서 굵게 · 링크 · 별표를 걷어낸다. 이름만 남긴다."""
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)   # 링크
    s = s.replace("**", "").replace("`", "")
    s = s.lstrip("★☆ ").strip()
    return s


def parse_structure(text):
    """구조.md 에서 큰 갈래 · 작은 갈래 · 글 · 비어 있는 것을 뽑는다."""
    lines = text.splitlines()
    found = {KIND_HUB: [], KIND_CLUSTER: [], KIND_POST: [], KIND_EMPTY: []}

    section = None          # 지금 어느 ## 절 안인가
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("## "):
            section = strip_md(stripped[3:])

        # ### 허브 N · 이름
        m = re.match(r"^###\s+허브\s*\d*\s*[·:.\-]?\s*(.+)$", stripped)
        if m:
            name = strip_md(m.group(1))
            if name:
                found[KIND_HUB].append(name)
            i += 1
            continue

        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            head = "".join(cells)
            rows, nxt = table_rows(lines, i)

            if "클러스터" in head:
                for r in rows:
                    name = strip_md(r[0])
                    if name:
                        found[KIND_CLUSTER].append(name)
            elif "글 제목 초안" in head or "글제목" in head.replace(" ", ""):
                for r in rows:
                    name = strip_md(r[0])
                    if name:
                        found[KIND_POST].append(name)
            elif section and "비어 있는 것" in section:
                for r in rows:
                    name = strip_md(r[0])
                    if name:
                        found[KIND_EMPTY].append(name)

            i = nxt
            continue

        i += 1

    return found


def parse_wiki(wiki_dir):
    """wiki/concepts/ 의 문서 제목을 뽑는다."""
    names = []
    if not os.path.isdir(wiki_dir):
        return names
    for fn in sorted(os.listdir(wiki_dir)):
        fn = nfc(fn)
        if not fn.endswith(".md") or fn.startswith("."):
            continue
        path = os.path.join(wiki_dir, fn)
        title = ""
        try:
            for line in read(path).splitlines():
                if line.startswith("# "):
                    title = strip_md(line[2:])
                    break
        except OSError:
            pass
        names.append(title or fn[:-3])
    return names


def dedupe(seq):
    seen = set()
    out = []
    for s in seq:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def load_tsv(path):
    """이미 채운 「화면」 칸을 지키려고 먼저 읽는다."""
    filled = {}
    if not os.path.isfile(path):
        return filled
    with open(path, "r", encoding="utf-8") as f:
        for n, line in enumerate(f):
            cells = nfc(line.rstrip("\n")).split("\t")
            if n == 0 and cells[:2] == TSV_HEADER[:2]:
                continue
            if len(cells) >= 3 and cells[2].strip():
                filled[(cells[0], cells[1])] = cells[2].strip()
    return filled


def cmd_list(kb, out_tsv):
    struct_path = os.path.join(kb, "outputs", "03-structure", "구조.md")
    wiki_dir = os.path.join(kb, "wiki", "concepts")

    if not os.path.isfile(struct_path):
        print("03 구조 문서가 안 보입니다.")
        print("  찾은 자리  outputs/03-structure/구조.md")
        print("03 을 먼저 돌리셔야 합니다.")
        return 2

    found = parse_structure(read(struct_path))
    found[KIND_DOC] = parse_wiki(wiki_dir)
    for k in ALL_KINDS:
        found[k] = dedupe(found[k])

    filled = load_tsv(out_tsv)

    os.makedirs(os.path.dirname(out_tsv), exist_ok=True)
    total = 0
    with open(out_tsv, "w", encoding="utf-8") as f:
        f.write("\t".join(TSV_HEADER) + "\n")
        for kind in ALL_KINDS:
            for name in found[kind]:
                f.write("%s\t%s\t%s\n" % (kind, name, filled.get((kind, name), "")))
                total += 1

    print("03 이 넘긴 것을 훑었습니다. 모두 %d 개." % total)
    for kind in ALL_KINDS:
        n = len(found[kind])
        mark = "" if n else "   ← 못 읽었습니다. 03 문서 모양이 바뀌었는지 봐야 합니다"
        print("  %-6s %4d%s" % (kind, n, mark))
    kept = sum(1 for k in filled if k in {(kd, nm) for kd in ALL_KINDS for nm in found[kd]})
    if kept:
        print("이미 채워 두신 화면 칸 %d 개는 그대로 뒀습니다." % kept)
    return 0


def cmd_check(kb, out_tsv, out_json):
    if not os.path.isfile(out_tsv):
        print("화면자리.tsv 가 없습니다. --목록 을 먼저 돌리세요.")
        return 2

    rows = []
    with open(out_tsv, "r", encoding="utf-8") as f:
        for n, line in enumerate(f):
            cells = nfc(line.rstrip("\n")).split("\t")
            if n == 0 and cells[:2] == TSV_HEADER[:2]:
                continue
            if len(cells) < 2 or not cells[1].strip():
                continue
            while len(cells) < 3:
                cells.append("")
            rows.append(cells[:3])

    missing = [r for r in rows if not r[2].strip()]

    by_kind = {}
    for kind, name, screen in rows:
        d = by_kind.setdefault(kind, {"전부": 0, "자리있음": 0})
        d["전부"] += 1
        if screen.strip():
            d["자리있음"] += 1

    result = {
        "전부": len(rows),
        "자리있음": len(rows) - len(missing),
        "자리없음": len(missing),
        "갈래별": by_kind,
        "자리없는것": [{"종류": r[0], "이름": r[1]} for r in missing],
    }
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    if not rows:
        print("잰 것이 하나도 없습니다. --목록 이 제대로 돌았는지 봐야 합니다.")
        return 2

    if not missing:
        print("자리 검사 통과. %d 개가 전부 어느 화면엔가 들어갔습니다." % len(rows))
        return 0

    print("어느 화면에도 안 들어간 것이 %d 개 있습니다." % len(missing))
    for kind in ALL_KINDS:
        items = [r[1] for r in missing if r[0] == kind]
        if not items:
            continue
        print("  %s  %d 개" % (kind, len(items)))
        for name in items[:8]:
            print("      %s" % name)
        if len(items) > 8:
            print("      그 밖 %d 개는 .kb/화면검사.json 에 있습니다" % (len(items) - 8))
    return 1


def main(argv):
    if len(argv) < 3 or argv[2] not in ("--목록", "--검사"):
        print(__doc__.strip())
        return 2

    kb = os.path.expanduser(argv[1])
    if not os.path.isdir(kb):
        print("작업 폴더가 안 보입니다.  %s" % kb)
        return 2

    out_tsv = os.path.join(kb, "outputs", "04-design", ".kb", "화면자리.tsv")
    out_json = os.path.join(kb, "outputs", "04-design", ".kb", "화면검사.json")

    if argv[2] == "--목록":
        return cmd_list(kb, out_tsv)
    return cmd_check(kb, out_tsv, out_json)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
