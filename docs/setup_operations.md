# Seido: бэкап, мониторинг, cron

## 1. Бэкап БД

Ежедневный бэкап (02:00):

```bash
crontab -e

# Добавить:
0 2 * * * /home/skazhi/Документы/seido-landing/scripts/backup_db.sh >> /tmp/seido-backup.log 2>&1
```

Проверить: `ls -la ~/Документы/seido-landing/backups/`

---

## 2. Мониторинг (бесплатно)

**Healthchecks.io** — пинг каждые 4 мин, алерт если бот упал:
- Регистрация: https://healthchecks.io
- Создать check, period = 10 min, grace = 5 min
- Скопировать URL (например `https://hc-ping.com/xxxxxxxx-xxxx-xxxx`)
- В `.env` добавить: `HEALTHCHECK_URL=https://hc-ping.com/xxx...`

**UptimeRobot** (бесплатно 50 мониторов):
- Регистрация: https://uptimerobot.com
- Мониторить Telegram Bot API или свой health-endpoint (если будет)

*Пока бот без веб-сервера — UptimeRobot не сможет проверить «живость» бота напрямую. Проще всего: добавить в бота периодический ping в Healthchecks.io.*

---

## 3. Cron: сбор результатов

Раз в неделю (воскресенье 03:00):

```bash
crontab -e

# Добавить:
0 3 * * 0 cd /home/skazhi/Документы/seido-landing && .venv/bin/python -m bot.scripts.collect_results --exclude-rr-5verst-s95 --runc-limit 200 --raceresult-limit 100 >> /tmp/seido-collect.log 2>&1
```

---

## Итоговый crontab

```cron
0 2 * * * /home/skazhi/Документы/seido-landing/scripts/backup_db.sh >> /tmp/seido-backup.log 2>&1
0 3 * * 0 cd /home/skazhi/Документы/seido-landing && .venv/bin/python -m bot.scripts.collect_results --exclude-rr-5verst-s95 --runc-limit 200 --raceresult-limit 100 >> /tmp/seido-collect.log 2>&1
```
