#!/usr/bin/env python3
"""예제: 인프런 챌린지 디스코드 채점봇 구조도 (blog: buildnwrite.com/blog/inflearn-challenge-grading-bot).

    python3 example/grading_bot.py   →  example/out/architecture.{drawio,png}
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
from drawio_kit import ACCENT, Diagram  # noqa: E402

DISCORD = "#5865F2"
d = Diagram(icons_dir=HERE / "icons", font="Pretendard")

d.title("인프런 챌린지 디스코드 채점봇 구조", 40, 20)
participant = d.actor("참여자", 120, 90)

d.container("Discord 서버 (입구)", "discord", 40, 230, 300, 190, stroke=DISCORD, fill="#f7f8ff")
welcome = d.logo_node("#welcome<br>/시작하기", "discord", 70, 280, 80)
week = d.logo_node("주차별 채널 6개<br>/피드백 (JSON 1개 첨부)", "discord", 200, 280, 80)

d.container("Supabase Edge Function (봇 본체 1개)", "supabase", 40, 490, 1120, 190)
verify = d.step("Ed25519 서명 검증<br>3초 안에 '처리 중' 응답", 70, 560, 200, 80)
redact = d.step("크리덴셜 마스킹<br>credentials, token, secret<br>→ [REDACTED]", 330, 560, 220, 80)
sim = d.step("유사도 계산 (책 원본 6개 내장)<br>노드 수 20% + 종류 30% + 설정값 50%", 610, 560, 260, 80)
tier = d.step("3갈래 판정<br>≥95% 인증만<br>70~95% AI<br>&lt;70% AI + 저자", 930, 540, 200, 120, shape="rhombus;")

sheets = d.logo_node("Google Sheets<br>신청자 명단", "googlesheets", 120, 770)
storage = d.logo_node("Supabase Storage<br>버킷 (마스킹 JSON)", "supabase", 390, 770)
gemini = d.logo_node("Gemini 2.5 Flash<br>(thinking 끔)", "googlegemini", 700, 770)

d.container("Discord 서버 (답글)", "discord", 880, 740, 280, 290, stroke=DISCORD, fill="#f7f8ff")
reply = d.logo_node("봇 답글<br>요약 + 제안 + @운영자 태그", "discord", 980, 800, 80)
thread = d.step("저자 스레드 코멘트", 920, 960, 200, 50, stroke=DISCORD)

d.edge(participant, welcome, "인프런 닉네임", exit_=(0.3, 1), entry=(0.5, 0), pos=-0.6, offset=(-44, 0))
d.edge(participant, week, "워크플로 .json", exit_=(0.7, 1), entry=(0.5, 0), pos=-0.6, offset=(48, 0))
d.edge(welcome, verify, "인증 요청", exit_=(0.5, 1), entry=(0.3, 0))
d.edge(week, verify, "슬래시 커맨드 (서명 포함)", exit_=(0.5, 1), entry=(0.7, 0))
d.edge(verify, redact)
d.edge(redact, sim)
d.edge(sim, tier)
d.edge(verify, sheets, "닉네임 대조 (읽기만, 5분 캐시)", exit_=(0.5, 1), entry=(0.5, 0))
d.edge(redact, storage, "저장 (운영 2주째 추가)", exit_=(0.5, 1), entry=(0.5, 0))
d.edge(tier, gemini, "95% 미만만 호출<br>요약, 제안 (JSON) 회신", both=True, exit_=(0.5, 1), entry=(0.5, 0),
       points=((1030, 720), (748, 720)), pos=0.1, offset=(0, -22))
d.edge(tier, reply, "follow-up 메시지", exit_=(0.5, 1), entry=(0.5, 0))
d.edge(reply, thread, "사람이 이어서", dashed=True, exit_=(0.5, 1), entry=(0.5, 0), pos=0.55, offset=(52, 0))

d.credit("© 2026 BuildnWrite. 자료: n8n-book-challenge 봇 소스 (2026-05 운영 기준)", 560, 1050)
d.render(HERE / "out" / "architecture.drawio", HERE / "out" / "architecture.png")
