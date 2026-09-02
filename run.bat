@echo off
REM Crypto Market Sentiment Analyzer - Windows Launcher

echo.
echo ============================================================
echo              CRYPTO MARKET SENTIMENT ANALYZER
echo ============================================================
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Error: Could not create virtual environment
        echo Make sure Python is installed and added to PATH
        pause
        exit /b 1
    )
    
    echo Installing dependencies...
    call venv\Scripts\activate.bat
    pip install -q -r requirements.txt
    if errorlevel 1 (
        echo Error: Could not install dependencies
        pause
        exit /b 1
    )
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run the application
if "%1"=="" (
    echo Running in watch mode (updates every 5 minutes)...
    echo.
    python main.py --interval 300
) else (
    python main.py %*
)

pause
