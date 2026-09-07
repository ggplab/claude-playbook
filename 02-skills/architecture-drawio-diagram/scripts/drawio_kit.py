#!/usr/bin/env python3
"""drawio_kit: 서비스 로고가 큼직한 아키텍처 구조도를 코드로 그려 draw.io 파일과 PNG로 뽑는다.

배치 스크립트는 이 모듈만 import 해서 20~40줄로 끝난다:

    from drawio_kit import Diagram
    d = Diagram(icons_dir="icons", font="Pretendard")
    d.title("서비스 구조", 40, 20)
    api = d.container("API 서버", "supabase", 40, 100, 600, 180)
    a = d.step("요청 검증", 70, 160, 200, 70)
    b = d.step("DB 저장", 330, 160, 200, 70)
    d.edge(a, b, "검증 통과")
    db = d.logo_node("Google Sheets", "googlesheets", 120, 360)
    d.edge(a, db, "읽기", exit_=(0.5, 1), entry=(0.5, 0))
    d.credit("© 2026 BuildnWrite", 560, 480)
    d.render("out/service.drawio", "out/service.png")

좌표는 px. 컨테이너 안에 단계 상자를 두고, 외부 서비스는 큰 로고 노드로 둔다.
로고는 icons_dir 안의 <슬러그>.png 를 base64로 내장한다 (draw.io CLI가 외부 파일 경로를 못 읽는다).
렌더는 draw.io 데스크톱 CLI (`draw.io -x -f png -s 2`) 를 쓰고, 결과를 폭 1200·256색으로 줄인다.
draw.io 경로는 환경변수 DRAWIO_BIN 으로 덮어쓸 수 있다.
"""
from __future__ import annotations

import base64
import os
import platform
import shutil
import subprocess
from pathlib import Path
from xml.sax.saxutils import escape

INK, MUTED, ACCENT = "#1a1a1a", "#6b6b6b", "#2b4ac6"


def find_drawio() -> str:
    env = os.environ.get("DRAWIO_BIN")
    if env and Path(env).exists():
        return env
    candidates = {
        "Darwin": ["/Applications/draw.io.app/Contents/MacOS/draw.io"],
        "Windows": [r"C:\Program Files\draw.io\draw.io.exe", os.path.expandvars(r"%LOCALAPPDATA%\Programs\draw.io\draw.io.exe")],
        "Linux": ["/usr/bin/drawio", "/opt/drawio/drawio", "/snap/bin/drawio"],
    }.get(platform.system(), [])
    for c in candidates:
        if Path(c).exists():
            return c
    for name in ("drawio", "draw.io"):
        p = shutil.which(name)
        if p:
            return p
    raise FileNotFoundError(
        "draw.io 데스크톱을 찾지 못했다. https://github.com/jgraph/drawio-desktop/releases 에서 설치하거나 DRAWIO_BIN 을 지정한다."
    )


class Diagram:
    def __init__(self, icons_dir: str | Path = "icons", font: str = "Pretendard", background: str = "#ffffff"):
        self.icons = Path(icons_dir)
        self.font = font
        self.background = background
        self.cells: list[str] = []
        self._n = 1

    # ---- 저수준 ----
    def _id(self) -> str:
        self._n += 1
        return f"c{self._n}"

    def data_uri(self, name: str) -> str:
        p = self.icons / f"{name}.png"
        if not p.exists():
            raise FileNotFoundError(f"로고 없음: {p} (CC0 로고를 {self.icons}/ 에 <슬러그>.png 로 둔다)")
        return "data:image/png," + base64.b64encode(p.read_bytes()).decode()

    def vertex(self, value: str, style: str, x, y, w, h, parent: str = "1") -> str:
        i = self._id()
        self.cells.append(
            f'<mxCell id="{i}" value="{escape(value)}" style="{style}" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
        )
        return i

    def edge(self, src: str, dst: str, label: str = "", *, dashed=False, both=False,
             exit_=None, entry=None, pos: float = 0.0, offset=(0, 0), points=(), color="#8a8a8a") -> None:
        """src→dst 화살표. exit_/entry 는 (x, y) 0~1 비율. pos 는 라벨 위치(-1~1), points 는 꺾임점."""
        i = self._id()
        style = (
            f"edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeColor={color};strokeWidth=1.6;"
            f"fontFamily={self.font};fontSize=12;fontColor={MUTED};labelBackgroundColor={self.background};"
            + ("dashed=1;" if dashed else "")
            + ("startArrow=classic;startFill=1;" if both else "")
            + (f"exitX={exit_[0]};exitY={exit_[1]};exitDx=0;exitDy=0;" if exit_ else "")
            + (f"entryX={entry[0]};entryY={entry[1]};entryDx=0;entryDy=0;" if entry else "")
        )
        pts = "".join(f'<mxPoint x="{px}" y="{py}"/>' for px, py in points)
        self.cells.append(
            f'<mxCell id="{i}" value="{escape(label)}" style="{style}" edge="1" parent="1" source="{src}" target="{dst}">'
            f'<mxGeometry x="{pos}" relative="1" as="geometry"><mxPoint x="{offset[0]}" y="{offset[1]}" as="offset"/>'
            + (f'<Array as="points">{pts}</Array>' if points else "")
            + "</mxGeometry></mxCell>"
        )

    # ---- 고수준 (참고 스타일 문법) ----
    def title(self, text: str, x, y, w=700, h=44, size=26) -> str:
        return self.vertex(text, f"text;html=1;align=left;verticalAlign=middle;fontFamily={self.font};fontSize={size};fontStyle=1;fontColor={INK};", x, y, w, h)

    def credit(self, text: str, x, y, w=600, h=30) -> str:
        return self.vertex(text, f"text;html=1;align=right;verticalAlign=middle;fontFamily={self.font};fontSize=12;fontColor={MUTED};", x, y, w, h)

    def actor(self, label: str, x, y, size=80) -> str:
        return self.vertex(label, f"ellipse;whiteSpace=wrap;html=1;aspect=fixed;fillColor=#f6f5f4;strokeColor={MUTED};fontFamily={self.font};fontSize=14;", x, y, size, size)

    def container(self, title: str, logo: str, x, y, w, h, stroke=ACCENT, fill="#eef1fb") -> str:
        """둥근 컨테이너 + 좌상단 작은 로고 + 제목. 안에 step 들을 배치한다."""
        i = self.vertex("", f"rounded=1;arcSize=6;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};strokeWidth=2;", x, y, w, h)
        self.vertex("", f"shape=image;imageAspect=1;image={self.data_uri(logo)};", x + 16, y + 12, 32, 32)
        self.vertex(title, f"text;html=1;align=left;verticalAlign=middle;fontFamily={self.font};fontSize=16;fontStyle=1;fontColor={INK};", x + 56, y + 8, w - 72, 40)
        return i

    def logo_node(self, label: str, logo: str, x, y, size=96) -> str:
        """큰 로고 + 아래 라벨. 외부 서비스·저장소에 쓴다."""
        return self.vertex(
            label,
            f"shape=image;imageAspect=1;image={self.data_uri(logo)};verticalLabelPosition=bottom;verticalAlign=top;"
            f"labelPosition=center;align=center;html=1;fontFamily={self.font};fontSize=14;fontColor={INK};spacingTop=6;",
            x, y, size, size,
        )

    def step(self, label: str, x, y, w, h, stroke=ACCENT, shape="") -> str:
        """컨테이너 안 처리 단계. shape='rhombus;' 를 주면 분기."""
        return self.vertex(
            label,
            f"{shape}rounded=1;arcSize=14;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor={stroke};strokeWidth=1.4;"
            f"fontFamily={self.font};fontSize=14;fontColor={INK};",
            x, y, w, h,
        )

    # ---- 출력 ----
    def xml(self, name: str = "architecture") -> str:
        return (
            f'<mxfile><diagram name="{name}" id="arch"><mxGraphModel grid="0" background="{self.background}">'
            '<root><mxCell id="0"/><mxCell id="1" parent="0"/>' + "".join(self.cells) + "</root></mxGraphModel></diagram></mxfile>"
        )

    def render(self, drawio_path: str | Path, png_path: str | Path | None = None, *, width: int = 1200, colors: int = 256, scale: int = 2) -> Path:
        drawio_path = Path(drawio_path)
        drawio_path.parent.mkdir(parents=True, exist_ok=True)
        drawio_path.write_text(self.xml(), encoding="utf-8")
        print("wrote", drawio_path, drawio_path.stat().st_size // 1024, "KB")
        if png_path is None:
            return drawio_path
        png_path = Path(png_path)
        png_path.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run([find_drawio(), "-x", "-f", "png", "-s", str(scale), "-b", "24", "-o", str(png_path), str(drawio_path)],
                           capture_output=True, text=True)
        if r.returncode != 0 or not png_path.exists():
            raise RuntimeError(f"draw.io 내보내기 실패: {r.stderr.strip()[-400:]}")
        try:
            from PIL import Image
        except ImportError:
            print("pillow 없음: 원본 크기 PNG 그대로 둔다 (pip install pillow 로 폭 축소·256색 적용)")
            return png_path
        im = Image.open(png_path).convert("RGB")
        if im.width > width:
            im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        im.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG).save(png_path, optimize=True)
        print("png", png_path, im.size, png_path.stat().st_size // 1024, "KB")
        return png_path
