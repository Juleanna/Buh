@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ╔════════════════════════════════════════════════╗
echo ║   Облiк ОЗ — Встановлення програм              ║
echo ║   Python, Node.js, PostgreSQL                   ║
echo ╚════════════════════════════════════════════════╝
echo.

:: ─────────────────────────────────────────────
:: 1. Перевірка прав адміністратора
:: ─────────────────────────────────────────────
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [УВАГА] Потрiбнi права адмiнiстратора для встановлення програм.
    echo Перезапуск з правами адмiнiстратора...
    echo.
    powershell -Command "Start-Process cmd -ArgumentList '/c cd /d \"%~dp0\" && \"%~f0\"' -Verb RunAs"
    exit /b
)

echo [OK] Права адмiнiстратора пiдтверджено.
echo.

:: ─────────────────────────────────────────────
:: 2. Перевірка winget
:: ─────────────────────────────────────────────
echo [1/6] Перевiрка Windows Package Manager (winget)...

winget --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ПОМИЛКА] winget не знайдено!
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('winget --version') do echo   Знайдено: winget %%v
echo.

:: ─────────────────────────────────────────────
:: 3. Python
:: ─────────────────────────────────────────────
echo [2/6] Перевiрка Python...
set "PYTHON_INSTALLED=0"
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do (
        echo   Вже встановлено: Python %%v
        set "PYTHON_INSTALLED=1"
    )
)

if "!PYTHON_INSTALLED!"=="0" (
    echo   Python не знайдено. Встановлення Python 3.12...
    echo.
    winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    if !errorlevel! neq 0 (
        echo.
        echo [ПОМИЛКА] Не вдалося встановити Python.
        echo   Спробуйте вручну: https://www.python.org/downloads/
        echo   При встановленнi поставте галочку "Add Python to PATH"
        echo.
    ) else (
        echo   Python 3.12 встановлено.
        call :RefreshPath
    )
)
echo.

:: ─────────────────────────────────────────────
:: 4. Node.js
:: ─────────────────────────────────────────────
echo [3/6] Перевiрка Node.js...
set "NODE_INSTALLED=0"
where node >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=1 delims= " %%v in ('node --version 2^>^&1') do (
        echo   Вже встановлено: Node.js %%v
        set "NODE_INSTALLED=1"
    )
)

if "!NODE_INSTALLED!"=="0" (
    echo   Node.js не знайдено. Встановлення Node.js LTS...
    echo.
    winget install OpenJS.NodeJS.LTS --silent --accept-package-agreements --accept-source-agreements
    if !errorlevel! neq 0 (
        echo.
        echo [ПОМИЛКА] Не вдалося встановити Node.js.
        echo   Спробуйте вручну: https://nodejs.org/
        echo.
    ) else (
        echo   Node.js LTS встановлено.
        call :RefreshPath
    )
)
echo.

:: ─────────────────────────────────────────────
:: 5. PostgreSQL
:: ─────────────────────────────────────────────
echo [4/6] Перевiрка PostgreSQL...
set "PG_INSTALLED=0"
where psql >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=3 delims= " %%v in ('psql --version 2^>^&1') do (
        echo   Вже встановлено: PostgreSQL %%v
        set "PG_INSTALLED=1"
    )
)

if "!PG_INSTALLED!"=="0" (
    echo   PostgreSQL не знайдено. Встановлення PostgreSQL 16...
    echo.
    echo   [УВАГА] Пiд час встановлення PostgreSQL з'явиться вiкно,
    echo   де потрiбно задати пароль для користувача postgres.
    echo   Запам'ятайте цей пароль — вiн знадобиться для backend\.env
    echo.
    winget install PostgreSQL.PostgreSQL.16 --silent --accept-package-agreements --accept-source-agreements
    if !errorlevel! neq 0 (
        echo.
        echo [ПОМИЛКА] Не вдалося встановити PostgreSQL.
        echo   Спробуйте вручну: https://www.postgresql.org/download/windows/
        echo.
    ) else (
        echo   PostgreSQL 16 встановлено.
        call :RefreshPath

        :: Додати PostgreSQL bin до PATH поточної сесії
        set "PG_BIN=C:\Program Files\PostgreSQL\16\bin"
        if exist "!PG_BIN!\psql.exe" (
            set "PATH=!PATH!;!PG_BIN!"
            echo   Додано до PATH: !PG_BIN!
        )

        :: Перевірити службу
        echo   Перевiрка служби PostgreSQL...
        sc query postgresql-x64-16 >nul 2>&1
        if !errorlevel! equ 0 (
            echo   Служба postgresql-x64-16 знайдена.
            net start postgresql-x64-16 2>nul
        ) else (
            echo   [УВАГА] Служба PostgreSQL не знайдена.
            echo   Можливо потрiбно перезавантажити комп'ютер.
        )
    )
)
echo.

:: ─────────────────────────────────────────────
:: 6. Оновлення PATH та фінальна верифікація
:: ─────────────────────────────────────────────
echo [5/6] Оновлення PATH...
call :RefreshPath

:: Додати PostgreSQL до PATH якщо є на диску але немає в PATH
if exist "C:\Program Files\PostgreSQL\16\bin\psql.exe" (
    echo !PATH! | findstr /i "postgresql" >nul
    if !errorlevel! neq 0 (
        set "PATH=!PATH!;C:\Program Files\PostgreSQL\16\bin"
        echo   Додано PostgreSQL до PATH поточної сесiї.
    )
)
echo.

echo [6/6] Верифiкацiя встановлення...
echo.
echo   ┌──────────────┬───────────────────────────────┐
echo   │ Програма     │ Статус                        │

:: Python
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do (
        echo   │ Python       │ %%v                       │
    )
) else (
    echo   │ Python       │ НЕ ЗНАЙДЕНО                   │
)

:: Node.js
where node >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=1 delims= " %%v in ('node --version 2^>^&1') do (
        echo   │ Node.js      │ %%v                        │
    )
) else (
    echo   │ Node.js      │ НЕ ЗНАЙДЕНО                   │
)

:: PostgreSQL
where psql >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=3 delims= " %%v in ('psql --version 2^>^&1') do (
        echo   │ PostgreSQL   │ %%v                       │
    )
) else (
    if exist "C:\Program Files\PostgreSQL\16\bin\psql.exe" (
        echo   │ PostgreSQL   │ Встановлено, потрiбен restart   │
    ) else (
        echo   │ PostgreSQL   │ НЕ ЗНАЙДЕНО                   │
    )
)

echo   └──────────────┴───────────────────────────────┘
echo.

:: ─────────────────────────────────────────────
:: Перевірка чи все встановлено
:: ─────────────────────────────────────────────
set "ALL_OK=1"
where python >nul 2>&1 || set "ALL_OK=0"
where node >nul 2>&1 || set "ALL_OK=0"

if "!ALL_OK!"=="1" (
    echo ╔════════════════════════════════════════════════╗
    echo ║   Всi програми встановлено!                    ║
    echo ╚════════════════════════════════════════════════╝
    echo.
    echo   Наступний крок — запустити setup.bat для налаштування проєкту.
    echo.
    choice /C YN /M "Запустити setup.bat зараз? (Y/N)"
    if !errorlevel! equ 1 (
        echo.
        call "%~dp0setup.bat"
    )
) else (
    echo.
    echo [УВАГА] Деякi програми не встановлено або не знайдено в PATH.
    echo.
    echo   Можливi рiшення:
    echo   1. Закрийте це вiкно i вiдкрийте нове (для оновлення PATH)
    echo   2. Перезавантажте комп'ютер
    echo   3. Запустiть цей скрипт повторно
    echo.
    echo   Пiсля того як усе встановлено — запустiть setup.bat
    echo.
)

pause
exit /b

:: ─────────────────────────────────────────────
:: Функція: Оновити PATH з реєстру
:: ─────────────────────────────────────────────
:RefreshPath
for /f "tokens=2,*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYS_PATH=%%b"
for /f "tokens=2,*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USR_PATH=%%b"
if defined SYS_PATH if defined USR_PATH (
    set "PATH=!SYS_PATH!;!USR_PATH!"
) else if defined SYS_PATH (
    set "PATH=!SYS_PATH!"
)
exit /b
