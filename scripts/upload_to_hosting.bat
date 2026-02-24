@echo off
chcp 65001 >nul
echo ========================================
echo   Загрузка файлов на хостинг seidorun.ru
echo ========================================
echo.

cd /d "%~dp0"

echo Запуск скрипта загрузки...
echo.

python upload_to_hosting.py

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Загрузка завершилась с ошибкой
    echo Проверьте настройки FTP в файле bot\.env
) else (
    echo.
    echo [OK] Загрузка завершена!
)

echo.
pause
