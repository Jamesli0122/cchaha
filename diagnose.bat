@echo off
chcp 65001 > nul 2>&1

echo ============================================
echo   Diagnostic Report
echo ============================================
echo.

echo [1] Python version:
python --version 2>&1
if %errorlevel% neq 0 (
    echo   *** Python NOT found in PATH ***
    echo   Please install Python 3.9+ from https://python.org
) else (
    echo   OK
)
echo.

echo [2] pip version:
pip --version 2>&1
if %errorlevel% neq 0 (
    echo   *** pip NOT found ***
) else (
    echo   OK
)
echo.

cd /d %~dp0backend
echo [3] Working directory:
echo   %cd%
if exist main.py (echo   main.py found) else (echo   *** main.py NOT found ***)
echo.

echo [4] Dependencies:
pip show fastapi uvicorn oracledb > nul 2>&1
if %errorlevel% neq 0 (
    echo   *** Missing dependencies ***
    echo   Installing now...
    pip install fastapi uvicorn oracledb
) else (
    echo   OK
)
echo.

echo [5] Oracle Instant Client:
where oci.dll 2>nul
if %errorlevel% neq 0 (
    echo   oci.dll not found in PATH ^(may not be needed for thin mode^)
) else (
    echo   OK
)
echo.

echo [6] Try starting server manually:
echo   Run: python main.py
echo   Then check http://127.0.0.1:8080
echo.
pause
