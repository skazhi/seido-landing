# Скрипт остановки бота Seido
# Обход политики выполнения для текущей сессии
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
Write-Host "Остановка бота Seido..." -ForegroundColor Yellow

# Находим все процессы Python, которые запускают main.py
$processes = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    try {
        $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
        $cmdLine -like "*main.py*"
    } catch {
        $false
    }
}

if ($processes) {
    Write-Host "Найдено процессов бота: $($processes.Count)" -ForegroundColor Cyan
    $processes | ForEach-Object {
        Write-Host "Остановка процесса ID: $($_.Id)" -ForegroundColor Yellow
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 1
    Write-Host "Бот остановлен!" -ForegroundColor Green
} else {
    Write-Host "Процессы бота не найдены." -ForegroundColor Yellow
}

Read-Host "Нажмите Enter для выхода"
