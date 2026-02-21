"""
Seido - Парсер RussiaRunning (russiarunning.com)
Парсинг через API
"""
import aiohttp
import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional
from .base import RaceParser

logger = logging.getLogger(__name__)

API_URL = "https://russiarunning.com/api/events/list/ru"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


class RussiaRunningParser(RaceParser):
    """Парсер RussiaRunning через API"""
    
    SOURCE_NAME = "RussiaRunning"
    BASE_URL = "https://russiarunning.com"
    
    async def parse_upcoming(self) -> List[Dict]:
        """
        Парсинг предстоящих забегов с RussiaRunning
        
        Returns:
            Список словарей с данными о забегах
        """
        races = []
        
        try:
            logger.info(f"Парсинг RussiaRunning...")
            
            # Получаем события на ближайшие 6 месяцев
            end_date = date.today() + timedelta(days=180)
            events = await self._fetch_events_until_date(end_date)
            
            for event in events:
                try:
                    race = self._normalize_event(event)
                    if race and self.is_future_race(race.get('date')):
                        races.append(race)
                except Exception as e:
                    logger.debug(f"Ошибка обработки события RussiaRunning: {e}")
                    continue
            
            logger.info(f"RussiaRunning: найдено {len(races)} забегов")
            
        except Exception as e:
            logger.error(f"RussiaRunning: ошибка парсинга - {e}")
        
        return races
    
    async def _fetch_events_until_date(self, end_date: date) -> List[Dict]:
        """Получает все события до указанной даты"""
        today = date.today()
        
        try:
            payload = {
                "Take": 500,
                "DateFrom": today.isoformat()
            }
            
            session = await self.get_session()
            async with session.post(API_URL, json=payload, headers=HEADERS) as resp:
                if resp.status != 200:
                    raise Exception(f"RussiaRunning API error: {resp.status}")
                data = await resp.json()
            
            events = []
            for item in data.get("Items", []):
                event_date_str = item.get("d", "").split("T")[0]
                try:
                    event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
                    if event_date <= end_date:
                        events.append({
                            "source": "russiarunning",
                            "external_id": str(item.get("c", "")),
                            "title": item.get("t", "").strip(),
                            "city": item.get("p", "").strip(),
                            "event_date": event_date,
                            "url": f"https://russiarunning.com/event/{item.get('c', '')}/"
                        })
                except ValueError:
                    continue
            
            return events
            
        except Exception as e:
            logger.error(f"RussiaRunning: ошибка получения событий - {e}")
            return []
    
    def _normalize_event(self, event: Dict) -> Dict:
        """Нормализация события RussiaRunning"""
        raw = {
            'name': event.get('title', ''),
            'date': event.get('event_date'),
            'city': event.get('city', ''),
            'location': event.get('city', ''),
            'url': event.get('url', ''),
            'distances': [],
        }
        
        return self.normalize_race_data(raw)
    
    async def parse_results(self, race_url: str) -> List[Dict]:
        """
        Парсинг результатов забега
        
        RussiaRunning имеет протоколы, но они требуют отдельного парсинга.
        Для MVP возвращаем пустой список.
        
        Args:
            race_url: URL страницы забега
            
        Returns:
            Пустой список
        """
        logger.warning(f"RussiaRunning: парсинг результатов недоступен для {race_url}")
        return []


# Оставляем старые функции для обратной совместимости
async def fetch_russiarunning_events(
    date_from: str = None,
    take: int = 500
) -> List[Dict]:
    """
    Получает список событий с API RussiaRunning.
    """
    if date_from is None:
        date_from = date.today().isoformat()
    
    payload = {
        "Take": take,
        "DateFrom": date_from
    }
    
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.post(API_URL, json=payload) as resp:
            if resp.status != 200:
                raise Exception(f"RussiaRunning API error: {resp.status}")
            data = await resp.json()
    
    events = []
    for item in data.get("Items", []):
        event_date_str = item.get("d", "").split("T")[0]
        try:
            event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        
        events.append({
            "source": "russiarunning",
            "external_id": str(item.get("c", "")),
            "title": item.get("t", "").strip(),
            "city": item.get("p", "").strip(),
            "event_date": event_date,
            "url": f"https://russiarunning.com/event/{item.get('c', '')}/"
        })
    
    return events


async def fetch_events_until_date(end_date: date) -> List[Dict]:
    """
    Получает все события до указанной даты.
    """
    today = date.today()
    events = await fetch_russiarunning_events(
        date_from=today.isoformat(),
        take=500
    )
    
    # Фильтруем по дате окончания
    filtered_events = [
        ev for ev in events 
        if ev["event_date"] <= end_date
    ]
    
    return filtered_events
