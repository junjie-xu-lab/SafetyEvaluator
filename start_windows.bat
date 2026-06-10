@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if not errorlevel 1 (
    python start.py %*
    exit /b %errorlevel%
)

where py >nul 2>nul
if not errorlevel 1 (
    py start.py %*
    exit /b %errorlevel%
)

echo.
echo Could not find Python.
echo Install Python 3.11 or newer, then run:
echo python start.py
pause
exit /b 1
