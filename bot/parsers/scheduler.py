"""
Seido - Планировщик парсинга забегов
Автоматический запуск парсеров по расписанию
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Dict

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from parsers.base import RaceParser
from parsers.russiarunning import RussiaRunningParser
from parsers.myrace import MyRaceParser
from parsers.ironstar import IronStarParser
from db import db

logger = logging.getLogger(__name__)


class ParseScheduler:
    """Планировщик парсинга забегов"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.parsers: List[RaceParser] = []
        self._setup_parsers()
    
    def _setup_parsers(self):
        """Настройка парсеров"""
        self.parsers = [
            RussiaRunningParser(),
            MyRaceParser(),
            IronStarParser(),
        ]
    
    async def parse_all(self) -> Dict[str, int]:
        """
        Запуск всех парсеров
        
        Returns:
            Словарь с количеством добавленных забегов по источникам
        """
        results = {}
        
        logger.info("🔄 Запуск парсинга забегов...")
        
        for parser in self.parsers:
            try:
                logger.info(f"Парсинг {parser.SOURCE_NAME}...")
                races = await parser.parse_upcoming()
                
                added = 0
                for race in races:
                    is_new = await self._save_race(race)
                    if is_new:
                        added += 1
                
                results[parser.SOURCE_NAME] = added
                logger.info(f"{parser.SOURCE_NAME}: добавлено {added} забегов")
                
                await parser.close()
                
            except Exception as e:
                logger.error(f"Ошибка парсинга {parser.SOURCE_NAME}: {e}")
                results[parser.SOURCE_NAME] = 0
        
        total = sum(results.values())
        logger.info(f"✅ Парсинг завершён. Всего добавлено: {total} забегов")
        
        return results
    
    async def _save_race(self, race: Dict) -> bool:
        """
        Сохранение забега в базу данных
        
        Args:
            race: Данные о забеге
            
        Returns:
            True если забег новый, False если уже существует
        """
        try:
            # Проверка на дубликат
            existing = await db.get_race_by_url(race.get('website_url', ''))
            if existing:
                logger.debug(f"Забег уже существует: {race['name']}")
                return False
            
            # Сохранение в базу
            await db.add_race(
                name=race.get('name', ''),
                date=race.get('date'),
                location=race.get('location', ''),
                organizer=race.get('organizer', ''),
                race_type=race.get('race_type', 'шоссе'),
                distances=race.get('distances', '[]'),
                website_url=race.get('website_url', ''),
                source=race.get('source', ''),
            )
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения забега: {e}")
            return False
    
    def start(self):
        """Запуск планировщика"""
        # Ежедневный парсинг в 3:00
        self.scheduler.add_job(
            self.parse_all,
            CronTrigger(hour=3, minute=0),
            id='daily_parse',
            name='Ежедневный парсинг забегов'
        )
        
        self.scheduler.start()
        logger.info("📅 Планировщик запущен (парсинг в 3:00 ежедневно)")
    
    def stop(self):
        """Остановка планировщика"""
        self.scheduler.shutdown()
        logger.info("📅 Планировщик остановлен")


# Глобальный экземпляр
scheduler = ParseScheduler()


# Функция для ручного запуска из бота
async def run_parse() -> Dict[str, int]:
    """Ручной запуск парсинга (для команды /parse)"""
    return await scheduler.parse_all()
