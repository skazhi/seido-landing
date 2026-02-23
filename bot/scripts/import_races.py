import asyncio
import asyncpg
import os
from datetime import date
from dotenv import load_dotenv
from pathlib import Path
import sys

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

load_dotenv()

# Импортируем парсер RussiaRunning
from bot.parsers.russiarunning import fetch_events_until_date

# Конфигурация БД
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME", "seido")
}

END_DATE = date(2026, 6, 1)  # 1 июня 2026 года


async def save_events_to_db(conn, events: list):
    """Сохраняет события в БД с обновлением существующих"""
    query = """
        INSERT INTO upcoming_races (source, external_id, title, city, event_date, url)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (source, external_id) DO UPDATE
        SET title = $3, city = $4, event_date = $5, url = $6, updated_at = NOW()
    """
    
    saved = 0
    updated = 0
    
    for ev in events:
        result = await conn.execute(
            query,
            ev["source"],
            ev["external_id"],
            ev["title"],
            ev["city"],
            ev["event_date"],
            ev["url"]
        )
        
        if result == "INSERT 0 1":
            saved += 1
        elif result == "UPDATE 1":
            updated += 1
    
    return saved, updated


async def main():
    print(f"🚀 Начало импорта забегов RussiaRunning до {END_DATE}")
    print("-" * 50)
    
    # 1. Получаем события
    print("📡 Запрос данных у RussiaRunning API...")
    try:
        events = await fetch_events_until_date(END_DATE)
        print(f"✅ Получено {len(events)} событий")
    except Exception as e:
        print(f"❌ Ошибка при получении данных: {e}")
        return
    
    if not events:
        print("⚠️ Нет событий для импорта")
        return
    
    # 2. Подключаемся к БД
    print("🔗 Подключение к PostgreSQL...")
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return
    
        # 3. Сохраняем в БД
    print("💾 Сохранение в базу данных...")
    saved = 0
    updated = 0
    
    try:
        saved, updated = await save_events_to_db(conn, events)
        print(f"✅ Добавлено: {saved} | Обновлено: {updated}")
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        await conn.close()
        return
    
    # 4. Статистика
    print("-" * 50)
    print("📊 Статистика импорта:")
    print(f"   Всего событий: {len(events)}")
    print(f"   Новых записей: {saved}")
    print(f"   Обновлённых: {updated}")
    
    if events:
        print("\n📅 Первые 5 забегов:")
        for ev in events[:5]:
            print(f"   • {ev['event_date']} | {ev['title']} ({ev['city']})")
    
    print("\n✅ Импорт завершён!")


if __name__ == "__main__":
    asyncio.run(main())
