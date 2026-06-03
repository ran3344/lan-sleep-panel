@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist "runtime" mkdir "runtime"

if exist "runtime\shutdown-api-tray.pid" (
    set /p TRAY_PID=<"runtime\shutdown-api-tray.pid"
    tasklist /FI "PID eq %TRAY_PID%" | find "%TRAY_PID%" >nul 2>nul
    if not errorlevel 1 exit /b 0
    del /q "runtime\shutdown-api-tray.pid" >nul 2>nul
)

set "PYTHON_CMD="
if exist ".venv\Scripts\python.exe" set "PYTHON_CMD=.venv\Scripts\python.exe"
if not defined PYTHON_CMD (
    py -3 -c "import sys" >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
    python -c "import sys" >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo Python 3.11+ was not found.
    echo Install Python and enable PATH, then run this file again.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

set "PYTHON_CMD=.venv\Scripts\python.exe"
".venv\Scripts\python.exe" -c "import flask, dotenv, pystray, PIL, waitress" >nul 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip > "runtime\pip-install.log" 2>&1
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt >> "runtime\pip-install.log" 2>&1
    if errorlevel 1 (
        echo Dependency install failed. See runtime\pip-install.log
        pause
        exit /b 1
    )
)

if not exist ".env" (
    copy /y ".env.example" ".env" >nul
)

findstr /b /c:"SECRET_KEY=" ".env" >nul
if errorlevel 1 (
    start /wait notepad ".env"
)

findstr /c:"SECRET_KEY=change_me_session_secret" ".env" >nul
if not errorlevel 1 (
    echo Update SECRET_KEY in .env before starting the service.
    start /wait notepad ".env"
    findstr /c:"SECRET_KEY=change_me_session_secret" ".env" >nul
    if not errorlevel 1 (
        echo SECRET_KEY is still unchanged. Startup cancelled.
        pause
        exit /b 1
    )
)

findstr /c:"APP_PASSWORD=change_me_login_password" ".env" >nul
if not errorlevel 1 (
    echo Update APP_PASSWORD in .env before starting the service.
    start /wait notepad ".env"
    findstr /c:"APP_PASSWORD=change_me_login_password" ".env" >nul
    if not errorlevel 1 (
        echo APP_PASSWORD is still unchanged. Startup cancelled.
        pause
        exit /b 1
    )
)

start "" /D "%~dp0" ".venv\Scripts\pythonw.exe" "%~dp0tray_app.py"
exit /b 0
