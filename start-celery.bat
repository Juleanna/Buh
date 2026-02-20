@echo off
title Oblik OZ -- Celery
echo ================================================
echo   Celery Worker + Beat
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
:: Zapusk Celery Beat (planuvalnik) u fonovomu vikni
:: -------------------------------------------------
echo Zapusk Celery Beat (planuvalnik)...
start "Oblik OZ - Celery Beat" cmd /k "cd /d "%~dp0backend" && call venv\Scripts\activate.bat && celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler"

timeout /t 2 /nobreak >nul

:: -------------------------------------------------
:: Zapusk Celery Worker (vykonavets zadach)
:: -------------------------------------------------
echo Zapusk Celery Worker...
echo Natysnit Ctrl+C dlya zupynky
echo.
celery -A config worker --loglevel=info --pool=solo
pause
