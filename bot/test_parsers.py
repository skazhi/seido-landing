"""
Тест парсеров забегов
"""
import asyncio
import sys
import os

# Исправление кодировки для Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Добавляем путь к bot
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

from parsers.russiarunning import RussiaRunningParser
from parsers.myrace import MyRaceParser
from parsers.ironstar import IronStarParser


async def test_parsers():
    """Тестирование всех парсеров"""
    
    print("\n=== Тестирование парсеров забегов ===\n")
    
    parsers = [
        ("RussiaRunning", RussiaRunningParser()),
        ("MyRace", MyRaceParser()),
        ("IronStar", IronStarParser()),
    ]
    
    for name, parser in parsers:
        print(f"Парсинг {name}...")
        try:
            races = await parser.parse_upcoming()
            print(f"[OK] {name}: найдено {len(races)} забегов")
            
            if races:
                print(f"   Пример: {races[0]['name']} ({races[0]['date']})")
            
            await parser.close()
        except Exception as e:
            print(f"[ERROR] {name}: {e}")
        print()
    
    print("=== Тестирование завершено ===")


if __name__ == "__main__":
    asyncio.run(test_parsers())
