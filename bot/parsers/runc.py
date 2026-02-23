"""
Seido - Парсер Беговое сообщество / RunC (runc.run, бывш. Юнистар)
События: runc.run и поддомены (moscowmarathon, moscowhalf, speedrace, aprilrun5km и тд)
"""
import logging
from typing import List, Dict
from .base import RaceParser

logger = logging.getLogger(__name__)

# Известные события Беговое сообщество (RunC) на 2026
# protocol_slug: слаг для results.runc.run/event/{slug}/overview/
RUNC_EVENTS_2026 = [
    {'name': 'Соревнования «Скорость»', 'date': '2026-02-21', 'location': 'Москва', 'url': 'https://speedrace.runc.run/', 'protocol_slug': 'speedrace'},
    {'name': 'Забег «Апрель»', 'date': '2026-04-05', 'location': 'Москва', 'url': 'https://aprilrun5km.runc.run/', 'protocol_slug': 'aprilrun5km'},
    {'name': 'Детский забег', 'date': '2026-04-25', 'location': 'Москва', 'url': 'https://kids.runc.run/', 'protocol_slug': 'kids'},
    {'name': 'Московский полумарафон', 'date': '2026-04-26', 'location': 'Москва', 'url': 'https://moscowhalf.runc.run/', 'protocol_slug': 'moscow_half'},
    {'name': 'Московский марафон', 'date': '2026-10-11', 'location': 'Москва', 'url': 'https://moscowmarathon.runc.run/', 'protocol_slug': 'moscow_marathon_42,2km'},
    {'name': 'Марафон «Белые ночи»', 'date': '2026-06-28', 'location': 'Санкт-Петербург', 'url': 'https://whitenightsmarathon.ru/', 'protocol_slug': 'whitenights'},
]


class RunCParser(RaceParser):
    """Парсер Беговое сообщество (RunC, бывш. Юнистар)"""

    SOURCE_NAME = "Беговое сообщество"
    BASE_URL = "https://runc.run"

    async def parse_upcoming(self) -> List[Dict]:
        """Парсинг предстоящих забегов Беговое сообщество"""
        races = []
        try:
            logger.info("Парсинг Беговое сообщество (RunC)...")
            for ev in RUNC_EVENTS_2026:
                slug = ev.get('protocol_slug', '')
                year = ev['date'][:4]  # 2026
                proto_url = f"https://results.runc.run/event/{slug}_{year}/overview/" if slug else ""
                raw = {
                    'name': ev['name'],
                    'date': ev['date'],
                    'city': ev['location'],
                    'location': ev['location'],
                    'url': ev['url'],
                    'organizer': 'Беговое сообщество',
                    'distances': [],
                    'protocol_url': proto_url,
                }
                race = self.normalize_race_data(raw)
                if self.is_future_race(race.get('date')):
                    races.append(race)
            logger.info(f"Беговое сообщество: найдено {len(races)} забегов")
        except Exception as e:
            logger.error(f"Беговое сообщество: ошибка - {e}")
        return races
