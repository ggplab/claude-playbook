# 터미널 하단에 상태줄 붙이기 — 모델·비용·사용량이 한눈에 보이는 2줄 상태바

> 원본: 아티팩트 「Claude Code 상태줄 설치 가이드」 (2026-07-20 공유)를 텍스트로 옮긴 것.
> 스크립트 원본 파일: [Chap8_statusline-command.sh](Chap8_statusline-command.sh)

Claude Code 화면 맨 아래에 상태줄을 띄우는 설정입니다. 지금 쓰는 모델, 프로젝트, 브랜치, 누적 비용, 그리고 컨텍스트·5시간·7일 사용량 게이지가 실시간으로 표시됩니다. 설치는 파일 1개 + 설정 1줄이면 끝납니다.

**상태줄 미리보기** (2줄 구성):

```
[Opus 4.8] 📁 my-project ⑃ feature-wt 🌿 main | ⚙ high | $1.42 ✎ 상태줄 설치
ctx ▓▓░░░░░░ 25%  5h ▓▓▓▓░░░░ 48%  7d ▓▓▓▓▓▓▓░ 83%
```

- 1줄: 모델 · 프로젝트 · 워크트리 · 브랜치 · effort · 누적 비용 · 세션 제목
- 2줄: 컨텍스트(ctx) · 5시간(5h) · 7일(7d) 사용량 진행바
- 사용량이 75%를 넘으면 게이지가 노란색, 90%를 넘으면 빨간색으로 바뀝니다.

## 가장 쉬운 방법: 링크만 주고 Claude Code에게 맡기기

터미널을 잘 몰라도 됩니다. 파일을 복사할 필요도 없습니다. Claude Code 채팅창에 아래를 그대로 붙여넣으면 Claude가 스크립트를 받아 저장하고 설정까지 끝냅니다.

```
아래 주소의 상태줄 스크립트를 ~/.claude/statusline-command.sh 로 저장하고,
settings.json의 statusLine이 이 파일을 실행하도록 설정해줘.
https://raw.githubusercontent.com/ggplab/claude-playbook/main/01-hanbit-claude-guidebook/chap8/Chap8_statusline-command.sh
- jq가 없으면 설치도 해줘
- 끝나면 Claude Code를 다시 켰을 때 상태줄이 보이는지 확인하는 방법을 알려줘
```

직접 설치하고 싶다면 아래 1 → 2 → 3 순서대로 따라 하세요.

## 1. 준비물 확인

- **Claude Code**가 설치돼 있어야 합니다 (macOS / Linux 터미널 기준).
- 스크립트가 `jq`라는 작은 도구를 사용합니다. 터미널에서 `jq --version`을 입력했을 때 오류가 나면 `brew install jq`로 설치하세요.

## 2. 스크립트 파일 저장

[Chap8_statusline-command.sh](Chap8_statusline-command.sh)의 내용 전체를 `~/.claude/statusline-command.sh` 경로에 파일로 저장하세요.

저장 후 터미널에서 실행 권한을 한 번 부여합니다:

```bash
chmod +x ~/.claude/statusline-command.sh
```

## 3. settings.json에 연결

`~/.claude/settings.json` 파일을 열어(없으면 새로 만들기) 최상위에 아래 항목을 추가합니다. 이미 다른 설정이 있다면 그 옆에 `"statusLine"` 키만 끼워 넣으면 됩니다.

```json
{
  "statusLine": {
    "type": "command",
    "command": "bash ~/.claude/statusline-command.sh"
  }
}
```

## 확인하기

Claude Code를 새로 실행하고 아무 메시지나 한 번 보내면, 입력창 바로 아래에 상태줄 2줄이 나타납니다. 안 보이면 아래를 점검하세요:

- `bash ~/.claude/statusline-command.sh`를 직접 실행했을 때 `jq: command not found`가 나오면 → 1단계의 jq 설치.
- settings.json 저장 후에도 안 뜨면 → Claude Code를 완전히 종료했다가 다시 실행.
- 그래도 안 되면 → Claude Code 채팅창에 "상태줄이 안 떠. 원인 찾아서 고쳐줘"라고 물어보세요. 그게 이 도구를 쓰는 가장 좋은 방법입니다.

> **참고** — 첫 줄의 `⑃`(워크트리)·`⚙`(effort)·`✎`(세션 제목)는 해당 정보가 있을 때만 나타납니다. 안 보여도 고장이 아닙니다. 비용 옆에 `⚠`가 붙으면 해당 모델의 비용 집계가 아직 지원되지 않는다는 표시입니다.
