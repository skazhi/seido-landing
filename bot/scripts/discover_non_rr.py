#!/usr/bin/env python3
"""
Seido - Поиск и сбор результатов БЕЗ RussiaRunning, 5верст, S95
Период: 01.06.2025 - 20.02.2026
Источники: RunC, Wild Trail, RHR, IronStar (протоколы где есть)
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bot.db import db

DATE_FROM = "2025-06-01"
DATE_TO = "2026-02-20"


def _in_period(d: str) -> bool:
    return DATE_FROM <= d <= DATE_TO


def log(msg: str):
    print(msg, flush=True)


# События за период 01.06.2025 - 20.02.2026 (часть до июня — для полноты, фильтр _in_period)
EVENTS_2025_2026 = [
    # RunC — results.runc.run (парсим Playwright)
    {"name": "Марафон «Белые ночи»", "date": "2025-06-28", "location": "Санкт-Петербург",
     "url": "https://whitenightsmarathon.ru/", "protocol_slug": "whitenights_2025",
     "organizer": "Беговое сообщество", "race_type": "шоссе"},
    {"name": "Московский марафон", "date": "2025-10-12", "location": "Москва",
     "url": "https://moscowmarathon.runc.run/", "protocol_slug": "moscow_marathon_42,2km_2025",
     "organizer": "Беговое сообщество", "race_type": "шоссе"},
    # Wild Trail — wildtrail.ru/results
    {"name": "Arkhyz Wild Trail", "date": "2025-06-28", "location": "Архыз",
     "url": "https://wildtrail.ru/awt", "protocol_url": "https://wildtrail.ru/results",
     "organizer": "Wild Trail", "race_type": "трейл"},
    {"name": "Rosa Wild Trail", "date": "2025-09-06", "location": "Сочи",
     "url": "https://wildtrail.ru/rwt", "protocol_url": "https://wildtrail.ru/results",
     "organizer": "Wild Trail", "race_type": "трейл"},
    {"name": "Dagestan Wild Trail", "date": "2025-04-12", "location": "Дагестан",
     "url": "https://wildtrail.ru/dwt", "protocol_url": "https://wildtrail.ru/results",
     "organizer": "Wild Trail", "race_type": "трейл"},
    # RaceResult (my.raceresult.com) — парсим Playwright
    {"name": "Московский спорт Гром 10К Измайлово", "date": "2025-11-22", "location": "Москва",
     "url": "https://my.raceresult.com/372673/", "protocol_url": "https://my.raceresult.com/372673/results",
     "organizer": "Grom Chrono", "race_type": "шоссе"},
    {"name": "Большой Московский триатлон", "date": "2025-06-01", "location": "Москва",
     "url": "https://my.raceresult.com/344093/", "protocol_url": "https://my.raceresult.com/344093/results",
     "organizer": "IronStar", "race_type": "триатлон"},
    # RHR — probeg.org (парсинг пока нет)
    {"name": "Golden Ring Ultra Trail 100", "date": "2025-07-24", "location": "Суздаль",
     "url": "https://goldenultra.ru/grut/", "protocol_url": "https://probeg.org/race/54011/",
     "organizer": "RHR", "race_type": "трейл"},
    {"name": "White Bridge Ultra Gelendzhik", "date": "2025-10-02", "location": "Геленджик",
     "url": "https://goldenultra.ru/", "protocol_url": "",
     "organizer": "RHR", "race_type": "трейл"},
    {"name": "Crazy Owl 50", "date": "2025-06-12", "location": "Москва",
     "url": "https://goldenultra.ru/", "protocol_url": "",
     "organizer": "RHR", "race_type": "трейл"},
    {"name": "Kalmyk Camel Trophy", "date": "2025-04-18", "location": "Калмыкия",
     "url": "https://goldenultra.ru/", "protocol_url": "",
     "organizer": "RHR", "race_type": "трейл"},
]


async def _upsert_race(ev: dict) -> bool:
    """Добавить забег или обновить protocol_url. Возвращает True если добавлен/обновлён."""
    protocol_url = ev.get("protocol_url") or (
        f"https://results.runc.run/event/{ev['protocol_slug']}/overview/"
        if ev.get("protocol_slug") else ""
    )
    async with db.db.execute(
        "SELECT id, protocol_url FROM races WHERE name = ? AND date = ?",
        (ev["name"], ev["date"])
    ) as c:
        row = await c.fetchone()
    if row:
        rid, proto = row[0], row[1]
        if protocol_url and proto != protocol_url:
            await db.db.execute("UPDATE races SET protocol_url = ? WHERE id = ?", (protocol_url, rid))
            await db.db.commit()
        return False
    website_url = f"{ev['url'].rstrip('/')}?year={ev['date'][:4]}"
    await db.add_race(
        name=ev["name"], date=ev["date"], location=ev.get("location", ""),
        organizer=ev["organizer"], race_type=ev.get("race_type", "шоссе"), distances="[]",
        website_url=website_url, protocol_url=protocol_url or "",
    )
    return True


async def main():
    parser = argparse.ArgumentParser(description="Поиск и сбор результатов без RR, 5верст, S95")
    parser.add_argument("--no-collect", action="store_true", help="Только добавить забеги, не запускать сбор")
    args = parser.parse_args()

    await db.connect()
    log(f"Период: {DATE_FROM} — {DATE_TO}")
    log("Источники: RunC, Wild Trail, RHR, RaceResult (без RussiaRunning, 5верст, S95)\n")

    # Фильтр по периоду
    events = [e for e in EVENTS_2025_2026 if _in_period(e["date"])]
    log(f"Событий в периоде: {len(events)}")

    added = 0
    for ev in events:
        is_new = await _upsert_race(ev)
        if is_new:
            added += 1
            log(f"  + {ev['name']} ({ev['date']})")
    log(f"\nДобавлено/обновлено: {added} новых")

    if not args.no_collect:
        log("\nЗапуск сбора результатов...")
        from bot.scripts.collect_results import run_collect
        await run_collect(exclude_rr_5verst_s95=True)

    await db.disconnect()
    log("Готово.")


if __name__ == "__main__":
    asyncio.run(main())
