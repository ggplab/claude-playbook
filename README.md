# Claude Playbook

한빛미디어 〈클로드가 다 해줌〉(가제) 책 실습 자료와 클로드 스킬·자동화 레시피를 함께 제공합니다.

#Claude #ClaudeCode #ClaudeDesktop #Automation #NoCode #AI

---

## 📚 책 실습 가이드 — 〈클로드가 다 해줌〉(가제)

- 저자: 임정
- **2026년 10월 출간 예정** (한빛미디어)
- 코딩을 모르는 직장인을 위한 노코드 관점의 클로드 자동화 실습서. 〈n8n이 다 해줌〉 후속작

> 집필 진행 중입니다. 각 장의 실습 자료는 출간에 맞춰 채워집니다.

| 장 / Ch. | 유즈케이스 / Use case | 주요 기능 / Features | 링크 / Link |
|----|-----------|------------|------|
| 2장 | 회의 아젠다 만들기 | 프로젝트, 아티팩트, 웹 검색, 프로젝트 지침 | [바로가기](./01-hanbit-claude-guidebook/chap2/) |
| 3장 | 흩어진 파일을 하나의 리포트로 | _업데이트 예정_ | [바로가기](./01-hanbit-claude-guidebook/chap3/) |
| 4장 | 리서치 자동화와 주식 리포트 | 코워크, 커넥터, 예약 작업, 스킬 | [바로가기](./01-hanbit-claude-guidebook/chap4/) |
| 5장 | 컴퓨터를 꺼도 도는 주가 수집기 | 앱스 스크립트, 구글 시트, PRD, 스킬 재사용 | [바로가기](./01-hanbit-claude-guidebook/chap5/) |
| 6장 | 우리 동네 실거래가 대시보드 배포 | 클로드 코드, CLAUDE.md, 깃허브 Pages | [바로가기](./01-hanbit-claude-guidebook/chap6/) |
| 7장 | 슬라이드 덱과 나만의 디자인 시스템 | 클로드 디자인, DESIGN.md | [바로가기](./01-hanbit-claude-guidebook/chap7/) |
| 8장 | 연말정산 조사팀 만들기 | 클로드 코드(CLI), 플랜 모드, 서브에이전트, 아티팩트 | [바로가기](./01-hanbit-claude-guidebook/chap8/) |
| 9장 | 알아서 쌓이는 업무일지 | 훅(Hooks), 깃허브 액션, 디스코드 웹훅 | [바로가기](./01-hanbit-claude-guidebook/chap9/) |

### 장별 기준 자료

따라 하다 막혔을 때 "제대로 나온 모양"을 확인하는 자료입니다.

| 자료 / Resource | 설명 / Description | 링크 / Link |
|------|------|------|
| 8장 산출물 기준본 | 조사 계획서 · 조사팀 셋 · 보고서 · PDF · 공유 카드 | [바로가기](./01-hanbit-claude-guidebook/chap8/outputs/) |
| 8장 카드 디자인 기준 | 카드가 메신저에서 실제로 읽히게 하는 최소 기준 | [바로가기](./01-hanbit-claude-guidebook/chap8/Chap8_card-design-system.md) |
| 8장 상태줄 | 터미널 하단에 모델·비용·사용량 게이지를 띄우는 스크립트와 설치 안내 | [바로가기](./01-hanbit-claude-guidebook/chap8/Chap8_statusline_install.md) |
| 9장 업무일지 형식 | 세션 종료 훅이 기록하는 형식. 훅을 걸 때 클로드에게 함께 준다 | [바로가기](./01-hanbit-claude-guidebook/chap9/WORKLOG_FORMAT.md) |
| 9장 산출물 기준본 | 계획서 · 훅 스크립트 · 주간 요약 · 워크플로 · 대시보드 | [바로가기](./01-hanbit-claude-guidebook/chap9/outputs/) |

---

## 🧩 스킬 모음

**스킬(Skill)** 은 반복되는 작업 절차를 한 번 정의해 두면, 필요할 때 클로드가 알아서 꺼내 쓰는 기능입니다.

| 스킬 / Skill | 한 줄 / Description | 링크 / Link |
|------|------|------|
| `/new-project` | 새 프로젝트를 일관된 네이밍·git 셋업으로 시작 | [바로가기](./02-skills/new-project/) |
| `korean-writing-style` | 보고서·메일·발표자료의 AI 말투와 번역투 제거 | [바로가기](./02-skills/korean-writing-style/) |
| `meeting-agenda` | 결정과 액션이 한 눈에 보이는 회의 아젠다 3종 | [바로가기](./02-skills/meeting-agenda/) |
| `json-to-pptx` | 문안 JSON 한 장으로 보고용 덱 생성 (python-pptx) | [바로가기](./02-skills/json-to-pptx/) |
| `pptx-finalize` | PPT 폰트 임베드 → PDF, 한글 폰트 깨짐 예방 | [바로가기](./02-skills/pptx-finalize/) |
| `markdown-to-pdf` | 마크다운 보고서를 표·코드 블록 그대로 PDF로 변환 (8장 실습) | [바로가기](./02-skills/markdown-to-pdf/) |
| `card-news` | JSON 한 장으로 휴대폰에서 읽히는 카드뉴스 PNG 덱 생성 (8장 실습) | [바로가기](./02-skills/card-news/) |
| `architecture-drawio-diagram` | 로고 큼직한 시스템 구조도를 코드로. draw.io 파일 + PNG, 없으면 Mermaid | [바로가기](./02-skills/architecture-drawio-diagram/) |
| 스킬 모음 전체 | 스킬 구조·설치 위치 설명 포함 | [바로가기](./02-skills/) |

### 외부 스킬 모음집

| 모음집 / Collection | 설명 / Description | 링크 / Link |
|------|------|------|
| k-skill | 한국 서비스용 스킬 100여 개 — SRT·KTX 예매, 카카오톡, 주식, 부동산, 정부 민원 | [바로가기](https://github.com/NomaDamas/k-skill) |
| 클로드 기본 탑재 | Word · PDF · PowerPoint · Excel — 설치 없이 말로 시키면 동작 | — |

---

## 🚀 클로드 시작하기

| 단계 / Step | 할 일 / Action | 비고 / Note |
|------|------|------|
| 1. 계정 만들기 | [claude.ai](https://claude.ai) 접속 → 구글 또는 이메일로 가입 | 무료로 시작 가능 |
| 2. 데스크톱 앱 설치 | [claude.ai/download](https://claude.ai/download) | 이 책 실습은 데스크톱 앱 기준 |
| 3. 로그인 | 설치한 앱에서 같은 계정으로 로그인 | — |
| 4. 첫 대화 | 입력창에 한국어로 질문을 적고 엔터 | 명령어 외울 필요 없음 |
| 5. (선택) 플랜 올리기 | 더 많이 쓰려면 Pro 구독 | 아래 플랜 표 참고 |
| 6. (심화) 터미널 | [Claude Code](https://claude.com/claude-code) 설치 | 8장부터 사용 |

---

## 💳 플랜 한눈에

| 플랜 / Plan | 월 요금 / Price | 한 줄 / Description |
|------|--------|------|
| **Free** | $0 | 가볍게 체험해 보기 |
| **Pro** | $20 / 월 (연 $200) | 일상 업무용 — 대부분 여기서 충분 |
| **Max** | $100 (5×) ~ $200 (20×) | 하루 종일 헤비하게 쓰는 사람 |

> 2026년 5월 기준이며 변동될 수 있습니다. 최신 정보는 [claude.com/pricing](https://claude.com/pricing).

---

## 📑 기능 인덱스

아래로 갈수록 자동화에 가깝습니다.

### 기본 — 대화하며 바로 쓰는 것

| 기능 / Feature | 한 줄 / Description |
|------|------|
| 프로젝트(Projects) | 관련 대화·파일·지침을 한 공간에 묶어 맥락 유지 |
| 아티팩트(Artifacts) | 문서·코드·HTML을 대화 옆 캔버스로 만들고 바로 편집 |
| 메모리(Memory) | 이전 대화의 맥락을 기억해 이어서 활용 |
| 파일 첨부·입출력 | PDF·이미지·문서·스프레드시트 올리고 결과물로 내려받기 |
| 음성 모드(Voice Mode) | 말로 입력하고 음성으로 대화 |
| 웹 검색(Web Search) | 최신 정보를 실시간으로 찾아 답변에 반영 |

### 연결·확장 — 외부 도구와 잇기

| 기능 / Feature | 한 줄 / Description |
|------|------|
| MCP 커넥터 | Google Drive·Sheets·Notion 등 외부 서비스 연결 |
| 스킬(Skills) | 반복 작업 절차를 자산으로 만들어 자동 호출 |
| 코드 실행 | 파이썬·Node 샌드박스에서 코드를 직접 실행 |

### 자동화·자율 실행 — 더 나아가면

| 기능 / Feature | 한 줄 / Description |
|------|------|
| Cowork | 데스크톱에서 멀티스텝 작업을 자율 실행 (권한 준 폴더 한정) |
| Routines | cron·API·GitHub 트리거로 클라우드에서 자율 실행 |
| Hooks | 정해진 순간에 반드시 실행되는 자동 동작 |
| Computer Use | 마우스·키보드·화면을 직접 조작 (리서치 프리뷰) |
| Claude Code | 터미널·웹에서 코드베이스를 직접 다루는 CLI 에이전트 |

> 기능과 플랜별 제공 범위는 자주 바뀝니다. 최신 정보는 [공식 문서](https://support.claude.com).

---

## 🛠️ CLI·외부 도구

| 도구 / Tool | 설명 / Description | 링크 / Link |
|------|------|------|
| Claude Code | Anthropic 공식 CLI 에이전트. Pro·Max 구독으로 사용 가능 | [바로가기](https://claude.com/claude-code) |
| 기타 코딩 에이전트 | Codex, OpenCode 등 — k-skill이 함께 동작 | — |
| MCP 커넥터 | Notion·Supabase·Playwright 등을 한 흐름으로 연결 | [바로가기](https://modelcontextprotocol.io) |

---

## 🙌 기여자

> Organized by 임정(지지플랩)

- 임정 @ 지지플랩 · [LinkedIn](https://www.linkedin.com/in/jayjunglim/) · [블로그](https://snowgot.tistory.com)
