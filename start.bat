@echo off
chcp 65001 >nul
echo ╔════════════════════════════════════════════════╗
echo ║   Облiк ОЗ — Запуск системи                   ║
echo ╚════════════════════════════════════════════════╝
echo.

:: ─────────────────────────────────────────────
:: Перевірка наявності встановлення
:: ─────────────────────────────────────────────
if not exist "%~dp0backend\venv" (
    echo [ПОМИЛКА] Backend не встановлено!
    echo   Спочатку запустiть: setup.bat
    echo.
    pause
    exit /b 1
)
if not exist "%~dp0frontend\node_modules" (
    echo [ПОМИЛКА] Frontend не встановлено!
    echo   Спочатку запустiть: setup.bat
    echo.
    pause
    exit /b 1
)

:: ─────────────────────────────────────────────
:: Запуск Backend
:: ─────────────────────────────────────────────
echo Запуск Backend (Django)...
start "Oblik OZ - Backend" cmd /k ""%~dp0start-backend.bat""

:: Чекаємо поки backend піднімається
echo Очiкування запуску backend...
timeout /t 3 /nobreak >nul

:: ─────────────────────────────────────────────
:: Запуск Frontend
:: ─────────────────────────────────────────────
echo Запуск Frontend (React)...
start "Oblik OZ - Frontend" cmd /k ""%~dp0start-frontend.bat""

:: Чекаємо поки frontend піднімається
timeout /t 5 /nobreak >nul

:: ─────────────────────────────────────────────
:: Готово
:: ─────────────────────────────────────────────
echo.
echo ╔════════════════════════════════════════════════╗
echo ║   Система запущена!                            ║
echo ╚════════════════════════════════════════════════╝
echo.
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo   Адмiнка:  http://localhost:8000/admin/
echo.
echo   Для зупинки: stop.bat
echo.

:: Відкриваємо браузер
start http://localhost:5173

pause
