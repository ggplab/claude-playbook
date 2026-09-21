# Aside로 서랍 저장과 신청 폼 입력하기

SKILL.md 8단계에서 읽는다. 브라우저는 Aside(`aside-browser` 스킬, `aside repl`)를 쓴다. Chrome MCP 는 로그인 세션이 따로라 브런치 편집기에 못 들어간다.

## 0. 원칙

- **로그인은 사람이 한다.** 로그인 폼이 뜨면 자격증명을 대신 넣지 않고, 사용자에게 Aside 브라우저에서 한 번 로그인해 달라고 한다. 어느 카카오계정으로 로그인했는지 기록 문서에 먼저 적는다. 2차 신청(2026-09-18)은 계정을 안 적어 두어 제출이 어느 계정으로 갔는지 추적하지 못했다.
- **ref 는 호출마다 새로 찾는다.** `aside repl` 은 호출할 때마다 `snapshot(page,{interactive:true})` 을 다시 찍고 그 결과에서 정규식으로 ref 를 뽑는다. 이전 호출에서 본 `e4` 같은 값은 다음 호출에서 다른 요소를 가리킨다(2026-09-17 실측: 같은 입력창이 e1, e4 로 바뀜).
- **긴 본문은 파일에서 읽어 넣는다.** 셸 인용 부호가 깨지므로 본문을 파일에 두고 파이썬으로 REPL 코드를 만들어 `aside repl "$CODE"` 로 넘긴다. 한 호출에 한 편이 안전하다.

## 1. 탭 붙이기

```bash
aside repl "const t = await listBrowserTabs(); console.log(JSON.stringify(t.map(x=>({id:x.targetId,url:x.url,title:x.title})))); const b = t.find(x=>/brunch\.co\.kr/.test(x.url)); if (b) { await attachBrowserTab(b.targetId); } else { await openTab('https://brunch.co.kr/'); } const s = await snapshot(page,{interactive:true}); console.log(s.tree);"
```

트리에 로그인 버튼이 보이면 멈추고 사용자에게 로그인을 부탁한다. 로그인된 프로필 이름이 보이면 그 계정명을 기록 문서에 적는다.

## 2. 서랍에 글 저장하기 (편집기 `https://brunch.co.kr/write`)

편집기의 상호작용 트리에서 `textbox` 는 순서대로 제목, 부제, 본문이다(2026-09-18 실측: `boxes[0]` 제목, `boxes[2]` 본문). 본문은 `contenteditable` 이라 `fill` 이 아니라 `pressSequentially` 로 넣고, 문단 사이는 Enter 두 번이다. 편집기는 자동 저장되어 서랍에 남는다.

```bash
# sample.txt: 첫 줄 제목, 빈 줄, 본문
CODE=$(python3 - sample.txt <<'PY'
import json,sys
t=open(sys.argv[1]).read().strip().split("\n",1)
title=json.dumps(t[0].strip(),ensure_ascii=False); body=json.dumps(t[1].strip(),ensure_ascii=False)
print(f"""await page.goto('https://brunch.co.kr/write'); await sleep(2500);
const s = await snapshot(page,{{interactive:true}});
const boxes = [...s.tree.matchAll(/textbox "[^"]*" \\[ref=(e\\d+)\\]/g)].map(m=>m[1]);
console.log('boxes', boxes.length, page.url());
await page.locator(boxes[0]).click(); await page.locator(boxes[0]).fill({title});
const bodyBox = page.locator(boxes[2]); await bodyBox.click();
const paras = {body}.split(/\\n\\s*\\n/);
for (let i=0;i<paras.length;i++) {{ await bodyBox.pressSequentially(paras[i], {{delay: 0}}); if (i<paras.length-1) {{ await bodyBox.press('Enter'); await bodyBox.press('Enter'); }} }}
await sleep(800);
console.log(await page.evaluate(() => [...document.querySelectorAll('[contenteditable="true"]')].map(e=>e.innerText.length+'|'+e.innerText.slice(0,25)+' ... '+e.innerText.slice(-30)).join('\\n')));"""
)
PY
)
aside repl "$CODE"
```

저장 확인: 마지막 출력의 글자 수가 파일 본문 글자 수와 같은지, 시작과 끝 30자가 같은지 본다. 두 편을 다 넣은 뒤 브런치 서랍 목록에서 제목 2편이 보이는지 한 번 더 본다.

## 3. 신청 폼 4단계 (`https://brunch.co.kr/apply?form`)

폼은 한 화면에 한 단계씩 나온다. 단계마다 `snapshot` 을 새로 찍고, `textbox` 와 `button "다음"` 의 ref 를 그 결과에서 뽑는다.

| 단계 | 화면 | 넣는 것 | 확인 |
|---|---|---|---|
| 01 작가소개 | textbox 1개, "N/300" 글자 수, 버튼 "다음" | 소개 문안 | 트리의 "N/300" 이 로컬 글자 수와 같은가 |
| 02 활동계획 | 같은 구조 | 활동 계획 문안 | 같음 |
| 03 자료첨부 | 서랍 글 체크박스 목록, 외부 링크 입력 | 서랍 글 2편 체크, 출간 책이나 대표 글 링크 | 체크 2건, 링크 주소 오타 |
| 04 SNS와 홈페이지 | 링크 입력, 선택 동의 체크박스, 버튼 "신청서 보내기" | 홈페이지 주소까지만 | 여기서 멈춘다 |

```bash
# 01 작가소개 넣기. bio.txt 에 소개 문안
CODE=$(python3 - bio.txt <<'PY'
import json,sys
bio=json.dumps(open(sys.argv[1]).read().strip(),ensure_ascii=False)
print(f"""await page.goto('https://brunch.co.kr/apply?form'); await sleep(2500);
let s = await snapshot(page,{{interactive:true}});
const tb = s.tree.match(/textbox "[^"]*" \\[ref=(e\\d+)\\]/)[1];
await page.locator(tb).click(); await page.locator(tb).fill({bio});
s = await snapshot(page,{{interactive:true}});
console.log(s.tree.match(/\\d+\\/300/)[0]);""")
PY
)
aside repl "$CODE"
```

"다음" 은 글자 수 확인 뒤에 누른다. 02 도 같은 방식이고, 03 과 04 는 트리를 출력해 체크박스와 링크 입력창의 ref 를 읽은 뒤 넣는다.

## 4. 멈추는 자리 (고정 게이트)

04 단계에서 **선택 동의 체크와 "신청서 보내기" 는 누르지 않는다.** 4단계 입력값을 표로 보여 주고 사용자 확인을 받은 뒤, 사용자가 직접 누르거나 명시적으로 지시했을 때만 누른다. 브런치는 신청서를 보낸 뒤 수정할 수 없고, 탈락하면 재신청 전에 기다려야 한다.

제출 직후 `https://brunch.co.kr/apply` 를 다시 열어 "심사중" 화면을 `page.screenshot({path:'./artifacts/apply-submitted.png'})` 로 남기고, Aside 세션 폴더에서 기록 문서 옆으로 복사한다. 2차 신청은 이 캡처가 없어 접수 여부를 며칠 동안 확인하지 못했다.
