"""
Seido - Парсер IronStar (iron-star.com)
Календарь: iron-star.com/event/
"""
import aiohttp
import logging
import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from .base import RaceParser

logger = logging.getLogger(__name__)

# Города из slug
SLUG_CITIES = {
    'moskva': 'Москва',
    'moscow': 'Москва',
    'luzhniki': 'Москва',
    'voronezh': 'Воронеж',
    'minsk': 'Минск',
    'sochi': 'Сочи',
    'egypt': 'Египет',
    'sharm': 'Шарм-эль-Шейх',
    'zavidovo': 'Завидово',
    'tyumen': 'Тюмень',
}


class IronStarParser(RaceParser):
    """Парсер IronStar"""

    SOURCE_NAME = "IronStar"
    BASE_URL = "https://iron-star.com"
    EVENTS_URL = "https://iron-star.com/event/"

    async def parse_upcoming(self) -> List[Dict]:
        """Парсинг предстоящих забегов"""
        session = await self.get_session()
        races = []

        try:
            logger.info("Парсинг IronStar...")

            async with session.get(self.EVENTS_URL) as response:
                if response.status != 200:
                    logger.error(f"IronStar error: {response.status}")
                    return races

                html = await response.text(encoding='utf-8')
                soup = BeautifulSoup(html, 'html.parser')

                # Ищем карточки событий (ссылки на /event/slug/)
                seen_urls = set()
                for a in soup.find_all('a', href=True):
                    href = a.get('href', '')
                    m = re.search(r'/event/([a-z0-9-]+)/', href, re.I)
                    if not m:
                        continue
                    slug = m.group(1)
                    if 'event' in slug or len(slug) < 5:
                        continue
                    url = f"{self.BASE_URL}/event/{slug}/" if not href.startswith('http') else href
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    # Название из slug (текст ссылки часто содержит дату и мусор)
                    name = self._slug_to_name(slug)

                    # Дата — ищем рядом DD.MM.YYYY
                    date_str = None
                    parent = a.find_parent()
                    for _ in range(5):
                        if not parent:
                            break
                        text = parent.get_text()
                        date_m = re.search(r'\d{2}\.\d{2}\.\d{4}', text)
                        if date_m:
                            date_str = date_m.group()
                            break
                        parent = parent.find_parent() if hasattr(parent, 'find_parent') else None

                    location = self._slug_to_city(slug)

                    raw = {
                        'name': name,
                        'date': date_str,
                        'city': location,
                        'location': location,
                        'url': url,
                        'distances': [],
                    }
                    race = self.normalize_race_data(raw)
                    if race.get('date') and self.is_future_race(race.get('date')):
                        races.append(race)

                logger.info(f"IronStar: найдено {len(races)} забегов")

        except Exception as e:
            logger.error(f"IronStar: ошибка - {e}")

        return races

    def _slug_to_name(self, slug: str) -> str:
        """Преобразование slug в читаемое название"""
        # ironlady-voronezh-2026 -> IronLady Voronezh 2026
        # liga-triatlona-ironstar-1-8-moskva-luzhniki-2026 -> Liga Triatlona IronStar 1/8 Moskva
        parts = slug.replace('-', ' ').split()
        filtered = []
        for p in parts:
            if p in ('2026', '2025') or (len(p) <= 2 and p.isdigit()):
                continue
            if p == '1' and filtered and filtered[-1].lower() == 'ironstar':
                continue  # ironstar 1/8
            filtered.append(p.capitalize())
        name = ' '.join(filtered)
        # Сокращения
        name = name.replace('Luzhniki', 'Лужники').replace('Moskva', 'Москва')
        name = name.replace('Voronezh', 'Воронеж').replace('Minsk', 'Минск')
        return name or slug

    def _slug_to_city(self, slug: str) -> str:
        """Извлечение города из slug"""
        slug_lower = slug.lower()
        for key, city in SLUG_CITIES.items():
            if key in slug_lower:
                return city
        return ''

    async def parse_results(self, race_url: str) -> List[Dict]:
        """Парсинг результатов не реализован"""
        return []
