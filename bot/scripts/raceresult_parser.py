#!/usr/bin/env python3
"""
Seido - Парсер результатов RaceResult (my.raceresult.com)
Использует Playwright для загрузки страницы и извлечения результатов.
"""
import asyncio
import logging
import re
from typing import List, Dict

logger = logging.getLogger(__name__)

# Импорт из rr_results_parser
from bot.scripts.rr_results_parser import (
    _is_valid_runner_row,
    _extract_table_rows,
    _extract_div_row,
    _map_header,
    _normalize_row,
    _parse_embedded_json,
)


def _extract_event_id(url: str) -> str | None:
    """Извлечь event ID из URL my.raceresult.com/372673/ или /372673/results"""
    m = re.search(r'my\.raceresult\.com/(\d+)', url, re.I)
    return m.group(1) if m else None


async def fetch_raceresult_results(protocol_url: str, timeout: int = 60000) -> List[Dict]:
    """
    Загрузить страницу результатов RaceResult и извлечь данные.

    Args:
        protocol_url: URL вида https://my.raceresult.com/372673/ или .../372673/results
        timeout: таймаут в мс

    Returns:
        Список словарей с полями: name, time, place, distance, city, gender, birth_date, ...
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("Установите playwright: pip install playwright && playwright install chromium")
        return []

    # Нормализуем URL — добавляем /results если нужно
    event_id = _extract_event_id(protocol_url)
    if not event_id:
        logger.warning(f"Не удалось извлечь event ID из {protocol_url}")
        return []
    base_url = f"https://my.raceresult.com/{event_id}/"
    results_url = f"https://my.raceresult.com/{event_id}/results" if "/results" not in protocol_url else protocol_url

    results: List[Dict] = []
    captured_json: List[str] = []

    async def capture_response(response):
        try:
            url = response.url.lower()
            if "raceresult" in url and ("result" in url or "participant" in url or "api" in url):
                ct = response.headers.get("content-type") or ""
                if "json" in ct:
                    body = await response.text()
                    if body and len(body) > 50 and ("name" in body or "Firstname" in body or "Lastname" in body):
                        captured_json.append(body)
        except Exception:
            pass

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        try:
            page = await browser.new_page()
            page.on("response", capture_response)
            await page.goto(results_url, wait_until="domcontentloaded", timeout=timeout)
            await asyncio.sleep(5)

            # Пробуем захваченный JSON
            for body in captured_json:
                rows = _parse_raceresult_json(body)
                if rows:
                    results.extend(rows)
                    break

            if results:
                await browser.close()
                return [r for r in results if r and _is_valid_runner_row(r)]

            # Альтернатива: таблица в DOM
            await asyncio.sleep(2)
            tables = await page.query_selector_all("table")
            for table in tables:
                rows = await _extract_table_rows(table)
                if len(rows) >= 3:
                    results.extend(rows)
                    break

            if not results:
                # RaceResult часто рендерит в div с классом rr...
                rows_sel = await page.query_selector_all(
                    "table tbody tr, [class*='ResultList'] tr, [class*='result'] tr"
                )
                for tr in rows_sel[:500]:
                    cells = await tr.query_selector_all("td")
                    if len(cells) >= 2:
                        texts = []
                        for c in cells:
                            t = await c.text_content()
                            texts.append((t or "").strip())
                        # Обычно: место, время, ФИО или ФИО, время, место
                        row = _parse_raceresult_row(texts)
                        if row:
                            results.append(row)

        except Exception as e:
            logger.warning(f"Ошибка Playwright RaceResult {protocol_url}: {e}")
        finally:
            await browser.close()

    return [r for r in results if r and _is_valid_runner_row(r)]


def _parse_raceresult_row(texts: List[str]) -> Dict | None:
    """Парсинг строки таблицы RaceResult"""
    if not texts:
        return None
    row = {}
    for i, t in enumerate(texts):
        if not t:
            continue
        if t.isdigit() and not row.get("place"):
            row["place"] = t
        elif re.match(r"^\d{1,2}:\d{2}(:\d{2})?(\.\d+)?$", t) or re.match(r"^\d+h\s*\d+m", t, re.I):
            row["time"] = t
        elif any(c.isalpha() for c in t) and len(t) > 3 and "категор" not in t.lower():
            if not row.get("name"):
                row["name"] = t
    if row.get("name"):
        return _normalize_row(row)
    return None


def _parse_raceresult_json(json_str: str) -> List[Dict]:
    """Парсинг JSON RaceResult API"""
    import json
    rows = []
    try:
        data = json.loads(json_str)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    r = _raceresult_dict_to_row(item)
                    if r:
                        rows.append(r)
        elif isinstance(data, dict):
            for key in ("data", "results", "Participants", "participants", "rows"):
                arr = data.get(key)
                if isinstance(arr, list):
                    for item in arr:
                        if isinstance(item, dict):
                            r = _raceresult_dict_to_row(item)
                            if r:
                                rows.append(r)
                    if rows:
                        break
            if not rows and isinstance(data, dict):
                for v in data.values():
                    if isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict):
                                r = _raceresult_dict_to_row(item)
                                if r:
                                    rows.append(r)
    except Exception:
        pass
    return rows


def _raceresult_dict_to_row(d: Dict) -> Dict | None:
    """Преобразование dict RaceResult в row"""
    first = d.get("Firstname") or d.get("firstname") or d.get("FirstName") or ""
    last = d.get("Lastname") or d.get("lastname") or d.get("LastName") or ""
    name = d.get("Name") or d.get("name") or f"{last} {first}".strip() or f"{first} {last}".strip()
    if not name or len(name) < 4:
        return None
    return _normalize_row({
        "name": str(name),
        "place": str(d.get("Rank") or d.get("Place") or d.get("Pos") or d.get("rank") or ""),
        "time": str(d.get("Time") or d.get("time") or d.get("Finish") or d.get("NetTime") or ""),
        "distance": str(d.get("Distance") or d.get("distance") or d.get("Race") or ""),
        "city": str(d.get("City") or d.get("city") or d.get("Location") or ""),
        "gender": str(d.get("Sex") or d.get("Gender") or d.get("sex") or ""),
        "birth_date": str(d.get("Birthyear") or d.get("BirthYear") or d.get("YoB") or ""),
    })
