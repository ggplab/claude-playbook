---
name: lecture-slide-make
description: 강의, 세미나, 사내 교육 슬라이드 덱(.pptx)을 콘텐츠 JSON 한 파일에서 만든다. 표지, 간지, 불릿, 2열, 표, 절차, 스크린샷, 정리, QR 연락처 슬라이드와 도식 프리셋 14종(두 패널, 층, 타임라인, 단계, 배치도, 카드, 허브, 분기, 포함, 벤, 매트릭스, 막대, 누적, KPI)을 python-pptx 네이티브 도형으로 그린다. "강의 슬라이드 만들어줘", "교육 자료 덱", "세미나 덱", "이 개념을 도식으로", "강의안을 슬라이드로" 같은 요청에 사용. 문안 확정이 먼저이고 도식은 결정 트리로 고른다. 디자인이 주인공인 대외 제안서나 브랜드 덱은 디자이너 템플릿이 낫고, 이 스킬은 내용이 먼저인 강의와 교육용이다.
argument-hint: "<content.json> [out.pptx] [--strict-assets]"
---

# lecture-slide-make

콘텐츠 JSON 한 파일을 **편집 가능한 pptx**로 만든다. 문안과 구조는 JSON이 갖고, 모양은 스크립트가 갖는다. 사용자는 나온 pptx를 PowerPoint에서 손본다.

참조 문서 3장은 이 스킬의 판단 기준이다. 해당 단계에서 읽는다.

| 문서 | 언제 읽나 |
|---|---|
| `references/decision-tree.md` | 3단계. 슬라이드 몸통을 무엇으로 채울지 고를 때 |
| `references/slide-anatomy.md` | 2단계와 5단계. 구성요소 이름, 타이포 계층, 표기 규칙, 마감 게이트 |
| `references/pipeline.md` | 사용자가 pptx에 손을 댄 뒤. 재생성 금지와 검수 루프 |

## 1. 구조를 먼저 확정한다

JSON을 쓰기 전에 사용자와 합의한다. 슬라이드를 만들고 나서 구조를 바꾸면 전부 다시 만든다.

| 물어볼 것 | 이유 |
|---|---|
| 청중과 자리 | 세미나룸이면 본문 글자만 20pt로 키운다 (`_meta.venue: "room"`). 라벨과 캡션은 그대로라 표와 도식 캡션이 빡빡해지면 문안을 줄인다 |
| 장르 | 강의와 컨설팅(`lecture`, 명사형 제목)인가 강연(`talk`, 완결문 훅)인가 |
| 장 수와 장별 질문 | 장마다 "이 장은 무엇에 답하는가" 한 줄. 20분에 10~14장이 적당하다 |

**첫 패스는 완성 덱이 아니다.** 덱 문법 3안 × 각 3장만 먼저 내고 하나를 고르게 한다. 완성본 30장을 받으면 반응이 "방향 수정"이 아니라 "전면 재작업"이 된다.

기본 골격은 **표지 → [간지 → 본문 장들] × N → 정리 → 연락처**다. 정리와 연락처 장은 묻지 않고 넣는다.

## 2. 문안을 JSON에 쓴다

`examples/lecture-sample.json`을 복사해 채운다. 최상위 키는 이렇다.

```json
{
  "title": "덱 제목",
  "copyright": "© 2026 Your Name. All rights reserved.",
  "font": "Noto Sans KR",
  "theme": "blue-slate",
  "_meta": { "genre": "lecture", "venue": "room", "density": { "words_per_slide_max": 40 } },
  "slides": [ { "type": "cover", "..." : "..." } ]
}
```

슬라이드 유형 11종:

| type | 용도 | 주요 키 |
|---|---|---|
| `cover` | 표지 | event, meta, title, speaker |
| `divider` | 간지. 장이 바뀔 때 | label(`[이론]` 같은 대괄호 접두), title, sub |
| `bullets` | 불릿 3~6개 | title, lead, items, note |
| `split` | 2열 대구. AS-IS/TO-BE, 문제/해결 | title, columns[2] (`{label, items}`) |
| `table` | 비교표. 속성 축 3개 이상 | title, header[], rows[][], widths[] |
| `process` | 순서 있는 단계를 가로로 | title, nodes[], input, output |
| `steps` | 실습 절차. 숫자 리스트 | title, items (`{name, desc}`) |
| `figure` | 도식. 프리셋 14종 | title, figure (`{preset, layout, ...}`) |
| `shot` | 스크린샷. side / top / pair | title, shot (`{shot_id, shot_desc, label, points}`) |
| `recap` | 정리. 번호 붙인 핵심 문장 | title, items, handoff |
| `contacts` | QR 가로 나열 | title, items (`{shot_id, label, sub}`) |

모든 슬라이드에 `notes`를 넣으면 발표자 노트로 들어간다. **말할 내용은 notes에, 화면에는 읽을 내용만** 쓴다.

문안 규칙은 `references/slide-anatomy.md`의 표기 치트시트를 따른다. 요약하면 이렇다.

- 제목은 짧은 명사 한 단. 서술형 문장 제목은 쓰지 않는다.
- 불릿은 ~함 / ~음 / 명사로 끝낸다. 장당 3~6개.
- 가운데점(·), em dash(—), `->`는 쓰지 않는다. 화살표는 `→`.
- "손에 쥐는 것", "함께 알아봅시다" 같은 AI 말투를 쓰지 않는다.

## 3. 시각 요소를 고른다

장마다 몸통을 무엇으로 채울지 `references/decision-tree.md`의 세 질문으로 판정한다.

1. 실물을 봐야 아는가 → `shot` 또는 `table`
2. 뼈대 관계는 무엇인가 → 순서, 포함, 분배, 분기, 병렬, 위치, 양 중 하나면 그 프리셋
3. 대비라면 형태는 무엇인가 → 축 두 개면 `matrix`, 시점별이면 `timeline`, 좌우 구조가 다르면 `two_panel`, 속성이 많으면 `table`

어느 갈래에도 안 걸리면 `bullets`다. 불릿은 폴백이지 기본값이 아니다. 프리셋별 JSON 키는 `examples/preset-catalog.json`에 14종 실물이 있으니 그 장을 복사해 값만 바꾼다.

## 4. 만든다

```bash
python3 ~/.claude/skills/lecture-slide-make/scripts/build_deck.py content.json out.pptx
```

- 스크린샷은 JSON 옆 `assets/shots/<shot_id>.png`를 읽는다. 없으면 점선 빈 슬롯으로 나가고 미수집 목록을 stderr에 찍는다. 마감 직전에는 `--strict-assets`로 돌려 0건을 확인한다.
- 장당 어절이 `density.words_per_slide_max`를 넘으면 경고한다. 글자를 줄이지 말고 장을 나눈다.
- 글자 크기는 스크립트 상단 `TYPE` 표의 이름으로만 쓴다. 숫자를 직접 넣지 않는다.
- 색은 `themes/<이름>.json`이 갖는다. `blue-slate`(파랑 + 슬레이트 회색)와 `ink-neutral`(검정 + 회색) 두 가지. 회사 색은 테마 파일을 복사해 이름을 새로 짓는다.
- Windows에서 열 파일이면 `"font": "Malgun Gothic"`으로 두는 편이 안전하다.

## 5. 마감 게이트

실패한 채 다음 단계로 넘어가지 않는다.

```bash
# G1 렌더: PDF로 변환해 넘침과 겹침을 눈으로 본다
soffice --headless --convert-to pdf out.pptx

# G2 기계 린트: 금지 문자와 AI 말투 0건
unzip -p out.pptx "ppt/slides/slide*.xml" | grep -oP '(?<=<a:t>)[^<]+' > /tmp/deck-text.txt
grep -cP "[\x{2014}\x{00B7}]|->" /tmp/deck-text.txt
grep -nE "손에 (쥐|남)|함께 알아봅시다|살펴보겠습니다" /tmp/deck-text.txt
```

- **G3 판단 검수**: placeholder 미교체, 서술형 제목, 위계 역전, 오탈자는 grep으로 못 잡는다. 덱을 만든 대화가 아닌 **새 대화**에 PDF를 넘겨 검수받는다.
- **G4 사람 최종**: 렌더 PDF와 검수 보고를 함께 보고 확인한다.

PDF 변환은 G1이 곧 배포본이다. 받는 쪽 PC에 같은 폰트가 없으면 pptx 대신 PDF를 보낸다.

## 사용자가 pptx에 손을 댄 뒤

**그 pptx가 정본이다.** JSON에서 다시 뽑지 않는다. 손으로 붙인 스크린샷과 제목 손질이 전부 사라진다. 검수 결과는 "슬라이드 번호 + 무엇을 어떻게" 지시서로 내고 사용자가 손본다. 손질본과 생성본의 차이는 대조 스크립트로 잰다.

```bash
python3 ~/.claude/skills/lecture-slide-make/scripts/compare_deck.py 생성본.pptx 손질본.pptx
```

결과 읽는 법은 `references/pipeline.md`에 있다. 반영할 곳은 문서가 아니라 생성기와 JSON 기본값이다.

## 모양을 바꾸고 싶을 때

| 바꿀 것 | 어디서 |
|---|---|
| 강조색, 회색 | `themes/<이름>.json`. 코드에 색을 넣지 않는다 |
| 폰트 | JSON 최상위 `font` |
| 글자 크기 | 스크립트 상단 `TYPE` 표. 이름으로만 쓴다 |
| 새 슬라이드 유형 | `talk_<이름>` 함수를 추가하고 `TALK_SLIDES`에 등록 |
| 새 도식 프리셋 | `_fig_<이름>` 함수를 추가하고 `FIGURES`에 등록 |

## 의존성

```bash
pip install python-pptx pillow
```

Pillow는 글자 폭을 재는 데 쓰며 없어도 돌아간다. PDF 변환에는 LibreOffice가 필요하다.
