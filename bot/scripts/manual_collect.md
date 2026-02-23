# Сбор протоколов забегов вручную

## Популярные источники протоколов

### 1. 5верст (5verst.ru)
- Сайт: https://5verst.ru/results
- Формат: PDF, Excel
- Как найти: Раздел "Результаты" → выбираешь забег → скачиваешь протокол

### 2. RHR (Run Hide Repeat)
- Сайт: https://rhr-marathon.ru/results
- Формат: PDF, Excel
- Как найти: Раздел "Результаты" → протоколы по забегам

### 3. S95 (Sport-95)
- Сайт: https://s95.run/results
- Формат: PDF, Excel

### 4. Московский марафон
- Сайт: https://moscowmarathon.ru/results
- Формат: PDF, Excel

### 5. RussiaRunning
- Сайт: https://russiarunning.com
- Формат: Онлайн-протоколы (нужен парсинг)

## Что делать

1. Заходи на сайт организатора
2. Находи раздел "Результаты" или "Протоколы"
3. Скачивай протоколы (PDF или Excel)
4. Сохраняй в `bot/protocols/` с понятным названием:
   - `5verst_pjaterka_2026-02-22.pdf`
   - `rhr_marathon_2026-01-15.xlsx`

## После сбора

Импортируй через:
```bash
cd bot/scripts
python add_races_and_results.py
# Выбрать: 3. Добавить результаты из протокола
```
