"""
Seido - Основной парсер протоколов забегов
Объединяет парсеры PDF и Excel, нормализует данные и импортирует в БД
"""
import asyncio
import sys
import logging
from pathlib import Path
from typing import List, Dict, Optional

# Добавляем путь к корню проекта
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bot.scripts.pdf_parser import PDFProtocolParser
from bot.scripts.excel_parser import ExcelProtocolParser
from bot.scripts.normalize_data import normalize_protocol_row
from bot.db import db

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ProtocolImporter:
    """Импортер протоколов в базу данных"""
    
    def __init__(self):
        self.stats = {
            'races_created': 0,
            'runners_created': 0,
            'runners_found': 0,
            'results_added': 0,
            'errors': 0
        }
    
    async def find_or_create_runner(
        self,
        first_name: str,
        last_name: str,
        birth_date: Optional[str] = None,
        gender: Optional[str] = None,
        city: Optional[str] = None
    ) -> int:
        """
        Найти существующего бегуна или создать нового
        
        Returns:
            ID бегуна
        """
        # Поиск существующего бегуна
        runner = await db.get_runner_by_name(
            last_name=last_name,
            first_name=first_name,
            birth_date=birth_date
        )
        
        if runner:
            self.stats['runners_found'] += 1
            return runner['id']
        
        # Создание нового бегуна (без telegram_id для импортированных)
        cursor = await db.db.execute(
            """
            INSERT INTO runners (first_name, last_name, middle_name, birth_date, gender, city)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (first_name, last_name, None, birth_date, gender, city)
        )
        await db.db.commit()
        
        self.stats['runners_created'] += 1
        return cursor.lastrowid
    
    async def find_or_create_race(
        self,
        name: str,
        date: str,
        location: str = '',
        organizer: str = '',
        race_type: str = 'шоссе',
        distances: str = '[]',
        website_url: str = '',
        protocol_url: str = ''
    ) -> int:
        """
        Найти существующий забег или создать новый
        
        Returns:
            ID забега
        """
        # Поиск по URL
        if website_url:
            existing = await db.get_race_by_url(website_url)
            if existing:
                return existing['id']
        
        # Поиск по названию и дате
        async with db.db.execute(
            "SELECT id FROM races WHERE name = ? AND date = ?",
            (name, date)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0]
        
        # Создание нового забега
        race_id = await db.add_race(
            name=name,
            date=date,
            location=location,
            organizer=organizer,
            race_type=race_type,
            distances=distances,
            website_url=website_url,
            protocol_url=protocol_url
        )
        
        self.stats['races_created'] += 1
        return race_id
    
    async def import_result(
        self,
        runner_id: int,
        race_id: int,
        distance: str,
        finish_time_seconds: Optional[int],
        overall_place: Optional[int] = None,
        gender_place: Optional[int] = None,
        age_group_place: Optional[int] = None,
        total_runners: Optional[int] = None
    ):
        """Импорт результата в базу"""
        try:
            await db.add_result(
                runner_id=runner_id,
                race_id=race_id,
                distance=distance,
                finish_time_seconds=finish_time_seconds,
                overall_place=overall_place,
                gender_place=gender_place,
                age_group_place=age_group_place,
                total_runners=total_runners
            )
            self.stats['results_added'] += 1
        except Exception as e:
            logger.error(f"Ошибка при добавлении результата: {e}")
            self.stats['errors'] += 1
    
    async def import_protocol(
        self,
        file_path: str,
        race_name: str,
        race_date: str,
        race_location: str = '',
        race_organizer: str = '',
        race_type: str = 'шоссе',
        distance: str = '',
        website_url: str = '',
        protocol_url: str = '',
        header_row: int = 0,
        sheet_name: Optional[str] = None
    ):
        """
        Импорт протокола из файла
        
        Args:
            file_path: Путь к файлу (PDF или Excel)
            race_name: Название забега
            race_date: Дата забега (YYYY-MM-DD)
            race_location: Место проведения
            race_organizer: Организатор
            race_type: Тип забега (шоссе, трейл, кросс)
            distance: Дистанция (если одна для всех)
            website_url: URL страницы забега
            protocol_url: URL протокола
            header_row: Номер строки с заголовками
            sheet_name: Название листа (для Excel)
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        
        logger.info(f"Начало импорта протокола: {file_path.name}")
        logger.info(f"Забег: {race_name} ({race_date})")
        
        # Парсинг файла
        if file_path.suffix.lower() == '.pdf':
            parser = PDFProtocolParser(str(file_path))
            raw_data = parser.parse(header_row=header_row)
        elif file_path.suffix.lower() in ['.xlsx', '.xls']:
            parser = ExcelProtocolParser(str(file_path))
            raw_data = parser.parse(sheet_name=sheet_name, header_row=header_row)
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {file_path.suffix}")
        
        if not raw_data:
            logger.warning("Не удалось извлечь данные из файла")
            return
        
        logger.info(f"Извлечено {len(raw_data)} строк из протокола")
        
        # Создание забега
        distances_json = f'[{{"name": "{distance}", "elevation": 0}}]' if distance else '[]'
        race_id = await self.find_or_create_race(
            name=race_name,
            date=race_date,
            location=race_location,
            organizer=race_organizer,
            race_type=race_type,
            distances=distances_json,
            website_url=website_url,
            protocol_url=protocol_url
        )
        
        # Нормализация и импорт результатов
        imported = 0
        for i, row in enumerate(raw_data, 1):
            try:
                # Нормализация данных
                normalized = normalize_protocol_row(row)
                
                # Пропускаем строки без обязательных данных
                if not normalized.get('last_name') or not normalized.get('first_name'):
                    continue
                
                # Используем дистанцию из параметров или из данных
                result_distance = distance or normalized.get('distance', '')
                if not result_distance:
                    continue
                
                # Поиск или создание бегуна
                runner_id = await self.find_or_create_runner(
                    first_name=normalized['first_name'],
                    last_name=normalized['last_name'],
                    birth_date=normalized.get('birth_date'),
                    gender=normalized.get('gender'),
                    city=normalized.get('city')
                )
                
                # Импорт результата
                await self.import_result(
                    runner_id=runner_id,
                    race_id=race_id,
                    distance=result_distance,
                    finish_time_seconds=normalized.get('finish_time_seconds'),
                    overall_place=normalized.get('overall_place'),
                    gender_place=normalized.get('gender_place'),
                    age_group_place=normalized.get('age_group_place'),
                    total_runners=None  # Можно вычислить из общего количества строк
                )
                
                imported += 1
                
                if imported % 100 == 0:
                    logger.info(f"Импортировано {imported} результатов...")
            
            except Exception as e:
                logger.error(f"Ошибка при обработке строки {i}: {e}")
                self.stats['errors'] += 1
                continue
        
        # Обновление total_runners для забега
        await db.db.execute(
            "UPDATE races SET total_runners = ? WHERE id = ?",
            (imported, race_id)
        )
        await db.db.commit()
        
        logger.info(f"Импорт завершён: {imported} результатов")
        self.print_stats()

    async def import_from_raw_data(
        self,
        raw_data: List[Dict],
        race_name: str,
        race_date: str,
        race_location: str = '',
        race_organizer: str = '',
        race_type: str = 'шоссе',
        distance: str = '',
        website_url: str = '',
        protocol_url: str = '',
    ):
        """
        Импорт результатов из уже распарсенных данных (например, из HTML).
        """
        if not raw_data:
            logger.warning("Нет данных для импорта")
            return

        logger.info(f"Импорт из {len(raw_data)} строк: {race_name} ({race_date})")

        dist_json = f'[{{"name": "{distance or "?"}", "elevation": 0}}]'
        race_id = await self.find_or_create_race(
            name=race_name,
            date=race_date,
            location=race_location,
            organizer=race_organizer,
            race_type=race_type,
            distances=dist_json,
            website_url=website_url,
            protocol_url=protocol_url
        )

        imported = 0
        for i, row in enumerate(raw_data, 1):
            try:
                normalized = normalize_protocol_row(row)
                if not normalized.get('last_name') or not normalized.get('first_name'):
                    continue
                result_distance = distance or normalized.get('distance', '') or '?'
                runner_id = await self.find_or_create_runner(
                    first_name=normalized['first_name'],
                    last_name=normalized['last_name'],
                    birth_date=normalized.get('birth_date'),
                    gender=normalized.get('gender'),
                    city=normalized.get('city')
                )
                await self.import_result(
                    runner_id=runner_id,
                    race_id=race_id,
                    distance=result_distance,
                    finish_time_seconds=normalized.get('finish_time_seconds'),
                    overall_place=normalized.get('overall_place'),
                    gender_place=normalized.get('gender_place'),
                    age_group_place=normalized.get('age_group_place'),
                    total_runners=None,
                )
                imported += 1
                if imported % 100 == 0:
                    logger.info(f"Импортировано {imported} результатов...")
            except Exception as e:
                logger.debug(f"Ошибка строка {i}: {e}")
                self.stats['errors'] += 1

        await db.db.commit()
        logger.info(f"Импорт завершён: {imported} результатов")
        self.print_stats()

    def print_stats(self):
        """Вывод статистики импорта"""
        print("\n" + "="*50)
        print("📊 Статистика импорта:")
        print(f"   Забегов создано: {self.stats['races_created']}")
        print(f"   Бегунов создано: {self.stats['runners_created']}")
        print(f"   Бегунов найдено: {self.stats['runners_found']}")
        print(f"   Результатов добавлено: {self.stats['results_added']}")
        print(f"   Ошибок: {self.stats['errors']}")
        print("="*50 + "\n")


async def main():
    """Пример использования"""
    # Подключение к БД
    await db.connect()
    
    importer = ProtocolImporter()
    
    # Пример импорта
    # await importer.import_protocol(
    #     file_path="path/to/protocol.pdf",
    #     race_name="Пятерка в Парке",
    #     race_date="2026-03-01",
    #     race_location="Москва, Парк Горького",
    #     race_organizer="5верст",
    #     distance="5 км",
    #     header_row=0
    # )
    
    print("Парсер протоколов готов к использованию!")
    print("Используйте метод import_protocol() для импорта протоколов")
    
    await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
