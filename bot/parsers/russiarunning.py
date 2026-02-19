"""
Seido - Парсер RussiaRunning (russiarunning.com)
Использует API: https://russiarunning.com/api/events/list/ru
"""
import aiohttp
import logging
from typing import List, Dict, Optional
from .base import RaceParser

logger = logging.getLogger(__name__)


class RussiaRunningParser(RaceParser):
    """Парсер RussiaRunning"""
    
    SOURCE_NAME = "RussiaRunning"
    BASE_URL = "https://russiarunning.com"
    API_URL = "https://russiarunning.com/api/events/list/ru"
    
    async def parse_upcoming(self) -> List[Dict]:
        """
        Парсинг предстоящих забегов через API RussiaRunning
        
        Returns:
            Список словарей с данными о забегах
        """
        session = await self.get_session()
        races = []
        
        try:
            # Параметры запроса
            payload = {
                'Take': 500,  # Максимальное количество
                'DateFrom': '',  # Все будущие
                'Filters': {},
            }
            
            logger.info(f"Парсинг RussiaRunning...")
            
            async with session.post(self.API_URL, json=payload) as response:
                if response.status != 200:
                    logger.error(f"RussiaRunning API error: {response.status}")
                    return races
                
                data = await response.json()
                
                if not data or 'Items' not in data:
                    logger.warning("RussiaRunning: нет данных в ответе")
                    return races
                
                for item in data['Items']:
                    try:
                        race = self._parse_event(item)
                        if race and self.is_future_race(race.get('date')):
                            races.append(race)
                    except Exception as e:
                        logger.error(f"Ошибка парсинга события: {e}")
                        continue
                
                logger.info(f"RussiaRunning: найдено {len(races)} забегов")
                
        except aiohttp.ClientError as e:
            logger.error(f"RussiaRunning: ошибка соединения - {e}")
        except Exception as e:
            logger.error(f"RussiaRunning: непредвиденная ошибка - {e}")
        
        return races
    
    def _parse_event(self, item: Dict) -> Optional[Dict]:
        """
        Парсинг одного события из API
        
        Args:
            item: Данные события из API
            
        Returns:
            Нормализованные данные о забеге
        """
        try:
            # Извлечение базовой информации
            raw = {
                'name': item.get('Name', ''),
                'date': item.get('StartDate', ''),
                'city': item.get('City', ''),
                'location': item.get('Location', ''),
                'url': f"{self.BASE_URL}{item.get('Url', '')}",
                'distances': [],
            }
            
            # Парсинг дистанций
            distances = []
            if 'Distances' in item:
                for dist in item['Distances']:
                    distances.append({
                        'name': dist.get('Name', ''),
                        'length': dist.get('Length', 0),
                        'elevation': dist.get('ElevationGain', 0),
                    })
            raw['distances'] = distances
            
            # Определение типа забега
            race_type = 'шоссе'
            if item.get('TypeName'):
                type_name = item.get('TypeName', '').lower()
                if 'трейл' in type_name or 'trail' in type_name:
                    race_type = 'трейл'
                elif 'кросс' in type_name:
                    race_type = 'кросс'
                elif 'стадион' in type_name:
                    race_type = 'стадион'
            
            raw['race_type'] = race_type
            
            return self.normalize_race_data(raw)
            
        except Exception as e:
            logger.error(f"Ошибка парсинга события RussiaRunning: {e}")
            return None
    
    async def parse_results(self, race_url: str) -> List[Dict]:
        """
        Парсинг результатов забега
        
        RussiaRunning не предоставляет публичные протоколы через API,
        поэтому этот метод возвращает пустой список.
        
        Args:
            race_url: URL страницы забега
            
        Returns:
            Пустой список (требуется ручной парсинг или договор)
        """
        logger.warning(f"RussiaRunning: парсинг результатов недоступен для {race_url}")
        return []
