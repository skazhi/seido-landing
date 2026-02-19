"""
Seido - Парсер IronStar (iron-star.com)
Парсинг HTML страницы со списком забегов
"""
import aiohttp
import logging
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from .base import RaceParser

logger = logging.getLogger(__name__)


class IronStarParser(RaceParser):
    """Парсер IronStar"""
    
    SOURCE_NAME = "IronStar"
    BASE_URL = "https://iron-star.com"
    EVENTS_URL = "https://iron-star.com/events"
    
    async def parse_upcoming(self) -> List[Dict]:
        """
        Парсинг предстоящих забегов с IronStar
        
        Returns:
            Список словарей с данными о забегах
        """
        session = await self.get_session()
        races = []
        
        try:
            logger.info(f"Парсинг IronStar...")
            
            async with session.get(self.EVENTS_URL) as response:
                if response.status != 200:
                    logger.error(f"IronStar error: {response.status}")
                    return races
                
                html = await response.text(encoding='utf-8')
                soup = BeautifulSoup(html, 'html.parser')
                
                # Поиск элементов забегов
                # IronStar использует .event-item-wrap для карточек событий
                event_items = soup.select('.event-item-wrap, .event-card, a.event-item')
                
                for item in event_items:
                    try:
                        race = self._parse_event(item)
                        if race and self.is_future_race(race.get('date')):
                            races.append(race)
                    except Exception as e:
                        logger.debug(f"Ошибка парсинга события IronStar: {e}")
                        continue
                
                logger.info(f"IronStar: найдено {len(races)} забегов")
                
        except aiohttp.ClientError as e:
            logger.error(f"IronStar: ошибка соединения - {e}")
        except Exception as e:
            logger.error(f"IronStar: непредвиденная ошибка - {e}")
        
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
            if not url:
                link = item.find('a')
                url = link.get('href', '') if link else ''
            if url and not url.startswith('http'):
                url = f"{self.BASE_URL}{url}"
            
            # Извлечение названия
            name = ''
            name_elem = item.select_one('h2, h3, .event-name, .event-title')
            if name_elem:
                # Удаляем дочерние элементы (бейджики, даты внутри заголовка)
                for child in name_elem.find_all(['span', 'small', 'badge', 'time']):
                    child.decompose()
                name = name_elem.get_text(strip=True)
            else:
                name = item.get_text(strip=True)[:100]
            
            # Извлечение даты
            date_str = ''
            date_elem = item.select_one('.date, .event-date, time, .date-time')
            if date_elem:
                date_str = date_elem.get_text(strip=True)
            
            # Извлечение города/места
            location = ''
            location_elem = item.select_one('.city, .location, .place, .geo')
            if location_elem:
                location = location_elem.get_text(strip=True)
            
            # Извлечение дистанций (если указаны на карточке)
            distances = []
            dist_elem = item.select_one('.distance, .distances')
            if dist_elem:
                dist_text = dist_elem.get_text(strip=True)
                # Парсинг строки типа "5 км, 10 км, 21 км"
                for d in dist_text.split(','):
                    d = d.strip()
                    if d:
                        distances.append({'name': d, 'elevation': 0})
            
            raw = {
                'name': name,
                'date': date_str,
                'city': location,
                'location': location,
                'url': url,
                'distances': distances,
            }
            
            return self.normalize_race_data(raw)
            
        except Exception as e:
            logger.debug(f"Ошибка парсинга события IronStar: {e}")
            return None
    
    async def parse_results(self, race_url: str) -> List[Dict]:
        """
        Парсинг результатов забега
        
        IronStar имеет протоколы, но они требуют отдельного парсинга.
        Для MVP возвращаем пустой список.
        
        Args:
            race_url: URL страницы забега
            
        Returns:
            Пустой список
        """
        logger.warning(f"IronStar: парсинг результатов недоступен для {race_url}")
        return []
