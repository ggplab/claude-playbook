#Requires -Version 7
<#
  세션 종료 훅 (SessionEnd)

  Claude Code 세션 1건을 업무일지.md에 한 줄로 기록한다.
  표준입력으로 훅 JSON({ cwd, transcript_path, session_id, reason, ... })을 받는다.

  기록하는 네 가지
    시작 시각 - transcript 첫 줄의 timestamp (UTC -> 로컬 변환)
    종료 시각 - 이 스크립트가 실행되는 시각
    폴더 이름 - cwd의 마지막 폴더 이름
    파일 이름 - transcript의 Write/Edit/MultiEdit/NotebookEdit 호출 대상

  어떤 이유로 실패하든 세션 종료를 막지 않는다. 항상 exit 0.
#>

# 내 업무일지 폴더. 다른 곳에 두었다면 이 한 줄만 바꾸면 됩니다.
$LogDir       = Join-Path $HOME 'Projects\work-log'
$LogFile      = Join-Path $LogDir '업무일지.md'
$TrackedTools = @('Write', 'Edit', 'MultiEdit', 'NotebookEdit')
$MaxFiles     = 10

function Get-KoreanDay([datetime]$d) {
    @('일', '월', '화', '수', '목', '금', '토')[[int]$d.DayOfWeek]
}

# 작업 폴더 안의 파일이면 상대 경로로, 밖이면 파일 이름만.
function Get-DisplayPath([string]$path, [string]$base) {
    try {
        $full = [System.IO.Path]::GetFullPath($path)
        $root = [System.IO.Path]::GetFullPath($base).TrimEnd('\', '/') + '\'
        if ($full.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) {
            return [System.IO.Path]::GetRelativePath($root, $full).Replace('\', '/')
        }
    } catch { }
    return [System.IO.Path]::GetFileName($path)
}

try {
    $raw  = [Console]::In.ReadToEnd()
    $hook = if ($raw -and $raw.Trim()) { $raw | ConvertFrom-Json } else { $null }

    $cwd    = if ($hook.cwd) { $hook.cwd } else { (Get-Location).Path }
    $folder = Split-Path -Leaf $cwd.TrimEnd('\', '/')

    $endTime   = Get-Date
    $startTime = $endTime
    $files     = [System.Collections.Generic.List[string]]::new()

    $needStart  = $true
    $transcript = $hook.transcript_path
    if ($transcript -and (Test-Path -LiteralPath $transcript)) {
        foreach ($line in [System.IO.File]::ReadLines($transcript)) {
            if (-not $line.Trim()) { continue }

            # 앞쪽 몇 줄(mode, permission-mode 등)에는 timestamp가 없다.
            # timestamp가 있는 첫 줄을 세션 시작으로 본다.
            if ($needStart -and $line -match '"timestamp":"([^"]+)"') {
                $startTime = [datetimeoffset]::Parse($Matches[1]).LocalDateTime
                $needStart = $false
            }

            # 편집 도구를 쓰지 않은 줄은 JSON 파싱까지 갈 필요가 없다.
            if ($line -notmatch '"type":"tool_use"') { continue }

            try { $entry = $line | ConvertFrom-Json } catch { continue }
            foreach ($block in @($entry.message.content)) {
                if ($block.type -ne 'tool_use') { continue }
                if ($TrackedTools -notcontains $block.name) { continue }

                $p = if ($block.input.file_path) { $block.input.file_path }
                     else { $block.input.notebook_path }
                if ($p -and -not $files.Contains($p)) { $files.Add($p) }
            }
        }
    }

    # transcript에서 timestamp를 하나도 못 찾았다면 실제 세션이 아니다.
    # (설정을 고쳐 세션이 다시 읽힐 때도 SessionEnd가 오는데, 그때는 기록할 게 없다)
    if ($needStart) { exit 0 }

    if ($files.Count -eq 0) {
        $fileCell = '-'
    } else {
        $shown    = @($files | ForEach-Object { Get-DisplayPath $_ $cwd } | Select-Object -Unique)
        $fileCell = ($shown | Select-Object -First $MaxFiles) -join ', '
        if ($shown.Count -gt $MaxFiles) {
            $fileCell += ", 외 $($shown.Count - $MaxFiles)개"
        }
    }
    # 파일 이름에 |가 있으면 표가 깨진다.
    $fileCell = $fileCell.Replace('|', '\|')

    $heading = '## {0} ({1})' -f $endTime.ToString('yyyy-MM-dd'), (Get-KoreanDay $endTime)
    $row     = '| {0} | {1} | {2} | {3} |' -f `
        $startTime.ToString('HH:mm'), $endTime.ToString('HH:mm'), $folder, $fileCell

    $utf8 = [System.Text.UTF8Encoding]::new($false)
    $nl   = [Environment]::NewLine

    # 여러 세션이 동시에 끝나도 줄이 섞이지 않도록 잠근다.
    $mutex   = [System.Threading.Mutex]::new($false, 'Global\ClaudeWorkLogDiary')
    $hasLock = $false
    try {
        try { $hasLock = $mutex.WaitOne(10000) }
        catch [System.Threading.AbandonedMutexException] { $hasLock = $true }

        if (-not (Test-Path -LiteralPath $LogFile)) {
            [System.IO.File]::WriteAllText($LogFile, "# 업무일지$nl", $utf8)
        }

        $lines = [System.Collections.Generic.List[string]]::new(
            [string[]][System.IO.File]::ReadAllLines($LogFile, $utf8))

        if ($lines -notcontains $heading) {
            $lines.AddRange([string[]]@(
                '', $heading, '', '| 시작 | 종료 | 폴더 | 파일 |', '|---|---|---|---|', $row))
        } else {
            # 한 세션이 두 번 끝난 것으로 잡히는 경우가 있다(설정을 고쳐 세션이 다시 읽힐 때 등).
            # 줄을 늘리지 말고 갱신한다. 세션은 (시작 시각, 폴더)로 구분한다.
            # 오늘 구역은 파일 맨 끝이므로 뒤에서부터 오늘 제목을 만날 때까지만 본다.
            $startStr = $startTime.ToString('HH:mm')
            $replaced = $false
            for ($i = $lines.Count - 1; $i -ge 0; $i--) {
                $line = $lines[$i]
                if ($line.StartsWith('## ')) { break }
                if (-not $line.StartsWith('|')) { continue }

                $cells = $line.Split('|')
                if ($cells.Count -lt 6) { continue }
                if ($cells[1].Trim() -eq $startStr -and $cells[3].Trim() -eq $folder) {
                    $lines[$i] = $row
                    $replaced = $true
                    break
                }
            }
            if (-not $replaced) { $lines.Add($row) }
        }
        [System.IO.File]::WriteAllLines($LogFile, $lines, $utf8)
    } finally {
        if ($hasLock) { $mutex.ReleaseMutex() }
        $mutex.Dispose()
    }

    # 6단계에서 저장소를 만들기 전까지는 조용히 건너뛴다.
    # 푸시가 실패해도(오프라인 등) 다음 세션 때 함께 올라간다.
    if (Test-Path -LiteralPath (Join-Path $LogDir '.git')) {
        $msg = '기록: {0} {1}' -f $endTime.ToString('yyyy-MM-dd HH:mm'), $folder
        & git -C $LogDir add -A            *>$null
        & git -C $LogDir commit -m $msg    *>$null
        & git -C $LogDir push              *>$null
    }
} catch {
    # 훅이 죽어도 세션 종료는 방해하지 않는다. 원인만 남긴다.
    try {
        $err = '[{0}] {1}{2}' -f (Get-Date -Format 's'), $_.Exception.Message, [Environment]::NewLine
        [System.IO.File]::AppendAllText((Join-Path $LogDir 'log-session.error.log'), $err)
    } catch { }
}

exit 0
