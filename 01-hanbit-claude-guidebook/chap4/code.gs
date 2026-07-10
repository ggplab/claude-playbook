/*
 * 한국 주식 시세 수집기 (구글 시트 + 앱스 스크립트)
 * chap4_PRD.md 반영본
 *
 * ▷ 사용법: 이 코드 전체를 복사해 Apps Script 편집기에 붙여넣고 저장하세요.
 *   그다음 시트로 돌아가 새로고침하면 상단에 '주식 수집기' 메뉴가 생깁니다.
 *   메뉴 → ① 최초 설정 을 한 번 누르면 탭·헤더·자동 실행이 스스로 만들어집니다.
 *
 * ※ 대상 종목을 바꾸거나 늘리려면 아래 SYMBOLS 목록만 고치면 됩니다.
 * ※ 공휴일을 반영하려면 아래 HOLIDAYS 목록에 'YYYY-MM-DD'를 추가하세요.
 */

// ===== 설정 =====================================================

// 수집할 종목: 이름 = 탭 이름, 코드 = KRX 종목코드
var SYMBOLS = [
  { name: '삼성전자',   code: '005930' },
  { name: 'SK하이닉스', code: '000660' }
];

// 데이터 탭 헤더 (PRD 2절)
var HEADERS = ['날짜', '종가', '전일대비', '등락률', '시가', '고가', '저가', '거래량'];

// 로그 탭
var LOG_SHEET   = '로그';
var LOG_HEADERS = ['시각', '종목', '구분', '내용'];

// 값 계산용 임시(스크래치) 탭 — 사람이 볼 필요 없어 숨김 처리됨
var SCRATCH_SHEET = '_임시';

// 자동 실행 트리거가 부를 함수 이름 (중복 방지에 사용)
var TRIGGER_HANDLER = 'dailyCollect';
var TRIGGER_HOUR    = 16; // 오후 4시

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
    .addToUi();
}

// ① 최초 설정: 탭·헤더 생성 + 자동 실행 등록 (한 번이면 끝)
function menuSetup() {
  ensureAllSheets_();
  var created = ensureTrigger_();
  log_('시스템', '정보', '최초 설정 완료. 자동 실행 ' + (created ? '등록됨' : '이미 등록되어 있음') + '.');
  SpreadsheetApp.getActiveSpreadsheet().toast(
    '탭과 헤더를 준비했고, 매일 오후 4시 자동 실행을 켰습니다.', '최초 설정 완료', 5);
}

// ② 지금 수집: 오늘 시세를 즉시 한 번 수집
function menuCollectNow() {
  var n = collectAll_();
  SpreadsheetApp.getActiveSpreadsheet().toast(
    n + '개 종목을 처리했습니다. 자세한 내용은 로그 탭을 확인하세요.', '수집 완료', 5);
}

// ③ 자동 실행 켜기/끄기 토글
function menuToggleAuto() {
  var ui = SpreadsheetApp.getUi();
  if (hasTrigger_()) {
    removeTriggers_();
    log_('시스템', '정보', '자동 실행을 껐습니다.');
    ui.alert('자동 실행을 껐습니다.\n다시 켜려면 이 메뉴를 한 번 더 누르세요.');
  } else {
    ensureAllSheets_();
    ensureTrigger_();
    log_('시스템', '정보', '자동 실행을 켰습니다. (매일 오후 4시)');
    ui.alert('자동 실행을 켰습니다.\n매일 오후 4시에 자동으로 수집합니다.');
  }
}

// ④ 문제 진단: 상태를 점검하고 결과를 알려줌
function menuDiagnose() {
  var lines = [];

  // 1) 탭 확인
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  for (var i = 0; i < SYMBOLS.length; i++) {
    var ok = !!ss.getSheetByName(SYMBOLS[i].name);
    lines.push('· ' + SYMBOLS[i].name + ' 탭: ' + (ok ? '있음' : '없음'));
  }
  lines.push('· 로그 탭: ' + (ss.getSheetByName(LOG_SHEET) ? '있음' : '없음'));

  // 2) 자동 실행 확인
  lines.push('· 자동 실행(오후 4시): ' + (hasTrigger_() ? '켜짐' : '꺼짐'));

  // 3) 시세 한 종목을 실제로 불러와 통신 확인
  var test = SYMBOLS[0];
  var q = fetchQuote_(test.code);
  var priceOk = isNum_(q.price);
  lines.push('· 시세 통신(' + test.name + ' 종가): ' + (priceOk ? '정상 (' + q.price + ')' : '값 못 받음 — 잠시 후 재시도 필요'));

  var msg = lines.join('\n');
  log_('시스템', '정보', '문제 진단 실행:\n' + msg);
  SpreadsheetApp.getUi().alert('문제 진단 결과', msg, SpreadsheetApp.getUi().ButtonSet.OK);
}

// ===== 자동 실행 진입점 =========================================

// 트리거가 매일 오후 4시에 부르는 함수
function dailyCollect() {
  ensureAllSheets_();
  collectAll_();
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

function hasTrigger_() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === TRIGGER_HANDLER) return true;
  }
  return false;
}

// 트리거가 없을 때만 새로 만듦. 새로 만들었으면 true 반환.
function ensureTrigger_() {
  if (hasTrigger_()) return false;
  ScriptApp.newTrigger(TRIGGER_HANDLER)
    .timeBased()
    .atHour(TRIGGER_HOUR)
    .everyDays(1)
    .create();
  return true;
}

function removeTriggers_() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === TRIGGER_HANDLER) {
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
    // 로그조차 실패하면 편집기 실행 기록에만 남김
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
  if (last < 2) return false; // 헤더만 있음
  var col = sheet.getRange(2, 1, last - 1, 1).getValues();
  for (var i = 0; i < col.length; i++) {
    if (formatCell_(col[i][0]) === dateStr) return true;
  }
  return false;
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
