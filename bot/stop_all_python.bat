@echo off
chcp 65001 >nul
echo ========================================
echo   Остановка всех процессов Python
echo ========================================
echo.

REM Останавливаем все процессы Python
taskkill /F /IM python.exe 2>NUL

if %ERRORLEVEL%==0 (
    echo [OK] Все процессы Python остановлены
) else (
    echo [ИНФО] Процессы Python не найдены или уже остановлены
)

echo.
pause
