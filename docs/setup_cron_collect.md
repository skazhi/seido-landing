# Cron: автоматический сбор результатов

Запуск `collect_results` раз в неделю (воскресенье 03:00):

```bash
# Открыть crontab
crontab -e

# Добавить строку (подставь свой путь к проекту):
0 3 * * 0 cd /home/skazhi/Документы/seido-landing && .venv/bin/python -m bot.scripts.collect_results --exclude-rr-5verst-s95 --runc-limit 200 --raceresult-limit 100 >> /tmp/seido-collect.log 2>&1
```
