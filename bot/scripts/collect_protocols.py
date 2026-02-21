"""
Seido - Сбор протоколов забегов
Автоматический поиск и скачивание протоколов с сайтов организаторов.
Список организаторов: docs/ORGANIZERS.md
"""
import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from datetime import datetime, timedelta, date
import re
from bs4 import BeautifulSoup

PROTOCOLS_DIR = Path(__file__).parent.parent / "protocols"
PROTOCOLS_DIR.mkdir(exist_ok=True)

# Фильтр года для сбора (2026 — текущий приоритет)
RESULTS_YEAR = 2026


def _safe_filename(name: str) -> str:
    """Безопасное имя файла"""
    return re.sub(r'[^\w\s\-\.]', '_', name)[:200]


async def download_file(url: str, filepath: Path):
    """Скачать файл по URL"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    async with aiofiles.open(filepath, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                    return True
    except Exception as e:
        print(f"Ошибка скачивания {url}: {e}")
    return False


async def find_5verst_protocols():
    """Поиск протоколов на 5verst.ru"""
    print("🔍 Поиск протоколов на 5verst.ru...")
    
    base_url = "https://5verst.ru"
    protocols = []
    
    try:
        async with aiohttp.ClientSession() as session:
            # Ищем страницу с результатами
            async with session.get(f"{base_url}/results") as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Ищем ссылки на протоколы (PDF, Excel)
                    links = soup.find_all('a', href=re.compile(r'\.(pdf|xlsx|xls)$', re.I))
                    for link in links[:10]:  # Первые 10
                        url = link.get('href')
                        if not url.startswith('http'):
                            url = f"{base_url}{url}"
                        protocols.append({
                            'url': url,
                            'name': link.text.strip() or url.split('/')[-1],
                            'source': '5verst'
                        })
    except Exception as e:
        print(f"Ошибка поиска на 5verst: {e}")
    
    return protocols


async def find_rhr_protocols():
    """Поиск протоколов на rhr-marathon.ru"""
    print("🔍 Поиск протоколов на rhr-marathon.ru...")
    
    base_url = "https://rhr-marathon.ru"
    protocols = []
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/results") as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    links = soup.find_all('a', href=re.compile(r'\.(pdf|xlsx|xls)$', re.I))
                    for link in links[:20]:
                        url = link.get('href')
                        if not url.startswith('http'):
                            url = base_url + (url if url.startswith('/') else '/' + url)
                        name = link.text.strip() or url.split('/')[-1]
                        if str(RESULTS_YEAR) in name or str(RESULTS_YEAR) in url:
                            protocols.append({
                                'url': url,
                                'name': name,
                                'source': 'RHR',
                                'year': RESULTS_YEAR
                            })
                    if not protocols and links:
                        for link in links[:20]:
                            url = link.get('href')
                            if not url.startswith('http'):
                                url = base_url + (url if url.startswith('/') else '/' + url)
                            protocols.append({
                                'url': url,
                                'name': (link.text.strip() or url.split('/')[-1]),
                                'source': 'RHR'
                            })
    except Exception as e:
        print(f"Ошибка поиска на RHR: {e}")
    
    return protocols


async def find_s95_protocols():
    """Поиск протоколов/результатов на s95.ru"""
    print("🔍 Поиск результатов на s95.ru...")
    
    base_url = "https://s95.ru"
    protocols = []
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/activities") as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    links = soup.find_all('a', href=re.compile(r'\.(pdf|xlsx|xls)$', re.I))
                    for link in links[:15]:
                        url = link.get('href')
                        if not url.startswith('http'):
                            url = base_url + (url if url.startswith('/') else '/' + url)
                        protocols.append({
                            'url': url,
                            'name': (link.text.strip() or url.split('/')[-1]),
                            'source': 'S95'
                        })
    except Exception as e:
        print(f"Ошибка поиска на S95: {e}")
    
    return protocols


async def find_russiarunning_protocols():
    """
    Получает список забегов RussiaRunning за 2026 через API.
    Протоколы могут быть на страницах событий.
    """
    print("🔍 Поиск забегов RussiaRunning (2026)...")
    
    api_url = "https://russiarunning.com/api/events/list/ru"
    events = []
    
    try:
        payload = {
            "Take": 500,
            "DateFrom": f"{RESULTS_YEAR}-01-01",
            "DateTo": f"{RESULTS_YEAR}-12-31"
        }
        headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data.get("Items", []):
                        event_date = item.get("d", "").split("T")[0]
                        if str(RESULTS_YEAR) in event_date:
                            event_id = item.get("c", "")
                            events.append({
                                'url': f"https://russiarunning.com/event/{event_id}/",
                                'name': f"russiarunning_{item.get('t', 'event')}_{event_date}",
                                'source': 'RussiaRunning',
                                'event_id': event_id,
                                'event_date': event_date
                            })
        print(f"   Найдено событий 2026: {len(events)}")
    except Exception as e:
        print(f"Ошибка RussiaRunning API: {e}")
    
    return events


async def collect_protocols(year: int = None):
    """
    Собрать протоколы со всех источников.
    year: фильтр года (по умолчанию RESULTS_YEAR=2026)
    """
    year = year or RESULTS_YEAR
    print("=" * 60)
    print(f"📥 СБОР ПРОТОКОЛОВ ЗАБЕГОВ (приоритет {year})")
    print("=" * 60)
    
    all_protocols = []
    
    # Организаторы из docs/ORGANIZERS.md
    all_protocols.extend(await find_5verst_protocols())
    all_protocols.extend(await find_rhr_protocols())
    all_protocols.extend(await find_s95_protocols())
    
    # RussiaRunning — список событий 2026 (для дальнейшего сбора протоколов)
    rr_events = await find_russiarunning_protocols()
    all_protocols.extend(rr_events)
    
    print(f"\n✅ Найдено протоколов/событий: {len(all_protocols)}")
    
    # Скачиваем только файлы (PDF, Excel)
    downloaded = 0
    event_urls = {}  # source -> [(name, url), ...]
    
    for proto in all_protocols:
        url = proto['url']
        name = proto.get('name', '') or url.split('/')[-1].split('?')[0]
        
        if re.search(r'\.(pdf|xlsx|xls)$', url, re.I):
            if not name.endswith(('.pdf', '.xlsx', '.xls')):
                name = name + ('.pdf' if '.pdf' in url.lower() else '.xlsx')
            filepath = PROTOCOLS_DIR / _safe_filename(name)
            if filepath.exists():
                print(f"⏭ Пропущен (уже есть): {name}")
                continue
            print(f"⬇ Скачиваю: {name}...")
            if await download_file(url, filepath):
                print(f"✅ Скачан: {name}")
                downloaded += 1
            else:
                print(f"❌ Ошибка: {name}")
        else:
            # URL без файла (страница события) — сохраняем для ручной проверки
            src = proto.get('source', 'other')
            event_urls.setdefault(src, []).append((name, url))
    
    for src, items in event_urls.items():
        list_file = PROTOCOLS_DIR / f"urls_{src}_{year}.txt"
        with open(list_file, 'w', encoding='utf-8') as f:
            for n, u in items:
                f.write(f"{n}\t{u}\n")
        print(f"📋 Сохранено {len(items)} ссылок: {list_file.name}")
    
    print(f"\n✅ Скачано новых протоколов: {downloaded}")
    print(f"📁 Папка: {PROTOCOLS_DIR}")
    
    return downloaded


async def main():
    await collect_protocols()


if __name__ == "__main__":
    asyncio.run(main())
