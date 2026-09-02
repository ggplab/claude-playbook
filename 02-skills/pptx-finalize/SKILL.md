---
name: pptx-finalize
description: "PPTX 발표 파일을 어디서 열어도 깨지지 않는 배포본으로 마무리한다. 폰트 임베드(OOXML 규약) → PDF 변환(LibreOffice) → 한글 파일명 정규화(NFC)를 한 번에. PPT를 PDF로 내보냈더니 한글 폰트가 깨진다, 다른 PC에서 열면 글씨체가 바뀐다, 폰트를 파일에 넣어 달라(임베드), 발표 파일 최종본 만들기 같은 요청에 사용. macOS 기준이며 LibreOffice와 fontconfig가 필요하다. 입력이 .pptx일 때만."
argument-hint: "<input.pptx> [--out-dir DIR] [--no-pdf] [--no-embed]"
---

# pptx-finalize

PPTX 발표 파일을 **어디서 열어도 안 깨지는 배포본**으로 마무리한다.

## 왜 필요한가

PowerPoint는 폰트를 파일에 넣지 않고 **이름만 저장**한다. 그래서 Pretendard나 나눔고딕처럼 기본 설치되지 않은 폰트로 만든 PPT는 다음 상황에서 글씨체가 바뀐다.

- 폰트가 없는 다른 PC에서 열 때
- 웹 변환기로 PDF를 만들 때
- Mac PowerPoint의 PDF 내보내기 (OTF 한글 폰트를 다른 폰트로 바꾸는 알려진 문제)

처방은 두 갈래이고 이 스킬은 둘 다 만든다.

| 산출물 | 용도 | 안전성 |
|---|---|---|
| `<이름>.pdf` | 발표 현장, 외부 공유 | 폰트가 PDF 안에 들어가므로 어디서 열어도 같다 |
| `<이름>_embedded.pptx` | 편집, 재배포 | Windows PowerPoint에서 안정적. Mac과 Google Slides는 임베드를 무시하기도 한다 |

## 실행

```bash
python3 ~/.claude/skills/pptx-finalize/scripts/finalize.py "<input.pptx>"
```

- 출력은 입력과 같은 폴더. **원본은 건드리지 않는다.**
- 옵션: `--out-dir DIR` 출력 폴더, `--no-pdf` 임베드만, `--no-embed` PDF만, `--soffice PATH` LibreOffice 경로 지정

## 동작 4단계

1. **스캔**: pptx 내부 XML에서 `typeface="..."` 참조를 전부 모은다.
2. **임베드**: 참조된 폰트 중 이 컴퓨터에 TTF로 설치된 것을 Regular와 Bold로 넣는다. Arial, 맑은 고딕 같은 범용 폰트와 미설치 폰트는 제외하고 경고로 알린다.
3. **PDF**: 임베드본을 LibreOffice headless로 변환한다. 이 컴퓨터의 폰트가 PDF에 들어간다.
4. **NFC**: 출력 파일명을 NFC로 정규화한다. macOS는 한글 파일명을 NFD로 저장해 Windows나 웹에서 자모가 분리돼 보이는 문제가 있다. `pdffonts`가 설치돼 있으면 PDF 임베드 결과를 자동 검증해 출력한다.

## 사용자에게 꼭 알릴 것

- **발표 현장에는 PDF를 가져간다.** "어디서 열어도 안 깨짐"을 보장하는 것은 PDF뿐이다.
- **PDF는 LibreOffice 렌더링**이라 PowerPoint와 줄바꿈이나 위치가 조금 다를 수 있다. 결과 PDF를 한 번 넘겨 본다. 레이아웃 충실도가 중요하면 `_embedded.pptx`를 Keynote로 열어 PDF로 내보내는 것이 대안이다.

## 의존성

| 도구 | 역할 | 설치 |
|---|---|---|
| LibreOffice (`soffice`) | PDF 변환 엔진 | `brew install --cask libreoffice` |
| fontconfig (`fc-list`) | 설치 폰트 목록 | `brew install fontconfig` |
| poppler (`pdffonts`) | PDF 폰트 검증 (선택) | `brew install poppler` |

## 한계

- Regular와 Bold만 임베드한다. Light나 SemiBold를 별도 폰트 이름으로 쓴 덱은 그 굵기가 빠진다. 필요하면 `finalize.py`의 `build_font_index`에서 weight 매칭을 넓힌다.
- 이미 임베드된 pptx(`embedTrueTypeFonts` 존재)는 다시 임베드하지 않는다. `--no-embed`로 PDF만 만든다.
- Windows에서는 LibreOffice 경로를 `--soffice`로 직접 지정해야 한다.
