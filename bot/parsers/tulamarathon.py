"""
Seido - Парсер TulaMarathon (tulamarathon.org)
"""
import logging
from typing import List, Dict
from .base import RaceParser

logger = logging.getLogger(__name__)

# Расписание 2026 с сайта
TULAMARATHON_EVENTS_2026 = [
    {'name': 'Забег Первая дорожка', 'date': '2026-01-25', 'location': 'Тула', 'url': 'https://tulamarathon.org/'},
    {'name': 'Эстафета Весна', 'date': '2026-04-19', 'location': 'Тула', 'url': 'https://tulamarathon.org/'},
    {'name': 'ЗаБег.РФ Тула', 'date': '2026-05-24', 'location': 'Тула', 'url': 'https://tulamarathon.org/'},
    {'name': 'Забег Ночная Тула', 'date': '2026-07-18', 'location': 'Тула', 'url': 'https://tulamarathon.org/'},
    {'name': 'Полумарафон Тула', 'date': '2026-08-23', 'location': 'Тула', 'url': 'https://tulamarathon.org/'},
    {'name': 'Полумарафон Оружейная столица', 'date': '2026-09-13', 'location': 'Тула', 'url': 'https://armory.tulamarathon.org/'},
    {'name': 'Эстафета Осень', 'date': '2026-10-11', 'location': 'Тула', 'url': 'https://tulamarathon.org/'},
    {'name': 'Забег Дедов Морозов', 'date': '2026-12-20', 'location': 'Тула', 'url': 'https://tulamarathon.org/'},
]


class TulaMarathonParser(RaceParser):
    """Парсер TulaMarathon"""

    SOURCE_NAME = "TulaMarathon"
    BASE_URL = "https://tulamarathon.org"

    async def parse_upcoming(self) -> List[Dict]:
        """Парсинг из статического списка"""
        races = []
        try:
            logger.info("Парсинг TulaMarathon...")
            for ev in TULAMARATHON_EVENTS_2026:
                raw = {
                    'name': ev['name'],
                    'date': ev['date'],
                    'city': ev['location'],
                    'location': ev['location'],
                    'url': ev['url'],
                    'organizer': 'TulaMarathon',
                }
                race = self.normalize_race_data(raw)
                if self.is_future_race(race.get('date')):
                    races.append(race)
            logger.info(f"TulaMarathon: найдено {len(races)} забегов")
        except Exception as e:
            logger.error(f"TulaMarathon: ошибка - {e}")
        return races
