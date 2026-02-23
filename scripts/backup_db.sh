#!/bin/bash
# Бэкап БД Seido. Запускать по cron ежедневно.
set -e
PROJECT_DIR="${PROJECT_DIR:-/home/skazhi/Документы/seido-landing}"
BACKUP_DIR="${PROJECT_DIR}/backups"
DB_PATH="${PROJECT_DIR}/bot/seido.db"
mkdir -p "$BACKUP_DIR"
DATE=$(date +%Y-%m-%d_%H-%M)
cp "$DB_PATH" "${BACKUP_DIR}/seido_${DATE}.db"
# Хранить последние 7 копий
ls -t "$BACKUP_DIR"/seido_*.db 2>/dev/null | tail -n +8 | xargs -r rm --
