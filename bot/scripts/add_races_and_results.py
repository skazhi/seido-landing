"""
Seido - Скрипт для добавления анонсов забегов и результатов
Универсальный инструмент для наполнения базы данных
"""
import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Добавляем путь к корню проекта и папке bot
bot_path = Path(__file__).parent.parent
sys.path.insert(0, str(bot_path.parent))
sys.path.insert(0, str(bot_path))

from db import db
from parsers.scheduler import scheduler
from scripts.parse_protocol import ProtocolImporter


async def add_race_announcements():
    """Добавление анонсов забегов через парсеры"""
    print("=" * 60)
    print("📅 ДОБАВЛЕНИЕ АНОНСОВ ЗАБЕГОВ")
    print("=" * 60)
    
    await db.connect()
    
    try:
        # Запуск парсинга всех источников
        results = await scheduler.parse_all()
        
        print("\n" + "=" * 60)
        print("📊 РЕЗУЛЬТАТЫ ПАРСИНГА:")
        print("=" * 60)
        
        total = 0
        for source, count in results.items():
            print(f"  {source}: {count} забегов")
            total += count
        
        print(f"\n✅ Всего добавлено: {total} забегов")
        
    except Exception as e:
        print(f"❌ Ошибка при парсинге: {e}")
    finally:
        await db.disconnect()


async def add_race_manually(
    name: str,
    date: str,
    location: str = '',
    organizer: str = '',
    race_type: str = 'шоссе',
    distances: List[str] = None,
    website_url: str = '',
    protocol_url: str = ''
):
    """Ручное добавление забега"""
    await db.connect()
    
    try:
        # Формируем JSON для дистанций
        if distances:
            import json
            distances_json = json.dumps([{"name": d, "elevation": 0} for d in distances])
        else:
            distances_json = '[]'
        
        # Проверка на дубликат
        existing = await db.get_race_by_url(website_url) if website_url else None
        if existing:
            print(f"⚠️ Забег уже существует: {existing['name']} ({existing['date']})")
            return existing['id']
        
        race_id = await db.add_race(
            name=name,
            date=date,
            location=location,
            organizer=organizer,
            race_type=race_type,
            distances=distances_json,
            website_url=website_url,
            protocol_url=protocol_url
        )
        
        print(f"✅ Забег добавлен: {name} (ID: {race_id})")
        return race_id
        
    except Exception as e:
        print(f"❌ Ошибка при добавлении забега: {e}")
        return None
    finally:
        await db.disconnect()


async def add_results_from_protocol(
    file_path: str,
    race_name: str,
    race_date: str,
    race_location: str = '',
    race_organizer: str = '',
    race_type: str = 'шоссе',
    distance: str = '',
    website_url: str = '',
    protocol_url: str = '',
    header_row: int = 0,
    sheet_name: Optional[str] = None
):
    """Добавление результатов из протокола"""
    print("=" * 60)
    print("📊 ДОБАВЛЕНИЕ РЕЗУЛЬТАТОВ ИЗ ПРОТОКОЛА")
    print("=" * 60)
    
    await db.connect()
    
    try:
        importer = ProtocolImporter()
        
        await importer.import_protocol(
            file_path=file_path,
            race_name=race_name,
            race_date=race_date,
            race_location=race_location,
            race_organizer=race_organizer,
            race_type=race_type,
            distance=distance,
            website_url=website_url,
            protocol_url=protocol_url,
            header_row=header_row,
            sheet_name=sheet_name
        )
        
        importer.print_stats()
        
    except Exception as e:
        print(f"❌ Ошибка при импорте протокола: {e}")
    finally:
        await db.disconnect()


async def show_statistics():
    """Показать статистику базы данных"""
    await db.connect()
    
    try:
        total_races = await db.get_total_races()
        total_runners = await db.get_total_runners()
        total_results = await db.get_total_results()
        
        print("=" * 60)
        print("📊 СТАТИСТИКА БАЗЫ ДАННЫХ")
        print("=" * 60)
        print(f"  Забегов: {total_races}")
        print(f"  Бегунов: {total_runners}")
        print(f"  Результатов: {total_results}")
        print("=" * 60)
        
    finally:
        await db.disconnect()


async def interactive_menu():
    """Интерактивное меню для добавления данных"""
    print("\n" + "=" * 60)
    print("🚀 SEIDO - ДОБАВЛЕНИЕ ДАННЫХ В БАЗУ")
    print("=" * 60)
    print("\nВыберите действие:")
    print("1. Добавить анонсы забегов (парсинг)")
    print("2. Добавить забег вручную")
    print("3. Добавить результаты из протокола")
    print("4. Показать статистику")
    print("5. Выход")
    
    choice = input("\nВаш выбор (1-5): ").strip()
    
    if choice == "1":
        await add_race_announcements()
    elif choice == "2":
        print("\n📝 Добавление забега вручную:")
        name = input("Название забега: ").strip()
        date = input("Дата (YYYY-MM-DD): ").strip()
        location = input("Место проведения (опционально): ").strip()
        organizer = input("Организатор (опционально): ").strip()
        race_type = input("Тип забега (шоссе/трейл/кросс, по умолчанию 'шоссе'): ").strip() or "шоссе"
        distances_input = input("Дистанции через запятую (например: 5 км, 10 км): ").strip()
        distances = [d.strip() for d in distances_input.split(",")] if distances_input else []
        website_url = input("Ссылка на сайт (опционально): ").strip()
        
        await add_race_manually(
            name=name,
            date=date,
            location=location,
            organizer=organizer,
            race_type=race_type,
            distances=distances,
            website_url=website_url
        )
    elif choice == "3":
        print("\n📄 Добавление результатов из протокола:")
        file_path = input("Путь к файлу протокола (PDF/Excel): ").strip()
        race_name = input("Название забега: ").strip()
        race_date = input("Дата забега (YYYY-MM-DD): ").strip()
        race_location = input("Место проведения (опционально): ").strip()
        race_organizer = input("Организатор (опционально): ").strip()
        distance = input("Дистанция (например: 5 км): ").strip()
        website_url = input("Ссылка на сайт забега (опционально): ").strip()
        protocol_url = input("Ссылка на протокол (опционально): ").strip()
        header_row = int(input("Номер строки с заголовками (по умолчанию 0): ").strip() or "0")
        
        await add_results_from_protocol(
            file_path=file_path,
            race_name=race_name,
            race_date=race_date,
            race_location=race_location,
            race_organizer=race_organizer,
            distance=distance,
            website_url=website_url,
            protocol_url=protocol_url,
            header_row=header_row
        )
    elif choice == "4":
        await show_statistics()
    elif choice == "5":
        print("👋 До свидания!")
        return False
    else:
        print("⚠️ Неверный выбор")
    
    return True


async def main():
    """Главная функция"""
    if len(sys.argv) > 1:
        # Режим командной строки
        command = sys.argv[1]
        
        if command == "announcements":
            await add_race_announcements()
        elif command == "stats":
            await show_statistics()
        elif command == "race":
            # Добавление забега через аргументы
            if len(sys.argv) < 4:
                print("Использование: python add_races_and_results.py race <название> <дата> [организатор]")
                return
            
            name = sys.argv[2]
            date = sys.argv[3]
            organizer = sys.argv[4] if len(sys.argv) > 4 else ""
            
            await add_race_manually(
                name=name,
                date=date,
                organizer=organizer
            )
        else:
            print("Неизвестная команда. Используйте: announcements, stats, race")
    else:
        # Интерактивный режим
        while True:
            if not await interactive_menu():
                break
            print("\n" + "-" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
