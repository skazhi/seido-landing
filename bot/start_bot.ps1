# Скрипт запуска бота Seido с логированием
# Обход политики выполнения для текущей сессии
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Запуск бота Seido" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Переходим в директорию скрипта
Set-Location $PSScriptRoot

# Проверяем, не запущен ли уже бот
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*python*" -and 
    (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine -like "*main.py*"
}

if ($pythonProcesses) {
    Write-Host "[ОШИБКА] Бот уже запущен!" -ForegroundColor Red
    Write-Host "Остановите предыдущий процесс перед запуском." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Запущенные процессы:" -ForegroundColor Yellow
    $pythonProcesses | Format-Table Id, ProcessName, StartTime -AutoSize
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

Write-Host "Запуск бота..." -ForegroundColor Green
Write-Host "Логи сохраняются в папке: logs\" -ForegroundColor Yellow
Write-Host "Для остановки нажмите Ctrl+C" -ForegroundColor Yellow
Write-Host ""

# Запускаем бота
try {
    python main.py
} catch {
    Write-Host "[ОШИБКА] Не удалось запустить бота: $_" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

Read-Host "Нажмите Enter для выхода"
