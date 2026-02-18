@echo off
chcp 65001 >nul
echo ╔════════════════════════════════════════════════╗
echo ║   Облiк ОЗ — Повне встановлення з нуля        ║
echo ╚════════════════════════════════════════════════╝
echo.

:: ─────────────────────────────────────────────
:: 1. Перевірка Python
:: ─────────────────────────────────────────────
echo [1/8] Перевiрка Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ПОМИЛКА] Python не знайдено!
    echo   Встановiть Python 3.11+ з https://www.python.org/downloads/
    echo   При встановленнi обов'язково поставте галочку "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do echo   Знайдено: Python %%v
echo.

:: ─────────────────────────────────────────────
:: 2. Перевірка Node.js
:: ─────────────────────────────────────────────
echo [2/8] Перевiрка Node.js...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ПОМИЛКА] Node.js не знайдено!
    echo   Встановiть Node.js 18+ з https://nodejs.org/
    echo.
    pause
    exit /b 1
)
for /f "tokens=1 delims= " %%v in ('node --version 2^>^&1') do echo   Знайдено: Node.js %%v
echo.

:: ─────────────────────────────────────────────
:: 3. Перевірка PostgreSQL
:: ─────────────────────────────────────────────
echo [3/8] Перевiрка PostgreSQL...
where psql >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [УВАГА] psql не знайдено в PATH.
    echo   Якщо PostgreSQL встановлений, додайте шлях до bin у змiнну PATH.
    echo   Типовий шлях: C:\Program Files\PostgreSQL\16\bin
    echo.
    echo   Або створiть базу даних вручну:
    echo   CREATE DATABASE buh_assets ENCODING 'UTF8';
    echo.
    set SKIP_DB=1
) else (
    for /f "tokens=3 delims= " %%v in ('psql --version 2^>^&1') do echo   Знайдено: PostgreSQL %%v
    set SKIP_DB=0
)
echo.

:: ─────────────────────────────────────────────
:: 4. Налаштування .env
:: ─────────────────────────────────────────────
echo [4/8] Налаштування конфiгурацiї...
cd /d "%~dp0backend"

if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo   Створено .env з шаблону .env.example
    ) else (
        echo   Створюю .env з налаштуваннями за замовчуванням...
        (
            echo ## Налаштування системи облiку основних засобiв
            echo.
            echo # Django
            echo DJANGO_SECRET_KEY=django-insecure-auto-generated-%RANDOM%%RANDOM%%RANDOM%
            echo DEBUG=True
            echo.
            echo # PostgreSQL
            echo POSTGRES_DB=buh_assets
            echo POSTGRES_USER=postgres
            echo POSTGRES_PASSWORD=your_password_here
            echo POSTGRES_HOST=localhost
            echo POSTGRES_PORT=5432
            echo.
            echo # CORS
            echo CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
        ) > .env
    )
    echo.
    echo   *** ВАЖЛИВО: вiдредагуйте backend\.env ***
    echo   Встановiть пароль PostgreSQL (POSTGRES_PASSWORD)
    echo.
    notepad .env
    echo   Натиснiть будь-яку клавiшу пiсля збереження .env...
    pause >nul
) else (
    echo   .env вже iснує — пропускаю.
)
echo.

:: ─────────────────────────────────────────────
:: 5. Python venv + залежності
:: ─────────────────────────────────────────────
echo [5/8] Створення Python-середовища та встановлення залежностей...

if exist "venv" (
    echo   Видаляю старе середовище...
    rmdir /s /q venv
)
python -m venv venv
if %errorlevel% neq 0 (
    echo [ПОМИЛКА] Не вдалося створити вiртуальне середовище
    pause
    exit /b 1
)
echo   Вiртуальне середовище створено.

call venv\Scripts\activate.bat
echo   Оновлення pip...
python -m pip install --upgrade pip --quiet
echo   Встановлення Python-залежностей (це може зайняти кiлька хвилин)...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo.
    echo [ПОМИЛКА] Не вдалося встановити Python-залежностi
    echo   Спробуйте вручну: cd backend ^& venv\Scripts\activate ^& pip install -r requirements.txt
    pause
    exit /b 1
)
echo   Python-залежностi встановлено.
echo.

:: ─────────────────────────────────────────────
:: 6. Створення бази даних
:: ─────────────────────────────────────────────
echo [6/8] Створення бази даних та мiграцiї...

:: Спробувати створити БД якщо psql доступний
if "%SKIP_DB%"=="0" (
    echo   Спроба створити базу даних buh_assets...

    :: Читаємо дані з .env
    for /f "tokens=1,* delims==" %%a in ('findstr "POSTGRES_USER" .env') do set "PGUSER=%%b"
    for /f "tokens=1,* delims==" %%a in ('findstr "POSTGRES_HOST" .env') do set "PGHOST=%%b"
    for /f "tokens=1,* delims==" %%a in ('findstr "POSTGRES_PORT" .env') do set "PGPORT=%%b"

    psql -U %PGUSER% -h %PGHOST% -p %PGPORT% -c "CREATE DATABASE buh_assets ENCODING 'UTF8';" 2>nul
    if %errorlevel% equ 0 (
        echo   База даних buh_assets створена.
    ) else (
        echo   База даних вже iснує або не вдалося створити — продовжую.
    )
)

echo   Виконання мiграцiй...
python manage.py makemigrations accounts assets documents reports 2>nul
python manage.py migrate
if %errorlevel% neq 0 (
    echo.
    echo [ПОМИЛКА] Мiграцiї не вдалися. Перевiрте:
    echo   1. PostgreSQL запущений
    echo   2. База даних buh_assets iснує
    echo   3. Налаштування в backend\.env коректнi
    echo.
    echo   Створити БД вручну: psql -U postgres -c "CREATE DATABASE buh_assets;"
    pause
    exit /b 1
)
echo   Мiграцiї виконано успiшно.
echo.

:: ─────────────────────────────────────────────
:: 7. Початкові дані + суперкористувач
:: ─────────────────────────────────────────────
echo [7/8] Заповнення початкових даних...
python manage.py seed_asset_groups
echo   16 груп ОЗ згiдно ПКУ ст. 138.3.3 створено.
echo.

echo   Створення суперкористувача (адмiнiстратора):
echo   Введiть логiн, email та пароль
echo.
python manage.py createsuperuser
echo.

:: ─────────────────────────────────────────────
:: 8. Frontend
:: ─────────────────────────────────────────────
echo [8/8] Встановлення frontend-залежностей...
cd /d "%~dp0frontend"

if exist "node_modules" (
    echo   Видаляю старi node_modules...
    rmdir /s /q node_modules
)

call npm install
if %errorlevel% neq 0 (
    echo.
    echo [ПОМИЛКА] npm install не вдався
    echo   Спробуйте вручну: cd frontend ^& npm install
    pause
    exit /b 1
)
echo   Frontend-залежностi встановлено.
echo.

:: ─────────────────────────────────────────────
:: Готово!
:: ─────────────────────────────────────────────
echo.
echo ╔════════════════════════════════════════════════╗
echo ║   Встановлення завершено успiшно!              ║
echo ╚════════════════════════════════════════════════╝
echo.
echo   Для запуску системи:
echo.
echo     start.bat          — запустити Backend + Frontend
echo     start-backend.bat  — тiльки Django сервер
echo     start-frontend.bat — тiльки React dev-сервер
echo     stop.bat           — зупинити все
echo.
echo   Вiдкрийте: http://localhost:5173
echo.
pause
