/*
 * 한국 주식 시세 수집기 (구글 시트 + 앱스 스크립트)
 * chap4_PRD.md 반영본 — 주간 이메일 리포트 추가
 *
 * ▷ 사용법: 이 코드 전체를 복사해 Apps Script 편집기에 붙여넣고 저장하세요.
 *   그다음 시트로 돌아가 새로고침하면 상단에 '주식 수집기' 메뉴가 생깁니다.
 *   메뉴 → ① 최초 설정 을 한 번 누르면 탭·헤더·자동 실행(매일 수집 + 매주 리포트)이 스스로 만들어집니다.
 *
 * ※ 대상 종목을 바꾸거나 늘리려면 아래 SYMBOLS 목록만 고치면 됩니다.
 * ※ 공휴일을 반영하려면 아래 HOLIDAYS 목록에 'YYYY-MM-DD'를 추가하세요.
 * ※ 리포트를 받을 주소를 바꾸려면 REPORT_EMAIL 을 지정하세요(비우면 시트 소유자 Gmail로 발송).
 */

// ===== 설정 =====================================================

// 수집할 종목: 이름 = 탭 이름, 코드 = KRX 종목코드
var SYMBOLS = [
  { name: '삼성전자',   code: '005930' },
  { name: 'SK하이닉스', code: '000660' }
];

// 데이터 탭 헤더 (PRD 2절) — 순서: 날짜, 종가, 전일대비, 등락률, 시가, 고가, 저가, 거래량
var HEADERS = ['날짜', '종가', '전일대비', '등락률', '시가', '고가', '저가', '거래량'];
var COL = { DATE: 0, CLOSE: 1, CHANGE: 2, PCT: 3, OPEN: 4, HIGH: 5, LOW: 6, VOLUME: 7 };

// 로그 탭
var LOG_SHEET   = '로그';
var LOG_HEADERS = ['시각', '종목', '구분', '내용'];

// 값 계산용 임시(스크래치) 탭 — 사람이 볼 필요 없어 숨김 처리됨
var SCRATCH_SHEET = '_임시';

// 매일 시세 수집 트리거
var COLLECT_HANDLER = 'dailyCollect';
var COLLECT_HOUR    = 16; // 오후 4시

// 매주 리포트 트리거
var REPORT_HANDLER  = 'weeklyReport';
var REPORT_HOUR     = 8;  // 오전 8시
// 리포트를 받을 주소. 비워 두면 시트 소유자(스크립트 실행 계정)의 Gmail로 보냄.
var REPORT_EMAIL    = '';

// 값이 늦게 뜰 때 재시도 규칙 (PRD 예외 1)
var MAX_TRIES = 8;      // 최대 재시도 횟수
var WAIT_MS   = 1500;   // 한 번 기다리는 시간(ms)

// 공휴일 목록 (PRD 예외 4). 필요 시 여기에 'YYYY-MM-DD' 추가.
var HOLIDAYS = [
  // 예) '2026-01-01', '2026-03-01'
];

// ===== 메뉴 =====================================================

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('주식 수집기')
    .addItem('① 최초 설정', 'menuSetup')
    .addItem('② 지금 수집', 'menuCollectNow')
    .addSeparator()
    .addItem('③ 자동 실행 켜기 / 끄기', 'menuToggleAuto')
    .addItem('④ 문제 진단', 'menuDiagnose')
    .addSeparator()
    .addItem('⑤ 리포트 지금 발송', 'menuSendReportNow')
    .addToUi();
}

// ① 최초 설정: 탭·헤더 생성 + 자동 실행(매일 수집 + 매주 리포트) 등록 (한 번이면 끝)
function menuSetup() {
  ensureAllSheets_();
  var c = ensureCollectTrigger_();
  var r = ensureReportTrigger_();
  log_('시스템', '정보',
    '최초 설정 완료. 매일 수집 ' + (c ? '등록됨' : '이미 있음') +
    ', 매주 리포트 ' + (r ? '등록됨' : '이미 있음') + '.');
  SpreadsheetApp.getActiveSpreadsheet().toast(
    '탭·헤더를 준비했고, 매일 오후 4시 수집과 매주 월요일 오전 8시 리포트를 켰습니다.', '최초 설정 완료', 6);
}

// ② 지금 수집: 오늘 시세를 즉시 한 번 수집
function menuCollectNow() {
  var n = collectAll_();
  SpreadsheetApp.getActiveSpreadsheet().toast(
    n + '개 종목을 처리했습니다. 자세한 내용은 로그 탭을 확인하세요.', '수집 완료', 5);
}

// ③ 자동 실행 켜기/끄기 토글 (매일 수집 + 매주 리포트를 함께 켜고 끔)
function menuToggleAuto() {
  var ui = SpreadsheetApp.getUi();
  if (hasAnyAutoTrigger_()) {
    removeTriggerFor_(COLLECT_HANDLER);
    removeTriggerFor_(REPORT_HANDLER);
    log_('시스템', '정보', '자동 실행(수집·리포트)을 껐습니다.');
    ui.alert('자동 실행을 껐습니다.\n(매일 수집과 매주 리포트가 모두 멈춥니다.)\n다시 켜려면 이 메뉴를 한 번 더 누르세요.');
  } else {
    ensureAllSheets_();
    ensureCollectTrigger_();
    ensureReportTrigger_();
    log_('시스템', '정보', '자동 실행(수집·리포트)을 켰습니다.');
    ui.alert('자동 실행을 켰습니다.\n· 매일 오후 4시 시세 수집\n· 매주 월요일 오전 8시 리포트 발송');
  }
}

// ④ 문제 진단: 상태를 점검하고 결과를 알려줌
function menuDiagnose() {
  var lines = [];
  var ss = SpreadsheetApp.getActiveSpreadsheet();

  // 1) 탭 확인
  for (var i = 0; i < SYMBOLS.length; i++) {
    var ok = !!ss.getSheetByName(SYMBOLS[i].name);
    lines.push('· ' + SYMBOLS[i].name + ' 탭: ' + (ok ? '있음' : '없음'));
  }
  lines.push('· 로그 탭: ' + (ss.getSheetByName(LOG_SHEET) ? '있음' : '없음'));

  // 2) 자동 실행 확인
  lines.push('· 매일 수집(오후 4시): ' + (hasTriggerFor_(COLLECT_HANDLER) ? '켜짐' : '꺼짐'));
  lines.push('· 매주 리포트(월 오전 8시): ' + (hasTriggerFor_(REPORT_HANDLER) ? '켜짐' : '꺼짐'));

  // 3) 리포트 수신 주소 확인
  lines.push('· 리포트 받을 주소: ' + reportRecipient_());

  // 4) 시세 한 종목을 실제로 불러와 통신 확인
  var test = SYMBOLS[0];
  var q = fetchQuote_(test.code);
  var priceOk = isNum_(q.price);
  lines.push('· 시세 통신(' + test.name + ' 종가): ' + (priceOk ? '정상 (' + q.price + ')' : '값 못 받음 — 잠시 후 재시도 필요'));

  var msg = lines.join('\n');
  log_('시스템', '정보', '문제 진단 실행:\n' + msg);
  SpreadsheetApp.getUi().alert('문제 진단 결과', msg, SpreadsheetApp.getUi().ButtonSet.OK);
}

// ⑤ 리포트 지금 발송: 지난주 요약 메일을 즉시 보냄
function menuSendReportNow() {
  var sent = buildAndSendReport_();
  SpreadsheetApp.getActiveSpreadsheet().toast(
    sent ? ('지난주 요약을 ' + reportRecipient_() + ' 로 보냈습니다.') : '발송에 실패했습니다. 로그 탭을 확인하세요.',
    '리포트 발송', 6);
}

// ===== 자동 실행 진입점 =========================================

// 매일 오후 4시 트리거가 부르는 함수
function dailyCollect() {
  ensureAllSheets_();
  collectAll_();
}

// 매주 월요일 오전 8시 트리거가 부르는 함수
function weeklyReport() {
  ensureAllSheets_();
  buildAndSendReport_();
}

// ===== 핵심 수집 로직 ===========================================

// 모든 종목을 돌며 오늘 시세 한 줄씩 추가. 처리한 종목 수 반환.
function collectAll_() {
  var today = new Date();

  // PRD 예외 4: 주말·공휴일이면 전체 건너뜀
  if (isWeekend_(today)) {
    log_('시스템', '건너뜀', '주말이라 수집하지 않습니다.');
    return 0;
  }
  if (isHoliday_(today)) {
    log_('시스템', '건너뜀', '공휴일이라 수집하지 않습니다.');
    return 0;
  }

  var dateStr = formatDate_(today);
  var count = 0;

  for (var i = 0; i < SYMBOLS.length; i++) {
    var sym = SYMBOLS[i];
    try {
      var sheet = getOrCreateDataSheet_(sym.name);

      // PRD 예외 4: 이미 오늘 날짜가 저장돼 있으면 중복이므로 건너뜀
      if (hasDate_(sheet, dateStr)) {
        log_(sym.name, '건너뜀', dateStr + ' 은 이미 저장되어 있습니다.');
        count++;
        continue;
      }

      // 시세 조회 (PRD 예외 1: 값이 늦게 뜨면 재시도)
      var q = fetchQuote_(sym.code);

      // 각 항목을 숫자면 값, 아니면 빈칸으로 (PRD 예외 3: 일부 비어도 줄 전체 실패 아님)
      var price  = isNum_(q.price)      ? q.price      : '';
      var pct    = isNum_(q.changepct)  ? q.changepct  : '';
      var open   = isNum_(q.priceopen)  ? q.priceopen  : '';
      var high   = isNum_(q.high)       ? q.high       : '';
      var low    = isNum_(q.low)        ? q.low        : '';
      var volume = isNum_(q.volume)     ? q.volume     : '';

      // PRD 예외 2: 전일대비는 등락률에서 역산 (국내 주식은 전일종가가 안 옴)
      // 전일종가 = 종가 / (1 + 등락률/100),  전일대비 = 종가 - 전일종가
      var change = '';
      if (isNum_(q.price) && isNum_(q.changepct)) {
        var prevClose = q.price / (1 + q.changepct / 100);
        change = Math.round(q.price - prevClose);
      }

      // 한 줄 추가: [날짜, 종가, 전일대비, 등락률, 시가, 고가, 저가, 거래량]
      sheet.appendRow([dateStr, price, change, pct, open, high, low, volume]);

      // 비어 있는 항목이 있으면 어떤 게 비었는지만 로그 (줄은 이미 저장됨)
      var missing = [];
      if (price  === '') missing.push('종가');
      if (change === '' && price !== '') missing.push('전일대비(등락률 없음)');
      if (pct    === '') missing.push('등락률');
      if (open   === '') missing.push('시가');
      if (high   === '') missing.push('고가');
      if (low    === '') missing.push('저가');
      if (volume === '') missing.push('거래량');

      if (missing.length === 0) {
        log_(sym.name, '정보', dateStr + ' 저장 완료. 종가 ' + price);
      } else {
        log_(sym.name, '경고', dateStr + ' 저장(일부 빈 값): ' + missing.join(', '));
      }
      count++;

    } catch (e) {
      // PRD 예외 7: 모든 오류는 로그 탭에 남김. 한 종목 실패해도 다음 종목은 계속.
      log_(sym.name, '오류', String(e && e.message ? e.message : e));
    }
  }
  return count;
}

// GOOGLEFINANCE 값을 임시 탭에 넣어 계산시키고, 값이 뜰 때까지 재시도해서 읽음
function fetchQuote_(code) {
  var ss  = SpreadsheetApp.getActiveSpreadsheet();
  var tmp = getScratchSheet_(ss);
  var attrs = ['price', 'changepct', 'priceopen', 'high', 'low', 'volume'];

  // 임시 탭 1행에 GOOGLEFINANCE 공식 6개를 나란히 씀
  for (var i = 0; i < attrs.length; i++) {
    tmp.getRange(1, i + 1).setFormula(
      '=GOOGLEFINANCE("KRX:' + code + '","' + attrs[i] + '")');
  }

  var result = {};
  for (var t = 0; t < MAX_TRIES; t++) {
    SpreadsheetApp.flush();     // 공식이 실제로 계산되도록 강제
    Utilities.sleep(WAIT_MS);   // 값이 뜰 때까지 잠시 대기
    var row = tmp.getRange(1, 1, 1, attrs.length).getValues()[0];

    var stillLoading = false;
    result = {};
    for (var j = 0; j < attrs.length; j++) {
      var v = row[j];
      result[attrs[j]] = v;
      // 아직 로딩 중이거나 오류면 재시도 대상
      if (v === 'Loading...' || v === '#N/A' || v === '' || v === null) {
        stillLoading = true;
      }
    }
    if (!stillLoading) break;   // 전부 값이 뜨면 종료
  }

  // 임시 공식 지우기(다음 실행에 영향 없도록)
  tmp.getRange(1, 1, 1, attrs.length).clearContent();
  return result;
}

// ===== 주간 리포트 ==============================================

// 지난주(직전 월~일) 요약을 만들어 메일로 보냄. 성공하면 true.
// 지난주 데이터가 아직 없으면(설치 초기 등) 가장 최근에 수집된 주간으로 자동 대체한다.
function buildAndSendReport_() {
  try {
    var range = chooseReportRange_();  // {start, end, fallback} (Date)
    var startStr = formatDate_(range.start);
    var endStr   = formatDate_(range.end);

    // 종목별 요약 계산 (PRD 예외 3의 연장: 비어 있는 값은 빼고 계산)
    var summaries = [];
    for (var i = 0; i < SYMBOLS.length; i++) {
      summaries.push(summarizeSymbol_(SYMBOLS[i].name, range.start, range.end));
    }

    var subject = '[주가 리포트] ' + startStr + ' ~ ' + endStr + ' 주간 요약';
    var html = buildReportHtml_(startStr, endStr, summaries, range.fallback);

    var to = reportRecipient_();
    MailApp.sendEmail({ to: to, subject: subject, htmlBody: html });

    var anyData = false;
    for (var k = 0; k < summaries.length; k++) if (summaries[k].hasData) anyData = true;
    var tag = !anyData ? ' 발송 완료(수집된 데이터 없음)' : (range.fallback ? ' 발송 완료(지난주 데이터 없어 최근 주간으로 대체)' : ' 발송 완료');
    log_('리포트', '정보', subject + ' → ' + to + tag);
    return true;

  } catch (e) {
    // PRD 예외 7 / 5-1: 발송 실패는 로그에 남기고 멈추지 않음
    log_('리포트', '오류', '리포트 발송 실패: ' + String(e && e.message ? e.message : e));
    return false;
  }
}

// 리포트에 쓸 기간을 고른다.
// 1) 우선 지난주(직전 월~일). 그 주에 데이터가 있으면 그대로 사용.
// 2) 없으면 가장 최근 수집일이 속한 주(월~일)로 대체(fallback=true).
// 3) 아무 데이터도 없으면 지난주 범위를 그대로 쓰되 '데이터 없음'으로 표시된다.
function chooseReportRange_() {
  var primary = lastWeekRange_(new Date());
  if (rangeHasData_(primary.start, primary.end)) {
    return { start: primary.start, end: primary.end, fallback: false };
  }
  var latest = latestDataDate_();
  if (!latest) {
    return { start: primary.start, end: primary.end, fallback: false };
  }
  var offset = (latest.getDay() + 6) % 7;           // 그 날이 속한 주의 월요일까지
  var mon = new Date(latest); mon.setDate(latest.getDate() - offset);
  var sun = new Date(mon);    sun.setDate(mon.getDate() + 6);
  return { start: mon, end: sun, fallback: true };
}

// 주어진 기간에 어느 종목이든 데이터가 한 줄이라도 있는지
function rangeHasData_(start, end) {
  for (var i = 0; i < SYMBOLS.length; i++) {
    var s = summarizeSymbol_(SYMBOLS[i].name, start, end);
    if (s.hasData) return true;
  }
  return false;
}

// 모든 종목 탭을 통틀어 가장 최근에 수집된 날짜(Date). 없으면 null.
function latestDataDate_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var latest = null;
  for (var i = 0; i < SYMBOLS.length; i++) {
    var sheet = ss.getSheetByName(SYMBOLS[i].name);
    if (!sheet) continue;
    var last = sheet.getLastRow();
    if (last < 2) continue;
    var col = sheet.getRange(2, 1, last - 1, 1).getValues();
    for (var r = 0; r < col.length; r++) {
      var d = parseRowDate_(col[r][0]);
      if (d && (latest === null || d > latest)) latest = d;
    }
  }
  return latest;
}

// 한 종목의 지난주 기록을 요약
function summarizeSymbol_(name, start, end) {
  var out = { name: name, hasData: false, days: 0,
    firstClose: null, lastClose: null, changeAbs: null, changePct: null,
    high: null, low: null, avgVolume: null };

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(name);
  if (!sheet) return out;

  var last = sheet.getLastRow();
  if (last < 2) return out;

  var data = sheet.getRange(2, 1, last - 1, HEADERS.length).getValues();
  var rows = [];
  for (var i = 0; i < data.length; i++) {
    var d = parseRowDate_(data[i][COL.DATE]);
    if (d && d >= dayStart_(start) && d <= dayEnd_(end)) rows.push(data[i]);
  }
  if (rows.length === 0) return out;

  // 날짜 순 정렬 (문자열 YYYY-MM-DD 기준으로 안정적)
  rows.sort(function (a, b) {
    return String(formatCell_(a[COL.DATE])).localeCompare(String(formatCell_(b[COL.DATE])));
  });

  var closes = numericCol_(rows, COL.CLOSE);
  var highs  = numericCol_(rows, COL.HIGH);
  var lows   = numericCol_(rows, COL.LOW);
  var vols   = numericCol_(rows, COL.VOLUME);

  out.hasData = true;
  out.days = rows.length;
  if (closes.length > 0) {
    out.firstClose = closes[0];
    out.lastClose  = closes[closes.length - 1];
    out.changeAbs  = out.lastClose - out.firstClose;
    out.changePct  = out.firstClose !== 0 ? (out.changeAbs / out.firstClose) * 100 : null;
  }
  if (highs.length > 0) out.high = Math.max.apply(null, highs);
  if (lows.length  > 0) out.low  = Math.min.apply(null, lows);
  if (vols.length  > 0) {
    var sum = 0; for (var v = 0; v < vols.length; v++) sum += vols[v];
    out.avgVolume = Math.round(sum / vols.length);
  }
  return out;
}

// 요약들을 HTML 이메일 표로
function buildReportHtml_(startStr, endStr, summaries, isFallback) {
  var css = 'font-family:Apple SD Gothic Neo,Malgun Gothic,sans-serif;font-size:14px;color:#222;';
  var th  = 'padding:8px 10px;background:#f2f4f7;border:1px solid #dfe3e8;text-align:right;';
  var thL = 'padding:8px 10px;background:#f2f4f7;border:1px solid #dfe3e8;text-align:left;';
  var td  = 'padding:8px 10px;border:1px solid #dfe3e8;text-align:right;';
  var tdL = 'padding:8px 10px;border:1px solid #dfe3e8;text-align:left;';

  var h = '<div style="' + css + '">';
  h += '<h2 style="margin:0 0 4px;">주간 주가 요약</h2>';
  h += '<p style="margin:0 0 12px;color:#667;">기간: ' + startStr + ' ~ ' + endStr + '</p>';
  if (isFallback) {
    h += '<p style="margin:0 0 12px;padding:8px 10px;background:#fff7e6;border:1px solid #ffd591;border-radius:4px;color:#8a6d3b;">' +
         '지난주 수집 데이터가 아직 없어, 가장 최근에 수집된 주간 데이터로 보여드립니다.</p>';
  }
  h += '<table style="border-collapse:collapse;">';
  h += '<tr>' +
       '<th style="' + thL + '">종목</th>' +
       '<th style="' + th + '">시작 종가</th>' +
       '<th style="' + th + '">종료 종가</th>' +
       '<th style="' + th + '">주간 등락</th>' +
       '<th style="' + th + '">등락률</th>' +
       '<th style="' + th + '">주간 고가</th>' +
       '<th style="' + th + '">주간 저가</th>' +
       '<th style="' + th + '">평균 거래량</th>' +
       '<th style="' + th + '">수집일</th>' +
       '</tr>';

  for (var i = 0; i < summaries.length; i++) {
    var s = summaries[i];
    if (!s.hasData) {
      h += '<tr><td style="' + tdL + '">' + s.name + '</td>' +
           '<td style="' + td + '" colspan="8">데이터 없음</td></tr>';
      continue;
    }
    var pctColor = (s.changeAbs >= 0) ? '#c0392b' : '#1e6fd9'; // 상승 빨강, 하락 파랑
    var sign = (s.changeAbs >= 0) ? '+' : '';
    h += '<tr>' +
      '<td style="' + tdL + '">' + s.name + '</td>' +
      '<td style="' + td + '">' + num_(s.firstClose) + '</td>' +
      '<td style="' + td + '">' + num_(s.lastClose) + '</td>' +
      '<td style="' + td + 'color:' + pctColor + ';">' + sign + num_(s.changeAbs) + '</td>' +
      '<td style="' + td + 'color:' + pctColor + ';">' + (s.changePct === null ? '-' : sign + s.changePct.toFixed(2) + '%') + '</td>' +
      '<td style="' + td + '">' + num_(s.high) + '</td>' +
      '<td style="' + td + '">' + num_(s.low) + '</td>' +
      '<td style="' + td + '">' + num_(s.avgVolume) + '</td>' +
      '<td style="' + td + '">' + s.days + '일</td>' +
      '</tr>';
  }
  h += '</table>';
  h += '<p style="margin:14px 0 0;color:#889;font-size:12px;">이 메일은 구글 시트 앱스 스크립트가 자동으로 보냈습니다.</p>';
  h += '</div>';
  return h;
}

// 리포트를 받을 주소 (설정이 비어 있으면 시트 소유자 계정)
function reportRecipient_() {
  if (REPORT_EMAIL && REPORT_EMAIL.indexOf('@') !== -1) return REPORT_EMAIL;
  var me = Session.getEffectiveUser().getEmail();
  return me || Session.getActiveUser().getEmail();
}

// ===== 시트/탭/헤더 준비 (PRD 예외 6: 없으면 스스로 만듦) =========

function ensureAllSheets_() {
  for (var i = 0; i < SYMBOLS.length; i++) {
    getOrCreateDataSheet_(SYMBOLS[i].name);
  }
  getOrCreateLogSheet_();
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  getScratchSheet_(ss);
}

function getOrCreateDataSheet_(name) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(name);
  if (!sheet) sheet = ss.insertSheet(name);
  ensureHeader_(sheet, HEADERS);
  return sheet;
}

function getOrCreateLogSheet_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(LOG_SHEET);
  if (!sheet) sheet = ss.insertSheet(LOG_SHEET);
  ensureHeader_(sheet, LOG_HEADERS);
  return sheet;
}

// 헤더(1행)가 비어 있으면 채움
function ensureHeader_(sheet, headers) {
  var first = sheet.getRange(1, 1).getValue();
  if (first === '' || first === null) {
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold');
    sheet.setFrozenRows(1);
  }
}

// 계산용 임시 탭 (숨김)
function getScratchSheet_(ss) {
  var tmp = ss.getSheetByName(SCRATCH_SHEET);
  if (!tmp) {
    tmp = ss.insertSheet(SCRATCH_SHEET);
    tmp.hideSheet();
  }
  return tmp;
}

// ===== 자동 실행 트리거 (PRD 예외 5: 중복 생성 방지) =============

function hasTriggerFor_(handler) {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === handler) return true;
  }
  return false;
}

function hasAnyAutoTrigger_() {
  return hasTriggerFor_(COLLECT_HANDLER) || hasTriggerFor_(REPORT_HANDLER);
}

// 매일 수집 트리거를 없을 때만 생성. 새로 만들었으면 true.
function ensureCollectTrigger_() {
  if (hasTriggerFor_(COLLECT_HANDLER)) return false;
  ScriptApp.newTrigger(COLLECT_HANDLER)
    .timeBased()
    .atHour(COLLECT_HOUR)
    .everyDays(1)
    .create();
  return true;
}

// 매주 월요일 리포트 트리거를 없을 때만 생성. 새로 만들었으면 true.
function ensureReportTrigger_() {
  if (hasTriggerFor_(REPORT_HANDLER)) return false;
  ScriptApp.newTrigger(REPORT_HANDLER)
    .timeBased()
    .onWeekDay(ScriptApp.WeekDay.MONDAY)
    .atHour(REPORT_HOUR)
    .create();
  return true;
}

function removeTriggerFor_(handler) {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === handler) {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }
}

// ===== 로그 (PRD 예외 7: 모든 상황을 로그 탭에 기록) =============

function log_(symbol, level, message) {
  try {
    var sheet = getOrCreateLogSheet_();
    var now = formatDateTime_(new Date());
    sheet.appendRow([now, symbol, level, message]);
  } catch (e) {
    Logger.log('로그 실패: ' + e);
  }
}

// ===== 작은 도우미 함수들 =======================================

function isNum_(v) {
  return typeof v === 'number' && isFinite(v);
}

function isWeekend_(d) {
  var day = d.getDay(); // 0=일, 6=토
  return day === 0 || day === 6;
}

function isHoliday_(d) {
  return HOLIDAYS.indexOf(formatDate_(d)) !== -1;
}

// 특정 탭의 A열에 해당 날짜가 이미 있는지
function hasDate_(sheet, dateStr) {
  var last = sheet.getLastRow();
  if (last < 2) return false;
  var col = sheet.getRange(2, 1, last - 1, 1).getValues();
  for (var i = 0; i < col.length; i++) {
    if (formatCell_(col[i][0]) === dateStr) return true;
  }
  return false;
}

// 지난주(직전 월요일 00:00 ~ 직전 일요일)의 범위 반환
function lastWeekRange_(today) {
  var t = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  var offsetToMonday = (t.getDay() + 6) % 7;      // 이번 주 월요일까지 거슬러 갈 일수
  var thisMonday = new Date(t); thisMonday.setDate(t.getDate() - offsetToMonday);
  var lastMonday = new Date(thisMonday); lastMonday.setDate(thisMonday.getDate() - 7);
  var lastSunday = new Date(thisMonday); lastSunday.setDate(thisMonday.getDate() - 1);
  return { start: lastMonday, end: lastSunday };
}

// 행에서 숫자 컬럼만 골라 배열로 (빈 값·비숫자 제외)
function numericCol_(rows, colIndex) {
  var out = [];
  for (var i = 0; i < rows.length; i++) {
    var v = rows[i][colIndex];
    if (isNum_(v)) out.push(v);
  }
  return out;
}

// 셀의 날짜값을 Date로 (문자열 'YYYY-MM-DD' 또는 Date 지원)
function parseRowDate_(v) {
  if (v instanceof Date) return new Date(v.getFullYear(), v.getMonth(), v.getDate());
  var s = String(v).trim();
  var m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  return null;
}

function dayStart_(d) { return new Date(d.getFullYear(), d.getMonth(), d.getDate()); }
function dayEnd_(d)   { return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59, 59); }

// 숫자를 천 단위 콤마로 (빈값은 '-')
function num_(v) {
  if (!isNum_(v)) return '-';
  var neg = v < 0; var s = String(Math.round(Math.abs(v)));
  s = s.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return (neg ? '-' : '') + s;
}

// 시트의 표준 시간대에 맞춰 날짜를 YYYY-MM-DD 로
function formatDate_(d) {
  var tz = SpreadsheetApp.getActiveSpreadsheet().getSpreadsheetTimeZone();
  return Utilities.formatDate(d, tz, 'yyyy-MM-dd');
}

function formatDateTime_(d) {
  var tz = SpreadsheetApp.getActiveSpreadsheet().getSpreadsheetTimeZone();
  return Utilities.formatDate(d, tz, 'yyyy-MM-dd HH:mm:ss');
}

// A열 값이 날짜 객체일 수도, 문자열일 수도 있어 안전하게 문자열화
function formatCell_(v) {
  if (v instanceof Date) return formatDate_(v);
  return String(v).trim();
}
