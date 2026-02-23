"""
Seido - Парсер TIMERMAN (kazan.run, timerman.org)
Казанский марафон и другие события TIMERMAN
"""
import aiohttp
import logging
import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from .base import RaceParser

logger = logging.getLogger(__name__)


class TimerManParser(RaceParser):
    """Парсер TIMERMAN"""

    SOURCE_NAME = "TIMERMAN"
    BASE_URL = "https://kazan.run"
    CALENDAR_URL = "https://timerman.org"

    async def parse_upcoming(self) -> List[Dict]:
        """Парсинг предстоящих забегов"""
        races = []

        # Казанский марафон 2026 — основной (обычно май)
        races.append(self.normalize_race_data({
            'name': 'Казанский марафон',
            'date': '2026-05-03',
            'city': 'Казань',
            'location': 'Казань',
            'url': 'https://kazan.run/',
            'organizer': 'TIMERMAN',
            'distances': [{'name': '42.2 км', 'elevation': 0}, {'name': '21.1 км', 'elevation': 0}],
        }))

        # Пробуем распарсить timerman.org
        try:
            session = await self.get_session()
            async with session.get(self.CALENDAR_URL) as response:
                if response.status == 200:
                    html = await response.text(encoding='utf-8')
                    soup = BeautifulSoup(html, 'html.parser')
                    for a in soup.find_all('a', href=True):
                        href = a.get('href', '')
                        if 'kazan' in href.lower() or 'event' in href.lower():
                            text = a.get_text(strip=True)
                            if text and 'марафон' in text.lower() and 'казан' not in text.lower():
                                # Доп. события
                                date_m = re.search(r'\d{1,2}\.\d{1,2}\.\d{4}|\d{4}-\d{2}-\d{2}', str(a))
                                date_str = date_m.group() if date_m else None
                                url = href if href.startswith('http') else f"https://timerman.org{href}"
                                if url not in [r.get('website_url') for r in races]:
                                    raw = {
                                        'name': text[:100],
                                        'date': date_str,
                                        'city': 'Казань',
                                        'location': 'Казань',
                                        'url': url,
                                        'organizer': 'TIMERMAN',
                                        'distances': [],
                                    }
                                    race = self.normalize_race_data(raw)
                                    if race.get('date') and self.is_future_race(race.get('date')):
                                        races.append(race)
        except Exception as e:
            logger.debug(f"TIMERMAN calendar parse: {e}")

        # Убираем дубликаты по URL
        seen = set()
        unique = []
        for r in races:
            url = r.get('website_url', '')
            if url and url not in seen:
                seen.add(url)
                unique.append(r)
            elif not url:
                unique.append(r)

        logger.info(f"TIMERMAN: найдено {len(unique)} забегов")
        return unique
