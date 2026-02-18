@echo off
echo ================================================
echo   Oblik OZ -- Stvorennya bazy danykh
echo ================================================
echo.

:: -------------------------------------------------
:: Perevirka psql
:: -------------------------------------------------
where psql >nul 2>&1
if %errorlevel% neq 0 (
    echo [POMYLKA] psql ne znajdeno v PATH!
    echo.
    echo   Dodajte shlyakh do PostgreSQL bin u zminnu PATH:
    echo   Typovyj shlyakh: C:\Program Files\PostgreSQL\16\bin
    echo.
    echo   Abo stvorit bazu vruchnu cherez pgAdmin:
    echo   CREATE DATABASE buh_assets ENCODING 'UTF8';
    echo.
    pause
    exit /b 1
)

:: -------------------------------------------------
:: Chytannya nalashtuvan z .env
:: -------------------------------------------------
set "PGUSER=postgres"
set "PGHOST=localhost"
set "PGPORT=5432"

if exist "%~dp0backend\.env" (
    echo Chytayu nalashtuvannya z backend\.env...
    for /f "tokens=1,* delims==" %%a in ('findstr "POSTGRES_USER" "%~dp0backend\.env"') do set "PGUSER=%%b"
    for /f "tokens=1,* delims==" %%a in ('findstr "POSTGRES_HOST" "%~dp0backend\.env"') do set "PGHOST=%%b"
    for /f "tokens=1,* delims==" %%a in ('findstr "POSTGRES_PORT" "%~dp0backend\.env"') do set "PGPORT=%%b"
    echo   Korystuvach: %PGUSER%
    echo   Khost: %PGHOST%:%PGPORT%
) else (
    echo [UVAGA] backend\.env ne znajdeno, vykorystovuyu znachennya za zamovchuvanniam.
    echo   Korystuvach: postgres, Khost: localhost:5432
)
echo.

:: -------------------------------------------------
:: Stvorennya bazy danykh
:: -------------------------------------------------
echo Stvorennya bazy danykh buh_assets...
psql -U %PGUSER% -h %PGHOST% -p %PGPORT% -c "CREATE DATABASE buh_assets ENCODING 'UTF8';"

if %errorlevel% equ 0 (
    echo.
    echo [OK] Baza danykh buh_assets stvorena uspishno!
) else (
    echo.
    echo [UVAGA] Baza danykh vzhe isnuye abo ne vdalosya stvoryty.
    echo   Mozhlyvi prychyny:
    echo   1. Baza buh_assets vzhe isnuye (ce normalno)
    echo   2. PostgreSQL ne zapushchenyj
    echo   3. Nevirnyj parol (pereverte backend\.env)
    echo.
    echo   Stvoryty vruchnu: psql -U postgres -c "CREATE DATABASE buh_assets ENCODING 'UTF8';"
)

echo.
pause
