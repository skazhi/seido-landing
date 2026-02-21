"""
Seido - Парсер Wild Trail (wildtrail.ru)
"""
import logging
from typing import List, Dict
from .base import RaceParser

logger = logging.getLogger(__name__)

# Календарь 2026
WILDTRAIL_EVENTS_2026 = [
    {'name': 'Nikola-Lenivets Winter Wild Trail', 'date': '2026-02-14', 'location': 'Никола-Ленivets', 'url': 'https://wildtrail.ru/nlwwt'},
    {'name': 'Dagestan Wild Trail', 'date': '2026-04-10', 'location': 'Дагестан', 'url': 'https://wildtrail.ru/dwt'},
    {'name': 'Arkhyz Wild Trail', 'date': '2026-06-26', 'location': 'Архыз', 'url': 'https://wildtrail.ru/awt'},
    {'name': 'Rosa Wild Fest', 'date': '2026-09-04', 'location': 'Сочи', 'url': 'https://wildtrail.ru/rwt'},
    {'name': 'Огни Дербента', 'date': '2026-11-15', 'location': 'Дербент', 'url': 'https://lightsofderbent.ru'},
    {'name': 'Sport-Marafon Fest', 'date': '2026-09-01', 'location': 'Сочи', 'url': 'https://sportmarafonfest.ru'},
]


class WildTrailParser(RaceParser):
    """Парсер Wild Trail"""

    SOURCE_NAME = "Wild Trail"
    BASE_URL = "https://wildtrail.ru"

    async def parse_upcoming(self) -> List[Dict]:
        """Парсинг из статического списка"""
        races = []
        try:
            logger.info("Парсинг Wild Trail...")
            for ev in WILDTRAIL_EVENTS_2026:
                raw = {
                    'name': ev['name'],
                    'date': ev['date'],
                    'city': ev['location'],
                    'location': ev['location'],
                    'url': ev['url'],
                    'organizer': 'Wild Trail',
                }
                race = self.normalize_race_data(raw)
                if self.is_future_race(race.get('date')):
                    races.append(race)
            logger.info(f"Wild Trail: найдено {len(races)} забегов")
        except Exception as e:
            logger.error(f"Wild Trail: ошибка - {e}")
        return races
