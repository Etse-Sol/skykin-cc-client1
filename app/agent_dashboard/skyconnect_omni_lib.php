<?php
/** Omnichannel threads, WhatsApp ingest, CSAT tokens. */

function sc_omni_ensure(PDO $db): void {
	$pg = ($db->getAttribute(PDO::ATTR_DRIVER_NAME) !== 'sqlite');
	$id = $pg ? 'SERIAL PRIMARY KEY' : 'INTEGER PRIMARY KEY AUTOINCREMENT';
	$ts = $pg ? 'TIMESTAMP DEFAULT NOW()' : 'DATETIME DEFAULT CURRENT_TIMESTAMP';
	$db->exec("CREATE TABLE IF NOT EXISTS skykin_omni_threads (
		thread_id $id,
		domain_name TEXT,
		channel TEXT,
		customer_key TEXT,
		customer_name TEXT,
		status TEXT DEFAULT 'open',
		agent_ext TEXT DEFAULT '',
		updated_at $ts
	)");
	$db->exec("CREATE TABLE IF NOT EXISTS skykin_omni_messages (
		msg_id $id,
		thread_id INTEGER,
		role TEXT,
		body TEXT,
		created_at $ts
	)");
	$db->exec("CREATE TABLE IF NOT EXISTS skykin_csat_tokens (
		token TEXT PRIMARY KEY,
		domain_name TEXT,
		agent_ext TEXT,
		phone TEXT,
		used INTEGER DEFAULT 0,
		created_at $ts
	)");
}

function sc_omni_bot_reply(PDO $db, string $text): string {
	if (!function_exists('skykin_crm_search_knowledge')) {
		return '';
	}
	$hit = skykin_crm_search_knowledge($db, $text);
	$art = $hit['articles'][0] ?? null;
	if (!$art || (int)($art['score'] ?? 0) < 12) {
		return '';
	}
	$title = trim((string)($art['title'] ?? ''));
	$ex = trim((string)($art['excerpt'] ?? ''));
	if ($title === '' && $ex === '') {
		return '';
	}
	return trim($title . ($ex !== '' ? "\n" . $ex : ''));
}

function sc_omni_thread(PDO $db, string $dom, string $channel, string $key, string $name = ''): array {
	sc_omni_ensure($db);
	$s = $db->prepare(
		"SELECT * FROM skykin_omni_threads
		 WHERE domain_name=:d AND channel=:c AND customer_key=:k AND status <> 'closed'
		 ORDER BY thread_id DESC LIMIT 1"
	);
	$s->execute([':d' => $dom, ':c' => $channel, ':k' => $key]);
	$row = $s->fetch(PDO::FETCH_ASSOC);
	if ($row) {
		return $row;
	}
	$db->prepare(
		'INSERT INTO skykin_omni_threads (domain_name, channel, customer_key, customer_name, status)
		 VALUES (:d,:c,:k,:n,\'open\')'
	)->execute([':d' => $dom, ':c' => $channel, ':k' => $key, ':n' => $name !== '' ? $name : $key]);
	$id = (int)$db->lastInsertId();
	$s = $db->prepare('SELECT * FROM skykin_omni_threads WHERE thread_id = :id');
	$s->execute([':id' => $id]);
	return $s->fetch(PDO::FETCH_ASSOC) ?: ['thread_id' => $id, 'domain_name' => $dom, 'channel' => $channel, 'customer_key' => $key, 'status' => 'open'];
}

function sc_omni_add_msg(PDO $db, int $tid, string $role, string $body): void {
	$body = trim($body);
	if ($tid < 1 || $body === '') {
		return;
	}
	$db->prepare('INSERT INTO skykin_omni_messages (thread_id, role, body) VALUES (:t,:r,:b)')
		->execute([':t' => $tid, ':r' => $role, ':b' => $body]);
	try {
		$db->prepare('UPDATE skykin_omni_threads SET updated_at = NOW() WHERE thread_id = :t')->execute([':t' => $tid]);
	} catch (Throwable $e) {
		$db->prepare("UPDATE skykin_omni_threads SET updated_at = datetime('now') WHERE thread_id = :t")->execute([':t' => $tid]);
	}
}

function sc_omni_msgs(PDO $db, int $tid): array {
	$s = $db->prepare('SELECT msg_id, role, body, created_at FROM skykin_omni_messages WHERE thread_id = :t ORDER BY msg_id ASC');
	$s->execute([':t' => $tid]);
	return $s->fetchAll(PDO::FETCH_ASSOC);
}

function sc_omni_customer_post(PDO $db, string $dom, string $channel, string $key, string $name, string $text): array {
	$th = sc_omni_thread($db, $dom, $channel, $key, $name);
	$tid = (int)$th['thread_id'];
	sc_omni_add_msg($db, $tid, 'customer', $text);
	$bot = sc_omni_bot_reply($db, $text);
	if ($bot !== '') {
		sc_omni_add_msg($db, $tid, 'bot', $bot);
	}
	return ['ok' => true, 'thread_id' => $tid, 'messages' => sc_omni_msgs($db, $tid), 'bot' => $bot];
}

function sc_omni_wa_send(string $to, string $text): void {
	$token = getenv('SKYKIN_WA_TOKEN') ?: '';
	$phoneId = getenv('SKYKIN_WA_PHONE_ID') ?: '';
	if ($token === '' || $phoneId === '' || $to === '' || $text === '') {
		return;
	}
	$payload = json_encode([
		'messaging_product' => 'whatsapp',
		'to' => preg_replace('/\D+/', '', $to),
		'type' => 'text',
		'text' => ['body' => $text],
	]);
	$ch = curl_init('https://graph.facebook.com/v21.0/' . rawurlencode($phoneId) . '/messages');
	curl_setopt_array($ch, [
		CURLOPT_POST => true,
		CURLOPT_RETURNTRANSFER => true,
		CURLOPT_TIMEOUT => 12,
		CURLOPT_HTTPHEADER => ['Authorization: Bearer ' . $token, 'Content-Type: application/json'],
		CURLOPT_POSTFIELDS => $payload,
	]);
	curl_exec($ch);
	curl_close($ch);
}

function sc_csat_make(PDO $db, string $dom, string $ext, string $phone): string {
	sc_omni_ensure($db);
	$token = bin2hex(random_bytes(16));
	$db->prepare('INSERT INTO skykin_csat_tokens (token, domain_name, agent_ext, phone) VALUES (:t,:d,:e,:p)')
		->execute([':t' => $token, ':d' => $dom, ':e' => $ext, ':p' => $phone]);
	return $token;
}

function sc_ops_wfm_forecast(PDO $db, string $dom): array {
	$te = time();
	$ts = $te - (28 * 86400);
	if (!function_exists('skykin_cdr_fetch_period')) {
		return [];
	}
	$rows = skykin_cdr_fetch_period($db, $dom, $ts, $te);
	$todayN = (int)date('N');
	$talk = 0;
	$talkN = 0;
	$bucket = [];
	foreach ($rows as $r) {
		$ep = (int)($r['start_epoch'] ?? 0);
		if ($ep < 1) {
			continue;
		}
		if ((int)date('N', $ep) !== $todayN) {
			continue;
		}
		$h = (int)date('G', $ep);
		$bucket[$h] = ($bucket[$h] ?? 0) + 1;
		$b = (int)($r['billsec'] ?? 0);
		if ($b > 0) {
			$talk += $b;
			$talkN++;
		}
	}
	$aht = $talkN > 0 ? ($talk / $talkN) : 180;
	$out = [];
	for ($h = 0; $h < 24; $h++) {
		$offered = round(($bucket[$h] ?? 0) / 4, 1);
		$hoursWork = ($offered * $aht) / 3600;
		$need = $offered < 0.3 ? 0 : (int)max(1, ceil($hoursWork * 1.25 + 0.4));
		$out[] = ['hour' => $h, 'offered' => $offered, 'agents_needed' => $need, 'aht' => (int)round($aht)];
	}
	return $out;
}
