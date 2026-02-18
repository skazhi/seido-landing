# Seido Bot - Telegram-бот для сбора беговой статистики

## Структура

```
bot/
├── main.py             # Точка входа
├── db.py               # Работа с базой данных
├── handlers.py         # Обработчики команд
├── config.py           # Конфигурация
├── requirements.txt    # Зависимости
└── schema.sql          # Схема БД
```

## Установка

1. Создать виртуальное окружение:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

2. Установить зависимости:
```bash
pip install -r requirements.txt
```

3. Создать файл `.env` с переменными:
```
BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=postgresql://user:password@localhost:5432/seido
```

4. Запустить бота:
```bash
python main.py
```

## Команды бота

- `/start` - Приветствие и регистрация
- `/myresults` - Мои результаты
- `/stats` - Общая статистика
- `/compare` - Сравнение с другим бегуном
- `/addrace` - Предложить забег
- `/help` - Справка
