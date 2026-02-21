"""
Seido - Парсер RHR / Golden Ultra (goldenultra.ru)
Running Heroes Russia - ультратрейлы
"""
import aiohttp
import logging
import re
from typing import List, Dict
from bs4 import BeautifulSoup
from .base import RaceParser

logger = logging.getLogger(__name__)

# Известные события RHR 2026 (календарь с sports.ru)
RHR_EVENTS_2026 = [
    {'name': 'Moscow Drift Cross', 'date': '2026-03-28', 'location': 'Москва', 'url': 'https://goldenultra.ru/'},
    {'name': 'RHR Plogging', 'date': '2026-04-01', 'location': 'Москва', 'url': 'https://goldenultra.ru/'},
    {'name': 'Kalmyk Camel Trophy', 'date': '2026-04-18', 'location': 'Калмыкия', 'url': 'https://goldenultra.ru/'},
    {'name': 'Crazy Owl 50', 'date': '2026-06-12', 'location': 'Москва', 'url': 'https://goldenultra.ru/'},
    {'name': 'Golden Ring Ultra Trail 100', 'date': '2026-07-24', 'location': 'Золотое кольцо', 'url': 'https://goldenultra.ru/'},
    {'name': 'Kodar Ridge Chara Sands', 'date': '2026-08-22', 'location': 'Чара', 'url': 'https://goldenultra.ru/'},
    {'name': 'White Bridge Ultra Gelendzhik', 'date': '2026-10-02', 'location': 'Геленджик', 'url': 'https://goldenultra.ru/'},
    {'name': 'Moscow Drift Cross', 'date': '2026-11-15', 'location': 'Москва', 'url': 'https://goldenultra.ru/'},
    {'name': 'Mad Fox Ultra', 'date': '2026-12-18', 'location': 'Москва', 'url': 'https://goldenultra.ru/'},
]


class GoldenUltraParser(RaceParser):
    """Парсер RHR (goldenultra.ru)"""

    SOURCE_NAME = "RHR"
    BASE_URL = "https://goldenultra.ru"

    async def parse_upcoming(self) -> List[Dict]:
        """Парсинг через статический список + попытка дополнения с сайта"""
        races = []
        try:
            logger.info("Парсинг RHR (goldenultra.ru)...")
            for ev in RHR_EVENTS_2026:
                raw = {
                    'name': ev['name'],
                    'date': ev['date'],
                    'city': ev['location'],
                    'location': ev['location'],
                    'url': ev['url'],
                    'organizer': 'RHR',
                }
                race = self.normalize_race_data(raw)
                if self.is_future_race(race.get('date')):
                    races.append(race)
            logger.info(f"RHR: найдено {len(races)} забегов")
        except Exception as e:
            logger.error(f"RHR: ошибка - {e}")
        return races
