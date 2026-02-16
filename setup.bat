@echo off
chcp 65001 >nul
echo ============================================
echo   Oblik OZ - Pochatkove nalashtuvannia
echo ============================================
echo.

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found! Install Python 3.12+
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found! Install Node.js 20+
    echo https://nodejs.org/
    pause
    exit /b 1
)

echo [1/7] Checking .env file...
cd /d "%~dp0backend"
if not exist ".env" (
    echo [!] .env file not found!
    echo Copying from .env.example...
    copy .env.example .env >nul
    echo.
    echo *** Edit backend\.env - set your PostgreSQL password ***
    echo.
    notepad .env
    echo Press any key after saving .env...
    pause >nul
)

echo.
echo [2/7] Creating Python virtual environment...
if not exist "venv" (
    python -m venv venv
    echo Virtual environment created.
) else (
    echo Virtual environment already exists.
)

echo.
echo [3/7] Installing Python dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Python dependencies
    pause
    exit /b 1
)

echo.
echo [4/7] Running migrations...
python manage.py makemigrations accounts assets
python manage.py migrate
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Migrations failed. Check:
    echo   1. PostgreSQL is running
    echo   2. Database exists: CREATE DATABASE buh_assets;
    echo   3. Settings in backend\.env are correct
    pause
    exit /b 1
)

echo.
echo [5/7] Seeding asset groups...
python manage.py seed_asset_groups

echo.
echo [6/7] Creating superuser...
python manage.py createsuperuser

echo.
echo [7/7] Installing frontend npm dependencies...
cd /d "%~dp0frontend"
call npm install
if %errorlevel% neq 0 (
    echo [ERROR] npm install failed
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Setup complete!
echo ============================================
echo.
echo   start-backend.bat  - run Django server
echo   start-frontend.bat - run React dev server
echo   start.bat          - run both
echo.
echo   Open http://localhost:5173
echo.
pause
