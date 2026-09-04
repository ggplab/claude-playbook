#!/usr/bin/env python3
"""card-news 빌더: 콘텐츠 JSON 하나에서 카드 PNG 덱을 만들고 규격을 실측 판정한다.

  python3 build.py <content.json>

의존성 0. 설치된 Chrome(또는 Chromium, Edge)의 headless 모드만 쓴다. playwright, npm, pip 불필요.
  - 렌더: Chrome --screenshot. 캔버스와 출력 해상도가 같으므로 배율 1x.
  - 규격 검사: Chrome --dump-dom 으로 template.html 안의 자가검사 스크립트 결과를 회수한다.
    정적 CSS 파싱은 캐스케이드를 못 풀어서 "CSS 파일 검사"가 되어 버린다. 그래서 브라우저가 실제로
    적용한 값을 잰다.

브라우저 경로를 직접 지정하려면 환경변수 CARD_NEWS_CHROME 에 실행 파일 경로를 넣는다.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# 모바일 공유 티어 규격. template.html 의 크기 3단(64/40/32)과 짝이다. 바꾸면 두 곳을 함께 고친다.
MIN_DISPLAY_PX = 390      # 휴대폰에서 카드가 표시되는 최소 폭
MIN_EFFECTIVE_PT = 11     # 한글이 확대 없이 읽히는 유효 하한
MAX_SIZE_STEPS = 3        # 한 카드 안의 서로 다른 글자 크기 상한
MAX_ITEMS = 6             # 카드당 항목 상한
MIN_CONTRAST = 4.5        # WCAG AA 본문 대비
BANNED_PUNCT = re.compile(r"[—–·]")   # em dash, en dash, 가운데점. AI 말투 흔적이라 카드에서 뺀다.

CHROME_CANDIDATES = [
    # macOS
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    # Windows
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    # Linux (PATH 에서 찾는다)
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge",
]


def find_chrome():
    env = os.environ.get("CARD_NEWS_CHROME")
    if env and Path(env).exists():
        return env
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
        found = shutil.which(c)
        if found:
            return found
    return None


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def rich(s):
    """**강조** 만 허용. 크기를 바꾸지 않고 색과 굵기로만 계층을 만든다."""
    return re.sub(r"\*\*(.+?)\*\*", r'<b style="color:#31302e">\1</b>', esc(s))


def br(s):
    return esc(s).replace("\n", "<br>")


def render_card(c):
    if c.get("type") == "cover":
        return f"""<div class="card cover">
  <div class="bar"></div>
  <div class="sm-a eyebrow">{esc(c.get('eyebrow', ''))}</div>
  <div class="lg">{br(c['title'])}</div>
  <div class="rule"></div>
  <div class="md-r">{br(c.get('sub', ''))}</div>
  <div class="foot"><span class="sm">{esc(c.get('foot_left', ''))}</span><span class="sm">{esc(c.get('foot_right', ''))}</span></div>
</div>"""

    items = "".join(
        '<li><span class="{kc} k">{k}</span><span class="sm v">{v}</span></li>'.format(
            kc="sm-a" if it.get("accent") else "sm-b", k=esc(it["k"]), v=esc(it["v"]))
        for it in c.get("items", []))
    note = ""
    if c.get("note"):
        note = f'<div class="note"><span class="sm">{rich(c["note"]).replace(chr(10), "<br>")}</span></div>'
    foot = ""
    if c.get("foot_left") or c.get("foot_right"):
        foot = (f'<div class="foot"><span class="sm">{esc(c.get("foot_left", ""))}</span>'
                f'<span class="sm">{esc(c.get("foot_right", ""))}</span></div>')
    return f"""<div class="card">
  <div class="bar"></div>
  <div class="sm-a label">{esc(c.get('label', ''))}</div>
  <div class="md title">{br(c['title'])}</div>
  <ul>{items}</ul>
  {note}{foot}
</div>"""


def build_html(cards, w, h):
    tpl = (HERE / "template.html").read_text(encoding="utf-8")
    body = "\n".join(render_card(c) for c in cards)
    return tpl.replace("__W__", str(w)).replace("__H__", str(h)).replace("__CARDS__", body)


def chrome(exe, args, timeout=90):
    return subprocess.run([exe, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                           "--no-sandbox"] + args,
                          capture_output=True, text=True, timeout=timeout)


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: build.py <content.json>")
    exe = find_chrome()
    if not exe:
        sys.exit("FAIL: Chrome을 찾을 수 없다. Chrome을 설치하거나 CARD_NEWS_CHROME 환경변수에 경로를 넣어라.")

    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    meta, cards = spec["meta"], spec["cards"]
    w, h = (int(x) for x in meta.get("canvas", "1080x1350").split("x"))
    out = Path(meta["outdir"]).expanduser()
    work = out / "_src"
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(exist_ok=True)

    floor = MIN_EFFECTIVE_PT / (MIN_DISPLAY_PX / w)
    fails, warns = [], []

    # 1. 정적 검사: 브라우저 없이 확실히 잡히는 것
    flat = json.dumps(spec, ensure_ascii=False)
    for m in BANNED_PUNCT.finditer(flat):
        ctx = flat[max(0, m.start() - 30):m.start() + 30]
        fails.append(f"금지 문장부호 {m.group()!r}: ...{ctx}...")
    for i, c in enumerate(cards, 1):
        n = len(c.get("items", []))
        if n > MAX_ITEMS:
            fails.append(f"카드 {i}: 항목 {n}개 (상한 {MAX_ITEMS}). 카드를 쪼개라.")

    # 2. 전체 HTML 렌더 + 브라우저 실측 회수
    all_html = work / "_all.html"
    all_html.write_text(build_html(cards, w, h), encoding="utf-8")
    dom = chrome(exe, ["--virtual-time-budget=4000", "--dump-dom", all_html.as_uri()]).stdout
    m = re.search(r"LINT_JSON:(\{.*?\})</div>", dom, re.S)
    if not m:
        sys.exit("FAIL: 자가검사 결과를 회수하지 못했다 (template.html의 script 확인)")
    report = json.loads(m.group(1))

    for r in report["cards"]:
        i = r["i"]
        if len(r["sizes"]) > MAX_SIZE_STEPS:
            fails.append(f"카드 {i}: 글자 크기 {len(r['sizes'])}단 {r['sizes']} (상한 {MAX_SIZE_STEPS})")
        if r["minSize"] < floor:
            fails.append(f"카드 {i}: 최소 글자 {r['minSize']}px < 하한 {floor:.1f}px")
        if r["contrast"] < MIN_CONTRAST:
            fails.append(f"카드 {i}: 대비 {r['contrast']}:1 < {MIN_CONTRAST} \"{r['contrastText']}\"")
        if r["slack"] < 0:
            fails.append(f"카드 {i}: 내용이 {-r['slack']}px 넘쳤다 (잘림) \"{r['lowest']}\"")
        elif r["slack"] < 24:
            warns.append(f"카드 {i}: 하단 여백 {r['slack']}px. 문구를 줄이는 편이 낫다.")

    if len(report["cards"]) != len(cards):
        fails.append(f"카드 수 불일치: 정의 {len(cards)} vs 렌더 {len(report['cards'])}")

    # 3. 판정을 통과한 뒤에만 PNG를 뽑는다
    if fails:
        print("FAIL")
        for f in fails:
            print("  -", f)
        for w_ in warns:
            print("  ! ", w_)
        sys.exit(1)

    for old in out.glob("card-*.png"):
        old.unlink()
    for i, c in enumerate(cards, 1):
        f = work / f"card-{i:02d}.html"
        f.write_text(build_html([c], w, h), encoding="utf-8")
        png = out / f"card-{i:02d}.png"
        chrome(exe, [f"--window-size={w},{h}", "--virtual-time-budget=3000",
                     f"--screenshot={png}", f.as_uri()])
        if not png.exists():
            sys.exit(f"FAIL: card-{i:02d}.png 생성 실패")

    n = len(list(out.glob("card-*.png")))
    print("PASS")
    print(f"  카드 {n}장 / 캔버스 {w}x{h} / 글자 하한 {floor:.1f}px")
    for w_ in warns:
        print("  ! ", w_)
    print(f"  출력: {out}")
    if n != len(cards):
        sys.exit(f"FAIL: PNG {n}장 != 정의 {len(cards)}장")


if __name__ == "__main__":
    main()
