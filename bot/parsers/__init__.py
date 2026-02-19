"""
Seido Parsers - Парсеры забегов из различных источников
"""
from .base import RaceParser
from .russiarunning import RussiaRunningParser
from .myrace import MyRaceParser
from .ironstar import IronStarParser

__all__ = [
    'RaceParser',
    'RussiaRunningParser',
    'MyRaceParser',
    'IronStarParser',
]
