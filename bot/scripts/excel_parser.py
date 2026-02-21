"""
Seido - Парсер Excel протоколов
Использует pandas для чтения Excel файлов
"""
import pandas as pd
import logging
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ExcelProtocolParser:
    """Парсер протоколов из Excel файлов"""
    
    def __init__(self, file_path: str):
        """
        Args:
            file_path: Путь к Excel файлу
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")
    
    def read_sheet(self, sheet_name: Optional[str] = None, header_row: int = 0) -> pd.DataFrame:
        """
        Чтение листа из Excel файла
        
        Args:
            sheet_name: Название листа (если None, то первый лист)
            header_row: Номер строки с заголовками
            
        Returns:
            DataFrame с данными
        """
        try:
            df = pd.read_excel(
                self.file_path,
                sheet_name=sheet_name,
                header=header_row,
                engine='openpyxl'  # Для .xlsx файлов
            )
            logger.info(f"Прочитан лист: {sheet_name or 'первый'}, строк: {len(df)}")
            return df
        except Exception as e:
            logger.error(f"Ошибка при чтении Excel: {e}")
            raise
    
    def parse_sheet(self, sheet_name: Optional[str] = None, header_row: int = 0) -> List[Dict]:
        """
        Парсинг листа в список словарей
        
        Args:
            sheet_name: Название листа
            header_row: Номер строки с заголовками
            
        Returns:
            Список словарей с данными
        """
        df = self.read_sheet(sheet_name, header_row)
        
        # Удаление пустых строк
        df = df.dropna(how='all')
        
        # Конвертация в список словарей
        results = df.to_dict('records')
        
        # Преобразование значений в строки и очистка
        cleaned_results = []
        for row in results:
            cleaned_row = {}
            for key, value in row.items():
                if pd.notna(value):
                    cleaned_row[str(key).strip()] = str(value).strip()
                else:
                    cleaned_row[str(key).strip()] = ''
            cleaned_results.append(cleaned_row)
        
        logger.info(f"Извлечено {len(cleaned_results)} строк из листа")
        return cleaned_results
    
    def get_sheet_names(self) -> List[str]:
        """
        Получить список названий листов
        
        Returns:
            Список названий листов
        """
        try:
            excel_file = pd.ExcelFile(self.file_path, engine='openpyxl')
            return excel_file.sheet_names
        except Exception as e:
            logger.error(f"Ошибка при получении списка листов: {e}")
            return []
    
    def parse(self, sheet_name: Optional[str] = None, header_row: int = 0) -> List[Dict]:
        """
        Полный парсинг протокола
        
        Args:
            sheet_name: Название листа (если None, то первый лист)
            header_row: Номер строки с заголовками
            
        Returns:
            Список словарей с результатами
        """
        logger.info(f"Парсинг Excel: {self.file_path.name}")
        
        if sheet_name is None:
            # Если лист не указан, пробуем найти подходящий
            sheet_names = self.get_sheet_names()
            if sheet_names:
                # Ищем лист с названием, содержащим "протокол", "результаты" и т.д.
                for name in sheet_names:
                    name_lower = name.lower()
                    if any(keyword in name_lower for keyword in ['протокол', 'результаты', 'results', 'protocol']):
                        sheet_name = name
                        logger.info(f"Автоматически выбран лист: {sheet_name}")
                        break
                
                # Если не нашли, берем первый
                if sheet_name is None:
                    sheet_name = sheet_names[0]
                    logger.info(f"Используется первый лист: {sheet_name}")
        
        results = self.parse_sheet(sheet_name, header_row)
        logger.info(f"Всего извлечено {len(results)} результатов")
        return results
