#!/usr/bin/env python3
"""
Seido - Парсер результатов RunC (results.runc.run)
Беговое сообщество / Moscow Marathon, Moscow Half и др.
Использует Playwright (как rr_results_parser).
"""
import asyncio
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

# Импорт функций из rr_results_parser — одинаковая структура SPA
from bot.scripts.rr_results_parser import (
    _extract_table_rows,
    _extract_div_row,
    _parse_embedded_json,
    _is_valid_runner_row,
)


async def fetch_runc_results(protocol_url: str, timeout: int = 30000) -> List[Dict]:
    """
    Загрузить страницу результатов RunC и извлечь данные.

    Args:
        protocol_url: URL вида https://results.runc.run/event/{slug}/overview/
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
            url = response.url.lower()
            if "api" in url or "result" in url or "event" in url or response.request.resource_type == "xhr":
                ct = response.headers.get("content-type") or ""
                if "json" in ct:
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

            for body in captured_json:
                rows = _parse_embedded_json(body)
                if rows:
                    results.extend(rows)
                    break
            if results:
                await browser.close()
                return [r for r in results if r and _is_valid_runner_row(r)]

            try:
                await page.wait_for_selector(
                    "table, [class*='result'], [class*='table'], [class*='row'], [class*='participant']",
                    timeout=10000
                )
            except Exception:
                pass
            await asyncio.sleep(1)

            tables = await page.query_selector_all("table")
            for table in tables:
                rows = await _extract_table_rows(table)
                if rows:
                    results.extend(rows)
                    break

            if not results:
                rows_sel = await page.query_selector_all(
                    "[class*='row']:not(thead *), [class*='result-row'], [class*='participant']"
                )
                for el in rows_sel[:500]:
                    row = await _extract_div_row(el)
                    if row:
                        results.append(row)

            if not results:
                json_data = await page.evaluate("""
                    () => {
                        if (window.__NUXT__) return JSON.stringify(window.__NUXT__);
                        if (window.__INITIAL_STATE__) return JSON.stringify(window.__INITIAL_STATE__);
                        for (const k of Object.keys(window)) {
                            if (k.includes('__') && typeof window[k] === 'object') {
                                try {
                                    const s = JSON.stringify(window[k]);
                                    if (s && s.includes('participant') && s.includes('result')) return s;
                                } catch (_) {}
                            }
                        }
                        return null;
                    }
                """)
                if json_data:
                    rows = _parse_embedded_json(json_data)
                    results.extend(rows)

        except Exception as e:
            logger.warning(f"Ошибка Playwright для RunC {protocol_url}: {e}")
        finally:
            await browser.close()

    return [r for r in results if r and _is_valid_runner_row(r)]
