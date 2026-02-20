@echo off
echo ================================================
echo   Oblik OZ -- Zupynka systemy
echo ================================================
echo.

:: -------------------------------------------------
:: Zakryttya vikon za nazvoyu (z derevom procesiv)
:: -------------------------------------------------
echo Zakryttya vikon Oblik OZ...
taskkill /f /t /fi "WINDOWTITLE eq Oblik OZ*" 2>nul

:: -------------------------------------------------
:: Zakryttya Celery procesiv
:: -------------------------------------------------
echo Zupynka Celery procesiv...
taskkill /f /im celery.exe 2>nul

:: -------------------------------------------------
:: Zakryttya procesiv na portakh
:: -------------------------------------------------
echo Zupynka procesiv na portu 8000 (Django)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /f /t /pid %%a 2>nul
)

echo Zupynka procesiv na portu 5173 (Vite)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /f /t /pid %%a 2>nul
)

echo.
echo Usi servisy zupyneno.
echo.
timeout /t 3 >nul
