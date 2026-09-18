$ErrorActionPreference = "Continue"
$Root = "D:\Rosa_Brain"
$env:ROSA_BRAIN_ROOT = $Root
$Py = Join-Path $Root ".venv\Scripts\python.exe"
$Learn = Join-Path $Root "scripts\auto_learn.py"
$Polish = Join-Path $Root "scripts\auto_polish.py"
$Skills = Join-Path $Root "scripts\auto_skills.py"
$WebLang = Join-Path $Root "scripts\auto_web_languages.py"
$Log = Join-Path $Root "data\keep_alive.log"
$State = Join-Path $Root "data\auto_learn_state.json"

function Write-Log([string]$msg) {
  $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
  Add-Content -Path $Log -Value $line -Encoding UTF8
}
function Test-ApiHealthy {
  try { $r = Invoke-WebRequest -Uri "http://127.0.0.1:8765/health" -UseBasicParsing -TimeoutSec 3; return ($r.StatusCode -eq 200) } catch { return $false }
}
function Test-IsVenvCmd([string]$cmd) {
  if (-not $cmd) { return $false }
  return ($cmd -match [regex]::Escape($Py)) -or ($cmd -match '\\.venv\\Scripts\\python\.exe')
}
function Get-ParentCmd([int]$ppid) {
  $parent = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $ppid) -ErrorAction SilentlyContinue
  if ($parent) { return $parent.CommandLine }
  return $null
}
function Get-AllLearners {
  @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and ($_.CommandLine -match 'auto_learn\.py|auto_polish\.py|auto_skills\.py|auto_web_languages\.py') -and ($_.CommandLine -match 'Rosa_Brain') })
}
function Get-AllApi {
  @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and ($_.CommandLine -match 'Rosa_Brain') -and ($_.CommandLine -match 'uvicorn| -m rosa_brain') -and ($_.CommandLine -notmatch 'auto_learn|auto_polish|auto_skills|auto_web') })
}
function Test-OwnedByVenv([object]$p) {
  if (Test-IsVenvCmd $p.CommandLine) { return $true }
  return (Test-IsVenvCmd (Get-ParentCmd ([int]$p.ParentProcessId)))
}
function Get-LearnerRoots {
  $roots = @()
  foreach ($p in @(Get-AllLearners)) {
    if (-not (Test-OwnedByVenv $p)) { continue }
    $pcmd = Get-ParentCmd ([int]$p.ParentProcessId)
    if ($pcmd -and ($pcmd -match 'auto_learn\.py|auto_polish\.py|auto_skills\.py|auto_web_languages\.py')) { continue }
    $roots += $p
  }
  return $roots
}
function Stop-OrphanNonVenv {
  foreach ($p in @(Get-AllLearners) + @(Get-AllApi)) {
    if (Test-OwnedByVenv $p) { continue }
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    Write-Log "Killed orphan non-venv $($p.ProcessId)"
  }
}
function Get-LearnMode {
  # IDLE_WHEN_SKILLS_DONE — never relaunch auto_skills after curriculum done
  if (-not (Test-Path $State)) { return "idle" }
  try {
    $raw = [System.IO.File]::ReadAllText($State)
    if ($raw.Length -gt 0 -and [int][char]$raw[0] -eq 0xFEFF) { $raw = $raw.Substring(1) }
    $j = $raw | ConvertFrom-Json
    if ($j.mode -eq "web_languages") { return "web" }
    $qpath = Join-Path $Root "data\web_languages_queue.json"
    if (Test-Path $qpath) {
      try {
        $qr = [System.IO.File]::ReadAllText($qpath)
        if ($qr.Length -gt 0 -and [int][char]$qr[0] -eq 0xFEFF) { $qr = $qr.Substring(1) }
        $q = $qr | ConvertFrom-Json
        if ($q.ready -and ($j.phase -eq "done" -or $j.skills_path_complete -eq $true)) { return "web" }
      } catch {}
    }
    if ($j.mode -eq "skills") {
      if ($j.phase -eq "done" -or $j.skills_path_complete -eq $true) { return "idle" }
      return "skills"
    }
    if ($j.mode -eq "understand_polish") {
      $steps = 0; if ($j.phase_steps) { $steps = [int]$j.phase_steps }
      $held = 0.0; if ($j.heldout_accuracy) { $held = [double]$j.heldout_accuracy }
      if ($steps -ge 30000 -and $held -ge 0.90) { return "idle" }
      return "polish"
    }
    if ($j.phase -eq "done") { return "idle" }
    if ($j.mode -eq "understand") { return "learn" }
    return "idle"
  } catch { return "idle" }
}
function Start-Api {
  Write-Log "Starting API (venv)"
  Start-Process -FilePath $Py -ArgumentList "-m","uvicorn","rosa_brain.api:app","--host","127.0.0.1","--port","8765" -WorkingDirectory $Root -WindowStyle Hidden
}
function Start-Learner {
  $mode = Get-LearnMode
  if ($mode -eq "web") {
    if (Test-Path $WebLang) {
      Write-Log "Starting web_languages learner"
      Start-Process -FilePath $Py -ArgumentList "`"$WebLang`"","--chunk","16" -WorkingDirectory $Root -WindowStyle Hidden
    }
  } elseif ($mode -eq "skills") {
    Write-Log "Starting skills curriculum learner"
    Start-Process -FilePath $Py -ArgumentList "`"$Skills`"","--chunk","16" -WorkingDirectory $Root -WindowStyle Hidden
  } elseif ($mode -eq "polish") {
    Write-Log "Starting detect polish learner"
    Start-Process -FilePath $Py -ArgumentList "`"$Polish`"" -WorkingDirectory $Root -WindowStyle Hidden
  } elseif ($mode -eq "learn") {
    Write-Log "Starting language learner"
    Start-Process -FilePath $Py -ArgumentList "`"$Learn`"","--chunk","10" -WorkingDirectory $Root -WindowStyle Hidden
  } else {
    Write-Log "Learner idle mode=$mode"
  }
}
Write-Log "keep_alive started (v7 no-skills-wipe + web)"
while ($true) {
  try {
    Stop-OrphanNonVenv
    if (-not (Test-ApiHealthy)) {
      netstat -ano | Select-String ":8765\s+.*LISTENING" | ForEach-Object {
        if ($_.ToString() -match "LISTENING\s+(\d+)\s*$") {
          $listenPid = [int]$Matches[1]
          if ($listenPid -gt 0) { taskkill /F /PID $listenPid 2>$null | Out-Null; Write-Log "Freed port PID $listenPid" }
        }
      }
      Start-Sleep -Seconds 1
      Start-Api
      Start-Sleep -Seconds 5
    }
    $mode = Get-LearnMode
    if ($mode -eq "skills") {
      Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and ($_.CommandLine -match 'auto_polish\.py') } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Log "Stopped polish for skills $($_.ProcessId)" }
    }
    # Never allow auto_skills while idle/web
    if ($mode -eq "idle" -or $mode -eq "web") {
      Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and ($_.CommandLine -match 'auto_skills\.py') } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Log "Blocked auto_skills in mode=$mode $($_.ProcessId)" }
    }
    $learners = @(Get-LearnerRoots)
    if ($learners.Count -gt 1) {
      $keep = $learners | Sort-Object ProcessId | Select-Object -First 1
      foreach ($p in $learners) {
        if ($p.ProcessId -ne $keep.ProcessId) {
          Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
          Write-Log "Killed extra learner $($p.ProcessId)"
        }
      }
      $learners = @($keep)
    }
    if ($learners.Count -eq 0 -and $mode -ne "idle") {
      Write-Log "Learner missing; restarting mode=$mode"
      Start-Learner
      Start-Sleep -Seconds 8
    }
  } catch { Write-Log ("Watchdog error: " + $_.Exception.Message) }
  Start-Sleep -Seconds 20
}
