@echo off
chcp 65001 >nul
echo ============================================
echo   Oblik OZ - Starting...
echo ============================================
echo.

echo Starting Backend...
start "Oblik OZ - Backend" cmd /k ""%~dp0start-backend.bat""

timeout /t 3 /nobreak >nul

echo Starting Frontend...
start "Oblik OZ - Frontend" cmd /k ""%~dp0start-frontend.bat""

timeout /t 5 /nobreak >nul

echo.
echo ============================================
echo   System is running!
echo ============================================
echo.
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo   Admin:    http://localhost:8000/admin/
echo.
echo   To stop: run stop.bat
echo.

start http://localhost:5173

pause
