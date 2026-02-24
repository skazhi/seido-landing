"""
Быстрый импорт протоколов забегов
Использование: python quick_import.py
"""
import asyncio
import sys
from pathlib import Path

# Добавляем путь к корню проекта
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bot.scripts.parse_protocol import ProtocolImporter
from bot.db import db


async def import_protocol_interactive():
    """Интерактивный импорт протокола"""
    await db.connect()
    importer = ProtocolImporter()
    
    print("\n" + "="*60)
    print("📥 Импорт протокола забега")
    print("="*60 + "\n")
    
    # Путь к файлу
    file_path = input("Путь к файлу протокола (PDF или Excel): ").strip()
    if not Path(file_path).exists():
        print(f"❌ Файл не найден: {file_path}")
        await db.disconnect()
        return
    
    # Информация о забеге
    print("\n📋 Информация о забеге:")
    race_name = input("Название забега: ").strip()
    race_date = input("Дата забега (YYYY-MM-DD): ").strip()
    race_location = input("Место проведения (город, локация): ").strip()
    race_organizer = input("Организатор: ").strip()
    race_type = input("Тип забега (шоссе/трейл/стадион) [шоссе]: ").strip() or "шоссе"
    distance = input("Дистанция (например: 5 км, 10 км, 21.1 км, 42.2 км): ").strip()
    website_url = input("Ссылка на сайт забега (необязательно): ").strip()
    protocol_url = input("Ссылка на протокол (необязательно): ").strip()
    
    # Параметры парсинга
    print("\n⚙️ Параметры парсинга:")
    header_row = input("Номер строки с заголовками (обычно 0 или 1) [0]: ").strip()
    header_row = int(header_row) if header_row else 0
    
    sheet_name = None
    if file_path.lower().endswith(('.xlsx', '.xls')):
        sheet_name = input("Название листа в Excel (Enter для автоматического выбора): ").strip()
        if not sheet_name:
            sheet_name = None
    
    # Подтверждение
    print("\n" + "="*60)
    print("📋 Подтверждение:")
    print(f"   Файл: {file_path}")
    print(f"   Забег: {race_name}")
    print(f"   Дата: {race_date}")
    print(f"   Дистанция: {distance}")
    print("="*60)
    
    confirm = input("\nНачать импорт? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Импорт отменён")
        await db.disconnect()
        return
    
    # Импорт
    print("\n🔄 Начинаю импорт...\n")
    
    try:
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
        
        print("\n✅ Импорт завершён успешно!")
        
    except Exception as e:
        print(f"\n❌ Ошибка при импорте: {e}")
        import traceback
        traceback.print_exc()
    
    await db.disconnect()


async def main():
    """Главная функция"""
    try:
        await import_protocol_interactive()
    except KeyboardInterrupt:
        print("\n\n❌ Импорт прерван пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
