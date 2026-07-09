/*************************************************************
 * 국내주식 시세 자동 수집기 (구글 시트 + 앱스 스크립트)
 * - 붙여넣기 후 시트 메뉴 [📈 주식 수집기]에서 실행하세요.
 * - 코드 지식이 없어도 됩니다. 아래는 자동으로 동작합니다.
 *
 * 사용 순서 (자세한 건 채팅 안내 참고):
 *   1) 이 코드를 Apps Script 편집기에 통째로 붙여넣기
 *   2) 저장(💾) 후 시트로 돌아가 새로고침
 *   3) 상단 메뉴 [📈 주식 수집기] → [① 최초 설정] 실행 (권한 승인)
 *   4) [③ 자동 실행 켜기]로 매일 오후 4시 자동 수집 시작
 *************************************************************/

// ===== 설정값 (원하면 여기만 바꾸면 됩니다) =====
var CONFIG = {
  MARKET_TAB: '관심종목',
  DATA_TAB:   '데이터',
  LOG_TAB:    '로그',
  TEMP_TAB:   '_temp',       // 시세 계산용 숨김 탭
  TIMEZONE:   'Asia/Seoul',
  RUN_HOUR:   16,            // 매일 자동 실행 시각(24시간제). 16 = 오후 4시
  // 처음 넣어둘 관심종목 (종목명, 종목코드, 시장)
  SEED_STOCKS: [
    ['삼성전자',   '005930', 'KOSPI'],
    ['SK하이닉스', '000660', 'KOSPI']
  ]
};

// ===== 시트를 열면 상단에 메뉴를 자동 생성 =====
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('📈 주식 수집기')
    .addItem('① 최초 설정 (탭·종목 만들기)', 'setup')
    .addItem('② 지금 한 번 수집하기', 'collectPrices')
    .addItem('③ 자동 실행 켜기 (매일 오후 4시)', 'enableDailyTrigger')
    .addItem('④ 자동 실행 끄기', 'disableDailyTrigger')
    .addToUi();
}

// ===== ① 최초 설정: 탭/헤더/종목 자동 생성 =====
function setup() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ss.setSpreadsheetTimeZone(CONFIG.TIMEZONE);

  // 관심종목 탭
  var m = getOrCreateSheet_(ss, CONFIG.MARKET_TAB);
  if (m.getLastRow() === 0) {
    m.getRange(1, 1, 1, 3).setValues([['종목명', '종목코드', '시장']]).setFontWeight('bold');
    m.getRange(2, 1, CONFIG.SEED_STOCKS.length, 3).setValues(CONFIG.SEED_STOCKS);
    // 종목코드가 앞의 0을 잃지 않도록 텍스트 서식
    m.getRange(2, 2, 100, 1).setNumberFormat('@');
    m.setFrozenRows(1);
  }

  // 데이터 탭
  var d = getOrCreateSheet_(ss, CONFIG.DATA_TAB);
  if (d.getLastRow() === 0) {
    d.getRange(1, 1, 1, 10).setValues([[
      '날짜', '종목명', '종목코드', '종가', '전일대비', '등락률(%)',
      '시가', '고가', '저가', '거래량'
    ]]).setFontWeight('bold');
    d.setFrozenRows(1);
  }

  // 로그 탭
  var l = getOrCreateSheet_(ss, CONFIG.LOG_TAB);
  if (l.getLastRow() === 0) {
    l.getRange(1, 1, 1, 4).setValues([['실행시각', '수집건수', '실패건수', '비고']])
      .setFontWeight('bold');
    l.setFrozenRows(1);
  }

  SpreadsheetApp.getActiveSpreadsheet().toast('최초 설정 완료! 이제 ②로 수집을 테스트하세요.', '✅ 완료', 5);
}

// ===== ② 시세 수집 (핵심) =====
function collectPrices() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var market = ss.getSheetByName(CONFIG.MARKET_TAB);
  var data   = ss.getSheetByName(CONFIG.DATA_TAB);
  if (!market || !data) { setup(); market = ss.getSheetByName(CONFIG.MARKET_TAB); data = ss.getSheetByName(CONFIG.DATA_TAB); }

  var today = Utilities.formatDate(new Date(), CONFIG.TIMEZONE, 'yyyy-MM-dd');
  var dow   = new Date().getDay(); // 0=일, 6=토

  // 주말이면 수집 건너뜀
  if (dow === 0 || dow === 6) {
    writeLog_(ss, today, 0, 0, '휴장(주말) - 건너뜀');
    return;
  }

  // 관심종목 읽기
  var lastRow = market.getLastRow();
  if (lastRow < 2) { writeLog_(ss, today, 0, 0, '관심종목 없음'); return; }
  var stocks = market.getRange(2, 1, lastRow - 1, 3).getValues()
    .filter(function (r) { return String(r[1]).trim() !== ''; });

  // 오늘 이미 수집된 종목코드 (중복 방지)
  var already = {};
  var dLast = data.getLastRow();
  if (dLast >= 2) {
    var existing = data.getRange(2, 1, dLast - 1, 3).getValues();
    existing.forEach(function (r) {
      var dt = (r[0] instanceof Date)
        ? Utilities.formatDate(r[0], CONFIG.TIMEZONE, 'yyyy-MM-dd')
        : String(r[0]);
      if (dt === today) already[String(r[2])] = true;
    });
  }

  // 임시 탭에 GOOGLEFINANCE 수식을 넣어 값 계산
  var temp = getOrCreateSheet_(ss, CONFIG.TEMP_TAB);
  temp.clear();
  temp.hideSheet();

  var rows = [];      // 이번에 저장할 종목만
  var formulas = [];
  stocks.forEach(function (s) {
    var code = String(s[1]).trim().replace(/^'/, '');
    if (already[code]) return; // 오늘 이미 저장됨
    var t = 'KRX:' + code;
    formulas.push([
      '=IFERROR(GOOGLEFINANCE("' + t + '","price"),"")',
      '=IFERROR(GOOGLEFINANCE("' + t + '","closeyesterday"),"")',
      '=IFERROR(GOOGLEFINANCE("' + t + '","changepct"),"")',
      '=IFERROR(GOOGLEFINANCE("' + t + '","priceopen"),"")',
      '=IFERROR(GOOGLEFINANCE("' + t + '","high"),"")',
      '=IFERROR(GOOGLEFINANCE("' + t + '","low"),"")',
      '=IFERROR(GOOGLEFINANCE("' + t + '","volume"),"")'
    ]);
    rows.push(s);
  });

  if (formulas.length === 0) { writeLog_(ss, today, 0, 0, '오늘 수집할 신규 종목 없음(이미 수집됨)'); return; }

  temp.getRange(1, 1, formulas.length, 7).setFormulas(formulas);
  SpreadsheetApp.flush();
  Utilities.sleep(3000); // GOOGLEFINANCE 값이 채워질 시간
  var vals = temp.getRange(1, 1, formulas.length, 7).getValues();

  var out = [];
  var ok = 0, fail = 0;
  for (var i = 0; i < rows.length; i++) {
    var name = rows[i][0], code = String(rows[i][1]).trim().replace(/^'/, '');
    var price = vals[i][0], yday = vals[i][1], chgpct = vals[i][2];
    var open = vals[i][3], high = vals[i][4], low = vals[i][5], vol = vals[i][6];

    if (price === '' || price === null) { fail++; continue; }
    var diff = (typeof price === 'number' && typeof yday === 'number') ? (price - yday) : '';
    out.push([today, name, "'" + code, price, diff, chgpct, open, high, low, vol]);
    ok++;
  }

  if (out.length > 0) {
    data.getRange(data.getLastRow() + 1, 1, out.length, 10).setValues(out);
  }
  temp.clear();
  writeLog_(ss, today, ok, fail, ok > 0 ? '정상' : '수집 실패(값 없음)');
  SpreadsheetApp.getActiveSpreadsheet().toast(ok + '건 저장, ' + fail + '건 실패', '📈 수집 완료', 5);
}

// ===== ③ 자동 실행 켜기: 매일 지정 시각 트리거 =====
function enableDailyTrigger() {
  disableDailyTrigger(); // 중복 방지
  ScriptApp.newTrigger('collectPrices')
    .timeBased()
    .everyDays(1)
    .atHour(CONFIG.RUN_HOUR)
    .inTimezone(CONFIG.TIMEZONE)
    .create();
  SpreadsheetApp.getActiveSpreadsheet().toast('매일 오후 ' + (CONFIG.RUN_HOUR - 12) + '시에 자동 수집됩니다.', '✅ 자동 실행 ON', 6);
}

// ===== ④ 자동 실행 끄기 =====
function disableDailyTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'collectPrices') ScriptApp.deleteTrigger(t);
  });
}

// ===== 보조 함수들 =====
function getOrCreateSheet_(ss, name) {
  return ss.getSheetByName(name) || ss.insertSheet(name);
}

function writeLog_(ss, dateStr, ok, fail, note) {
  var l = getOrCreateSheet_(ss, CONFIG.LOG_TAB);
  if (l.getLastRow() === 0) {
    l.getRange(1, 1, 1, 4).setValues([['실행시각', '수집건수', '실패건수', '비고']]).setFontWeight('bold');
  }
  var now = Utilities.formatDate(new Date(), CONFIG.TIMEZONE, 'yyyy-MM-dd HH:mm');
  l.appendRow([now, ok, fail, note]);
}
