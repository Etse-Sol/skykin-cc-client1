<?php
/**
 * After-hours callback saver — called by FreeSWITCH (no browser session).
 * Auth: shared key SKYKIN_AH_CB_KEY (header X-SkyKin-Key or ?key=).
 *
 * GET/POST: phone, domain, did, uuid
 */
declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');

require_once __DIR__ . '/skykin_config.php';

$key_expected = getenv('SKYKIN_AH_CB_KEY') ?: 'skykin-ah-cb-2026';
$key_got = $_SERVER['HTTP_X_SKYKIN_KEY']
    ?? ($_GET['key'] ?? ($_POST['key'] ?? ''));
if (!is_string($key_got) || !hash_equals($key_expected, $key_got)) {
    http_response_code(403);
    echo json_encode(['ok' => false, 'error' => 'forbidden']);
    exit;
}

/** @return array{ok:bool,callback_id?:int,dedup?:bool,phone?:string,callback_time?:string,error?:string} */
function skykin_ah_cb_insert(PDO $db, string $phone, string $domain, string $did, string $uuid, string $called_at = ''): array {
    $digits = preg_replace('/\D+/', '', $phone) ?? '';
    if ($digits === '' || strlen($digits) < 7) {
        return ['ok' => false, 'error' => 'phone required'];
    }
    $display = $phone;
    if ($digits !== '' && ($digits[0] ?? '') !== '+') {
        if (str_starts_with($digits, '251') && strlen($digits) >= 12) {
            $display = '+' . $digits;
        } elseif (strlen($digits) === 9) {
            $display = '+251' . $digits;
        } elseif (strlen($digits) === 10 && $digits[0] === '0') {
            $display = '+251' . substr($digits, 1);
        } else {
            $display = $digits;
        }
    }

    $driver = $db->getAttribute(PDO::ATTR_DRIVER_NAME);
    if ($driver === 'sqlite') {
        $db->exec("CREATE TABLE IF NOT EXISTS skykin_callbacks (
            callback_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            customer_phone TEXT,
            callback_time TEXT,
            notes TEXT,
            agent_id TEXT,
            status TEXT DEFAULT 'Scheduled',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )");
    } else {
        $db->exec("CREATE TABLE IF NOT EXISTS skykin_callbacks (
            callback_id SERIAL PRIMARY KEY,
            customer_name VARCHAR(150),
            customer_phone VARCHAR(50),
            callback_time TIMESTAMP,
            notes TEXT,
            agent_id VARCHAR(50),
            status VARCHAR(50) DEFAULT 'Scheduled',
            created_at TIMESTAMP DEFAULT NOW()
        )");
    }

    try {
        $chk = $db->prepare(
            "SELECT callback_id FROM skykin_callbacks
             WHERE status = 'Scheduled'
               AND agent_id = 'after-hours'
               AND (customer_phone = :p OR customer_phone = :d OR notes LIKE :like)
               AND created_at >= NOW() - INTERVAL '24 hours'
             LIMIT 1"
        );
        $chk->execute([
            ':p' => $display,
            ':d' => $digits,
            ':like' => '%' . $digits . '%',
        ]);
    } catch (Throwable $e) {
        $chk = $db->prepare(
            "SELECT callback_id FROM skykin_callbacks
             WHERE status = 'Scheduled' AND agent_id = 'after-hours'
               AND (customer_phone = :p OR customer_phone = :d)
             ORDER BY callback_id DESC LIMIT 1"
        );
        $chk->execute([':p' => $display, ':d' => $digits]);
    }
    $existing = $chk->fetch(PDO::FETCH_ASSOC);
    if ($existing) {
        return ['ok' => true, 'dedup' => true, 'callback_id' => (int)$existing['callback_id']];
    }

    // callback_time = when they actually called (EAT). Morning agents dial them back.
    $tz = new DateTimeZone('Africa/Addis_Ababa');
    $called = null;
    if ($called_at !== '') {
        try {
            // Accept EAT wall time or ISO/UTC (e.g. 2026-09-08T21:14:00Z from file queue).
            if (preg_match('/Z$|[\+\-]\d{2}:?\d{2}$/', $called_at) || str_contains($called_at, 'T')) {
                $called = new DateTime($called_at);
                $called->setTimezone($tz);
            } else {
                $called = new DateTime($called_at, $tz);
            }
        } catch (Throwable $e) {
            $called = null;
        }
    }
    if ($called === null) {
        $called = new DateTime('now', $tz);
    }
    $callback_time = $called->format('Y-m-d H:i:s');
    // Keep Notes short for agents; call time is in the Time column.
    $notes = 'After hours';
    if ($did !== '' && $did !== 'log-backfill' && $did !== 'smoke' && $did !== 'test') {
        $notes .= ' · DID ' . $did;
    }

    $ins = $db->prepare(
        "INSERT INTO skykin_callbacks
            (customer_name, customer_phone, callback_time, notes, agent_id, status)
         VALUES
            (:name, :phone, :time, :notes, 'after-hours', 'Scheduled')"
    );
    $ins->execute([
        ':name' => 'After-hours caller',
        ':phone' => $display,
        ':time' => $callback_time,
        ':notes' => $notes,
    ]);
    return ['ok' => true, 'phone' => $display, 'callback_time' => $callback_time];
}

// Drain file queue written by Lua when curl is unavailable.
if (isset($_GET['drain']) || isset($_POST['drain'])) {
    try {
        $db = skykin_pdo_fusionpbx();
        $paths = [
            '/var/lib/freeswitch/recordings/skykin_after_hours_queue.txt',
            '/usr/local/freeswitch/recordings/skykin_after_hours_queue.txt',
        ];
        $n = 0;
        foreach ($paths as $path) {
            if (!is_readable($path)) {
                continue;
            }
            $lines = file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) ?: [];
            @file_put_contents($path, '');
            foreach ($lines as $line) {
                $parts = explode('|', $line);
                if (count($parts) < 3) {
                    continue;
                }
                // ts|domain|phone|did|uuid  OR  domain|phone|did|uuid
                $called_at = '';
                if (preg_match('/^\d{4}-\d{2}-\d{2}/', $parts[0] ?? '')) {
                    $called_at = $parts[0] ?? '';
                    $domain = $parts[1] ?? 'ahununu';
                    $phone = $parts[2] ?? '';
                    $did = $parts[3] ?? '';
                    $uuid = $parts[4] ?? '';
                } else {
                    $domain = $parts[0] ?? 'ahununu';
                    $phone = $parts[1] ?? '';
                    $did = $parts[2] ?? '';
                    $uuid = $parts[3] ?? '';
                }
                $r = skykin_ah_cb_insert($db, $phone, $domain, $did, $uuid, $called_at);
                if (!empty($r['ok'])) {
                    $n++;
                }
            }
        }
        echo json_encode(['ok' => true, 'drained' => $n]);
    } catch (Throwable $e) {
        http_response_code(500);
        echo json_encode(['ok' => false, 'error' => $e->getMessage()]);
    }
    exit;
}

$phone = trim((string)($_POST['phone'] ?? $_GET['phone'] ?? ''));
$domain = trim((string)($_POST['domain'] ?? $_GET['domain'] ?? 'ahununu'));
$did = trim((string)($_POST['did'] ?? $_GET['did'] ?? ''));
$uuid = trim((string)($_POST['uuid'] ?? $_GET['uuid'] ?? ''));
$called_at = trim((string)($_POST['called_at'] ?? $_GET['called_at'] ?? ''));

try {
    $db = skykin_pdo_fusionpbx();
    $r = skykin_ah_cb_insert($db, $phone, $domain, $did, $uuid, $called_at);
    if (empty($r['ok'])) {
        http_response_code(400);
    }
    echo json_encode($r);
} catch (Throwable $e) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => $e->getMessage()]);
}
