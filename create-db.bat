@echo off
chcp 65001 >nul
echo ============================================
echo   Create PostgreSQL database
echo ============================================
echo.

set /p PGUSER="PostgreSQL user (default: postgres): "
if "%PGUSER%"=="" set PGUSER=postgres

set /p PGHOST="Host (default: localhost): "
if "%PGHOST%"=="" set PGHOST=localhost

set /p PGPORT="Port (default: 5432): "
if "%PGPORT%"=="" set PGPORT=5432

echo.
echo Creating database buh_assets...
psql -U %PGUSER% -h %PGHOST% -p %PGPORT% -c "CREATE DATABASE buh_assets ENCODING 'UTF8';"

if %errorlevel% equ 0 (
    echo.
    echo Database buh_assets created successfully!
) else (
    echo.
    echo Database may already exist or connection failed.
    echo Create manually: CREATE DATABASE buh_assets;
)

echo.
pause
