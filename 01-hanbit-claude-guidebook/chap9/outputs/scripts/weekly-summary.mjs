#!/usr/bin/env node
/**
 * 주간 업무 요약
 *
 * 업무일지.md에서 최근 7일치 세션을 모아 디스코드 카드(임베드) 하나로 보낸다.
 * 카드 안은 날짜별로 나뉘고, 각 날짜에 그날의 세션이 시각 순으로 들어간다.
 * GitHub Actions가 매주 금요일 18:00(KST)에 실행한다. 날짜 계산은 TZ=Asia/Seoul 기준.
 *
 *   node scripts/weekly-summary.mjs            디스코드로 전송 (DISCORD_WEBHOOK_URL 필요)
 *   node scripts/weekly-summary.mjs --dry-run  보내지 않고 화면에만 출력
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const DAYS = 7;                 // 집계 기간 (발송일 포함 직전 7일)
const FILES_PER_SESSION = 4;    // 세션 한 줄에 보여줄 파일 이름 수
const EMBED_COLOR = 0x4a56d6;   // 카드 왼쪽 색 막대

// 디스코드 임베드 한도
const FIELD_VALUE_LIMIT = 1024;
const TOTAL_LIMIT = 6000;

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토'];

const logPath = join(dirname(fileURLToPath(import.meta.url)), '..', '업무일지.md');

/** 업무일지.md -> 세션 목록. `## YYYY-MM-DD` 구역 아래의 표 행만 읽는다. */
function parseDiary(text) {
  const sessions = [];
  let date = null;

  for (const line of text.split(/\r?\n/)) {
    const heading = line.match(/^##\s+(\d{4}-\d{2}-\d{2})/);
    if (heading) {
      date = heading[1];
      continue;
    }
    if (!date || !line.trimStart().startsWith('|')) continue;

    const cells = line.split('|').slice(1, -1).map((c) => c.trim());
    if (cells.length < 4) continue;

    // 표 머리글(| 시작 | 종료 |...)과 구분선(|---|)은 여기서 걸러진다.
    if (!/^\d{1,2}:\d{2}$/.test(cells[0])) continue;

    const [start, end, folder, fileCell] = cells;

    // 기록할 때 10개를 넘긴 세션은 "외 N개"로 줄여 두었다. 그 수만 따로 받아 둔다.
    let trimmed = 0;
    const files = [];
    if (fileCell !== '-') {
      for (const chunk of fileCell.split(',').map((f) => f.trim())) {
        if (!chunk) continue;
        const more = chunk.match(/^외 (\d+)개$/);
        if (more) trimmed += Number(more[1]);
        else files.push(chunk);
      }
    }

    sessions.push({ date, start, end, folder, files, trimmed });
  }
  return sessions;
}

const toMinutes = (hhmm) => {
  const [h, m] = hhmm.split(':').map(Number);
  return h * 60 + m;
};

/** 자정을 넘긴 세션도 음수가 되지 않게 한다. */
function durationOf(session) {
  const d = toMinutes(session.end) - toMinutes(session.start);
  return d < 0 ? d + 1440 : d;
}

function formatDuration(minutes) {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m}분`;
  if (m === 0) return `${h}시간`;
  return `${h}시간 ${m}분`;
}

const dateKey = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const shortLabel = (key) => key.slice(5).replace('-', '/');

/** `2026-08-07` -> `8월 7일 (금)` */
function dayHeading(key) {
  const [y, m, d] = key.split('-').map(Number);
  const weekday = WEEKDAYS[new Date(y, m - 1, d).getDay()];
  return `${m}월 ${d}일 (${weekday})`;
}

/** 경로는 길어서 카드에서 읽기 어렵다. 파일 이름만 남긴다. */
const baseName = (path) => path.split('/').pop();

/** 세션 하나를 카드 안의 두 줄로 만든다. */
function renderSession(session) {
  const head =
    `\`${session.start}–${session.end}\`  **${session.folder}** · ${formatDuration(durationOf(session))}`;

  const names = [...new Set(session.files.map(baseName))];
  if (names.length === 0 && session.trimmed === 0) {
    return `${head}\n고친 파일 없음`;
  }

  const shown = names.slice(0, FILES_PER_SESSION);
  const rest = names.length - shown.length + session.trimmed;
  const tail = rest > 0 ? ` 외 ${rest}개` : '';

  return `${head}\n${shown.join(', ')}${tail}`;
}

/** 하루치를 카드의 칸(field) 하나로 만든다. 1024자를 넘으면 뒤에서부터 줄인다. */
function renderDay(key, daySessions) {
  const sorted = [...daySessions].sort((a, b) => toMinutes(a.start) - toMinutes(b.start));
  const blocks = sorted.map(renderSession);

  let value = blocks.join('\n\n');
  let dropped = 0;
  while (value.length > FIELD_VALUE_LIMIT && blocks.length > 1) {
    blocks.pop();
    dropped += 1;
    value = blocks.join('\n\n') + `\n\n… 외 ${dropped}개 세션`;
  }

  return { name: dayHeading(key), value: value.slice(0, FIELD_VALUE_LIMIT) };
}

function buildEmbed(sessions, fromKey, toKey) {
  const period = `${shortLabel(fromKey)} ~ ${shortLabel(toKey)}`;
  const base = { title: '📋 주간 업무 요약', color: EMBED_COLOR, footer: { text: period } };

  if (sessions.length === 0) {
    return { ...base, description: '이번 주 기록 없음' };
  }

  const totalMinutes = sessions.reduce((sum, s) => sum + durationOf(s), 0);
  // 개수는 경로로 센다. 이름으로 세면 폴더가 다른 같은 이름이 하나로 합쳐진다.
  const uniqueFiles = new Set(sessions.flatMap((s) => s.files));
  const trimmed = sessions.reduce((sum, s) => sum + s.trimmed, 0);

  const description =
    `${sessions.length}세션 · ${formatDuration(totalMinutes)} · 파일 ${uniqueFiles.size + trimmed}개`;

  const byDate = new Map();
  for (const s of sessions) {
    if (!byDate.has(s.date)) byDate.set(s.date, []);
    byDate.get(s.date).push(s);
  }

  const fields = [];
  let used = base.title.length + description.length + period.length;
  for (const key of [...byDate.keys()].sort()) {
    const field = renderDay(key, byDate.get(key));
    const cost = field.name.length + field.value.length;
    if (used + cost > TOTAL_LIMIT) {
      fields.push({ name: '…', value: `남은 ${byDate.size - fields.length}일은 길어서 생략했습니다.` });
      break;
    }
    used += cost;
    fields.push(field);
  }

  return { ...base, description, fields };
}

/** 보내는 내용 그대로를 Actions 로그에서 읽을 수 있게 펼친다. */
function preview(embed) {
  const lines = [`[제목] ${embed.title}`, `[본문] ${embed.description}`];
  for (const f of embed.fields ?? []) {
    lines.push('', `[${f.name}]`, f.value);
  }
  lines.push('', `[꼬리] ${embed.footer.text}`);
  return lines.join('\n');
}

// ── 실행 ──────────────────────────────────────────────────────────────

const dryRun = process.argv.includes('--dry-run');

let text;
try {
  text = readFileSync(logPath, 'utf8');
} catch {
  console.error(`업무일지를 찾을 수 없습니다: ${logPath}`);
  process.exit(1);
}

const today = new Date();
const from = new Date(today);
from.setDate(from.getDate() - (DAYS - 1));

const fromKey = dateKey(from);
const toKey = dateKey(today);

const recent = parseDiary(text).filter((s) => s.date >= fromKey && s.date <= toKey);
const embed = buildEmbed(recent, fromKey, toKey);

if (dryRun) {
  console.log(preview(embed));
  process.exit(0);
}

const webhook = process.env.DISCORD_WEBHOOK_URL;
if (!webhook) {
  console.error('DISCORD_WEBHOOK_URL이 비어 있습니다. 저장소 시크릿을 등록했는지 확인하세요.');
  process.exit(1);
}

const res = await fetch(webhook, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ embeds: [embed] }),
});

if (!res.ok) {
  console.error(`디스코드 전송 실패: ${res.status} ${res.statusText}`);
  console.error(await res.text());
  process.exit(1);
}

console.log(`전송 완료 (${recent.length}세션, ${(embed.fields ?? []).length}일)`);
