@echo off
chcp 65001 >nul
title Oblik OZ - Frontend
echo ============================================
echo   React Frontend - http://localhost:5173
echo ============================================
echo.

cd /d "%~dp0frontend"

if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
    echo.
)

echo Starting Vite dev server...
echo Press Ctrl+C to stop
echo.
call npm run dev
pause
