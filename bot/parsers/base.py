"""
Seido - Базовый класс для парсеров забегов
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from datetime import datetime, date
import re
import aiohttp
import logging

logger = logging.getLogger(__name__)


class RaceParser(ABC):
    """Базовый класс для парсеров забегов"""
    
    SOURCE_NAME: str = "unknown"
    BASE_URL: str = ""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Получить HTTP сессию"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                },
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session
    
    async def close(self):
        """Закрыть сессию"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    @abstractmethod
    async def parse_upcoming(self) -> List[Dict]:
        """
        Парсинг предстоящих забегов
        
        Returns:
            Список словарей с данными о забегах
        """
        pass
    
    def normalize_race_data(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Приведение данных к единому формату
        
        Args:
            raw: Сырые данные от парсера
            
        Returns:
            Нормализованные данные
        """
        return {
            'name': self.clean_string(raw.get('name', '')),
            'date': self.parse_date(raw.get('date')),
            'location': self.clean_string(raw.get('city', raw.get('location', ''))),
            'organizer': self.detect_organizer(raw),
            'race_type': raw.get('race_type', 'шоссе'),
            'distances': self.parse_distances(raw.get('distances', [])),
            'website_url': raw.get('url', raw.get('website_url', '')),
            'protocol_url': raw.get('protocol_url', ''),
            'source': self.SOURCE_NAME,
            'is_active': True,
        }
    
    def clean_string(self, text: str) -> str:
        """Очистка строки от лишних пробелов и символов"""
        if not text:
            return ''
        return ' '.join(text.split())
    
    def parse_date(self, date_str: str) -> Optional[str]:
        """
        Парсинг даты из различных форматов
        
        Поддерживаемые форматы:
        - DD.MM.YYYY
        - YYYY-MM-DD
        - DD Month YYYY
        - Month DD, YYYY
        """
        if not date_str:
            return None
        
        # Уже дата
        if isinstance(date_str, date):
            return date_str.isoformat()
        
        date_str = self.clean_string(date_str)
        
        # Форматы для парсинга
        formats = [
            '%d.%m.%Y',      # 15.03.2026
            '%Y-%m-%d',      # 2026-03-15
            '%d %B %Y',      # 15 марта 2026
            '%d %b %Y',      # 15 мар 2026
            '%B %d, %Y',     # March 15, 2026
            '%b %d, %Y',     # Mar 15, 2026
            '%d.%m.%Y %H:%M', # 15.03.2026 10:00
        ]
        
        # Русские месяцы
        month_map = {
            'января': 'January', 'февраля': 'February', 'марта': 'March',
            'апреля': 'April', 'мая': 'May', 'июня': 'June',
            'июля': 'July', 'августа': 'August', 'сентября': 'September',
            'октября': 'October', 'ноября': 'November', 'декабря': 'December',
            'янв': 'Jan', 'фев': 'Feb', 'мар': 'Mar', 'апр': 'Apr',
            'июн': 'Jun', 'июл': 'Jul', 'авг': 'Aug', 'сен': 'Sep',
            'окт': 'Oct', 'ноя': 'Nov', 'дек': 'Dec',
        }
        
        # Замена русских месяцев на английские
        for ru, en in month_map.items():
            date_str = date_str.lower().replace(ru, en)
        
        for fmt in formats:
            try:
                parsed = datetime.strptime(date_str, fmt)
                return parsed.date().isoformat()
            except ValueError:
                continue
        
        # Попытка найти дату в строке
        date_match = re.search(r'\d{1,2}\.\d{1,2}\.\d{4}', date_str)
        if date_match:
            try:
                parsed = datetime.strptime(date_match.group(), '%d.%m.%Y')
                return parsed.date().isoformat()
            except ValueError:
                pass
        
        logger.warning(f"Не удалось распарсить дату: {date_str}")
        return None
    
    def detect_organizer(self, raw: Dict) -> str:
        """
        Определение организатора по URL или названию.
        Канонические имена см. в docs/ORGANIZERS.md
        """
        url = raw.get('url', '').lower()
        name = raw.get('name', '').lower()
        
        organizers = {
            '5verst': '5верст',
            '5 верст': '5верст',
            's95': 'S95',
            'sport-95': 'S95',
            'rhr': 'RHR',
            'runhide': 'RHR',
            'rhr-marathon': 'RHR',
            'moscow marathon': 'Московский марафон',
            'moscowmarathon': 'Московский марафон',
            'ironstar': 'IronStar',
            'iron-star': 'IronStar',
            'russiarunning': 'RussiaRunning',
            'myrace': 'MyRace',
            'timerman': 'TIMERMAN',
            'kazan.run': 'TIMERMAN',
            'kazan marathon': 'TIMERMAN',
            'казанский марафон': 'TIMERMAN',
            'runc.run': 'Юнистар',
            'unistar': 'Юнистар',
            'юнистар': 'Юнистар',
            'белые ночи': 'Марафон «Белые ночи»',
            'whitenights': 'Марафон «Белые ночи»',
            'runup': 'RUNUP',
            'iloverunning': 'I Love Running',
            'orgeo': 'Orgeo',
            'cronosport': 'CronoSport',
        }
        
        for key, value in organizers.items():
            if key in url or key in name:
                return value
        
        return raw.get('organizer', 'Не указан')
    
    def parse_distances(self, distances: Any) -> str:
        """
        Парсинг дистанций в JSON формат
        
        Args:
            distances: Может быть строкой, списком или dict
            
        Returns:
            JSON строка с дистанциями
        """
        import json
        
        if not distances:
            return json.dumps([])
        
        if isinstance(distances, str):
            # Попытка распарсить JSON
            try:
                return distances
            except:
                # Строка с дистанциями
                return json.dumps([{'name': distances, 'elevation': 0}])
        
        if isinstance(distances, list):
            result = []
            for d in distances:
                if isinstance(d, str):
                    result.append({'name': d, 'elevation': 0})
                elif isinstance(d, dict):
                    result.append(d)
            return json.dumps(result)
        
        return json.dumps([])
    
    def is_future_race(self, race_date: Optional[str]) -> bool:
        """Проверка, что забег в будущем"""
        if not race_date:
            return False
        try:
            parsed = datetime.fromisoformat(race_date).date()
            return parsed >= date.today()
        except:
            return False
