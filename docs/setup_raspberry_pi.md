# Seido: развёртывание на Raspberry Pi (24/7 бесплатно)

## Требования

- Raspberry Pi 5 (или Pi 4 с 2+ ГБ RAM)
- Raspberry Pi OS (64-bit) — лучше Bookworm
- SSH-доступ к Pi
- Pi подключён к интернету и питанию 24/7

---

## 1. Подключение по SSH

```bash
ssh pi@<IP_АДРЕС_PI>
# или: ssh pi@raspberrypi.local
```

---

## 2. Обновление системы

```bash
sudo apt update && sudo apt upgrade -y
```

---

## 3. Установка зависимостей

```bash
sudo apt install -y python3.11 python3.11-venv python3-pip git

# Для Playwright (парсеры)
sudo apt install -y libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 libpango-1.0-0 libcairo2
```

---

## 4. Клонирование репозитория

```bash
cd /home/pi
git clone https://github.com/skazhi/seido-landing.git
cd seido-landing
```

---

## 5. Виртуальное окружение и зависимости

```bash
cd /home/pi/seido-landing

python3.11 -m venv .venv
source .venv/bin/activate

pip install -r bot/requirements.txt

# Playwright Chromium (может занять несколько минут)
playwright install chromium
playwright install-deps
```

---

## 6. Настройка .env

```bash
cd /home/pi/seido-landing/bot
nano .env
```

Содержимое:
```
BOT_TOKEN=твой_токен_от_BotFather
ADMIN_ID=твой_telegram_id
HEALTHCHECK_URL=https://hc-ping.com/xxx
```

Сохранить: Ctrl+O, Enter, Ctrl+X.

---

## 7. Перенос БД (если есть данные с компьютера)

На **локальном компьютере**:
```bash
scp /home/skazhi/Документы/seido-landing/bot/seido.db pi@<IP_PI>:/home/pi/seido-landing/bot/
```

---

## 8. Проверка запуска

```bash
cd /home/pi/seido-landing/bot
source ../.venv/bin/activate
python main.py
```

Убедиться, что бот запускается. Ctrl+C для остановки.

---

## 9. Systemd — автозапуск 24/7

```bash
sudo nano /etc/systemd/system/seido-bot.service
```

Содержимое:
```ini
[Unit]
Description=Seido Telegram Bot
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/seido-landing/bot
Environment="PATH=/home/pi/seido-landing/.venv/bin"
ExecStart=/home/pi/seido-landing/.venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable seido-bot
sudo systemctl start seido-bot
sudo systemctl status seido-bot
```

Логи: `journalctl -u seido-bot -f`

---

## 10. Cron

```bash
crontab -e
```

Добавить:
```cron
0 2 * * * PROJECT_DIR=/home/pi/seido-landing /home/pi/seido-landing/scripts/backup_db.sh >> /tmp/seido-backup.log 2>&1
0 3 * * 0 cd /home/pi/seido-landing && .venv/bin/python -m bot.scripts.collect_results --exclude-rr-5verst-s95 --runc-limit 200 --raceresult-limit 100 >> /tmp/seido-collect.log 2>&1
```

---

## 11. Обновление кода

```bash
cd /home/pi/seido-landing
git pull
sudo systemctl restart seido-bot
```

---

## Замечания

- **Статический IP** — в роутере закрепи IP за Pi, чтобы не потерять доступ.
- **Wake-on-LAN** — не нужен, Pi обычно всегда включён.
- **Температура** — Pi 5 может греться под нагрузкой; при необходимости — радиатор/вентилятор.
- **Резервное питание** — при частых отключениях света желательно ИБП.
