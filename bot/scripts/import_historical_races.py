#!/usr/bin/env python3
"""
Seido — импорт исторических забегов в РФ
Дубликаты не создаются. Для RR сохраняем protocol_url для последующего сбора протоколов.
Запуск: python -m bot.scripts.import_historical_races
        python -m bot.scripts.import_historical_races --period 2023
"""
import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import aiohttp

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bot.db import db

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Периоды по умолчанию
PERIODS = {
    "2024_2026": ("2024-01-01", "2026-02-22"),
    "2023": ("2023-01-01", "2024-01-01"),
}
RR_API_URL = "https://russiarunning.com/api/events/list/ru"
RR_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


async def fetch_rr_events(date_from: str, date_to: str) -> list[dict]:
    """Получить все события RussiaRunning за период (с пагинацией)"""
    events = []
    skip = 0
    take = 200

    async with aiohttp.ClientSession(headers=RR_HEADERS) as session:
        while True:
            payload = {"Take": take, "Skip": skip, "DateFrom": date_from}
            try:
                async with session.post(RR_API_URL, json=payload) as resp:
                    if resp.status != 200:
                        logger.warning(f"RR API error: {resp.status}")
                        break
                    data = await resp.json()
            except Exception as e:
                logger.warning(f"RR API request error: {e}")
                break

            items = data.get("Items", [])
            if not items:
                break

            for item in items:
                event_date_str = (item.get("d") or "").split("T")[0]
                try:
                    event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
                except ValueError:
                    continue

                date_from_dt = datetime.strptime(date_from, "%Y-%m-%d").date()
                date_to_dt = datetime.strptime(date_to, "%Y-%m-%d").date()
                if event_date < date_from_dt or event_date > date_to_dt:
                    continue

                event_id = item.get("c", "")
                events.append({
                    "name": (item.get("t") or "").strip(),
                    "date": event_date_str,
                    "location": (item.get("p") or "").strip(),
                    "url": f"https://russiarunning.com/event/{event_id}/",
                    "protocol_url": f"https://results.russiarunning.com/event/{event_id}/" if event_id else "",
                    "organizer": "RussiaRunning",
                })

            logger.info(f"  RR: загружено {len(events)} событий (skip={skip})")
            if len(items) < take:
                break
            if len(items) == 0:
                break
            skip += take
            await asyncio.sleep(0.5)  # вежливая пауза

    return events


def _static_events_2023() -> list[dict]:
    """Забеги RunC, WildTrail за 2023"""
    return [
        {"name": "Московский марафон", "date": "2023-10-15", "location": "Москва",
         "url": "https://moscowmarathon.runc.run/", "organizer": "Беговое сообщество",
         "protocol_url": "https://results.runc.run/event/moscow_marathon_42,2km_2023/overview/"},
        {"name": "Марафон «Белые ночи»", "date": "2023-07-02", "location": "Санкт-Петербург",
         "url": "https://whitenightsmarathon.ru/", "organizer": "Беговое сообщество",
         "protocol_url": "https://results.runc.run/event/whitenights_2023/overview/"},
        {"name": "Московский полумарафон", "date": "2023-04-23", "location": "Москва",
         "url": "https://moscowhalf.runc.run/", "organizer": "Беговое сообщество",
         "protocol_url": "https://results.runc.run/event/moscow_half_2023/overview/"},
        {"name": "Arkhyz Wild Trail", "date": "2023-06-23", "location": "Архыз",
         "url": "https://wildtrail.ru/awt", "organizer": "Wild Trail", "protocol_url": "https://wildtrail.ru/results"},
        {"name": "Rosa Wild Fest", "date": "2023-09-02", "location": "Сочи",
         "url": "https://wildtrail.ru/rwt", "organizer": "Wild Trail", "protocol_url": "https://wildtrail.ru/results"},
    ]


def _static_events_2024_2025() -> list[dict]:
    """Дополнительные забеги RunC, WildTrail и др. за 2024–2025 (известные)"""
    # RunC / Беговое сообщество
    runc = [
        {"name": "Московский марафон", "date": "2024-10-13", "location": "Москва",
         "url": "https://moscowmarathon.runc.run/", "organizer": "Беговое сообщество",
         "protocol_url": "https://results.runc.run/event/moscow_marathon_42,2km_2024/overview/"},
        {"name": "Московский марафон", "date": "2025-10-12", "location": "Москва",
         "url": "https://moscowmarathon.runc.run/", "organizer": "Беговое сообщество",
         "protocol_url": "https://results.runc.run/event/moscow_marathon_42,2km_2025/overview/"},
        {"name": "Марафон «Белые ночи»", "date": "2024-06-29", "location": "Санкт-Петербург",
         "url": "https://whitenightsmarathon.ru/", "organizer": "Беговое сообщество",
         "protocol_url": "https://results.runc.run/event/whitenights_2024/overview/"},
        {"name": "Марафон «Белые ночи»", "date": "2025-06-28", "location": "Санкт-Петербург",
         "url": "https://whitenightsmarathon.ru/", "organizer": "Беговое сообщество",
         "protocol_url": "https://results.runc.run/event/whitenights_2025/overview/"},
        {"name": "Московский полумарафон", "date": "2024-04-28", "location": "Москва",
         "url": "https://moscowhalf.runc.run/", "organizer": "Беговое сообщество",
         "protocol_url": "https://results.runc.run/event/moscow_half_2024/overview/"},
        {"name": "Московский полумарафон", "date": "2025-04-27", "location": "Москва",
         "url": "https://moscowhalf.runc.run/", "organizer": "Беговое сообщество",
         "protocol_url": "https://results.runc.run/event/moscow_half_2025/overview/"},
    ]
    # Wild Trail
    wildtrail = [
        {"name": "Arkhyz Wild Trail", "date": "2024-06-28", "location": "Архыз",
         "url": "https://wildtrail.ru/awt", "organizer": "Wild Trail", "protocol_url": "https://wildtrail.ru/results"},
        {"name": "Rosa Wild Fest", "date": "2024-09-06", "location": "Сочи",
         "url": "https://wildtrail.ru/rwt", "organizer": "Wild Trail", "protocol_url": "https://wildtrail.ru/results"},
        {"name": "Arkhyz Wild Trail", "date": "2025-06-27", "location": "Архыз",
         "url": "https://wildtrail.ru/awt", "organizer": "Wild Trail", "protocol_url": "https://wildtrail.ru/results"},
        {"name": "Rosa Wild Fest", "date": "2025-09-05", "location": "Сочи",
         "url": "https://wildtrail.ru/rwt", "organizer": "Wild Trail", "protocol_url": "https://wildtrail.ru/results"},
    ]
    return runc + wildtrail


def _get_static_events(date_from: str, date_to: str) -> list[dict]:
    """Статические забеги в заданном периоде"""
    all_static = _static_events_2023() + _static_events_2024_2025()
    from_dt = datetime.strptime(date_from, "%Y-%m-%d").date()
    to_dt = datetime.strptime(date_to, "%Y-%m-%d").date()
    result = []
    for ev in all_static:
        try:
            d = datetime.strptime(ev["date"], "%Y-%m-%d").date()
            if from_dt <= d < to_dt:
                result.append(ev)
        except ValueError:
            continue
    return result


async def load_existing_keys() -> tuple[set[str], set[tuple[str, str]]]:
    """Загрузить в память существующие URL и (name, date) для быстрой проверки дубликатов"""
    urls = set()
    name_dates = set()
    async with db.db.execute("SELECT website_url, name, date FROM races") as cursor:
        rows = await cursor.fetchall()
    for row in rows:
        url = (row[0] or "").strip()
        name = (row[1] or "").strip()
        date_str = (row[2] or "").strip()
        if url:
            urls.add(url)
        if name and date_str:
            name_dates.add((name, date_str))
    return urls, name_dates


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", choices=list(PERIODS.keys()), default="2024_2026",
                        help="Период: 2024_2026 (по умолч.) или 2023")
    parser.add_argument("--date-from", help="Начало периода (YYYY-MM-DD)")
    parser.add_argument("--date-to", help="Конец периода (YYYY-MM-DD)")
    args = parser.parse_args()

    if args.date_from and args.date_to:
        date_from, date_to = args.date_from, args.date_to
    else:
        date_from, date_to = PERIODS[args.period]
    logger.info(f"Период: {date_from} — {date_to}")

    await db.connect()

    urls, name_dates = await load_existing_keys()
    logger.info(f"В БД уже есть забегов с URL, проверка дубликатов по (name,date)")

    total_added = 0

    def is_duplicate(name: str, date_str: str, url: str) -> bool:
        if url and url in urls:
            return True
        key = (name.strip(), date_str)
        if key in name_dates:
            return True
        return False

    def mark_added(name: str, date_str: str, url: str):
        if url:
            urls.add(url)
        name_dates.add((name.strip(), date_str))

    # 1. RussiaRunning
    logger.info("RussiaRunning: загрузка событий...")
    rr_events = await fetch_rr_events(date_from, date_to)
    logger.info(f"RussiaRunning: получено {len(rr_events)} событий в периоде")

    to_insert = []
    for ev in rr_events:
        name = (ev.get("name") or "").strip()
        date_str = ev.get("date") or ""
        url = (ev.get("url") or "").strip()
        if not name or not date_str:
            continue
        if is_duplicate(name, date_str, url):
            continue
        to_insert.append({
            "name": name,
            "date": date_str,
            "location": ev.get("location", ""),
            "organizer": ev.get("organizer", "RussiaRunning"),
            "website_url": url,
            "protocol_url": (ev.get("protocol_url") or "").strip(),
        })
        mark_added(name, date_str, url)

    # Пакетная вставка RR (одна транзакция)
    if to_insert:
        for r in to_insert:
            await db.db.execute(
                """INSERT INTO races (name, date, location, organizer, race_type, distances, website_url, protocol_url, is_active)
                   VALUES (?, ?, ?, ?, 'шоссе', '[]', ?, ?, 1)""",
                (r["name"], r["date"], r["location"], r["organizer"], r["website_url"], r["protocol_url"]),
            )
        await db.db.commit()
    total_added = len(to_insert)
    logger.info(f"RussiaRunning: добавлено {total_added} новых забегов")

    # 2. RunC, WildTrail и др. (статический список)
    static = _get_static_events(date_from, date_to)
    static_to_insert = []
    for ev in static:
        name = (ev.get("name") or "").strip()
        date_str = ev.get("date") or ""
        url = (ev.get("url") or "").strip()
        if not name or not date_str:
            continue
        if is_duplicate(name, date_str, url):
            continue
        static_to_insert.append({
            "name": name,
            "date": date_str,
            "location": ev.get("location", ""),
            "organizer": ev.get("organizer", ""),
            "website_url": url,
            "protocol_url": (ev.get("protocol_url") or "").strip(),
        })
        mark_added(name, date_str, url)

    if static_to_insert:
        for r in static_to_insert:
            await db.db.execute(
                """INSERT INTO races (name, date, location, organizer, race_type, distances, website_url, protocol_url, is_active)
                   VALUES (?, ?, ?, ?, ?, '[]', ?, ?, 1)""",
                (r["name"], r["date"], r["location"], r["organizer"], "шоссе", r["website_url"], r["protocol_url"]),
            )
        await db.db.commit()
    static_added = len(static_to_insert)
    total_added += static_added
    logger.info(f"RunC/WildTrail и др.: добавлено {static_added} новых забегов")

    await db.disconnect()
    logger.info(f"Итого добавлено: {total_added} забегов")


if __name__ == "__main__":
    asyncio.run(main())
