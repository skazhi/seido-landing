@echo off
chcp 65001 >nul
echo ========================================
echo   Запуск бота Seido
echo ========================================
echo.

cd /d "%~dp0"

REM Проверяем, не запущен ли уже бот
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" 2^>NUL ^| find /I "python.exe"') do (
    echo [ПРОВЕРКА] Найден процесс Python
    echo Проверяем, не является ли это ботом...
)

REM Простая проверка - если python.exe запущен, предупреждаем
tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find /I "python.exe" >NUL
if "%ERRORLEVEL%"=="0" (
    echo [ВНИМАНИЕ] Обнаружены запущенные процессы Python
    echo Убедитесь, что предыдущий экземпляр бота остановлен
    echo.
    choice /C YN /M "Продолжить запуск"
    if errorlevel 2 exit /b 1
    echo.
)

echo Запуск бота...
echo Логи сохраняются в папке: logs\
echo Для остановки нажмите Ctrl+C
echo.

REM Создаём папку для логов, если её нет
if not exist "logs" mkdir logs

python main.py

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Бот завершился с ошибкой
    echo Проверьте логи в папке logs\
)

pause
