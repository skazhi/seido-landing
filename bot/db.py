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
        CREATE INDEX IF NOT EXISTS idx_races_organizer ON races(organizer);
        CREATE INDEX IF NOT EXISTS idx_results_runner ON results(runner_id);
        CREATE INDEX IF NOT EXISTS idx_results_race ON results(race_id);

        -- Организаторы (для будущей регистрации и привязки данных)
        -- См. docs/ORGANIZERS.md
        CREATE TABLE IF NOT EXISTS organizers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_name TEXT UNIQUE NOT NULL,
            display_name TEXT,
            website TEXT,
            contact_email TEXT,
            contact_telegram TEXT,
            seido_user_id INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_organizers_canonical ON organizers(canonical_name);

        -- Заявки на привязку результата («это я»)
        CREATE TABLE IF NOT EXISTS result_claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            result_id INTEGER NOT NULL REFERENCES results(id) ON DELETE CASCADE,
            runner_id INTEGER NOT NULL REFERENCES runners(id) ON DELETE CASCADE,
            telegram_id INTEGER,
            status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
            admin_comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TIMESTAMP,
            reviewed_by INTEGER,
            UNIQUE(result_id, runner_id)
        );
        CREATE INDEX IF NOT EXISTS idx_result_claims_status ON result_claims(status);

        -- Обратная связь от пользователей (feedback)
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            runner_id INTEGER REFERENCES runners(id) ON DELETE SET NULL,
            telegram_id INTEGER,
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        await self.db.commit()

        # Миграция: добавить organizer_id в races (если ещё нет)
        try:
            await self.db.execute(
                "ALTER TABLE races ADD COLUMN organizer_id INTEGER REFERENCES organizers(id)"
            )
            await self.db.commit()
        except Exception:
            pass

        # Миграция: Юнистар → Беговое сообщество (переименование организатора)
        try:
            await self.db.execute(
                "UPDATE races SET organizer = 'Беговое сообщество' WHERE organizer = 'Юнистар'"
            )
            await self.db.commit()
        except Exception:
            pass

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
        birth_date: Optional[str] = None,
        prefer_telegram: bool = True
    ) -> Optional[Dict]:
        """Найти бегуна по имени и фамилии. prefer_telegram: при нескольких — вернуть с telegram_id."""
        if birth_date:
            sql = "SELECT * FROM runners WHERE last_name = ? AND first_name = ? AND birth_date = ?"
            params = (last_name, first_name, birth_date)
        else:
            sql = "SELECT * FROM runners WHERE last_name = ? AND first_name = ?"
            params = (last_name, first_name)
        if prefer_telegram:
            sql += " ORDER BY CASE WHEN telegram_id IS NOT NULL THEN 0 ELSE 1 END"
        async with self.db.execute(sql, params) as cursor:
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
        middle_name: Optional[str] = None,
        club_name: Optional[str] = None,
    ) -> int:
        """Создать нового бегуна"""
        cursor = await self.db.execute(
            """
            INSERT INTO runners (telegram_id, first_name, last_name, middle_name, birth_date, gender, city, club_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (telegram_id, first_name, last_name, middle_name, birth_date, gender, city, club_name)
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
        """Получить предстоящие забеги (анонсы)"""
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
    
    async def get_past_races(self, limit: int = 20) -> List[Dict]:
        """Получить прошедшие забеги"""
        async with self.db.execute(
            """
            SELECT r.*, 
                   COUNT(res.id) as results_count
            FROM races r
            LEFT JOIN results res ON r.id = res.race_id
            WHERE r.date < date('now') AND r.is_active = 1
            GROUP BY r.id
            ORDER BY r.date DESC
            LIMIT ?
            """,
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_races_with_results(self, limit: int = 20) -> List[Dict]:
        """Получить забеги с результатами"""
        async with self.db.execute(
            """
            SELECT r.*, 
                   COUNT(res.id) as results_count
            FROM races r
            INNER JOIN results res ON r.id = res.race_id
            WHERE r.is_active = 1
            GROUP BY r.id
            HAVING results_count > 0
            ORDER BY r.date DESC
            LIMIT ?
            """,
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_race_status(self, race_id: int) -> Dict[str, any]:
        """
        Определить статус забега
        
        Returns:
            Словарь с полями:
            - status: 'upcoming', 'past', 'completed'
            - results_count: количество результатов
            - has_results: есть ли результаты
        """
        race = await self.get_race_by_id(race_id)
        if not race:
            return {'status': 'unknown', 'results_count': 0, 'has_results': False}
        
        from datetime import date, datetime
        race_date = datetime.fromisoformat(race['date']).date() if isinstance(race['date'], str) else race['date']
        today = date.today()
        
        # Подсчёт результатов
        async with self.db.execute(
            "SELECT COUNT(*) FROM results WHERE race_id = ?",
            (race_id,)
        ) as cursor:
            row = await cursor.fetchone()
            results_count = row[0] if row else 0
        
        has_results = results_count > 0
        is_past = race_date < today
        
        if is_past and has_results:
            status = 'completed'
        elif is_past:
            status = 'past'
        else:
            status = 'upcoming'
        
        return {
            'status': status,
            'results_count': results_count,
            'has_results': has_results,
            'race_date': race_date,
            'is_past': is_past
        }

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

    async def get_races_filtered(
        self,
        city: Optional[str] = None,
        race_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        distance: Optional[str] = None,
        organizer: Optional[str] = None,
        query: Optional[str] = None,
        upcoming_only: bool = True,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[List[Dict], int]:
        """
        Забеги с фильтрами и пагинацией.
        Returns: (races, total_count)
        """
        conditions = ["is_active = 1"]
        params: list = []

        if upcoming_only:
            conditions.append("date >= date('now')")
        else:
            conditions.append("date < date('now')")

        if city:
            conditions.append("location LIKE ?")
            params.append(f"%{city}%")
        if race_type:
            conditions.append("race_type = ?")
            params.append(race_type)
        if date_from:
            conditions.append("date >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("date <= ?")
            params.append(date_to)
        if distance:
            conditions.append("distances LIKE ?")
            params.append(f"%{distance}%")
        if organizer:
            conditions.append("organizer LIKE ?")
            params.append(f"%{organizer}%")
        if query:
            conditions.append("(name LIKE ? OR organizer LIKE ? OR location LIKE ?)")
            q = f"%{query}%"
            params.extend([q, q, q])

        where = " AND ".join(conditions)
        order = "ORDER BY date ASC" if upcoming_only else "ORDER BY date DESC"

        # Подсчёт всего
        async with self.db.execute(
            f"SELECT COUNT(*) FROM races WHERE {where}",
            params
        ) as cursor:
            row = await cursor.fetchone()
            total = row[0] if row else 0

        params.extend([limit, offset])
        async with self.db.execute(
            f"""
            SELECT * FROM races
            WHERE {where}
            {order}
            LIMIT ? OFFSET ?
            """,
            params
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows], total

    async def get_race_by_id(self, race_id: int) -> Optional[Dict]:
        """Получить забег по ID (для карточки забега)"""
        async with self.db.execute(
            "SELECT * FROM races WHERE id = ? AND is_active = 1",
            (race_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

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

    async def get_race_by_name_date(self, name: str, date_str: str) -> Optional[Dict]:
        """Получить забег по названию и дате (для проверки дубликата)"""
        if not name or not date_str:
            return None
        async with self.db.execute(
            "SELECT * FROM races WHERE name = ? AND date = ?",
            (name.strip(), date_str)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_race_results(
        self, race_id: int, limit: int = 30, offset: int = 0
    ) -> tuple[List[Dict], int]:
        """
        Финишный протокол забега: список результатов с ФИО бегунов.
        Returns: (results, total_count)
        """
        async with self.db.execute(
            "SELECT COUNT(*) FROM results WHERE race_id = ?",
            (race_id,)
        ) as cursor:
            row = await cursor.fetchone()
            total = row[0] if row else 0

        async with self.db.execute(
            """
            SELECT r.id as result_id, r.runner_id, r.distance, r.finish_time, r.finish_time_seconds,
                   r.overall_place, r.gender_place, r.total_runners,
                   ru.last_name, ru.first_name, ru.middle_name, ru.birth_date, ru.telegram_id
            FROM results r
            JOIN runners ru ON r.runner_id = ru.id
            WHERE r.race_id = ?
            ORDER BY (r.overall_place IS NULL), r.overall_place ASC, r.finish_time_seconds ASC, r.id ASC
            LIMIT ? OFFSET ?
            """,
            (race_id, limit, offset)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows], total

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

    async def get_runner_personal_bests(self, runner_id: int) -> List[Dict]:
        """
        Личные рекорды бегуна — лучшие результаты по каждой дистанции из базы.
        Берутся только из протоколов (results), ручной ввод невозможен.
        """
        async with self.db.execute(
            """
            SELECT r.distance, r.finish_time_seconds, r.finish_time,
                   rac.name as race_name, rac.date as race_date
            FROM results r
            JOIN races rac ON r.race_id = rac.id
            WHERE r.runner_id = ? AND r.finish_time_seconds IS NOT NULL
            ORDER BY r.distance, r.finish_time_seconds ASC
            """,
            (runner_id,)
        ) as cursor:
            rows = await cursor.fetchall()
        # Оставляем лучший результат на каждую дистанцию (первый в порядке ASC)
        seen = {}
        for row in rows:
            d = dict(row)
            dist = d['distance']
            if dist not in seen:
                seen[dist] = d
        return list(seen.values())

    async def search_results_by_name(
        self,
        query: str,
        limit: int = 20
    ) -> List[Dict]:
        """Поиск результатов по ФИО бегуна (для «найти мой результат»)"""
        q = f"%{query.strip()}%"
        async with self.db.execute(
            """
            SELECT r.id as result_id, r.runner_id, r.race_id, r.distance, r.finish_time, r.finish_time_seconds,
                   r.overall_place, r.total_runners,
                   ru.last_name, ru.first_name, ru.middle_name, ru.birth_date, ru.telegram_id,
                   rac.name as race_name, rac.date as race_date, rac.organizer,
                   rac.protocol_url, rac.website_url
            FROM results r
            JOIN runners ru ON r.runner_id = ru.id
            JOIN races rac ON r.race_id = rac.id
            WHERE (ru.last_name LIKE ? OR ru.first_name LIKE ? OR ru.middle_name LIKE ?)
            ORDER BY rac.date DESC
            LIMIT ?
            """,
            (q, q, q, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_result_with_race(self, result_id: int) -> Optional[Dict]:
        """Результат с данными забега"""
        async with self.db.execute(
            """
            SELECT r.*, rac.name as race_name, rac.date as race_date, rac.organizer,
                   rac.protocol_url, rac.website_url
            FROM results r
            JOIN races rac ON r.race_id = rac.id
            WHERE r.id = ?
            """,
            (result_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def add_result_claim(
        self,
        result_id: int,
        runner_id: int,
        telegram_id: Optional[int] = None
    ) -> int:
        """Создать заявку «это я»"""
        try:
            cursor = await self.db.execute(
                """
                INSERT INTO result_claims (result_id, runner_id, telegram_id, status)
                VALUES (?, ?, ?, 'pending')
                ON CONFLICT(result_id, runner_id) DO NOTHING
                """,
                (result_id, runner_id, telegram_id)
            )
            await self.db.commit()
            return cursor.lastrowid
        except Exception:
            return 0

    async def get_pending_result_claims(self, limit: int = 50) -> List[Dict]:
        """Заявки на рассмотрении"""
        async with self.db.execute(
            """
            SELECT rc.*,
                   ru_claim.last_name, ru_claim.first_name, ru_claim.birth_date,
                   res.distance, res.finish_time, res.overall_place,
                   rac.name as race_name, rac.date as race_date, rac.organizer
            FROM result_claims rc
            JOIN results res ON rc.result_id = res.id
            JOIN runners ru_claim ON rc.runner_id = ru_claim.id
            JOIN races rac ON res.race_id = rac.id
            WHERE rc.status = 'pending'
            ORDER BY rc.created_at DESC
            LIMIT ?
            """,
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def approve_result_claim(self, claim_id: int, admin_id: Optional[int] = None) -> bool:
        """Одобрить заявку: переносим result к runner заявителя"""
        async with self.db.execute(
            "SELECT result_id, runner_id FROM result_claims WHERE id = ? AND status = 'pending'",
            (claim_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return False
        result_id, new_runner_id = row[0], row[1]
        await self.db.execute(
            "UPDATE results SET runner_id = ? WHERE id = ?",
            (new_runner_id, result_id)
        )
        await self.db.execute(
            "UPDATE result_claims SET status = 'approved', reviewed_at = CURRENT_TIMESTAMP, reviewed_by = ? WHERE id = ?",
            (admin_id, claim_id)
        )
        await self.db.commit()
        return True

    async def reject_result_claim(self, claim_id: int, admin_id: Optional[int] = None, comment: str = "") -> bool:
        """Отклонить заявку"""
        await self.db.execute(
            "UPDATE result_claims SET status = 'rejected', reviewed_at = CURRENT_TIMESTAMP, reviewed_by = ?, admin_comment = ? WHERE id = ?",
            (admin_id, comment or None, claim_id)
        )
        await self.db.commit()
        return True

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

    async def submit_feedback(
        self,
        telegram_id: int,
        text: str,
        runner_id: Optional[int] = None,
    ) -> int:
        """Сохранить обратную связь от пользователя"""
        cursor = await self.db.execute(
            """
            INSERT INTO feedback (runner_id, telegram_id, text)
            VALUES (?, ?, ?)
            """,
            (runner_id, telegram_id, text)
        )
        await self.db.commit()
        return cursor.lastrowid

    async def get_feedback_list(self, limit: int = 20) -> List[Dict]:
        """Получить последние сообщения обратной связи"""
        async with self.db.execute(
            """
            SELECT f.id, f.telegram_id, f.text, f.created_at,
                   r.first_name, r.last_name
            FROM feedback f
            LEFT JOIN runners r ON f.runner_id = r.id
            ORDER BY f.created_at DESC
            LIMIT ?
            """,
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

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
    
    async def delete_race(self, race_id: int) -> Dict[str, int]:
        """
        Удалить забег и все связанные данные (по запросу организатора)
        
        Returns:
            Словарь со статистикой удаления
        """
        stats = {
            'results_deleted': 0,
            'subscriptions_deleted': 0
        }
        
        # Подсчёт удаляемых результатов
        async with self.db.execute(
            "SELECT COUNT(*) FROM results WHERE race_id = ?",
            (race_id,)
        ) as cursor:
            row = await cursor.fetchone()
            stats['results_deleted'] = row[0] if row else 0
        
        # Подсчёт удаляемых подписок
        async with self.db.execute(
            "SELECT COUNT(*) FROM race_subscriptions WHERE race_id = ?",
            (race_id,)
        ) as cursor:
            row = await cursor.fetchone()
            stats['subscriptions_deleted'] = row[0] if row else 0
        
        # Удаляем результаты
        await self.db.execute(
            "DELETE FROM results WHERE race_id = ?",
            (race_id,)
        )
        
        # Удаляем подписки
        await self.db.execute(
            "DELETE FROM race_subscriptions WHERE race_id = ?",
            (race_id,)
        )
        
        # Удаляем забег
        await self.db.execute(
            "DELETE FROM races WHERE id = ?",
            (race_id,)
        )
        
        await self.db.commit()
        return stats
    
    async def delete_races_by_organizer(self, organizer: str) -> Dict[str, int]:
        """
        Удалить все забеги организатора (по запросу организатора)
        
        Returns:
            Словарь со статистикой удаления
        """
        stats = {
            'races_deleted': 0,
            'results_deleted': 0,
            'subscriptions_deleted': 0
        }
        
        # Получаем все ID забегов организатора
        async with self.db.execute(
            "SELECT id FROM races WHERE organizer = ?",
            (organizer,)
        ) as cursor:
            race_ids = [row[0] for row in await cursor.fetchall()]
        
        stats['races_deleted'] = len(race_ids)
        
        if not race_ids:
            return stats
        
        # Подсчёт результатов
        placeholders = ','.join('?' * len(race_ids))
        async with self.db.execute(
            f"SELECT COUNT(*) FROM results WHERE race_id IN ({placeholders})",
            race_ids
        ) as cursor:
            row = await cursor.fetchone()
            stats['results_deleted'] = row[0] if row else 0
        
        # Подсчёт подписок
        async with self.db.execute(
            f"SELECT COUNT(*) FROM race_subscriptions WHERE race_id IN ({placeholders})",
            race_ids
        ) as cursor:
            row = await cursor.fetchone()
            stats['subscriptions_deleted'] = row[0] if row else 0
        
        # Удаляем результаты
        await self.db.execute(
            f"DELETE FROM results WHERE race_id IN ({placeholders})",
            race_ids
        )
        
        # Удаляем подписки
        await self.db.execute(
            f"DELETE FROM race_subscriptions WHERE race_id IN ({placeholders})",
            race_ids
        )
        
        # Удаляем забеги
        await self.db.execute(
            "DELETE FROM races WHERE organizer = ?",
            (organizer,)
        )
        
        await self.db.commit()
        return stats

    # ============================================
    # ОРГАНИЗАТОРЫ (organizers)
    # См. docs/ORGANIZERS.md
    # ============================================

    async def get_organizer_by_canonical_name(
        self, canonical_name: str
    ) -> Optional[Dict]:
        """Получить организатора по каноническому имени"""
        async with self.db.execute(
            "SELECT * FROM organizers WHERE canonical_name = ?",
            (canonical_name,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_races_by_organizer(self, organizer_name: str) -> List[Dict]:
        """Получить забеги организатора (по строке organizer) — для сценария привязки"""
        async with self.db.execute(
            """
            SELECT r.*, COUNT(res.id) as results_count
            FROM races r
            LEFT JOIN results res ON r.id = res.race_id
            WHERE r.organizer = ? AND r.is_active = 1
            GROUP BY r.id
            ORDER BY r.date DESC
            """,
            (organizer_name,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def create_organizer(
        self,
        canonical_name: str,
        display_name: str = '',
        website: str = '',
        contact_telegram: str = '',
        contact_email: str = '',
    ) -> int:
        """Создать организатора"""
        display_name = display_name or canonical_name
        await self.db.execute(
            """
            INSERT INTO organizers (canonical_name, display_name, website, contact_telegram, contact_email, status)
            VALUES (?, ?, ?, ?, ?, 'active')
            ON CONFLICT(canonical_name) DO UPDATE SET
                display_name = excluded.display_name,
                website = excluded.website,
                contact_telegram = excluded.contact_telegram,
                contact_email = excluded.contact_email,
                updated_at = CURRENT_TIMESTAMP
            """,
            (canonical_name, display_name, website, contact_telegram, contact_email)
        )
        await self.db.commit()
        org = await self.get_organizer_by_canonical_name(canonical_name)
        return org['id'] if org else 0

    async def link_races_to_organizer(
        self, organizer_name: str, organizer_id: int
    ) -> int:
        """
        Привязать все забеги с organizer=organizer_name к organizer_id.
        Используется при регистрации организатора.
        Returns: количество обновлённых забегов
        """
        result = await self.db.execute(
            "UPDATE races SET organizer_id = ? WHERE organizer = ?",
            (organizer_id, organizer_name)
        )
        await self.db.commit()
        return result.rowcount


# Глобальный экземпляр
db = Database()
