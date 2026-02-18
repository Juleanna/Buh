@echo off
chcp 65001 >nul
title Облiк ОЗ — Frontend
echo ╔════════════════════════════════════════════════╗
echo ║   React Frontend — http://localhost:5173       ║
echo ╚════════════════════════════════════════════════╝
echo.

cd /d "%~dp0frontend"

:: ─────────────────────────────────────────────
:: Перевірка node_modules
:: ─────────────────────────────────────────────
if not exist "node_modules" (
    echo Залежностi не знайдено. Встановлення...
    call npm install
    if %errorlevel% neq 0 (
        echo.
        echo [ПОМИЛКА] npm install не вдався
        echo   Перевiрте чи Node.js встановлений: node --version
        echo.
        pause
        exit /b 1
    )
    echo.
)

:: ─────────────────────────────────────────────
:: Запуск dev-сервера
:: ─────────────────────────────────────────────
echo Запуск Vite dev-сервера...
echo Натиснiть Ctrl+C для зупинки
echo.
call npm run dev
pause
