"""
Seido - Работа с базой данных (SQLite)
"""
import aiosqlite
from typing import Optional, List, Dict, Any
from datetime import date
import os
import sys

# Исправление кодировки для Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = os.path.join(os.path.dirname(__file__), "seido.db")


class Database:
    def __init__(self):
        self.db: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Подключение к базе данных"""
        self.db = await aiosqlite.connect(DB_PATH)
        self.db.row_factory = aiosqlite.Row
        await self.init_db()
        print("[OK] Подключение к базе данных установлено")

    async def disconnect(self):
        """Отключение от базы данных"""
        if self.db:
            await self.db.close()
            print("[OK] Подключение к базе данных закрыто")

    async def init_db(self):
        """Инициализация таблиц"""
        await self.db.executescript("""
        -- Бегуны (runners)
        CREATE TABLE IF NOT EXISTS runners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            middle_name TEXT,
            birth_date TEXT,
            gender TEXT CHECK (gender IN ('M', 'F')),
            city TEXT,
            country TEXT DEFAULT 'Россия',
            club_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Забеги (races)
        CREATE TABLE IF NOT EXISTS races (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            date TEXT NOT NULL,
            location TEXT,
            organizer TEXT,
            race_type TEXT,
            distances TEXT,
            website_url TEXT,
            protocol_url TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Результаты (results)
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            runner_id INTEGER NOT NULL REFERENCES runners(id) ON DELETE CASCADE,
            race_id INTEGER NOT NULL REFERENCES races(id) ON DELETE CASCADE,
            distance TEXT NOT NULL,
            finish_time TEXT,
            finish_time_seconds INTEGER,
            pace TEXT,
            pace_seconds_per_km INTEGER,
            overall_place INTEGER,
            gender_place INTEGER,
            age_group TEXT,
            age_group_place INTEGER,
            club_place INTEGER,
            total_runners INTEGER,
            points INTEGER,
            is_official INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(runner_id, race_id, distance)
        );

        -- Заявки на добавление забегов (race_submissions)
        CREATE TABLE IF NOT EXISTS race_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submitted_by INTEGER,
            race_name TEXT NOT NULL,
            race_date TEXT,
            protocol_url TEXT,
            file_path TEXT,
            status TEXT DEFAULT 'pending',
            admin_comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TIMESTAMP
        );

        -- Подписки на забеги (race_subscriptions)
        CREATE TABLE IF NOT EXISTS race_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            runner_id INTEGER NOT NULL REFERENCES runners(id) ON DELETE CASCADE,
            race_id INTEGER NOT NULL REFERENCES races(id) ON DELETE CASCADE,
            status TEXT DEFAULT 'planning',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(runner_id, race_id)
        );

        -- Индексы
        CREATE INDEX IF NOT EXISTS idx_runners_last_name ON runners(last_name);
        CREATE INDEX IF NOT EXISTS idx_runners_telegram ON runners(telegram_id);
        CREATE INDEX IF NOT EXISTS idx_races_date ON races(date);
        CREATE INDEX IF NOT EXISTS idx_results_runner ON results(runner_id);
        CREATE INDEX IF NOT EXISTS idx_results_race ON results(race_id);
        """)
        await self.db.commit()

    # ============================================
    # БЕГУНЫ (RUNNERS)
    # ============================================

    async def get_runner_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """Получить бегуна по Telegram ID"""
        async with self.db.execute(
            "SELECT * FROM runners WHERE telegram_id = ?",
            (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_runner_by_name(
        self,
        last_name: str,
        first_name: str,
        birth_date: Optional[str] = None
    ) -> Optional[Dict]:
        """Найти бегуна по имени и фамилии"""
        if birth_date:
            async with self.db.execute(
                "SELECT * FROM runners WHERE last_name = ? AND first_name = ? AND birth_date = ?",
                (last_name, first_name, birth_date)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
        else:
            async with self.db.execute(
                "SELECT * FROM runners WHERE last_name = ? AND first_name = ?",
                (last_name, first_name)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def create_runner(
        self,
        telegram_id: int,
        first_name: str,
        last_name: str,
        birth_date: Optional[str] = None,
        gender: Optional[str] = None,
        city: Optional[str] = None,
    ) -> int:
        """Создать нового бегуна"""
        cursor = await self.db.execute(
            """
            INSERT INTO runners (telegram_id, first_name, last_name, birth_date, gender, city)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (telegram_id, first_name, last_name, birth_date, gender, city)
        )
        await self.db.commit()
        return cursor.lastrowid

    async def update_runner(self, telegram_id: int, **kwargs) -> bool:
        """Обновить данные бегуна"""
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [telegram_id]

        await self.db.execute(
            f"""
            UPDATE runners
            SET {set_clause}, updated_at = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
            """,
            values
        )
        await self.db.commit()
        return True

    # ============================================
    # ЗАБЕГИ (RACES)
    # ============================================

    async def get_upcoming_races(self, limit: int = 10) -> List[Dict]:
        """Получить предстоящие забеги"""
        async with self.db.execute(
            """
            SELECT * FROM races
            WHERE date >= date('now') AND is_active = 1
            ORDER BY date ASC
            LIMIT ?
            """,
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_race_by_id(self, race_id: int) -> Optional[Dict]:
        """Получить забег по ID"""
        async with self.db.execute(
            "SELECT * FROM races WHERE id = ?",
            (race_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def search_races(self, query: str, limit: int = 10) -> List[Dict]:
        """Поиск забегов по названию"""
        async with self.db.execute(
            """
            SELECT * FROM races
            WHERE name LIKE ? OR organizer LIKE ?
            ORDER BY date DESC
            LIMIT ?
            """,
            (f"%{query}%", f"%{query}%", limit)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_race_by_url(self, url: str) -> Optional[Dict]:
        """Получить забег по URL (для проверки на дубликат)"""
        if not url:
            return None
        async with self.db.execute(
            "SELECT * FROM races WHERE website_url = ?",
            (url,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def add_race(
        self,
        name: str,
        date: str,
        location: str = '',
        organizer: str = '',
        race_type: str = 'шоссе',
        distances: str = '[]',
        website_url: str = '',
        protocol_url: str = '',
        source: str = '',
    ) -> int:
        """Добавить новый забег"""
        cursor = await self.db.execute(
            """
            INSERT INTO races 
            (name, date, location, organizer, race_type, distances, website_url, protocol_url, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (name, date, location, organizer, race_type, distances, website_url, protocol_url)
        )
        await self.db.commit()
        return cursor.lastrowid

    # ============================================
    # РЕЗУЛЬТАТЫ (RESULTS)
    # ============================================

    async def get_runner_results(self, runner_id: int) -> List[Dict]:
        """Получить все результаты бегуна"""
        async with self.db.execute(
            """
            SELECT
                r.*,
                rac.name as race_name,
                rac.date as race_date,
                rac.organizer
            FROM results r
            JOIN races rac ON r.race_id = rac.id
            WHERE r.runner_id = ?
            ORDER BY rac.date DESC, r.distance
            """,
            (runner_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_best_result(
        self,
        runner_id: int,
        distance: str
    ) -> Optional[Dict]:
        """Получить лучший результат на дистанции"""
        async with self.db.execute(
            """
            SELECT * FROM results
            WHERE runner_id = ? AND distance = ?
            ORDER BY finish_time_seconds ASC
            LIMIT 1
            """,
            (runner_id, distance)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_all_distances_for_runner(self, runner_id: int) -> List[str]:
        """Получить все дистанции, которые бежал бегун"""
        async with self.db.execute(
            "SELECT DISTINCT distance FROM results WHERE runner_id = ?",
            (runner_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row['distance'] for row in rows]

    async def add_result(
        self,
        runner_id: int,
        race_id: int,
        distance: str,
        finish_time_seconds: int,
        overall_place: Optional[int] = None,
        gender_place: Optional[int] = None,
        age_group_place: Optional[int] = None,
        total_runners: Optional[int] = None,
    ) -> int:
        """Добавить результат"""
        cursor = await self.db.execute(
            """
            INSERT INTO results (
                runner_id, race_id, distance, finish_time_seconds,
                overall_place, gender_place, age_group_place, total_runners
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (runner_id, race_id, distance) DO UPDATE SET
                finish_time_seconds = excluded.finish_time_seconds,
                overall_place = excluded.overall_place,
                gender_place = excluded.gender_place,
                age_group_place = excluded.age_group_place,
                total_runners = excluded.total_runners,
                updated_at = CURRENT_TIMESTAMP
            """,
            (runner_id, race_id, distance, finish_time_seconds,
             overall_place, gender_place, age_group_place, total_runners)
        )
        await self.db.commit()
        return cursor.lastrowid

    # ============================================
    # СТАТИСТИКА
    # ============================================

    async def get_total_runners(self) -> int:
        """Общее количество бегунов"""
        async with self.db.execute("SELECT COUNT(*) FROM runners") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_total_races(self) -> int:
        """Общее количество забегов"""
        async with self.db.execute("SELECT COUNT(*) FROM races") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_total_results(self) -> int:
        """Общее количество результатов"""
        async with self.db.execute("SELECT COUNT(*) FROM results") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_top_runners_by_results(self, limit: int = 10) -> List[Dict]:
        """Топ бегунов по количеству результатов"""
        async with self.db.execute(
            """
            SELECT
                r.last_name,
                r.first_name,
                r.city,
                COUNT(res.id) as results_count
            FROM runners r
            JOIN results res ON r.id = res.runner_id
            GROUP BY r.id
            ORDER BY results_count DESC
            LIMIT ?
            """,
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # ============================================
    # ПОДПИСКИ НА ЗАБЕГИ
    # ============================================

    async def subscribe_to_race(self, runner_id: int, race_id: int) -> bool:
        """Подписать бегуна на забег"""
        await self.db.execute(
            """
            INSERT INTO race_subscriptions (runner_id, race_id)
            VALUES (?, ?)
            ON CONFLICT (runner_id, race_id) DO NOTHING
            """,
            (runner_id, race_id)
        )
        await self.db.commit()
        return True

    async def get_runner_subscriptions(self, runner_id: int) -> List[Dict]:
        """Получить подписки бегуна"""
        async with self.db.execute(
            """
            SELECT rac.* FROM races rac
            JOIN race_subscriptions rs ON rac.id = rs.race_id
            WHERE rs.runner_id = ? AND rac.date >= date('now')
            ORDER BY rac.date ASC
            """,
            (runner_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # ============================================
    # ЗАЯВКИ НА ДОБАВЛЕНИЕ ЗАБЕГОВ
    # ============================================

    async def submit_race(
        self,
        submitted_by: int,
        race_name: str,
        race_date: Optional[str] = None,
        protocol_url: Optional[str] = None,
    ) -> int:
        """Создать заявку на добавление забега"""
        cursor = await self.db.execute(
            """
            INSERT INTO race_submissions
            (submitted_by, race_name, race_date, protocol_url)
            VALUES (?, ?, ?, ?)
            """,
            (submitted_by, race_name, race_date, protocol_url)
        )
        await self.db.commit()
        return cursor.lastrowid

    # ============================================
    # УДАЛЕНИЕ ДАННЫХ
    # ============================================

    async def delete_runner(self, runner_id: int) -> bool:
        """Удалить бегуна и все его данные"""
        # Удаляем результаты
        await self.db.execute(
            "DELETE FROM results WHERE runner_id = ?",
            (runner_id,)
        )
        
        # Удаляем подписки
        await self.db.execute(
            "DELETE FROM race_subscriptions WHERE runner_id = ?",
            (runner_id,)
        )
        
        # Удаляем профиль
        await self.db.execute(
            "DELETE FROM runners WHERE id = ?",
            (runner_id,)
        )
        
        await self.db.commit()
        return True


# Глобальный экземпляр
db = Database()
