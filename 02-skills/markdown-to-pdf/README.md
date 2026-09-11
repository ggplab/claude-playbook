# `markdown-to-pdf`: 클로드가 쓴 마크다운 보고서를 그대로 PDF로 만드는 스킬

> 클로드가 만든 `report.md`를 메일에 첨부하려면 PDF가 필요합니다. 워드로 열어 저장하면 표와 코드
> 블록이 흐트러집니다. 이 스킬은 마크다운을 그대로 PDF로 찍습니다. 8장 실습에서 씁니다.

같은 폴더의 [`SKILL.md`](./SKILL.md), [`scripts/`](./scripts), [`assets/`](./assets), [`package.json`](./package.json)을
그대로 복사해서 씁니다.

---

## 무엇을 해결하나

| 상황 | 이 스킬 |
|---|---|
| 마크다운 표가 워드에서 깨진다 | 브라우저 엔진으로 렌더링해 표 테두리와 줄무늬가 그대로 남는다 |
| 코드 블록이 회색 상자 없이 나온다 | 구문 강조와 배경색이 붙는다 |
| 한글이 네모로 깨진다 | 시스템 한글 폰트를 쓰고, CSS로 폰트를 바꿀 수 있다 |
| 매번 스타일을 다시 정한다 | 기본 스타일이 내장돼 있고 `--css`로 내 스타일을 덮어쓴다 |

### 한 줄 사용 예

```
report.md를 PDF로 만들어줘. 출처 목록까지 들어가야 해.
```

클로드가 스킬을 꺼내 이렇게 실행합니다.

```bash
node ~/.claude/skills/markdown-to-pdf/scripts/convert.cjs --input report.md --output report.pdf
```

성공하면 JSON 한 줄로 결과를 돌려줍니다.

```json
{ "success": true, "input": "report.md", "output": "report.pdf", "pages": 3 }
```

---

## 스킬 파일 해부

| 파일 | 역할 |
|---|---|
| `SKILL.md` | 클로드에게 주는 사용법. 옵션 표와 문제 해결 |
| `scripts/convert.cjs` | 명령줄 진입점. 옵션을 읽고 변환을 호출한다 |
| `scripts/lib/converter.cjs` | `md-to-pdf`로 실제 변환 |
| `scripts/lib/chrome-finder.cjs` | 설치된 Chrome을 찾아 쓴다. 없으면 Chromium을 내려받는다 |
| `assets/default-style.css` | 기본 PDF 스타일. 여백 2cm, 표 줄무늬, 코드 배경 |
| `package.json` | 의존 패키지 두 개(`md-to-pdf`, `gray-matter`) |

앞의 스킬들과 달리 **Node.js 패키지가 필요**합니다. 그래서 `SKILL.md` 맨 위에 설치 절차가 있고,
클로드는 실행 전에 `node_modules`가 있는지 확인합니다.

| 옵션 | 뜻 | 기본값 |
|---|---|---|
| `--input`, `-i` | 입력 마크다운 | 필수 |
| `--output`, `-o` | 출력 PDF 경로 | `<입력>.pdf` |
| `--css`, `-c` | 내 CSS 파일 | 내장 스타일 |
| `--no-highlight` | 코드 구문 강조 끄기 | 켜짐 |

---

## 따라 만들기 (5분)

### 1. 클로드에게 설치시키기 (권장)

터미널에서 클로드 코드를 열고 이렇게 요청합니다. 파일을 직접 옮길 필요가 없습니다.

```
아래 저장소의 markdown-to-pdf 스킬을 내 컴퓨터에 설치해줘.
https://github.com/ggplab/claude-playbook/tree/main/02-skills/markdown-to-pdf
- 필요한 패키지가 없으면 설치도 해줘
- 설치가 끝나면 스킬 목록에 보이는지 확인해줘
```

Node.js 18 이상이 필요하고, Chrome이 없으면 첫 실행에서 Chromium(약 150MB)을 내려받습니다.
"필요한 패키지가 없으면 설치도 해줘"를 함께 적으면 클로드가 처리합니다.

### 2. 직접 설치하기

```bash
mkdir -p ~/.claude/skills
cp -r 02-skills/markdown-to-pdf ~/.claude/skills/markdown-to-pdf
cd ~/.claude/skills/markdown-to-pdf && npm install
```

### 3. 확인

```bash
node ~/.claude/skills/markdown-to-pdf/scripts/convert.cjs --input README.md
```

옆에 `README.pdf`가 생기면 성공입니다. 한글이 깨지지 않는지 열어 봅니다.

### 내 스타일로 바꾸기

8장 실습은 [`print-style.css`](../../01-hanbit-claude-guidebook/chap8/outputs/print-style.css)를 `--css`로 넘겨
보고서 모양을 맞췄습니다. 폰트와 여백만 바꾼 작은 CSS입니다. 그대로 복사해 시작하면 됩니다.

---

## 왜 이렇게 만드나 (설계 포인트)

- **워드를 거치지 않는다.** 마크다운을 HTML로 바꾸고 브라우저가 PDF로 찍습니다. 웹에서 보이는 그대로 나옵니다.
- **스타일을 파일로 분리한다.** 보고서 종류마다 CSS 한 장만 바꾸면 되고, 스킬 본체는 손대지 않습니다.
- **결과를 JSON으로 돌려준다.** 클로드가 "됐다"가 아니라 페이지 수까지 확인하고 보고합니다.

---

## 더 확장하기

- 표지와 머리글이 필요하면 마크다운 맨 위 YAML 프론트매터에 `title`을 넣습니다. 스킬이 읽어 씁니다.
- 회사 폰트를 쓰려면 CSS에 `@font-face`로 넣습니다. 남의 PC에서도 같게 나오려면 base64로 임베드합니다.
- 폴더 안 마크다운을 전부 변환하는 반복문을 `SKILL.md`에 추가하면 여러 문서를 한 번에 마감합니다.

---

← [스킬 모음으로 돌아가기](../README.md)
