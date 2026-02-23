"""
Seido Bot - Главный файл запуска
"""
import asyncio
import logging
import sys
import os
from datetime import datetime

# Исправление кодировки для Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Создаём папку для логов
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Имя файла лога с датой
LOG_FILE = os.path.join(LOG_DIR, f"bot_{datetime.now().strftime('%Y%m%d')}.log")

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from config import BOT_TOKEN, PROJECT_NAME, HEALTHCHECK_URL
from db import db
from handlers import router
from parsers.scheduler import scheduler as parse_scheduler

# Настройка логгирования
# Формат: дата/время - уровень - сообщение
log_format = "%(asctime)s - %(levelname)s - %(message)s"
date_format = "%Y-%m-%d %H:%M:%S"

# Настройка логирования: и в консоль, и в файл
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    datefmt=date_format,
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.MARKDOWN)
dp = Dispatcher()

# Регистрируем роутер с обработчиками
dp.include_router(router)


async def on_startup():
    """Действия при запуске"""
    print(f"\n🚀 Запуск бота {PROJECT_NAME}...")
    await db.connect()

    # Меню команд (видны при нажатии /)
    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="myresults", description="Мои результаты"),
        BotCommand(command="find_result", description="Найти результат по ФИО"),
        BotCommand(command="profile", description="Мой профиль"),
        BotCommand(command="calendar", description="Календарь забегов"),
        BotCommand(command="search", description="Поиск забегов"),
        BotCommand(command="history", description="История забегов"),
        BotCommand(command="compare", description="Сравнение с бегуном"),
        BotCommand(command="addrace", description="Добавить забег"),
        BotCommand(command="stats", description="Статистика"),
        BotCommand(command="help", description="Помощь"),
    ])

    # Запуск планировщика парсинга
    parse_scheduler.start()
    
    # Первичный парсинг забегов
    print("🔄 Запуск первичного парсинга забегов...")
    try:
        results = await parse_scheduler.parse_all()
        total = sum(results.values())
        print(f"✅ Парсинг завершён. Добавлено забегов: {total}")
    except Exception as e:
        print(f"⚠️ Ошибка парсинга: {e}")
    
    # Пинг мониторинга (Healthchecks.io) — раз в 4 мин
    async def _healthcheck_loop():
        if not HEALTHCHECK_URL:
            return
        import aiohttp
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    await session.get(HEALTHCHECK_URL, timeout=aiohttp.ClientTimeout(total=5))
            except Exception:
                pass
            await asyncio.sleep(240)  # 4 мин

    if HEALTHCHECK_URL:
        asyncio.create_task(_healthcheck_loop())

    print(f"✅ Бот {PROJECT_NAME} запущен!\n")


async def on_shutdown():
    """Действия при остановке"""
    print(f"\n🛑 Остановка бота {PROJECT_NAME}...")
    parse_scheduler.stop()
    await db.disconnect()
    await bot.session.close()
    print(f"✅ Бот {PROJECT_NAME} остановлен\n")


async def main():
    """Основная функция"""
    # Регистрируем хуки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Запускаем polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
