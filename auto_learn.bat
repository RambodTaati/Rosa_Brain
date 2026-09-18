@echo off
setlocal
cd /d "%~dp0"
set "ROSA_BRAIN_ROOT=%~dp0"
if "%ROSA_BRAIN_ROOT:~-1%"=="\" set "ROSA_BRAIN_ROOT=%ROSA_BRAIN_ROOT:~0,-1%"
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [Rosa_Brain] venv missing
  pause
  exit /b 1
)
echo [Rosa_Brain] auto-learn starting: English first, then Persian
"%PY%" "%~dp0scripts\auto_learn.py" --once-phase all
echo [Rosa_Brain] auto-learn finished
pause
