@echo off
echo ================================================
echo   Oblik OZ -- Zapusk systemy
echo ================================================
echo.

:: -------------------------------------------------
:: Perevirka nayavnosti vstanovlennya
:: -------------------------------------------------
if not exist "%~dp0backend\venv" (
    echo [POMYLKA] Backend ne vstanovleno!
    echo   Spochatku zapustit: setup.bat
    echo.
    pause
    exit /b 1
)
if not exist "%~dp0frontend\node_modules" (
    echo [POMYLKA] Frontend ne vstanovleno!
    echo   Spochatku zapustit: setup.bat
    echo.
    pause
    exit /b 1
)

:: -------------------------------------------------
:: Zapusk Backend
:: -------------------------------------------------
echo Zapusk Backend (Django)...
start "Oblik OZ - Backend" cmd /k ""%~dp0start-backend.bat""

:: Chekayemo poky backend pidnimayetsya
echo Ochikuvannya zapusku backend...
timeout /t 3 /nobreak >nul

:: -------------------------------------------------
:: Zapusk Frontend
:: -------------------------------------------------
echo Zapusk Frontend (React)...
start "Oblik OZ - Frontend" cmd /k ""%~dp0start-frontend.bat""

:: Chekayemo poky frontend pidnimayetsya
timeout /t 5 /nobreak >nul

:: -------------------------------------------------
:: Gotovo
:: -------------------------------------------------
echo.
echo ================================================
echo   Systema zapushchena!
echo ================================================
echo.
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo   Admin:    http://localhost:8000/admin/
echo.
echo   Dlya zupynky: stop.bat
echo.

:: Vidkryvayemo brauzer
start http://localhost:5173

pause
