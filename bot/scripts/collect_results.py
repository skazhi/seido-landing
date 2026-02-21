#!/usr/bin/env python3
"""
Seido - Сбор результатов с протоколов завершённых забегов
Загружает протоколы по URL из БД, парсит и импортирует с матчингом бегунов.
Запуск: python -m bot.scripts.collect_results
"""
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


async def run_collect():
    """Основная логика сбора (db должна быть подключена)"""
    async with db.db.execute(
        """
        SELECT id, name, date, location, organizer, race_type, protocol_url, website_url
        FROM races
        WHERE date < date('now') AND protocol_url IS NOT NULL AND protocol_url != ''
        ORDER BY date DESC
        LIMIT 100
        """
    ) as cursor:
        races = [dict(row) for row in await cursor.fetchall()]

    if not races:
        logger.info("Нет забегов с URL протоколов в БД.")
        return

    downloadable = [r for r in races if is_downloadable_protocol(r.get("protocol_url", ""))]
    if not downloadable:
        logger.info(
            f"Найдено {len(races)} забегов с protocol_url, но ни один не ведёт на PDF/Excel. "
            "HTML-страницы (например results.russiarunning.com) пока не парсятся."
        )
        return

    importer = ProtocolImporter()
    for race in races:
        url = race.get("protocol_url", "").strip()
        if not url:
            continue
        if not _is_downloadable_protocol(url):
            logger.debug(f"Пропуск (HTML, не PDF/Excel): {race['name']}")
            continue
        logger.info(f"Обработка: {race['name']} ({race['date']})")
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
    await db.connect()
    await run_collect()
    await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
