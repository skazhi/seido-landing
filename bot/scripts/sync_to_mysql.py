"""
Синхронизация данных из SQLite в MySQL для сайта seidorun.ru
"""
import asyncio
import aiosqlite
import pymysql
import os
import sys
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

# Добавляем родительскую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Путь к локальной SQLite БД
SQLITE_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "seido.db")

# Настройки MySQL (из переменных окружения или по умолчанию)
MYSQL_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'u3426357_Skazhi'),
    'password': os.getenv('MYSQL_PASSWORD', 'fS9eO6gL2rbB5uM5'),
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


async def sync_runners(sqlite_conn, mysql_conn):
    """Синхронизация бегунов"""
    print("🔄 Синхронизация бегунов...")
    
    # Получаем всех бегунов из SQLite
    async with sqlite_conn.execute("SELECT * FROM runners") as cursor:
        rows = await cursor.fetchall()
        runners = [dict(row) for row in rows]
    
    mysql_cursor = mysql_conn.cursor()
    
    synced = 0
    updated = 0
    errors = 0
    
    for runner in runners:
        try:
            # Проверяем, существует ли бегун
            mysql_cursor.execute(
                "SELECT id FROM runners WHERE telegram_id = %s",
                (runner['telegram_id'],)
            )
            exists = mysql_cursor.fetchone()
            
            if exists:
                # Обновляем
                mysql_cursor.execute("""
                    UPDATE runners SET
                        first_name = %s,
                        last_name = %s,
                        middle_name = %s,
                        birth_date = %s,
                        gender = %s,
                        city = %s,
                        country = %s,
                        club_name = %s,
                        updated_at = NOW()
                    WHERE telegram_id = %s
                """, (
                    runner['first_name'],
                    runner['last_name'],
                    runner.get('middle_name'),
                    runner.get('birth_date'),
                    runner.get('gender'),
                    runner.get('city'),
                    runner.get('country', 'Россия'),
                    runner.get('club_name'),
                    runner['telegram_id']
                ))
                updated += 1
            else:
                # Вставляем нового
                mysql_cursor.execute("""
                    INSERT INTO runners (
                        telegram_id, first_name, last_name, middle_name,
                        birth_date, gender, city, country, club_name
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    runner['telegram_id'],
                    runner['first_name'],
                    runner['last_name'],
                    runner.get('middle_name'),
                    runner.get('birth_date'),
                    runner.get('gender'),
                    runner.get('city'),
                    runner.get('country', 'Россия'),
                    runner.get('club_name')
                ))
                synced += 1
        except Exception as e:
            print(f"  ❌ Ошибка при синхронизации бегуна {runner.get('telegram_id')}: {e}")
            errors += 1
    
    mysql_conn.commit()
    print(f"  ✅ Бегуны: добавлено {synced}, обновлено {updated}, ошибок {errors}")
    return synced + updated


async def sync_races(sqlite_conn, mysql_conn):
    """Синхронизация забегов"""
    print("🔄 Синхронизация забегов...")
    
    # Получаем все забеги из SQLite
    async with sqlite_conn.execute("SELECT * FROM races") as cursor:
        rows = await cursor.fetchall()
        races = [dict(row) for row in rows]
    
    mysql_cursor = mysql_conn.cursor()
    
    synced = 0
    updated = 0
    errors = 0
    
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
                    distances = json.dumps(distances) if not distances.startswith('[') else distances
                except:
                    distances = ''
            
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
        except Exception as e:
            print(f"  ❌ Ошибка при синхронизации забега {race.get('name')}: {e}")
            errors += 1
    
    mysql_conn.commit()
    print(f"  ✅ Забеги: добавлено {synced}, обновлено {updated}, ошибок {errors}")
    return synced + updated


async def sync_results(sqlite_conn, mysql_conn):
    """Синхронизация результатов"""
    print("🔄 Синхронизация результатов...")
    
    # Получаем все результаты из SQLite с JOIN к runners и races
    async with sqlite_conn.execute("""
        SELECT r.*, ru.telegram_id, ra.name as race_name, ra.date as race_date
        FROM results r
        JOIN runners ru ON r.runner_id = ru.id
        JOIN races ra ON r.race_id = ra.id
    """) as cursor:
        rows = await cursor.fetchall()
        results = [dict(row) for row in rows]
    
    mysql_cursor = mysql_conn.cursor()
    
    synced = 0
    updated = 0
    errors = 0
    
    for result in results:
        try:
            # Находим runner_id в MySQL по telegram_id
            mysql_cursor.execute(
                "SELECT id FROM runners WHERE telegram_id = %s",
                (result['telegram_id'],)
            )
            runner_row = mysql_cursor.fetchone()
            if not runner_row:
                continue  # Пропускаем, если бегун не найден
            
            mysql_runner_id = runner_row[0]
            
            # Находим race_id в MySQL по имени и дате
            mysql_cursor.execute(
                "SELECT id FROM races WHERE name = %s AND date = %s",
                (result['race_name'], result['race_date'])
            )
            race_row = mysql_cursor.fetchone()
            if not race_row:
                continue  # Пропускаем, если забег не найден
            
            mysql_race_id = race_row[0]
            
            # Проверяем, существует ли результат
            mysql_cursor.execute("""
                SELECT id FROM results 
                WHERE runner_id = %s AND race_id = %s AND distance = %s
            """, (mysql_runner_id, mysql_race_id, result['distance']))
            exists = mysql_cursor.fetchone()
            
            if exists:
                # Обновляем
                mysql_cursor.execute("""
                    UPDATE results SET
                        finish_time = %s,
                        finish_time_seconds = %s,
                        pace = %s,
                        pace_seconds_per_km = %s,
                        overall_place = %s,
                        gender_place = %s,
                        age_group = %s,
                        age_group_place = %s,
                        club_place = %s,
                        total_runners = %s,
                        points = %s,
                        is_official = %s,
                        updated_at = NOW()
                    WHERE runner_id = %s AND race_id = %s AND distance = %s
                """, (
                    result.get('finish_time'),
                    result.get('finish_time_seconds'),
                    result.get('pace'),
                    result.get('pace_seconds_per_km'),
                    result.get('overall_place'),
                    result.get('gender_place'),
                    result.get('age_group'),
                    result.get('age_group_place'),
                    result.get('club_place'),
                    result.get('total_runners'),
                    result.get('points'),
                    result.get('is_official', 1),
                    mysql_runner_id,
                    mysql_race_id,
                    result['distance']
                ))
                updated += 1
            else:
                # Вставляем новый
                mysql_cursor.execute("""
                    INSERT INTO results (
                        runner_id, race_id, distance,
                        finish_time, finish_time_seconds, pace, pace_seconds_per_km,
                        overall_place, gender_place, age_group, age_group_place,
                        club_place, total_runners, points, is_official
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    mysql_runner_id,
                    mysql_race_id,
                    result['distance'],
                    result.get('finish_time'),
                    result.get('finish_time_seconds'),
                    result.get('pace'),
                    result.get('pace_seconds_per_km'),
                    result.get('overall_place'),
                    result.get('gender_place'),
                    result.get('age_group'),
                    result.get('age_group_place'),
                    result.get('club_place'),
                    result.get('total_runners'),
                    result.get('points'),
                    result.get('is_official', 1)
                ))
                synced += 1
        except Exception as e:
            print(f"  ❌ Ошибка при синхронизации результата: {e}")
            errors += 1
    
    mysql_conn.commit()
    print(f"  ✅ Результаты: добавлено {synced}, обновлено {updated}, ошибок {errors}")
    return synced + updated


async def main():
    """Основная функция синхронизации"""
    print("=" * 60)
    print("🚀 Синхронизация данных Seido: SQLite → MySQL")
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
        print()
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return
    
    try:
        # Синхронизируем данные
        runners_count = await sync_runners(sqlite_conn, mysql_conn)
        print()
        races_count = await sync_races(sqlite_conn, mysql_conn)
        print()
        results_count = await sync_results(sqlite_conn, mysql_conn)
        print()
        
        print("=" * 60)
        print("✅ Синхронизация завершена!")
        print(f"   Бегуны: {runners_count}")
        print(f"   Забеги: {races_count}")
        print(f"   Результаты: {results_count}")
        print("=" * 60)
        
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
