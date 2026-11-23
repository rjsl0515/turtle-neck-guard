@echo off
setlocal
cd /d "%~dp0"

set "PY_CMD="
where py >nul 2>nul && (py -3 --version >nul 2>nul && set "PY_CMD=py -3")
if not defined PY_CMD (where python >nul 2>nul && (python --version >nul 2>nul && set "PY_CMD=python"))

if not defined PY_CMD (
    echo [ERROR] Python 3 is not installed or not in PATH.
    echo Please install Python from https://www.python.org/downloads/ and check 'Add python.exe to PATH'.
    pause
    exit /b 1
)

echo [1/4] Checking virtual environment...
if not exist ".venv\Scripts\python.exe" (
    %PY_CMD% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo [2/4] Installing required packages (pywebview, pyinstaller)...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install pywebview pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install packages.
    pause
    exit /b 1
)

echo [3/4] Building standalone EXE...
".venv\Scripts\pyinstaller.exe" --noconsole --onefile --clean --collect-all webview --name "TurtleNeckGuard" --add-data "index.html;." windows_app.py
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    pause
    exit /b 1
)

echo [4/4] Finalizing output file...
".venv\Scripts\python.exe" -c "import shutil; shutil.copy2(r'dist\TurtleNeckGuard.exe', 'dist\\\uac70\ubd81\ubaa9\uad50\uc815\uae30.exe')"

if exist "dist\TurtleNeckGuard.exe" (
    echo.
    echo [SUCCESS] Build finished! Check the dist folder.
) else (
    echo.
    echo [ERROR] Output exe file not found.
)
pause
