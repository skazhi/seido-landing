import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота от @BotFather
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Админы бота (Telegram ID)
ADMINS = [
    int(os.getenv('ADMIN_ID', 0)),  # Твой ID
]

# Названия проекта
PROJECT_NAME = "Seido"
PROJECT_TAGLINE = "Засейди свои результаты"

# Мониторинг: URL от Healthchecks.io (опционально)
HEALTHCHECK_URL = os.getenv("HEALTHCHECK_URL", "").strip()
