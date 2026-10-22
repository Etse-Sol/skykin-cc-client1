<?php
// SkyKin Technologies – CRM (Customer Relationship Manager)
require_once __DIR__ . '/session_bootstrap.php';
require_once __DIR__ . '/skykin_config.php';

// Agents and supervisors both use CRM (caller lookup / contacts)
$is_api = isset($_GET['api']);
skykin_require_login($is_api);

$logged_in_user   = $_SESSION['username']    ?? '';
$logged_in_domain = skykin_default_domain();
$domain  = htmlspecialchars(skykin_domain_param($_GET['domain'] ?? null));
$embed   = !empty($_GET['embed']);

function getDB() {
    static $db = null;
    if ($db !== null) return $db;
    $db = skykin_pdo_fusionpbx(); // throws RuntimeException on failure
    return $db;
}

// ── Ensure CRM table exists ──────────────────────────────────────────────────
try {
    $db = getDB();
    $isSQLite = ($db->getAttribute(PDO::ATTR_DRIVER_NAME) === 'sqlite');
    if ($isSQLite) {
        $db->exec("CREATE TABLE IF NOT EXISTS skykin_contacts (
            contact_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            phone         TEXT NOT NULL UNIQUE,
            alt_phone     TEXT,
            full_name     TEXT NOT NULL,
            email         TEXT,
            company       TEXT,
            language      TEXT DEFAULT 'English',
            account_type  TEXT DEFAULT 'Customer',
            notes         TEXT,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        )");
    } else {
        $db->exec("CREATE TABLE IF NOT EXISTS skykin_contacts (
            contact_id    SERIAL PRIMARY KEY,
            phone         TEXT NOT NULL UNIQUE,
            alt_phone     TEXT,
            full_name     TEXT NOT NULL,
            email         TEXT,
            company       TEXT,
            language      TEXT DEFAULT 'English',
            account_type  TEXT DEFAULT 'Customer',
            notes         TEXT,
            created_at    TIMESTAMP DEFAULT NOW(),
            updated_at    TIMESTAMP DEFAULT NOW()
        )");
    }
    skykin_crm_ensure_contacts($db);
    skykin_crm_ensure_journey($db);
    skykin_crm_ensure_cases($db);
    skykin_crm_ensure_knowledge($db);
    try {
        skykin_crm_seed_knowledge($db);
    } catch (Throwable $eKb) { /* ignore */ }
    // Sample contacts if empty
    $cnt = $db->query("SELECT COUNT(*) FROM skykin_contacts")->fetchColumn();
    if ($cnt == 0) {
        $db->exec("INSERT INTO skykin_contacts (phone,full_name,email,company,language,account_type,notes,fayda_verified,csat,sentiment,products) VALUES
            ('+251911000001','Abebe Girma','abebe@example.com','TechCo','Amharic','VIP','Prefers callbacks in the morning',0,4.0,'Neutral','Prepaid plan | telebirr wallet'),
            ('+251922000002','Sara Mohammed','sara@example.com','BizGroup','English','Customer','Call history: 5 support tickets',0,4.5,'Positive','Postpaid | telebirr'),
            ('+251933000003','Dawit Bekele','dawit@example.com','RetailPlus','Oromo','Customer','',0,NULL,'Neutral','Prepaid plan'),
            ('+251911234567','Selam T.','selam@example.com','Ethio Telecom','Amharic','Gold','Three contacts this week about SIM and telebirr. Identity verified with Fayda.',1,5.0,'Neutral','Prepaid plan | telebirr wallet')
        ");
    }
    // Ensure Selam demo contact + multi-channel journey (mockup Customer 360)
    try {
        $selamPhone = '+251911234567';
        $haveSelam = $db->prepare("SELECT contact_id FROM skykin_contacts WHERE phone = :p OR phone LIKE :t LIMIT 1");
        $haveSelam->execute([':p' => $selamPhone, ':t' => '%911234567%']);
        if (!$haveSelam->fetch()) {
            try {
                $db->prepare("INSERT INTO skykin_contacts
                    (phone,full_name,email,company,language,account_type,notes,fayda_verified,csat,sentiment,products)
                    VALUES (:p,'Selam T.','selam@example.com','Ethio Telecom','Amharic','Gold',
                    'Three contacts this week about SIM and telebirr. Identity verified with Fayda.',1,5.0,'Neutral','Prepaid plan | telebirr wallet')")
                    ->execute([':p' => $selamPhone]);
            } catch (Throwable $eIns) { /* unique race */ }
        } else {
            try {
                $db->prepare("UPDATE skykin_contacts SET
                    full_name='Selam T.', account_type='Gold', language='Amharic',
                    fayda_verified=1, csat=5.0, sentiment='Neutral',
                    products='Prepaid plan | telebirr wallet',
                    notes='Three contacts this week about SIM and telebirr. Identity verified with Fayda.'
                    WHERE phone = :p OR phone LIKE :t")
                    ->execute([':p' => $selamPhone, ':t' => '%911234567%']);
            } catch (Throwable $eUp) { /* columns may be missing on first run */ }
        }
        $jc = $db->prepare("SELECT COUNT(*) FROM skykin_journey_events WHERE phone = :p OR phone LIKE :t");
        $jc->execute([':p' => $selamPhone, ':t' => '%911234567%']);
        if ((int)$jc->fetchColumn() === 0) {
            $ins = $db->prepare("INSERT INTO skykin_journey_events (phone, event_at, channel, summary) VALUES (:p,:t,:c,:s)");
            $demo = [
                [date('Y-m-d') . ' 10:12:00', 'Voice', 'Lost phone, asks for SIM swap'],
                [date('Y-m-d') . ' 09:40:00', 'Web chat', 'Bot shared the SIM swap article'],
                [date('Y-m-d', strtotime('-1 day')) . ' 16:20:00', 'WhatsApp', 'Asked about telebirr limit'],
                [date('Y-m-d', strtotime('-3 day')) . ' 11:05:00', 'App', 'Viewed data packages'],
                [date('Y-m-d', strtotime('-7 day')) . ' 14:00:00', 'Shop', 'SIM registered with Fayda'],
                [date('Y-m-d', strtotime('-30 day')) . ' 09:00:00', 'SMS survey', 'CSAT 5 out of 5'],
            ];
            foreach ($demo as $d) {
                $ins->execute([':p' => $selamPhone, ':t' => $d[0], ':c' => $d[1], ':s' => $d[2]]);
            }
        }
        try {
            $chkCase = $db->prepare("SELECT COUNT(*) FROM skykin_cases WHERE customer_phone LIKE :t AND LOWER(COALESCE(status,'')) NOT IN ('closed','resolved')");
            $chkCase->execute([':t' => '%911234567%']);
            if ((int)$chkCase->fetchColumn() === 0) {
                $db->prepare("INSERT INTO skykin_cases (customer_name, customer_phone, issue_type, description, status, priority)
                    VALUES ('Selam T.', :p, 'SIM replacement', 'Lost phone — SIM swap', 'Open', 'High')")
                    ->execute([':p' => $selamPhone]);
            }
        } catch (Throwable $e2) { /* cases table may differ */ }
    } catch (Throwable $e) { /* ignore seed errors */ }
} catch (Exception $e) { /* silent */ }

// ── API ──────────────────────────────────────────────────────────────────────
if (isset($_GET['api'])) {
    error_reporting(0);
    header('Content-Type: application/json');

    try {
        $db = getDB();

        // Lookup by phone — full Customer 360 payload
        if ($_GET['api'] === 'lookup' || $_GET['api'] === '360') {
            $phone = $_GET['phone'] ?? '';
            if (!$phone) { echo json_encode(null); exit; }
            $row = skykin_crm_find_contact($db, $phone);
            if (!$row) {
                $norm = skykin_normalize_phone_storage($phone);
                if ($norm !== '' && $norm !== $phone) {
                    $row = skykin_crm_find_contact($db, $norm);
                }
            }
            // Always return 360 shape (even unknown caller) so UI can show CDR journey
            $out = skykin_crm_build_360($db, $phone, $row);
            if (!$row && empty($out['call_history']) && empty($out['journey'])) {
                // keep null for strict unknown with no activity
                if (($_GET['api'] ?? '') === 'lookup' && empty($out['full_name'])) {
                    echo json_encode($out);
                    exit;
                }
            }
            echo json_encode($out);
            exit;
        }

        // Add a journey event (demo / agent notes on history track)
        if ($_GET['api'] === 'journey_add' && $_SERVER['REQUEST_METHOD'] === 'POST') {
            skykin_crm_ensure_journey($db);
            $body = json_decode(file_get_contents('php://input'), true);
            if (!is_array($body)) {
                echo json_encode(['ok' => false, 'error' => 'Invalid JSON']);
                exit;
            }
            $rawPhone = trim((string)($body['phone'] ?? ''));
            $digits = preg_replace('/\D+/', '', $rawPhone);
            // Keep short extensions (101/102) as-is — do not turn into 0…
            if (preg_match('/^\d{2,6}$/', $digits)) {
                $ph = $digits;
            } else {
                $ph = skykin_normalize_phone_storage($rawPhone);
            }
            $channel = trim((string)($body['channel'] ?? 'CRM'));
            $summary = trim((string)($body['summary'] ?? ''));
            $eventAt = trim((string)($body['event_at'] ?? ''));
            if ($ph === '' || $summary === '') {
                echo json_encode(['ok' => false, 'error' => 'phone and summary required']);
                exit;
            }
            if ($eventAt === '') {
                $eventAt = date('Y-m-d H:i:s');
            }
            $allowed = ['Voice','Web chat','WhatsApp','App','Shop','SMS','SMS survey','Case','CRM'];
            if (!in_array($channel, $allowed, true)) {
                $channel = 'CRM';
            }
            $s = $db->prepare("INSERT INTO skykin_journey_events (phone, event_at, channel, summary) VALUES (:p,:t,:c,:s)");
            $s->execute([':p' => $ph, ':t' => $eventAt, ':c' => $channel, ':s' => $summary]);
            echo json_encode(['ok' => true, 'phone' => $ph, 'channel' => $channel]);
            exit;
        }

        // List cases (call reason + status) — also import saved wrap-up journey reasons
        if ($_GET['api'] === 'cases') {
            skykin_crm_ensure_cases($db);
            $synced = 0;
            try {
                $synced = skykin_crm_sync_cases_from_journey($db);
            } catch (Throwable $eSync) {
                $synced = 0;
            }
            $isSqlite = ($db->getAttribute(PDO::ATTR_DRIVER_NAME) === 'sqlite');
            $dateFmt = $isSqlite
                ? "strftime('%Y-%m-%d %H:%M', created_at)"
                : "to_char(created_at,'YYYY-MM-DD HH24:MI')";
            $phone = trim((string)($_GET['phone'] ?? ''));
            $status = trim((string)($_GET['status'] ?? ''));
            $where = '1=1';
            $params = [];
            if ($phone !== '') {
                $digits = preg_replace('/\D+/', '', $phone);
                if (preg_match('/^\d{2,6}$/', $digits)) {
                    $where .= ' AND (customer_phone = :p OR customer_phone LIKE :p2)';
                    $params[':p'] = $digits;
                    $params[':p2'] = $digits . '@%';
                } else {
                    $where .= ' AND (customer_phone LIKE :q OR customer_phone LIKE :t)';
                    $params[':q'] = '%' . $phone . '%';
                    $params[':t'] = '%' . substr($digits, -9) . '%';
                }
            }
            if ($status !== '' && strcasecmp($status, 'All') !== 0) {
                $where .= ' AND status = :st';
                $params[':st'] = $status;
            }
            $casesOut = [];
            try {
                $s = $db->prepare("SELECT case_id, {$dateFmt} as created_at,
                    customer_name, customer_phone, issue_type, description, status, priority, agent_id, department
                    FROM skykin_cases WHERE {$where}
                    ORDER BY created_at DESC LIMIT 200");
                $s->execute($params);
                $casesOut = $s->fetchAll(PDO::FETCH_ASSOC);
            } catch (Throwable $eList) {
                $s = $db->prepare("SELECT case_id, created_at,
                    customer_name, customer_phone, issue_type, description, status, priority, agent_id
                    FROM skykin_cases WHERE {$where}
                    ORDER BY created_at DESC LIMIT 200");
                $s->execute($params);
                $casesOut = $s->fetchAll(PDO::FETCH_ASSOC);
            }
            $flags = JSON_UNESCAPED_UNICODE;
            if (defined('JSON_INVALID_UTF8_SUBSTITUTE')) {
                $flags |= JSON_INVALID_UTF8_SUBSTITUTE;
            }
            $json = json_encode([
                'ok' => true,
                'synced_from_journey' => $synced,
                'cases' => $casesOut,
            ], $flags);
            if (!is_string($json) || $json === '') {
                $json = json_encode(['ok' => true, 'cases' => [], 'error' => 'json_encode']);
            }
            echo $json;
            exit;
        }

        // Create / update case from wrap-up (reason + outcome/status)
        if ($_GET['api'] === 'case_save' && $_SERVER['REQUEST_METHOD'] === 'POST') {
            skykin_crm_ensure_cases($db);
            $body = json_decode(file_get_contents('php://input'), true);
            if (!is_array($body)) {
                echo json_encode(['ok' => false, 'error' => 'Invalid JSON']);
                exit;
            }
            $rawPhone = trim((string)($body['phone'] ?? ''));
            $digits = preg_replace('/\D+/', '', $rawPhone);
            if (preg_match('/^\d{2,6}$/', $digits)) {
                $ph = $digits;
            } else {
                $ph = skykin_normalize_phone_storage($rawPhone);
            }
            $reason = trim((string)($body['reason'] ?? $body['issue_type'] ?? ''));
            $notes = trim((string)($body['notes'] ?? $body['description'] ?? ''));
            $outcome = trim((string)($body['outcome'] ?? ''));
            $status = trim((string)($body['status'] ?? ''));
            if ($status === '' && $outcome !== '') {
                $status = skykin_crm_outcome_to_case_status($outcome);
            }
            if ($status === '') {
                $status = 'Open';
            }
            $name = trim((string)($body['customer_name'] ?? ''));
            $agent = trim((string)($body['agent_id'] ?? ($_SESSION['username'] ?? '')));
            $priority = trim((string)($body['priority'] ?? 'Medium'));
            if ($priority === '') {
                $priority = 'Medium';
            }
            if ($ph === '' || $reason === '') {
                echo json_encode(['ok' => false, 'error' => 'phone and reason required']);
                exit;
            }
            if ($name === '') {
                $c = skykin_crm_find_contact($db, $ph);
                $name = trim((string)($c['full_name'] ?? ''));
                if ($name === '') {
                    $name = $ph;
                }
            }
            $desc = $notes !== '' ? $notes : ($outcome !== '' ? ('Outcome: ' . $outcome) : $reason);

            // Each wrap-up = its own case row (reason + status), do not collapse into one open case
            $db->prepare("INSERT INTO skykin_cases
                (customer_name, customer_phone, issue_type, description, status, priority, agent_id, department)
                VALUES (:n,:p,:r,:d,:st,:pr,:a,'Voice')")
                ->execute([
                    ':n' => $name,
                    ':p' => $ph,
                    ':r' => $reason,
                    ':d' => $desc,
                    ':st' => $status,
                    ':pr' => $priority,
                    ':a' => $agent,
                ]);
            $newId = (int)$db->lastInsertId();
            echo json_encode(['ok' => true, 'case_id' => $newId, 'updated' => false, 'status' => $status]);
            exit;
        }

        // Knowledge base — list / search articles
        if ($_GET['api'] === 'knowledge') {
            skykin_crm_ensure_knowledge($db);
            try {
                skykin_crm_seed_knowledge($db);
            } catch (Throwable $e) { /* ignore */ }
            $isSqlite = ($db->getAttribute(PDO::ATTR_DRIVER_NAME) === 'sqlite');
            $dateFmt = $isSqlite
                ? "strftime('%Y-%m-%d %H:%M', updated_at)"
                : "to_char(updated_at,'YYYY-MM-DD HH24:MI')";
            $q = trim((string)($_GET['q'] ?? $_GET['search'] ?? ''));
            $id = (int)($_GET['id'] ?? 0);
            if ($id > 0) {
                $s = $db->prepare("SELECT article_id, title, tag, body, keywords, {$dateFmt} as updated_at
                    FROM skykin_knowledge WHERE article_id = :id LIMIT 1");
                $s->execute([':id' => $id]);
                $row = $s->fetch(PDO::FETCH_ASSOC);
                echo json_encode(['ok' => true, 'article' => $row ?: null]);
                exit;
            }
            if ($q !== '') {
                $like = '%' . $q . '%';
                $s = $db->prepare("SELECT article_id, title, tag, keywords, {$dateFmt} as updated_at,
                    SUBSTR(body, 1, 160) as excerpt
                    FROM skykin_knowledge
                    WHERE title LIKE :q OR body LIKE :q OR COALESCE(keywords,'') LIKE :q
                    ORDER BY updated_at DESC LIMIT 50");
                $s->execute([':q' => $like]);
            } else {
                $s = $db->query("SELECT article_id, title, tag, keywords, {$dateFmt} as updated_at,
                    SUBSTR(body, 1, 160) as excerpt
                    FROM skykin_knowledge ORDER BY updated_at DESC LIMIT 50");
            }
            echo json_encode(['ok' => true, 'articles' => $s->fetchAll(PDO::FETCH_ASSOC)]);
            exit;
        }

        if ($_GET['api'] === 'knowledge_save' && $_SERVER['REQUEST_METHOD'] === 'POST') {
            if (!skykin_user_in_groups(['admin', 'superadmin', 'supervisor'])) {
                http_response_code(403);
                echo json_encode(['ok' => false, 'error' => 'Access denied']);
                exit;
            }
            skykin_crm_ensure_knowledge($db);
            $body = json_decode(file_get_contents('php://input'), true);
            if (!is_array($body)) {
                echo json_encode(['ok' => false, 'error' => 'Invalid JSON']);
                exit;
            }
            $id = (int)($body['article_id'] ?? 0);
            $title = trim((string)($body['title'] ?? ''));
            $tag = trim((string)($body['tag'] ?? 'Guide')) ?: 'Guide';
            $kb = trim((string)($body['body'] ?? ''));
            $kw = trim((string)($body['keywords'] ?? ''));
            if ($title === '' || $kb === '') {
                echo json_encode(['ok' => false, 'error' => 'Title and body required']);
                exit;
            }
            if ($id > 0) {
                $db->prepare("UPDATE skykin_knowledge SET title=:t, tag=:g, body=:b, keywords=:k, updated_at=NOW() WHERE article_id=:id")
                    ->execute([':t' => $title, ':g' => $tag, ':b' => $kb, ':k' => $kw, ':id' => $id]);
                echo json_encode(['ok' => true, 'article_id' => $id, 'updated' => true]);
                exit;
            }
            $db->prepare("INSERT INTO skykin_knowledge (title, tag, body, keywords) VALUES (:t,:g,:b,:k)")
                ->execute([':t' => $title, ':g' => $tag, ':b' => $kb, ':k' => $kw]);
            echo json_encode(['ok' => true, 'article_id' => (int)$db->lastInsertId(), 'updated' => false]);
            exit;
        }

        // Update case status only
        if ($_GET['api'] === 'case_status' && $_SERVER['REQUEST_METHOD'] === 'POST') {
            skykin_crm_ensure_cases($db);
            $body = json_decode(file_get_contents('php://input'), true);
            if (!is_array($body)) {
                echo json_encode(['ok' => false, 'error' => 'Invalid JSON']);
                exit;
            }
            $caseId = (int)($body['case_id'] ?? 0);
            $status = trim((string)($body['status'] ?? ''));
            $allowed = ['Open', 'Follow-up', 'Escalated', 'In Progress', 'Resolved', 'Closed', 'Received', 'Pending'];
            if ($caseId <= 0 || $status === '' || !in_array($status, $allowed, true)) {
                echo json_encode(['ok' => false, 'error' => 'Invalid case_id or status']);
                exit;
            }
            $db->prepare("UPDATE skykin_cases SET status = :st WHERE case_id = :id")
                ->execute([':st' => $status, ':id' => $caseId]);
            echo json_encode(['ok' => true, 'case_id' => $caseId, 'status' => $status]);
            exit;
        }

        // Seed full mockup journey for a phone (Selam-style demo)
        if ($_GET['api'] === 'journey_seed' && $_SERVER['REQUEST_METHOD'] === 'POST') {
            skykin_crm_ensure_contacts($db);
            skykin_crm_ensure_journey($db);
            $body = json_decode(file_get_contents('php://input'), true);
            if (!is_array($body)) {
                echo json_encode(['ok' => false, 'error' => 'Invalid JSON']);
                exit;
            }
            $ph = skykin_normalize_phone_storage((string)($body['phone'] ?? '+251911234567'));
            $name = trim((string)($body['full_name'] ?? 'Selam T.'));
            if ($ph === '') {
                echo json_encode(['ok' => false, 'error' => 'phone required']);
                exit;
            }
            // Upsert contact profile for demo
            $ex = $db->prepare("SELECT contact_id FROM skykin_contacts WHERE phone = :p LIMIT 1");
            $ex->execute([':p' => $ph]);
            $id = $ex->fetchColumn();
            if ($id) {
                $db->prepare("UPDATE skykin_contacts SET full_name=:n, account_type='Gold', language='Amharic',
                    fayda_verified=1, csat=5.0, sentiment='Neutral',
                    products='Prepaid plan | telebirr wallet',
                    notes='Three contacts this week about SIM and telebirr. Identity verified with Fayda.',
                    updated_at=NOW()
                    WHERE contact_id=:id")->execute([':n' => $name, ':id' => $id]);
            } else {
                try {
                    $db->prepare("INSERT INTO skykin_contacts
                        (phone,full_name,language,account_type,notes,fayda_verified,csat,sentiment,products)
                        VALUES (:p,:n,'Amharic','Gold','Three contacts this week about SIM and telebirr. Identity verified with Fayda.',1,5.0,'Neutral','Prepaid plan | telebirr wallet')")
                        ->execute([':p' => $ph, ':n' => $name]);
                } catch (Throwable $e) {
                    // SQLite NOW() may fail on updated_at path above only
                }
            }
            $db->prepare("DELETE FROM skykin_journey_events WHERE phone = :p")->execute([':p' => $ph]);
            $ins = $db->prepare("INSERT INTO skykin_journey_events (phone, event_at, channel, summary) VALUES (:p,:t,:c,:s)");
            $demo = [
                [date('Y-m-d') . ' 10:12:00', 'Voice', 'Lost phone, asks for SIM swap'],
                [date('Y-m-d') . ' 09:40:00', 'Web chat', 'Bot shared the SIM swap article'],
                [date('Y-m-d', strtotime('-1 day')) . ' 16:20:00', 'WhatsApp', 'Asked about telebirr limit'],
                [date('Y-m-d', strtotime('-3 day')) . ' 11:05:00', 'App', 'Viewed data packages'],
                [date('Y-m-d', strtotime('-7 day')) . ' 14:00:00', 'Shop', 'SIM registered with Fayda'],
                [date('Y-m-d', strtotime('-30 day')) . ' 09:00:00', 'SMS survey', 'CSAT 5 out of 5'],
            ];
            foreach ($demo as $d) {
                $ins->execute([':p' => $ph, ':t' => $d[0], ':c' => $d[1], ':s' => $d[2]]);
            }
            try {
                $chk = $db->prepare("SELECT COUNT(*) FROM skykin_cases WHERE customer_phone = :p AND LOWER(COALESCE(status,'')) NOT IN ('closed','resolved')");
                $chk->execute([':p' => $ph]);
                if ((int)$chk->fetchColumn() === 0) {
                    $db->prepare("INSERT INTO skykin_cases (customer_name, customer_phone, issue_type, description, status, priority)
                        VALUES (:n,:p,'SIM replacement','Lost phone — SIM swap','Open','High')")
                        ->execute([':n' => $name, ':p' => $ph]);
                }
            } catch (Throwable $e) { /* ignore */ }
            echo json_encode(['ok' => true, 'phone' => $ph, 'events' => count($demo)]);
            exit;
        }

        // AI summary refresh for Customer 360 (Gemini/local if configured)
        if ($_GET['api'] === 'ai_summary' && $_SERVER['REQUEST_METHOD'] === 'POST') {
            $body = json_decode(file_get_contents('php://input'), true);
            if (!is_array($body)) {
                echo json_encode(['ok' => false, 'error' => 'Invalid JSON']);
                exit;
            }
            $phone = (string)($body['phone'] ?? '');
            $payload = skykin_crm_build_360($db, $phone, skykin_crm_find_contact($db, $phone));
            $summary = (string)($payload['ai_summary'] ?? '');
            $next = (string)($payload['next_best_action'] ?? '');
            $provider = 'rules';
            if (is_file(__DIR__ . '/skykin_ai.php')) {
                require_once __DIR__ . '/skykin_ai.php';
                if (function_exists('skykin_ai_ready') && skykin_ai_ready() && function_exists('skykin_ai_chat_json')) {
                    $journeyLines = [];
                    foreach (array_slice($payload['journey'] ?? [], 0, 12) as $j) {
                        $journeyLines[] = trim(($j['event_at'] ?? '') . ' | ' . ($j['channel'] ?? '') . ': ' . ($j['summary'] ?? ''));
                    }
                    $sys = 'You are a call-center coach for Ethio Telecom SkyConnect. '
                        . 'Return JSON only: {"summary":"2 short sentences","next_best_action":"one imperative sentence"}. '
                        . 'Be specific to SIM, telebirr, Fayda when present. Do not invent facts.';
                    $user = "Customer: " . ($payload['full_name'] ?? '') . "\nPhone: {$phone}\n"
                        . "Products: " . ($payload['products'] ?? '') . "\n"
                        . "Fayda: " . (!empty($payload['fayda_verified']) ? 'yes' : 'no') . "\n"
                        . "Open cases: " . (int)($payload['open_case_count'] ?? 0) . "\n"
                        . "Journey:\n" . implode("\n", $journeyLines);
                    $ai = skykin_ai_chat_json($sys, $user);
                    if (!empty($ai['ok']) && is_array($ai['data'] ?? null)) {
                        $d = $ai['data'];
                        if (!empty($d['summary'])) {
                            $summary = (string)$d['summary'];
                        }
                        if (!empty($d['next_best_action'])) {
                            $next = (string)$d['next_best_action'];
                        } elseif (!empty($d['next'])) {
                            $next = (string)$d['next'];
                        }
                        $provider = (string)($ai['provider'] ?? 'skykin_ai');
                    }
                }
            }
            echo json_encode([
                'ok' => true,
                'ai_summary' => $summary,
                'next_best_action' => $next,
                'provider' => $provider,
            ]);
            exit;
        }

        // List all contacts
        if ($_GET['api'] === 'list') {
            $search = $_GET['search'] ?? '';
            $where  = '1=1';
            $params = [];
            $isSQLite = ($db->getAttribute(PDO::ATTR_DRIVER_NAME) === 'sqlite');
            $likeOp = $isSQLite ? 'LIKE' : 'ILIKE';
            if ($search) {
                $where = "full_name {$likeOp} :q OR phone {$likeOp} :q OR company {$likeOp} :q OR email {$likeOp} :q";
                $params[':q'] = '%'.$search.'%';
            }
            $s = $db->prepare("SELECT * FROM skykin_contacts WHERE $where ORDER BY full_name LIMIT 200");
            $s->execute($params);
            echo json_encode($s->fetchAll(PDO::FETCH_ASSOC));
            exit;
        }

        // Save / update contact
        if ($_GET['api'] === 'save' && $_SERVER['REQUEST_METHOD'] === 'POST') {
            skykin_crm_ensure_contacts($db);
            $body = json_decode(file_get_contents('php://input'), true);
            $id   = $body['contact_id'] ?? null;
            $isSQLite = ($db->getAttribute(PDO::ATTR_DRIVER_NAME) === 'sqlite');
            $nowFunc = $isSQLite ? "datetime('now')" : "NOW()";
            $rawPh = trim((string)($body['phone'] ?? ''));
            $digPh = preg_replace('/\D+/', '', $rawPh);
            $ph = preg_match('/^\d{2,6}$/', $digPh) ? $digPh : skykin_normalize_phone_storage($rawPh);
            $rawAp = trim((string)($body['alt_phone'] ?? ''));
            $digAp = preg_replace('/\D+/', '', $rawAp);
            $ap = $rawAp === '' ? '' : (preg_match('/^\d{2,6}$/', $digAp) ? $digAp : skykin_normalize_phone_storage($rawAp));
            $fn = trim((string)($body['full_name'] ?? ''));
            if ($ph === '' || $fn === '') {
                echo json_encode(['ok' => false, 'error' => 'Name and phone are required']);
                exit;
            }
            $fayda = !empty($body['fayda_verified']) ? 1 : 0;
            $csat = isset($body['csat']) && $body['csat'] !== '' && $body['csat'] !== null
                ? (float)$body['csat'] : null;
            $sentiment = trim((string)($body['sentiment'] ?? 'Neutral'));
            if ($sentiment === '') $sentiment = 'Neutral';
            $products = trim((string)($body['products'] ?? ''));
            $params = [
                ':ph' => $ph,
                ':ap' => $ap,
                ':fn' => $fn,
                ':em' => trim((string)($body['email'] ?? '')),
                ':co' => trim((string)($body['company'] ?? '')),
                ':la' => trim((string)($body['language'] ?? 'Amharic')) ?: 'Amharic',
                ':at' => trim((string)($body['account_type'] ?? 'Customer')) ?: 'Customer',
                ':no' => trim((string)($body['notes'] ?? '')),
                ':fy' => $fayda,
                ':cs' => $csat,
                ':se' => $sentiment,
                ':pr' => $products,
            ];
            if ($id) {
                $s = $db->prepare("UPDATE skykin_contacts SET
                    phone=:ph, alt_phone=:ap, full_name=:fn, email=:em,
                    company=:co, language=:la, account_type=:at, notes=:no,
                    fayda_verified=:fy, csat=:cs, sentiment=:se, products=:pr,
                    updated_at={$nowFunc} WHERE contact_id=:id");
                $params[':id'] = (int)$id;
                $s->execute($params);
                echo json_encode(['ok'=>true,'action'=>'updated','contact_id'=>(int)$id,'phone'=>$ph]);
            } else {
                $s = $db->prepare("INSERT INTO skykin_contacts
                    (phone,alt_phone,full_name,email,company,language,account_type,notes,fayda_verified,csat,sentiment,products)
                    VALUES (:ph,:ap,:fn,:em,:co,:la,:at,:no,:fy,:cs,:se,:pr)");
                $s->execute($params);
                $newId = (int)$db->lastInsertId();
                echo json_encode(['ok'=>true,'action'=>'created','contact_id'=>$newId,'phone'=>$ph]);
            }
            exit;
        }

        // Delete contact
        if ($_GET['api'] === 'delete' && isset($_GET['id'])) {
            $id = (int)$_GET['id'];
            if ($id <= 0) {
                echo json_encode(['ok' => false, 'error' => 'Invalid contact id']);
                exit;
            }
            $s = $db->prepare('DELETE FROM skykin_contacts WHERE contact_id=:id');
            $s->execute([':id' => $id]);
            echo json_encode(['ok' => true, 'deleted' => $s->rowCount()]);
            exit;
        }

    } catch (Throwable $e) { echo json_encode(['ok' => false, 'error' => $e->getMessage(), 'cases' => []]); }
    exit;
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<?php echo skykin_favicon_tag(); ?>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sky Connect – CRM</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',sans-serif;background:#f0f2f5;color:#333;min-height:100vh}

.topbar{background:linear-gradient(135deg,#0047AB,#00B4D8);border-bottom:1px solid #e0e0e0;padding:0 24px;height:56px;
  display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100}
.topbar-left{display:flex;align-items:center;gap:20px}
.brand{font-weight:700;font-size:17px;color:#58a6ff;letter-spacing:.5px}
.brand span{color:#333;font-weight:400}
.nav-links{display:flex;gap:4px}
.nav-links a{color:#888;text-decoration:none;padding:6px 14px;border-radius:6px;font-size:13px;transition:.2s}
.nav-links a:hover,.nav-links a.active{background:#f0f2f5;color:#333}
.topbar-right{display:flex;align-items:center;gap:12px;font-size:13px;color:#888}
.user-pill{background:#f0f2f5;padding:5px 12px;border-radius:20px;color:#333;font-size:12px}

.toolbar{background:#ffffff;border-bottom:1px solid #e0e0e0;padding:12px 24px;
  display:flex;align-items:center;gap:12px}
.toolbar input{background:#f0f2f5;border:1px solid #e0e0e0;color:#333;
  padding:7px 12px;border-radius:6px;font-size:13px;width:280px}
.toolbar input:focus{outline:none;border-color:#58a6ff}
.btn-primary{background:#238636;color:#fff;border:none;padding:7px 16px;border-radius:6px;
  cursor:pointer;font-size:13px;font-weight:500}
.btn-primary:hover{background:#2ea043}
.btn-sec{background:#f0f2f5;color:#333;border:1px solid #e0e0e0;padding:7px 14px;
  border-radius:6px;cursor:pointer;font-size:13px}
.btn-sec:hover{background:#e0e0e0}

.layout{display:grid;grid-template-columns:1fr 400px;height:calc(100vh - 110px)}
.contact-list{overflow-y:auto;border-right:1px solid #e0e0e0}
.contact-panel{overflow-y:auto;background:#ffffff;padding:24px}

.contact-item{padding:14px 16px;border-bottom:1px solid #21262d;cursor:pointer;transition:.15s}
.contact-item:hover{background:#f0f2f5}
.contact-item.selected{background:#388bfd18;border-left:3px solid #58a6ff}
.ct-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;gap:8px}
.ct-actions{display:flex;align-items:center;gap:6px;flex-shrink:0}
.btn-icon-delete{background:transparent;border:none;color:#dc2626;cursor:pointer;padding:4px 6px;border-radius:6px;font-size:14px;line-height:1}
.btn-icon-delete:hover{background:#fee2e2}
.form-actions{display:grid;grid-template-columns:1fr auto;gap:10px;margin-top:4px;align-items:stretch}
.form-actions .btn-save{margin-top:0}
.form-actions .btn-delete{margin-top:0;width:auto;min-width:120px;white-space:nowrap}
.ct-name{font-size:14px;font-weight:600}
.ct-badge{padding:2px 8px;border-radius:10px;font-size:10px;font-weight:600}
.ct-badge.VIP{background:#d2992233;color:#d29922}
.ct-badge.Customer{background:#388bfd22;color:#58a6ff}
.ct-meta{font-size:11px;color:#888;display:flex;gap:12px}
.lang-dot{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:4px}
.lang-Amharic{background:#f85149}
.lang-English{background:#3fb950}
.lang-Oromo{background:#58a6ff}
.lang-Other{background:#d29922}

/* Panel */
.panel-title{font-size:15px;font-weight:600;margin-bottom:16px}
.form-field{margin-bottom:14px}
.form-field label{display:block;font-size:11px;color:#888;margin-bottom:5px;text-transform:uppercase;letter-spacing:.4px}
.form-field input,.form-field select,.form-field textarea{
  width:100%;background:#f0f2f5;border:1px solid #e0e0e0;color:#333;
  padding:8px 10px;border-radius:6px;font-family:inherit;font-size:13px}
.form-field input:focus,.form-field select:focus,.form-field textarea:focus{outline:none;border-color:#58a6ff}
.form-field textarea{resize:vertical;min-height:70px}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.btn-save{width:100%;background:#238636;color:#fff;border:none;padding:11px;border-radius:8px;
  cursor:pointer;font-size:14px;font-weight:600;margin-top:4px}
.btn-save:hover{background:#2ea043}
.btn-delete{background:#da363322;color:#f85149;border:1px solid #da363344;padding:8px 14px;
  border-radius:6px;cursor:pointer;font-size:12px;margin-top:8px;width:100%}
.btn-delete:hover{background:#f8514922}

.call-history{margin-top:20px}
.call-history h4{font-size:12px;color:#888;margin-bottom:10px;text-transform:uppercase;letter-spacing:.5px}
.ch-row{display:flex;justify-content:space-between;align-items:center;
  padding:8px 10px;background:#f0f2f5;border-radius:6px;margin-bottom:6px;font-size:12px}
.ch-dir{padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600}
.ch-dir.inbound{background:#388bfd22;color:#58a6ff}
.ch-dir.outbound{background:#f0883e22;color:#f0883e}
.empty-state{text-align:center;padding:40px;color:#888;font-size:13px}
.count-badge{background:#f0f2f5;color:#888;padding:3px 10px;border-radius:10px;font-size:12px;margin-left:8px}

/* SkyKin light workspace */
:root{
  --sk-blue:#2563eb;--sk-blue-soft:#eff6ff;--sk-text:#172033;
  --sk-muted:#64748b;--sk-canvas:#f6f8fb;--sk-surface:#fff;
  --sk-line:#e8edf3;--sk-shadow:0 8px 28px rgba(15,23,42,.06)
}
body{background:var(--sk-canvas);color:var(--sk-text);font-size:14px}
.topbar{height:60px;padding:0 24px;background:linear-gradient(135deg,#0047ab,#00b4d8);border:0;box-shadow:0 2px 8px rgba(0,0,0,.2)}
.topbar-left{gap:28px}
.brand{color:#fff;font-size:18px;font-weight:700;letter-spacing:1px;white-space:nowrap}
.brand .brand-sky{color:#00e5ff}
.brand .role-badge{margin-left:10px;padding:2px 10px;background:rgba(255,255,255,.2);border-radius:20px;color:#fff;font-size:11px;font-weight:600;letter-spacing:0}
.nav-links{gap:6px}
.nav-links a{color:rgba(255,255,255,.82);padding:8px 12px;border-radius:7px;font-size:12px;font-weight:600}
.nav-links a:hover{background:rgba(255,255,255,.12);color:#fff}
.nav-links a.active{background:rgba(255,255,255,.2);color:#fff}
.topbar-right{color:rgba(255,255,255,.86)}
.user-pill{background:rgba(255,255,255,.14);color:#fff;padding:7px 12px;border-radius:9px}
.topbar-right a{color:#fff!important;font-weight:600;opacity:.85}
.topbar-right a:hover{opacity:1}

.toolbar{min-height:62px;padding:11px 28px;background:var(--sk-canvas);border:0;gap:10px}
.toolbar input{height:38px;width:min(360px,45vw);background:#fff;border:1px solid #dbe3ec;color:var(--sk-text);padding:7px 12px;border-radius:9px}
.toolbar input:focus{outline:0;border-color:#93b4f4;box-shadow:0 0 0 3px rgba(37,99,235,.09)}
.btn-primary{height:38px;background:var(--sk-blue);padding:0 18px;border-radius:9px;font-weight:650;box-shadow:0 3px 8px rgba(37,99,235,.16)}
.btn-primary:hover{background:#1d4ed8}
.count-badge{margin-left:2px;background:#e8eef7;color:#526277;padding:5px 10px;font-weight:650}

.layout{grid-template-columns:minmax(0,1fr) 420px;gap:14px;height:calc(100vh - 126px);padding:0 20px 18px}
.contact-list,.contact-panel{background:var(--sk-surface);border:0;border-radius:14px;box-shadow:var(--sk-shadow)}
.contact-list{padding:8px;overflow-y:auto}
.contact-panel{padding:22px}
.contact-item{margin:3px 0;padding:13px 14px;border:0;border-radius:10px}
.contact-item:hover{background:#f8fafc}
.contact-item.selected{background:var(--sk-blue-soft);border:0;box-shadow:inset 3px 0 var(--sk-blue)}
.ct-name{color:var(--sk-text);font-size:13px}
.ct-meta{color:var(--sk-muted)}
.ct-badge{padding:3px 8px}
.ct-badge.VIP{background:#fff7ed;color:#c2410c}
.ct-badge.Customer{background:#eff6ff;color:#2563eb}
.ct-badge.Prospect{background:#f5f3ff;color:#7c3aed}
.ct-badge.Partner{background:#f0fdf4;color:#15803d}

.panel-title{font-size:17px;color:var(--sk-text);margin-bottom:20px}
.form-field{margin-bottom:15px}
.form-field label{color:var(--sk-muted);font-size:10px;font-weight:700}
.form-field input,.form-field select,.form-field textarea{background:#fff;border:1px solid #dbe3ec;color:var(--sk-text);padding:9px 11px;border-radius:9px}
.form-field input:focus,.form-field select:focus,.form-field textarea:focus{border-color:#93b4f4;box-shadow:0 0 0 3px rgba(37,99,235,.09)}
.form-field textarea{min-height:82px}
.form-row{gap:12px}
.btn-save{background:var(--sk-blue);border-radius:10px;box-shadow:0 3px 8px rgba(37,99,235,.16)}
.btn-save:hover{background:#1d4ed8}
.btn-delete{background:#fff5f5;color:#dc2626;border:0;border-radius:10px}
.btn-delete:hover{background:#fee2e2}
.call-history{margin-top:24px;padding-top:0}
.call-history h4{color:var(--sk-muted);font-size:10px;font-weight:700}
.ch-row{background:#f8fafc;border-radius:9px;padding:9px 11px}
.empty-state{color:var(--sk-muted)}

body.embed-mode{background:var(--sk-canvas)}
body.embed-mode .topbar{display:none}
body.embed-mode .layout{height:calc(100vh - 62px)}
body.embed-mode .crm-footer{display:none}

@media(max-width:850px){
  .topbar{padding:0 14px}.brand span,.topbar-right .user-pill{display:none}
  .nav-links{overflow-x:auto}.nav-links a{white-space:nowrap;padding:8px}
  .toolbar{padding:10px 14px}.layout{grid-template-columns:1fr;height:auto;padding:0 10px 12px}
  .contact-list{max-height:42vh}.contact-panel{min-height:50vh}.form-row{grid-template-columns:1fr}
}
</style>
</head>
<body<?php echo $embed ? ' class="embed-mode"' : ''; ?>>

<?php if (!$embed): ?>
<div class="topbar">
  <div class="topbar-left">
    <div class="brand"><span class="brand-sky">Sky</span> Connect <span class="role-badge">SUPERVISOR</span></div>
    <nav class="nav-links">
      <a href="/app/agent_dashboard/supervisor.php">Supervisor</a>
      <a href="/app/agent_dashboard/reports.php">Reports</a>
      <a href="/app/agent_dashboard/evaluation.php">Evaluation</a>
      <a href="/app/agent_dashboard/crm.php" class="active">CRM</a>
      <a href="/app/agent_dashboard/billing.php">Billing</a>
      <a href="/app/agent_dashboard/index.php">Agent View</a>
    </nav>
  </div>
  <div class="topbar-right">
    <div class="user-pill"><?php echo htmlspecialchars($logged_in_user); ?></div>
    <a href="/logout.php" style="color:#f85149;font-size:12px;text-decoration:none">Logout</a>
  </div>
</div>
<?php endif; ?>

<div class="toolbar">
  <input type="text" id="searchBox" placeholder="Search by name, phone, company..." oninput="loadContacts()" autofocus>
  <button class="btn-primary" onclick="newContact()">+ New Contact</button>
  <span id="contactCount" class="count-badge">0</span>
</div>

<div class="layout">
  <div class="contact-list" id="contactList">
    <div class="empty-state">Loading...</div>
  </div>

  <div class="contact-panel">
    <div id="panelEmpty" class="empty-state" style="margin-top:60px">
      <div style="font-size:32px;margin-bottom:12px">&#128100;</div>
      <div style="font-weight:600;color:#333;margin-bottom:6px">Select a contact</div>
      <div>Click a contact to view or edit</div>
    </div>
    <div id="panelForm" style="display:none">
      <div class="panel-title" id="panelTitle">Contact Details</div>
      <input type="hidden" id="fId">
      <div class="form-row">
        <div class="form-field"><label>Full Name *</label><input id="fName" placeholder="Full name"></div>
        <div class="form-field"><label>Account Type</label>
          <select id="fType"><option>Customer</option><option>VIP</option><option>Prospect</option><option>Partner</option></select>
        </div>
      </div>
      <div class="form-row">
        <div class="form-field"><label>Phone *</label><input id="fPhone" placeholder="+251911000000"></div>
        <div class="form-field"><label>Alt Phone</label><input id="fAlt" placeholder="Optional"></div>
      </div>
      <div class="form-row">
        <div class="form-field"><label>Email</label><input id="fEmail" type="email" placeholder="email@example.com"></div>
        <div class="form-field"><label>Company</label><input id="fCompany" placeholder="Company name"></div>
      </div>
      <div class="form-field"><label>Preferred Language</label>
        <select id="fLang">
          <option>English</option><option>Amharic</option><option>Oromo</option><option>Tigrinya</option><option>Other</option>
        </select>
      </div>
      <div class="form-field"><label>Notes</label><textarea id="fNotes" placeholder="Any notes about this customer..."></textarea></div>
      <div class="form-actions">
        <button class="btn-save" type="button" onclick="saveContact()">Save Contact</button>
        <button class="btn-delete" type="button" id="btnDelete" onclick="deleteContact()" style="display:none">Delete</button>
      </div>

      <!-- Call history for this contact -->
      <div class="call-history" id="callHistorySection" style="display:none">
        <h4>Recent Call History</h4>
        <div id="callHistoryList"></div>
      </div>
    </div>
  </div>
</div>
<div class="crm-footer" style="text-align:center;font-size:11px;color:#aaa;padding:16px 24px">Sky Connect &copy; <?php echo date('Y'); ?> | Powered by SkyKin Technology</div>

<script>
const DOMAIN = '<?php echo $domain; ?>';
let allContacts = [];

async function loadContacts() {
    const q = document.getElementById('searchBox').value.trim();
    const resp = await fetch(`crm.php?api=list&domain=${DOMAIN}&search=${encodeURIComponent(q)}`);
    allContacts = await resp.json();
    document.getElementById('contactCount').textContent = allContacts.length;
    const list = document.getElementById('contactList');
    if (!allContacts.length) { list.innerHTML='<div class="empty-state">No contacts found</div>'; return; }
    const langColors = {Amharic:'#f85149',English:'#3fb950',Oromo:'#58a6ff',Tigrinya:'#d29922',Other:'#8b949e'};
    list.innerHTML = allContacts.map(c => `
      <div class="contact-item" data-id="${c.contact_id}" onclick="editContactById(${c.contact_id})">
        <div class="ct-top">
          <span class="ct-name">${escapeHtml(c.full_name)}</span>
          <div class="ct-actions">
            <span class="ct-badge ${escapeHtml(c.account_type)}">${escapeHtml(c.account_type)}</span>
            <button type="button" class="btn-icon-delete" title="Delete contact"
              onclick="deleteContactById(${c.contact_id}, event)">&#128465;</button>
          </div>
        </div>
        <div class="ct-meta">
          <span>${escapeHtml(c.phone)}</span>
          <span><span class="lang-dot lang-${escapeHtml(c.language)}" style="background:${langColors[c.language]||'#8b949e'}"></span>${escapeHtml(c.language)}</span>
          ${c.company?`<span>${escapeHtml(c.company)}</span>`:''}
        </div>
      </div>`).join('');
}

function escapeHtml(s) {
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function editContactById(id) {
    const c = allContacts.find(x => String(x.contact_id) === String(id));
    if (!c) return;
    editContact(c);
}

function newContact() {
    document.querySelectorAll('.contact-item').forEach(e=>e.classList.remove('selected'));
    document.getElementById('panelEmpty').style.display = 'none';
    document.getElementById('panelForm').style.display  = 'block';
    document.getElementById('panelTitle').textContent   = 'New Contact';
    document.getElementById('fId').value      = '';
    document.getElementById('fName').value    = '';
    document.getElementById('fPhone').value   = '';
    document.getElementById('fAlt').value     = '';
    document.getElementById('fEmail').value   = '';
    document.getElementById('fCompany').value = '';
    document.getElementById('fNotes').value   = '';
    document.getElementById('fType').value    = 'Customer';
    document.getElementById('fLang').value    = 'English';
    document.getElementById('btnDelete').style.display = 'none';
    document.getElementById('callHistorySection').style.display = 'none';
}

function editContact(c) {
    if (typeof c === 'string') {
        try { c = JSON.parse(c); } catch (e) { return; }
    }
    document.querySelectorAll('.contact-item').forEach(e => {
        e.classList.toggle('selected', String(e.dataset.id) === String(c.contact_id));
    });
    document.getElementById('panelEmpty').style.display = 'none';
    document.getElementById('panelForm').style.display  = 'block';
    document.getElementById('panelTitle').textContent   = 'Edit Contact';
    document.getElementById('fId').value      = c.contact_id || '';
    document.getElementById('fName').value    = c.full_name   || '';
    document.getElementById('fPhone').value   = c.phone       || '';
    document.getElementById('fAlt').value     = c.alt_phone   || '';
    document.getElementById('fEmail').value   = c.email       || '';
    document.getElementById('fCompany').value = c.company     || '';
    document.getElementById('fNotes').value   = c.notes       || '';
    document.getElementById('fType').value    = c.account_type || 'Customer';
    document.getElementById('fLang').value    = c.language    || 'English';
    document.getElementById('btnDelete').style.display = 'block';

    // Show call history if present
    if (c.call_history && c.call_history.length > 0) {
        const list = document.getElementById('callHistoryList');
        list.innerHTML = c.call_history.map(h =>
            `<div class="ch-row">
              <span>${h.call_time}</span>
              <span class="ch-dir ${h.direction}">${h.direction}</span>
              <span>${Math.floor(h.billsec/60)}m ${h.billsec%60}s</span>
              <span style="color:#888">${h.hangup_cause||''}</span>
            </div>`).join('');
        document.getElementById('callHistorySection').style.display = 'block';
    } else {
        document.getElementById('callHistorySection').style.display = 'none';
    }
}

async function saveContact() {
    const body = {
        contact_id:   document.getElementById('fId').value || null,
        full_name:    document.getElementById('fName').value.trim(),
        phone:        document.getElementById('fPhone').value.trim(),
        alt_phone:    document.getElementById('fAlt').value.trim(),
        email:        document.getElementById('fEmail').value.trim(),
        company:      document.getElementById('fCompany').value.trim(),
        language:     document.getElementById('fLang').value,
        account_type: document.getElementById('fType').value,
        notes:        document.getElementById('fNotes').value.trim(),
    };
    if (!body.full_name || !body.phone) { alert('Name and phone are required'); return; }
    const resp = await fetch(`crm.php?api=save&domain=${DOMAIN}`,{
        method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)
    });
    const r = await resp.json();
    if (r.ok) { loadContacts(); alert(r.action === 'created' ? 'Contact created!' : 'Contact updated!'); }
    else alert('Error: '+(r.error||'Unknown'));
}

async function deleteContactById(id, ev) {
    if (ev) { ev.stopPropagation(); ev.preventDefault(); }
    if (!id) return;
    const c = allContacts.find(x => String(x.contact_id) === String(id));
    const label = c ? (c.full_name + ' (' + c.phone + ')') : ('contact #' + id);
    if (!confirm('Delete ' + label + '?')) return;
    const resp = await fetch(`crm.php?api=delete&id=${encodeURIComponent(id)}&domain=${DOMAIN}`);
    const r = await resp.json().catch(() => ({}));
    if (!r.ok) { alert('Delete failed: ' + (r.error || 'Unknown error')); return; }
    document.getElementById('panelForm').style.display = 'none';
    document.getElementById('panelEmpty').style.display = 'block';
    loadContacts();
}

async function deleteContact() {
    const id = document.getElementById('fId').value;
    await deleteContactById(id);
}

loadContacts();
</script>
<script>
<?php echo skykin_js_bootstrap(); ?>
</script>
<script src="idle_watch.js?v=20260818"></script>
</body>
</html>
