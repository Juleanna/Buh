@echo off
chcp 65001 >nul
title Облiк ОЗ — Backend
echo ╔════════════════════════════════════════════════╗
echo ║   Django Backend — http://localhost:8000       ║
echo ╚════════════════════════════════════════════════╝
echo.

cd /d "%~dp0backend"

:: ─────────────────────────────────────────────
:: Перевірка venv
:: ─────────────────────────────────────────────
if not exist "venv\Scripts\activate.bat" (
    echo [ПОМИЛКА] Вiртуальне середовище не знайдено!
    echo   Спочатку запустiть: setup.bat
    echo.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

:: ─────────────────────────────────────────────
:: Міграції
:: ─────────────────────────────────────────────
echo Застосування мiграцiй...
python manage.py migrate --no-input
if %errorlevel% neq 0 (
    echo.
    echo [УВАГА] Мiграцiї не вдалися. Перевiрте:
    echo   1. PostgreSQL запущений
    echo   2. Налаштування в backend\.env коректнi
    echo.
)

:: ─────────────────────────────────────────────
:: Запуск сервера
:: ─────────────────────────────────────────────
echo.
echo Запуск Django сервера...
echo Натиснiть Ctrl+C для зупинки
echo.
python manage.py runserver 0.0.0.0:8000
pause
