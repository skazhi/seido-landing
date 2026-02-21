#!/usr/bin/env python3
"""
Seido - Поиск и сбор протоколов за период 01.01.2025 - 20.02.2026
1. Добавляет прошлые забеги в БД (RussiaRunning API с DateFrom в прошлом)
2. Ищет URL протоколов на страницах забегов
3. Запускает сбор результатов
"""
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


async def main():
    await db.connect()
    log(f"Поиск протоколов за {DATE_FROM} — {DATE_TO}")

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
    await run_collect()

    await db.disconnect()
    log("Готово.")


if __name__ == "__main__":
    asyncio.run(main())
