@echo off
chcp 65001 > nul 2>&1

echo ============================================
echo   JY Loan Search - Backend
echo   URL: http://127.0.0.1:8080
echo ============================================
echo.

cd /d %~dp0
cd backend

if not exist main.py (
    echo ERROR: main.py not found in %cd%
    pause
    exit /b 1
)

echo Installing dependencies...
pip install -r ..\requirements.txt > nul 2>&1

echo Starting server, please wait 3 seconds...
start /b python main.py
timeout /t 3 /nobreak > nul
start "" http://127.0.0.1:8080
echo Server is running. You can close this window.
pause
