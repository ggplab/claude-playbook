# `pptx-finalize`: PPT를 PDF로 내보내면 한글 폰트가 깨지는 문제를 끝내는 스킬

> 발표 5분 전, 남의 노트북에서 연 내 PPT의 글씨체가 전부 바뀌어 있던 경험. 이 스킬은 그 상황을
> 명령 한 줄로 예방합니다.

같은 폴더의 [`SKILL.md`](./SKILL.md)와 [`scripts/finalize.py`](./scripts/finalize.py)를 그대로 복사해서 씁니다.

---

## 무엇을 해결하나

PowerPoint는 폰트를 파일 안에 넣지 않고 **이름만 기억**합니다. 그래서 회사에서 쓰는 브랜드 폰트나
무료로 받은 한글 폰트로 만든 발표자료는 폰트가 없는 환경에서 다른 글씨체로 바뀝니다. 특히 Mac에서
PDF로 내보낼 때 한글 폰트가 치환되는 문제가 자주 보고됩니다.

이 스킬은 세 가지를 한 번에 합니다.

| 단계 | 하는 일 | 결과 |
|---|---|---|
| 폰트 임베드 | 참조된 폰트 중 설치된 것을 파일 안에 넣는다 | `<이름>_embedded.pptx` |
| PDF 변환 | LibreOffice로 변환해 폰트를 PDF에 넣는다 | `<이름>.pdf` |
| 파일명 정규화 | macOS 한글 파일명(NFD)을 NFC로 바꾼다 | Windows와 웹에서 자모 분리 없음 |

원본은 그대로 두고 새 파일만 만듭니다.

### 한 줄 사용 예

```
/pptx-finalize 분기보고.pptx
```

클로드가 스크립트를 실행하고 이렇게 보고합니다(예시).

```
[스캔] 참조 typeface 3종: Pretendard×212, Arial×18, +mn-ea×6
[폰트] 임베드 대상: Pretendard (R=Pretendard-Regular.ttf, B=Pretendard-Bold.ttf)
[임베드] ✓ 분기보고_embedded.pptx
[PDF] ✓ 분기보고.pdf
[검증] PDF 임베드 폰트: Pretendard-Bold, Pretendard-Regular
```

---

## 스킬 파일 해부

이 스킬은 `SKILL.md`와 파이썬 스크립트 한 개로 구성됩니다. 절차가 복잡한 작업은 클로드에게
말로 설명하기보다 **스크립트로 고정**하고, `SKILL.md`에는 언제 어떻게 실행하는지만 적는 것이 안정적입니다.

```yaml
---
name: pptx-finalize
description: "PPTX 발표 파일을 어디서 열어도 깨지지 않는 배포본으로 마무리한다. ... 입력이 .pptx일 때만."
argument-hint: "<input.pptx> [--out-dir DIR] [--no-pdf] [--no-embed]"
---
```

`description`에 사용자가 실제로 말할 법한 표현("PDF로 내보냈더니 한글이 깨진다")을 넣어 두면
슬래시 명령을 몰라도 클로드가 알아서 꺼냅니다.

`finalize.py`는 표준 라이브러리만 씁니다. pptx는 zip 파일이므로 압축을 풀어 XML 세 곳을 고치고
폰트 파일을 넣은 뒤 다시 묶습니다.

| 함수 | 역할 |
|---|---|
| `scan_typefaces` | 덱이 참조하는 폰트 이름을 센다 |
| `build_font_index` | `fc-list`로 설치 폰트를 굵기별로 정리한다 |
| `embed_fonts` | OOXML 규약대로 폰트를 넣은 새 pptx를 쓴다 |
| `to_pdf` | LibreOffice headless 변환 |
| `nfc` | 파일명 정규화 |

---

## 따라 만들기 (5분)

### 1. 의존 도구 설치 (macOS)

```bash
brew install --cask libreoffice
brew install fontconfig poppler
```

### 2. 스킬 복사

```bash
mkdir -p ~/.claude/skills/pptx-finalize/scripts
cp 02-skills/pptx-finalize/SKILL.md ~/.claude/skills/pptx-finalize/
cp 02-skills/pptx-finalize/scripts/finalize.py ~/.claude/skills/pptx-finalize/scripts/
```

### 3. 확인

아무 pptx 하나로 시켜 봅니다.

```
/pptx-finalize 테스트.pptx
```

같은 폴더에 `테스트_embedded.pptx`와 `테스트.pdf`가 생기면 성공입니다.

### Windows에서 쓰려면

LibreOffice를 설치하고 실행 경로를 옵션으로 넘깁니다.

```
/pptx-finalize 보고서.pptx --soffice "C:\Program Files\LibreOffice\program\soffice.exe"
```

`fc-list`가 없으면 임베드 단계는 건너뛰고 `--no-embed`로 PDF만 만듭니다.

---

## 왜 이렇게 만드나 (설계 포인트)

- **원본을 건드리지 않는다.** 실패해도 잃는 것이 없어야 안심하고 돌립니다.
- **PDF를 기본 산출물로 둔다.** 임베드 pptx는 여는 프로그램마다 대접이 다르지만 PDF는 어디서나 같습니다.
- **검증을 스크립트에 넣는다.** `pdffonts`로 실제 임베드 여부를 출력하므로 "됐다고 믿는" 상태를 없앱니다.

---

## 더 확장하기

- Light, SemiBold 같은 굵기까지 임베드하려면 `build_font_index`의 weight 조건을 넓힙니다.
- 폴더 안의 pptx를 전부 처리하는 반복문을 `SKILL.md`에 추가하면 여러 파일을 한 번에 마감합니다.
- 결과 PDF를 사내 드라이브에 올리는 단계를 이어 붙이면 "마감하고 공유"가 한 명령이 됩니다.

---

← [스킬 모음으로 돌아가기](../README.md)
