#!/usr/bin/env python3
"""강의·강연 덱 생성기 — 콘텐츠 JSON 1개에서 편집 가능한 .pptx 를 만든다.

JSON 최상위에 "slides" 배열을 두는 가변 길이 덱(강연·강의·컨설팅) 경로만 지원한다.

사용:
    python3 build_deck.py <content.json> [out.pptx] [--strict-assets]

왜 pptx인가: 사용자가 항상 직접 손을 대므로 산출물은 편집 가능한 네이티브
도형·텍스트여야 한다. HTML→PDF→이미지 슬라이드는 수정이 불가능해 쓰지 않는다.
"""
import json
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Pt

# ---------------------------------------------------------------- 테마 (색)
# 색은 이 파일이 갖지 않는다. themes/<이름>.json 이 갖고, 여기서는 이름으로 고른다.
#
# 고르는 순서 (먼저 잡히는 것이 이긴다)
#   1. 콘텐츠 json 의 "theme" 키          — 한 덱만 다른 테마로 뽑을 때
#   2. 위로 올라가며 만나는 design-system/theme.json — 프로젝트·강의 단위 기준
#   3. DEFAULT_THEME                      — 아무 지정도 없으면 종전 렌더 그대로
#
# 기본값이 blue-slate 인 것은 의도다. 지정하지 않은 프로젝트(강연 덱 포함)는
# 무채색 전환 이전과 똑같이 렌더돼야 한다.
DEFAULT_THEME = "blue-slate"
THEME_DIR = Path(__file__).resolve().parent.parent / "themes"

# 색 역할이 넷이다. 무채색 테마에서 강조는 색이 아니라 명도 + 채움 + 선 굵기로 만든다.
#   (a) 개선된 쪽      samples good, two_panel 우측, stages 마지막 노드 → tint 채움 + accent 테두리
#   (b) 잠긴 것/다른 것 layers 층, matrix 칸, bars 막대                 → accent 채움 + 굵은 선
#   (c) 실행됐다        timeline 찬 점 vs 빈 점                         → 채움 유무
#   (d) 크롬           구간 라벨·코스라인·서수·회귀 루프 선             → mark
_THEME = {}

def _rgb(hexstr):
    h = hexstr.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _find_project_theme(start_dir, limit=4):
    """콘텐츠 json 이 있는 곳에서 위로 올라가며 design-system/theme.json 을 찾는다.
    .git 을 만나거나 limit 단계를 넘으면 멈춘다 — 워크트리 밖 남의 프로젝트를 집어오면 안 된다."""
    d = Path(start_dir).resolve()
    for _ in range(limit + 1):
        cand = d / "design-system" / "theme.json"
        if cand.exists():
            return json.loads(cand.read_text(encoding="utf-8")).get("theme")
        if (d / ".git").exists() or d.parent == d:
            break
        d = d.parent
    return None


def load_theme(name):
    """테마 하나를 읽어 전역 색 상수에 바인딩한다."""
    global _THEME, TEXT, TEXT_SUB, BORDER, HAIRLINE, SHOT_BG
    global ACCENT, ACCENT_DARK, ACCENT_LIGHT, ACCENT_TINT, MARK, ORDINAL
    path = THEME_DIR / f"{name}.json"
    if not path.exists():
        avail = ", ".join(sorted(p.stem for p in THEME_DIR.glob("*.json")))
        sys.exit(f"테마 '{name}' 가 없다. {THEME_DIR} 에 있는 것: {avail}")
    _THEME = json.loads(path.read_text(encoding="utf-8"))
    c = _THEME["color"]
    TEXT         = _rgb(c["text"])         # 잉크
    TEXT_SUB     = _rgb(c["textSub"])      # 보조 본문
    BORDER       = _rgb(c["border"])       # 기본 테두리
    HAIRLINE     = _rgb(c["hairline"])     # 선·화살표·비활성 전용
    SHOT_BG      = _rgb(c["surface"])      # 중립 면 (빈 슬롯·대조군 카드)
    ACCENT       = _rgb(c["accent"])       # (a)(b) 강조 획·채움·섹션 라벨
    ACCENT_DARK  = _rgb(c["accentDark"])   # 강조 텍스트
    ACCENT_LIGHT = _rgb(c["accentLight"])
    ACCENT_TINT  = _rgb(c["tint"])         # (a) 강조 면
    MARK         = _rgb(c["mark"])         # (d) 크롬
    ORDINAL      = _rgb(c["ordinal"])      # (d) 정리 장 서수 전용 — mark 와 한 단 다르다
    return _THEME


WHITE = RGBColor(0xFF, 0xFF, 0xFF)
_DEFAULT = object()   # "기본 색" 자리표시. 실제 값은 호출 시점에 읽는다 — 아래 주석 참고
load_theme(DEFAULT_THEME)   # import 시점 기본값. build() 가 실제 테마로 다시 바인딩한다.

FONT = "Noto Sans KR"   # 2026-08-18 사용자 확정. 자간은 음수 금지
MONO = "JetBrains Mono"

# ---------------------------------------------------------------- 타이포 사다리 (SSOT)
# 계층 이름 → (크기 CSS px, 행간). 요소는 반드시 이 표의 이름으로만 크기·행간을 얻는다.
# 숫자 리터럴로 크기를 지정하는 코드를 새로 만들지 않는다. 단이 부족하면 크기를 새로 만들
# 것이 아니라 weight(400/700)와 색으로 구분한다. (2026-08-18 사용자 확정)
TYPE = {
    "display": (56, 1.28),  # 간지 타이틀 — 표지 제목, 실습 제목
    "title":   (36, 1.38),  # 장 타이틀 — 강의 목표, 전체 구조, Plan Build Sustain, 정리
    "heading": (20, 1.50),  # 소제목 — PBS 단계명, PBS 요약문
    "label":   (18, 1.40),  # 섹션 라벨 — 학습 목표/결과물/핵심 개념/산출물, 실습, 코스라인,
                            #             표지 회차, 노드 제목, 구간 밴드(PLAN/BUILD/SUSTAIN), 실습 산출물명
    "body":    (16, 1.60),  # 본문 — 불릿, Recap 문장, 노드 설명, 루프 라벨, INPUT/OUTPUT, 정리 산출물
    "caption": (14, 1.55),  # 캡션 — ▪태그, N분, 스크린샷 슬롯
    "chrome":  (12, 1.30),  # 크롬 — 카피라이트, 페이지 번호 (최소 12, 더 내리지 않는다)
}

# talk 덱 전용 사다리 (2026-08-31 사용자 확정).
# 참조 덱(claude-vod-slides v1.3 손질본) 실측을 1280x720 캔버스로 환산한 값이다.
# VOD 6장 고정 덱은 종전 값을 그대로 쓴다 — build_talk 만 이 표로 갈아탄다.
TALK_TYPE = {
    "display": (61, 1.28),
    "title":   (41, 1.26),
    "heading": (20, 1.50),   # 타이틀 바로 아래 줄글. 참조 덱 실측 150%
    "label":   (23, 1.38),
    "body":    (20, 1.50),
    "caption": (15, 1.48),
    "chrome":  (13, 1.30),
}


# 세미나룸·컨퍼런스장 변형. TALK_TYPE 과 body 단 **하나만** 다르다.
# 근거(2026-09-01 실측): 손질본 45장의 타이틀 30.75pt · 라벨 17.25pt · 캡션 11.25pt 는
# TALK_TYPE 환산값과 정확히 일치하고, 본문만 15pt → 20pt 로 올라가 있었다.
# 20pt = 26.667px (pt_of 가 0.75 를 곱한다). 라벨 단은 건드리지 않는다.
TALK_TYPE_ROOM = dict(TALK_TYPE, body=(26.667, 1.50))

# talk 덱 본문 불릿에 ▪ 를 찍을지. build_talk 가 _meta.body_marker 로 덮어쓴다.
MARKER_DEFAULT = True


def fs(tier):
    return TYPE[tier][0]

def lh(tier):
    return TYPE[tier][1]


# 캔버스는 HTML 덱과 같은 1280x720 px 기준으로 잡고 px 로만 계산한다.
CANVAS_W, CANVAS_H = 1280, 720
PAD_X, PAD_TOP, PAD_BOTTOM = 64, 52, 40
CONTENT_W = CANVAS_W - PAD_X * 2


def px(v):
    """CSS px → EMU. 96px = 1in."""
    return Emu(int(round(v * 914400 / 96)))


def pt_of(css_px):
    """CSS px → pt (1px = 0.75pt). HTML 덱과 시각적 크기를 맞춘다."""
    return Pt(css_px * 0.75)


# ---------------------------------------------------------------- 원시 요소
def flat(shape):
    """테마 기본 스타일(effectRef)이 붙는 그림자를 뺀다.
    shadow.inherit=False 만으로는 LibreOffice·PowerPoint 일부에서 그림자가 남는다."""
    sp = shape._element
    style = sp.find('{http://schemas.openxmlformats.org/presentationml/2006/main}style')
    if style is not None:
        sp.remove(style)
    shape.shadow.inherit = False
    return shape


def textbox(slide, x, y, w, h, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(px(x), px(y), px(w), px(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    tf.paragraphs[0].alignment = align
    return box, tf


def _lh_for_size(size):
    """크기로 사다리의 행간을 되찾는다. 사다리에 없는 크기는 중간값을 준다."""
    for _sz, _lh in TYPE.values():
        if abs(_sz - size) < 0.51:
            return _lh
    return 1.40


def run(par, text, size, *, bold=True, color=_DEFAULT, font=_DEFAULT, spacing=None):
    # 기본값을 인자 자리에 두면 import 시점 팔레트가 박제된다. 호출 시점에 읽는다.
    color = TEXT if color is _DEFAULT else color
    font = FONT if font is _DEFAULT else font
    # para() 를 거치지 않고 첫 문단에 바로 쓰는 자리(러닝헤드·푸터·라벨·캡션)가 많다.
    # 그대로 두면 행간이 파워포인트 기본 100% 로 렌더돼, 그 줄이 두 줄로 넘치는 순간 붙는다.
    # 명시가 없을 때만 사다리 값을 채운다 (2026-08-31 실측으로 25개 문단이 비어 있었다).
    if par.line_spacing is None:
        par.line_spacing = _lh_for_size(size)
    r = par.add_run()
    r.text = text
    r.font.size = pt_of(size)
    r.font.bold = bold
    r.font.color.rgb = color
    r.font.name = font
    if spacing is not None:
        r.font._rPr.set("spc", str(int(spacing * 100)))
    return r


def para(tf, first=False, line=None, space_after=0):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    if line:
        p.line_spacing = line
    p.space_after = Pt(space_after)
    return p


def hline(slide, x, y, w, color=_DEFAULT, weight=0.75):
    color = BORDER if color is _DEFAULT else color
    ln = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, px(x), px(y), px(w), Emu(0))
    ln.fill.background()
    ln.line.color.rgb = color
    ln.line.width = Pt(weight)
    flat(ln)
    return ln


def vline(slide, x, y, h, color=_DEFAULT, weight=0.75):
    color = BORDER if color is _DEFAULT else color
    ln = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, px(x), px(y), Emu(0), px(h))
    ln.fill.background()
    ln.line.color.rgb = color
    ln.line.width = Pt(weight)
    flat(ln)
    return ln

def bullets_height(items, w, *, tier="body", gap=9):
    """bullets() 가 실제로 먹는 높이. 레이아웃을 재는 쪽은 전부 이 함수를 쓴다.
    줄당 4px 은 Noto Sans KR 의 line gap 보정 — 계산값보다 렌더가 크다 (_theory_samples 와 같은 이유)."""
    step = round(fs(tier) * lh(tier)) + 4
    return sum(wrapped_lines(it if isinstance(it, str) else it[0], w, tier) * step + gap
               for it in items)


def bullets(slide, x, y, w, items, *, size=None, gap=9, line=None, tier="body",
            marker=True):
    size = size or fs("body")
    line = line or lh("body")
    """개조식 불릿. items 는 [(plain, bold_or_None), ...] 또는 문자열 리스트.

    marker=False 면 ▪ 를 찍지 않고 내어쓰기도 걸지 않는다 — 마커 없는 여러 줄
    본문 블록이 된다. 실측 근거: 손질된 발표 덱 다수에서 ▪ 가 살아남은 장보다
    마커 없는 본문 블록이 훨씬 많았다. 종전에는 이 형태를 낼 방법이
    없어 매번 파워포인트에서 손으로 지웠다."""
    box, tf = textbox(slide, x, y, w, bullets_height(items, w, tier=tier, gap=gap))
    for i, item in enumerate(items):
        p = para(tf, first=(i == 0), line=line, space_after=gap)
        if marker:
            # 내어쓰기. 두 줄로 넘치는 항목의 둘째 줄이 마커 자리로 파고들면
            # 목록이 아니라 문단으로 읽힌다 (2026-08-31 저자 소개 장에서 실측).
            hang = int(Pt(size * 1.15))
            pPr = p._p.get_or_add_pPr()
            pPr.set("marL", str(hang))
            pPr.set("indent", str(-hang))
            run(p, "▪  ", size, color=HAIRLINE)
        for seg, strong in normalize(item):
            run(p, seg, size, bold=strong, color=TEXT)
    return box


def normalize(item):
    """'앞 **강조** 뒤' 형식을 [(텍스트, 볼드여부)] 로 쪼갠다."""
    if isinstance(item, (list, tuple)):
        return item
    out, buf, strong = [], "", False
    for chunk in item.split("**"):
        if chunk:
            out.append((chunk, strong))
        strong = not strong
    return out or [(item, False)]



def footer(slide, page, copyright_text, total=6):
    # 크롬 최소 12px
    # 폴리오 표기는 "현재 / 전체" 고정 — 남은 분량이 보여야 한다.
    y = CANVAS_H - 54
    hline(slide, PAD_X, y, CONTENT_W)
    _, tf = textbox(slide, PAD_X, y + 13, CONTENT_W, 18, align=PP_ALIGN.CENTER)
    run(tf.paragraphs[0], copyright_text, fs("chrome"), bold=False, color=TEXT_SUB)
    _, tf2 = textbox(slide, PAD_X, y + 13, CONTENT_W, 18, align=PP_ALIGN.RIGHT)
    run(tf2.paragraphs[0], f"{page:02d} / {total:02d}", fs("chrome"), color=HAIRLINE)


def page_number(slide, page, total):
    """폴리오만. 구분선과 카피라이트가 마스터로 올라간 덱에서 쓴다."""
    y = CANVAS_H - 54
    _, tf = textbox(slide, PAD_X, y + 13, CONTENT_W, 18, align=PP_ALIGN.RIGHT)
    run(tf.paragraphs[0], f"{page:02d} / {total:02d}", fs("chrome"), color=HAIRLINE)


# 장수가 많은 발표 덱에서는 러닝헤드(아이브로우)가 필요하다. 지금 어느 순서인지
# 보여야 한다. runhead 를 넘기지 않으면 러닝헤드 없이 그려진다.
RUNHEAD_W = 320


def headline(slide, title_text, runhead=None):
    """장 타이틀 한 단. runhead 를 주면 우측 상단에 길잡이를 함께 둔다.
    반환값은 밑줄 아래 y."""
    y = PAD_TOP + 8
    title_h = round(fs("title") * lh("title")) + 6
    title_w = CONTENT_W - RUNHEAD_W if runhead else CONTENT_W
    box, tf = textbox(slide, PAD_X, y, title_w, title_h)
    p = para(tf, first=True, line=lh("title"))
    run(p, title_text, fs("title"), color=TEXT)
    if runhead:
        # 크롬 계층. 러닝헤드는 타이틀 상단선에 맞춰 오른쪽 끝에 둔다.
        _, tf2 = textbox(slide, PAD_X + CONTENT_W - RUNHEAD_W, y + 6,
                         RUNHEAD_W, 22, align=PP_ALIGN.RIGHT)
        run(tf2.paragraphs[0], runhead, fs("chrome"), bold=False, color=TEXT_SUB)
    bottom = y + title_h + 18
    hline(slide, PAD_X, bottom, CONTENT_W)
    return bottom


def col_label(slide, x, y, text, w=240):
    """열 라벨. 굵은 본문색 한 줄만 두고 밑줄도 자간도 쓰지 않는다.
    반환 y 는 라벨 높이 + 10 이다."""
    h = round(fs("label") * lh("label")) + 4
    _, tf = textbox(slide, x, y, w, h)
    run(tf.paragraphs[0], text, fs("label"), color=TEXT)
    return y + h + 10


# ---------------------------------------------------------------- 슬라이드
# 이번 빌드에서 파일을 못 찾아 placeholder 로 나간 shot_id 들.
# 조용히 비는 것을 금지한다 — 빌드가 소리를 내야 나중에 찾기 쉽다.
MISSING_SHOTS = []


def shot_slot(s, x, y, w, h, shot_id, shot_desc, base_dir=None):
    """스크린샷 자리. json 옆 assets/shots/<shot_id>.png 가 있으면 그 이미지를
    contain-fit 으로 넣고, 없으면 점선 placeholder 를 그린다.

    placeholder 로 떨어지면 MISSING_SHOTS 에 적는다. 사용자는 placeholder 장을
    채우기보다 통째로 지운다는 것이 실측이라, 빌드가 소리를 내야 한다."""
    if base_dir:
        img = Path(base_dir) / "assets" / "shots" / f"{shot_id}.png"
        if img.exists():
            from PIL import Image
            iw, ih = Image.open(img).size
            scale = min(w / iw, h / ih)
            dw, dh = iw * scale, ih * scale
            pic = s.shapes.add_picture(str(img), px(x + (w - dw) / 2), px(y + (h - dh) / 2),
                                       px(dw), px(dh))
            pic.line.color.rgb = BORDER
            pic.line.width = Pt(0.75)
            pic.shadow.inherit = False
            return pic
    MISSING_SHOTS.append(shot_id)
    slot = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, px(x), px(y), px(w), px(h))
    slot.adjustments[0] = 0.03
    slot.fill.solid()
    slot.fill.fore_color.rgb = SHOT_BG
    slot.line.color.rgb = HAIRLINE
    slot.line.width = Pt(1.2)
    slot.line.dash_style = 4  # dash
    flat(slot)
    tf = slot.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run(p, f"{shot_id}.png", fs("caption"), bold=False, color=TEXT_SUB, font=MONO)
    p2 = para(tf, line=lh("caption"), space_after=0)
    p2.alignment = PP_ALIGN.CENTER
    run(p2, shot_desc, fs("caption"), bold=False, color=TEXT_SUB)
    return slot

def _find_noto_font():
    """NotoSansKR-Regular 폰트 파일을 후보 경로에서 찾는다. 못 찾으면 None.
    wrapped_lines() 의 줄바꿈 폭 계산에만 쓰는 근사용 탐색이다 — 실제 렌더 폰트는
    FONT 전역(또는 콘텐츠 json 의 "font" 키)이 따로 정한다."""
    names = ("NotoSansKR-Regular.ttf", "NotoSansKR-Regular.otf")
    roots = [
        Path.home() / "Library" / "Fonts",
        Path("/Library") / "Fonts",
        Path("C:/Windows/Fonts"),
    ]
    for root in roots:
        if not root.exists():
            continue
        for name in names:
            cand = root / name
            if cand.exists():
                return cand
    fonts_dir = Path("/usr/share/fonts")
    if fonts_dir.exists():
        for name in names:
            hit = next(fonts_dir.rglob(name), None)
            if hit:
                return hit
    return None


def wrapped_lines(text, box_w=CONTENT_W, tier="body"):
    """text 가 box_w 안에서 몇 줄로 감기는지 센다.

    한장 이론의 lead·takeaway 아래 간격을 한 줄 분량으로 고정해 두었더니, 문장이
    두 줄이 되는 순간 아래 요소를 파고들었다. 줄 수를 세어 간격을 밀어 준다.
    PIL 이 없거나 폰트 파일을 못 찾으면 글자 수 × 폰트 크기 × 0.95 근사로 폴백한다."""
    if not text:
        return 0
    size = fs(tier)
    width_of = None
    font_path = _find_noto_font()
    if font_path is not None:
        try:
            from PIL import ImageFont
            font = ImageFont.truetype(str(font_path), size)
            width_of = font.getlength
        except Exception:
            width_of = None
    if width_of is None:
        width_of = lambda s: len(s) * size * 0.95
    n, cur = 1, ""
    for word in text.replace("**", "").split(" "):
        trial = word if not cur else cur + " " + word
        if width_of(trial) <= box_w:
            cur = trial
        else:
            n += 1
            cur = word
    return n

def _fig_box(s, x, y, w, h, title, points=None, *, accent=False, tint=False,
             title_tier="label", center=False):
    box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, px(x), px(y), px(max(8, w)), px(max(8, h)))
    box.adjustments[0] = 0.06
    if tint:
        box.fill.solid()
        box.fill.fore_color.rgb = ACCENT_TINT
    else:
        box.fill.background()
    box.line.color.rgb = ACCENT if accent else BORDER
    box.line.width = Pt(1.2 if accent else 1.0)
    flat(box)
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = px(12)
    tf.margin_top = tf.margin_bottom = px(9)
    tf.vertical_anchor = MSO_ANCHOR.TOP if points else MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER if center else PP_ALIGN.LEFT
    p.space_after = Pt(6 if points else 0)
    run(p, title, fs(title_tier), color=ACCENT_DARK if accent else TEXT)
    for t in (points or []):
        p2 = para(tf, line=lh("caption"), space_after=3)
        p2.alignment = PP_ALIGN.CENTER if center else PP_ALIGN.LEFT
        run(p2, "▪  ", fs("caption"), bold=False, color=HAIRLINE)
        run(p2, t, fs("caption"), bold=False, color=TEXT)
    return box


def _fig_arrow_down(s, cx, y, h, *, accent=False):
    col = ACCENT if accent else HAIRLINE
    vline(s, cx, y, max(4, h - 8), color=col, weight=1.2)
    tri = s.shapes.add_shape(MSO_SHAPE.ISOSCELES_TRIANGLE, px(cx - 5), px(y + h - 9), px(10), px(9))
    tri.rotation = 180
    tri.fill.solid(); tri.fill.fore_color.rgb = col; tri.line.fill.background(); flat(tri)


def _fig_arrow_right(s, x, cy, w, *, accent=False):
    col = ACCENT if accent else HAIRLINE
    arr = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, px(x), px(cy - 6), px(max(12, w)), px(12))
    arr.fill.solid(); arr.fill.fore_color.rgb = col; arr.line.fill.background(); flat(arr)


def _fig_connect(s, x1, y1, x2, y2, *, accent=False, dashed=False):
    """ㄱ자 연결선. 허브에서 갈래로 뻗을 때 쓴다."""
    col = ACCENT if accent else HAIRLINE
    mid = x1 + (x2 - x1) * 0.45
    for shp in (hline(s, x1, y1, mid - x1, color=col, weight=1.0),
                vline(s, mid, min(y1, y2), abs(y2 - y1), color=col, weight=1.0),
                hline(s, mid, y2, x2 - mid, color=col, weight=1.0)):
        if dashed:
            shp.line.dash_style = 4


def _alpha_fill(shape, color, pct):
    """반투명 채움. 겹치는 원의 교집합이 저절로 진해진다 ﹣ 무채색에서 겹침을
    나르는 수단이 명도뿐이라 벤다이어그램에는 이게 필요하다."""
    from pptx.oxml.ns import qn
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    sf = shape._element.spPr.find(qn("a:solidFill"))
    clr = sf.find(qn("a:srgbClr"))
    clr.append(clr.makeelement(qn("a:alpha"), {"val": str(int(pct * 1000))}))
    return shape


def _fig_note(s, x, y, w, text):
    if not text:
        return y
    _, tf = textbox(s, x, y + 8, w, 22)
    run(para(tf, first=True, line=lh("caption")), text, fs("caption"), bold=False, color=TEXT_SUB)
    return y + 8 + round(fs("caption") * lh("caption")) * wrapped_lines(text, w, "caption")


def _note_h(spec):
    return 32 if spec.get("note") else 0


# ---------------------------------------------------------------- 프리셋 14종

def _fig_two_panel(s, spec, rect):
    """좌우가 서로 다른 흐름으로 돈다. arrows=False 면 순서 없는 항목 나열."""
    X, Y, W, H = rect
    gap = max(32, W * 0.05)
    col_w = (W - gap) / 2
    sides = (spec["left"], spec["right"])
    n = max(len(sd["nodes"]) for sd in sides)
    nh = _note_h(spec)
    body = H - 46 - nh                          # 46 = col_label 이 실제로 먹는 높이
    arrows = spec.get("arrows", True)
    arrow_h = min(30, max(16, body * 0.10)) if arrows else 14
    box_h = max(40, (body - arrow_h * (n - 1)) / n)
    # 박스가 눌리면 제목과 불릿이 아래 박스를 파고든다. 조용히 겹치므로 여기서 잡는다
    # (2026-08-24 실사고: stack 배치에 얹었더니 3단 박스가 54px 로 눌렸다).
    need = 34 + max(len(nd.get("points") or []) if isinstance(nd, dict) else 0
                    for sd in sides for nd in sd["nodes"]) * (round(fs("caption") * lh("caption")) + 3)
    if box_h < need:
        print(f"  ! two_panel 박스 {int(box_h)}px < 필요 {int(need)}px — 글이 아래 박스를 파고든다. "
              f"layout 을 split 이나 full 로 바꾸거나 노드를 줄여야 한다", file=sys.stderr)
    for i, sd in enumerate(sides):
        x = X + (col_w + gap) * i
        accent = (i == 1)
        yy = col_label(s, x, Y, sd["label"], w=col_w)
        for j, node in enumerate(sd["nodes"]):
            title, pts = (node, None) if isinstance(node, str) else (node["title"], node.get("points"))
            _fig_box(s, x, yy, col_w, box_h, title, pts,
                     accent=accent, tint=accent and j == len(sd["nodes"]) - 1)
            yy += box_h
            if j < len(sd["nodes"]) - 1:
                if arrows:
                    _fig_arrow_down(s, x + col_w / 2, yy, arrow_h, accent=accent)
                yy += arrow_h
    vline(s, X + col_w + gap / 2, Y + 6, H - nh - 12)
    return _fig_note(s, X, Y + H - nh, W, spec.get("note"))


def _fig_layers(s, spec, rect):
    """층마다 성질이 다른 개념. 아래로 갈수록 안쪽. inset=0 이면 평평한 스택."""
    X, Y, W, H = rect
    layers = spec["layers"]
    nh = _note_h(spec)
    body = H - nh
    gap = 10
    h = max(40, (body - gap * (len(layers) - 1)) / len(layers))
    inset = spec.get("inset", 20)
    yy = Y
    for i, lay in enumerate(layers):
        acc = bool(lay.get("accent"))
        pad = inset * i
        box = _fig_box(s, X + pad, yy, W - pad * 2, h, lay["label"], accent=acc, tint=acc)
        if lay.get("note"):
            p = box.text_frame.paragraphs[0]
            run(p, "      ", fs("caption"), bold=False)
            run(p, lay["note"], fs("caption"), bold=False, color=ACCENT_DARK if acc else TEXT_SUB)
        yy += h + gap
    return _fig_note(s, X, Y + body, W, spec.get("note"))


def _fig_timeline(s, spec, rect):
    """같은 시점들에 무엇이 실행되고 무엇이 빠지나. 찬 점이 반드시 실행."""
    X, Y, W, H = rect
    marks, rows = spec["marks"], spec["rows"]
    nh = _note_h(spec)
    body = H - nh
    lab_w = min(150, W * 0.18)
    track_x, track_w = X + lab_w, W - lab_w
    stepx = track_w / (len(marks) + 1)
    for i, m in enumerate(marks):
        cx = track_x + stepx * (i + 1)
        _, tf = textbox(s, cx - stepx / 2, Y, stepx, 20, align=PP_ALIGN.CENTER)
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        run(tf.paragraphs[0], m, fs("caption"), bold=False, color=TEXT_SUB)
    y2 = Y + 28
    row_h = min(96, max(44, (body - 28) / len(rows)))
    for r, rw in enumerate(rows):
        cy = y2 + row_h * r + row_h / 2
        acc = bool(rw.get("accent"))
        _, tf = textbox(s, X, cy - 12, lab_w - 14, 24)
        run(tf.paragraphs[0], rw["label"], fs("label"), color=ACCENT_DARK if acc else TEXT)
        hline(s, track_x, cy, track_w, color=ACCENT if acc else BORDER, weight=1.2 if acc else 0.75)
        for i, hit in enumerate(rw["hits"]):
            cx = track_x + stepx * (i + 1)
            dot = s.shapes.add_shape(MSO_SHAPE.OVAL, px(cx - 8), px(cy - 8), px(16), px(16))
            dot.fill.solid()
            dot.fill.fore_color.rgb = (ACCENT if acc else HAIRLINE) if hit else WHITE
            dot.line.color.rgb = ACCENT if acc else HAIRLINE
            dot.line.width = Pt(1.2); flat(dot)
    return _fig_note(s, X, Y + body, W, spec.get("note"))


def _fig_stages(s, spec, rect):
    """좌에서 우로 흐르는 단계. taper 로 좁아지면 깔때기, loop 을 주면 회귀 점선."""
    X, Y, W, H = rect
    stages = spec["stages"]
    nh = _note_h(spec)
    loop_h = 50 if spec.get("loop") else 0
    body = H - nh - loop_h
    n = len(stages)
    gap = max(26, W * 0.035)
    w = (W - gap * (n - 1)) / n
    taper = spec.get("taper")
    need = 60 + max(len(st.get("points") or []) for st in stages) * (round(fs("caption") * lh("caption")) + 7)
    h_full = max(64, min(body, max(need, body * 0.78) if taper else need))
    xs = []
    for i, st in enumerate(stages):
        x = X + (w + gap) * i
        xs.append(x)
        h = h_full * (1 - 0.45 * i / max(1, n - 1)) if taper else h_full
        acc = bool(st.get("accent")) or (taper and i == n - 1)
        _fig_box(s, x, Y + (h_full - h) / 2, w, h, st["title"], st.get("points"), accent=acc, tint=acc)
        if i < n - 1:
            _fig_arrow_right(s, x + w + 8, Y + h_full / 2, gap - 16)
    if spec.get("loop"):
        ly = Y + h_full + 24
        fx, lx = xs[0] + w / 2, xs[-1] + w / 2
        for shp in (vline(s, lx, Y + h_full, ly - (Y + h_full), color=ACCENT, weight=1.2),
                    hline(s, fx, ly, lx - fx, color=ACCENT, weight=1.2),
                    vline(s, fx, Y + h_full + 8, ly - (Y + h_full) - 8, color=ACCENT, weight=1.2)):
            shp.line.dash_style = 4
        up = s.shapes.add_shape(MSO_SHAPE.ISOSCELES_TRIANGLE, px(fx - 6), px(Y + h_full), px(12), px(10))
        up.fill.solid(); up.fill.fore_color.rgb = ACCENT; up.line.fill.background(); flat(up)
        lbl_w = min(W, max(200, len(spec["loop"]) * 15 + 44))
        lb = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                px(X + W / 2 - lbl_w / 2), px(ly - 14), px(lbl_w), px(28))
        lb.adjustments[0] = 0.5
        lb.fill.solid(); lb.fill.fore_color.rgb = WHITE; lb.line.fill.background(); flat(lb)
        lb.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        lp = lb.text_frame.paragraphs[0]; lp.alignment = PP_ALIGN.CENTER
        run(lp, spec["loop"], fs("body"), color=ACCENT_DARK)
    return _fig_note(s, X, Y + body + loop_h, W, spec.get("note"))


def _fig_placemap(s, spec, rect):
    """한 화면 안에서 무엇이 어디 놓이나. 프레임이 곧 은유다."""
    X, Y, W, H = rect
    nh = _note_h(spec)
    body = H - nh
    lab_h = (int(fs("caption") * lh("caption")) + 6) if spec.get("frame_label") else 0
    if lab_h:
        _, tf = textbox(s, X, Y, W, lab_h - 4)
        run(tf.paragraphs[0], spec["frame_label"], fs("caption"), bold=False, color=HAIRLINE)
    fy = Y + lab_h
    frame_h = body - lab_h
    frame = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, px(X), px(fy), px(W), px(frame_h))
    frame.adjustments[0] = 0.03
    frame.fill.solid(); frame.fill.fore_color.rgb = SHOT_BG
    frame.line.color.rgb = BORDER; frame.line.width = Pt(1.0); flat(frame)
    pad = 14
    for a in spec["areas"]:
        _fig_box(s, X + pad + W * a["x"], fy + pad, W * a["w"] - pad * 2, frame_h - pad * 2,
                 a["label"], a.get("points"), accent=bool(a.get("accent")), tint=bool(a.get("accent")))
    return _fig_note(s, X, Y + body, W, spec.get("note"))


def _fig_cards(s, spec, rect):
    """동등한 항목 N개. 어느 하나가 앞서지 않는 나열 (4개 제품 지도 같은 것).
    5개를 넘으면 두 줄로 접는다."""
    X, Y, W, H = rect
    items = spec["cards"]
    nh = _note_h(spec)
    body = H - nh
    per = spec.get("per_row") or (len(items) if len(items) <= 4 else (len(items) + 1) // 2)
    rows = (len(items) + per - 1) // per
    gapx = max(18, W * 0.025)
    gapy = 16
    w = (W - gapx * (per - 1)) / per
    h = max(56, (body - gapy * (rows - 1)) / rows)
    for i, it in enumerate(items):
        r, c = divmod(i, per)
        _fig_box(s, X + (w + gapx) * c, Y + (h + gapy) * r, w, h,
                 it["title"], it.get("points"), accent=bool(it.get("accent")), tint=bool(it.get("accent")))
    return _fig_note(s, X, Y + body, W, spec.get("note"))


def _fig_hub(s, spec, rect):
    """중심 하나가 여러 곳에 걸린다. 지침이 모든 대화에, 기준 파일이 모든 산출물에."""
    X, Y, W, H = rect
    spokes = spec["spokes"]
    nh = _note_h(spec)
    body = H - nh
    hub_w = W * 0.32
    sp_x = X + hub_w + max(48, W * 0.07)
    sp_w = X + W - sp_x
    gap = 14
    sh = max(44, (body - gap * (len(spokes) - 1)) / len(spokes))
    hub_h = min(body, max(80, body * 0.5))
    hub_cy = Y + body / 2
    _fig_box(s, X, hub_cy - hub_h / 2, hub_w, hub_h, spec["hub"]["title"],
             spec["hub"].get("points"), accent=True, tint=True)
    for i, sp in enumerate(spokes):
        yy = Y + (sh + gap) * i
        title, pts = (sp, None) if isinstance(sp, str) else (sp["title"], sp.get("points"))
        _fig_connect(s, X + hub_w, hub_cy, sp_x, yy + sh / 2, accent=True, dashed=True)
        _fig_box(s, sp_x, yy, sp_w, sh, title, pts)
    return _fig_note(s, X, Y + body, W, spec.get("note"))


def _fig_branch(s, spec, rect):
    """조건 하나로 길이 갈린다. 폴백 규칙이나 판정 분기를 그릴 때."""
    X, Y, W, H = rect
    nh = _note_h(spec)
    body = H - nh
    cond_w = W * 0.3
    br_x = X + cond_w + max(56, W * 0.08)
    br_w = X + W - br_x
    branches = spec["branches"][:3]
    gap = 18
    bh = max(50, (body - gap * (len(branches) - 1)) / len(branches))
    cy = Y + body / 2
    ch = min(body, max(72, body * 0.42))
    _fig_box(s, X, cy - ch / 2, cond_w, ch, spec["condition"], spec.get("condition_points"), center=False)
    for i, br in enumerate(branches):
        yy = Y + (bh + gap) * i
        acc = bool(br.get("accent"))
        _fig_connect(s, X + cond_w, cy, br_x, yy + bh / 2, accent=acc)
        if br.get("edge"):
            _, tf = textbox(s, X + cond_w + 6, yy + bh / 2 - 26, br_x - X - cond_w - 6, 20)
            run(tf.paragraphs[0], br["edge"], fs("caption"), bold=False,
                color=ACCENT_DARK if acc else TEXT_SUB)
        _fig_box(s, br_x, yy, br_w, bh, br["title"], br.get("points"), accent=acc, tint=acc)
    return _fig_note(s, X, Y + body, W, spec.get("note"))


def _fig_nested(s, spec, rect):
    """포함 관계. 바깥에서 안으로 좁혀 들어간다 (프로젝트 안에 대화, 세션 안에 기록)."""
    X, Y, W, H = rect
    rings = spec["rings"]
    nh = _note_h(spec)
    body = H - nh
    n = len(rings)
    stepx = (W * 0.30) / max(1, n - 1) if n > 1 else 0
    stepy = (body * 0.30) / max(1, n - 1) if n > 1 else 0
    # 바깥 링의 라벨과 캡션이 안쪽 링 위에 올라타지 않게 최소 간격을 둔다.
    ring_head = 10 + int(fs("label") * lh("label")) + 2 + (20 if any(r.get("note") for r in rings) else 0) + 8
    if n > 1:
        stepy = max(stepy, min(ring_head, (body - 80) / (2 * (n - 1))))
    for i, ring in enumerate(rings):
        acc = bool(ring.get("accent")) or i == n - 1
        x, y = X + stepx * i, Y + stepy * i
        w, h = W - stepx * 2 * i, body - stepy * 2 * i
        box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, px(x), px(y), px(w), px(h))
        box.adjustments[0] = 0.05
        box.fill.solid()
        box.fill.fore_color.rgb = ACCENT_TINT if acc else (SHOT_BG if i == 0 else WHITE)
        box.line.color.rgb = ACCENT if acc else BORDER
        box.line.width = Pt(1.2 if acc else 1.0); flat(box)
        label_h = int(fs("label") * lh("label")) + 2
        _, tf = textbox(s, x + 14, y + 10, w - 28, label_h)
        run(tf.paragraphs[0], ring["label"], fs("label"), color=ACCENT_DARK if acc else TEXT)
        if ring.get("note"):
            _, tf = textbox(s, x + 14, y + 10 + label_h, w - 28, 20)
            run(tf.paragraphs[0], ring["note"], fs("caption"), bold=False, color=TEXT_SUB)
    return _fig_note(s, X, Y + body, W, spec.get("note"))


def _fig_matrix(s, spec, rect):
    """2x2 사분면. 판단 축이 두 개일 때. 강조 칸 하나만 accent."""
    X, Y, W, H = rect
    nh = _note_h(spec)
    body = H - nh
    # 축 라벨 자리는 글자 크기에 따라간다. 고정값이면 사다리를 올렸을 때 라벨이 칸을 덮는다.
    ax_w = round(fs("label") * lh("label")) + 22  # 세로축 라벨 폭 (세로쓰기)
    ax_h = round(fs("label") * lh("label")) + 8  # 가로축 라벨 높이
    gx, gy = X + ax_w, Y + ax_h
    gw, gh = W - ax_w, body - ax_h
    gap = 12
    cw, chh = (gw - gap) / 2, (gh - gap) / 2
    cols, rowsl = spec["cols"], spec["rows"]
    for c in range(2):
        _, tf = textbox(s, gx + (cw + gap) * c, Y, cw, ax_h - 6, align=PP_ALIGN.CENTER)
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        run(tf.paragraphs[0], cols[c], fs("label"), color=TEXT_SUB)
    for r in range(2):
        # 세로축은 세로로 세운다 (2026-08-31 사용자 확정). 가로로 두면 긴 라벨이
        # 여러 줄로 접혀 축 폭을 잡아먹고, 칸과 라벨의 관계도 흐려진다.
        _, tf = textbox(s, X, gy + (chh + gap) * r, ax_w - 16, chh,
                        align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        tf._bodyPr.set("vert", "eaVert")
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        run(tf.paragraphs[0], rowsl[r], fs("label"), color=TEXT_SUB)
    for i, cell in enumerate(spec["cells"][:4]):
        r, c = divmod(i, 2)
        acc = bool(cell.get("accent"))
        _fig_box(s, gx + (cw + gap) * c, gy + (chh + gap) * r, cw, chh,
                 cell["title"], cell.get("points"), accent=acc, tint=acc)
    return _fig_note(s, X, Y + body, W, spec.get("note"))


def _fig_bars(s, spec, rect):
    """수치 비교 막대. 숫자는 출처가 있는 것만 쓴다 (facts-and-claims)."""
    X, Y, W, H = rect
    bars = spec["bars"]
    nh = _note_h(spec)
    body = H - nh
    lab_w = min(220, W * 0.26)
    val_w = 110
    track_x = X + lab_w
    track_w = W - lab_w - val_w
    top = max(v["value"] for v in bars) or 1
    gap = 14
    bh = min(56, max(26, (body - gap * (len(bars) - 1)) / len(bars)))
    for i, b in enumerate(bars):
        yy = Y + (bh + gap) * i
        acc = bool(b.get("accent"))
        _, tf = textbox(s, X, yy + bh / 2 - 12, lab_w - 14, 24)
        run(tf.paragraphs[0], b["label"], fs("body"), color=ACCENT_DARK if acc else TEXT)
        bw = max(6, track_w * b["value"] / top)
        bar = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, px(track_x), px(yy + 4), px(bw), px(bh - 8))
        bar.adjustments[0] = 0.18
        bar.fill.solid(); bar.fill.fore_color.rgb = ACCENT if acc else BORDER
        bar.line.fill.background(); flat(bar)
        _, tf = textbox(s, track_x + bw + 12, yy + bh / 2 - 12, val_w, 24)
        run(tf.paragraphs[0], b.get("display") or str(b["value"]), fs("body"),
            color=ACCENT_DARK if acc else TEXT_SUB)
    return _fig_note(s, X, Y + body, W, spec.get("note"))


def _fig_area(s, spec, rect):
    """누적 영역. 구성비·누적이 시간으로 변할 때 (bars·timeline 으로 안 되는 정량 추세).
    시리즈는 아래→위로 쌓고 초점 시리즈를 맨 아래 둔다 ﹣ 밑변이 직선인 밴드만
    크기를 바로 읽을 수 있다. y 는 0 에서 시작한다 (면적이 곧 크기 주장).
    범례 대신 밴드 끝에 제자리 라벨을 붙인다. 숫자는 출처 있는 것만 (facts-and-claims)."""
    X, Y, W, H = rect
    series = spec["series"][:3]
    if len(spec["series"]) > 3:
        print("  ! area 누적 시리즈는 3개까지다 — 넘치는 시리즈는 버린다. 나머지는 '기타'로 접는다",
              file=sys.stderr)
    xl = spec["x_labels"]
    n = len(xl)
    nh = _note_h(spec)
    body = H - nh
    lab_w = 150                                  # 우측 제자리 라벨 열
    ax_h = 30                                    # x 라벨 줄
    pw, ph = W - lab_w, body - ax_h
    top = (spec.get("y_max") or
           max(sum(sr["values"][i] for sr in series) for i in range(n))) * 1.06 or 1
    xs = [X + pw * i / (n - 1) for i in range(n)]

    def ypos(v):
        return Y + ph - ph * v / top

    for frac in (1 / 3, 2 / 3):                  # 숫자 없는 격자 2줄 + 기준선
        hline(s, X, Y + ph * frac, pw, color=HAIRLINE, weight=0.75)
    hline(s, X, Y + ph, pw, color=BORDER, weight=1.0)

    cum = [0.0] * n
    prev_y = [Y + ph] * n
    labels = []
    for sr in series:
        acc = bool(sr.get("accent"))
        cum = [c + v for c, v in zip(cum, sr["values"])]
        ys = [ypos(c) for c in cum]
        pts = list(zip(xs, ys)) + list(zip(reversed(xs), reversed(prev_y)))
        fb = s.shapes.build_freeform(pts[0][0], pts[0][1], scale=9525)
        fb.add_line_segments(pts[1:], close=True)
        band = fb.convert_to_shape()
        _alpha_fill(band, ACCENT if acc else HAIRLINE, 26 if acc else 16)
        band.line.fill.background(); flat(band)
        fb = s.shapes.build_freeform(xs[0], ys[0], scale=9525)   # 위 경계선만 따로 긋는다
        fb.add_line_segments(list(zip(xs, ys))[1:], close=False)
        edge = fb.convert_to_shape()
        edge.fill.background()
        edge.line.color.rgb = ACCENT if acc else HAIRLINE
        edge.line.width = Pt(1.6 if acc else 1.0); flat(edge)
        labels.append(((ys[-1] + prev_y[-1]) / 2, sr, acc))
        prev_y = ys

    # 제자리 라벨 ﹣ 얇은 밴드끼리 겹치지 않게 위에서부터 최소 간격을 벌린다
    lab_h, sep = 44, 50
    labels.sort(key=lambda t: t[0])              # 위(작은 y)부터
    adj = []
    for cy, sr, acc in labels:
        if adj and cy - adj[-1][0] < sep:
            cy = adj[-1][0] + sep
        adj.append([cy, sr, acc])
    over = adj[-1][0] - (Y + ph - lab_h / 2)
    if over > 0:                                 # 바닥을 넘으면 전체를 위로 민다
        for t in adj:
            t[0] -= over
    for cy, sr, acc in adj:
        _, tf = textbox(s, X + pw + 10, cy - lab_h / 2, lab_w - 10, lab_h)
        run(tf.paragraphs[0], sr["label"], fs("label"), color=ACCENT_DARK if acc else TEXT)
        if sr.get("display"):
            run(para(tf, line=lh("caption")), sr["display"], fs("caption"), bold=False, color=TEXT_SUB)

    idxs = (0, n // 2, n - 1) if n > 4 else range(n)   # x 라벨은 처음·중간·끝만
    for i in idxs:
        _, tf = textbox(s, max(X, xs[i] - 60), Y + ph + 6, 120, 22)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT if i == 0 else (PP_ALIGN.RIGHT if i == n - 1 else PP_ALIGN.CENTER)
        run(p, xl[i], fs("caption"), bold=False, color=TEXT_SUB)
    return _fig_note(s, X, Y + body, W, spec.get("note"))


def _fig_kpi(s, spec, rect):
    """핵심 지표 카드 줄. cards 의 정량판 ﹣ 큰 숫자 + 델타 + 비교 기준.
    방향은 색이 아니라 ▲▼ 글리프가 나른다 (무채색 원칙). 카드 3장까지,
    초점 카드 하나만 accent. 델타에는 비교 기준을 반드시 붙인다.
    보조 시각물(spark/progress)은 줄에 1~2개만. 숫자는 출처 있는 것만."""
    X, Y, W, H = rect
    cards = spec["cards"]
    if len(cards) > 3:
        print("  ! kpi 카드는 슬라이드에서 3장까지다 — 넘치는 카드는 버린다. 5개 이상이면 표로 내린다",
              file=sys.stderr)
        cards = cards[:3]
    nh = _note_h(spec)
    body = H - nh
    gap = 24
    cw = (W - gap * (len(cards) - 1)) / len(cards)
    ch = min(body, 260)
    yc = Y + (body - ch) / 2
    pad = 20
    for i, c in enumerate(cards):
        acc = bool(c.get("accent"))
        x = X + (cw + gap) * i
        box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, px(x), px(yc), px(cw), px(ch))
        box.adjustments[0] = 0.05
        if acc:
            box.fill.solid(); box.fill.fore_color.rgb = ACCENT_TINT
        else:
            box.fill.background()
        box.line.color.rgb = ACCENT if acc else BORDER
        box.line.width = Pt(1.2 if acc else 1.0); flat(box)
        _, tf = textbox(s, x + pad, yc + pad, cw - pad * 2, 26)
        run(tf.paragraphs[0], c["label"], fs("label"), color=TEXT_SUB)
        _, tf = textbox(s, x + pad, yc + pad + 36, cw - pad * 2, 56)
        p = tf.paragraphs[0]
        run(p, str(c["value"]), fs("title"), color=ACCENT_DARK if acc else TEXT)
        if c.get("unit"):
            run(p, "  " + c["unit"], fs("body"), bold=False, color=TEXT_SUB)
        if c.get("delta"):
            _, tf = textbox(s, x + pad, yc + pad + 104, cw - pad * 2, 24)
            p = tf.paragraphs[0]
            run(p, c["delta"], fs("body"), color=ACCENT_DARK if acc else TEXT)
            if c.get("basis"):
                run(p, "  " + c["basis"], fs("body"), bold=False, color=TEXT_SUB)
        vy = yc + ch - pad - 34
        if c.get("progress") is not None:
            track = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, px(x + pad), px(vy + 14), px(cw - pad * 2), px(10))
            track.fill.solid(); track.fill.fore_color.rgb = SHOT_BG
            track.line.fill.background(); flat(track)
            fw = max(10, (cw - pad * 2) * max(0.0, min(1.0, float(c["progress"]))))
            bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, px(x + pad), px(vy + 14), px(fw), px(10))
            bar.fill.solid(); bar.fill.fore_color.rgb = ACCENT if acc else BORDER
            bar.line.fill.background(); flat(bar)
        elif c.get("spark"):
            vals = [float(v) for v in c["spark"]]
            span = (max(vals) - min(vals)) or 1
            sw, sh_ = cw - pad * 2, 30
            pts = [(x + pad + sw * j / (len(vals) - 1),
                    vy + sh_ - sh_ * (v - min(vals)) / span) for j, v in enumerate(vals)]
            fb = s.shapes.build_freeform(pts[0][0], pts[0][1], scale=9525)
            fb.add_line_segments(pts[1:], close=False)
            sp = fb.convert_to_shape()
            sp.fill.background()
            sp.line.color.rgb = ACCENT if acc else HAIRLINE
            sp.line.width = Pt(1.5); flat(sp)
    return _fig_note(s, X, Y + body, W, spec.get("note"))


def _venn_label(s, cx, cy, w, label, points, *, acc=False, tier="label"):
    """원 안 라벨. 원은 가운데가 넓고 위아래가 좁으니 세로 중앙에 앉힌다."""
    h = 24 + (round(fs("caption") * lh("caption")) + 3) * len(points or [])
    _, tf = textbox(s, cx - w / 2, cy - h / 2, w, h, align=PP_ALIGN.CENTER)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run(p, label, fs(tier), color=ACCENT_DARK if acc else TEXT)
    for t in (points or []):
        p2 = para(tf, line=lh("caption"), space_after=3)
        p2.alignment = PP_ALIGN.CENTER
        run(p2, t, fs("caption"), bold=False, color=TEXT_SUB)


def _fig_venn(s, spec, rect):
    """겹치는 집합. nested 의 변형이다 ﹣ nested 는 포함(안에 완전히 들어간다),
    venn 은 교집합(일부만 겹친다). 원 2개 또는 3개.

    무채색에서 겹침은 반투명 채움이 나른다. 교집합이 저절로 한 단 진해진다."""
    X, Y, W, H = rect
    sets = spec["sets"][:3]
    nh = _note_h(spec)
    body = H - nh
    ov = spec.get("overlap")
    n = len(sets)

    if n == 2:
        # 지름 d, 중심 간격 0.70d (겹침 30%). 전체 폭 1.70d
        d = min(body, W / 1.70)
        r = d / 2
        cy = Y + body / 2
        mid = X + W / 2
        cxs = [mid - 0.35 * d, mid + 0.35 * d]
        lab_w = d * 0.62
        lab_pos = [(cxs[0] - r * 0.42, cy), (cxs[1] + r * 0.42, cy)]
        ov_pos = (mid, cy)
        ov_w = d * 0.32
    else:
        d = min(body * 0.70, W * 0.58)
        r = d / 2
        cx0, cy0 = X + W / 2, Y + body / 2
        off = d * 0.27
        cxs = [cx0 - off, cx0 + off, cx0]
        cys = [cy0 - off * 0.92, cy0 - off * 0.92, cy0 + off * 0.92]
        lab_w = d * 0.52
        lab_pos = [(cx0 - off - r * 0.44, cy0 - off * 1.30),
                   (cx0 + off + r * 0.44, cy0 - off * 1.30),
                   (cx0, cy0 + off * 1.66)]      # 아래 원 라벨은 교집합을 피해 더 내린다
        ov_pos = (cx0, cy0 - off * 0.10)
        # 3원 교집합은 자리가 좁다. 넓게 잡아 한 줄로 앉히고, 문안도 짧게 준다
        # (넘치면 아래 원 라벨을 파고든다 ﹣ 2026-08-24 실측)
        ov_w = d * 0.50

    for i, st in enumerate(sets):
        cx = cxs[i]
        cy_i = cy if n == 2 else cys[i]
        acc = bool(st.get("accent"))
        c = s.shapes.add_shape(MSO_SHAPE.OVAL, px(cx - r), px(cy_i - r), px(d), px(d))
        _alpha_fill(c, HAIRLINE, 20)
        c.line.color.rgb = ACCENT if acc else HAIRLINE
        c.line.width = Pt(1.6 if acc else 1.0)
        flat(c)

    for i, st in enumerate(sets):
        _venn_label(s, lab_pos[i][0], lab_pos[i][1], lab_w,
                    st["label"], st.get("points"), acc=bool(st.get("accent")))
    if ov:
        _venn_label(s, ov_pos[0], ov_pos[1], ov_w,
                    ov["label"], ov.get("points"), acc=True, tier="body")
    return _fig_note(s, X, Y + body, W, spec.get("note"))


FIGURES = {
    "two_panel": _fig_two_panel,
    "layers": _fig_layers,
    "timeline": _fig_timeline,
    "stages": _fig_stages,
    "placemap": _fig_placemap,
    "cards": _fig_cards,
    "hub": _fig_hub,
    "branch": _fig_branch,
    "nested": _fig_nested,
    "venn": _fig_venn,
    "matrix": _fig_matrix,
    "bars": _fig_bars,
    "area": _fig_area,
    "kpi": _fig_kpi,
}


def _fig_aside(s, aside, x, y, w):
    """도식 옆이나 아래에 붙는 글 설명. 도식이 못 담는 것만 여기 쓴다.
    본문 불릿보다 한 단 낮게 쓴다 — 도식이 주인공인 장에서 옆 글이 같은 무게면 시선이 갈린다."""
    tier = aside.get("tier", "caption")
    yy = col_label(s, x, y, aside["label"], w=w) if aside.get("label") else y
    if aside.get("lead"):
        _, tf = textbox(s, x, yy, w, 24)
        run(para(tf, first=True, line=lh(tier)), aside["lead"], fs(tier), bold=False, color=TEXT)
        yy += round(fs(tier) * lh(tier)) * wrapped_lines(aside["lead"], w, tier=tier) + 18
    if aside.get("points"):
        bullets(s, x, yy, w, aside["points"], size=fs(tier), line=lh(tier), tier=tier)
    return yy

def _shot_block(s, th, y, base_dir, reserve=0):
    """스크린샷 — 화면으로 봐야 아는 기능은 글로 적지 않는다.
    촬영본이 없으면 shot_slot 이 파일명과 담을 내용만 적은 빈 슬롯을 그린다(사용자가 나중에 넣는다)."""
    sh = th["shot"]
    if sh.get("layout") == "top":
        return _shot_top(s, sh, y, base_dir, reserve)
    h = sh.get("h", 244)
    left_w = int(CONTENT_W * 0.54)
    right_x = PAD_X + left_w + 36
    right_w = CONTENT_W - left_w - 36

    shot_slot(s, PAD_X, y, left_w, h, sh["shot_id"], sh["shot_desc"], base_dir)
    yy = col_label(s, right_x, y, sh["label"], w=right_w) if sh.get("label") else y
    if sh.get("points"):
        bullets(s, right_x, yy, right_w, sh["points"])
    return y + h



def _shot_top(s, sh, y, base_dir, reserve=0):
    """스크린샷을 전폭 상단에 두고 설명을 그 아래 2열로 편다.
    좌우 분할은 4:3 캡처가 폭에 묶여 작아진다. 화면 자체가 주인공인 장은 이 배치를 쓴다."""
    cols = sh["columns"]
    tier = sh.get("desc_tier", "caption")     # 샷이 주인공이라 설명은 한 단 낮춘다
    step = round(fs(tier) * lh(tier))
    gap = 40
    col_w = (CONTENT_W - gap) / 2
    # 실제 소비 높이로 잰다: col_label 46 + 불릿마다 (줄수 x step + 9).
    # 줄 수를 안 세면 두 줄짜리 항목에서 takeaway 가 불릿을 파고든다.
    desc_h = 46 + max(bullets_height(c["points"], col_w, tier=tier) for c in cols)
    # 바닥을 두지 않는다. 남는 만큼만 쓰고, 모자라면 그건 내용이 많다는 신호다
    # (고정 하한이 곧 오버플로였다).
    h = sh.get("h") or ((CANVAS_H - 54 - 24) - 30 - y - desc_h - reserve)
    if h < 120:
        print(f"  ! 상단 샷 높이 {int(h)}px — 화면이 주인공인 장인데 자리가 없다. "
              f"설명 줄이나 takeaway 를 줄여야 한다", file=sys.stderr)
    shot_slot(s, PAD_X, y, CONTENT_W, h, sh["shot_id"], sh["shot_desc"], base_dir)
    yy = y + h + 22
    for i, c in enumerate(cols[:2]):
        x = PAD_X + (col_w + gap) * i
        if i:
            vline(s, PAD_X + col_w + gap / 2, yy - 4, desc_h - 12)
        by = col_label(s, x, yy, c["label"], w=col_w)
        bullets(s, x, by, col_w, c["points"], size=fs(tier), line=lh(tier), tier=tier)
    return yy + desc_h


def _figure_block(s, th, y, avail):
    """layout 이 도식의 자리를 정하고, 도식 함수는 그 자리 안에만 그린다.
      full  : 전폭 (기본)
      split : 좌 도식 + 우 설명
      stack : 상 도식 + 하 설명 2열
    """
    spec = th["figure"]
    fn = FIGURES.get(spec.get("preset"))
    if fn is None:
        raise SystemExit(f"알 수 없는 도식 프리셋: {spec.get('preset')!r} (가능: {', '.join(FIGURES)})")
    aside = spec.get("aside")
    # 기본이 split 이다. 도식을 단독으로 전폭에 두는 경우보다 슬라이드를 갈라
    # 좌 도식 + 우 글로 쓰는 쪽이 표준이다.
    # 가로로 긴 도식(stages, timeline, bars, two_panel)은 json 에서 "stack" 을 명시한다.
    layout = spec.get("layout") or ("split" if aside else "full")
    if layout == "split" and aside:
        ratio = spec.get("ratio", 0.58)
        gap = 44
        fw = CONTENT_W * ratio - gap / 2
        fn(s, spec, (PAD_X, y, fw, avail))
        _fig_aside(s, aside, PAD_X + fw + gap, y, CONTENT_W - fw - gap)
        return y + avail
    if layout == "stack" and aside:
        desc_h = 46 + bullets_height(aside.get("points") or [], CONTENT_W, tier="caption")
        fh = max(120, avail - desc_h - 20)
        fn(s, spec, (PAD_X, y, CONTENT_W, fh))
        _fig_aside(s, aside, PAD_X, y + fh + 20, CONTENT_W)
        return y + avail
    return fn(s, spec, (PAD_X, y, CONTENT_W, avail))


def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])

# ================================================================ 강연·강의 덱 (가변 길이)
# 슬라이드 배열(JSON "slides")을 그대로 따라 만든다.
# 골격은 표지 → [장 시작 간지 → 본문 장들] x N → EOD 간지 (Q&A 간지는 옵션).
# 크기·행간은 TYPE 이름으로만 얻는다.

def _headline_block(slide, title, subhead=None, runhead=None):
    """장 타이틀 + (선택) 서브헤드. 반환값은 본문 시작 y."""
    bottom = headline(slide, title, runhead)
    if subhead:
        _, tf = textbox(slide, PAD_X, bottom + 16, CONTENT_W, 26)
        # 참조 덱 실측: 이 자리는 라벨성 부제가 아니라 완전한 서술문 한두 줄이다.
        # 그래서 회색이 아니라 본문 색으로 둔다 (2026-08-31 사용자 확정).
        run(para(tf, first=True, line=lh("heading")), subhead, fs("heading"),
            bold=False, color=TEXT)
        return bottom + 54
    return bottom


def talk_cover(prs, d, s, spec):
    # 표지에 짤이나 이미지를 깔 수 있다. shot_id 를 주면 글 아래에 넣는다.
    if spec.get("shot_id"):
        img_h = spec.get("shot_h", 250)
        shot_slot(s, PAD_X + CONTENT_W / 2 - 300, CANVAS_H - img_h - 76, 600, img_h,
                  spec["shot_id"], spec.get("shot_desc", ""), d.get("_dir"))
        cy = (CANVAS_H - img_h - 76) / 2 + 24
        _, tf = textbox(s, PAD_X, cy - 96, CONTENT_W, 26, align=PP_ALIGN.CENTER)
        run(tf.paragraphs[0], spec["event"], fs("label"), color=MARK)
        _, tf = textbox(s, PAD_X, cy - 58, CONTENT_W, 24, align=PP_ALIGN.CENTER)
        run(tf.paragraphs[0], spec["meta"], fs("label"), bold=False, color=TEXT_SUB)
        _, tf = textbox(s, PAD_X, cy - 12, CONTENT_W, 80, align=PP_ALIGN.CENTER)
        run(para(tf, first=True, line=lh("display")), spec["title"], fs("display"), color=TEXT)
        if spec.get("speaker"):
            _, tf = textbox(s, PAD_X, cy + 74, CONTENT_W, 24, align=PP_ALIGN.CENTER)
            run(tf.paragraphs[0], spec["speaker"], fs("label"), bold=False, color=TEXT_SUB)
        return
    cy = CANVAS_H / 2
    _, tf = textbox(s, PAD_X, cy - 132, CONTENT_W, 26, align=PP_ALIGN.CENTER)
    run(tf.paragraphs[0], spec["event"], fs("label"), color=MARK)

    _, tf = textbox(s, PAD_X, cy - 92, CONTENT_W, 24, align=PP_ALIGN.CENTER)
    run(tf.paragraphs[0], spec["meta"], fs("label"), bold=False, color=TEXT_SUB)

    _, tf = textbox(s, PAD_X, cy - 40, CONTENT_W, 96, align=PP_ALIGN.CENTER)
    p = para(tf, first=True, line=lh("display"))
    run(p, spec["title"], fs("display"), color=TEXT)

    if spec.get("speaker"):
        _, tf = textbox(s, PAD_X, cy + 76, CONTENT_W, 24, align=PP_ALIGN.CENTER)
        run(tf.paragraphs[0], spec["speaker"], fs("label"), bold=False, color=TEXT_SUB)


def talk_divider(prs, d, s, spec):
    """간지 3종 공용 — 장 시작 · EOD · Q&A. 배경은 흰색, accent 는 라벨에만."""
    cy = CANVAS_H / 2
    if spec.get("label"):
        _, tf = textbox(s, PAD_X, cy - 106, CONTENT_W, 24, align=PP_ALIGN.CENTER)
        run(tf.paragraphs[0], spec["label"], fs("label"), color=MARK)
    _, tf = textbox(s, PAD_X, cy - 62, CONTENT_W, 96, align=PP_ALIGN.CENTER)
    run(para(tf, first=True, line=lh("display")), spec["title"], fs("display"), color=TEXT)
    # 구분선은 sub 와 무관하게 켜고 끈다. 종전에는 sub 없는 간지에서 선까지 사라졌다.
    if spec.get("rule", True):
        hline(s, PAD_X + CONTENT_W / 2 - 120, cy + 42, 240)
    if spec.get("sub"):
        _, tf = textbox(s, PAD_X, cy + 62, CONTENT_W, 26, align=PP_ALIGN.CENTER)
        run(tf.paragraphs[0], spec["sub"], fs("body"), bold=False, color=TEXT_SUB)


def talk_bullets(prs, d, s, spec):
    y = _headline_block(s, spec["title"], spec.get("subhead"), spec.get("runhead"))
    y += 34
    if spec.get("lead"):
        _, tf = textbox(s, PAD_X, y, CONTENT_W, 26)
        run(para(tf, first=True, line=lh("heading")), spec["lead"], fs("heading"), color=TEXT)
        y += 46
    bullets(s, PAD_X, y, CONTENT_W, spec["items"], gap=14,
            marker=spec.get("marker", MARKER_DEFAULT))
    if spec.get("note"):
        _, tf = textbox(s, PAD_X, CANVAS_H - 96, CONTENT_W, 20)
        run(tf.paragraphs[0], spec["note"], fs("caption"), bold=False, color=TEXT_SUB)


def talk_split(prs, d, s, spec):
    """2열 대구 — AS-IS/TO-BE · 다루는것/안다루는것 · 문제/해결."""
    y = _headline_block(s, spec["title"], spec.get("subhead"), spec.get("runhead"))
    y += 34
    gap = 56
    col_w = (CONTENT_W - gap) / 2
    for i, col in enumerate(spec["columns"]):
        x = PAD_X + (col_w + gap) * i
        if i:
            vline(s, PAD_X + col_w + gap / 2, y - 6, 300)
        cy = col_label(s, x, y, col["label"], w=col_w)
        bullets(s, x, cy, col_w, col["items"], gap=13,
                marker=spec.get("marker", MARKER_DEFAULT))
    if spec.get("note"):
        _, tf = textbox(s, PAD_X, CANVAS_H - 96, CONTENT_W, 20)
        run(tf.paragraphs[0], spec["note"], fs("caption"), bold=False, color=TEXT_SUB)


def talk_table(prs, d, s, spec):
    """비교표 — 개념 대비는 산문 대신 표로 보여준다."""
    y = _headline_block(s, spec["title"], spec.get("subhead"), spec.get("runhead"))
    y += 30
    cols = spec["header"]
    widths = spec.get("widths") or [1] * len(cols)
    unit = CONTENT_W / sum(widths)
    xs, acc = [], PAD_X
    for w in widths:
        xs.append(acc)
        acc += w * unit

    # 줄 높이는 사다리에서 계산한다. 고정 px 를 쓰면 본문 단이 커질 때 구분선이 글자를 관통한다.
    head_h = int(fs("label") * lh("label")) + 6
    for i, h in enumerate(cols):
        _, tf = textbox(s, xs[i], y, widths[i] * unit - 18, head_h)
        run(tf.paragraphs[0], h, fs("label"), color=TEXT)
    y += head_h + 8
    hline(s, PAD_X, y, CONTENT_W, color=ACCENT, weight=1.5)
    y += 12

    line_h = int(fs("body") * lh("body"))
    row_h = spec.get("row_h", line_h + 20)
    for r, row in enumerate(spec["rows"]):
        for i, cell in enumerate(row):
            _, tf = textbox(s, xs[i], y, widths[i] * unit - 18, line_h + 6)
            p = para(tf, first=True, line=lh("body"))
            for seg, strong in normalize(cell):
                run(p, seg, fs("body"), bold=strong, color=TEXT if strong else TEXT_SUB)
        y += row_h
        if r < len(spec["rows"]) - 1:
            hline(s, PAD_X, y - 6, CONTENT_W)
    if spec.get("note"):
        _, tf = textbox(s, PAD_X, CANVAS_H - 96, CONTENT_W, 20)
        run(tf.paragraphs[0], spec["note"], fs("caption"), bold=False, color=TEXT_SUB)


def talk_process(prs, d, s, spec):
    """프로세스형 도식 — 순서 있는 단계 흐름을 가로로 자동 배치."""
    y = _headline_block(s, spec["title"], spec.get("subhead"), spec.get("runhead"))
    nodes = spec["nodes"]
    n = len(nodes)
    gap = 26
    node_w = (CONTENT_W - gap * (n - 1)) / n
    node_h = 132
    oy = y + 96

    for i, nd in enumerate(nodes):
        x = PAD_X + (node_w + gap) * i
        box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, px(x), px(oy), px(node_w), px(node_h))
        box.adjustments[0] = 0.08
        focal = nd.get("focal")
        if focal == "fill":
            box.fill.solid()
            box.fill.fore_color.rgb = ACCENT
            box.line.color.rgb = ACCENT
        elif focal == "outline":
            box.fill.background()
            box.line.color.rgb = ACCENT
            box.line.width = Pt(1.5)
        else:
            box.fill.background()
            box.line.color.rgb = BORDER
            box.line.width = Pt(1.0)
        flat(box)
        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = px(14)
        tf.margin_top = tf.margin_bottom = px(12)
        tf.vertical_anchor = MSO_ANCHOR.TOP
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        p.line_spacing = lh("label")
        p.space_after = Pt(6)
        run(p, f'{i + 1}  {nd["title"]}', fs("label"),
            color=WHITE if focal == "fill" else (ACCENT_DARK if focal == "outline" else TEXT))
        p2 = para(tf, line=lh("body"))
        p2.alignment = PP_ALIGN.LEFT
        run(p2, nd["sub"], fs("body"), bold=False,
            color=RGBColor(0xD7, 0xE4, 0xFF) if focal == "fill" else TEXT_SUB)

        if i < n - 1:
            arr = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW,
                                     px(x + node_w + 5), px(oy + node_h / 2 - 6),
                                     px(gap - 10), px(12))
            arr.fill.solid()
            arr.fill.fore_color.rgb = HAIRLINE
            arr.line.fill.background()
            flat(arr)

    by = oy + node_h + 30
    if spec.get("input"):
        _, tf = textbox(s, PAD_X, by, CONTENT_W / 2, 20)
        run(tf.paragraphs[0], spec["input"], fs("body"), bold=False, color=TEXT_SUB)
    if spec.get("output"):
        _, tf = textbox(s, PAD_X + CONTENT_W / 2, by, CONTENT_W / 2, 20, align=PP_ALIGN.RIGHT)
        run(tf.paragraphs[0], spec["output"], fs("body"), bold=False, color=TEXT_SUB)
    if spec.get("note"):
        _, tf = textbox(s, PAD_X, by + 34, CONTENT_W, 20)
        run(tf.paragraphs[0], spec["note"], fs("caption"), bold=False, color=TEXT_SUB)


def talk_steps(prs, d, s, spec):
    """순차 절차 — 숫자 리스트 고정 (번호는 용도별로 고정해서 쓴다)."""
    y = _headline_block(s, spec["title"], spec.get("subhead"), spec.get("runhead"))
    y += 30
    if spec.get("lead"):
        _, tf = textbox(s, PAD_X, y, CONTENT_W, 26)
        run(para(tf, first=True, line=lh("heading")), spec["lead"], fs("heading"), color=TEXT)
        y += 44

    items = spec["items"]
    has_desc = any(isinstance(it, dict) and it.get("desc") for it in items)
    # 이름 줄 높이는 body 사다리에서 계산한다. 세미나룸(본문 20pt)에서 고정 27px 을 쓰면
    # 설명이 이름 위로 올라와 겹친다.
    name_h = int(TYPE["body"][0] * TYPE["body"][1]) + 4
    desc_h = int(TYPE["caption"][0] * TYPE["caption"][1]) + 2
    row_h = spec.get("row_h", (name_h + desc_h + 14) if has_desc else (name_h + 16))
    for i, it in enumerate(items):
        name = it["name"] if isinstance(it, dict) else it
        desc = it.get("desc") if isinstance(it, dict) else None
        _, tf = textbox(s, PAD_X, y, 44, 24)
        run(para(tf, first=True, line=lh("body")), f"{i + 1}", fs("body"), color=ACCENT_DARK)
        _, tf = textbox(s, PAD_X + 44, y, CONTENT_W - 44, 24)
        p = para(tf, first=True, line=lh("body"))
        for seg, strong in normalize(name):
            run(p, seg, fs("body"), bold=strong, color=TEXT if strong else TEXT_SUB)
        if desc:
            _, tf = textbox(s, PAD_X + 44, y + name_h, CONTENT_W - 44, desc_h)
            run(para(tf, first=True, line=lh("caption")), desc, fs("caption"),
                bold=False, color=TEXT_SUB)
        y += row_h
        if i < len(items) - 1:
            hline(s, PAD_X, y - 12, CONTENT_W)
    if spec.get("note"):
        _, tf = textbox(s, PAD_X, CANVAS_H - 96, CONTENT_W, 20)
        run(tf.paragraphs[0], spec["note"], fs("caption"), bold=False, color=TEXT_SUB)


def talk_recap(prs, d, s, spec):
    """EOD 직전 정리 — 번호 붙인 핵심 문장 + (선택) 인계 경로."""
    y = _headline_block(s, spec["title"], spec.get("subhead"), spec.get("runhead"))
    y += 34
    ly = col_label(s, PAD_X, y, spec.get("label", "핵심"), w=CONTENT_W)
    _, tf = textbox(s, PAD_X, ly, CONTENT_W, 0)
    for i, line in enumerate(spec["items"]):
        p = para(tf, first=(i == 0), line=lh("body"), space_after=16)
        run(p, f"{i + 1}  ", fs("body"), color=ORDINAL)
        for seg, strong in normalize(line):
            run(p, seg, fs("body"), bold=strong, color=TEXT if strong else TEXT_SUB)
    if spec.get("handoff"):
        hy = CANVAS_H - 192
        hline(s, PAD_X, hy, CONTENT_W)
        hy = col_label(s, PAD_X, hy + 18, spec.get("handoff_label", "인계"), w=CONTENT_W)
        _, tf = textbox(s, PAD_X, hy, CONTENT_W, 24)
        p = para(tf, first=True, line=lh("body"))
        for seg, strong in normalize(spec["handoff"]):
            run(p, seg, fs("body"), bold=strong, color=TEXT if strong else TEXT_SUB)


# ---------------------------------------------------------------- talk 뼈대 2종 (2026-08-31 신설)
# 강연 덱의 뼈대는 스크린샷과 도식이다 (사용자 확정). 불릿 나열은 이 둘이 안 맞을 때의 폴백이다.
# VOD 이론장이 이미 갖고 있던 shot_slot / FIGURES 를 talk 경로로 끌어와 일반화했다.
# 두 함수 모두 레이아웃을 새로 쓰지 않고 기존 배치 함수를 감싸기만 한다.

BODY_BOTTOM = CANVAS_H - 54 - 24   # footer 밑줄 위로 남기는 여백


def _talk_body_top(s, spec):
    y = _headline_block(s, spec["title"], spec.get("subhead"), spec.get("runhead"))
    return y + 28


def _talk_note(s, spec):
    """장 바닥 한 줄. 도식이 못 담는 단서를 여기 둔다."""
    if not spec.get("note"):
        return 0
    _, tf = textbox(s, PAD_X, CANVAS_H - 96, CONTENT_W, 20)
    run(tf.paragraphs[0], spec["note"], fs("caption"), bold=False, color=TEXT_SUB)
    return 34


def _talk_shot_pair(s, sh, y, base_dir):
    """화면 두 장 좌우 대비. 배드와 굿, 전과 후처럼 모양 차이 자체가 논지인 장에 쓴다.
    초보자가 많은 방에서는 노드를 읽히려 하지 말고 이 배치로 모양만 보인다."""
    gap = 36
    col_w = (CONTENT_W - gap) / 2
    h = sh.get("h", 296)
    for i, c in enumerate(sh["columns"][:2]):
        x = PAD_X + (col_w + gap) * i
        # 라벨은 선택이다. 종전에는 키가 없으면 KeyError 로 죽었고, 빈 문자열을 넣으면
        # 46px 를 그냥 먹었다. 없으면 화면을 그만큼 위로 올린다.
        cy = col_label(s, x, y, c["label"], w=col_w) if c.get("label") else y
        shot_slot(s, x, cy, col_w, h, c["shot_id"], c.get("shot_desc", ""), base_dir)
        if c.get("caption"):
            _, tf = textbox(s, x, cy + h + 10, col_w, 40)
            run(para(tf, first=True, line=lh("caption")), c["caption"],
                fs("caption"), bold=False, color=TEXT_SUB)
    return y + 46 + h


def talk_shot(prs, d, s, spec):
    """스크린샷 장. layout 은 셋이다.
      side : 좌 화면 + 우 설명 (기본)
      top  : 전폭 화면 + 아래 2열 설명. 화면 자체가 주인공일 때
      pair : 화면 두 장 좌우 대비
    촬영본이 없으면 파일명과 담을 내용만 적은 빈 슬롯이 나온다. 사용자가 나중에 넣는다."""
    y = _talk_body_top(s, spec)
    sh = spec["shot"]
    base_dir = d.get("_dir")
    reserve = _talk_note(s, spec)
    if sh.get("layout") == "pair":
        _talk_shot_pair(s, sh, y, base_dir)
    else:
        _shot_block(s, {"shot": sh}, y, base_dir, reserve=reserve)


def talk_figure(prs, d, s, spec):
    """도식 장. FIGURES 프리셋 14종을 그대로 쓴다.
    배치 기본값은 split(좌 도식 + 우 설명). 가로로 긴 프리셋만 stack 을 명시한다."""
    y = _talk_body_top(s, spec)
    avail = BODY_BOTTOM - y - _talk_note(s, spec)
    _figure_block(s, {"figure": spec["figure"]}, y, avail)


def talk_contacts(prs, d, s, spec):
    """QR 을 가로로 늘어놓는 장. 발표가 끝난 뒤 이어질 경로를 남긴다.
    덱 마지막에 기본으로 넣는다 (2026-08-31 사용자 지시)."""
    y = _talk_body_top(s, spec)
    items = spec["items"]
    n = max(1, len(items))
    gap = 44
    col_w = (CONTENT_W - gap * (n - 1)) / n
    qr = min(col_w, 220)
    for i, it in enumerate(items):
        x = PAD_X + (col_w + gap) * i
        shot_slot(s, x + (col_w - qr) / 2, y, qr, qr,
                  it["shot_id"], it.get("shot_desc", ""), d.get("_dir"))
        _, tf = textbox(s, x, y + qr + 18, col_w, 28, align=PP_ALIGN.CENTER)
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        run(tf.paragraphs[0], it["label"], fs("label"), color=TEXT)
        if it.get("sub"):
            _, tf = textbox(s, x, y + qr + 50, col_w, 24, align=PP_ALIGN.CENTER)
            tf.paragraphs[0].alignment = PP_ALIGN.CENTER
            run(tf.paragraphs[0], it["sub"], fs("caption"), bold=False, color=TEXT_SUB)
    _talk_note(s, spec)


TALK_SLIDES = {
    "cover":   talk_cover,
    "divider": talk_divider,
    "bullets": talk_bullets,
    "split":   talk_split,
    "table":   talk_table,
    "process": talk_process,
    "steps":   talk_steps,
    "recap":   talk_recap,
    "shot":    talk_shot,
    "figure":  talk_figure,
    "contacts": talk_contacts,
}


def install_master_chrome(prs, copyright_text):
    """장마다 똑같이 반복되는 요소를 슬라이드 마스터로 올린다.
    푸터 구분선과 카피라이트가 대상이다. 페이지 번호는 장마다 달라 슬라이드에 남는다.

    python-pptx 는 마스터·레이아웃에 add_textbox 를 열어 주지 않는다. 그래서 임시 슬라이드에
    그린 뒤 그 XML 을 마스터의 spTree 로 옮기고 임시 슬라이드를 지운다. 결과 파일에서는
    사용자가 [보기 > 슬라이드 마스터] 에서 한 번만 고치면 전 장에 반영된다."""
    from copy import deepcopy
    tmp = blank(prs)
    y = CANVAS_H - 54
    hline(tmp, PAD_X, y, CONTENT_W)
    _, tf = textbox(tmp, PAD_X, y + 13, CONTENT_W, 18, align=PP_ALIGN.CENTER)
    run(tf.paragraphs[0], copyright_text, fs("chrome"), bold=False, color=TEXT_SUB)

    master_tree = prs.slide_master.shapes._spTree
    for sp in list(tmp.shapes):
        master_tree.append(deepcopy(sp._element))

    # 임시 슬라이드 제거 (관계와 목록 양쪽에서)
    xml_slides = prs.slides._sldIdLst
    last = list(xml_slides)[-1]
    prs.part.drop_rel(last.rId)
    xml_slides.remove(last)


def _talk_lint(data, specs):
    """렌더는 막지 않고 stderr 로만 말한다. 차단은 미수집 자산(--strict-assets) 하나뿐이다.
    여기서 소리를 내는 목적은 문제를 빌드 시점에 앞당겨 드러내는 것이다."""
    meta = data.get("_meta", {})
    warn = lambda m: print(f"   ⚠ {m}", file=sys.stderr)

    def slide_text(sp):
        out = [sp.get("title", ""), sp.get("subhead", ""), sp.get("lead", ""), sp.get("sub", "")]
        out += [str(x) for x in sp.get("items", [])]
        for col in sp.get("columns", []) or []:
            out.append(col.get("label", ""))
            out += [str(x) for x in col.get("items", [])]
        return " ".join(x for x in out if x)

    # 밀도 — 어절 기준. 한국어라 영어 단어 수와 단위가 다르다. 기본 상한 40어절.
    dens = meta.get("density", {})
    cap = dens.get("words_per_slide_max", 40)
    if cap:
        over = [(i, n) for i, sp in enumerate(specs, 1)
                if (n := len(slide_text(sp).split())) > cap]
        if over:
            warn(f"장당 {cap}어절 초과 {len(over)}장: " +
                 ", ".join(f"{i}({n})" for i, n in over[:8]))


def build_talk(data, out_path, strict_assets=False):
    meta = data.get("_meta", {})
    # 사다리를 talk 값으로 갈아탄다. CLI 는 덱 하나당 한 프로세스라 VOD 렌더와 섞이지 않는다.
    # venue=room 이면 본문 단만 20pt 로 올린다 (세미나룸 뒷자리 가독성).
    venue = meta.get("venue", "vod")
    TYPE.update(TALK_TYPE_ROOM if venue == "room" else TALK_TYPE)
    # 발표 덱은 마커 없는 본문이 기본이다. 강의 덱은 종전대로 ▪.
    global MARKER_DEFAULT
    MARKER_DEFAULT = meta.get("body_marker", meta.get("genre") != "talk")
    print(f"   장르 {meta.get('genre', '(미선언)')} · 시청조건 {venue}"
          f" · 본문 {fs('body') * 0.75:.4g}pt · 마커 {'on' if MARKER_DEFAULT else 'off'}",
          file=sys.stderr)
    MISSING_SHOTS.clear()
    prs = Presentation()
    prs.slide_width = px(CANVAS_W)
    prs.slide_height = px(CANVAS_H)
    specs = data["slides"]
    total = len(specs)
    # 기본값은 끔이다. 파워포인트에서 마스터 편집이 실사용으로 이어지지 않았고,
    # 템플릿 장을 복사해 쓰는 방식에서는 푸터가 슬라이드에 있어야 복사할 때 같이
    # 따라온다. 필요하면 JSON 에서 use_master: true 로 켤 수 있다.
    use_master = data.get("use_master", False)
    if use_master:
        install_master_chrome(prs, data["copyright"])
    for i, spec in enumerate(specs):
        kind = spec["type"]
        if kind not in TALK_SLIDES:
            raise SystemExit(f"알 수 없는 슬라이드 유형: {kind} (가능: {', '.join(TALK_SLIDES)})")
        s = blank(prs)
        TALK_SLIDES[kind](prs, data, s, spec)
        if use_master:
            page_number(s, i + 1, total)
        else:
            footer(s, i + 1, data["copyright"], total)
        # 구어 멘트는 슬라이드에 박제하지 않고 speaker notes 로만
        if spec.get("notes"):
            s.notes_slide.notes_text_frame.text = spec["notes"]

    _talk_lint(data, specs)
    if MISSING_SHOTS:
        uniq = sorted(set(MISSING_SHOTS))
        print(f"   ⚠ 촬영본 미수집 {len(uniq)}건 — 빈 자리로 나갔다: "
              + ", ".join(uniq), file=sys.stderr)
        for sid in uniq:
            print(f"     assets/shots/{sid}.png", file=sys.stderr)
        if strict_assets:
            raise SystemExit("--strict-assets: 미수집 자산이 있어 중단한다")
    for u in meta.get("unrenderable", []):
        print(f"   · 수작업 장 {u.get('slide')} ({u.get('kind')}) — 생성기 범위 밖",
              file=sys.stderr)
    prs.save(out_path)
    return out_path


# ---------------------------------------------------------------- 진입점
def build(data, out_path, strict_assets=False):
    # 색은 그리기 전에 확정한다. 지정이 없으면 DEFAULT_THEME 이라 종전 렌더가 그대로 나온다.
    theme_name = data.get("theme") or _find_project_theme(data.get("_dir", ".")) or DEFAULT_THEME
    th = load_theme(theme_name)
    # 디스크에 남은 pptx 가 어느 테마에서 나왔는지 나중에 알 길이 이 줄뿐이다.
    print(f"   테마 {th['name']} {th['version']}", file=sys.stderr)
    # 콘텐츠 json 최상위 "font" 키가 있으면 전역 폰트를 그 이름으로 바꾼다.
    # "theme" 키는 이미 테마 이름으로 쓰이므로 충돌을 피해 별도 키를 둔다.
    global FONT
    if data.get("font"):
        FONT = data["font"]
    if not data.get("slides"):
        raise SystemExit('slides 배열이 필요하다 — 이 생성기는 가변 덱 경로만 지원한다')
    return build_talk(data, out_path, strict_assets=strict_assets)


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    strict = "--strict-assets" in sys.argv
    src = Path(argv[0])
    data = json.loads(src.read_text(encoding="utf-8"))
    data["_dir"] = str(src.parent)  # assets/shots 촬영본 탐색 기준
    out = Path(argv[1]) if len(argv) > 1 else src.with_suffix(".pptx")
    build(data, out, strict_assets=strict)
    print(f"→ {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
