#!/usr/bin/env python3
"""화면 둘러보기(screen tour) 장표 생성기.

앱 화면 한 장을 찍고(또는 저장한 캡처를 받고), 장마다 한 곳에 빨간 박스와 말풍선을 얹은
PNG(tour-01.png ...)와 덱에 붙일 HTML 조각(tour.html)을 만든다.

실행:
  uv run --with playwright==1.56.0 python scripts/screentour.py examples/watch-party.json --out out/
  (--lang ko 로 한국어 문구. playwright 버전은 설치된 chromium 빌드에 맞춰 고정한다.)

입력 JSON (examples/watch-party.json 참고):
  url 또는 image      캡처할 주소 / 저장한 PNG(JSON 파일 기준 상대경로). 둘 다 있으면 image 우선.
  viewport            [너비, 높이]. 기본 [1500, 844]
  goto_timeout_ms     첫 요청 대기. Cloud Run 콜드스타트를 고려해 기본 120000
  pre                 캡처 전 단계(url일 때만). 각 항목은 아래 중 하나
                        {"click": 셀렉터, "optional": true}   없으면 건너뜀
                        {"wait_for": 셀렉터, "timeout_ms": 90000}   나타날 때까지
                        {"wait_ms": 숫자}
                        {"hide": 셀렉터}                     display:none
  wait_ms             pre 이후 마지막 대기
  copyright, foot_en, foot_ko, eyebrow_en, eyebrow_ko   덱 조각의 라벨과 푸터
  items[]             장 목록
    selector 또는 box   [x,y,w,h] (뷰포트 px). selector는 boundingBox를 박스로 바꾼다.
    text_box            true면 요소 전체 대신 글자가 차지한 영역만(긴 상태줄용)
    pad                 박스를 사방으로 넓힐 px (기본 6)
    title_en/ko         덱 슬라이드 제목
    caption_en/ko       말풍선 문구(없으면 제목)
    side                "l": 말풍선이 박스 오른쪽, 화살표가 왼쪽 / "r": 박스 왼쪽, 화살표가 오른쪽

selector를 못 찾으면 항목 번호와 제목을 적고 exit 1로 멈춘다.
"""
import argparse
import html
import json
import shutil
import sys
from pathlib import Path

from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

RED = "#FF2D2D"
INK = "#141830"      # 말풍선 기본색·본문 (DESIGN 토큰 계열, 덱 CSS와 동일)
SUB = "#4A5270"
DIM = "#7E86A0"
FONT = "Pretendard,'Apple SD Gothic Neo',Arial,sans-serif"

CSS = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
.tour-frame{{font-family:{FONT};color:{INK}}}
.tour-slide{{position:relative;width:1920px;height:1080px;padding:56px 140px 120px;background:#F6F7FB;overflow:hidden}}
.tour-eb{{display:inline-flex;font-size:24px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#2F52D0;padding:10px 20px;border:1px solid rgba(61,99,232,.35);border-radius:999px;background:rgba(61,99,232,.08)}}
.tour-head{{display:flex;align-items:center;gap:20px}}
.tour-head p{{font-size:34px;font-weight:800}}
.tour-foot{{position:absolute;left:140px;right:140px;bottom:56px;display:flex;justify-content:space-between;font-size:22px;color:{DIM}}}
.stage{{position:relative;width:__W__px;height:__H__px;overflow:hidden;border-radius:20px}}
.tour-slide .stage{{margin-top:24px}}
.stage img{{width:__W__px;height:__H__px;display:block;border-radius:20px}}
.grid{{position:absolute;inset:0;border-radius:20px;pointer-events:none;background-image:linear-gradient(rgba(255,255,255,.07) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.07) 1px,transparent 1px);background-size:60px 60px}}
.hl{{position:absolute;border:5px solid {RED};border-radius:10px;box-shadow:0 0 0 4000px rgba(10,14,28,.35)}}
.call{{position:absolute;background:{RED};color:#fff;font-size:30px;font-weight:700;line-height:1.3;padding:14px 22px;border-radius:14px;box-shadow:0 12px 30px rgba(20,24,48,.25);max-width:520px;word-break:keep-all}}
.call:before{{content:"";position:absolute;width:14px;height:14px;background:inherit;transform:rotate(45deg);top:22px}}
.call.l:before{{left:-7px}}.call.r:before{{right:-7px}}
"""


def fail(msg):
    print(f"screentour: {msg}", file=sys.stderr)
    sys.exit(1)


def stage_html(img_src, box, text, side, pos=None):
    x, y, w, h = box
    left, top = pos if pos else (0, 0)
    vis = "" if pos else "visibility:hidden;"
    return (
        f'<div class="stage"><img src="{html.escape(img_src)}" alt="">'
        f'<div class="grid"></div>'
        f'<div class="hl" style="left:{x-5}px;top:{y-5}px;width:{w}px;height:{h}px"></div>'
        f'<div class="call {side}" style="{vis}left:{left}px;top:{top}px">{html.escape(text)}</div></div>'
    )


def clamp(v, lo, hi):
    return max(lo, min(v, hi))


def place_callout(box, cw, ch, side, W, H):
    """말풍선 좌상단을 계산. 지정한 쪽에 안 들어가면 반대쪽, 그래도 안 되면 박스 위/아래."""
    x, y, w, h = box
    gap = 18
    cy = clamp(y + (h - ch) // 2, 12, H - ch - 12)
    right_of = (x + w + gap, cy)        # side "l" (화살표가 왼쪽)
    left_of = (x - gap - cw, cy)        # side "r"
    fits = lambda p: 8 <= p[0] and p[0] + cw <= W - 8
    order = [("l", right_of), ("r", left_of)] if side == "l" else [("r", left_of), ("l", right_of)]
    for s, p in order:
        if fits(p):
            return s, p
    above = (clamp(x, 12, W - cw - 12), y - ch - gap)
    below = (clamp(x, 12, W - cw - 12), y + h + gap)
    p = above if above[1] >= 8 else below
    return side, (p[0], clamp(p[1], 8, H - ch - 8))


def capture_page(pg, cfg, out, W, H):
    # 콜드스타트나 일시 끊김이 있어 세 번까지 다시 시도한다
    for attempt in range(3):
        try:
            pg.goto(cfg["url"], timeout=cfg.get("goto_timeout_ms", 120000))
            break
        except Exception as e:  # noqa: BLE001
            if attempt == 2:
                fail(f"접속 실패 ({cfg['url']}): {str(e).splitlines()[0]}. 행사 계정이 삭제됐으면 image 입력으로 돌린다.")
            pg.wait_for_timeout(5000)
    for i, step in enumerate(cfg.get("pre", [])):
        try:
            if "click" in step:
                try:
                    pg.wait_for_selector(step["click"], timeout=step.get("timeout_ms", 60000 if not step.get("optional") else 8000))
                except PWTimeout:
                    if step.get("optional"):
                        continue
                    raise
                pg.click(step["click"])
            elif "wait_for" in step:
                pg.wait_for_selector(step["wait_for"], timeout=step.get("timeout_ms", 90000))
            elif "wait_ms" in step:
                pg.wait_for_timeout(step["wait_ms"])
            elif "hide" in step:
                pg.add_style_tag(content=f'{step["hide"]}{{display:none !important}}')
            else:
                fail(f"pre[{i}]: 알 수 없는 단계 {step}")
        except PWTimeout:
            try:
                pg.screenshot(path=str(out / "_timeout.png"))
            except Exception:  # noqa: BLE001
                pass
            fail(f"pre[{i}] 시간 초과: {step} (그 순간 화면: {out / '_timeout.png'})")
    pg.wait_for_timeout(cfg.get("wait_ms", 1000))
    cap = out / "capture.png"
    pg.screenshot(path=str(cap))
    return cap


def resolve_boxes(pg, items, W, H):
    boxes = []
    for n, it in enumerate(items, 1):
        name = f"items[{n}] {it.get('title_en') or it.get('title_ko') or ''}".strip()
        pad = it.get("pad", 6)
        if "box" in it:
            x, y, w, h = it["box"]
        elif "selector" in it:
            if pg is None:
                fail(f"{name}: image 입력에서는 selector를 쓸 수 없다. box를 적는다.")
            sel = it["selector"]
            if it.get("text_box"):
                bb = pg.evaluate(
                    """s=>{const e=document.querySelector(s);if(!e)return null;
                    const r=document.createRange();r.selectNodeContents(e);const b=r.getBoundingClientRect();
                    return {x:b.x,y:b.y,width:b.width,height:b.height}}""", sel)
            else:
                loc = pg.locator(sel).first
                bb = loc.bounding_box() if loc.count() else None
            if not bb or bb["width"] == 0:
                fail(f"{name}: selector를 찾지 못했다 ({sel})")
            x, y, w, h = bb["x"], bb["y"], bb["width"], bb["height"]
        else:
            fail(f"{name}: selector 또는 box가 필요하다")
        x, y, w, h = round(x - pad), round(y - pad), round(w + 2 * pad), round(h + 2 * pad)
        x2, y2 = min(x + w, W), min(y + h, H)
        x, y = max(x, 0), max(y, 0)
        boxes.append([x, y, x2 - x, y2 - y])
    return boxes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--out", default="out")
    ap.add_argument("--lang", choices=["en", "ko"], default="en")
    a = ap.parse_args()

    cfg_path = Path(a.config).resolve()
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    out = out.resolve()
    W, H = cfg.get("viewport", [1500, 844])
    items = cfg.get("items", [])
    if not items:
        fail("items가 비었다")
    if not cfg.get("url") and not cfg.get("image"):
        fail("url 또는 image가 필요하다")
    L = a.lang
    css = CSS.replace("__W__", str(W)).replace("__H__", str(H))

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        if cfg.get("image"):
            src = (cfg_path.parent / cfg["image"]).resolve()
            if not src.exists():
                fail(f"image 파일이 없다: {src}")
            cap = out / "capture.png"
            if src != cap:
                shutil.copyfile(src, cap)
            live = None
        else:
            cap = capture_page(pg, cfg, out, W, H)
            live = pg
        boxes = resolve_boxes(live, items, W, H)

        # 렌더 페이지(말풍선 크기를 재고, 장마다 stage만 잘라 PNG로 저장)
        rp = b.new_page(viewport={"width": W + 40, "height": H + 40})
        fragments = []
        total = len(items)
        for n, (it, box) in enumerate(zip(items, boxes), 1):
            text = it.get(f"caption_{L}") or it.get(f"title_{L}") or ""
            title = it.get(f"title_{L}") or text
            side = it.get("side", "l")
            doc = lambda inner: f"<!doctype html><meta charset=utf-8><style>{css}body{{background:#fff}}</style><div class=tour-frame>{inner}</div>"
            # 이미지는 상대경로(capture.png)로 읽으므로 out/ 안에 임시 HTML 파일로 렌더한다
            page_file = out / f"_render-{n:02d}.html"
            page_file.write_text(doc(stage_html("capture.png", box, text, side)), encoding="utf-8")
            rp.goto(page_file.as_uri())
            cw, ch = rp.evaluate("()=>{const c=document.querySelector('.call');return [c.offsetWidth,c.offsetHeight]}")
            side2, pos = place_callout(box, cw, ch, side, W, H)
            inner = stage_html("capture.png", box, text, side2, pos)
            page_file.write_text(doc(inner), encoding="utf-8")
            rp.goto(page_file.as_uri())
            rp.wait_for_load_state("load")
            rp.locator(".stage").screenshot(path=str(out / f"tour-{n:02d}.png"))
            page_file.unlink()

            eb = cfg.get(f"eyebrow_{L}", "Screen tour" if L == "en" else "화면 둘러보기")
            foot = cfg.get(f"foot_{L}", "")
            frag_stage = stage_html("capture.png", box, text, side2, pos)
            fragments.append(
                f'<!-- tour {n}/{total} -->\n<div class="tour-frame"><section class="tour-slide">'
                f'<div class="tour-head"><span class="tour-eb">{html.escape(eb)} {n}/{total}</span><p>{html.escape(title)}</p></div>'
                f'{frag_stage}'
                f'<div class="tour-foot"><span>{html.escape(foot)}</span><span>{html.escape(cfg.get("copyright", ""))}</span></div>'
                f'</section></div>'
            )
        b.close()

    page = (f"<!doctype html><meta charset=utf-8><title>screen tour</title><style>{css}body{{background:#E9ECF5}}"
            f".tour-slide{{margin:24px auto}}</style>\n" + "\n".join(fragments) + "\n")
    (out / "tour.html").write_text(page, encoding="utf-8")
    files = sorted(x.name for x in out.iterdir())
    print("screentour: ok", ", ".join(files))
    for n, bx in enumerate(boxes, 1):
        print(f"  tour-{n:02d}: box={bx}")


if __name__ == "__main__":
    main()
