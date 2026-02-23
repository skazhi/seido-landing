"""
Seido - Парсер Open Band Trails (openband.run)
"""
import logging
from typing import List, Dict
from .base import RaceParser

logger = logging.getLogger(__name__)

OPENBAND_EVENTS_2026 = [
    {'name': 'Open Band Trails — Буран', 'date': '2026-01-18', 'location': 'Москва, Кузьминки', 'url': 'https://openband.run/'},
    {'name': 'Open Band Trails — Мороз', 'date': '2026-02-22', 'location': 'Октябрьский, МО', 'url': 'https://openband.run/'},
    {'name': 'Open Band Trails — Лёд', 'date': '2026-03-15', 'location': 'Пушкино, МО', 'url': 'https://openband.run/'},
    {'name': 'Open Band Trails — Мгла', 'date': '2026-04-25', 'location': 'Москва, Битца', 'url': 'https://openband.run/'},
    {'name': 'Open Band Trails — Молния', 'date': '2026-07-19', 'location': 'Беломестный, МО', 'url': 'https://openband.run/'},
    {'name': 'Open Band Trails — Ливень', 'date': '2026-09-06', 'location': 'Ильинское, МО', 'url': 'https://openband.run/'},
    {'name': 'Open Band Trails — Туман', 'date': '2026-10-10', 'location': 'Фрязино, МО', 'url': 'https://openband.run/'},
    {'name': 'Open Band Trails — Буря', 'date': '2026-11-15', 'location': 'Красногорск, МО', 'url': 'https://openband.run/'},
]


class OpenBandParser(RaceParser):
    """Парсер Open Band Trails"""

    SOURCE_NAME = "Open Band"
    BASE_URL = "https://openband.run"

    async def parse_upcoming(self) -> List[Dict]:
        """Парсинг из статического списка"""
        races = []
        try:
            logger.info("Парсинг Open Band...")
            for ev in OPENBAND_EVENTS_2026:
                raw = {
                    'name': ev['name'],
                    'date': ev['date'],
                    'city': ev['location'],
                    'location': ev['location'],
                    'url': ev['url'],
                    'organizer': 'Open Band',
                }
                race = self.normalize_race_data(raw)
                if self.is_future_race(race.get('date')):
                    races.append(race)
            logger.info(f"Open Band: найдено {len(races)} забегов")
        except Exception as e:
            logger.error(f"Open Band: ошибка - {e}")
        return races
