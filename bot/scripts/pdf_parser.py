"""
Seido - Парсер PDF протоколов
Использует pdfplumber для извлечения таблиц из PDF
"""
import pdfplumber
import logging
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class PDFProtocolParser:
    """Парсер протоколов из PDF файлов"""
    
    def __init__(self, file_path: str):
        """
        Args:
            file_path: Путь к PDF файлу
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")
    
    def extract_tables(self, page_num: Optional[int] = None) -> List[List[List[str]]]:
        """
        Извлечение таблиц из PDF
        
        Args:
            page_num: Номер страницы (если None, то все страницы)
            
        Returns:
            Список таблиц (каждая таблица - список строк, каждая строка - список ячеек)
        """
        tables = []
        
        try:
            with pdfplumber.open(self.file_path) as pdf:
                pages = [pdf.pages[page_num]] if page_num is not None else pdf.pages
                
                for page in pages:
                    # Извлечение таблиц со страницы
                    page_tables = page.extract_tables()
                    if page_tables:
                        tables.extend(page_tables)
                        logger.info(f"Найдено {len(page_tables)} таблиц на странице {page.page_number}")
        
        except Exception as e:
            logger.error(f"Ошибка при извлечении таблиц из PDF: {e}")
            raise
        
        return tables
    
    def parse_table(self, table: List[List[str]], header_row: int = 0) -> List[Dict]:
        """
        Парсинг таблицы в список словарей
        
        Args:
            table: Таблица (список строк)
            header_row: Номер строки с заголовками (обычно 0)
            
        Returns:
            Список словарей с данными
        """
        if not table or len(table) <= header_row:
            return []
        
        # Извлечение заголовков
        headers = [str(cell).strip() if cell else '' for cell in table[header_row]]
        
        # Нормализация заголовков (приведение к нижнему регистру, удаление пробелов)
        headers = [h.lower().replace(' ', '_').replace('ё', 'е') for h in headers]
        
        # Парсинг строк данных
        results = []
        for row in table[header_row + 1:]:
            if not row or all(not cell or str(cell).strip() == '' for cell in row):
                continue  # Пропускаем пустые строки
            
            # Создание словаря из строки
            row_dict = {}
            for i, header in enumerate(headers):
                if i < len(row):
                    value = row[i]
                    if value is not None:
                        row_dict[header] = str(value).strip()
                    else:
                        row_dict[header] = ''
            
            # Пропускаем строки без данных
            if any(row_dict.values()):
                results.append(row_dict)
        
        return results
    
    def parse(self, page_num: Optional[int] = None, header_row: int = 0) -> List[Dict]:
        """
        Полный парсинг протокола
        
        Args:
            page_num: Номер страницы (если None, то все страницы)
            header_row: Номер строки с заголовками
            
        Returns:
            Список словарей с результатами
        """
        logger.info(f"Парсинг PDF: {self.file_path.name}")
        
        tables = self.extract_tables(page_num)
        
        if not tables:
            logger.warning("Таблицы не найдены в PDF")
            return []
        
        all_results = []
        for i, table in enumerate(tables):
            logger.info(f"Обработка таблицы {i + 1}/{len(tables)}")
            results = self.parse_table(table, header_row)
            all_results.extend(results)
            logger.info(f"Извлечено {len(results)} строк из таблицы {i + 1}")
        
        logger.info(f"Всего извлечено {len(all_results)} результатов")
        return all_results
    
    def detect_columns(self, table: List[List[str]]) -> Dict[str, int]:
        """
        Автоматическое определение колонок по заголовкам
        
        Args:
            table: Таблица (список строк)
            
        Returns:
            Словарь {название_колонки: индекс}
        """
        if not table:
            return {}
        
        headers = [str(cell).strip().lower() if cell else '' for cell in table[0]]
        
        column_map = {}
        
        # Поиск стандартных колонок
        keywords = {
            'место': ['место', 'place', 'позиция', 'pos'],
            'фио': ['фио', 'имя', 'name', 'участник', 'runner'],
            'время': ['время', 'time', 'финиш', 'finish'],
            'дистанция': ['дистанция', 'distance', 'дист'],
            'год': ['год', 'year', 'год_рождения', 'birth'],
            'город': ['город', 'city', 'место', 'location'],
            'пол': ['пол', 'gender', 'sex', 'м/ж'],
            'клуб': ['клуб', 'club', 'команда', 'team'],
        }
        
        for key, variants in keywords.items():
            for i, header in enumerate(headers):
                if any(variant in header for variant in variants):
                    column_map[key] = i
                    break
        
        return column_map
