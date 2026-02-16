@echo off
chcp 65001 >nul
echo Stopping services...

taskkill /f /fi "WINDOWTITLE eq Oblik OZ - Backend*" 2>nul
taskkill /f /fi "WINDOWTITLE eq Oblik OZ - Frontend*" 2>nul

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a 2>nul
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a 2>nul
)

echo.
echo All services stopped.
pause
