#!/usr/bin/env python3
"""
Seido - Парсер результатов RussiaRunning (results.russiarunning.com)
Использует Playwright для загрузки SPA и извлечения таблицы результатов.
"""
import asyncio
import logging
import re
from typing import List, Dict

logger = logging.getLogger(__name__)


def _is_valid_runner_row(r: Dict) -> bool:
    """Отсеивает строки-категории, заголовки и мусор"""
    name = (r.get("name") or "").strip()
    if not name or len(name) < 4:
        return False
    t = name.lower()
    skip = ("онлайн", "офлайн", "участие", "забег", "детский", "км.", "км ", "полумарафон",
            "марафон", "дистанц", "категор", "всего", "место", "фио", "итого", "dns", "dnf",
            "start", "finish", "старт", "финиш")
    if any(s in t for s in skip):
        return False
    if not any(c.isalpha() for c in name):
        return False
    return True


async def fetch_rr_results(protocol_url: str, timeout: int = 30000) -> List[Dict]:
    """
    Загрузить страницу результатов RussiaRunning и извлечь данные.

    Args:
        protocol_url: URL вида https://results.russiarunning.com/event/{id}
        timeout: таймаут в мс

    Returns:
        Список словарей с полями: name, time, place, distance, city, gender, birth_date, ...
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("Установите playwright: pip install playwright && playwright install chromium")
        return []

    results: List[Dict] = []
    captured_json: List[str] = []

    async def capture_response(response):
        try:
            if "api" in response.url or "result" in response.url.lower() or response.request.resource_type == "xhr":
                if "json" in (response.headers.get("content-type") or ""):
                    body = await response.text()
                    if body and ("name" in body or "participant" in body.lower() or "result" in body.lower()):
                        captured_json.append(body)
        except Exception:
            pass

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        try:
            page = await browser.new_page()
            page.on("response", capture_response)
            await page.goto(protocol_url, wait_until="domcontentloaded", timeout=timeout)
            await asyncio.sleep(3)

            # Сначала пробуем захваченный JSON
            for body in captured_json:
                rows = _parse_embedded_json(body)
                if rows:
                    results.extend(rows)
                    break
            if results:
                await browser.close()
                return results

            # Ждём появления контента
            try:
                await page.wait_for_selector(
                    "table, [class*='result'], [class*='table'], [class*='row'], [class*='participant'], div",
                    timeout=10000
                )
            except Exception:
                pass
            await asyncio.sleep(1)

            # Пробуем разные селекторы
            # 1. Таблица
            tables = await page.query_selector_all("table")
            for table in tables:
                rows = await _extract_table_rows(table)
                if rows:
                    results.extend(rows)
                    break

            # 2. Div-таблицы (CSS grid/flex)
            if not results:
                rows_sel = await page.query_selector_all(
                    "[class*='row']:not(thead *), [class*='result-row'], [class*='participant']"
                )
                for el in rows_sel[:500]:  # лимит
                    row = await _extract_div_row(el)
                    if row:
                        results.append(row)

            # 3. JSON в __NUXT__ или data
            if not results:
                json_data = await page.evaluate("""
                    () => {
                        if (window.__NUXT__) return JSON.stringify(window.__NUXT__);
                        if (window.__INITIAL_STATE__) return JSON.stringify(window.__INITIAL_STATE__);
                        const scripts = document.querySelectorAll('script[type="application/json"]');
                        for (const s of scripts) {
                            if (s.textContent && s.textContent.includes('result')) return s.textContent;
                        }
                        return null;
                    }
                """)
                if json_data:
                    rows = _parse_embedded_json(json_data)
                    results.extend(rows)

        except Exception as e:
            logger.warning(f"Ошибка Playwright для {protocol_url}: {e}")
        finally:
            await browser.close()

    # Отфильтровать мусор (категории, заголовки)
    return [r for r in results if r and _is_valid_runner_row(r)]


async def _extract_table_rows(table) -> List[Dict]:
    rows_data = []
    try:
        tbody = await table.query_selector("tbody") or table
        trs = await tbody.query_selector_all("tr")
        if not trs:
            trs = await table.query_selector_all("tr")

        # Заголовки
        header_cells = await (await table.query_selector("thead tr") or trs[0]).query_selector_all("th, td")
        headers = []
        for h in header_cells:
            t = await h.text_content()
            headers.append((t or "").strip().lower())

        for tr in trs[1:] if len(trs) > 1 else []:
            cells = await tr.query_selector_all("td")
            if not cells:
                continue
            row = {}
            for i, cell in enumerate(cells):
                text = (await cell.text_content() or "").strip()
                if i < len(headers) and headers[i]:
                    key = _map_header(headers[i])
                    if key:
                        row[key] = text
                else:
                    row[f"col_{i}"] = text
            if row.get("name") or row.get("full_name") or any("col_" in k and v for k, v in row.items()):
                rows_data.append(_normalize_row(row))
    except Exception as e:
        logger.debug(f"Ошибка извлечения таблицы: {e}")
    return rows_data


def _map_header(h: str) -> str | None:
    h = h.lower()
    if "место" in h or "place" in h or "позиц" in h or h == "#":
        return "place"
    if "фио" in h or "имя" in h or "name" in h or "участник" in h:
        return "name"
    if "время" in h or "time" in h or "финиш" in h:
        return "time"
    if "дистанц" in h or "distance" in h:
        return "distance"
    if "город" in h or "city" in h:
        return "city"
    if "пол" in h or "gender" in h or "м/ж" in h:
        return "gender"
    if "год" in h or "рожден" in h or "birth" in h or "возраст" in h:
        return "birth_date"
    if "клуб" in h or "club" in h:
        return "club"
    if "категор" in h or "группа" in h or "age" in h:
        return "age_group"
    return None


def _normalize_row(row: Dict) -> Dict:
    """Привести к формату normalize_protocol_row"""
    out = {}
    out["name"] = row.get("name") or row.get("full_name") or ""
    # Если name не задан — пробуем col_1 (часто: место, имя, время)
    if not out["name"]:
        for i in (1, 2, 0):
            c = row.get(f"col_{i}", "")
            if c and _is_valid_runner_row({"name": c}):
                out["name"] = c
                break
    out["place"] = row.get("place") or row.get("overall_place")
    out["time"] = row.get("time") or row.get("finish_time")
    out["distance"] = row.get("distance")
    out["city"] = row.get("city")
    out["gender"] = row.get("gender")
    out["birth_date"] = row.get("birth_date")
    out["club"] = row.get("club")
    out["age_group"] = row.get("age_group")
    out["gender_place"] = row.get("gender_place")
    out["age_group_place"] = row.get("age_group_place")
    return out


async def _extract_div_row(el) -> Dict | None:
    try:
        text = await el.text_content()
        if not text or len(text) < 5:
            return None
        # Простой парсинг: число время ФИО
        parts = text.split()
        if len(parts) >= 2:
            return _normalize_row({
                "place": parts[0] if parts[0].isdigit() else None,
                "time": parts[1] if ":" in parts[1] else None,
                "name": " ".join(parts[2:]) if len(parts) > 2 else None,
            })
    except Exception:
        pass
    return None


def _parse_embedded_json(json_str: str) -> List[Dict]:
    import json
    rows = []
    try:
        data = json.loads(json_str)

        def find_participants(obj):
            if isinstance(obj, list):
                for item in obj:
                    if isinstance(item, dict):
                        keys_lower = str(item).lower()
                        if any(k in keys_lower for k in ("firstname", "lastname", "fullname", "фио", "participant", "runner")):
                            r = _dict_to_row(item)
                            if r and _is_valid_runner_row(r):
                                rows.append(r)
                    else:
                        find_participants(item)
            elif isinstance(obj, dict):
                for v in obj.values():
                    find_participants(v)

        find_participants(data)
    except Exception as e:
        logger.debug(f"Ошибка парсинга JSON: {e}")
    return rows


def _dict_to_row(d: Dict) -> Dict:
    name = (d.get("name") or d.get("fullName") or d.get("фио")
            or f"{d.get('lastName', '')} {d.get('firstName', '')} {d.get('middleName', '')}".strip()
            or f"{d.get('last_name', '')} {d.get('first_name', '')}".strip())
    return _normalize_row({
        "name": str(name) if name else "",
        "place": str(d.get("place") or d.get("position") or d.get("overallPlace") or d.get("место") or ""),
        "time": str(d.get("time") or d.get("finishTime") or d.get("resultTime") or d.get("время") or ""),
        "distance": str(d.get("distance") or d.get("дистанция") or d.get("raceName") or ""),
        "city": str(d.get("city") or d.get("город") or d.get("location") or ""),
        "gender": str(d.get("gender") or d.get("пол") or d.get("sex") or ""),
        "birth_date": str(d.get("birthDate") or d.get("birthYear") or d.get("birth_date") or ""),
    })
