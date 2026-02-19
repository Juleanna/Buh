@echo off
setlocal enabledelayedexpansion

echo ================================================
echo   Oblik OZ -- Onovlennya roli superkorystuvachiv
echo ================================================
echo.

:: -------------------------------------------------
:: Chytayemo konfiguratsiyu z .env
:: -------------------------------------------------
set "ENV_FILE=%~dp0backend\.env"

if not exist "%ENV_FILE%" (
    echo [POMYLKA] Fajl .env ne znajdeno: %ENV_FILE%
    echo   Spochatku zapustit: setup.bat
    pause
    exit /b 1
)

:: Znachennya za zamovchuvanniam
set "POSTGRES_DB=buh_assets"
set "POSTGRES_USER=postgres"
set "POSTGRES_PASSWORD=postgres"
set "POSTGRES_HOST=localhost"
set "POSTGRES_PORT=5432"

:: Parsymo .env fajl
for /f "usebackq tokens=1,* delims==" %%a in ("%ENV_FILE%") do (
    set "line=%%a"
    if not "!line:~0,1!"=="#" (
        if "%%a"=="POSTGRES_DB" set "POSTGRES_DB=%%b"
        if "%%a"=="POSTGRES_USER" set "POSTGRES_USER=%%b"
        if "%%a"=="POSTGRES_PASSWORD" set "POSTGRES_PASSWORD=%%b"
        if "%%a"=="POSTGRES_HOST" set "POSTGRES_HOST=%%b"
        if "%%a"=="POSTGRES_PORT" set "POSTGRES_PORT=%%b"
    )
)

echo   Baza danykh: %POSTGRES_DB% @ %POSTGRES_HOST%:%POSTGRES_PORT%
echo.

:: -------------------------------------------------
:: Perevirka psql
:: -------------------------------------------------
where psql >nul 2>&1
if %errorlevel% neq 0 (
    echo [POMYLKA] psql ne znajdeno v PATH
    echo   Dodajte shlyakh do PostgreSQL\bin u zminnu PATH
    echo   Typovyj shlyakh: C:\Program Files\PostgreSQL\16\bin
    pause
    exit /b 1
)

:: -------------------------------------------------
:: Vykonannya SQL zapytu
:: -------------------------------------------------
echo Onovlennya roli superkorystuvachiv na "admin"...
set "PGPASSWORD=%POSTGRES_PASSWORD%"

psql -h %POSTGRES_HOST% -p %POSTGRES_PORT% -U %POSTGRES_USER% -d %POSTGRES_DB% -c "UPDATE accounts_user SET role = 'admin' WHERE is_superuser = true AND role != 'admin';"

if %errorlevel%==0 (
    echo.
    echo [OK] Rol superkorystuvachiv onovleno do "admin"
) else (
    echo.
    echo [POMYLKA] Ne vdalosya vykonaty SQL zapyt
    echo   Pereverte shcho PostgreSQL zapushcheno ta dani v .env korektni
)

echo.
pause
endlocal
