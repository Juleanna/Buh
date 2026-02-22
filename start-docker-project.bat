@echo off
title Buh Docker Auto-Start

echo ================================================
echo   Avtozapusk projektu Oblik OZ (Docker)
echo ================================================
echo.

echo Chekaju zapusku Docker Desktop...
:wait_docker
docker info >nul 2>&1
if errorlevel 1 (
    timeout /t 5 /nobreak >nul
    goto wait_docker
)
echo Docker Desktop gotovyj!
echo.

cd /d "C:\Buh"

echo Zapusk kontejneriv...
docker compose up -d

echo.
echo ================================================
echo   Projekt zapuscheno!
echo   Frontend: http://localhost
echo   Backend:  http://localhost:8000
echo ================================================

timeout /t 10 /nobreak >nul
