-- Seido: Схема базы данных MySQL
-- Версия: 1.0
-- Для хостинга reg.ru (MySQL)

-- ============================================
-- ТАБЛИЦА: Бегуны (runners)
-- ============================================
CREATE TABLE IF NOT EXISTS runners (
    id INT PRIMARY KEY AUTO_INCREMENT,
    telegram_id BIGINT UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    middle_name VARCHAR(100),
    birth_date DATE,
    gender CHAR(1) CHECK (gender IN ('M', 'F')),
    city VARCHAR(100),
    country VARCHAR(100) DEFAULT 'Россия',
    club_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_last_name (last_name),
    INDEX idx_telegram (telegram_id),
    INDEX idx_city (city)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- ТАБЛИЦА: Забеги (races)
-- ============================================
CREATE TABLE IF NOT EXISTS races (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(200) NOT NULL,
    date DATE NOT NULL,
    location VARCHAR(200),
    organizer VARCHAR(100),
    race_type VARCHAR(50),
    distances JSON,
    website_url VARCHAR(500),
    protocol_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_date (date),
    INDEX idx_name (name),
    INDEX idx_organizer (organizer),
    INDEX idx_location (location)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- ТАБЛИЦА: Результаты (results)
-- ============================================
CREATE TABLE IF NOT EXISTS results (
    id INT PRIMARY KEY AUTO_INCREMENT,
    runner_id INT NOT NULL,
    race_id INT NOT NULL,
    distance VARCHAR(50) NOT NULL,
    finish_time TIME,
    finish_time_seconds INT,
    pace TIME,
    pace_seconds_per_km INT,
    overall_place INT,
    gender_place INT,
    age_group VARCHAR(20),
    age_group_place INT,
    club_place INT,
    total_runners INT,
    points INT,
    is_official BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (runner_id) REFERENCES runners(id) ON DELETE CASCADE,
    FOREIGN KEY (race_id) REFERENCES races(id) ON DELETE CASCADE,
    UNIQUE KEY unique_result (runner_id, race_id, distance),
    INDEX idx_runner (runner_id),
    INDEX idx_race (race_id),
    INDEX idx_time (finish_time_seconds)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- ТАБЛИЦА: Подписки на забеги (race_subscriptions)
-- ============================================
CREATE TABLE IF NOT EXISTS race_subscriptions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    runner_id INT NOT NULL,
    race_id INT NOT NULL,
    status VARCHAR(20) DEFAULT 'planning',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (runner_id) REFERENCES runners(id) ON DELETE CASCADE,
    FOREIGN KEY (race_id) REFERENCES races(id) ON DELETE CASCADE,
    UNIQUE KEY unique_subscription (runner_id, race_id),
    INDEX idx_runner (runner_id),
    INDEX idx_race (race_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- ТАБЛИЦА: Беговые клубы (clubs)
-- ============================================
CREATE TABLE IF NOT EXISTS clubs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    city VARCHAR(100),
    logo_url VARCHAR(500),
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_verified BOOLEAN DEFAULT FALSE,
    INDEX idx_name (name),
    INDEX idx_city (city)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- ТАБЛИЦА: Члены клубов (club_members)
-- ============================================
CREATE TABLE IF NOT EXISTS club_members (
    id INT PRIMARY KEY AUTO_INCREMENT,
    club_id INT NOT NULL,
    runner_id INT NOT NULL,
    role VARCHAR(50) DEFAULT 'member',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE CASCADE,
    FOREIGN KEY (runner_id) REFERENCES runners(id) ON DELETE CASCADE,
    UNIQUE KEY unique_member (club_id, runner_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- ПРИМЕРЫ ДАННЫХ (удалить перед продакшеном)
-- ============================================

-- Пример бегуна
INSERT INTO runners (first_name, last_name, birth_date, gender, city, telegram_id) VALUES
('Иван', 'Иванов', '1990-05-15', 'M', 'Москва', 123456789),
('Петр', 'Петров', '1985-08-20', 'M', 'Санкт-Петербург', 987654321),
('Анна', 'Сидорова', '1992-03-10', 'F', 'Москва', 456789123);

-- Пример забега
INSERT INTO races (name, date, location, organizer, race_type, distances, website_url) VALUES
('Пятерка в Парке', '2026-03-01', 'Парк Горького, Москва', '5верст', 'шоссе', 
 '[{"name": "5 км", "elevation": 20}]', 'https://5verst.ru'),
('Московский Марафон', '2026-09-20', 'Москва', 'Беговое сообщество', 'шоссе',
 '[{"name": "5 км", "elevation": 50}, {"name": "10 км", "elevation": 80}, {"name": "21.1 км", "elevation": 100}, {"name": "42.2 км", "elevation": 150}]',
 'https://marathon.ru'),
('Лужники', '2026-05-15', 'Лужники, Москва', 'Спорт-Марафон', 'шоссе',
 '[{"name": "10 км", "elevation": 30}, {"name": "21.1 км", "elevation": 50}]',
 'https://sport-marafon.ru');

-- Пример результатов
INSERT INTO results (runner_id, race_id, distance, finish_time, finish_time_seconds, overall_place, total_runners) VALUES
(1, 1, '5 км', '00:25:30', 1530, 42, 350),
(1, 2, '10 км', '00:52:15', 3135, 128, 1200),
(2, 1, '5 км', '00:23:45', 1425, 25, 350),
(2, 3, '10 км', '00:48:30', 2910, 85, 800),
(3, 1, '5 км', '00:28:20', 1700, 95, 350);
