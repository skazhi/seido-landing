-- Seido: Схема базы данных PostgreSQL
-- Версия: 0.1
-- Дата: 2026-02-18

-- ============================================
-- ТАБЛИЦА: Бегуны (runners)
-- ============================================
CREATE TABLE runners (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE,           -- ID пользователя Telegram
    first_name VARCHAR(100) NOT NULL,    -- Имя
    last_name VARCHAR(100) NOT NULL,     -- Фамилия
    middle_name VARCHAR(100),            -- Отчество (опционально)
    birth_date DATE,                     -- Дата рождения
    gender CHAR(1) CHECK (gender IN ('M', 'F')),  -- Пол: M/F
    city VARCHAR(100),                   -- Город
    country VARCHAR(100) DEFAULT 'Россия',  -- Страна
    club_name VARCHAR(100),              -- Название клуба (опционально)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для быстрого поиска
CREATE INDEX idx_runners_last_name ON runners(last_name);
CREATE INDEX idx_runners_full_name ON runners(last_name, first_name, middle_name);
CREATE INDEX idx_runners_telegram ON runners(telegram_id);
CREATE INDEX idx_runners_city ON runners(city);
CREATE INDEX idx_runners_birth_date ON runners(birth_date);

-- ============================================
-- ТАБЛИЦА: Забеги (races)
-- ============================================
CREATE TABLE races (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,          -- Название забега
    date DATE NOT NULL,                  -- Дата проведения
    location VARCHAR(200),               -- Место проведения (город, трасса)
    organizer VARCHAR(100),              -- Организатор (5верст, S95, RHR и т.д.)
    race_type VARCHAR(50),               -- Тип: шоссе, трейл, кросс, стадион
    distances JSONB,                     -- Доступные дистанции: [{"name": "5 км", "elevation": 50}]
    website_url VARCHAR(500),            -- Ссылка на страницу забега
    protocol_url VARCHAR(500),           -- Ссылка на протокол
    is_active BOOLEAN DEFAULT TRUE,      -- Актуален ли забег
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы
CREATE INDEX idx_races_date ON races(date);
CREATE INDEX idx_races_name ON races(name);
CREATE INDEX idx_races_organizer ON races(organizer);
CREATE INDEX idx_races_location ON races(location);
CREATE INDEX idx_races_type ON races(race_type);

-- ============================================
-- ТАБЛИЦА: Результаты (results)
-- ============================================
CREATE TABLE results (
    id SERIAL PRIMARY KEY,
    runner_id INTEGER NOT NULL REFERENCES runners(id) ON DELETE CASCADE,
    race_id INTEGER NOT NULL REFERENCES races(id) ON DELETE CASCADE,
    distance VARCHAR(50) NOT NULL,       -- Дистанция (5 км, 10 км, 21.1 км и т.д.)
    finish_time INTERVAL,                -- Финишное время (hh:mm:ss)
    finish_time_seconds INTEGER,         -- Время в секундах (для расчётов)
    pace INTERVAL,                       -- Темп (мин/км)
    pace_seconds_per_km INTEGER,         -- Темп в секундах на км
    overall_place INTEGER,               -- Место в общем зачёте
    gender_place INTEGER,                -- Место среди своего пола
    age_group VARCHAR(20),               -- Возрастная категория (18-29, 30-39 и т.д.)
    age_group_place INTEGER,             -- Место в возрастной категории
    club_place INTEGER,                  -- Место в зачёте клубов
    total_runners INTEGER,               -- Всего участников на дистанции
    points INTEGER,                      -- Очки (если есть система начисления)
    is_official BOOLEAN DEFAULT TRUE,    -- Официальный результат
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Уникальность: один бегун не может иметь два результата на одном забеге на одной дистанции
    UNIQUE(runner_id, race_id, distance)
);

-- Индексы для быстрого поиска результатов
CREATE INDEX idx_results_runner ON results(runner_id);
CREATE INDEX idx_results_race ON results(race_id);
CREATE INDEX idx_results_time ON results(finish_time_seconds);
CREATE INDEX idx_results_place ON results(overall_place);
CREATE INDEX idx_results_distance ON results(distance);

-- ============================================
-- ТАБЛИЦА: Заявки на добавление забегов (race_submissions)
-- ============================================
CREATE TABLE race_submissions (
    id SERIAL PRIMARY KEY,
    submitted_by BIGINT,                 -- Telegram ID отправителя
    race_name VARCHAR(200) NOT NULL,     -- Название забега
    race_date DATE,                      -- Дата забега
    protocol_url VARCHAR(500),           -- Ссылка на протокол
    file_path VARCHAR(500),              -- Путь к загруженному файлу
    status VARCHAR(20) DEFAULT 'pending', -- pending, approved, rejected
    admin_comment TEXT,                  -- Комментарий админа
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP
);

CREATE INDEX idx_submissions_status ON race_submissions(status);

-- ============================================
-- ТАБЛИЦА: Подписки на забеги (race_subscriptions)
-- ============================================
CREATE TABLE race_subscriptions (
    id SERIAL PRIMARY KEY,
    runner_id INTEGER NOT NULL REFERENCES runners(id) ON DELETE CASCADE,
    race_id INTEGER NOT NULL REFERENCES races(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'planning', -- planning, registered, finished
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(runner_id, race_id)
);

CREATE INDEX idx_subscriptions_runner ON race_subscriptions(runner_id);
CREATE INDEX idx_subscriptions_race ON race_subscriptions(race_id);

-- ============================================
-- ТАБЛИЦА: Пользователи с Pro-статусом (premium_users)
-- ============================================
CREATE TABLE premium_users (
    id SERIAL PRIMARY KEY,
    runner_id INTEGER UNIQUE NOT NULL REFERENCES runners(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'free',   -- free, pro, trial
    trial_ends_at TIMESTAMP,
    subscription_ends_at TIMESTAMP,
    payment_provider VARCHAR(50),        -- yookassa, tinkoff
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- ПРЕДСТАВЛЕНИЯ (VIEWS) для удобных запросов
-- ============================================

-- Лучшие результаты бегуна по каждой дистанции
CREATE VIEW runner_bests AS
SELECT 
    r.runner_id,
    ru.last_name,
    ru.first_name,
    res.distance,
    MIN(res.finish_time_seconds) as best_time_seconds,
    MIN(res.finish_time) FILTER (WHERE res.finish_time_seconds = MIN(res.finish_time_seconds) OVER (PARTITION BY res.distance)) as best_time
FROM results res
JOIN runners ru ON res.runner_id = ru.id
GROUP BY r.runner_id, ru.last_name, ru.first_name, res.distance;

-- Рейтинг бегунов по средней дистанции
CREATE VIEW distance_rating AS
SELECT 
    ru.id as runner_id,
    ru.last_name,
    ru.first_name,
    ru.city,
    res.distance,
    res.finish_time_seconds,
    res.overall_place,
    res.total_runners,
    ROUND(100.0 * (res.total_runners - res.overall_place + 1) / res.total_runners, 2) as rating_percent
FROM results res
JOIN runners ru ON res.runner_id = ru.id
WHERE res.overall_place IS NOT NULL AND res.total_runners > 0;

-- ============================================
-- ФУНКЦИИ И ТРИГГЕРЫ
-- ============================================

-- Автоматическое обновление updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_runners_updated_at BEFORE UPDATE ON runners
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_races_updated_at BEFORE UPDATE ON races
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_results_updated_at BEFORE UPDATE ON results
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- ПРИМЕРЫ ДАННЫХ (для тестирования)
-- ============================================

-- Пример бегуна
-- INSERT INTO runners (first_name, last_name, birth_date, gender, city)
-- VALUES ('Иван', 'Иванов', '1990-05-15', 'M', 'Москва');

-- Пример забега
-- INSERT INTO races (name, date, location, organizer, race_type, distances)
-- VALUES ('Пятерка в Парке', '2026-03-01', 'Парк Горького, Москва', '5верст', 'шоссе', 
--         '[{"name": "5 км", "elevation": 20}]');

-- Пример результата
-- INSERT INTO results (runner_id, race_id, distance, finish_time_seconds, finish_time, overall_place, total_runners)
-- VALUES (1, 1, '5 км', 1500, '00:25:00', 42, 350);

-- ============================================
-- КОММЕНТАРИИ
-- ============================================

COMMENT ON TABLE runners IS 'Профили бегунов';
COMMENT ON TABLE races IS 'Информация о забегах';
COMMENT ON TABLE results IS 'Результаты бегунов на забегах';
COMMENT ON TABLE race_submissions IS 'Заявки на добавление забегов от пользователей';
COMMENT ON TABLE race_subscriptions IS 'Подписки бегунов на предстоящие забеги';
COMMENT ON TABLE premium_users IS 'Pro-подписки пользователей';
