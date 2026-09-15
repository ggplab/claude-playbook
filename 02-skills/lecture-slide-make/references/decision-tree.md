# 시각 요소 결정 트리

슬라이드 한 장의 몸통을 무엇으로 채울지 고르는 세 가지 질문이다. 위에서 아래로 내려가며 처음 "예"가 나오는 곳에서 멈춘다.

![시각 요소 결정 트리](../assets/decision-tree.png)

## 세 가지 질문

| 질문 | 답 | 슬라이드 유형 |
|---|---|---|
| **Q1. 실물을 봐야 아는가** (매체 판정) | 화면을 봐야 안다 | `shot` |
| | 텍스트 실물을 나란히 봐야 한다 | `table` |
| **Q2. 뼈대 관계는 무엇인가** (여덟 갈래, 서로 배타적) | 대비. A와 B가 다르다 | Q3으로 |
| | 순서. A 다음 B | `figure` / `stages` |
| | 포함. A 안에 B | `figure` / `layers` 또는 `nested` |
| | 분배. 하나가 여럿에 | `figure` / `hub` |
| | 분기. 조건에 따라 | `figure` / `branch` |
| | 병렬. 동등한 N개 | `figure` / `cards` |
| | 위치. 무엇이 어디에 | `figure` / `placemap` |
| | 양. 크기 차이 | `figure` / `bars` |
| **Q3. 대비의 형태는 무엇인가** (Q2에서 대비로 온 경우에만) | 판단 축이 두 개다 | `figure` / `matrix` |
| | 시점별로 다르다 | `figure` / `timeline` |
| | 좌우가 다른 구조로 돈다 | `figure` / `two_panel` |
| | 속성 축이 3개 이상 | `table` |

어느 갈래에도 안 걸리면 `bullets`다. 불릿은 폴백이지 기본값이 아니다.

## 도식 프리셋 14종

`figure` 유형 슬라이드의 `figure.preset` 값이다. 전부 python-pptx 네이티브 도형이라 pptx 안에서 그대로 편집된다. 각 프리셋의 JSON 키는 `examples/preset-catalog.json`에 실물이 있다.

| 프리셋 | 관계 | 언제 쓰나 | 규칙과 한도 |
|---|---|---|---|
| `two_panel` | 대비 | 좌우가 서로 다른 흐름으로 돈다 | `arrows: true`는 순서가 있을 때만. 없는 흐름을 만들지 않는다 |
| `layers` | 포함 | 층마다 성질이 다르다 | 잠기거나 달라지는 층만 `accent` |
| `timeline` | 대비 | 같은 시점들에 무엇이 실행되고 무엇이 빠지나 | 빈 점이 곧 누락 |
| `stages` | 순서 | 좌에서 우로 흐른다 | `loop`는 마지막에서 처음으로 되돌아갈 때, `taper`는 단마다 좁아질 때 |
| `placemap` | 위치 | 한 화면 안에서 무엇이 어디 놓이나 | 프레임 라벨이 곧 은유 |
| `cards` | 병렬 | 동등한 항목 N개 | 어느 하나가 앞서지 않는 나열. `per_row`로 줄 수 조절 |
| `hub` | 분배 | 중심 하나가 여러 곳에 걸린다 | spoke 4개 이하 |
| `branch` | 분기 | 조건 하나로 길이 갈린다 | `condition` 한 줄, 가지 2~3개 |
| `nested` | 포함 | 바깥에서 안으로 좁혀 들어간다 | 완전 포함일 때만. 일부만 겹치면 `venn` |
| `venn` | 포함 | 겹치는 집합 | 원 2개 또는 3개. `overlap`이 교집합 라벨 |
| `matrix` | 대비 | 판단 축이 두 개다 | 강조 칸 하나만 `accent` |
| `bars` | 양 | 수치 비교 | 8행 이하 내림차순. 숫자는 출처 있는 것만. 초점 1행만 `accent` |
| `area` | 양 | 구성비가 시간으로 변한다 | 누적 시리즈 3개까지. y축은 0부터 |
| `kpi` | 양 | 핵심 숫자 몇 개의 요약 | 카드 3장까지. 방향은 색이 아니라 ▲▼ 글리프. 델타엔 비교 기준(`basis`) 필수 |

### 프리셋 실물

| | | |
|---|---|---|
| ![two_panel arrows](../assets/presets/01-two_panel-arrows-true.webp) `two_panel` arrows: true | ![two_panel](../assets/presets/02-two_panel-arrows-false.webp) `two_panel` arrows: false | ![layers](../assets/presets/03-layers.webp) `layers` |
| ![timeline](../assets/presets/04-timeline.webp) `timeline` | ![stages loop](../assets/presets/05-stages-loop.webp) `stages` loop | ![stages taper](../assets/presets/06-stages-taper.webp) `stages` taper |
| ![placemap](../assets/presets/07-placemap.webp) `placemap` | ![cards](../assets/presets/08-cards.webp) `cards` | ![hub](../assets/presets/09-hub.webp) `hub` |
| ![branch](../assets/presets/10-branch.webp) `branch` | ![nested](../assets/presets/11-nested.webp) `nested` | ![matrix](../assets/presets/12-matrix.webp) `matrix` |
| ![bars](../assets/presets/13-bars.webp) `bars` | ![area](../assets/presets/17-area.png) `area` | ![kpi](../assets/presets/18-kpi.png) `kpi` |
| ![venn](../assets/presets/19-venn.png) `venn` | | |

## 배치 3종

도식이 슬라이드 안에서 차지하는 자리다. `figure.layout` 값으로 고른다.

| 값 | 배치 | 언제 |
|---|---|---|
| `full` | 도식이 전폭 | 기본값 |
| `split` | 좌 도식 + 우 설명(`aside`) | 도식이 못 담는 것만 오른쪽에 글로. `ratio`로 좌우 비율 |
| `stack` | 상 도식 + 하 설명 | 도식이 가로로 길 때. `timeline`, `stages`, `bars`, `area`, `kpi`가 여기 해당 |

| | | |
|---|---|---|
| ![full](../assets/presets/14-layout-full.webp) `layout: full` | ![split](../assets/presets/15-layout-split.webp) `layout: split` | ![stack](../assets/presets/16-layout-stack.webp) `layout: stack` |

## 그리지 말아야 할 것

- 글 한 문단이면 충분한 것을 "예쁘게" 그리려고 도식을 만들지 않는다.
- 한 장에 도식은 하나다. 둘이 필요하면 핵심이 둘이라는 뜻이니 장을 나눈다.
- 비교 항목이 많으면 도식보다 표가 낫다. Q3의 마지막 가지가 그 자리다.
