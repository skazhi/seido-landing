# Импортируем только то, что нужно для RussiaRunning
from .russiarunning import fetch_russiarunning_events, fetch_events_until_date

__all__ = [
    'fetch_russiarunning_events',
    'fetch_events_until_date'
]
