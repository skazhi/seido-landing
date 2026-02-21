"""
Seido - Нормализация данных из протоколов
Обработка ФИО, времени, места, даты рождения
"""
import re
from typing import Dict, Optional, Tuple
from datetime import datetime


def normalize_name(full_name: str) -> Dict[str, str]:
    """
    Нормализация ФИО из протокола
    
    Поддерживаемые форматы:
    - "Иванов Иван Иванович"
    - "Иванов И.И."
    - "ИВАНОВ ИВАН"
    - "Иванов Иван"
    
    Returns:
        Словарь с ключами: first_name, last_name, middle_name
    """
    if not full_name or not isinstance(full_name, str):
        return {'first_name': '', 'last_name': '', 'middle_name': None}
    
    # Очистка от лишних пробелов
    name = ' '.join(full_name.split())
    
    # Разделение на части
    parts = name.split()
    
    if len(parts) == 0:
        return {'first_name': '', 'last_name': '', 'middle_name': None}
    elif len(parts) == 1:
        # Только фамилия или имя
        return {'first_name': '', 'last_name': parts[0].title(), 'middle_name': None}
    elif len(parts) == 2:
        # Фамилия Имя
        return {
            'first_name': parts[1].title(),
            'last_name': parts[0].title(),
            'middle_name': None
        }
    else:
        # Фамилия Имя Отчество
        return {
            'first_name': parts[1].title(),
            'last_name': parts[0].title(),
            'middle_name': parts[2].title() if len(parts) > 2 else None
        }


def normalize_time(time_str: str) -> Optional[int]:
    """
    Нормализация времени финиша в секунды
    
    Поддерживаемые форматы:
    - "15:30" (MM:SS)
    - "1:15:30" (HH:MM:SS)
    - "15:30.5" (MM:SS.mmm)
    - "930" (секунды)
    - "1ч 15м 30с"
    
    Returns:
        Время в секундах или None
    """
    if not time_str:
        return None
    
    # Удаление пробелов
    time_str = str(time_str).strip()
    
    # Если уже число (секунды)
    if time_str.isdigit():
        return int(time_str)
    
    # Удаление лишних символов
    time_str = re.sub(r'[^\d:.]', '', time_str)
    
    # Формат MM:SS или HH:MM:SS
    if ':' in time_str:
        parts = time_str.split(':')
        if len(parts) == 2:
            # MM:SS
            try:
                minutes = int(parts[0])
                seconds = float(parts[1])
                return int(minutes * 60 + seconds)
            except ValueError:
                return None
        elif len(parts) == 3:
            # HH:MM:SS
            try:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = float(parts[2])
                return int(hours * 3600 + minutes * 60 + seconds)
            except ValueError:
                return None
    
    # Формат "1ч 15м 30с" или "1:15:30"
    match = re.search(r'(\d+)[чh:]\s*(\d+)[мm:]\s*(\d+)', time_str, re.IGNORECASE)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = int(match.group(3))
        return hours * 3600 + minutes * 60 + seconds
    
    return None


def normalize_place(place_str: str) -> Optional[int]:
    """
    Нормализация места
    
    Поддерживаемые форматы:
    - "1"
    - "1-е"
    - "1 место"
    - "DNF" (Did Not Finish)
    - "DSQ" (Disqualified)
    
    Returns:
        Место (число) или None
    """
    if not place_str:
        return None
    
    place_str = str(place_str).strip().upper()
    
    # DNF, DSQ, DNS
    if place_str in ['DNF', 'DSQ', 'DNS', 'НФ', 'СН', 'ДИСК']:
        return None
    
    # Извлечение числа
    match = re.search(r'(\d+)', place_str)
    if match:
        return int(match.group(1))
    
    return None


def normalize_birth_date(birth_str: str) -> Optional[str]:
    """
    Нормализация даты рождения
    
    Поддерживаемые форматы:
    - "1990" (только год)
    - "1990-05-15" (YYYY-MM-DD)
    - "15.05.1990" (DD.MM.YYYY)
    - "15/05/1990" (DD/MM/YYYY)
    
    Returns:
        Дата в формате YYYY-MM-DD или None
    """
    if not birth_str:
        return None
    
    birth_str = str(birth_str).strip()
    
    # Только год
    if birth_str.isdigit() and len(birth_str) == 4:
        year = int(birth_str)
        if 1950 <= year <= 2010:  # Разумный диапазон
            return f"{year}-01-01"  # Устанавливаем 1 января
    
    # Полная дата
    formats = [
        '%Y-%m-%d',      # 1990-05-15
        '%d.%m.%Y',      # 15.05.1990
        '%d/%m/%Y',      # 15/05/1990
        '%Y.%m.%d',      # 1990.05.15
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(birth_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    return None


def normalize_distance(distance_str: str) -> str:
    """
    Нормализация дистанции
    
    Поддерживаемые форматы:
    - "5 км"
    - "5км"
    - "5000 м"
    - "5K"
    - "5.0"
    
    Returns:
        Нормализованная дистанция (например, "5 км")
    """
    if not distance_str:
        return ""
    
    distance_str = str(distance_str).strip()
    
    # Извлечение числа
    match = re.search(r'(\d+\.?\d*)', distance_str)
    if not match:
        return distance_str
    
    distance = float(match.group(1))
    
    # Определение единиц измерения
    if 'км' in distance_str.lower() or 'km' in distance_str.lower() or 'k' in distance_str.lower():
        return f"{distance:.1f} км".rstrip('0').rstrip('.')
    elif 'м' in distance_str.lower() or 'm' in distance_str.lower():
        # Метры в километры
        km = distance / 1000
        return f"{km:.1f} км".rstrip('0').rstrip('.')
    else:
        # По умолчанию километры
        return f"{distance:.1f} км".rstrip('0').rstrip('.')


def normalize_gender(gender_str: str) -> Optional[str]:
    """
    Нормализация пола
    
    Returns:
        'M' или 'F' или None
    """
    if not gender_str:
        return None
    
    gender_str = str(gender_str).strip().upper()
    
    if gender_str in ['М', 'M', 'МУЖ', 'MALE', 'МУЖСКОЙ']:
        return 'M'
    elif gender_str in ['Ж', 'F', 'ЖЕН', 'FEMALE', 'ЖЕНСКИЙ']:
        return 'F'
    
    return None


def normalize_city(city_str: str) -> str:
    """
    Нормализация города
    
    Returns:
        Очищенное название города
    """
    if not city_str:
        return ""
    
    city = str(city_str).strip()
    
    # Удаление лишних символов
    city = re.sub(r'[^\w\s-]', '', city)
    
    # Капитализация
    return city.title()


def _looks_like_runner_name(text: str) -> bool:
    """Проверка: похоже ли на ФИО (а не на категорию/дистанцию)"""
    if not text or len(text) < 4:
        return False
    t = text.lower()
    # Категории и метки, которые не ФИО
    skip = ("онлайн", "офлайн", "участие", "забег", "детский", "км.", "км ", "полумарафон",
            "марафон", "дистанц", "категор", "всего", "место", "фио")
    if any(s in t for s in skip):
        return False
    # Должна содержать буквы
    if not any(c.isalpha() for c in text):
        return False
    return True


def normalize_protocol_row(row: Dict) -> Dict:
    """
    Нормализация одной строки протокола
    
    Args:
        row: Словарь с сырыми данными из протокола
        
    Returns:
        Нормализованный словарь
    """
    normalized = {}
    
    # ФИО
    full_name = row.get('name') or row.get('full_name') or row.get('фио') or ''
    if not _looks_like_runner_name(full_name):
        return {'first_name': '', 'last_name': '', **{k: None for k in [
            'middle_name', 'finish_time_seconds', 'overall_place', 'birth_date', 'distance',
            'gender', 'city', 'gender_place', 'age_group_place', 'age_group', 'club'
        ]}}
    name_parts = normalize_name(full_name)
    normalized.update(name_parts)
    
    # Время
    time_str = row.get('time') or row.get('finish_time') or row.get('время') or ''
    normalized['finish_time_seconds'] = normalize_time(time_str)
    
    # Место
    place_str = row.get('place') or row.get('место') or row.get('overall_place') or ''
    normalized['overall_place'] = normalize_place(place_str)
    
    # Дата рождения
    birth_str = row.get('birth_date') or row.get('birth_year') or row.get('год_рождения') or ''
    normalized['birth_date'] = normalize_birth_date(birth_str)
    
    # Дистанция
    distance_str = row.get('distance') or row.get('дистанция') or ''
    normalized['distance'] = normalize_distance(distance_str)
    
    # Пол
    gender_str = row.get('gender') or row.get('пол') or row.get('sex') or ''
    normalized['gender'] = normalize_gender(gender_str)
    
    # Город
    city_str = row.get('city') or row.get('город') or row.get('location') or ''
    normalized['city'] = normalize_city(city_str)
    
    # Дополнительные поля
    normalized['gender_place'] = normalize_place(row.get('gender_place') or row.get('место_по_полу') or '')
    normalized['age_group_place'] = normalize_place(row.get('age_group_place') or row.get('место_в_категории') or '')
    normalized['age_group'] = row.get('age_group') or row.get('возрастная_категория') or None
    normalized['club'] = row.get('club') or row.get('клуб') or None
    
    return normalized
