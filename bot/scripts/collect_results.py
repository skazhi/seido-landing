#!/usr/bin/env python3
"""
Seido - Сбор результатов с протоколов завершённых забегов
Загружает протоколы по URL из БД, парсит и импортирует с матчингом бегунов.
Запуск: python -m bot.scripts.collect_results
        python -m bot.scripts.collect_results --exclude-rr-5verst-s95  # без RR, 5верст, S95
"""
import argparse
import asyncio
import logging
import sys
import tempfile
from pathlib import Path

import aiohttp

# Путь к корню
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bot.db import db
from bot.scripts.parse_protocol import ProtocolImporter

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


async def download_file(url: str) -> Path | None:
    """Скачать файл во временную директорию"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status != 200:
                    logger.warning(f"Ошибка загрузки {url}: HTTP {resp.status}")
                    return None
                content = await resp.read()
                ext = ".pdf"
                if ".xls" in url.lower():
                    ext = ".xlsx"
                elif url.lower().endswith(".xls"):
                    ext = ".xls"
                with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                    f.write(content)
                    return Path(f.name)
    except Exception as e:
        logger.warning(f"Ошибка загрузки {url}: {e}")
        return None


def _is_downloadable_protocol(url: str) -> bool:
    """Проверяет, ведёт ли URL на PDF/Excel (а не HTML-страницу)"""
    u = url.lower()
    if u.endswith(".pdf") or u.endswith(".xlsx") or u.endswith(".xls"):
        return True
    if ".pdf" in u or ".xls" in u:
        return True
    return False


# Источники для исключения (--exclude-rr-5verst-s95)
EXCLUDE_URL_PATTERNS = (
    "results.russiarunning.com",
    "russiarunning.com",
    "5verst.ru",
    "5verst",
    "s95.ru",
    "s95",
)
EXCLUDE_ORGANIZERS = ("RussiaRunning", "5верст", "5верст.", "S95", "s95")


def _is_excluded(race: dict, exclude_patterns: tuple) -> bool:
    """Проверка: исключён ли забег по URL или организатору"""
    url = ((race.get("protocol_url") or "") + (race.get("website_url") or "")).lower()
    org = (race.get("organizer") or "").lower()
    for p in exclude_patterns:
        if p.lower() in url:
            return True
    for o in EXCLUDE_ORGANIZERS:
        if o.lower() in org:
            return True
    return False


async def run_collect(
    exclude_rr_5verst_s95: bool = False,
    max_races: int = 2000,
    runc_limit: int = 200,
    raceresult_limit: int = 100,
    rr_limit: int = 100,
    date_to: str | None = None,
):
    """Основная логика сбора (db должна быть подключена).
    exclude_rr_5verst_s95: исключить RussiaRunning, 5верст, S95
    max_races: макс. забегов за прогон
    date_to: только забеги до этой даты (YYYY-MM-DD), для приоритета старого
    """
    where = "date < date('now') AND protocol_url IS NOT NULL AND protocol_url != ''"
    params = []
    if date_to:
        where += " AND date <= ?"
        params.append(date_to)
    sql = f"""
        SELECT id, name, date, location, organizer, race_type, protocol_url, website_url
        FROM races
        WHERE {where}
        ORDER BY date DESC
        LIMIT {max_races}
    """
    async with db.db.execute(sql, params) as cursor:
        all_races = [dict(row) for row in await cursor.fetchall()]

    if exclude_rr_5verst_s95:
        races = [r for r in all_races if not _is_excluded(r, EXCLUDE_URL_PATTERNS)]
        logger.info(f"После исключения RR/5верст/S95: {len(races)} забегов из {len(all_races)}")
    else:
        races = all_races

    if not races:
        logger.info("Нет забегов с URL протоколов в БД.")
        return

    downloadable = [r for r in races if _is_downloadable_protocol(r.get("protocol_url", ""))]
    rr_races = [r for r in races if "results.russiarunning.com" in (r.get("protocol_url") or "")]
    runc_races = [r for r in races if "results.runc.run" in (r.get("protocol_url") or "")]
    raceresult_races = [r for r in races if "my.raceresult.com" in (r.get("protocol_url") or "")]
    if not downloadable and not rr_races and not runc_races and not raceresult_races:
        logger.info(
            f"Найдено {len(races)} забегов с protocol_url, но нет PDF/Excel и не RussiaRunning."
        )
        return

    importer = ProtocolImporter()
    rr_processed = 0
    runc_processed = 0
    raceresult_processed = 0

    for race in races:
        url = race.get("protocol_url", "").strip()
        if not url:
            continue
        if not _is_downloadable_protocol(url) and "results.russiarunning.com" not in url and "results.runc.run" not in url and "my.raceresult.com" not in url:
            continue
        logger.info(f"Обработка: {race['name']} ({race['date']})")

        # RussiaRunning — пропускаем если exclude
        if "results.russiarunning.com" in url and exclude_rr_5verst_s95:
            continue
        if "results.russiarunning.com" in url:
            if rr_processed >= rr_limit:
                logger.info(f"  Пропуск RR (лимит {rr_limit})")
                continue
            try:
                from bot.scripts.rr_results_parser import fetch_rr_results
                raw_data = await fetch_rr_results(url)
                if raw_data:
                    await importer.import_from_raw_data(
                        raw_data=raw_data,
                        race_name=race["name"],
                        race_date=race["date"],
                        race_location=race.get("location", ""),
                        race_organizer=race.get("organizer", "RussiaRunning"),
                        race_type=race.get("race_type", "шоссе"),
                        distance="",
                        website_url=race.get("website_url", ""),
                        protocol_url=url,
                    )
                else:
                    logger.warning(f"  Не удалось извлечь результаты")
            except ImportError as e:
                logger.warning(f"  Playwright не установлен: pip install playwright && playwright install chromium")
            except Exception as e:
                logger.warning(f"  Ошибка RR parser: {e}")
            rr_processed += 1
            continue

        # RunC (results.runc.run) — парсим через Playwright
        if "results.runc.run" in url:
            if runc_processed >= runc_limit:
                logger.info(f"  Пропуск RunC (достигнут лимит {runc_limit})")
                continue
            try:
                from bot.scripts.runc_results_parser import fetch_runc_results
                raw_data = await fetch_runc_results(url)
                if raw_data:
                    await importer.import_from_raw_data(
                        raw_data=raw_data,
                        race_name=race["name"],
                        race_date=race["date"],
                        race_location=race.get("location", ""),
                        race_organizer=race.get("organizer", "Беговое сообщество"),
                        race_type=race.get("race_type", "шоссе"),
                        distance="",
                        website_url=race.get("website_url", ""),
                        protocol_url=url,
                    )
                else:
                    logger.warning(f"  Не удалось извлечь результаты RunC")
            except ImportError as e:
                logger.warning(f"  Playwright не установлен: pip install playwright && playwright install chromium")
            except Exception as e:
                logger.warning(f"  Ошибка RunC parser: {e}")
            runc_processed += 1
            continue

        # RaceResult (my.raceresult.com) — парсим через Playwright
        if "my.raceresult.com" in url:
            if raceresult_processed >= raceresult_limit:
                logger.info(f"  Пропуск RaceResult (лимит {raceresult_limit})")
                continue
            try:
                from bot.scripts.raceresult_parser import fetch_raceresult_results
                raw_data = await fetch_raceresult_results(url)
                if raw_data:
                    await importer.import_from_raw_data(
                        raw_data=raw_data,
                        race_name=race["name"],
                        race_date=race["date"],
                        race_location=race.get("location", ""),
                        race_organizer=race.get("organizer", "RaceResult"),
                        race_type=race.get("race_type", "шоссе"),
                        distance="",
                        website_url=race.get("website_url", ""),
                        protocol_url=url,
                    )
                else:
                    logger.warning(f"  Не удалось извлечь результаты RaceResult")
            except ImportError as e:
                logger.warning(f"  Playwright не установлен: pip install playwright && playwright install chromium")
            except Exception as e:
                logger.warning(f"  Ошибка RaceResult parser: {e}")
            raceresult_processed += 1
            continue

        path = await download_file(url)
        if not path:
            logger.warning(f"  Пропуск (не удалось скачать)")
            continue
        try:
            await importer.import_protocol(
                file_path=str(path),
                race_name=race["name"],
                race_date=race["date"],
                race_location=race.get("location", ""),
                race_organizer=race.get("organizer", ""),
                race_type=race.get("race_type", "шоссе"),
                distance="",
                website_url=race.get("website_url", ""),
                protocol_url=url,
            )
        except Exception as e:
            logger.warning(f"  Ошибка импорта: {e}")
        finally:
            path.unlink(missing_ok=True)

    logger.info(
        f"Итог: создано забегов {importer.stats['races_created']}, "
        f"результатов {importer.stats['results_added']}, "
        f"ошибок {importer.stats['errors']}"
    )


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exclude-rr-5verst-s95", action="store_true",
                        help="Исключить RussiaRunning, 5верст, S95")
    parser.add_argument("--max-races", type=int, default=2000,
                        help="Макс. забегов за прогон (default: 2000)")
    parser.add_argument("--runc-limit", type=int, default=200,
                        help="Лимит RunC за прогон (default: 200)")
    parser.add_argument("--raceresult-limit", type=int, default=100,
                        help="Лимит RaceResult за прогон (default: 100)")
    parser.add_argument("--rr-limit", type=int, default=100,
                        help="Лимит RussiaRunning за прогон при включённом RR (default: 100)")
    parser.add_argument("--date-to", type=str,
                        help="Только забеги до даты (YYYY-MM-DD), например 2024-01-01 для 2023")
    parser.add_argument("--loop", type=int, default=1,
                        help="Запустить N раз подряд (для долгого сбора)")
    args = parser.parse_args()
    await db.connect()
    for i in range(args.loop):
        if args.loop > 1:
            logger.info(f"=== Прогон {i + 1}/{args.loop} ===")
        await run_collect(
            exclude_rr_5verst_s95=args.exclude_rr_5verst_s95,
            max_races=args.max_races,
            runc_limit=args.runc_limit,
            raceresult_limit=args.raceresult_limit,
            rr_limit=args.rr_limit,
            date_to=args.date_to,
        )
        if i < args.loop - 1:
            import time
            time.sleep(5)  # пауза между прогонами
    await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
