"""
Seido Bot - Главный файл запуска
"""
import asyncio
import logging
import sys

# Исправление кодировки для Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from aiogram import Bot, Dispatcher
from config import BOT_TOKEN, PROJECT_NAME
from db import db
from handlers import router

# Настройка логгирования
logging.basicConfig(level=logging.INFO, format="%(message)s")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Регистрируем роутер с обработчиками
dp.include_router(router)


async def on_startup():
    """Действия при запуске"""
    print(f"\n🚀 Запуск бота {PROJECT_NAME}...")
    await db.connect()
    print(f"✅ Бот {PROJECT_NAME} запущен!\n")


async def on_shutdown():
    """Действия при остановке"""
    print(f"\n🛑 Остановка бота {PROJECT_NAME}...")
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
