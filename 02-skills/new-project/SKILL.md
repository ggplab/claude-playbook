---
name: new-project
description: 새 프로젝트 디렉토리 생성 전 네이밍 컨벤션 검증 및 이름 추천. 프로젝트 이름이나 설명을 입력하면 kebab-case 이름 후보를 제안하고 충돌 체크 후 디렉토리를 생성한다.
argument-hint: "<프로젝트 설명 또는 이름>"
---

<!--
  이 파일은 공개용 재사용 템플릿입니다.
  ★ 표시가 붙은 줄은 본인 환경에 맞게 바꿔서 쓰세요.
  - WORKSPACE: 새 프로젝트를 모아 두는 폴더 (예: ~/Projects, ~/work, ~/dev)
  - 선택 단계(.gitignore 템플릿, Codex 등록)는 안 쓰면 통째로 지워도 됩니다.
-->

사용자가 새 프로젝트를 만들려고 한다. 아래 절차를 따라 네이밍을 도와주고 디렉토리를 생성하라.

작업 폴더(WORKSPACE)는 `~/Projects`로 가정한다. ★ 본인 환경이 다르면 이 경로를 일괄 치환해서 쓴다.

## 네이밍 규칙

- **형식**: `kebab-case`: 소문자, 영문, 숫자, 하이픈만
- **금지**: 한글, 대문자, 언더스코어(`_`), 공백
- **활성 프로젝트**: `~/Projects/<이름>/`
- **실험/임시**: 이름 앞에 `_scratch-` 사용
- **보관**: 나중에 `_archive-<이름>/`으로 prefix 변경

## 절차

### Step 1. 현재 프로젝트 목록 확인
```bash
ls ~/Projects/ | grep -v "^_" | sort
```

### Step 2. 이름 후보 생성
사용자 입력(`$ARGUMENTS`)을 기반으로:
1. 입력을 그대로 kebab-case로 변환한 안
2. 더 간결하게 줄인 안
3. 도메인/목적이 명확한 안

예시:
- 입력: "농산물 가격 대시보드" → `price-dashboard`, `agri-price-tracker`, `crop-price-board`
- 입력: "투자 모니터링 봇" → `invest-monitor`, `stock-alert-bot`, `invest-bot`

### Step 3. 충돌 체크
후보 이름이 기존 프로젝트와 겹치거나 비슷한지 확인:
```bash
ls ~/Projects/ | grep -i "<후보이름>"
```

비슷한 프로젝트가 있으면 사용자에게 알리고: "기존 `<유사프로젝트>`와 관련 있나요? 확장인가요, 별개인가요?"

### Step 4. 확정 및 생성
사용자가 이름을 확정하면:
```bash
mkdir ~/Projects/<확정이름>
cd ~/Projects/<확정이름>
git init -b main
```

#### .gitignore 선택 (선택)
프로젝트 유형을 물어보고 알맞은 `.gitignore`를 넣는다. 본인 템플릿이 없으면
GitHub 공식 모음([github.com/github/gitignore](https://github.com/github/gitignore))을 그대로 써도 된다.
- **Python** → `Python.gitignore`
- **Node.js** → `Node.gitignore`
- **기타/모름** → 빈 `.gitignore`로 시작해 필요할 때 추가

#### Initial commit
```bash
git add .gitignore
git commit -m "Initial project setup"
```

그리고 필요 여부를 물어본다:
- GitHub repo 생성? (`gh repo create <이름> --private --source=. --remote=origin`)
- 프로젝트 규칙 파일(`CLAUDE.md`) 추가?
- 환경변수 시작점(`.env`) 추가?

### Step 5. (선택) Codex 등 다른 CLI 에이전트에 신뢰 등록
Codex CLI를 함께 쓴다면 새 폴더를 신뢰 목록에 추가한다. ★ 안 쓰면 이 단계는 지운다.
```bash
printf '\n[projects."%s/Projects/<확정이름>"]\ntrust_level = "trusted"\n' "$HOME" >> ~/.codex/config.toml
```

## 주의사항
- 이름을 임의로 확정하지 말고 반드시 사용자 선택을 받는다
- 디렉토리 생성 전 "이 이름으로 만들까요?" 확인
- 기존 프로젝트 삭제/수정은 하지 않는다
