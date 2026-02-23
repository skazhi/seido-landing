#!/usr/bin/env python3
"""
Seido - Поиск и сбор протоколов за период 01.01.2025 - 20.02.2026
1. Добавляет прошлые забеги в БД (RussiaRunning API с DateFrom в прошлом)
2. Ищет URL протоколов на страницах забегов
3. Запускает сбор результатов
"""
import argparse
import asyncio
import re
import sys
from pathlib import Path
from datetime import date, datetime

import aiohttp

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bot.db import db


DATE_FROM = "2025-01-01"
DATE_TO = "2026-02-20"
RUSSIA_RUNNING_API = "https://russiarunning.com/api/events/list/ru"


async def fetch_rr_events() -> list:
    """События RussiaRunning за период (включая прошедшие)"""
    payload = {"Take": 1000, "DateFrom": DATE_FROM}
    async with aiohttp.ClientSession() as session:
        async with session.post(RUSSIA_RUNNING_API, json=payload) as resp:
            if resp.status != 200:
                log(f"RussiaRunning API error: {resp.status}")
                return []
            data = await resp.json()
    today = date.today()
    date_to = datetime.strptime(DATE_TO, "%Y-%m-%d").date()
    events = []
    for item in data.get("Items", []):
        try:
            ds = item.get("d", "").split("T")[0]
            d = datetime.strptime(ds, "%Y-%m-%d").date()
            if d < today and d <= date_to:  # только прошедшие
                events.append({
                    "title": item.get("t", "").strip(),
                    "city": item.get("p", "").strip(),
                    "date": d.isoformat(),
                    "url": f"https://russiarunning.com/event/{item.get('c', '')}/",
                    "external_id": str(item.get("c", "")),
                })
        except (ValueError, TypeError):
            continue
    return events


async def find_protocol_url(page_url: str) -> str | None:
    """Ищет ссылку на протокол на странице забега"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(page_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
    except Exception:
        return None
    # Ищем PDF, Excel, или ссылки с result/protocol
    patterns = [
        r'href="([^"]+\.pdf[^"]*)"',
        r'href="([^"]+\.xlsx[^"]*)"',
        r'href="([^"]+\.xls)"',
        r'href="(https?://[^"]*result[^"]*)"',
        r'href="(https?://[^"]*protocol[^"]*)"',
        r'href="(https?://[^"]*протокол[^"]*)"',
        r'href="/event/[^/]+/result',
    ]
    for p in patterns:
        m = re.search(p, html, re.I)
        if m:
            url = m.group(1)
            if url.startswith("/"):
                url = "https://russiarunning.com" + url
            if "russiarunning" in url or url.endswith(".pdf") or url.endswith(".xlsx"):
                return url
    return None


def log(msg: str):
    print(msg, flush=True)


# Прошедшие забеги RunC/Wild Trail/RHR с известными URL протоколов
PAST_RUNC_EVENTS = [
    {"name": "Московский марафон", "date": "2024-10-13", "location": "Москва", "url": "https://moscowmarathon.runc.run/", "protocol_slug": "moscow_marathon_42,2km_2024"},
    {"name": "Московский марафон", "date": "2025-10-12", "location": "Москва", "url": "https://moscowmarathon.runc.run/", "protocol_slug": "moscow_marathon_42,2km_2025"},
    {"name": "Московский полумарафон", "date": "2024-04-28", "location": "Москва", "url": "https://moscowhalf.runc.run/", "protocol_slug": "moscow_half_2024"},
    {"name": "Московский полумарафон", "date": "2025-04-27", "location": "Москва", "url": "https://moscowhalf.runc.run/", "protocol_slug": "moscow_half_2025"},
    {"name": "Соревнования «Скорость»", "date": "2024-02-24", "location": "Москва", "url": "https://speedrace.runc.run/", "protocol_slug": "speedrace_2024"},
    {"name": "Соревнования «Скорость»", "date": "2025-02-22", "location": "Москва", "url": "https://speedrace.runc.run/", "protocol_slug": "speedrace_2025"},
    {"name": "Забег «Апрель»", "date": "2024-04-07", "location": "Москва", "url": "https://aprilrun5km.runc.run/", "protocol_slug": "aprilrun5km_2024"},
    {"name": "Забег «Апрель»", "date": "2025-04-06", "location": "Москва", "url": "https://aprilrun5km.runc.run/", "protocol_slug": "aprilrun5km_2025"},
    {"name": "Марафон «Белые ночи»", "date": "2024-06-29", "location": "Санкт-Петербург", "url": "https://whitenightsmarathon.ru/", "protocol_slug": "whitenights_2024"},
    {"name": "Марафон «Белые ночи»", "date": "2025-06-28", "location": "Санкт-Петербург", "url": "https://whitenightsmarathon.ru/", "protocol_slug": "whitenights_2025"},
]

PAST_WILDTRAIL_EVENTS = [
    {"name": "Arkhyz Wild Trail", "date": "2024-06-29", "location": "Архыз", "url": "https://wildtrail.ru/awt", "protocol_url": "https://wildtrail.ru/results"},
    {"name": "Arkhyz Wild Trail", "date": "2025-06-28", "location": "Архыз", "url": "https://wildtrail.ru/awt", "protocol_url": "https://wildtrail.ru/results"},
    {"name": "Dagestan Wild Trail", "date": "2024-04-13", "location": "Дагестан", "url": "https://wildtrail.ru/dwt", "protocol_url": "https://wildtrail.ru/results"},
    {"name": "Dagestan Wild Trail", "date": "2025-04-12", "location": "Дагестан", "url": "https://wildtrail.ru/dwt", "protocol_url": "https://wildtrail.ru/results"},
    {"name": "Rosa Wild Trail", "date": "2024-09-07", "location": "Сочи", "url": "https://wildtrail.ru/rwt", "protocol_url": "https://wildtrail.ru/results"},
    {"name": "Rosa Wild Trail", "date": "2025-09-06", "location": "Сочи", "url": "https://wildtrail.ru/rwt", "protocol_url": "https://wildtrail.ru/results"},
]


async def _upsert_race_with_protocol(ev: dict, organizer: str, race_type: str, protocol_url: str):
    """Добавить забег или обновить protocol_url. Ищем по (name, date), т.к. url может быть общим для разных лет."""
    async with db.db.execute(
        "SELECT id, protocol_url, website_url FROM races WHERE name = ? AND date = ?",
        (ev["name"], ev["date"])
    ) as c:
        row = await c.fetchone()
    if row:
        rid, proto, _ = row[0], row[1], row[2]
        if not proto and protocol_url:
            await db.db.execute("UPDATE races SET protocol_url = ? WHERE id = ?", (protocol_url, rid))
            await db.db.commit()
        elif proto != protocol_url and protocol_url:
            await db.db.execute("UPDATE races SET protocol_url = ? WHERE id = ?", (protocol_url, rid))
            await db.db.commit()
        return rid, False
    # Новый забег — используем url с датой для уникальности (один site на несколько лет)
    website_url = f"{ev['url'].rstrip('/')}?year={ev['date'][:4]}"
    rid = await db.add_race(
        name=ev["name"], date=ev["date"], location=ev.get("location", ""),
        organizer=organizer, race_type=race_type, distances="[]",
        website_url=website_url, protocol_url=protocol_url or "",
    )
    return rid, True


async def process_runc_wildtrail():
    """Добавить/обновить прошедшие забеги RunC и Wild Trail"""
    added, updated = 0, 0
    for ev in PAST_RUNC_EVENTS:
        proto = f"https://results.runc.run/event/{ev['protocol_slug']}/overview/"
        _, is_new = await _upsert_race_with_protocol(ev, "Беговое сообщество", "шоссе", proto)
        if is_new:
            added += 1
        else:
            updated += 1
    log(f"RunC: добавлено {added}, обновлено {updated}")

    added, updated = 0, 0
    for ev in PAST_WILDTRAIL_EVENTS:
        proto = ev.get("protocol_url", "https://wildtrail.ru/results")
        _, is_new = await _upsert_race_with_protocol(ev, "Wild Trail", "трейл", proto)
        if is_new:
            added += 1
        else:
            updated += 1
    log(f"Wild Trail: добавлено {added}, обновлено {updated}")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-rr", action="store_true",
                        help="При сборе результатов пропустить RussiaRunning, 5верст, S95")
    args = parser.parse_args()

    await db.connect()
    log(f"Поиск протоколов за {DATE_FROM} — {DATE_TO}")

    # RunC и Wild Trail — статические списки
    log("\nОбработка RunC и Wild Trail...")
    await process_runc_wildtrail()

    events = await fetch_rr_events()
    log(f"RussiaRunning: найдено {len(events)} прошедших забегов")

    added_races = 0
    protocols_found = 0
    for i, ev in enumerate(events):
        name = ev["title"]
        race_date = ev["date"]
        url = ev["url"]
        city = ev.get("city", "")

        # Проверяем, есть ли забег
        async with db.db.execute(
            "SELECT id, protocol_url FROM races WHERE website_url = ? OR (name = ? AND date = ?)",
            (url, name, race_date)
        ) as c:
            row = await c.fetchone()
        if row:
            rid, proto = row[0], row[1]
            if proto:
                protocols_found += 1
                continue
        else:
            # Добавляем забег
            try:
                rid = await db.add_race(
                    name=name,
                    date=race_date,
                    location=city,
                    organizer="RussiaRunning",
                    race_type="шоссе",
                    distances="[]",
                    website_url=url,
                    protocol_url="",
                )
                added_races += 1
            except Exception as e:
                log(f"  Ошибка добавления {name}: {e}")
                continue

        # RussiaRunning: страницы SPA — ссылок на PDF в HTML нет, сразу используем results
        proto_url = None
        if ev.get("external_id"):
            proto_url = f"https://results.russiarunning.com/event/{ev['external_id']}"
        # Для других источников: await find_protocol_url(url)
        if proto_url:
            await db.db.execute(
                "UPDATE races SET protocol_url = ? WHERE id = ?",
                (proto_url, rid)
            )
            await db.db.commit()
            protocols_found += 1
            log(f"  [{protocols_found}] {name[:40]}... -> {proto_url[:60]}...")

        if (i + 1) % 20 == 0:
            log(f"  Обработано {i+1}/{len(events)}")

    log(f"\nДобавлено забегов: {added_races}, с протоколами: {protocols_found}")

    # Запуск сбора
    log("\nЗапуск сбора результатов...")
    from bot.scripts.collect_results import run_collect
    await run_collect(exclude_rr_5verst_s95=args.skip_rr)

    await db.disconnect()
    log("Готово.")


if __name__ == "__main__":
    asyncio.run(main())
