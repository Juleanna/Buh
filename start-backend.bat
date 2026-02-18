@echo off
title Oblik OZ -- Backend
echo ================================================
echo   Django Backend -- http://localhost:8000
echo ================================================
echo.

cd /d "%~dp0backend"

:: -------------------------------------------------
:: Perevirka venv
:: -------------------------------------------------
if not exist "venv\Scripts\activate.bat" (
    echo [POMYLKA] Virtualne seredovyshche ne znajdeno!
    echo   Spochatku zapustit: setup.bat
    echo.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

:: -------------------------------------------------
:: Migracii
:: -------------------------------------------------
echo Zastosuvannya migracij...
python manage.py migrate --no-input
if %errorlevel% neq 0 (
    echo.
    echo [UVAGA] Migracii ne vdalysya. Pereverte:
    echo   1. PostgreSQL zapushchenyj
    echo   2. Nalashtuvannya v backend\.env korektni
    echo.
)

:: -------------------------------------------------
:: Zapusk servera
:: -------------------------------------------------
echo.
echo Zapusk Django servera...
echo Natysnit Ctrl+C dlya zupynky
echo.
python manage.py runserver 0.0.0.0:8000
pause
