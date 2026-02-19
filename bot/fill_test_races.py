"""
Seido - Заполнение базы тестовыми данными о забегах
Для демонстрации функционала
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from db import db


TEST_RACES = [
    {
        'name': 'Пятерка в Парке',
        'date': '2026-03-01',
        'location': 'Москва, Парк Горького',
        'organizer': '5верст',
        'race_type': 'шоссе',
        'distances': '[{"name": "5 км", "elevation": 20}]',
        'website_url': 'https://5verst.ru/pjaterka-v-parke',
    },
    {
        'name': 'Московский полумарафон',
        'date': '2026-04-15',
        'location': 'Москва, Лужники',
        'organizer': 'Московский марафон',
        'race_type': 'шоссе',
        'distances': '[{"name": "21.1 км", "elevation": 50}]',
        'website_url': 'https://moscowmarathon.ru/half',
    },
    {
        'name': 'Забег за мечтой',
        'date': '2026-03-15',
        'location': 'Москва, ВДНХ',
        'organizer': 'RHR',
        'race_type': 'шоссе',
        'distances': '[{"name": "5 км", "elevation": 10}, {"name": "10 км", "elevation": 25}]',
        'website_url': 'https://rhr.run/zabeg-za-mechtoj',
    },
    {
        'name': 'IronStar 1/4',
        'date': '2026-05-20',
        'location': 'Москва',
        'organizer': 'IronStar',
        'race_type': 'триатлон',
        'distances': '[{"name": "1/4 IM", "elevation": 0}]',
        'website_url': 'https://iron-star.com/events/ironstar-1-4-moscow',
    },
    {
        'name': 'Лисья гора',
        'date': '2026-03-08',
        'location': 'Москва, Битцевский парк',
        'organizer': 'S95',
        'race_type': 'трейл',
        'distances': '[{"name": "5 км", "elevation": 150}, {"name": "10 км", "elevation": 300}]',
        'website_url': 'https://s95.run/lisya-gora',
    },
    {
        'name': 'Весенний забег',
        'date': '2026-04-01',
        'location': 'Санкт-Петербург',
        'organizer': '5верст',
        'race_type': 'шоссе',
        'distances': '[{"name": "5 км", "elevation": 15}]',
        'website_url': 'https://5verst.ru/spring-spb',
    },
    {
        'name': 'Кросс по пересеченной местности',
        'date': '2026-03-22',
        'location': 'Москва, Лосиный остров',
        'organizer': 'Не указан',
        'race_type': 'кросс',
        'distances': '[{"name": "10 км", "elevation": 100}]',
        'website_url': '',
    },
    {
        'name': 'Ночной забег',
        'date': '2026-06-15',
        'location': 'Москва, Набережная',
        'organizer': 'RHR',
        'race_type': 'шоссе',
        'distances': '[{"name": "5 км", "elevation": 5}, {"name": "10 км", "elevation": 10}]',
        'website_url': 'https://rhr.run/night-run',
    },
    {
        'name': 'Трейл в Битце',
        'date': '2026-04-20',
        'location': 'Москва, Битца',
        'organizer': 'S95',
        'race_type': 'трейл',
        'distances': '[{"name": "10 км", "elevation": 250}, {"name": "20 км", "elevation": 500}]',
        'website_url': 'https://s95.run/bitza-trail',
    },
    {
        'name': 'Детский забег',
        'date': '2026-05-01',
        'location': 'Москва, Парк Горького',
        'organizer': '5верст',
        'race_type': 'шоссе',
        'distances': '[{"name": "1 км", "elevation": 0}, {"name": "2 км", "elevation": 5}]',
        'website_url': 'https://5verst.ru/kids',
    },
]


async def fill_test_data():
    """Заполнение базы тестовыми забегами"""
    print("=== Заполнение базы тестовыми данными ===\n")
    
    await db.connect()
    
    added = 0
    for race in TEST_RACES:
        try:
            # Проверка на дубликат
            existing = await db.get_race_by_url(race.get('website_url', ''))
            if existing:
                print(f"[SKIP] {race['name']} (уже в базе)")
                continue
            
            await db.add_race(
                name=race['name'],
                date=race['date'],
                location=race['location'],
                organizer=race['organizer'],
                race_type=race['race_type'],
                distances=race['distances'],
                website_url=race.get('website_url', ''),
            )
            print(f"[OK] {race['name']} ({race['date']})")
            added += 1
        except Exception as e:
            print(f"[ERROR] {race['name']}: {e}")
    
    await db.disconnect()
    
    print(f"\n=== Добавлено {added} забегов ===")


if __name__ == "__main__":
    asyncio.run(fill_test_data())
