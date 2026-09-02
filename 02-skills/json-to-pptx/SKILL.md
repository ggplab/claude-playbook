---
name: json-to-pptx
description: 업무용 발표 덱(.pptx)을 콘텐츠 JSON 한 파일에서 만든다. 표지, 간지, 불릿, 2열 비교, 표, KPI, 마무리 7가지 슬라이드 유형을 python-pptx로 그리고 발표자 노트까지 넣는다. "발표자료 만들어줘", "보고용 PPT", "주간 보고 덱", "이 내용을 슬라이드로", "pptx로 뽑아줘" 같은 요청에 사용. 문안 확정이 먼저이고 이 스킬은 문안을 pptx로 옮기는 단계만 담당한다. 디자인이 중요한 대외 제안서는 디자이너 템플릿을 쓰고 이 스킬은 내부 보고와 초안용이다.
argument-hint: "<content.json> [out.pptx]"
---

# json-to-pptx

콘텐츠 JSON 한 파일을 **편집 가능한 pptx**로 만든다. 문안과 구조는 JSON이 갖고, 모양은 스크립트가 갖는다. 사용자는 나온 pptx를 PowerPoint에서 손본다.

## 언제 쓰나

- 내부 보고, 주간 리뷰, 회의 자료처럼 **내용이 먼저이고 디자인은 깔끔하면 되는** 덱
- 같은 형식의 덱을 반복해서 만들 때 (매주 보고, 분기 리뷰)
- 클로드가 정리한 내용을 바로 슬라이드로 옮길 때

대외 제안서나 브랜드 덱은 디자이너 템플릿이 낫다. 이 스킬로 초안을 만든 뒤 옮겨도 된다.

## 절차

### 1. 문안을 먼저 확정한다

JSON을 쓰기 전에 사용자와 다음을 합의한다. 슬라이드를 만들고 나서 구조를 바꾸면 전부 다시 만든다.

| 물어볼 것 | 이유 |
|---|---|
| 청중과 자리 | 결정을 받는 자리인지 공유하는 자리인지에 따라 첫 장이 달라진다 |
| 결론 한 문장 | KPI 슬라이드의 `takeaway`와 마무리 슬라이드가 여기서 나온다 |
| 장 수 상한 | 내부 보고는 8~12장이 적당하다 |

### 2. JSON을 쓴다

`examples/quarterly-review.json`을 복사해 채운다. 구조는 이렇다.

```json
{
  "title": "덱 제목", "subtitle": "부제", "author": "발표자", "date": "2026-10-07",
  "footer": "푸터에 들어갈 짧은 문구",
  "theme": { "font": "Malgun Gothic", "accent": "#2563EB" },
  "slides": [ { "type": "cover" }, ... ]
}
```

슬라이드 유형 7종:

| type | 용도 | 주요 키 |
|---|---|---|
| `cover` | 표지 | title, subtitle (덱 메타에서 상속 가능) |
| `section` | 간지. 장이 바뀔 때 | number, title, subtitle |
| `bullets` | 불릿 목록. 6개 이하 | title, items (문자열 또는 `{text, sub[]}`), source |
| `two_column` | 비교. 잘된 것과 안 된 것, 현재와 제안 | title, columns[2] (`{heading, items, accent}`) |
| `table` | 표. 8행 이하 | title, header[], rows[][], widths[] (열 비율), source |
| `kpi` | 숫자 카드 4개 이하 | title, items (`{label, value, delta, accent}`), takeaway |
| `closing` | 마무리. 오늘 결정할 것 | title, items, contact |

모든 슬라이드에 `notes`를 넣으면 발표자 노트로 들어간다. **말할 내용은 notes에, 화면에는 읽을 내용만** 넣는다.

### 3. 만든다

```bash
python3 ~/.claude/skills/json-to-pptx/scripts/build_pptx.py content.json out.pptx
```

경고가 나오면 (불릿 7개 이상, 표 9행 이상, KPI 5개 이상) JSON을 나눠 다시 만든다. 스크립트는 경고만 내고 멈추지 않는다.

### 4. 확인한다

- 장 수가 JSON의 `slides` 개수와 같은지 출력 메시지로 확인한다.
- LibreOffice가 있으면 PDF로 변환해 넘겨 본다. 글자가 상자를 넘치면 문안을 줄인다. 글자 크기를 내리지 않는다.
- 배포본이 필요하면 `pptx-finalize` 스킬로 폰트 임베드와 PDF 변환을 한다.

## 모양을 바꾸고 싶을 때

| 바꿀 것 | 어디서 |
|---|---|
| 강조색, 폰트 | JSON의 `theme` 블록. 코드에 색을 넣지 않는다 |
| 글자 크기 | 스크립트 상단 `TYPE` 표. 이름(display, title, body 등)으로만 쓴다 |
| 새 슬라이드 유형 | 스크립트에 `slide_<이름>` 함수를 추가하고 `BUILDERS`에 등록한다 |

Mac에서 만들어 Windows로 보내면 폰트가 바뀔 수 있다. `theme.font`를 받는 쪽 기본 폰트(맑은 고딕)로 두거나 `pptx-finalize`로 PDF를 함께 보낸다.

## 의존성

```bash
pip install python-pptx
```
