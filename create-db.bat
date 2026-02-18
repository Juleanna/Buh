@echo off
chcp 65001 >nul
echo ╔════════════════════════════════════════════════╗
echo ║   Облiк ОЗ — Створення бази даних             ║
echo ╚════════════════════════════════════════════════╝
echo.

:: ─────────────────────────────────────────────
:: Перевірка psql
:: ─────────────────────────────────────────────
where psql >nul 2>&1
if %errorlevel% neq 0 (
    echo [ПОМИЛКА] psql не знайдено в PATH!
    echo.
    echo   Додайте шлях до PostgreSQL bin у змiнну PATH:
    echo   Типовий шлях: C:\Program Files\PostgreSQL\16\bin
    echo.
    echo   Або створiть базу вручну через pgAdmin:
    echo   CREATE DATABASE buh_assets ENCODING 'UTF8';
    echo.
    pause
    exit /b 1
)

:: ─────────────────────────────────────────────
:: Читання налаштувань з .env
:: ─────────────────────────────────────────────
set "PGUSER=postgres"
set "PGHOST=localhost"
set "PGPORT=5432"

if exist "%~dp0backend\.env" (
    echo Читаю налаштування з backend\.env...
    for /f "tokens=1,* delims==" %%a in ('findstr "POSTGRES_USER" "%~dp0backend\.env"') do set "PGUSER=%%b"
    for /f "tokens=1,* delims==" %%a in ('findstr "POSTGRES_HOST" "%~dp0backend\.env"') do set "PGHOST=%%b"
    for /f "tokens=1,* delims==" %%a in ('findstr "POSTGRES_PORT" "%~dp0backend\.env"') do set "PGPORT=%%b"
    echo   Користувач: %PGUSER%
    echo   Хост: %PGHOST%:%PGPORT%
) else (
    echo [УВАГА] backend\.env не знайдено, використовую значення за замовчуванням.
    echo   Користувач: postgres, Хост: localhost:5432
)
echo.

:: ─────────────────────────────────────────────
:: Створення бази даних
:: ─────────────────────────────────────────────
echo Створення бази даних buh_assets...
psql -U %PGUSER% -h %PGHOST% -p %PGPORT% -c "CREATE DATABASE buh_assets ENCODING 'UTF8';"

if %errorlevel% equ 0 (
    echo.
    echo [OK] База даних buh_assets створена успiшно!
) else (
    echo.
    echo [УВАГА] База даних вже iснує або не вдалося створити.
    echo   Можливi причини:
    echo   1. База buh_assets вже iснує (це нормально)
    echo   2. PostgreSQL не запущений
    echo   3. Невiрний пароль (перевiрте backend\.env)
    echo.
    echo   Створити вручну: psql -U postgres -c "CREATE DATABASE buh_assets ENCODING 'UTF8';"
)

echo.
pause
