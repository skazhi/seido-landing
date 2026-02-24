@echo off
chcp 65001 >nul
echo ========================================
echo   Синхронизация БД на сайт seidorun.ru
echo ========================================
echo.

cd /d "%~dp0"

REM Загружаем переменные окружения из .env (если есть)
if exist "..\.env" (
    echo Загрузка настроек из .env...
    for /f "usebackq tokens=1,2 delims==" %%a in ("..\.env") do (
        if "%%a"=="MYSQL_HOST" set MYSQL_HOST=%%b
        if "%%a"=="MYSQL_USER" set MYSQL_USER=%%b
        if "%%a"=="MYSQL_PASSWORD" set MYSQL_PASSWORD=%%b
        if "%%a"=="MYSQL_DATABASE" set MYSQL_DATABASE=%%b
    )
)

echo Запуск синхронизации...
echo.

python sync_to_mysql.py

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Синхронизация завершилась с ошибкой
    echo Проверьте настройки подключения к MySQL
) else (
    echo.
    echo [OK] Синхронизация завершена успешно!
)

echo.
pause
