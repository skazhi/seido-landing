<?php
/**
 * Seido API
 * Работа с базой данных MySQL на хостинге reg.ru
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');
header('Access-Control-Max-Age: 86400');

// Обработка preflight запроса
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// Конфигурация БД
define('DB_HOST', 'localhost');
define('DB_NAME', 'u3426357_seido');        // Измени на своё имя БД
define('DB_USER', 'u3426357_Skazhi');   // Измени на своего пользователя
define('DB_PASS', 'EhmN083fA1108nv1!'); // Измени на свой пароль
define('DB_CHARSET', 'utf8mb4');

// Подключение к БД
function getDbConnection() {
    try {
        $dsn = "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=" . DB_CHARSET;
        $options = [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false,
        ];
        return new PDO($dsn, DB_USER, DB_PASS, $options);
    } catch (PDOException $e) {
        jsonResponse([
            'error' => 'Database connection failed',
            'message' => $e->getMessage(),
            'host' => DB_HOST,
            'database' => DB_NAME,
            'user' => DB_USER
        ], 500);
        return null;
    }
}

// Получение параметра
function getParam($name, $default = null) {
    return $_GET[$name] ?? $default;
}

// JSON ответ
function jsonResponse($data, $status = 200) {
    http_response_code($status);
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
    exit();
}

// Главная страница API
function apiInfo() {
    jsonResponse([
        'service' => 'Seido API',
        'version' => '1.0',
        'status' => 'running',
        'endpoints' => [
            'GET /api/api.php' => 'Информация об API',
            'GET /api/api.php?action=races_upcoming' => 'Предстоящие забеги',
            'GET /api/api.php?action=races_past' => 'Прошедшие забеги',
            'GET /api/api.php?action=race&id=1' => 'Информация о забеге',
            'GET /api/api.php?action=runner_results&telegram_id=123' => 'Результаты бегуна',
            'GET /api/api.php?action=runner_bests&telegram_id=123' => 'Личные рекорды',
            'GET /api/api.php?action=rating&distance=5 км' => 'Рейтинг на дистанции',
            'GET /api/api.php?action=clubs' => 'Список клубов',
            'GET /api/api.php?action=club&id=1' => 'Информация о клубе',
        ]
    ]);
}

// Предстоящие забеги
function getUpcomingRaces($pdo) {
    try {
        // Получаем все предстоящие забеги (сегодня и позже), только активные
        $stmt = $pdo->query("
            SELECT * 
            FROM races 
            WHERE date >= CURDATE() 
            AND is_active = 1 
            ORDER BY date ASC, name ASC 
            LIMIT 100
        ");
        $races = $stmt->fetchAll();
        
        // Декодируем JSON поля
        foreach ($races as &$race) {
            if ($race['distances']) {
                $race['distances'] = json_decode($race['distances'], true);
            }
            // Форматируем дату для удобства
            if ($race['date']) {
                $dateObj = new DateTime($race['date']);
                $race['date_formatted'] = $dateObj->format('d.m.Y');
                $race['date_iso'] = $race['date'];
            }
        }
        
        jsonResponse(['status' => 'ok', 'count' => count($races), 'data' => $races]);
    } catch (PDOException $e) {
        jsonResponse(['error' => $e->getMessage()], 500);
    }
}

// Прошедшие забеги
function getPastRaces($pdo) {
    try {
        $stmt = $pdo->query("SELECT * FROM races WHERE date < CURDATE() ORDER BY date DESC LIMIT 50");
        $races = $stmt->fetchAll();
        
        foreach ($races as &$race) {
            if ($race['distances']) {
                $race['distances'] = json_decode($race['distances'], true);
            }
        }
        
        jsonResponse(['status' => 'ok', 'count' => count($races), 'data' => $races]);
    } catch (PDOException $e) {
        jsonResponse(['error' => $e->getMessage()], 500);
    }
}

// Информация о забеге
function getRace($pdo, $id) {
    try {
        $stmt = $pdo->prepare("SELECT * FROM races WHERE id = ?");
        $stmt->execute([$id]);
        $race = $stmt->fetch();
        
        if (!$race) {
            jsonResponse(['error' => 'Race not found'], 404);
        }
        
        if ($race['distances']) {
            $race['distances'] = json_decode($race['distances'], true);
        }
        
        // Получаем результаты по забегу
        $resultsStmt = $pdo->prepare("
            SELECT r.*, ru.first_name, ru.last_name 
            FROM results r
            JOIN runners ru ON r.runner_id = ru.id
            WHERE r.race_id = ?
            ORDER BY r.finish_time_seconds ASC
        ");
        $resultsStmt->execute([$id]);
        $race['results'] = $resultsStmt->fetchAll();
        
        jsonResponse(['status' => 'ok', 'data' => $race]);
    } catch (PDOException $e) {
        jsonResponse(['error' => $e->getMessage()], 500);
    }
}

// Результаты бегуна
function getRunnerResults($pdo, $telegramId) {
    try {
        $stmt = $pdo->prepare("
            SELECT r.*, ra.name as race_name, ra.date as race_date, ra.location as race_location
            FROM results r
            JOIN runners ru ON r.runner_id = ru.id
            JOIN races ra ON r.race_id = ra.id
            WHERE ru.telegram_id = ?
            ORDER BY ra.date DESC, r.finish_time_seconds ASC
        ");
        $stmt->execute([$telegramId]);
        $results = $stmt->fetchAll();
        
        if (empty($results)) {
            jsonResponse(['status' => 'ok', 'message' => 'No results found', 'data' => []]);
        }
        
        jsonResponse(['status' => 'ok', 'count' => count($results), 'data' => $results]);
    } catch (PDOException $e) {
        jsonResponse(['error' => $e->getMessage()], 500);
    }
}

// Личные рекорды бегуна
function getRunnerBests($pdo, $telegramId) {
    try {
        $stmt = $pdo->prepare("
            SELECT 
                r.distance,
                MIN(r.finish_time_seconds) as best_time_seconds,
                r.finish_time as best_time,
                ra.name as race_name,
                ra.date as race_date
            FROM results r
            JOIN runners ru ON r.runner_id = ru.id
            JOIN races ra ON r.race_id = ra.id
            WHERE ru.telegram_id = ?
            GROUP BY r.distance
            ORDER BY 
                CASE 
                    WHEN r.distance LIKE '5%' THEN 1
                    WHEN r.distance LIKE '10%' THEN 2
                    WHEN r.distance LIKE '21%' THEN 3
                    WHEN r.distance LIKE '42%' THEN 4
                    ELSE 5
                END
        ");
        $stmt->execute([$telegramId]);
        $bests = $stmt->fetchAll();
        
        jsonResponse(['status' => 'ok', 'count' => count($bests), 'data' => $bests]);
    } catch (PDOException $e) {
        jsonResponse(['error' => $e->getMessage()], 500);
    }
}

// Рейтинг на дистанции
function getRating($pdo, $distance) {
    try {
        $stmt = $pdo->prepare("
            SELECT 
                ru.id,
                ru.first_name,
                ru.last_name,
                ru.city,
                MIN(r.finish_time_seconds) as best_time_seconds,
                r.finish_time as best_time,
                COUNT(*) as races_count,
                MIN(r.overall_place) as best_place
            FROM results r
            JOIN runners ru ON r.runner_id = ru.id
            WHERE r.distance = ?
            GROUP BY r.runner_id
            HAVING best_time_seconds IS NOT NULL
            ORDER BY best_time_seconds ASC
            LIMIT 50
        ");
        $stmt->execute([$distance]);
        $rating = $stmt->fetchAll();
        
        jsonResponse(['status' => 'ok', 'count' => count($rating), 'data' => $rating]);
    } catch (PDOException $e) {
        jsonResponse(['error' => $e->getMessage()], 500);
    }
}

// Список клубов
function getClubs($pdo) {
    try {
        $stmt = $pdo->query("
            SELECT c.*, COUNT(cm.id) as members_count
            FROM clubs c
            LEFT JOIN club_members cm ON c.id = cm.club_id
            GROUP BY c.id
            ORDER BY members_count DESC, c.name ASC
        ");
        $clubs = $stmt->fetchAll();
        
        jsonResponse(['status' => 'ok', 'count' => count($clubs), 'data' => $clubs]);
    } catch (PDOException $e) {
        jsonResponse(['error' => $e->getMessage()], 500);
    }
}

// Информация о клубе
function getClub($pdo, $id) {
    try {
        $stmt = $pdo->prepare("SELECT * FROM clubs WHERE id = ?");
        $stmt->execute([$id]);
        $club = $stmt->fetch();
        
        if (!$club) {
            jsonResponse(['error' => 'Club not found'], 404);
        }
        
        // Получаем членов клуба
        $membersStmt = $pdo->prepare("
            SELECT ru.* 
            FROM club_members cm
            JOIN runners ru ON cm.runner_id = ru.id
            WHERE cm.club_id = ?
        ");
        $membersStmt->execute([$id]);
        $club['members'] = $membersStmt->fetchAll();
        
        jsonResponse(['status' => 'ok', 'data' => $club]);
    } catch (PDOException $e) {
        jsonResponse(['error' => $e->getMessage()], 500);
    }
}

// Основной роутер
try {
    $pdo = getDbConnection();
    if (!$pdo) {
        // Ошибка подключения уже обработана в getDbConnection()
        exit();
    }
} catch (Exception $e) {
    jsonResponse(['error' => 'Database connection failed', 'message' => $e->getMessage()], 500);
}

$action = getParam('action', '');
$id = getParam('id', null);
$telegram_id = getParam('telegram_id', null);
$distance = getParam('distance', '');

switch ($action) {
    case '':
        apiInfo();
        break;
        
    case 'races_upcoming':
        getUpcomingRaces($pdo);
        break;
        
    case 'races_past':
        getPastRaces($pdo);
        break;
        
    case 'race':
        if ($id) {
            getRace($pdo, $id);
        } else {
            jsonResponse(['error' => 'Missing race ID'], 400);
        }
        break;
        
    case 'runner_results':
        if ($telegram_id) {
            getRunnerResults($pdo, $telegram_id);
        } else {
            jsonResponse(['error' => 'Missing telegram_id'], 400);
        }
        break;
        
    case 'runner_bests':
        if ($telegram_id) {
            getRunnerBests($pdo, $telegram_id);
        } else {
            jsonResponse(['error' => 'Missing telegram_id'], 400);
        }
        break;
        
    case 'rating':
        if ($distance) {
            getRating($pdo, $distance);
        } else {
            jsonResponse(['error' => 'Missing distance'], 400);
        }
        break;
        
    case 'clubs':
        getClubs($pdo);
        break;
        
    case 'club':
        if ($id) {
            getClub($pdo, $id);
        } else {
            jsonResponse(['error' => 'Missing club ID'], 400);
        }
        break;
        
    default:
        jsonResponse(['error' => 'Unknown action', 'available_actions' => [
            'races_upcoming', 'races_past', 'race', 
            'runner_results', 'runner_bests', 'rating',
            'clubs', 'club'
        ]], 400);
}
?>
