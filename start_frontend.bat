@echo off
chcp 65001 > nul 2>&1

echo Opening frontend in browser...
start "" "%~dp0frontend\index.html"
echo Done.
pause
