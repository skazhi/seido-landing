"""
Seido - Парсер Высшая лига (topliga.ru / events.topliga.ru)
Vue SPA — используем статический список по календарю 2026
"""
import logging
from typing import List, Dict
from .base import RaceParser

logger = logging.getLogger(__name__)

TOPLIGA_EVENTS_2026 = [
    {'name': 'Новогодний забег', 'date': '2026-01-01', 'location': 'Краснодар', 'url': 'https://events.topliga.ru/'},
    {'name': 'Hard Run', 'date': '2026-02-22', 'location': 'Краснодар', 'url': 'https://events.topliga.ru/'},
    {'name': 'Beauty Run', 'date': '2026-03-08', 'location': 'Краснодар', 'url': 'https://events.topliga.ru/'},
    {'name': 'Сириус Автодром', 'date': '2026-04-05', 'location': 'Сириус', 'url': 'https://events.topliga.ru/'},
    {'name': 'Когалымский полумарафон', 'date': '2026-09-06', 'location': 'Когалым', 'url': 'https://events.topliga.ru/'},
    {'name': 'Донской марафон', 'date': '2026-09-27', 'location': 'Ростов-на-Дону', 'url': 'https://events.topliga.ru/'},
    {'name': 'Сочи Марафон', 'date': '2026-11-01', 'location': 'Сочи', 'url': 'https://events.topliga.ru/'},
]


class TopligaParser(RaceParser):
    """Парсер Высшая лига"""

    SOURCE_NAME = "Высшая лига"
    BASE_URL = "https://events.topliga.ru"

    async def parse_upcoming(self) -> List[Dict]:
        """Парсинг из статического списка (SPA — парсинг сложен)"""
        races = []
        try:
            logger.info("Парсинг Высшая лига...")
            for ev in TOPLIGA_EVENTS_2026:
                raw = {
                    'name': ev['name'],
                    'date': ev['date'],
                    'city': ev['location'],
                    'location': ev['location'],
                    'url': ev['url'],
                    'organizer': 'Высшая лига',
                }
                race = self.normalize_race_data(raw)
                if self.is_future_race(race.get('date')):
                    races.append(race)
            logger.info(f"Высшая лига: найдено {len(races)} забегов")
        except Exception as e:
            logger.error(f"Высшая лига: ошибка - {e}")
        return races
