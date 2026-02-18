@echo off
chcp 65001 >nul
echo ╔════════════════════════════════════════════════╗
echo ║   Облiк ОЗ — Зупинка системи                  ║
echo ╚════════════════════════════════════════════════╝
echo.

:: ─────────────────────────────────────────────
:: Закриття вікон за назвою
:: ─────────────────────────────────────────────
echo Зупинка Backend...
taskkill /f /fi "WINDOWTITLE eq Oblik OZ*" 2>nul

:: ─────────────────────────────────────────────
:: Закриття процесів на портах
:: ─────────────────────────────────────────────
echo Зупинка процесiв на порту 8000 (Django)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a 2>nul
)

echo Зупинка процесiв на порту 5173 (Vite)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a 2>nul
)

echo.
echo Усi сервiси зупинено.
echo.
pause
