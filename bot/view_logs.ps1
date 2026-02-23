# Скрипт просмотра последних логов бота
# Обход политики выполнения для текущей сессии
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Просмотр логов бота Seido" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$logDir = Join-Path $PSScriptRoot "logs"

if (-not (Test-Path $logDir)) {
    Write-Host "[ОШИБКА] Папка логов не найдена: $logDir" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Находим последний файл лога
$logFiles = Get-ChildItem -Path $logDir -Filter "bot_*.log" | Sort-Object LastWriteTime -Descending

if (-not $logFiles) {
    Write-Host "[ИНФО] Файлы логов не найдены." -ForegroundColor Yellow
    Read-Host "Нажмите Enter для выхода"
    exit 0
}

$latestLog = $logFiles[0]
Write-Host "Последний файл лога: $($latestLog.Name)" -ForegroundColor Green
Write-Host "Размер: $([math]::Round($latestLog.Length / 1KB, 2)) KB" -ForegroundColor Cyan
Write-Host "Дата изменения: $($latestLog.LastWriteTime)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Последние 50 строк лога:" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Gray

# Показываем последние 50 строк
Get-Content -Path $latestLog.FullName -Tail 50 -Encoding UTF8

Write-Host ""
Write-Host "----------------------------------------" -ForegroundColor Gray
Write-Host "Для просмотра полного лога откройте файл:" -ForegroundColor Cyan
Write-Host $latestLog.FullName -ForegroundColor White

Read-Host "`nНажмите Enter для выхода"
