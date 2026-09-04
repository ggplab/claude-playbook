# 7장 클로드 코드(CLI)로 조사팀 만들기

> 집필 진행 중 — 실습 자료는 출간에 맞춰 계속 업데이트됩니다.

## 실습 자료

| 항목 | 내용 |
|------|------|
| 유즈케이스 | 연말정산 준비 조사를 조사팀에게 맡기고, 결과를 공유용 카드로 받기 |
| 사용 기능 | 클로드 코드(CLI), 플랜 모드, 서브에이전트, 아티팩트, 스킬 설치, 상태줄 |
| 산출물 | 조사 계획서(`Plan.md`) · 조사팀 세 명 · 조사 보고서 · 아티팩트 · PDF · 공유용 카드 |

## 파일

| 파일 | 쓰임 |
|------|------|
| [`outputs/`](./outputs) | **7장을 완주해서 나온 산출물 기준본.** 따라 하다 막혔을 때 "제대로 나온 모양"을 확인한다 |
| [`Chap7_card-design-system.md`](./Chap7_card-design-system.md) | 카드가 메신저에서 실제로 읽히게 하는 최소 기준. 카드를 만들 때 클로드에게 함께 준다 |
| [`markdown-to-pdf`](../../02-skills/markdown-to-pdf/) | 마크다운을 PDF로 만드는 스킬. 보고서를 문서로 남길 때 쓴다 (스킬 모음에 있음) |
| [`card-news`](../../02-skills/card-news/) | 카드 디자인 기준을 코드로 고정한 카드뉴스 스킬. 카드를 손으로 만들지 않고 JSON 한 장으로 뽑을 때 쓴다 (스킬 모음에 있음) |
| [`Chap7_statusline_install.md`](./Chap7_statusline_install.md) | 상태줄 설치 안내와 안 뜰 때 점검 목록 |
| [`Chap7_statusline-command.sh`](./Chap7_statusline-command.sh) | 상태줄 스크립트 본체 |

## 스킬 설치하기

터미널에서 클로드 코드를 실행한 뒤 이렇게 요청하면 됩니다. 파일을 직접 옮길 필요는 없습니다.

### 7.4.1 보고서를 PDF로: `markdown-to-pdf`

```
아래 저장소의 markdown-to-pdf 스킬을 내 컴퓨터에 설치해줘.
https://github.com/ggplab/claude-playbook/tree/main/02-skills/markdown-to-pdf
- 필요한 패키지가 없으면 설치도 해줘
- 설치가 끝나면 스킬 목록에 보이는지 확인해줘
```

설치 후 스킬 목록에 `markdown-to-pdf`가 보이면 성공입니다.

> 이 스킬은 Node.js 18 이상이 필요하고, 첫 실행에서 브라우저 엔진을 내려받을 수 있습니다. 위 프롬프트처럼 "필요한 패키지가 없으면 설치도 해줘"를 함께 적으면 클로드가 알아서 처리합니다.

### 7.4.2 공유용 카드: `card-news`

```
아래 저장소의 card-news 스킬을 내 컴퓨터에 설치해줘.
https://github.com/ggplab/claude-playbook/tree/main/02-skills/card-news
- 설치가 끝나면 스킬 목록에 보이는지 확인해줘
```

설치 후 스킬 목록에 `card-news`가 보이면 성공입니다. Chrome만 있으면 되고 추가 패키지 설치는 없습니다.

> 이 스킬은 [`Chap7_card-design-system.md`](./Chap7_card-design-system.md)의 기준(글자 3단, 최소 32px, 항목 6개 이하)을 코드로 고정한 것입니다. 기준에 못 미치면 PNG를 만들지 않고 이유를 알려 줍니다. 스킬 없이 기준 문서만 클로드에게 주고 카드를 만들어도 됩니다. 두 방법 모두 책 본문에서 다룹니다.
