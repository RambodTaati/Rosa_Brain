@echo off
cd /d "%~dp0"
echo [Rosa_Brain] keep-alive watchdog starting...
start "Rosa_Brain_KeepAlive" /MIN powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\keep_alive.ps1"
echo [Rosa_Brain] watchdog launched minimized.
