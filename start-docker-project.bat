@echo off
chcp 65001 >nul
title Buh Docker Auto-Start

echo ================================================
echo   Автозапуск проекту Облік ОЗ (Docker)
echo ================================================
echo.

:: Чекаємо поки Docker Desktop повністю запуститься
echo Чекаю запуску Docker Desktop...
:wait_docker
docker info >nul 2>&1
if errorlevel 1 (
    timeout /t 5 /nobreak >nul
    goto wait_docker
)
echo Docker Desktop готовий!
echo.

:: Переходимо в папку проекту
cd /d "C:\Buh"

:: Запускаємо всі контейнери
echo Запуск контейнерів...
docker compose up -d

echo.
echo ================================================
echo   Проект запущено!
echo   Frontend: http://localhost
echo   Backend:  http://localhost:8000
echo ================================================

:: Закрити вікно через 10 секунд
timeout /t 10 /nobreak >nul
