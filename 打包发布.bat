@echo off
setlocal EnableExtensions
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\package_release.ps1"
if errorlevel 1 (
    echo Release package failed.
    pause
    exit /b 1
)

pause
exit /b 0
