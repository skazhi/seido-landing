"""
Seido - Парсер MyRace (myrace.info)
Парсинг HTML страницы со списком забегов
"""
import aiohttp
import logging
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from .base import RaceParser

logger = logging.getLogger(__name__)


class MyRaceParser(RaceParser):
    """Парсер MyRace"""
    
    SOURCE_NAME = "MyRace"
    BASE_URL = "https://myrace.info"
    CALENDAR_URL = "https://myrace.info/calendar"
    
    async def parse_upcoming(self) -> List[Dict]:
        """
        Парсинг предстоящих забегов с MyRace
        
        Returns:
            Список словарей с данными о забегах
        """
        session = await self.get_session()
        races = []
        
        try:
            logger.info(f"Парсинг MyRace...")
            
            async with session.get(self.CALENDAR_URL) as response:
                if response.status != 200:
                    logger.error(f"MyRace error: {response.status}")
                    return races
                
                html = await response.text(encoding='utf-8')
                soup = BeautifulSoup(html, 'html.parser')
                
                # Поиск элементов забегов
                # Селектор может измениться, нужно мониторить
                event_items = soup.select('.events-list__item, .event-card, a[href*="/event/"]')
                
                for item in event_items:
                    try:
                        race = self._parse_event(item)
                        if race and self.is_future_race(race.get('date')):
                            races.append(race)
                    except Exception as e:
                        logger.debug(f"Ошибка парсинга события MyRace: {e}")
                        continue
                
                logger.info(f"MyRace: найдено {len(races)} забегов")
                
        except aiohttp.ClientError as e:
            logger.error(f"MyRace: ошибка соединения - {e}")
        except Exception as e:
            logger.error(f"MyRace: непредвиденная ошибка - {e}")
        
        return races
    
    def _parse_event(self, item) -> Optional[Dict]:
        """
        Парсинг одного события из HTML
        
        Args:
            item: BeautifulSoup элемент
            
        Returns:
            Нормализованные данные о забеге
        """
        try:
            # Извлечение ссылки
            url = item.get('href', '')
            if url and not url.startswith('http'):
                url = f"{self.BASE_URL}{url}"
            
            # Извлечение названия
            name = ''
            name_elem = item.select_one('h2, .event-name, .title')
            if name_elem:
                # Удаляем дочерние элементы (например, бейджики)
                for child in name_elem.find_all(['span', 'small', 'badge']):
                    child.decompose()
                name = name_elem.get_text(strip=True)
            else:
                name = item.get_text(strip=True)[:100]
            
            # Извлечение даты
            date_str = ''
            date_elem = item.select_one('.date, .event-date, time')
            if date_elem:
                date_str = date_elem.get_text(strip=True)
            
            # Извлечение города/места
            location = ''
            location_elem = item.select_one('.city, .location, .place')
            if location_elem:
                location = location_elem.get_text(strip=True)
            
            raw = {
                'name': name,
                'date': date_str,
                'city': location,
                'location': location,
                'url': url,
                'distances': [],
            }
            
            return self.normalize_race_data(raw)
            
        except Exception as e:
            logger.debug(f"Ошибка парсинга события MyRace: {e}")
            return None
    
    async def parse_results(self, race_url: str) -> List[Dict]:
        """
        Парсинг результатов забега
        
        MyRace не предоставляет публичные протоколы,
        поэтому этот метод возвращает пустой список.
        
        Args:
            race_url: URL страницы забега
            
        Returns:
            Пустой список
        """
        logger.warning(f"MyRace: парсинг результатов недоступен для {race_url}")
        return []
