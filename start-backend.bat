@echo off
chcp 65001 >nul
title Oblik OZ - Backend
echo ============================================
echo   Django Backend - http://localhost:8000
echo ============================================
echo.

cd /d "%~dp0backend"
call venv\Scripts\activate.bat

echo Applying migrations...
python manage.py migrate --run-syncdb

echo.
echo Starting Django server...
echo Press Ctrl+C to stop
echo.
python manage.py runserver 0.0.0.0:8000
pause
