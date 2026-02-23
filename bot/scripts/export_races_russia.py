#!/usr/bin/env python3
"""
Seido — экспорт забегов в России за период в CSV/XLSX
Период: 01.01.2025 — 22.02.2026
Запуск: python -m bot.scripts.export_races_russia
"""
import asyncio
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bot.db import db


def _protocol_format(url: str) -> str:
    """Определить формат протокола по URL"""
    if not url or not url.strip():
        return "нет"
    u = url.lower()
    if "results.russiarunning.com" in u:
        return "RussiaRunning (HTML)"
    if "results.runc.run" in u:
        return "RunC (HTML)"
    if "my.raceresult.com" in u:
        return "RaceResult (HTML)"
    if ".pdf" in u or u.endswith(".pdf"):
        return "PDF"
    if ".xlsx" in u or u.endswith(".xlsx"):
        return "Excel (.xlsx)"
    if ".xls" in u or u.endswith(".xls"):
        return "Excel (.xls)"
    return "другой (HTML/ссылка)"


def _format_distances(dist: str | None) -> str:
    """Преобразовать distances в читаемый вид"""
    if not dist:
        return ""
    try:
        data = json.loads(dist)
        if isinstance(data, list):
            names = [d.get("name", d) if isinstance(d, dict) else str(d) for d in data]
            return "; ".join(names)
    except (json.JSONDecodeError, TypeError):
        pass
    return str(dist) if dist else ""


async def run_export(date_from: str = "2025-01-01", date_to: str = "2026-02-22"):
    """Экспорт забегов в CSV"""
    await db.connect()

    sql = """
        SELECT r.id, r.name, r.date, r.location, r.organizer, r.race_type,
               r.distances, r.website_url, r.protocol_url,
               (SELECT COUNT(*) FROM results res WHERE res.race_id = r.id) as results_count
        FROM races r
        WHERE r.date >= ? AND r.date <= ?
          AND r.is_active = 1
        ORDER BY r.date ASC, r.name
    """
    async with db.db.execute(sql, (date_from, date_to)) as cursor:
        rows = await cursor.fetchall()

    races = [dict(row) for row in rows]

    out_path = Path(__file__).parent.parent.parent / "data" / "races_russia_2025_2026.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow([
            "Дата",
            "Название",
            "Вид забега",
            "Дистанции",
            "Организатор",
            "Город/место",
            "Есть протокол",
            "Формат протокола",
            "Результатов в БД",
            "Ссылка на забег",
            "Ссылка на протокол",
        ])
        for r in races:
            protocol_url = (r.get("protocol_url") or "").strip()
            has_protocol = "да" if protocol_url else "нет"
            fmt = _protocol_format(protocol_url) if protocol_url else ""
            writer.writerow([
                r.get("date", ""),
                r.get("name", ""),
                r.get("race_type") or "",
                _format_distances(r.get("distances")),
                r.get("organizer") or "",
                r.get("location") or "",
                has_protocol,
                fmt,
                r.get("results_count") or 0,
                r.get("website_url") or "",
                protocol_url,
            ])

    await db.disconnect()
    print(f"Экспортировано {len(races)} забегов → {out_path}")


if __name__ == "__main__":
    asyncio.run(run_export())
