@echo off
echo ===================================================
echo        AutoApply Pro - First Time Setup & Run      
echo ===================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH. Please install Python 3.10+ and try again.
    pause
    exit /b
)

:: Create Virtual Environment if it doesn't exist
if not exist venv\ (
    echo [1/4] Creating Python Virtual Environment...
    python -m venv venv
) else (
    echo [1/4] Virtual Environment already exists.
)

:: Activate and install requirements
echo [2/4] Installing Python Dependencies (This might take a minute)...
call venv\Scripts\activate
pip install -r requirements.txt --quiet

:: Install Playwright browsers
echo [3/4] Installing Chromium browser for automation...
playwright install chromium

:: Start the app
echo.
echo [4/4] Starting AutoApply Pro Web Server...
echo.
echo ===================================================
echo  SUCCESS! App is running at: http://127.0.0.1:8000
echo  Keep this window open while using the app.
echo ===================================================
echo.
uvicorn web_app:app --reload
pause
