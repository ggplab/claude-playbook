# 8장 산출물 기준본

〈클로드가 다 해줌〉 8장을 완주하면 나오는 결과물입니다. **따라 하다 막혔을 때 "제대로 나온 모양"을 확인하는 용도**입니다.

파일을 그대로 내려받아 쓰기보다, 8장 본문의 프롬프트로 직접 만들어 보시길 권합니다. 클로드는 같은 요청에도 표현이 조금씩 다를 수 있고, 기준은 겉모습이 아니라 **동작**입니다.

## 파일

| 파일 | 무엇 | 8장 위치 |
|------|------|---------|
| [`plan.md`](./plan.md) | 계획서. 목표·산출물·만드는 순서·내가 직접 해야 하는 일·가정 | 8.2 |
| [`업무일지.md`](./업무일지.md) | 저자의 실제 일지를 **익명화**한 것. 형태는 실제 그대로 | 8.3 |
| [`scripts/log-session.ps1`](./scripts/log-session.ps1) | 세션 종료 훅 스크립트 | 8.3 |
| [`scripts/weekly-summary.mjs`](./scripts/weekly-summary.mjs) | 주간 요약 집계·디스코드 발송 | 8.4 |
| [`workflows/weekly-summary.yml`](./workflows/weekly-summary.yml) | 금요일 자동 실행 설정 | 8.4 |
| [`dashboard.html`](./dashboard.html) | 로컬 업무 대시보드 (**목업 데이터**) | 8.4 |

## 쓰기 전에 고쳐야 하는 것

**`scripts/log-session.ps1` 17행** — 업무일지 폴더 경로입니다. 다른 곳에 두었다면 이 한 줄만 바꾸면 됩니다.

```powershell
$LogDir       = Join-Path $HOME 'Projects\work-log'
```

**`workflows/weekly-summary.yml`** — 이 파일은 저장소의 `.github/workflows/` 안에 있어야 깃허브가 인식합니다. 여기서는 그 폴더에 두면 이 저장소가 실행해 버리므로 `workflows/`에 보관해 두었습니다. 내 저장소로 옮길 때 경로를 맞춰 주세요.

```
work-log/.github/workflows/weekly-summary.yml
```

## 이 안에 없는 것

**디스코드 웹훅 주소와 깃허브 시크릿은 없습니다.** 비밀번호와 같은 값이라 저장소에 올리지 않습니다. 8.4에서 직접 만들어 등록하시면 됩니다.

**실제 업무일지도 없습니다.** `업무일지.md`는 형식만 보여 주는 예시이고 내용은 지어낸 것입니다. 진짜 일지에는 내가 작업한 폴더 이름이 그대로 남기 때문에, 저자의 것을 올리지 않았습니다. 여러분의 일지도 **비공개 저장소**에 두세요.

## 참고

- 일지 형식 기준: [`../WORKLOG_FORMAT.md`](../WORKLOG_FORMAT.md)
- 훅 공식 문서: https://code.claude.com/docs/en/hooks
