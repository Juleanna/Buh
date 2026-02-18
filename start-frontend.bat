@echo off
title Oblik OZ -- Frontend
echo ================================================
echo   React Frontend -- http://localhost:5173
echo ================================================
echo.

cd /d "%~dp0frontend"

:: -------------------------------------------------
:: Perevirka node_modules
:: -------------------------------------------------
if not exist "node_modules" (
    echo Zalezhnosti ne znajdeno. Vstanovlennya...
    call npm install
    if %errorlevel% neq 0 (
        echo.
        echo [POMYLKA] npm install ne vdavsya
        echo   Pereverte chy Node.js vstanovlenyj: node --version
        echo.
        pause
        exit /b 1
    )
    echo.
)

:: -------------------------------------------------
:: Zapusk dev-servera
:: -------------------------------------------------
echo Zapusk Vite dev-servera...
echo Natysnit Ctrl+C dlya zupynky
echo.
call npm run dev
pause
