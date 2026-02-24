"""
Синхронизация только забегов из SQLite в MySQL
(без бегунов и результатов)
"""
import asyncio
import aiosqlite
import pymysql
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

# Путь к локальной SQLite БД
SQLITE_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "seido.db")

# Настройки MySQL (из переменных окружения или по умолчанию)
MYSQL_CONFIG = {
    'host': os.getenv('MYSQL_HOST', '31.31.196.247'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'u3426357_Skazhi'),
    'password': os.getenv('MYSQL_PASSWORD', 'EhmN083fA1108nv1!'),
    'database': os.getenv('MYSQL_DATABASE', 'u3426357_seido'),
    'charset': 'utf8mb4',
    'autocommit': False
}


async def get_sqlite_connection():
    """Подключение к SQLite"""
    return await aiosqlite.connect(SQLITE_DB)


def get_mysql_connection():
    """Подключение к MySQL"""
    return pymysql.connect(**MYSQL_CONFIG)


async def sync_races_only(sqlite_conn, mysql_conn):
    """Синхронизация только забегов"""
    print("🔄 Синхронизация забегов...")
    
    # Получаем все забеги из SQLite
    async with sqlite_conn.execute("SELECT * FROM races") as cursor:
        rows = await cursor.fetchall()
        # Получаем названия колонок
        column_names = [description[0] for description in cursor.description]
        races = [dict(zip(column_names, row)) for row in rows]
    
    mysql_cursor = mysql_conn.cursor()
    
    synced = 0
    updated = 0
    errors = 0
    
    print(f"   Найдено забегов в SQLite: {len(races)}")
    
    for race in races:
        try:
            # Проверяем, существует ли забег (по имени и дате)
            mysql_cursor.execute(
                "SELECT id FROM races WHERE name = %s AND date = %s",
                (race['name'], race['date'])
            )
            exists = mysql_cursor.fetchone()
            
            # Преобразуем distances в JSON строку, если это строка
            distances = race.get('distances', '')
            if isinstance(distances, str) and distances:
                try:
                    import json
                    # Если это уже JSON строка, оставляем как есть
                    if not distances.startswith('[') and not distances.startswith('{'):
                        distances = json.dumps([{"name": distances}])
                except:
                    distances = '[]'
            elif not distances:
                distances = '[]'
            
            if exists:
                # Обновляем
                mysql_cursor.execute("""
                    UPDATE races SET
                        location = %s,
                        organizer = %s,
                        race_type = %s,
                        distances = %s,
                        website_url = %s,
                        protocol_url = %s,
                        is_active = %s,
                        updated_at = NOW()
                    WHERE name = %s AND date = %s
                """, (
                    race.get('location'),
                    race.get('organizer'),
                    race.get('race_type'),
                    distances,
                    race.get('website_url'),
                    race.get('protocol_url'),
                    race.get('is_active', 1),
                    race['name'],
                    race['date']
                ))
                updated += 1
            else:
                # Вставляем нового
                mysql_cursor.execute("""
                    INSERT INTO races (
                        name, date, location, organizer, race_type,
                        distances, website_url, protocol_url, is_active
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    race['name'],
                    race['date'],
                    race.get('location'),
                    race.get('organizer'),
                    race.get('race_type'),
                    distances,
                    race.get('website_url'),
                    race.get('protocol_url'),
                    race.get('is_active', 1)
                ))
                synced += 1
                
            if (synced + updated) % 10 == 0:
                print(f"   Обработано: {synced + updated}/{len(races)}")
                
        except Exception as e:
            print(f"  ❌ Ошибка при синхронизации забега '{race.get('name')}': {e}")
            errors += 1
    
    mysql_conn.commit()
    print(f"  ✅ Забеги: добавлено {synced}, обновлено {updated}, ошибок {errors}")
    return synced + updated


async def main():
    """Основная функция синхронизации"""
    print("=" * 60)
    print("🚀 Синхронизация забегов: SQLite → MySQL")
    print("=" * 60)
    print(f"📅 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Проверяем наличие SQLite БД
    if not os.path.exists(SQLITE_DB):
        print(f"❌ Ошибка: файл {SQLITE_DB} не найден!")
        return
    
    # Подключаемся к базам данных
    try:
        sqlite_conn = await get_sqlite_connection()
        mysql_conn = get_mysql_connection()
        print("✅ Подключение к базам данных установлено")
        print(f"   MySQL: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}")
        print()
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        import traceback
        traceback.print_exc()
        return
    
    try:
        # Синхронизируем только забеги
        races_count = await sync_races_only(sqlite_conn, mysql_conn)
        print()
        
        print("=" * 60)
        print("✅ Синхронизация завершена!")
        print(f"   Забегов синхронизировано: {races_count}")
        print("=" * 60)
        print()
        print("🌐 Проверь сайт: https://seidorun.ru")
        print("   API: https://seidorun.ru/api/api.php?action=races_upcoming")
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await sqlite_conn.close()
        mysql_conn.close()
        print("\n🔌 Соединения закрыты")


if __name__ == "__main__":
    asyncio.run(main())
