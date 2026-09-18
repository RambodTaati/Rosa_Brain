@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "ROSA_BRAIN_ROOT=%~dp0"
if "%ROSA_BRAIN_ROOT:~-1%"=="\" set "ROSA_BRAIN_ROOT=%ROSA_BRAIN_ROOT:~0,-1%"
set "PY=%~dp0.venv\Scripts\python.exe"

if not exist "%PY%" (
  echo [Rosa_Brain] venv not found. Run Setup-Windows.ps1 first.
  pause
  exit /b 1
)

REM Ensure keep-alive watchdog is running
wmic process where "name='powershell.exe'" get CommandLine 2>nul | find /I "keep_alive.ps1" >nul
if errorlevel 1 (
  echo [Rosa_Brain] starting keep-alive watchdog...
  start "Rosa_Brain_KeepAlive" /MIN powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\keep_alive.ps1"
)

"%PY%" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=2).read(); print('OK')" 1>nul 2>nul
if not errorlevel 1 (
  echo [Rosa_Brain] API already running at http://127.0.0.1:8765
  echo Keep-alive is watching training. This window can close.
  pause
  exit /b 0
)

echo [Rosa_Brain] waiting for keep-alive...
timeout /t 8 /nobreak >nul
"%PY%" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=2).read(); print('OK')" 1>nul 2>nul
if not errorlevel 1 (
  echo [Rosa_Brain] API is up.
  pause
  exit /b 0
)

echo [Rosa_Brain] fallback direct API start...
"%PY%" -m rosa_brain
pause
