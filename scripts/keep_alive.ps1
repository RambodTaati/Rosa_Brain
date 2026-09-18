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
$Queue = Join-Path $Root "data\web_languages_queue.json"

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
function Test-WebQueueReady {
  if (-not (Test-Path $Queue)) { return $false }
  try {
    $qraw = [System.IO.File]::ReadAllText($Queue)
    if ($qraw.Length -gt 0 -and [int][char]$qraw[0] -eq 0xFEFF) { $qraw = $qraw.Substring(1) }
    $q = $qraw | ConvertFrom-Json
    return [bool]$q.ready
  } catch { return $false }
}
function Read-LearnState {
  if (-not (Test-Path $State)) { return $null }
  try {
    $raw = [System.IO.File]::ReadAllText($State)
    if ($raw.Length -gt 0 -and [int][char]$raw[0] -eq 0xFEFF) { $raw = $raw.Substring(1) }
    return ($raw | ConvertFrom-Json)
  } catch { return $null }
}
function Get-AllLearners {
  @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and ($_.CommandLine -match 'auto_learn\.py|auto_polish\.py|auto_skills\.py|auto_web_languages\.py') -and ($_.CommandLine -match 'Rosa_Brain') })
}
function Get-AllApi {
  @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and ($_.CommandLine -match 'Rosa_Brain') -and ($_.CommandLine -match 'uvicorn| -m rosa_brain') -and ($_.CommandLine -notmatch 'auto_learn|auto_polish|auto_skills|auto_web_languages') })
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
function Stop-AutoSkillsOnly {
  foreach ($p in @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and ($_.CommandLine -match 'auto_skills\.py') })) {
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    Write-Log "Stopped auto_skills $($p.ProcessId) (phase done / web mode)"
  }
}
function Get-LearnMode {
  $j = Read-LearnState
  if (-not $j) { return "skills" }
  try {
    $mode = [string]$j.mode
    $phase = [string]$j.phase
    $queueReady = Test-WebQueueReady

    # Web languages active (mirrored or native)
    if ($mode -eq "web_languages" -or $mode -eq "web") {
      return "web"
    }
    # Skills path complete
    if ($phase -eq "done") {
      if ($queueReady) { return "web" }
      return "idle"
    }
    # Explicit skills still in progress
    if ($mode -eq "skills") {
      if ($phase -eq "done") {
        if ($queueReady) { return "web" }
        return "idle"
      }
      return "skills"
    }
    if ($mode -eq "understand_polish") {
      $steps = 0; if ($j.phase_steps) { $steps = [int]$j.phase_steps }
      $held = 0.0; if ($j.heldout_accuracy) { $held = [double]$j.heldout_accuracy }
      if ($steps -ge 30000 -and $held -ge 0.90) {
        if ($queueReady) { return "web" }
        return "skills"
      }
      return "polish"
    }
    if ($mode -eq "understand") { return "learn" }
    # Fallback: if queue ready and skills markers present, prefer web
    if ($queueReady -and ($j.skills_path_complete -eq $true)) { return "web" }
    return "skills"
  } catch { return "skills" }
}
function Start-Api {
  Write-Log "Starting API (venv)"
  Start-Process -FilePath $Py -ArgumentList "-m","uvicorn","rosa_brain.api:app","--host","127.0.0.1","--port","8765" -WorkingDirectory $Root -WindowStyle Hidden
}
function Start-Learner {
  $mode = Get-LearnMode
  $j = Read-LearnState
  $phase = if ($j) { [string]$j.phase } else { "" }

  if ($mode -eq "idle") {
    Write-Log "Learner idle (skills done; web queue not ready) — not starting auto_skills"
    Stop-AutoSkillsOnly
    return
  }
  if ($mode -eq "web") {
    Stop-AutoSkillsOnly
    if (-not (Test-Path $WebLang)) {
      Write-Log "auto_web_languages.py missing"
      return
    }
    Write-Log "Starting web_languages learner"
    Start-Process -FilePath $Py -ArgumentList "`"$WebLang`"" -WorkingDirectory $Root -WindowStyle Minimized
    return
  }
  if ($mode -eq "skills") {
    if ($phase -eq "done") {
      Write-Log "Refusing Start-Learner skills: phase=done"
      Stop-AutoSkillsOnly
      return
    }
    Write-Log "Starting skills curriculum learner"
    Start-Process -FilePath $Py -ArgumentList "`"$Skills`"","--chunk","16" -WorkingDirectory $Root -WindowStyle Hidden
    return
  }
  if ($mode -eq "polish") {
    Write-Log "Starting detect polish learner"
    Start-Process -FilePath $Py -ArgumentList "`"$Polish`"" -WorkingDirectory $Root -WindowStyle Hidden
    return
  }
  Write-Log "Starting language learner"
  Start-Process -FilePath $Py -ArgumentList "`"$Learn`"","--chunk","10" -WorkingDirectory $Root -WindowStyle Hidden
}

Write-Log "keep_alive started (stable v7 web-mode + no-wipe)"
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
    if ($mode -eq "web" -or $mode -eq "idle") {
      Stop-AutoSkillsOnly
    }
    if ($mode -eq "skills") {
      Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and ($_.CommandLine -match 'auto_polish\.py') } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Log "Stopped polish for skills $($_.ProcessId)" }
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
    if ($learners.Count -eq 0) {
      if ($mode -eq "idle") {
        Write-Log "No learner; mode=idle (ok)"
      } else {
        Write-Log "Learner missing; restarting mode=$mode"
        Start-Learner
        Start-Sleep -Seconds 8
      }
    }
  } catch { Write-Log ("Watchdog error: " + $_.Exception.Message) }
  Start-Sleep -Seconds 20
}
