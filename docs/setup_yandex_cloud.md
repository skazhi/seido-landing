# Seido: развёртывание на Yandex Cloud

## 1. Регистрация и создание VM

1. Перейди на https://console.cloud.yandex.ru
2. Регистрация (если ещё нет) — нужна карта для free tier (средства не списываются в рамках триала)
3. Создать каталог → **Compute Cloud** → **Создать ВМ**

**Рекомендуемая конфигурация:**
- **Платформа:** Intel Broadwell
- **vCPU:** 2
- **Память:** 2 ГБ
- **Диск:** 10 ГБ (Ubuntu 22.04 LTS)
- **Зона:** ru-central1-a (или ближайшая)
- **Сеть:** по умолчанию, выдать публичный IP
- **Логин:** `ubuntu` (или свой)

4. После создания — скопировать **публичный IP** и **приватный ключ** (если создавал при старте ВМ).

---

## 2. Подключение по SSH

```bash
ssh ubuntu@<ПУБЛИЧНЫЙ_IP>
# или с указанием ключа:
ssh -i ~/.ssh/ya_key ubuntu@<ПУБЛИЧНЫЙ_IP>
```

---

## 3. Установка зависимостей на сервере

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip git
# Playwright для парсеров
sudo apt install -y libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2
```

---

## 4. Клонирование репозитория

```bash
cd ~
git clone https://github.com/skazhi/seido-landing.git
cd seido-landing
```

---

## 5. Настройка окружения

```bash
cd ~/seido-landing

# Виртуальное окружение
python3.11 -m venv .venv
source .venv/bin/activate

# Зависимости
pip install -r bot/requirements.txt

# Playwright Chromium
playwright install chromium
playwright install-deps  # если нужны системные библиотеки
```

---

## 6. Создание .env

```bash
cd ~/seido-landing/bot
nano .env
```

Содержимое:
```
BOT_TOKEN=твой_токен_от_BotFather
ADMIN_ID=твой_telegram_id
HEALTHCHECK_URL=https://hc-ping.com/xxx  # опционально
```

Сохранить: Ctrl+O, Enter, Ctrl+X.

---

## 7. Перенос БД (если уже есть данные)

С локальной машины:
```bash
scp /home/skazhi/Документы/seido-landing/bot/seido.db ubuntu@<IP>:~/seido-landing/bot/
```

Или скопировать `backups/` и взять последний бэкап.

---

## 8. Проверка запуска

```bash
cd ~/seido-landing/bot
source ../.venv/bin/activate
python main.py
```

Убедиться, что бот запускается. Остановить: Ctrl+C.

---

## 9. Systemd — автозапуск и перезапуск при падении

```bash
sudo nano /etc/systemd/system/seido-bot.service
```

Содержимое (подставь свой пользователь — скорее всего `ubuntu`):
```ini
[Unit]
Description=Seido Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/seido-landing/bot
Environment="PATH=/home/ubuntu/seido-landing/.venv/bin"
ExecStart=/home/ubuntu/seido-landing/.venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Активация:
```bash
sudo systemctl daemon-reload
sudo systemctl enable seido-bot
sudo systemctl start seido-bot
sudo systemctl status seido-bot
```

Логи: `journalctl -u seido-bot -f`

---

## 10. Cron: бэкап и сбор результатов

```bash
crontab -e
```

Добавить:
```cron
0 2 * * * PROJECT_DIR=/home/ubuntu/seido-landing /home/ubuntu/seido-landing/scripts/backup_db.sh >> /tmp/seido-backup.log 2>&1
0 3 * * 0 cd /home/ubuntu/seido-landing && .venv/bin/python -m bot.scripts.collect_results --exclude-rr-5verst-s95 --runc-limit 200 --raceresult-limit 100 >> /tmp/seido-collect.log 2>&1
```

*Скрипт бэкапа использует `PROJECT_DIR` из окружения — в cron уже указан корректный путь.*

---

## 11. Обновление кода с GitHub

```bash
cd ~/seido-landing
git pull
sudo systemctl restart seido-bot
```

---

## Чеклист

- [ ] VM создана, есть публичный IP
- [ ] SSH-подключение работает
- [ ] Python 3.11, venv, git установлены
- [ ] Репозиторий склонирован
- [ ] .env создан с BOT_TOKEN и ADMIN_ID
- [ ] БД перенесена (если нужна)
- [ ] `python main.py` запускается без ошибок
- [ ] systemd настроен, бот работает 24/7
- [ ] Cron для бэкапа и сбора настроен
