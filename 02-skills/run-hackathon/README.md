# `run-hackathon`: 하루짜리 해커톤을 기획부터 제출까지 한 꾸러미로

> 2026-10-16 Google DeepMind AI Hackathon에서 저자 팀(앱 Watch Party Host)이 실제로 한 순서를 옮긴 스킬입니다. 수상하지는 못했고, 그래서 무엇이 모자랐는지가 회고 절에 그대로 있습니다. 후기 글: [같이보기에 늦게 온 시청자, AI가 '지금 무슨 상황이에요?'에 대신 답한다](https://buildnwrite.com/blog/watch-party-host-hackathon/)

같은 폴더의 [`SKILL.md`](./SKILL.md)가 그대로 복사해서 쓰는 본문이고, `scripts/`와 `examples/`가 함께 갑니다.

---

## 무엇을 해결하나

해커톤 하루는 짧고, 메인 세션 하나로 기획과 개발과 덱과 영상을 다 하면 마감 직전에 무엇이 남았는지 보이지 않습니다. 이 스킬은 하루를 **0. 규정과 마감 읽기, 1. 기획, 2. 개발, 3. 검증, 4. 영상 녹화, 5. 발표, 제출, 회고**로 나누고, 단계마다 맡는 세션과 "끝났다고 판정하는 명령이나 파일"을 둡니다. 세션끼리는 공유 노트 폴더로 결정을 주고받습니다.

### 한 줄 사용 예

```
[행사 이름] 해커톤 준비해줘. 마감과 심사 기준은 [행사 가이드 위치]에 있어
```

---

## 들어 있는 것

| 파일 | 역할 |
|---|---|
| `SKILL.md` | 0~5단계 절차, 세션 지도, 제출 체크리스트, 회고(이 스킬이 막으려는 실패 7가지와 수상작을 보고 깨달은 것) |
| `scripts/screentour.py` | 앱 화면 한 장에 빨간 박스와 말풍선을 얹어 덱의 "화면 둘러보기" 장표 PNG와 HTML 조각을 만든다 |
| `examples/watch-party.json` | 배포된 앱 주소로 캡처해 3장을 만드는 입력 예시 |
| `examples/watch-party-image.json`, `examples/watch-party-capture.png` | 저장한 캡처로 같은 3장을 다시 만드는 예시(행사 주소가 사라진 뒤용) |

---

## 따라 만들기

### 1. 폴더 복사

```bash
# 저장소를 받은 폴더에서(Claude Code 개인 전역)
mkdir -p ~/.claude/skills
cp -R 02-skills/run-hackathon ~/.claude/skills/run-hackathon
```

프로젝트 한정으로 쓰려면 `<프로젝트>/.claude/skills/run-hackathon`에 둡니다.

### 2. 저자 환경 값 바꾸기

`SKILL.md`의 다음 값이 저자 환경 기준입니다. 자기 행사와 장비에 맞게 고칩니다.

- 행사 자원: 계정 삭제 시각, 지급 크레딧, 클라우드 리전과 배포 명령(Cloud Run)
- 백업 장비: 저자는 맥미니 Docker와 Cloudflare Tunnel
- 공유 노트 폴더 위치와 파일 이름 규약
- 덱 디자인 토큰(`screentour.py` 상단 색상과 글꼴)

### 3. 화면 둘러보기 장표 뽑아 보기

```bash
cd ~/.claude/skills/run-hackathon
uv run --with playwright==1.56.0 python scripts/screentour.py examples/watch-party-image.json --out out/ --lang ko
```

`out/tour-01.png`부터 3장과 `out/tour.html`이 나오면 성공입니다. playwright 버전은 설치된 chromium 빌드에 맞춰야 하고, "Executable doesn't exist"가 나오면 `playwright install`을 실행합니다.

---

## 설계 포인트

- **모델 설계를 기획의 맨 앞에 둡니다.** 주최 측이 대표 모델을 내건 해커톤은 심사도 그 모델을 얼마나 제대로 썼는지를 봅니다. 기능보다 "그 모델이 아니면 안 되는 일"부터 정합니다.
- **결제 경로는 하나로 고정합니다.** 선불 API 키와 프로젝트 결제를 섞어 쓰다 키가 바닥나면 제출용 앱까지 멈춘 줄 알게 됩니다. 처음부터 프로젝트 결제(Vertex AI)로 잡습니다.
- **검증은 독립 단계입니다.** 측정하지 않은 주장은 덱에서 뺍니다.
- **첫 산출물은 "1분 안에 보여 줄 한 장면"입니다.** 심사위원은 사업 기획이 아니라 실제 입력으로 바로 도는 프로토타입을 봅니다. 수상작을 보고 얻은 결론이고, 회고 절에 있습니다.

---

← [스킬 모음으로 돌아가기](../README.md)
