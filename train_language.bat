@echo off
setlocal
cd /d "%~dp0"
set ROSA_BRAIN_ROOT=%~dp0
set ROSA_BRAIN_ROOT=%ROSA_BRAIN_ROOT:~0,-1%
set ROSA_TRAIN_STEPS=1000
echo [Rosa_Brain] language curriculum training...
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\train_curriculum.py" --phase language --steps %ROSA_TRAIN_STEPS%
pause
