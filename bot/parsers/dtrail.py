"""
Seido - Парсер Dream Trail (dtrail.ru)
"""
import logging
from typing import List, Dict
from .base import RaceParser

logger = logging.getLogger(__name__)

DREAM_TRAIL_EVENTS = [
    {'name': 'Dream Trail Lyskovo', 'date': '2026-06-27', 'location': 'Лысково', 'url': 'https://dtrail.ru/dtl_2026/'},
    {'name': 'Dream Trail Khimki Forest', 'date': '2026-05-01', 'location': 'Химки', 'url': 'https://dtrail.ru/'},
]


class DreamTrailParser(RaceParser):
    """Парсер Dream Trail"""

    SOURCE_NAME = "Dream Trail"
    BASE_URL = "https://dtrail.ru"

    async def parse_upcoming(self) -> List[Dict]:
        """Парсинг из статического списка"""
        races = []
        try:
            logger.info("Парсинг Dream Trail...")
            for ev in DREAM_TRAIL_EVENTS:
                raw = {
                    'name': ev['name'],
                    'date': ev['date'],
                    'city': ev['location'],
                    'location': ev['location'],
                    'url': ev['url'],
                    'organizer': 'Dream Trail',
                }
                race = self.normalize_race_data(raw)
                if self.is_future_race(race.get('date')):
                    races.append(race)
            logger.info(f"Dream Trail: найдено {len(races)} забегов")
        except Exception as e:
            logger.error(f"Dream Trail: ошибка - {e}")
        return races
