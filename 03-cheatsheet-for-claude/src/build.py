"""치트시트 빌드: 내용 JSON + 디자인 토큰 → HTML → PDF·PNG, 넘침 검사.

사용: python3 src/build.py ko
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
OUT = ROOT / "build"


def token_css() -> str:
    tokens = json.loads((SRC / "design-tokens.json").read_text())
    lines = [f"  --{k}: {v['hex']};" for k, v in tokens["color"].items()]
    return ":root {\n" + "\n".join(lines) + "\n}"


def build_html(lang: str) -> Path:
    data = json.loads((SRC / f"content.{lang}.json").read_text())
    html = (SRC / "a3.html").read_text()
    html = html.replace("/*__TOKENS__*/", token_css())
    html = html.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))
    out = OUT / f"claude-cheatsheet-a3-{lang}.html"
    out.write_text(html)
    return out


# 칸 밖으로 글자가 넘친 요소를 찾는다
OVERFLOW_JS = """
() => {
  const bad = [];
  document.querySelectorAll('.card, .panel, .card-body, pre, .page, .tile, .loop, .adv .a, .safe, .areas, .pipe-wrap, .inner, .cards').forEach(el => {
    if (el.scrollHeight > el.clientHeight + 1 || el.scrollWidth > el.clientWidth + 1) {
      bad.push({cls: el.className, page: el.closest('.page')?.id, id: el.closest('[id]')?.id,
                h: [el.scrollHeight, el.clientHeight], w: [el.scrollWidth, el.clientWidth]});
    }
  });
  return bad;
}
"""


def render(html: Path, lang: str) -> None:
    # A3 가로 420×297mm = 1587×1123 CSS px (96dpi)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1588, "height": 2246}, device_scale_factor=3)
        page.goto(html.as_uri())
        page.wait_for_selector("body[data-ready='1']")
        page.evaluate("document.fonts.ready")
        bad = page.evaluate(OVERFLOW_JS)
        for side in ("front", "back"):
            page.locator(f"#{side}").screenshot(path=str(OUT / f"claude-cheatsheet-a3-{lang}-{side}.png"))
        page.pdf(path=str(OUT / f"claude-cheatsheet-a3-{lang}.pdf"),
                 width="420mm", height="297mm", print_background=True)
        browser.close()
    if bad:
        print("넘침", len(bad), "건")
        for b in bad:
            print(" ", b)
        sys.exit(1)
    print("넘침 0건")


if __name__ == "__main__":
    lang = sys.argv[1] if len(sys.argv) > 1 else "ko"
    OUT.mkdir(exist_ok=True)
    render(build_html(lang), lang)
