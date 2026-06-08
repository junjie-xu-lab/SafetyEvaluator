@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo.
        echo Could not create the virtual environment with "python".
        echo If Python is installed through the Windows launcher, try:
        echo py start.py
        pause
        exit /b 1
    )
)

echo Installing dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo.
    echo Could not upgrade pip.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Could not install dependencies from requirements.txt.
    pause
    exit /b 1
)

echo Starting SafetyEvaluator...
".venv\Scripts\python.exe" -m streamlit run app.py
if errorlevel 1 (
    echo.
    echo SafetyEvaluator stopped with an error.
    pause
    exit /b 1
)
