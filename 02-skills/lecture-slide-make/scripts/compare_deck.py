#!/usr/bin/env python3
"""손질본 → 생성기 환류. 생성한 pptx 와 사용자가 손으로 마감한 pptx 를 실측 대조한다.

    python3 compare_deck.py <생성본.pptx> <손질본.pptx>

목적은 "무엇이 더 예쁜가"가 아니라 **생성기가 못 내는 형태를 찾아내는 것**이다.
과거 손질본을 이 대조로 되짚어 보니 세 가지를 손으로 찾아냈고, 셋 다
문서에는 안 적혀 있던 것이었다 — 마커 없는 본문, 본문 폰트 크기 변경, 러닝헤드 생존.
같은 일을 다음 덱에서 또 손으로 하지 않기 위해 스크립트로 굳힌다.

읽기 전용이다. 어떤 파일도 쓰지 않는다.
"""
import sys, collections
from pathlib import Path
from pptx import Presentation
from pptx.util import Emu

PT = lambda emu: round(Emu(emu).inches, 2)


def scan(path):
    prs = Presentation(path)
    d = {"n": len(prs.slides), "sizes": collections.Counter(), "marker": 0,
         "img": 0, "img_slides": 0, "layouts": collections.Counter(),
         "titles": [], "plain_body": 0, "words": [], "runhead": 0, "notes": 0}
    for s in prs.slides:
        d["layouts"][s.slide_layout.name] += 1
        has_marker = has_img = has_plain = False
        words = 0
        for sh in s.shapes:
            if sh.shape_type == 13:
                d["img"] += 1
                has_img = True
            if not sh.has_text_frame:
                continue
            t = sh.text_frame.text
            if not t.strip():
                continue
            words += len(t.split())
            sizes = {round(r.font.size.pt, 2)
                     for p in sh.text_frame.paragraphs for r in p.runs if r.font.size}
            for sz in sizes:
                d["sizes"][sz] += 1
            if "▪" in t:
                has_marker = True
            # 러닝헤드: 우측 상단 작은 글씨
            if sh.left and PT(sh.left) > 8.5 and sh.top and PT(sh.top) < 1.2:
                d["runhead"] += 1
            # 타이틀 후보 = 그 덱에서 가장 큰 두 단
            d["titles"].append((max(sizes) if sizes else 0, t.strip().split("\n")[0]))
            # 마커 없는 본문 블록: 여러 줄인데 ▪ 가 없다
            if "▪" not in t and len(t.strip()) > 15 and "\n" in t.strip():
                has_plain = True
        d["marker"] += has_marker
        d["img_slides"] += has_img
        d["plain_body"] += has_plain
        d["words"].append(words)
        if s.has_notes_slide and s.notes_slide.notes_text_frame.text.strip():
            d["notes"] += 1
    return d


def ladder(d, top=7):
    return sorted(d["sizes"].items(), key=lambda x: -x[1])[:top]


def main():
    if len(sys.argv) < 3:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    gen, fix = Path(sys.argv[1]), Path(sys.argv[2])
    g, f = scan(gen), scan(fix)

    def row(label, a, b, note=""):
        print(f"  {label:<22} {str(a):>12} {str(b):>12}   {note}")

    print(f"\n생성본 {gen.name}  ↔  손질본 {fix.name}\n")
    print(f"  {'':<22} {'생성본':>12} {'손질본':>12}")
    print("  " + "-" * 52)
    row("장수", g["n"], f["n"])
    row("▪ 있는 장", g["marker"], f["marker"],
        "← 손질본이 훨씬 적으면 marker=False 가 필요하다" if f["marker"] < g["marker"] else "")
    row("마커 없는 본문 장", g["plain_body"], f["plain_body"])
    row("이미지 있는 장", g["img_slides"], f["img_slides"],
        "← 손질본이 많으면 자산이 안 붙어 나간 것" if f["img_slides"] > g["img_slides"] else "")
    row("이미지 총 개수", g["img"], f["img"])
    row("러닝헤드 흔적", g["runhead"], f["runhead"])
    row("노트 있는 장", g["notes"], f["notes"])
    gw = sorted(g["words"])[len(g["words"]) // 2] if g["words"] else 0
    fw = sorted(f["words"])[len(f["words"]) // 2] if f["words"] else 0
    row("장당 어절 중앙값", gw, fw,
        "← 손질본이 낮으면 밀도 상한을 낮춘다" if fw < gw else "")

    print("\n  폰트 사다리 (많이 쓰인 순)")
    print(f"    생성본  " + ", ".join(f"{k}pt×{v}" for k, v in ladder(g)))
    print(f"    손질본  " + ", ".join(f"{k}pt×{v}" for k, v in ladder(f)))
    only_fix = sorted(set(f["sizes"]) - set(g["sizes"]))
    if only_fix:
        print(f"    ⚠ 손질본에만 있는 크기: {', '.join(f'{x}pt' for x in only_fix)}")
        print("      → 생성기 사다리에 없는 단이다. 새 타입이 필요하거나 단을 잘못 골랐다.")
    shifted = [(k, g["sizes"][k], f["sizes"].get(k, 0)) for k in sorted(g["sizes"])
               if g["sizes"][k] >= 20 and f["sizes"].get(k, 0) * 3 < g["sizes"][k]]
    if shifted:
        print("    ⚠ 생성본에서 많이 쓰였는데 손질본에서 사라진 크기:")
        for k, a, b in shifted:
            print(f"        {k}pt  {a} → {b}   (이 단이 통째로 거부됐다)")

    print("\n  마스터/레이아웃")
    for tag, d in (("생성본", g), ("손질본", f)):
        print(f"    {tag}  " + ", ".join(f"{k}×{v}" for k, v in d["layouts"].items()))
    ext = set(f["layouts"]) - set(g["layouts"])
    if ext:
        print(f"    ⚠ 손질본에만 있는 레이아웃: {', '.join(ext)}")
        print("      → 외부 덱에서 가져온 장이다. _meta.unrenderable 로 선언할 대상.")

    print("\n  제목 형식 (손질본 상위 단)")
    top_sz = max(f["sizes"], default=0)
    # 타이틀 단은 「가장 큰 것 2개」가 아니다 — 간지(45.75)·statement(36)·본문 타이틀(30.75)이
    # 다 제목이다. 상한의 60% 이상을 전부 제목 단으로 본다.
    lvl = {s for s, _ in f["titles"] if s >= top_sz * 0.6}
    import re
    lab = [t for s, t in f["titles"] if s in lvl and re.match(r"^[^:)]{1,20}[:)]\s", t)]
    tot = [t for s, t in f["titles"] if s in lvl]
    if tot:
        print(f"    라벨+콜론 {len(lab)} / {len(tot)}")
        if lab:
            print("      예: " + " · ".join(lab[:4]))
        print("      → 라벨이 반복 슬롯 안쪽에만 나오면 슬롯 문법이지 제목 스타일이 아니다.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
