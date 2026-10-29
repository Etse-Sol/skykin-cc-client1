<?php
/**
 * JSON ops for SkyConnect menus (schedule, QA, surveys, admin studio).
 * Does not change FreeSWITCH dialplan / media.
 */
require_once __DIR__ . '/session_bootstrap.php';
require_once __DIR__ . '/skykin_config.php';
require_once __DIR__ . '/skyconnect_omni_lib.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

skykin_require_login(true);
skykin_session_touch();
if (function_exists('session_write_close')) {
	session_write_close();
}

$op = trim((string)($_GET['op'] ?? $_GET['api'] ?? ''));
$dom = skykin_domain_param($_GET['domain'] ?? null);
$from = $_GET['from'] ?? date('Y-m-d', strtotime('-7 days'));
$to = $_GET['to'] ?? date('Y-m-d');
$ts = strtotime($from . ' 00:00:00');
$te = strtotime($to . ' 23:59:59');
$me = (string)($_SESSION['username'] ?? '');
$body = [];
if (($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
	$raw = file_get_contents('php://input');
	$decoded = json_decode((string)$raw, true);
	$body = is_array($decoded) ? $decoded : $_POST;
}

function sc_ops_groups(): array {
	$out = [];
	foreach ($_SESSION['groups'] ?? [] as $g) {
		$n = strtolower(is_array($g) ? (string)($g['group_name'] ?? '') : (string)$g);
		if ($n !== '') {
			$out[] = $n;
		}
	}
	return $out;
}

function sc_ops_need(array $allowed): void {
	$have = sc_ops_groups();
	foreach ($allowed as $a) {
		if (in_array($a, $have, true)) {
			return;
		}
	}
	try {
		$pack = skykin_app_role_from_groups(
			sc_ops_db(),
			(string)($_SESSION['user_uuid'] ?? ''),
			$_SESSION['groups'] ?? ($_SESSION['user']['groups'] ?? [])
		);
		$role = (string)($pack['role'] ?? 'agent');
		if (in_array($role, $allowed, true)) {
			return;
		}
		if (!empty($pack['is_admin']) && (in_array('admin', $allowed, true) || in_array('superadmin', $allowed, true))) {
			return;
		}
		if (!empty($pack['is_supervisor']) && in_array('supervisor', $allowed, true)) {
			return;
		}
	} catch (Throwable $e) {
		/* fall through */
	}
	http_response_code(403);
	echo json_encode(['ok' => false, 'error' => 'Access denied']);
	exit;
}

function sc_ops_db(): PDO {
	return skykin_pdo_fusionpbx();
}

function sc_ops_domain_uuid(PDO $db, string $dom): ?string {
	if (!empty($_SESSION['domain_uuid'])) {
		return (string)$_SESSION['domain_uuid'];
	}
	$s = $db->prepare('SELECT domain_uuid FROM v_domains WHERE domain_name = :d LIMIT 1');
	$s->execute([':d' => $dom]);
	$u = $s->fetchColumn();
	return $u ? (string)$u : null;
}

function sc_ops_uuid(): string {
	$data = random_bytes(16);
	$data[6] = chr((ord($data[6]) & 0x0f) | 0x40);
	$data[8] = chr((ord($data[8]) & 0x3f) | 0x80);
	$hex = bin2hex($data);
	return sprintf(
		'%s-%s-%s-%s-%s',
		substr($hex, 0, 8),
		substr($hex, 8, 4),
		substr($hex, 12, 4),
		substr($hex, 16, 4),
		substr($hex, 20, 12)
	);
}

function sc_ops_truthy($v): bool {
	if (is_bool($v)) {
		return $v;
	}
	return in_array(strtolower(trim((string)$v)), ['1', 't', 'true', 'yes', 'on'], true);
}

function sc_ops_load_users(PDO $db, string $du): array {
	$s = $db->prepare(
		"SELECT user_uuid, username, user_email, user_enabled, user_status
		 FROM v_users WHERE domain_uuid = :u ORDER BY username"
	);
	$s->execute([':u' => $du]);
	$users = $s->fetchAll(PDO::FETCH_ASSOC);
	$by = [];
	foreach ($users as $u) {
		$id = (string)$u['user_uuid'];
		$en = $u['user_enabled'];
		$by[$id] = [
			'user_uuid' => $id,
			'username' => (string)$u['username'],
			'user_email' => (string)($u['user_email'] ?? ''),
			'user_enabled' => sc_ops_truthy($en) ? 'true' : 'false',
			'user_status' => (string)($u['user_status'] ?? ''),
			'groups' => '',
			'group_list' => [],
			'extension' => '',
		];
	}
	if ($by === []) {
		return [];
	}
	$ids = array_keys($by);
	$ph = implode(',', array_fill(0, count($ids), '?'));
	try {
		$g = $db->prepare(
			"SELECT ug.user_uuid, COALESCE(NULLIF(ug.group_name,''), g.group_name) AS group_name
			 FROM v_user_groups ug
			 LEFT JOIN v_groups g ON g.group_uuid = ug.group_uuid
			 WHERE ug.user_uuid IN ($ph)"
		);
		$g->execute($ids);
		foreach ($g->fetchAll(PDO::FETCH_ASSOC) as $row) {
			$id = (string)$row['user_uuid'];
			$n = strtolower(trim((string)$row['group_name']));
			if ($n === '' || !isset($by[$id])) {
				continue;
			}
			if (!in_array($n, $by[$id]['group_list'], true)) {
				$by[$id]['group_list'][] = $n;
			}
		}
	} catch (Throwable $e) {
		/* older installs */
	}
	try {
		$e = $db->prepare(
			"SELECT eu.user_uuid, e.extension
			 FROM v_extension_users eu
			 JOIN v_extensions e ON e.extension_uuid = eu.extension_uuid
			 WHERE eu.user_uuid IN ($ph)
			 ORDER BY e.extension"
		);
		$e->execute($ids);
		foreach ($e->fetchAll(PDO::FETCH_ASSOC) as $row) {
			$id = (string)$row['user_uuid'];
			if (!isset($by[$id])) {
				continue;
			}
			$ext = (string)$row['extension'];
			$by[$id]['extension'] = $by[$id]['extension'] === '' ? $ext : ($by[$id]['extension'] . ',' . $ext);
		}
	} catch (Throwable $ex) {
		/* ignore */
	}
	$skills = [];
	try {
		$skills = sc_ops_load_user_skills($db, $du);
	} catch (Throwable $eSk) {
		$skills = [];
	}
	$out = [];
	foreach ($by as $row) {
		$row['groups'] = implode(', ', $row['group_list']);
		$row['skills'] = $skills[(string)$row['user_uuid']] ?? [];
		$out[] = $row;
	}
	return $out;
}

function sc_ops_find_group(PDO $db, string $du, string $name): ?array {
	$s = $db->prepare(
		"SELECT group_uuid, group_name FROM v_groups
		 WHERE lower(group_name) = lower(:n)
		   AND (domain_uuid = :d OR domain_uuid IS NULL)
		 ORDER BY CASE WHEN domain_uuid = :d2 THEN 0 ELSE 1 END
		 LIMIT 1"
	);
	$s->execute([':n' => $name, ':d' => $du, ':d2' => $du]);
	$row = $s->fetch(PDO::FETCH_ASSOC);
	return $row ?: null;
}

function sc_ops_sip_pass(): string {
	$chars = 'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789';
	$out = '';
	for ($i = 0; $i < 16; $i++) {
		$out .= $chars[random_int(0, strlen($chars) - 1)];
	}
	return $out;
}

function sc_ops_next_ext(PDO $db, string $du): string {
	try {
		$s = $db->prepare("SELECT extension FROM v_extensions
			WHERE domain_uuid = :d AND extension ~ '^[0-9]+$'
			ORDER BY extension::int DESC LIMIT 1");
		$s->execute([':d' => $du]);
		$last = (int)$s->fetchColumn();
		if ($last >= 100) {
			return (string)($last + 1);
		}
	} catch (Throwable $e) {
		/* ignore */
	}
	return '103';
}

function sc_ops_esc_xml(string $s): string {
	return htmlspecialchars($s, ENT_XML1 | ENT_QUOTES, 'UTF-8');
}

function sc_ops_next_service_ext(PDO $db, string $du, int $start = 9000): string {
	$n = $start - 1;
	$queries = [
		"SELECT ivr_menu_extension FROM v_ivr_menus WHERE domain_uuid = :d AND ivr_menu_extension ~ '^[0-9]+$'",
		"SELECT queue_extension FROM v_call_center_queues WHERE domain_uuid = :d AND queue_extension ~ '^[0-9]+$'",
		"SELECT call_flow_extension FROM v_call_flows WHERE domain_uuid = :d AND call_flow_extension ~ '^[0-9]+$'",
	];
	foreach ($queries as $sql) {
		try {
			$s = $db->prepare($sql);
			$s->execute([':d' => $du]);
			foreach ($s->fetchAll(PDO::FETCH_COLUMN) as $e) {
				$v = (int)$e;
				if ($v >= $start && $v > $n) {
					$n = $v;
				}
			}
		} catch (Throwable $e) {
			/* ignore */
		}
	}
	return (string)($n >= $start ? $n + 1 : $start);
}

function sc_ops_put_dialplan(PDO $db, string $du, string $dom, string $uuid, string $name, string $number, string $xml, string $order, string $appUuid): void {
	$db->prepare(
		"INSERT INTO v_dialplans (
			dialplan_uuid, domain_uuid, app_uuid, dialplan_context, dialplan_name, dialplan_number,
			dialplan_xml, dialplan_order, dialplan_enabled, dialplan_description, dialplan_continue
		) VALUES (:id, :d, :a, :c, :n, :num, :x, :o, true, :ds, false)"
	)->execute([
		':id' => $uuid,
		':d' => $du,
		':a' => $appUuid,
		':c' => $dom,
		':n' => $name,
		':num' => $number,
		':x' => $xml,
		':o' => $order,
		':ds' => 'SkyConnect',
	]);
}

function sc_ops_drop_dialplan(PDO $db, string $du, string $uuid): void {
	if ($uuid === '') {
		return;
	}
	try {
		$db->prepare('DELETE FROM v_dialplan_details WHERE dialplan_uuid = :id')->execute([':id' => $uuid]);
	} catch (Throwable $e) {
		/* no details table */
	}
	try {
		$db->prepare('DELETE FROM v_dialplans WHERE dialplan_uuid = :id AND domain_uuid = :d')
			->execute([':id' => $uuid, ':d' => $du]);
	} catch (Throwable $e) {
		/* ignore */
	}
}

function sc_ops_ensure_fayda(PDO $db): void {
	skykin_crm_ensure_contacts($db);
	foreach ([
		'ALTER TABLE skykin_contacts ADD COLUMN IF NOT EXISTS fayda_verified INTEGER DEFAULT 0',
		'ALTER TABLE skykin_contacts ADD COLUMN fayda_verified INTEGER DEFAULT 0',
	] as $sql) {
		try {
			$db->exec($sql);
			break;
		} catch (Throwable $e) {
			/* exists */
		}
	}
}

function sc_ops_list_contacts(PDO $db): array {
	sc_ops_ensure_fayda($db);
	$list = [];
	try {
		$list = $db->query(
			"SELECT full_name, phone, COALESCE(fayda_verified, 0) AS fayda_verified, language, account_type
			 FROM skykin_contacts ORDER BY contact_id DESC LIMIT 80"
		)->fetchAll(PDO::FETCH_ASSOC);
	} catch (Throwable $e) {
		try {
			$list = $db->query(
				"SELECT full_name, phone, language, account_type FROM skykin_contacts ORDER BY contact_id DESC LIMIT 80"
			)->fetchAll(PDO::FETCH_ASSOC);
			foreach ($list as &$r) {
				$r['fayda_verified'] = 0;
			}
			unset($r);
		} catch (Throwable $e2) {
			$list = [];
		}
	}
	$verified = 0;
	foreach ($list as $r) {
		if (sc_ops_truthy($r['fayda_verified'] ?? 0)) {
			$verified++;
		}
	}
	$total = $list ? count($list) : 0;
	try {
		$total = (int)$db->query('SELECT COUNT(*) FROM skykin_contacts')->fetchColumn();
	} catch (Throwable $e) {
		/* keep */
	}
	return ['contacts' => $list, 'total' => $total, 'verified' => $verified];
}

function sc_ops_ensure_did_table(PDO $db): void {
	$db->exec("CREATE TABLE IF NOT EXISTS skykin_did_routes (
		route_id SERIAL PRIMARY KEY,
		domain_name TEXT NOT NULL,
		did TEXT NOT NULL,
		dest_ext TEXT NOT NULL,
		dest_kind TEXT DEFAULT 'ivr',
		updated_at TIMESTAMP DEFAULT NOW(),
		UNIQUE (domain_name, did)
	)");
}

function sc_ops_write_fs_file(string $txt, array $paths): void {
	foreach ($paths as $path) {
		$dir = dirname($path);
		if (is_dir($dir) && is_writable($dir)) {
			@file_put_contents($path, $txt);
		}
	}
}

function sc_ops_reload_xml(): array {
	$xml = function_exists('skykin_fs_api') ? trim((string)skykin_fs_api('reloadxml')) : '';
	$mem = function_exists('skykin_fs_api') ? trim((string)skykin_fs_api('memcache flush')) : '';
	return ['reloadxml' => $xml, 'memcache' => $mem];
}

/** @return array{ivr_menu_uuid:string,ivr_menu_extension:string} */
function sc_ops_ivr_create_menu(PDO $db, string $du, string $dom, string $name, string $ext, string $greet = '', string $desc = ''): array {
	if ($ext === '') {
		$ext = sc_ops_next_service_ext($db, $du, 9000);
	}
	$id = sc_ops_uuid();
	$dp = sc_ops_uuid();
	$xml = "<extension name=\"".sc_ops_esc_xml($name)."\" continue=\"false\" uuid=\"".sc_ops_esc_xml($dp)."\">\n"
		."	<condition field=\"destination_number\" expression=\"^".sc_ops_esc_xml($ext)."\$\">\n"
		."		<action application=\"answer\" data=\"\"/>\n"
		."		<action application=\"sleep\" data=\"1000\"/>\n"
		."		<action application=\"set\" data=\"ivr_menu_uuid=".sc_ops_esc_xml($id)."\"/>\n"
		."		<action application=\"ivr\" data=\"".sc_ops_esc_xml($id)."\"/>\n"
		."	</condition>\n"
		."</extension>\n";
	try {
		sc_ops_put_dialplan($db, $du, $dom, $dp, $name, $ext, $xml, '101', 'a5788e9b-58bc-bd1b-df59-fff5d51253ab');
	} catch (Throwable $e) {
		$dp = '';
	}
	$db->prepare(
		"INSERT INTO v_ivr_menus (
			ivr_menu_uuid, domain_uuid, dialplan_uuid, ivr_menu_name, ivr_menu_extension,
			ivr_menu_greet_long, ivr_menu_greet_short, ivr_menu_invalid_sound, ivr_menu_exit_sound,
			ivr_menu_confirm_attempts, ivr_menu_timeout, ivr_menu_inter_digit_timeout,
			ivr_menu_max_failures, ivr_menu_max_timeouts, ivr_menu_digit_len, ivr_menu_direct_dial,
			ivr_menu_ringback, ivr_menu_context, ivr_menu_enabled, ivr_menu_description,
			ivr_menu_language, ivr_menu_dialect, ivr_menu_voice
		) VALUES (
			:id, :d, :dp, :n, :e,
			:gl, :gs, 'ivr/ivr-that_was_an_invalid_entry.wav', 'voicemail/vm-goodbye.wav',
			1, 3000, 2000, 3, 3, 5, false,
			'local_stream://default', :ctx, true, :ds, 'en', 'us', 'callie'
		)"
	)->execute([
		':id' => $id,
		':d' => $du,
		':dp' => $dp !== '' ? $dp : null,
		':n' => $name,
		':e' => $ext,
		':gl' => $greet,
		':gs' => $greet,
		':ctx' => $dom,
		':ds' => $desc !== '' ? $desc : 'SkyConnect IVR',
	]);
	return ['ivr_menu_uuid' => $id, 'ivr_menu_extension' => $ext];
}

function sc_ops_ivr_add_option(PDO $db, string $du, string $menu, string $digits, string $param, string $desc = '', string $action = 'menu-exec-app'): string {
	$opt = sc_ops_uuid();
	$db->prepare(
		"INSERT INTO v_ivr_menu_options (ivr_menu_option_uuid, ivr_menu_uuid, domain_uuid,
			ivr_menu_option_digits, ivr_menu_option_action, ivr_menu_option_param, ivr_menu_option_description, ivr_menu_option_order)
		 VALUES (:id, :m, :d, :dig, :a, :p, :ds, :ord)"
	)->execute([
		':id' => $opt,
		':m' => $menu,
		':d' => $du,
		':dig' => $digits,
		':a' => $action !== '' ? $action : 'menu-exec-app',
		':p' => $param,
		':ds' => $desc,
		':ord' => (int)$digits,
	]);
	return $opt;
}

function sc_ops_ivr_transfer_param(string $ext): string {
	$e = preg_replace('/\D+/', '', $ext);
	return 'transfer ' . $e . ' XML ${domain_name}';
}

/** @param array<int,mixed> $branches */
function sc_ops_ivr_save_branches(PDO $db, string $du, string $dom, string $parentId, array $branches): void {
	foreach ($branches as $b) {
		if (!is_array($b)) {
			continue;
		}
		$dig = trim((string)($b['digits'] ?? $b['digit'] ?? ''));
		if ($dig === '') {
			continue;
		}
		$param = trim((string)($b['param'] ?? ''));
		$subName = trim((string)($b['new_submenu'] ?? $b['submenu'] ?? ''));
		$desc = trim((string)($b['description'] ?? $b['label'] ?? ''));
		if ($subName !== '') {
			$child = sc_ops_ivr_create_menu($db, $du, $dom, $subName, '', '', $desc !== '' ? $desc : ('Submenu of ' . $subName));
			$param = sc_ops_ivr_transfer_param($child['ivr_menu_extension']);
			if ($desc === '') {
				$desc = 'submenu ' . $subName;
			}
		}
		if ($param === '') {
			continue;
		}
		sc_ops_ivr_add_option($db, $du, $parentId, $dig, $param, $desc);
	}
}

function sc_ops_write_did_map(PDO $db): void {
	sc_ops_ensure_did_table($db);
	$rows = [];
	try {
		$rows = $db->query('SELECT domain_name, did, dest_ext FROM skykin_did_routes ORDER BY domain_name, did')->fetchAll(PDO::FETCH_ASSOC);
	} catch (Throwable $e) {
		$rows = [];
	}
	$txt = "# domain|did|extension\n";
	foreach ($rows as $r) {
		$txt .= $r['domain_name'] . '|' . preg_replace('/\D+/', '', (string)$r['did']) . '|' . preg_replace('/\D+/', '', (string)$r['dest_ext']) . "\n";
	}
	sc_ops_write_fs_file($txt, [
		'/var/lib/freeswitch/recordings/skykin_did_map.txt',
		'/etc/freeswitch/scripts/skykin_did_map.txt',
	]);
}

function sc_ops_write_hunt_map(PDO $db): void {
	$txt = "# SKYKIN_HUNT_STAFF_v2 domain|queue_ext|agent_ext  (if a domain+queue has rows, Lua rings only those agents)\n";
	try {
		$rows = $db->query(
			"SELECT COALESCE(t.domain_uuid, a.domain_uuid, q.domain_uuid) AS domain_uuid,
			        q.queue_extension, a.agent_id, a.agent_contact
			 FROM v_call_center_tiers t
			 JOIN v_call_center_agents a ON a.call_center_agent_uuid = t.call_center_agent_uuid
			 LEFT JOIN v_call_center_queues q ON q.call_center_queue_uuid = t.call_center_queue_uuid"
		)->fetchAll(PDO::FETCH_ASSOC);
		$domCache = [];
		foreach ($rows as $r) {
			$du = (string)($r['domain_uuid'] ?? '');
			if ($du === '') {
				continue;
			}
			if (!isset($domCache[$du])) {
				$s = $db->prepare('SELECT domain_name FROM v_domains WHERE domain_uuid = :u LIMIT 1');
				$s->execute([':u' => $du]);
				$domCache[$du] = (string)$s->fetchColumn();
			}
			$dom = $domCache[$du];
			$qext = preg_replace('/\D+/', '', (string)($r['queue_extension'] ?? ''));
			if ($qext === '') {
				$qext = '*';
			}
			$ext = preg_replace('/\D+/', '', (string)$r['agent_id']);
			if ($ext === '' && preg_match('#user/([^@]+)@#', (string)($r['agent_contact'] ?? ''), $m)) {
				$ext = preg_replace('/\D+/', '', $m[1]);
			}
			if ($dom !== '' && $ext !== '') {
				$txt .= $dom . '|' . $qext . '|' . $ext . "\n";
			}
		}
	} catch (Throwable $e) {
		/* keep header only */
	}
	sc_ops_write_fs_file($txt, [
		'/var/lib/freeswitch/recordings/skykin_hunt_agents.txt',
		'/etc/freeswitch/scripts/skykin_hunt_agents.txt',
	]);
}

function sc_ops_biz_hours_key(string $dom): string {
	return 'biz_hours:' . $dom;
}

function sc_ops_biz_hours_get(string $dom): array {
	$raw = skykin_setting_get(sc_ops_biz_hours_key($dom), '');
	$j = json_decode($raw, true);
	if (!is_array($j)) {
		$j = [];
	}
	$enabled = !empty($j['enabled']);
	return [
		'enabled' => $enabled,
		'tz' => (string)($j['tz'] ?? 'Africa/Addis_Ababa'),
		'open' => preg_replace('/\D+/', '', (string)($j['open'] ?? '0800')) ?: '0800',
		'close' => preg_replace('/\D+/', '', (string)($j['close'] ?? '1900')) ?: '1900',
		'days' => (string)($j['days'] ?? '1,2,3,4,5,6,7'),
	];
}

function sc_ops_write_biz_hours(PDO $db): void {
	if (function_exists('skykin_ensure_settings_table')) {
		skykin_ensure_settings_table($db);
	}
	$txt = "# SKYKIN_BIZ_HOURS_FILE_v1 domain|on|tz|open|close|days\n";
	try {
		$rows = $db->query("SELECT setting_key, setting_value FROM skykin_settings WHERE setting_key LIKE 'biz_hours:%'")->fetchAll(PDO::FETCH_ASSOC);
		foreach ($rows as $r) {
			$dom = substr((string)$r['setting_key'], strlen('biz_hours:'));
			$j = json_decode((string)$r['setting_value'], true);
			if ($dom === '' || !is_array($j) || empty($j['enabled'])) {
				continue;
			}
			$tz = preg_replace('/[^\w\/_+-]/', '', (string)($j['tz'] ?? 'Africa/Addis_Ababa')) ?: 'Africa/Addis_Ababa';
			$open = preg_replace('/\D+/', '', (string)($j['open'] ?? '0800')) ?: '0800';
			$close = preg_replace('/\D+/', '', (string)($j['close'] ?? '1900')) ?: '1900';
			$days = preg_replace('/[^\d,]/', '', (string)($j['days'] ?? '1,2,3,4,5,6,7')) ?: '1,2,3,4,5,6,7';
			$txt .= $dom . '|on|' . $tz . '|' . $open . '|' . $close . '|' . $days . "\n";
		}
	} catch (Throwable $e) {
		/* keep header */
	}
	sc_ops_write_fs_file($txt, [
		'/var/lib/freeswitch/recordings/skykin_biz_hours.txt',
		'/etc/freeswitch/scripts/skykin_biz_hours.txt',
	]);
}

function sc_ops_queue_members(PDO $db, string $du): array {
	$out = [];
	try {
		$s = $db->prepare(
			"SELECT t.call_center_queue_uuid, a.user_uuid, a.agent_id, a.agent_name
			 FROM v_call_center_tiers t
			 JOIN v_call_center_agents a ON a.call_center_agent_uuid = t.call_center_agent_uuid
			 WHERE t.domain_uuid = :d OR a.domain_uuid = :d"
		);
		$s->execute([':d' => $du]);
		foreach ($s->fetchAll(PDO::FETCH_ASSOC) as $r) {
			$qid = (string)$r['call_center_queue_uuid'];
			if (!isset($out[$qid])) {
				$out[$qid] = [];
			}
			$uid = (string)($r['user_uuid'] ?? '');
			if ($uid !== '') {
				$out[$qid][] = $uid;
			}
		}
	} catch (Throwable $e) {
		/* ignore */
	}
	return $out;
}

function sc_ops_ensure_cc_agent(PDO $db, string $du, string $dom, array $user): ?string {
	$uid = (string)($user['user_uuid'] ?? '');
	$ext = preg_replace('/\D+/', '', explode(',', (string)($user['extension'] ?? ''))[0] ?? '');
	if ($uid === '' || $ext === '') {
		return null;
	}
	$find = $db->prepare('SELECT call_center_agent_uuid FROM v_call_center_agents WHERE domain_uuid = :d AND user_uuid = :u LIMIT 1');
	$find->execute([':d' => $du, ':u' => $uid]);
	$id = $find->fetchColumn();
	if ($id) {
		return (string)$id;
	}
	$id = sc_ops_uuid();
	$name = (string)($user['username'] ?? $ext);
	$contact = '{call_timeout=20,sip_invite_domain=' . $dom . '}user/' . $ext . '@' . $dom;
	$db->prepare(
		"INSERT INTO v_call_center_agents (
			call_center_agent_uuid, domain_uuid, user_uuid, agent_name, agent_type,
			agent_call_timeout, agent_id, agent_password, agent_contact, agent_status,
			agent_max_no_answer, agent_wrap_up_time, agent_reject_delay_time, agent_busy_delay_time
		) VALUES (
			:id, :d, :u, :n, 'callback', 20, :aid, '', :c, 'Logged Out', 0, 10, 0, 0
		)"
	)->execute([':id' => $id, ':d' => $du, ':u' => $uid, ':n' => $name, ':aid' => $ext, ':c' => $contact]);
	return $id;
}

function sc_ops_default_skills(): array {
	return [
		['skill_key' => 'amharic', 'label' => 'Amharic', 'kind' => 'language', 'sort_order' => 1],
		['skill_key' => 'english', 'label' => 'English', 'kind' => 'language', 'sort_order' => 2],
		['skill_key' => 'oromo', 'label' => 'Afaan Oromo', 'kind' => 'language', 'sort_order' => 3],
		['skill_key' => 'sim', 'label' => 'SIM / identity', 'kind' => 'product', 'sort_order' => 10],
		['skill_key' => 'telebirr', 'label' => 'telebirr', 'kind' => 'product', 'sort_order' => 11],
		['skill_key' => 'billing', 'label' => 'Billing', 'kind' => 'product', 'sort_order' => 12],
		['skill_key' => 'general', 'label' => 'General', 'kind' => 'product', 'sort_order' => 20],
	];
}

function sc_ops_ensure_skill_tables(PDO $db): void {
	$drv = $db->getAttribute(PDO::ATTR_DRIVER_NAME);
	if ($drv === 'sqlite') {
		$db->exec("CREATE TABLE IF NOT EXISTS skykin_skills (
			skill_key TEXT PRIMARY KEY,
			label TEXT NOT NULL,
			kind TEXT DEFAULT 'product',
			sort_order INTEGER DEFAULT 0
		)");
		$db->exec("CREATE TABLE IF NOT EXISTS skykin_user_skills (
			user_uuid TEXT NOT NULL,
			skill_key TEXT NOT NULL,
			domain_uuid TEXT,
			PRIMARY KEY (user_uuid, skill_key)
		)");
		$db->exec("CREATE TABLE IF NOT EXISTS skykin_queue_skills (
			call_center_queue_uuid TEXT PRIMARY KEY,
			skill_key TEXT NOT NULL,
			domain_uuid TEXT
		)");
	} else {
		$db->exec("CREATE TABLE IF NOT EXISTS skykin_skills (
			skill_key TEXT PRIMARY KEY,
			label TEXT NOT NULL,
			kind TEXT DEFAULT 'product',
			sort_order INTEGER DEFAULT 0
		)");
		$db->exec("CREATE TABLE IF NOT EXISTS skykin_user_skills (
			user_uuid UUID NOT NULL,
			skill_key TEXT NOT NULL,
			domain_uuid UUID,
			PRIMARY KEY (user_uuid, skill_key)
		)");
		$db->exec("CREATE TABLE IF NOT EXISTS skykin_queue_skills (
			call_center_queue_uuid UUID PRIMARY KEY,
			skill_key TEXT NOT NULL,
			domain_uuid UUID
		)");
	}
	foreach (sc_ops_default_skills() as $sk) {
		try {
			$db->prepare(
				"INSERT INTO skykin_skills (skill_key, label, kind, sort_order) VALUES (:k,:l,:n,:o)
				 ON CONFLICT (skill_key) DO NOTHING"
			)->execute([':k' => $sk['skill_key'], ':l' => $sk['label'], ':n' => $sk['kind'], ':o' => $sk['sort_order']]);
		} catch (Throwable $e) {
			try {
				$db->prepare('INSERT OR IGNORE INTO skykin_skills (skill_key, label, kind, sort_order) VALUES (:k,:l,:n,:o)')
					->execute([':k' => $sk['skill_key'], ':l' => $sk['label'], ':n' => $sk['kind'], ':o' => $sk['sort_order']]);
			} catch (Throwable $e2) {
				/* ignore */
			}
		}
	}
}

function sc_ops_skill_catalog(PDO $db): array {
	sc_ops_ensure_skill_tables($db);
	try {
		return $db->query('SELECT skill_key, label, kind, sort_order FROM skykin_skills ORDER BY sort_order, label')->fetchAll(PDO::FETCH_ASSOC) ?: [];
	} catch (Throwable $e) {
		return sc_ops_default_skills();
	}
}

/** @return array<string,string[]> user_uuid => skill_keys */
function sc_ops_load_user_skills(PDO $db, string $du): array {
	sc_ops_ensure_skill_tables($db);
	$out = [];
	try {
		$s = $db->prepare('SELECT user_uuid, skill_key FROM skykin_user_skills WHERE domain_uuid = :d OR domain_uuid IS NULL');
		$s->execute([':d' => $du]);
		foreach ($s->fetchAll(PDO::FETCH_ASSOC) as $r) {
			$id = (string)$r['user_uuid'];
			$out[$id][] = (string)$r['skill_key'];
		}
	} catch (Throwable $e) {
		/* ignore */
	}
	return $out;
}

/** @return array<string,string> queue_uuid => skill_key */
function sc_ops_load_queue_skills(PDO $db, string $du): array {
	sc_ops_ensure_skill_tables($db);
	$out = [];
	try {
		$s = $db->prepare('SELECT call_center_queue_uuid, skill_key FROM skykin_queue_skills WHERE domain_uuid = :d');
		$s->execute([':d' => $du]);
		foreach ($s->fetchAll(PDO::FETCH_ASSOC) as $r) {
			$out[(string)$r['call_center_queue_uuid']] = (string)$r['skill_key'];
		}
	} catch (Throwable $e) {
		/* ignore */
	}
	return $out;
}

function sc_ops_set_queue_skill(PDO $db, string $du, string $qid, string $skill): void {
	sc_ops_ensure_skill_tables($db);
	$skill = strtolower(trim($skill));
	if ($qid === '') {
		return;
	}
	if ($skill === '' || $skill === 'none') {
		try {
			$db->prepare('DELETE FROM skykin_queue_skills WHERE call_center_queue_uuid = :q')->execute([':q' => $qid]);
		} catch (Throwable $e) {
			/* ignore */
		}
		return;
	}
	try {
		$db->prepare(
			"INSERT INTO skykin_queue_skills (call_center_queue_uuid, skill_key, domain_uuid) VALUES (:q,:k,:d)
			 ON CONFLICT (call_center_queue_uuid) DO UPDATE SET skill_key = EXCLUDED.skill_key, domain_uuid = EXCLUDED.domain_uuid"
		)->execute([':q' => $qid, ':k' => $skill, ':d' => $du]);
	} catch (Throwable $e) {
		$db->prepare('DELETE FROM skykin_queue_skills WHERE call_center_queue_uuid = :q')->execute([':q' => $qid]);
		$db->prepare('INSERT INTO skykin_queue_skills (call_center_queue_uuid, skill_key, domain_uuid) VALUES (:q,:k,:d)')
			->execute([':q' => $qid, ':k' => $skill, ':d' => $du]);
	}
}

/** @return array{members:int,skipped:array} */
function sc_ops_set_queue_members(PDO $db, string $du, string $dom, string $qid, array $want): array {
	$want = array_values(array_unique(array_filter(array_map('strval', $want))));
	$users = [];
	foreach (sc_ops_load_users($db, $du) as $u) {
		$users[(string)$u['user_uuid']] = $u;
	}
	$qrow = $db->prepare(
		'SELECT call_center_queue_uuid, queue_name FROM v_call_center_queues WHERE call_center_queue_uuid = :id AND domain_uuid = :d LIMIT 1'
	);
	$qrow->execute([':id' => $qid, ':d' => $du]);
	$queue = $qrow->fetch(PDO::FETCH_ASSOC);
	if (!$queue) {
		return ['members' => 0, 'skipped' => ['queue']];
	}
	try {
		$db->prepare('DELETE FROM v_call_center_tiers WHERE call_center_queue_uuid = :q AND domain_uuid = :d')
			->execute([':q' => $qid, ':d' => $du]);
	} catch (Throwable $e) {
		$db->prepare('DELETE FROM v_call_center_tiers WHERE call_center_queue_uuid = :q')->execute([':q' => $qid]);
	}
	$pos = 1;
	$added = 0;
	$skipped = [];
	foreach ($want as $uid) {
		if (!isset($users[$uid])) {
			$skipped[] = $uid;
			continue;
		}
		$aid = sc_ops_ensure_cc_agent($db, $du, $dom, $users[$uid]);
		if (!$aid) {
			$skipped[] = (string)($users[$uid]['username'] ?? $uid) . ' (no extension)';
			continue;
		}
		$tid = sc_ops_uuid();
		$okTier = false;
		try {
			$db->prepare(
				"INSERT INTO v_call_center_tiers (
					call_center_tier_uuid, domain_uuid, call_center_queue_uuid, call_center_agent_uuid, tier_level, tier_position
				) VALUES (:id, :d, :q, :a, 1, :p)"
			)->execute([':id' => $tid, ':d' => $du, ':q' => $qid, ':a' => $aid, ':p' => $pos]);
			$okTier = true;
		} catch (Throwable $e) {
			try {
				$db->prepare(
					"INSERT INTO v_call_center_tiers (
						call_center_tier_uuid, domain_uuid, call_center_queue_uuid, call_center_agent_uuid,
						tier_level, tier_position, queue_name, agent_name
					) VALUES (:id, :d, :q, :a, 1, :p, :qn, :an)"
				)->execute([
					':id' => $tid,
					':d' => $du,
					':q' => $qid,
					':a' => $aid,
					':p' => $pos,
					':qn' => (string)$queue['queue_name'],
					':an' => (string)($users[$uid]['username'] ?? ''),
				]);
				$okTier = true;
			} catch (Throwable $e2) {
				$skipped[] = (string)($users[$uid]['username'] ?? $uid);
			}
		}
		if ($okTier) {
			$added++;
			$pos++;
		}
	}
	sc_ops_write_hunt_map($db);
	return ['members' => $added, 'skipped' => $skipped];
}

function sc_ops_sync_skill_queues(PDO $db, string $du, string $dom): int {
	$qskills = sc_ops_load_queue_skills($db, $du);
	$uskills = sc_ops_load_user_skills($db, $du);
	$n = 0;
	foreach ($qskills as $qid => $skill) {
		$want = [];
		foreach ($uskills as $uid => $keys) {
			if (in_array($skill, $keys, true)) {
				$want[] = $uid;
			}
		}
		sc_ops_set_queue_members($db, $du, $dom, $qid, $want);
		$n++;
	}
	return $n;
}

function sc_ops_link_ext(PDO $db, string $du, string $userUuid, string $extUuid): void {
	$link = $db->prepare('SELECT 1 FROM v_extension_users WHERE user_uuid = :u AND extension_uuid = :e LIMIT 1');
	$link->execute([':u' => $userUuid, ':e' => $extUuid]);
	if ($link->fetchColumn()) {
		return;
	}
	$db->prepare(
		"INSERT INTO v_extension_users (extension_user_uuid, domain_uuid, extension_uuid, user_uuid)
		 VALUES (:id, :d, :e, :u)"
	)->execute([':id' => sc_ops_uuid(), ':d' => $du, ':e' => $extUuid, ':u' => $userUuid]);
}

/** Link an existing SIP extension, or create one cloned from a live 1xx on this domain. */
function sc_ops_ensure_extension(PDO $db, string $du, string $dom, string $ext, string $userUuid, string $display, string $sipPass, bool $create): array {
	$ex = $db->prepare('SELECT extension_uuid, password FROM v_extensions WHERE domain_uuid = :d AND extension = :e LIMIT 1');
	$ex->execute([':d' => $du, ':e' => $ext]);
	$row = $ex->fetch(PDO::FETCH_ASSOC);
	if ($row) {
		sc_ops_link_ext($db, $du, $userUuid, (string)$row['extension_uuid']);
		if ($sipPass !== '') {
			$db->prepare('UPDATE v_extensions SET password = :p WHERE extension_uuid = :id')
				->execute([':p' => $sipPass, ':id' => (string)$row['extension_uuid']]);
			return ['ok' => true, 'created' => false, 'extension' => $ext, 'sip_password' => $sipPass, 'sip_updated' => true];
		}
		return ['ok' => true, 'created' => false, 'extension' => $ext, 'sip_password' => ''];
	}
	if (!$create) {
		return ['ok' => false, 'error' => 'Extension ' . $ext . ' does not exist. Tick Create new extension.'];
	}
	$sip = $sipPass !== '' ? $sipPass : sc_ops_sip_pass();
	$ctx = $dom !== '' ? $dom : (string)($_SESSION['domain_name'] ?? '');
	$cid = $display !== '' ? $display : $ext;
	$id = sc_ops_uuid();
	$tpl = $db->prepare("SELECT extension_uuid FROM v_extensions
		WHERE domain_uuid = :d AND extension ~ '^[0-9]{2,6}$'
		ORDER BY extension LIMIT 1");
	$tpl->execute([':d' => $du]);
	$tid = $tpl->fetchColumn();
	if ($tid) {
		$db->prepare(
			"INSERT INTO v_extensions (
				extension_uuid, domain_uuid, extension, password,
				accountcode, effective_caller_id_name, effective_caller_id_number,
				outbound_caller_id_name, outbound_caller_id_number,
				directory_first_name, directory_visible, directory_exten_visible,
				max_registrations, limit_max, limit_destination, user_context,
				call_timeout, call_group, call_screen_enabled, user_record, hold_music,
				enabled, description, extension_type
			)
			SELECT
				:id, domain_uuid, :ext, :pw,
				accountcode, :cn, :enum,
				outbound_caller_id_name, outbound_caller_id_number,
				:cn2, directory_visible, directory_exten_visible,
				max_registrations, limit_max, limit_destination, user_context,
				call_timeout, call_group, call_screen_enabled, user_record, hold_music,
				true, :desc, COALESCE(extension_type, 'default')
			FROM v_extensions WHERE extension_uuid = :tid"
		)->execute([
			':id' => $id,
			':ext' => $ext,
			':pw' => $sip,
			':cn' => $cid,
			':enum' => $ext,
			':cn2' => $cid,
			':desc' => 'SkyConnect ' . $cid,
			':tid' => $tid,
		]);
	} else {
		$db->prepare(
			"INSERT INTO v_extensions (
				extension_uuid, domain_uuid, extension, password,
				effective_caller_id_name, effective_caller_id_number,
				directory_first_name, directory_visible, directory_exten_visible,
				max_registrations, limit_max, user_context, call_timeout,
				enabled, description, extension_type
			) VALUES (
				:id, :d, :ext, :pw,
				:cn, :enum,
				:cn2, true, true,
				'5', '5', :ctx, 30,
				true, :desc, 'default'
			)"
		)->execute([
			':id' => $id,
			':d' => $du,
			':ext' => $ext,
			':pw' => $sip,
			':cn' => $cid,
			':enum' => $ext,
			':cn2' => $cid,
			':ctx' => $ctx,
			':desc' => 'SkyConnect ' . $cid,
		]);
	}
	sc_ops_link_ext($db, $du, $userUuid, $id);
	return ['ok' => true, 'created' => true, 'extension' => $ext, 'sip_password' => $sip, 'extension_uuid' => $id];
}

function sc_ops_known_group_names(PDO $db, string $du, bool $allowSuper): array {
	$s = $db->prepare(
		"SELECT lower(group_name) AS n FROM v_groups
		 WHERE domain_uuid IS NULL OR domain_uuid = :d"
	);
	$s->execute([':d' => $du]);
	$out = [];
	foreach ($s->fetchAll(PDO::FETCH_ASSOC) as $r) {
		$n = (string)$r['n'];
		if ($n === '' || ($n === 'superadmin' && !$allowSuper)) {
			continue;
		}
		$out[] = $n;
	}
	return $out;
}

function sc_ops_load_roles(PDO $db, string $du): array {
	$catalog = [];
	try {
		$catalog = $db->query(
			"SELECT application_name, permission_name FROM v_permissions
			 ORDER BY application_name, permission_name"
		)->fetchAll(PDO::FETCH_ASSOC);
	} catch (Throwable $e) {
		$catalog = [];
	}
	$groups = [];
	$gs = $db->prepare(
		"SELECT group_uuid, group_name, group_level, group_description, domain_uuid, group_protected
		 FROM v_groups
		 WHERE domain_uuid IS NULL OR domain_uuid = :d
		 ORDER BY group_level DESC NULLS LAST, group_name"
	);
	try {
		$gs->execute([':d' => $du]);
		$groups = $gs->fetchAll(PDO::FETCH_ASSOC);
	} catch (Throwable $e) {
		$gs = $db->prepare(
			"SELECT group_uuid, group_name, group_level, group_description, domain_uuid
			 FROM v_groups WHERE domain_uuid IS NULL OR domain_uuid = :d ORDER BY group_name"
		);
		$gs->execute([':d' => $du]);
		$groups = $gs->fetchAll(PDO::FETCH_ASSOC);
	}
	$by = [];
	foreach ($groups as $g) {
		$id = (string)$g['group_uuid'];
		$by[$id] = [
			'group_uuid' => $id,
			'group_name' => (string)$g['group_name'],
			'group_level' => (int)($g['group_level'] ?? 10),
			'group_description' => (string)($g['group_description'] ?? ''),
			'global' => empty($g['domain_uuid']),
			'protected' => sc_ops_truthy($g['group_protected'] ?? false),
			'permissions' => [],
		];
	}
	if ($by) {
		try {
			$p = $db->query(
				"SELECT group_uuid, permission_name FROM v_group_permissions
				 WHERE permission_assigned = 'true' OR permission_assigned IS TRUE OR permission_assigned = 't'"
			);
			foreach ($p->fetchAll(PDO::FETCH_ASSOC) as $row) {
				$id = (string)$row['group_uuid'];
				if (isset($by[$id])) {
					$by[$id]['permissions'][] = (string)$row['permission_name'];
				}
			}
		} catch (Throwable $e) {
			/* ignore */
		}
	}
	return ['catalog' => $catalog, 'roles' => array_values($by)];
}

function sc_ops_set_user_groups(PDO $db, string $du, string $userUuid, array $names, bool $allowSuper): void {
	$allowed = sc_ops_known_group_names($db, $du, $allowSuper);
	$want = [];
	foreach ($names as $n) {
		$n = strtolower(trim((string)$n));
		if (in_array($n, $allowed, true)) {
			$want[$n] = true;
		}
	}
	$cur = $db->prepare(
		"SELECT ug.user_group_uuid, lower(COALESCE(NULLIF(ug.group_name,''), g.group_name)) AS n
		 FROM v_user_groups ug
		 LEFT JOIN v_groups g ON g.group_uuid = ug.group_uuid
		 WHERE ug.user_uuid = :u"
	);
	$cur->execute([':u' => $userUuid]);
	$have = [];
	foreach ($cur->fetchAll(PDO::FETCH_ASSOC) as $r) {
		$have[(string)$r['n']] = (string)$r['user_group_uuid'];
	}
	$managed = $allowed;
	foreach ($have as $n => $uuid) {
		if (!in_array($n, $managed, true)) {
			continue;
		}
		if (!isset($want[$n])) {
			$db->prepare('DELETE FROM v_user_groups WHERE user_group_uuid = :x')->execute([':x' => $uuid]);
		}
	}
	foreach ($want as $n => $_) {
		if (isset($have[$n])) {
			continue;
		}
		$grp = sc_ops_find_group($db, $du, $n);
		if (!$grp) {
			continue;
		}
		$db->prepare(
			"INSERT INTO v_user_groups (user_group_uuid, domain_uuid, group_name, group_uuid, user_uuid)
			 VALUES (:id, :d, :n, :g, :u)"
		)->execute([
			':id' => sc_ops_uuid(),
			':d' => $du,
			':n' => $grp['group_name'],
			':g' => $grp['group_uuid'],
			':u' => $userUuid,
		]);
	}
}

function sc_ops_wfm_ensure(PDO $db): void {
	$isSqlite = ($db->getAttribute(PDO::ATTR_DRIVER_NAME) === 'sqlite');
	$id = $isSqlite ? 'INTEGER PRIMARY KEY AUTOINCREMENT' : 'SERIAL PRIMARY KEY';
	$db->exec("CREATE TABLE IF NOT EXISTS skykin_wfm_shifts (
		shift_id $id,
		domain_name TEXT,
		name TEXT,
		start_hm TEXT,
		end_hm TEXT,
		days TEXT,
		notes TEXT
	)");
	$db->exec("CREATE TABLE IF NOT EXISTS skykin_wfm_holidays (
		holiday_id $id,
		domain_name TEXT,
		holiday_date TEXT,
		name TEXT
	)");
	$db->exec("CREATE TABLE IF NOT EXISTS skykin_wfm_assign (
		assign_id $id,
		domain_name TEXT,
		agent_ext TEXT,
		agent_name TEXT,
		shift_id INTEGER,
		weekend_off TEXT DEFAULT 'true'
	)");
}

function sc_ops_wfm_seed(PDO $db, string $dom): void {
	$s = $db->prepare('SELECT COUNT(*) FROM skykin_wfm_shifts WHERE domain_name = :d');
	$s->execute([':d' => $dom]);
	if ((int)$s->fetchColumn() === 0) {
		$ins = $db->prepare(
			'INSERT INTO skykin_wfm_shifts (domain_name, name, start_hm, end_hm, days, notes)
			 VALUES (:d,:n,:a,:b,:days,:note)'
		);
		$ins->execute([':d' => $dom, ':n' => 'Weekday day', ':a' => '08:00', ':b' => '16:00', ':days' => '1,2,3,4,5', ':note' => 'Mon–Fri']);
		$ins->execute([':d' => $dom, ':n' => 'Weekday evening', ':a' => '16:00', ':b' => '00:00', ':days' => '1,2,3,4,5', ':note' => 'Mon–Fri late']);
		$ins->execute([':d' => $dom, ':n' => 'Weekend', ':a' => '08:00', ':b' => '16:00', ':days' => '6,7', ':note' => 'Sat–Sun']);
	}
	$h = $db->prepare('SELECT COUNT(*) FROM skykin_wfm_holidays WHERE domain_name = :d');
	$h->execute([':d' => $dom]);
	if ((int)$h->fetchColumn() === 0) {
		$hi = $db->prepare('INSERT INTO skykin_wfm_holidays (domain_name, holiday_date, name) VALUES (:d,:dt,:n)');
		foreach ([
			['2026-01-07', 'Ethiopian Christmas'],
			['2026-01-19', 'Timkat'],
			['2026-03-02', 'Adwa Victory'],
			['2026-05-01', 'Labour Day'],
			['2026-05-05', 'Patriots Day'],
			['2026-05-28', 'Derg Downfall'],
			['2026-09-11', 'Ethiopian New Year'],
			['2026-09-27', 'Meskel'],
		] as $row) {
			$hi->execute([':d' => $dom, ':dt' => $row[0], ':n' => $row[1]]);
		}
	}
}

function sc_ops_wfm_pack(PDO $db, string $dom): array {
	sc_ops_wfm_ensure($db);
	sc_ops_wfm_seed($db, $dom);
	$sh = $db->prepare('SELECT * FROM skykin_wfm_shifts WHERE domain_name = :d ORDER BY shift_id');
	$sh->execute([':d' => $dom]);
	$shifts = $sh->fetchAll(PDO::FETCH_ASSOC);
	$ho = $db->prepare('SELECT * FROM skykin_wfm_holidays WHERE domain_name = :d ORDER BY holiday_date');
	$ho->execute([':d' => $dom]);
	$holidays = $ho->fetchAll(PDO::FETCH_ASSOC);
	$as = $db->prepare('SELECT * FROM skykin_wfm_assign WHERE domain_name = :d ORDER BY agent_ext');
	$as->execute([':d' => $dom]);
	$assign = $as->fetchAll(PDO::FETCH_ASSOC);
	return ['shifts' => $shifts, 'holidays' => $holidays, 'assign' => $assign];
}

function sc_ops_wfm_cell(array $shift, bool $weekendOff, array $holidayDates, int $dow, string $ymd): array {
	if (isset($holidayDates[$ymd])) {
		return ['label' => 'Holiday', 'note' => $holidayDates[$ymd], 'off' => true];
	}
	$days = array_filter(array_map('intval', explode(',', (string)($shift['days'] ?? ''))));
	if (in_array($dow, $days, true)) {
		$hours = trim(($shift['start_hm'] ?? '') . '–' . ($shift['end_hm'] ?? ''));
		return ['label' => $hours !== '–' ? $hours : (string)($shift['name'] ?? 'Duty'), 'note' => (string)($shift['name'] ?? ''), 'off' => false];
	}
	if ($weekendOff && ($dow === 6 || $dow === 7)) {
		return ['label' => 'Off', 'note' => 'Weekend', 'off' => true];
	}
	return ['label' => 'Off', 'note' => '', 'off' => true];
}

function sc_ops_surveys(PDO $db): void {
	$isSqlite = ($db->getAttribute(PDO::ATTR_DRIVER_NAME) === 'sqlite');
	if ($isSqlite) {
		$db->exec("CREATE TABLE IF NOT EXISTS skykin_surveys (
			survey_id INTEGER PRIMARY KEY AUTOINCREMENT,
			domain_name TEXT,
			agent_ext TEXT,
			agent_name TEXT,
			channel TEXT DEFAULT 'Voice',
			rating INTEGER,
			resolved TEXT,
			comment TEXT,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP
		)");
	} else {
		$db->exec("CREATE TABLE IF NOT EXISTS skykin_surveys (
			survey_id SERIAL PRIMARY KEY,
			domain_name TEXT,
			agent_ext TEXT,
			agent_name TEXT,
			channel TEXT DEFAULT 'Voice',
			rating SMALLINT,
			resolved TEXT,
			comment TEXT,
			created_at TIMESTAMP DEFAULT NOW()
		)");
	}
}

try {
	$db = sc_ops_db();

	if ($op === 'me_schedule') {
		$ext = trim((string)($_GET['ext'] ?? ''));
		$leave = null;
		try {
			$s = $db->prepare("SELECT id, request_type, reason, status, requested_at
				FROM skykin_leave_requests
				WHERE agent_ext = :e AND domain = :d
				ORDER BY id DESC LIMIT 5");
			$s->execute([':e' => $ext, ':d' => $dom]);
			$leave = $s->fetchAll(PDO::FETCH_ASSOC);
		} catch (Throwable $e) {
			$leave = [];
		}
		$pack = sc_ops_wfm_pack($db, $dom);
		$asg = null;
		foreach ($pack['assign'] as $a) {
			if ((string)($a['agent_ext'] ?? '') === $ext) {
				$asg = $a;
				break;
			}
		}
		$shift = null;
		if ($asg) {
			foreach ($pack['shifts'] as $sh) {
				if ((string)$sh['shift_id'] === (string)$asg['shift_id']) {
					$shift = $sh;
					break;
				}
			}
		}
		$holidayDates = [];
		foreach ($pack['holidays'] as $h) {
			$holidayDates[(string)$h['holiday_date']] = (string)$h['name'];
		}
		$weekendOff = !$asg || sc_ops_truthy($asg['weekend_off'] ?? 'true');
		$hours = $shift ? ($shift['start_hm'] . '–' . $shift['end_hm']) : '08:00–16:00';
		$week = [];
		$names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
		$todayN = (int)date('N');
		$monday = strtotime('monday this week');
		foreach ($names as $i => $day) {
			$dow = $i + 1;
			$ymd = date('Y-m-d', strtotime('+' . $i . ' day', $monday));
			if ($shift) {
				$cell = sc_ops_wfm_cell($shift, $weekendOff, $holidayDates, $dow, $ymd);
			} else {
				$off = $dow >= 6 || isset($holidayDates[$ymd]);
				$cell = [
					'label' => $off ? (isset($holidayDates[$ymd]) ? 'Holiday' : 'Off') : $hours,
					'note' => $holidayDates[$ymd] ?? ($off ? 'Weekend' : 'Unassigned'),
					'off' => $off,
				];
			}
			$week[] = [
				'day' => $day,
				'shift' => $cell['label'],
				'note' => $cell['note'],
				'today' => $dow === $todayN,
				'date' => $ymd,
			];
		}
		echo json_encode(['ok' => true, 'week' => $week, 'leave' => $leave, 'hours' => $hours, 'shift' => $shift]);
		exit;
	}

	if ($op === 'wfm') {
		sc_ops_need(['supervisor', 'admin', 'superadmin']);
		echo json_encode(array_merge(['ok' => true], sc_ops_wfm_pack($db, $dom)));
		exit;
	}

	if ($op === 'wfm_shift_save' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_ops_need(['supervisor', 'admin', 'superadmin']);
		sc_ops_wfm_ensure($db);
		$id = (int)($body['shift_id'] ?? 0);
		$name = trim((string)($body['name'] ?? ''));
		$start = trim((string)($body['start_hm'] ?? '08:00'));
		$end = trim((string)($body['end_hm'] ?? '16:00'));
		$days = trim((string)($body['days'] ?? '1,2,3,4,5'));
		$notes = trim((string)($body['notes'] ?? ''));
		if ($name === '') {
			echo json_encode(['ok' => false, 'error' => 'Shift name required']);
			exit;
		}
		if ($id > 0) {
			$db->prepare('UPDATE skykin_wfm_shifts SET name=:n, start_hm=:a, end_hm=:b, days=:days, notes=:note WHERE shift_id=:id AND domain_name=:d')
				->execute([':n' => $name, ':a' => $start, ':b' => $end, ':days' => $days, ':note' => $notes, ':id' => $id, ':d' => $dom]);
		} else {
			$db->prepare('INSERT INTO skykin_wfm_shifts (domain_name, name, start_hm, end_hm, days, notes) VALUES (:d,:n,:a,:b,:days,:note)')
				->execute([':d' => $dom, ':n' => $name, ':a' => $start, ':b' => $end, ':days' => $days, ':note' => $notes]);
		}
		echo json_encode(array_merge(['ok' => true], sc_ops_wfm_pack($db, $dom)));
		exit;
	}

	if ($op === 'wfm_shift_delete' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_ops_need(['supervisor', 'admin', 'superadmin']);
		$id = (int)($body['shift_id'] ?? 0);
		$db->prepare('DELETE FROM skykin_wfm_assign WHERE domain_name=:d AND shift_id=:id')->execute([':d' => $dom, ':id' => $id]);
		$db->prepare('DELETE FROM skykin_wfm_shifts WHERE domain_name=:d AND shift_id=:id')->execute([':d' => $dom, ':id' => $id]);
		echo json_encode(array_merge(['ok' => true], sc_ops_wfm_pack($db, $dom)));
		exit;
	}

	if ($op === 'wfm_holiday_save' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_ops_need(['supervisor', 'admin', 'superadmin']);
		sc_ops_wfm_ensure($db);
		$dt = trim((string)($body['holiday_date'] ?? ''));
		$name = trim((string)($body['name'] ?? 'Holiday'));
		if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $dt)) {
			echo json_encode(['ok' => false, 'error' => 'Date YYYY-MM-DD']);
			exit;
		}
		$db->prepare('INSERT INTO skykin_wfm_holidays (domain_name, holiday_date, name) VALUES (:d,:dt,:n)')
			->execute([':d' => $dom, ':dt' => $dt, ':n' => $name]);
		echo json_encode(array_merge(['ok' => true], sc_ops_wfm_pack($db, $dom)));
		exit;
	}

	if ($op === 'wfm_holiday_delete' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_ops_need(['supervisor', 'admin', 'superadmin']);
		$id = (int)($body['holiday_id'] ?? 0);
		$db->prepare('DELETE FROM skykin_wfm_holidays WHERE domain_name=:d AND holiday_id=:id')->execute([':d' => $dom, ':id' => $id]);
		echo json_encode(array_merge(['ok' => true], sc_ops_wfm_pack($db, $dom)));
		exit;
	}

	if ($op === 'wfm_assign' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_ops_need(['supervisor', 'admin', 'superadmin']);
		sc_ops_wfm_ensure($db);
		$shiftId = (int)($body['shift_id'] ?? 0);
		$weekendOff = !empty($body['weekend_off']) ? 'true' : 'false';
		$agents = $body['agents'] ?? [];
		if (!is_array($agents) || $agents === []) {
			$ext = trim((string)($body['agent_ext'] ?? ''));
			if ($ext !== '') {
				$agents = [['ext' => $ext, 'name' => (string)($body['agent_name'] ?? $ext)]];
			}
		}
		if ($shiftId < 1 || $agents === []) {
			echo json_encode(['ok' => false, 'error' => 'Shift and agents required']);
			exit;
		}
		$del = $db->prepare('DELETE FROM skykin_wfm_assign WHERE domain_name=:d AND agent_ext=:e');
		$ins = $db->prepare('INSERT INTO skykin_wfm_assign (domain_name, agent_ext, agent_name, shift_id, weekend_off) VALUES (:d,:e,:n,:s,:w)');
		foreach ($agents as $ag) {
			$ext = trim((string)($ag['ext'] ?? $ag['agent_ext'] ?? ''));
			if ($ext === '') {
				continue;
			}
			$del->execute([':d' => $dom, ':e' => $ext]);
			$ins->execute([
				':d' => $dom,
				':e' => $ext,
				':n' => trim((string)($ag['name'] ?? $ag['agent_name'] ?? $ext)),
				':s' => $shiftId,
				':w' => $weekendOff,
			]);
		}
		echo json_encode(array_merge(['ok' => true], sc_ops_wfm_pack($db, $dom)));
		exit;
	}

	if ($op === 'wfm_forecast') {
		sc_ops_need(['supervisor', 'admin', 'superadmin']);
		echo json_encode(['ok' => true, 'hours' => sc_ops_wfm_forecast($db, $dom)]);
		exit;
	}

	if ($op === 'omni_inbox') {
		sc_omni_ensure($db);
		$s = $db->prepare(
			"SELECT * FROM skykin_omni_threads WHERE domain_name = :d AND status <> 'closed'
			 ORDER BY updated_at DESC NULLS LAST, thread_id DESC LIMIT 80"
		);
		try {
			$s->execute([':d' => $dom]);
		} catch (Throwable $e) {
			$s = $db->prepare(
				"SELECT * FROM skykin_omni_threads WHERE domain_name = :d AND status <> 'closed'
				 ORDER BY thread_id DESC LIMIT 80"
			);
			$s->execute([':d' => $dom]);
		}
		echo json_encode(['ok' => true, 'threads' => $s->fetchAll(PDO::FETCH_ASSOC)]);
		exit;
	}

	if ($op === 'omni_thread') {
		sc_omni_ensure($db);
		$tid = (int)($_GET['thread_id'] ?? $body['thread_id'] ?? 0);
		$s = $db->prepare('SELECT * FROM skykin_omni_threads WHERE thread_id = :id AND domain_name = :d');
		$s->execute([':id' => $tid, ':d' => $dom]);
		$th = $s->fetch(PDO::FETCH_ASSOC);
		if (!$th) {
			echo json_encode(['ok' => false, 'error' => 'Thread not found']);
			exit;
		}
		echo json_encode(['ok' => true, 'thread' => $th, 'messages' => sc_omni_msgs($db, $tid)]);
		exit;
	}

	if ($op === 'omni_claim' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_omni_ensure($db);
		$tid = (int)($body['thread_id'] ?? 0);
		$ext = trim((string)($body['agent_ext'] ?? $_SESSION['user_extension'] ?? $me));
		$db->prepare("UPDATE skykin_omni_threads SET status='agent', agent_ext=:e WHERE thread_id=:id AND domain_name=:d")
			->execute([':e' => $ext, ':id' => $tid, ':d' => $dom]);
		echo json_encode(['ok' => true]);
		exit;
	}

	if ($op === 'omni_reply' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_omni_ensure($db);
		$tid = (int)($body['thread_id'] ?? 0);
		$text = trim((string)($body['text'] ?? ''));
		$ext = trim((string)($body['agent_ext'] ?? $me));
		if ($tid < 1 || $text === '') {
			echo json_encode(['ok' => false, 'error' => 'Message required']);
			exit;
		}
		$s = $db->prepare('SELECT * FROM skykin_omni_threads WHERE thread_id = :id AND domain_name = :d');
		$s->execute([':id' => $tid, ':d' => $dom]);
		$th = $s->fetch(PDO::FETCH_ASSOC);
		if (!$th) {
			echo json_encode(['ok' => false, 'error' => 'Thread not found']);
			exit;
		}
		if ((string)($th['agent_ext'] ?? '') === '') {
			$db->prepare("UPDATE skykin_omni_threads SET status='agent', agent_ext=:e WHERE thread_id=:id")
				->execute([':e' => $ext, ':id' => $tid]);
		}
		sc_omni_add_msg($db, $tid, 'agent', $text);
		if ((string)($th['channel'] ?? '') === 'whatsapp') {
			sc_omni_wa_send((string)$th['customer_key'], $text);
		}
		echo json_encode(['ok' => true, 'messages' => sc_omni_msgs($db, $tid)]);
		exit;
	}

	if ($op === 'omni_close' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		$tid = (int)($body['thread_id'] ?? 0);
		$db->prepare("UPDATE skykin_omni_threads SET status='closed' WHERE thread_id=:id AND domain_name=:d")
			->execute([':id' => $tid, ':d' => $dom]);
		echo json_encode(['ok' => true]);
		exit;
	}

	if ($op === 'survey_link' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		$ext = trim((string)($body['agent_ext'] ?? $me));
		$phone = trim((string)($body['phone'] ?? ''));
		$token = sc_csat_make($db, $dom, $ext, $phone);
		$path = '/app/agent_dashboard/skyconnect_omni.php?ui=csat&t=' . rawurlencode($token);
		echo json_encode(['ok' => true, 'token' => $token, 'path' => $path]);
		exit;
	}

	if ($op === 'me_learning') {
		$ext = trim((string)($_GET['ext'] ?? ''));
		$skills = [
			['label' => 'Greeting', 'key' => 'score_greeting'],
			['label' => 'Knowledge', 'key' => 'score_knowledge'],
			['label' => 'Resolution', 'key' => 'score_resolution'],
			['label' => 'Tone / empathy', 'key' => 'score_tone'],
			['label' => 'Procedure', 'key' => 'score_procedure'],
			['label' => 'Closing', 'key' => 'score_closing'],
		];
		$avgs = [];
		$evals = [];
		try {
			$s = $db->prepare("SELECT * FROM skykin_evaluations
				WHERE domain_name = :d AND agent_ext = :e
				ORDER BY eval_date DESC LIMIT 20");
			$s->execute([':d' => $dom, ':e' => $ext]);
			$evals = $s->fetchAll(PDO::FETCH_ASSOC);
			foreach ($skills as $sk) {
				$sum = 0;
				$n = 0;
				foreach ($evals as $ev) {
					$v = (int)($ev[$sk['key']] ?? 0);
					if ($v > 0) {
						$sum += $v;
						$n++;
					}
				}
				$avgs[] = [
					'label' => $sk['label'],
					'pct' => $n ? (int)round(($sum / $n) / 5 * 100) : 0,
					'samples' => $n,
				];
			}
		} catch (Throwable $e) {
			$avgs = array_map(static fn($sk) => ['label' => $sk['label'], 'pct' => 0, 'samples' => 0], $skills);
		}
		$articles = [];
		try {
			skykin_crm_ensure_knowledge($db);
			$articles = $db->query("SELECT article_id, title, tag FROM skykin_knowledge ORDER BY updated_at DESC LIMIT 8")->fetchAll(PDO::FETCH_ASSOC);
		} catch (Throwable $e) {
			$articles = [];
		}
		$learn = ['assignments' => [], 'assigned' => 0, 'passed' => 0, 'pct' => 0];
		try {
			$learn = skykin_learn_agent_pack($db, $dom, $ext);
		} catch (Throwable $e) {
			$learn = ['assignments' => [], 'assigned' => 0, 'passed' => 0, 'pct' => 0];
		}
		echo json_encode([
			'ok' => true,
			'skills' => $avgs,
			'evals' => $evals,
			'articles' => $articles,
			'count' => count($evals),
			'learning' => $learn,
		]);
		exit;
	}

	if ($op === 'learn_catalog') {
		sc_ops_need(['supervisor', 'admin', 'superadmin']);
		skykin_learn_ensure($db);
		$s = $db->prepare("SELECT course_id, domain_name, skill_key, title, body, quiz_json, created_by, created_at
			FROM skykin_learn_courses WHERE domain_name=:d OR domain_name='' OR domain_name IS NULL
			ORDER BY skill_key, course_id");
		$s->execute([':d' => $dom]);
		$rows = $s->fetchAll(PDO::FETCH_ASSOC);
		foreach ($rows as &$r) {
			$quiz = skykin_learn_decode_quiz((string)($r['quiz_json'] ?? ''));
			$r['skill'] = skykin_learn_skills()[$r['skill_key'] ?? ''] ?? (string)$r['skill_key'];
			$r['quiz_count'] = count($quiz);
			$r['quiz'] = $quiz;
			unset($r['quiz_json']);
		}
		unset($r);
		echo json_encode(['ok' => true, 'courses' => $rows, 'skills' => skykin_learn_skills()]);
		exit;
	}

	if ($op === 'learn_team') {
		sc_ops_need(['supervisor', 'admin', 'superadmin']);
		skykin_learn_ensure($db);
		$by = [];
		try {
			$du = sc_ops_domain_uuid($db, $dom);
			if ($du) {
				foreach (sc_ops_load_users($db, $du) as $u) {
					$exts = preg_split('/\s*,\s*/', trim((string)($u['extension'] ?? ''))) ?: [];
					$ext = preg_replace('/\D+/', '', (string)($exts[0] ?? ''));
					if ($ext === '') {
						continue;
					}
					$by[$ext] = [
						'agent_ext' => $ext,
						'agent_name' => (string)($u['username'] ?? $ext),
						'assigned' => 0,
						'passed' => 0,
						'best_pct' => 0,
					];
				}
			}
		} catch (Throwable $e) {
			$by = [];
		}
		$s = $db->prepare("SELECT a.agent_ext, a.agent_name,
			COUNT(*) AS assigned,
			SUM(CASE WHEN a.status='passed' THEN 1 ELSE 0 END) AS passed,
			MAX(a.last_pct) AS best_pct
			FROM skykin_learn_assign a
			WHERE a.domain_name=:d
			GROUP BY a.agent_ext, a.agent_name
			ORDER BY a.agent_name, a.agent_ext");
		$s->execute([':d' => $dom]);
		foreach ($s->fetchAll(PDO::FETCH_ASSOC) as $r) {
			$ext = (string)$r['agent_ext'];
			$prev = $by[$ext] ?? ['agent_ext' => $ext, 'agent_name' => $ext];
			$by[$ext] = [
				'agent_ext' => $ext,
				'agent_name' => (string)($r['agent_name'] ?: $prev['agent_name'] ?? $ext),
				'assigned' => (int)$r['assigned'],
				'passed' => (int)$r['passed'],
				'best_pct' => (int)$r['best_pct'],
			];
		}
		$team = array_values($by);
		usort($team, static function ($a, $b) {
			return strnatcasecmp((string)$a['agent_name'], (string)$b['agent_name']);
		});
		echo json_encode(['ok' => true, 'team' => $team]);
		exit;
	}

	if ($op === 'learn_save' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_ops_need(['supervisor', 'admin', 'superadmin']);
		skykin_learn_ensure($db);
		$title = trim((string)($body['title'] ?? ''));
		$skill = trim((string)($body['skill_key'] ?? 'knowledge'));
		if (!isset(skykin_learn_skills()[$skill])) {
			$skill = 'knowledge';
		}
		$lesson = trim((string)($body['body'] ?? ''));
		$quizIn = $body['quiz'] ?? [];
		$quiz = [];
		if (is_array($quizIn)) {
			foreach ($quizIn as $row) {
				if (!is_array($row)) {
					continue;
				}
				$qtxt = trim((string)($row['q'] ?? ''));
				$choices = array_values(array_filter(array_map('strval', is_array($row['choices'] ?? null) ? $row['choices'] : [])));
				$ans = (int)($row['answer'] ?? 0);
				if ($qtxt === '' || count($choices) < 2) {
					continue;
				}
				if ($ans < 0 || $ans >= count($choices)) {
					$ans = 0;
				}
				$quiz[] = ['q' => $qtxt, 'choices' => $choices, 'answer' => $ans];
			}
		}
		if ($title === '' || $lesson === '') {
			echo json_encode(['ok' => false, 'error' => 'Title and lesson text are required']);
			exit;
		}
		if (count($quiz) < 1) {
			echo json_encode(['ok' => false, 'error' => 'Add at least one quiz question']);
			exit;
		}
		$id = (int)($body['course_id'] ?? 0);
		$payload = json_encode($quiz, JSON_UNESCAPED_UNICODE);
		if ($id > 0) {
			$db->prepare('UPDATE skykin_learn_courses SET skill_key=:k, title=:t, body=:b, quiz_json=:q WHERE course_id=:id AND domain_name=:d')
				->execute([':k' => $skill, ':t' => $title, ':b' => $lesson, ':q' => $payload, ':id' => $id, ':d' => $dom]);
		} else {
			$db->prepare('INSERT INTO skykin_learn_courses (domain_name, skill_key, title, body, quiz_json, created_by) VALUES (:d,:k,:t,:b,:q,:c)')
				->execute([':d' => $dom, ':k' => $skill, ':t' => $title, ':b' => $lesson, ':q' => $payload, ':c' => $me]);
		}
		echo json_encode(['ok' => true]);
		exit;
	}

	if ($op === 'learn_assign' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_ops_need(['supervisor', 'admin', 'superadmin']);
		skykin_learn_ensure($db);
		$ext = trim((string)($body['agent_ext'] ?? ''));
		$name = trim((string)($body['agent_name'] ?? $ext));
		$cid = (int)($body['course_id'] ?? 0);
		if ($ext === '' || $cid < 1) {
			echo json_encode(['ok' => false, 'error' => 'Agent and course required']);
			exit;
		}
		skykin_learn_assign_one($db, $dom, $ext, $name, $cid, 'supervisor');
		echo json_encode(array_merge(['ok' => true], skykin_learn_agent_pack($db, $dom, $ext)));
		exit;
	}

	if ($op === 'learn_course') {
		skykin_learn_ensure($db);
		$cid = (int)($_GET['course_id'] ?? $body['course_id'] ?? 0);
		$ext = trim((string)($_GET['ext'] ?? $body['agent_ext'] ?? ''));
		$s = $db->prepare("SELECT * FROM skykin_learn_courses WHERE course_id=:id AND (domain_name=:d OR domain_name='' OR domain_name IS NULL) LIMIT 1");
		$s->execute([':id' => $cid, ':d' => $dom]);
		$row = $s->fetch(PDO::FETCH_ASSOC);
		if (!$row) {
			echo json_encode(['ok' => false, 'error' => 'Course not found']);
			exit;
		}
		$quiz = skykin_learn_decode_quiz((string)$row['quiz_json']);
		$have = sc_ops_groups();
		$sup = in_array('supervisor', $have, true) || in_array('admin', $have, true) || in_array('superadmin', $have, true);
		$asg = null;
		if ($ext !== '') {
			$a = $db->prepare('SELECT * FROM skykin_learn_assign WHERE domain_name=:d AND agent_ext=:e AND course_id=:c LIMIT 1');
			$a->execute([':d' => $dom, ':e' => $ext, ':c' => $cid]);
			$asg = $a->fetch(PDO::FETCH_ASSOC) ?: null;
		}
		echo json_encode([
			'ok' => true,
			'course' => [
				'course_id' => (int)$row['course_id'],
				'title' => $row['title'],
				'skill_key' => $row['skill_key'],
				'skill' => skykin_learn_skills()[$row['skill_key']] ?? $row['skill_key'],
				'body' => $row['body'],
				'quiz' => $sup ? $quiz : skykin_learn_public_quiz($quiz),
				'quiz_count' => count($quiz),
			],
			'assignment' => $asg,
		]);
		exit;
	}

	if ($op === 'learn_quiz' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		skykin_learn_ensure($db);
		$cid = (int)($body['course_id'] ?? 0);
		$ext = trim((string)($body['agent_ext'] ?? $_GET['ext'] ?? ''));
		$answers = is_array($body['answers'] ?? null) ? $body['answers'] : [];
		if ($ext === '' || $cid < 1) {
			echo json_encode(['ok' => false, 'error' => 'Course and agent required']);
			exit;
		}
		$c = $db->prepare("SELECT * FROM skykin_learn_courses WHERE course_id=:id AND (domain_name=:d OR domain_name='' OR domain_name IS NULL) LIMIT 1");
		$c->execute([':id' => $cid, ':d' => $dom]);
		$course = $c->fetch(PDO::FETCH_ASSOC);
		if (!$course) {
			echo json_encode(['ok' => false, 'error' => 'Course not found']);
			exit;
		}
		$a = $db->prepare('SELECT * FROM skykin_learn_assign WHERE domain_name=:d AND agent_ext=:e AND course_id=:c LIMIT 1');
		$a->execute([':d' => $dom, ':e' => $ext, ':c' => $cid]);
		$asg = $a->fetch(PDO::FETCH_ASSOC);
		if (!$asg) {
			echo json_encode(['ok' => false, 'error' => 'This course is not assigned to you']);
			exit;
		}
		$quiz = skykin_learn_decode_quiz((string)$course['quiz_json']);
		$n = count($quiz);
		$right = 0;
		foreach ($quiz as $i => $row) {
			$want = (int)($row['answer'] ?? 0);
			$got = (int)($answers[$i] ?? -1);
			if ($got === $want) {
				$right++;
			}
		}
		$pct = $n ? (int)round($right / $n * 100) : 0;
		$pass = $pct >= 70 ? 1 : 0;
		$status = $pass ? 'passed' : 'failed';
		$db->prepare('INSERT INTO skykin_learn_attempts (assign_id, pct, passed) VALUES (:a,:p,:ok)')
			->execute([':a' => $asg['assign_id'], ':p' => $pct, ':ok' => $pass]);
		$nowSql = ($db->getAttribute(PDO::ATTR_DRIVER_NAME) === 'sqlite') ? 'CURRENT_TIMESTAMP' : 'NOW()';
		$db->prepare("UPDATE skykin_learn_assign SET status=:s, last_pct=:p, completed_at={$nowSql} WHERE assign_id=:id")
			->execute([':s' => $status, ':p' => $pct, ':id' => $asg['assign_id']]);
		echo json_encode([
			'ok' => true,
			'pct' => $pct,
			'right' => $right,
			'total' => $n,
			'passed' => (bool)$pass,
			'status' => $status,
		]);
		exit;
	}

	if ($op === 'survey_submit' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_ops_surveys($db);
		$rating = max(1, min(5, (int)($body['rating'] ?? 0)));
		$ch = trim((string)($body['channel'] ?? 'Voice')) ?: 'Voice';
		$resolved = trim((string)($body['resolved'] ?? ''));
		$comment = trim((string)($body['comment'] ?? ''));
		$ext = trim((string)($body['agent_ext'] ?? ''));
		$db->prepare("INSERT INTO skykin_surveys (domain_name, agent_ext, agent_name, channel, rating, resolved, comment)
			VALUES (:d,:e,:n,:c,:r,:rv,:cm)")
			->execute([
				':d' => $dom,
				':e' => $ext,
				':n' => $me,
				':c' => $ch,
				':r' => $rating,
				':rv' => $resolved,
				':cm' => $comment,
			]);
		echo json_encode(['ok' => true]);
		exit;
	}

	if ($op === 'surveys') {
		sc_ops_need(['supervisor', 'admin', 'superadmin']);
		sc_ops_surveys($db);
		$rows = [];
		try {
			$s = $db->prepare("SELECT * FROM skykin_surveys WHERE domain_name = :d ORDER BY survey_id DESC LIMIT 200");
			$s->execute([':d' => $dom]);
			$rows = $s->fetchAll(PDO::FETCH_ASSOC);
		} catch (Throwable $e) {
			$rows = [];
		}
		$n = count($rows);
		$avg = 0;
		$resolvedYes = 0;
		foreach ($rows as $r) {
			$avg += (int)($r['rating'] ?? 0);
			if (strcasecmp((string)($r['resolved'] ?? ''), 'yes') === 0) {
				$resolvedYes++;
			}
		}
		$csatContacts = 0.0;
		$csatN = 0;
		try {
			$c = $db->query("SELECT AVG(csat) AS a, COUNT(csat) AS n FROM skykin_contacts WHERE csat IS NOT NULL");
			$row = $c ? $c->fetch(PDO::FETCH_ASSOC) : null;
			$csatContacts = (float)($row['a'] ?? 0);
			$csatN = (int)($row['n'] ?? 0);
		} catch (Throwable $e) {
			/* ignore */
		}
		$csat = $n ? round($avg / $n, 2) : round($csatContacts, 2);
		$nps = 0;
		if ($n) {
			$prom = 0;
			$det = 0;
			foreach ($rows as $r) {
				$rt = (int)($r['rating'] ?? 0);
				if ($rt >= 5) {
					$prom++;
				} elseif ($rt <= 2) {
					$det++;
				}
			}
			$nps = (int)round((($prom - $det) / $n) * 100);
		}
		echo json_encode([
			'ok' => true,
			'rows' => $rows,
			'csat' => $csat,
			'nps' => $nps,
			'response_n' => $n,
			'crm_csat_n' => $csatN,
			'resolved_rate' => $n ? round($resolvedYes / $n * 100) : 0,
		]);
		exit;
	}

	if ($op === 'reasons') {
		sc_ops_need(['supervisor', 'admin', 'superadmin']);
		skykin_crm_ensure_cases($db);
		$rows = $db->query("SELECT COALESCE(NULLIF(issue_type,''),'Unspecified') AS reason, COUNT(*) AS calls
			FROM skykin_cases GROUP BY 1 ORDER BY calls DESC LIMIT 30")->fetchAll(PDO::FETCH_ASSOC);
		echo json_encode(['ok' => true, 'reasons' => $rows]);
		exit;
	}

	if ($op === 'studio') {
		sc_ops_need(['admin', 'superadmin']);
		$du = sc_ops_domain_uuid($db, $dom);
		$ivr = [];
		$ivrOpts = [];
		$queues = [];
		$flows = [];
		$recordings = [];
		$users = [];
		$extensions = [];
		$nextExt = '';
		$nextServiceExt = '';
		$roles = [];
		$permCatalog = [];
		$didRoutes = [];
		$notes = [];
		if ($du) {
			try {
				$s = $db->prepare("SELECT ivr_menu_uuid, ivr_menu_name, ivr_menu_extension, ivr_menu_enabled, ivr_menu_description
					FROM v_ivr_menus WHERE domain_uuid = :u ORDER BY ivr_menu_name");
				$s->execute([':u' => $du]);
				$ivr = $s->fetchAll(PDO::FETCH_ASSOC);
				$s2 = $db->prepare("SELECT o.ivr_menu_option_uuid, o.ivr_menu_uuid, o.ivr_menu_option_digits AS digits,
					o.ivr_menu_option_action AS action, o.ivr_menu_option_param AS param,
					o.ivr_menu_option_description AS description
					FROM v_ivr_menu_options o
					JOIN v_ivr_menus m ON m.ivr_menu_uuid = o.ivr_menu_uuid
					WHERE m.domain_uuid = :u
					ORDER BY o.ivr_menu_option_digits");
				$s2->execute([':u' => $du]);
				$ivrOpts = $s2->fetchAll(PDO::FETCH_ASSOC);
			} catch (Throwable $e) {
				$notes[] = 'IVR: ' . $e->getMessage();
			}
			try {
				$s = $db->prepare("SELECT call_center_queue_uuid, queue_name, queue_extension, queue_strategy, queue_moh_sound
					FROM v_call_center_queues WHERE domain_uuid = :u ORDER BY queue_extension");
				$s->execute([':u' => $du]);
				$queues = $s->fetchAll(PDO::FETCH_ASSOC);
				$members = sc_ops_queue_members($db, $du);
				$qskills = sc_ops_load_queue_skills($db, $du);
				foreach ($queues as &$q) {
					$qid = (string)($q['call_center_queue_uuid'] ?? '');
					$q['member_uuids'] = $members[$qid] ?? [];
					$q['required_skill'] = $qskills[$qid] ?? '';
				}
				unset($q);
			} catch (Throwable $e) {
				$notes[] = 'Queues: ' . $e->getMessage();
			}
			try {
				$s = $db->prepare("SELECT call_flow_uuid, call_flow_name, call_flow_extension, call_flow_status, call_flow_label, call_flow_feature_code
					FROM v_call_flows WHERE domain_uuid = :u ORDER BY call_flow_name");
				$s->execute([':u' => $du]);
				$flows = $s->fetchAll(PDO::FETCH_ASSOC);
			} catch (Throwable $e) {
				$notes[] = 'Flows: ' . $e->getMessage();
			}
			try {
				$s = $db->prepare("SELECT recording_uuid, recording_name, recording_filename, recording_description
					FROM v_recordings WHERE domain_uuid = :u ORDER BY recording_name LIMIT 80");
				$s->execute([':u' => $du]);
				$recordings = $s->fetchAll(PDO::FETCH_ASSOC);
			} catch (Throwable $e) {
				$notes[] = 'Recordings: ' . $e->getMessage();
			}
			try {
				$users = sc_ops_load_users($db, $du);
			} catch (Throwable $e) {
				$notes[] = 'Users: ' . $e->getMessage();
			}
			try {
				$s = $db->prepare("SELECT extension_uuid, extension, effective_caller_id_name, enabled
					FROM v_extensions WHERE domain_uuid = :u ORDER BY extension");
				$s->execute([':u' => $du]);
				$extensions = $s->fetchAll(PDO::FETCH_ASSOC);
				$nextExt = sc_ops_next_ext($db, $du);
			} catch (Throwable $e) {
				$notes[] = 'Extensions: ' . $e->getMessage();
			}
			$nextServiceExt = sc_ops_next_service_ext($db, $du);
			try {
				$pack = sc_ops_load_roles($db, $du);
				$roles = $pack['roles'];
				$permCatalog = $pack['catalog'];
			} catch (Throwable $e) {
				$notes[] = 'Roles: ' . $e->getMessage();
			}
			try {
				sc_ops_ensure_did_table($db);
				$ds = $db->prepare('SELECT route_id, did, dest_ext, dest_kind FROM skykin_did_routes WHERE domain_name = :n ORDER BY did');
				$ds->execute([':n' => $dom]);
				$didRoutes = $ds->fetchAll(PDO::FETCH_ASSOC);
			} catch (Throwable $e) {
				$notes[] = 'DID: ' . $e->getMessage();
			}
		} else {
			$notes[] = 'Domain UUID not found for ' . $dom;
		}
		echo json_encode([
			'ok' => true,
			'domain' => $dom ?: (string)($_SESSION['domain_name'] ?? ''),
			'ivr' => $ivr,
			'ivr_options' => $ivrOpts,
			'queues' => $queues,
			'flows' => $flows,
			'recordings' => $recordings,
			'users' => $users,
			'extensions' => $extensions,
			'next_extension' => $nextExt,
			'next_service_extension' => $nextServiceExt ?? '',
			'roles' => $roles,
			'permission_catalog' => $permCatalog,
			'skills' => $du ? sc_ops_skill_catalog($db) : sc_ops_default_skills(),
			'did_routes' => $didRoutes,
			'notes' => $notes,
			'settings' => [
				'session_idle_minutes' => skykin_idle_timeout_minutes(),
				'biz_hours' => sc_ops_biz_hours_get($dom ?: (string)($_SESSION['domain_name'] ?? '')),
			],
		]);
		exit;
	}

	if ($op === 'user_save' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_ops_need(['admin', 'superadmin']);
		$du = sc_ops_domain_uuid($db, $dom);
		if (!$du) {
			echo json_encode(['ok' => false, 'error' => 'Domain not found']);
			exit;
		}
		$allowSuper = in_array('superadmin', sc_ops_groups(), true);
		$uuid = trim((string)($body['user_uuid'] ?? ''));
		$username = trim((string)($body['username'] ?? ''));
		$email = trim((string)($body['user_email'] ?? ''));
		$password = (string)($body['password'] ?? '');
		$enabled = sc_ops_truthy($body['user_enabled'] ?? true);
		$groups = $body['group_list'] ?? $body['groups'] ?? [];
		if (is_string($groups)) {
			$groups = array_filter(array_map('trim', explode(',', $groups)));
		}
		if (!is_array($groups)) {
			$groups = [];
		}
		$ext = trim((string)($body['extension'] ?? ''));
		$createExt = sc_ops_truthy($body['create_extension'] ?? false);
		$sipPass = trim((string)($body['sip_password'] ?? ''));
		if ($uuid === '') {
			if ($username === '' || $password === '') {
				echo json_encode(['ok' => false, 'error' => 'Username and password required']);
				exit;
			}
			if (strlen($password) < 12) {
				echo json_encode(['ok' => false, 'error' => 'Password must be at least 12 characters']);
				exit;
			}
			$chk = $db->prepare('SELECT 1 FROM v_users WHERE domain_uuid = :d AND lower(username) = lower(:n) LIMIT 1');
			$chk->execute([':d' => $du, ':n' => $username]);
			if ($chk->fetchColumn()) {
				echo json_encode(['ok' => false, 'error' => 'Username already exists']);
				exit;
			}
			$uuid = sc_ops_uuid();
			$db->prepare(
				"INSERT INTO v_users (user_uuid, domain_uuid, username, password, user_email, user_enabled, user_type, add_user, add_date)
				 VALUES (:id, :d, :n, :p, :e, :en, 'default', :who, NOW())"
			)->execute([
				':id' => $uuid,
				':d' => $du,
				':n' => $username,
				':p' => password_hash($password, PASSWORD_DEFAULT),
				':e' => $email,
				':en' => $enabled ? 'true' : 'false',
				':who' => $me,
			]);
		} else {
			$row = $db->prepare('SELECT user_uuid, username FROM v_users WHERE user_uuid = :id AND domain_uuid = :d LIMIT 1');
			$row->execute([':id' => $uuid, ':d' => $du]);
			$exist = $row->fetch(PDO::FETCH_ASSOC);
			if (!$exist) {
				echo json_encode(['ok' => false, 'error' => 'User not found']);
				exit;
			}
			if ($username === '') {
				$username = (string)$exist['username'];
			}
			$sql = "UPDATE v_users SET username = :n, user_email = :e, user_enabled = :en WHERE user_uuid = :id AND domain_uuid = :d";
			$params = [
				':n' => $username,
				':e' => $email,
				':en' => $enabled ? 'true' : 'false',
				':id' => $uuid,
				':d' => $du,
			];
			$db->prepare($sql)->execute($params);
			if ($password !== '') {
				if (strlen($password) < 12) {
					echo json_encode(['ok' => false, 'error' => 'Password must be at least 12 characters']);
					exit;
				}
				$db->prepare('UPDATE v_users SET password = :p WHERE user_uuid = :id')
					->execute([':p' => password_hash($password, PASSWORD_DEFAULT), ':id' => $uuid]);
			}
		}
		sc_ops_set_user_groups($db, $du, $uuid, $groups, $allowSuper);
		$extInfo = null;
		if ($ext !== '') {
			if (!preg_match('/^\d{2,8}$/', $ext)) {
				echo json_encode(['ok' => false, 'error' => 'Extension must be 2–8 digits']);
				exit;
			}
			$extInfo = sc_ops_ensure_extension($db, $du, $dom ?: (string)($_SESSION['domain_name'] ?? ''), $ext, $uuid, $username, $sipPass, $createExt);
			if (empty($extInfo['ok'])) {
				echo json_encode(['ok' => false, 'error' => $extInfo['error'] ?? 'Could not set extension']);
				exit;
			}
		}
		echo json_encode([
			'ok' => true,
			'user_uuid' => $uuid,
			'users' => sc_ops_load_users($db, $du),
			'extension' => $extInfo,
		]);
		exit;
	}

	if ($op === 'group_save' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_ops_need(['admin', 'superadmin']);
		$du = sc_ops_domain_uuid($db, $dom);
		if (!$du) {
			echo json_encode(['ok' => false, 'error' => 'Domain not found']);
			exit;
		}
		$allowSuper = in_array('superadmin', sc_ops_groups(), true);
		$gid = trim((string)($body['group_uuid'] ?? ''));
		$name = strtolower(trim((string)($body['group_name'] ?? '')));
		$name = preg_replace('/[^a-z0-9_\- ]/', '', $name);
		$name = trim(str_replace(' ', '_', $name));
		$desc = trim((string)($body['group_description'] ?? ''));
		$level = (int)($body['group_level'] ?? 20);
		if ($level < 10) {
			$level = 10;
		}
		if ($level > 50 && !$allowSuper) {
			$level = 50;
		}
		$perms = $body['permissions'] ?? [];
		if (!is_array($perms)) {
			$perms = [];
		}
		$perms = array_values(array_unique(array_filter(array_map('strval', $perms))));
		$clone = trim((string)($body['clone_from'] ?? ''));
		if ($clone !== '' && $perms === []) {
			$c = $db->prepare(
				"SELECT permission_name FROM v_group_permissions
				 WHERE group_uuid = :g AND (permission_assigned = 'true' OR permission_assigned IS TRUE)"
			);
			$c->execute([':g' => $clone]);
			$perms = array_column($c->fetchAll(PDO::FETCH_ASSOC), 'permission_name');
		}
		$locked = ['superadmin', 'public'];
		if ($gid === '') {
			if ($name === '' || in_array($name, $locked, true)) {
				echo json_encode(['ok' => false, 'error' => 'Choose a role name (not superadmin)']);
				exit;
			}
			$exists = $db->prepare(
				"SELECT 1 FROM v_groups WHERE lower(group_name) = :n AND (domain_uuid IS NULL OR domain_uuid = :d) LIMIT 1"
			);
			$exists->execute([':n' => $name, ':d' => $du]);
			if ($exists->fetchColumn()) {
				echo json_encode(['ok' => false, 'error' => 'Role name already exists']);
				exit;
			}
			$gid = sc_ops_uuid();
			$db->prepare(
				"INSERT INTO v_groups (group_uuid, domain_uuid, group_name, group_level, group_protected, group_description)
				 VALUES (:id, :d, :n, :lv, false, :ds)"
			)->execute([':id' => $gid, ':d' => $du, ':n' => $name, ':lv' => $level, ':ds' => $desc]);
		} else {
			$row = $db->prepare('SELECT group_uuid, group_name, domain_uuid FROM v_groups WHERE group_uuid = :id LIMIT 1');
			$row->execute([':id' => $gid]);
			$exist = $row->fetch(PDO::FETCH_ASSOC);
			if (!$exist) {
				echo json_encode(['ok' => false, 'error' => 'Role not found']);
				exit;
			}
			$gname = strtolower((string)$exist['group_name']);
			if ($gname === 'superadmin' && !$allowSuper) {
				echo json_encode(['ok' => false, 'error' => 'Cannot edit superadmin']);
				exit;
			}
			if (empty($exist['domain_uuid']) && !$allowSuper) {
				echo json_encode(['ok' => false, 'error' => 'Global FusionPBX roles are read-only here. Create a new role and clone permissions.']);
				exit;
			}
			if ($name === '') {
				$name = $gname;
			}
			$db->prepare(
				"UPDATE v_groups SET group_name = :n, group_level = :lv, group_description = :ds WHERE group_uuid = :id"
			)->execute([':n' => $name, ':lv' => $level, ':ds' => $desc, ':id' => $gid]);
		}
		$valid = [];
		try {
			$all = $db->query('SELECT permission_name FROM v_permissions')->fetchAll(PDO::FETCH_COLUMN);
			$ok = array_fill_keys($all, true);
			foreach ($perms as $p) {
				if (isset($ok[$p])) {
					$valid[] = $p;
				}
			}
		} catch (Throwable $e) {
			$valid = $perms;
		}
		$cur = $db->prepare('SELECT group_permission_uuid, permission_name FROM v_group_permissions WHERE group_uuid = :g');
		$cur->execute([':g' => $gid]);
		$have = [];
		foreach ($cur->fetchAll(PDO::FETCH_ASSOC) as $r) {
			$have[(string)$r['permission_name']] = (string)$r['group_permission_uuid'];
		}
		$want = array_fill_keys($valid, true);
		foreach ($have as $p => $id) {
			if (!isset($want[$p])) {
				$db->prepare('DELETE FROM v_group_permissions WHERE group_permission_uuid = :x')->execute([':x' => $id]);
			}
		}
		$gnameFinal = $name;
		foreach ($want as $p => $_) {
			if (isset($have[$p])) {
				$db->prepare(
					"UPDATE v_group_permissions SET permission_assigned = 'true', group_name = :n WHERE group_permission_uuid = :x"
				)->execute([':n' => $gnameFinal, ':x' => $have[$p]]);
				continue;
			}
			$db->prepare(
				"INSERT INTO v_group_permissions (group_permission_uuid, domain_uuid, permission_name, permission_assigned, group_name, group_uuid)
				 VALUES (:id, :d, :p, 'true', :n, :g)"
			)->execute([':id' => sc_ops_uuid(), ':d' => $du, ':p' => $p, ':n' => $gnameFinal, ':g' => $gid]);
		}
		$pack = sc_ops_load_roles($db, $du);
		echo json_encode(['ok' => true, 'group_uuid' => $gid, 'roles' => $pack['roles']]);
		exit;
	}

	if ($op === 'group_delete' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_ops_need(['admin', 'superadmin']);
		$du = sc_ops_domain_uuid($db, $dom);
		if (!$du) {
			echo json_encode(['ok' => false, 'error' => 'Domain not found']);
			exit;
		}
		$gid = trim((string)($body['group_uuid'] ?? ''));
		if ($gid === '') {
			echo json_encode(['ok' => false, 'error' => 'Role not selected']);
			exit;
		}
		$row = $db->prepare(
			'SELECT group_uuid, group_name, domain_uuid, group_protected FROM v_groups WHERE group_uuid = :id LIMIT 1'
		);
		try {
			$row->execute([':id' => $gid]);
			$exist = $row->fetch(PDO::FETCH_ASSOC);
		} catch (Throwable $e) {
			$row = $db->prepare('SELECT group_uuid, group_name, domain_uuid FROM v_groups WHERE group_uuid = :id LIMIT 1');
			$row->execute([':id' => $gid]);
			$exist = $row->fetch(PDO::FETCH_ASSOC);
		}
		if (!$exist) {
			echo json_encode(['ok' => false, 'error' => 'Role not found']);
			exit;
		}
		$gname = strtolower((string)$exist['group_name']);
		$locked = ['superadmin', 'public', 'agent', 'supervisor', 'admin'];
		if (in_array($gname, $locked, true)) {
			echo json_encode(['ok' => false, 'error' => 'Cannot delete built-in role ' . $gname]);
			exit;
		}
		if (empty($exist['domain_uuid']) || (string)$exist['domain_uuid'] !== $du) {
			echo json_encode(['ok' => false, 'error' => 'Only roles created on this domain can be deleted']);
			exit;
		}
		if (sc_ops_truthy($exist['group_protected'] ?? false)) {
			echo json_encode(['ok' => false, 'error' => 'Protected role']);
			exit;
		}
		$db->prepare('DELETE FROM v_user_groups WHERE group_uuid = :g AND domain_uuid = :d')->execute([':g' => $gid, ':d' => $du]);
		try {
			$db->prepare('DELETE FROM v_group_permissions WHERE group_uuid = :g')->execute([':g' => $gid]);
		} catch (Throwable $e) {
			echo json_encode(['ok' => false, 'error' => 'Could not clear permissions']);
			exit;
		}
		$db->prepare('DELETE FROM v_groups WHERE group_uuid = :g AND domain_uuid = :d')->execute([':g' => $gid, ':d' => $du]);
		$pack = sc_ops_load_roles($db, $du);
		echo json_encode(['ok' => true, 'roles' => $pack['roles'], 'users' => sc_ops_load_users($db, $du)]);
		exit;
	}

	if ($op === 'ivr_save' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_ops_need(['admin', 'superadmin']);
		$du = sc_ops_domain_uuid($db, $dom);
		$id = trim((string)($body['ivr_menu_uuid'] ?? ''));
		if (!$du) {
			echo json_encode(['ok' => false, 'error' => 'Domain not found']);
			exit;
		}
		$name = trim((string)($body['ivr_menu_name'] ?? ''));
		$enabled = sc_ops_truthy($body['ivr_menu_enabled'] ?? true) ? 'true' : 'false';
		$desc = trim((string)($body['ivr_menu_description'] ?? ''));
		if ($id === '') {
			if ($name === '') {
				echo json_encode(['ok' => false, 'error' => 'IVR name required']);
				exit;
			}
			$ext = preg_replace('/\D+/', '', (string)($body['ivr_menu_extension'] ?? ''));
			$greet = trim((string)($body['ivr_menu_greet_long'] ?? ''));
			$made = sc_ops_ivr_create_menu($db, $du, $dom, $name, $ext, $greet, $desc);
			$id = $made['ivr_menu_uuid'];
			$ext = $made['ivr_menu_extension'];
			$branches = $body['branches'] ?? [];
			if (is_array($branches) && $branches) {
				sc_ops_ivr_save_branches($db, $du, $dom, $id, $branches);
			}
			echo json_encode(['ok' => true, 'ivr_menu_uuid' => $id, 'ivr_menu_extension' => $ext, 'created' => true, 'reload' => sc_ops_reload_xml()]);
			exit;
		}
		$db->prepare(
			"UPDATE v_ivr_menus SET ivr_menu_name = COALESCE(NULLIF(:n,''), ivr_menu_name),
				ivr_menu_enabled = :en, ivr_menu_description = :ds
			 WHERE ivr_menu_uuid = :id AND domain_uuid = :d"
		)->execute([':n' => $name, ':en' => $enabled, ':ds' => $desc, ':id' => $id, ':d' => $du]);
		echo json_encode(['ok' => true, 'reload' => sc_ops_reload_xml()]);
		exit;
	}

	if ($op === 'ivr_option_save' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_ops_need(['admin', 'superadmin']);
		$du = sc_ops_domain_uuid($db, $dom);
		$opt = trim((string)($body['ivr_menu_option_uuid'] ?? ''));
		$menu = trim((string)($body['ivr_menu_uuid'] ?? ''));
		$digits = trim((string)($body['digits'] ?? ''));
		$action = trim((string)($body['action'] ?? 'menu-exec-app'));
		$param = trim((string)($body['param'] ?? ''));
		$desc = trim((string)($body['description'] ?? ''));
		if (!$du) {
			echo json_encode(['ok' => false, 'error' => 'Domain not found']);
			exit;
		}
		if ($opt !== '') {
			$db->prepare(
				"UPDATE v_ivr_menu_options SET ivr_menu_option_digits = COALESCE(NULLIF(:dig,''), ivr_menu_option_digits),
					ivr_menu_option_action = COALESCE(NULLIF(:a,''), ivr_menu_option_action),
					ivr_menu_option_param = :p, ivr_menu_option_description = :ds
				 WHERE ivr_menu_option_uuid = :id"
			)->execute([':dig' => $digits, ':a' => $action, ':p' => $param, ':ds' => $desc, ':id' => $opt]);
			echo json_encode(['ok' => true, 'ivr_menu_option_uuid' => $opt, 'reload' => sc_ops_reload_xml()]);
			exit;
		}
		if ($menu === '' || $digits === '') {
			echo json_encode(['ok' => false, 'error' => 'Digit and menu required']);
			exit;
		}
		$subName = trim((string)($body['new_submenu'] ?? $body['submenu'] ?? ''));
		if ($subName !== '') {
			$child = sc_ops_ivr_create_menu($db, $du, $dom, $subName, '', '', $desc !== '' ? $desc : ('Submenu of ' . $subName));
			$param = sc_ops_ivr_transfer_param($child['ivr_menu_extension']);
			if ($desc === '') {
				$desc = 'submenu ' . $subName;
			}
		}
		if ($param === '') {
			echo json_encode(['ok' => false, 'error' => 'Destination or new submenu required']);
			exit;
		}
		$opt = sc_ops_ivr_add_option($db, $du, $menu, $digits, $param, $desc, $action);
		echo json_encode(['ok' => true, 'ivr_menu_option_uuid' => $opt, 'reload' => sc_ops_reload_xml()]);
		exit;
	}

	if ($op === 'queue_save' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_ops_need(['admin', 'superadmin']);
		$du = sc_ops_domain_uuid($db, $dom);
		$id = trim((string)($body['call_center_queue_uuid'] ?? ''));
		if (!$du) {
			echo json_encode(['ok' => false, 'error' => 'Domain not found']);
			exit;
		}
		$strategy = trim((string)($body['queue_strategy'] ?? ''));
		$moh = trim((string)($body['queue_moh_sound'] ?? ''));
		$name = trim((string)($body['queue_name'] ?? ''));
		$ok = ['longest-idle-agent', 'round-robin', 'ring-all', 'top-down', 'agent-with-least-talk-time', 'agent-with-fewest-calls', 'sequentially-by-agent-order', 'random'];
		if ($strategy !== '' && !in_array($strategy, $ok, true)) {
			echo json_encode(['ok' => false, 'error' => 'Unknown strategy']);
			exit;
		}
		if ($id === '') {
			if ($name === '') {
				echo json_encode(['ok' => false, 'error' => 'Queue name required']);
				exit;
			}
			$ext = preg_replace('/\D+/', '', (string)($body['queue_extension'] ?? ''));
			if ($ext === '') {
				$ext = sc_ops_next_service_ext($db, $du, 9010);
			}
			if ($strategy === '') {
				$strategy = 'longest-idle-agent';
			}
			if ($moh === '') {
				$moh = 'local_stream://default';
			}
			$id = sc_ops_uuid();
			$dp = sc_ops_uuid();
			$xml = "<extension name=\"".sc_ops_esc_xml($name)."\" continue=\"false\" uuid=\"".sc_ops_esc_xml($dp)."\">\n"
				."	<condition field=\"destination_number\" expression=\"^(callcenter\\+)?".sc_ops_esc_xml($ext)."$\">\n"
				."		<action application=\"answer\" data=\"\"/>\n"
				."		<action application=\"set\" data=\"hangup_after_bridge=true\"/>\n"
				."		<action application=\"callcenter\" data=\"".sc_ops_esc_xml($ext)."@".sc_ops_esc_xml($dom)."\"/>\n"
				."	</condition>\n"
				."</extension>\n";
			try {
				sc_ops_put_dialplan($db, $du, $dom, $dp, $name, $ext, $xml, '230', '95788e50-9500-079e-2807-fd530b0ea370');
			} catch (Throwable $e) {
				$dp = '';
			}
			$db->prepare(
				"INSERT INTO v_call_center_queues (
					call_center_queue_uuid, domain_uuid, dialplan_uuid, queue_name, queue_extension,
					queue_strategy, queue_moh_sound, queue_record_template, queue_time_base_score,
					queue_max_wait_time, queue_max_wait_time_with_no_agent, queue_max_wait_time_with_no_agent_time_reached,
					queue_tier_rules_apply, queue_tier_rule_wait_second, queue_tier_rule_wait_multiply_level,
					queue_tier_rule_no_agent_no_wait, queue_discard_abandoned_after, queue_abandoned_resume_allowed,
					queue_context, queue_description, queue_language, queue_dialect, queue_voice
				) VALUES (
					:id, :d, :dp, :n, :e,
					:s, :m, '', 'system',
					0, 0, 0,
					false, 30, false,
					false, 60, false,
					:ctx, :ds, 'en', 'us', 'callie'
				)"
			)->execute([
				':id' => $id,
				':d' => $du,
				':dp' => $dp !== '' ? $dp : null,
				':n' => $name,
				':e' => $ext,
				':s' => $strategy,
				':m' => $moh,
				':ctx' => $dom,
				':ds' => 'SkyConnect queue',
			]);
			$skill = strtolower(trim((string)($body['required_skill'] ?? $body['skill'] ?? '')));
			if ($skill !== '') {
				sc_ops_set_queue_skill($db, $du, $id, $skill);
				sc_ops_sync_skill_queues($db, $du, $dom);
			}
			echo json_encode(['ok' => true, 'call_center_queue_uuid' => $id, 'queue_extension' => $ext, 'created' => true]);
			exit;
		}
		$db->prepare(
			"UPDATE v_call_center_queues
			 SET queue_name = COALESCE(NULLIF(:n,''), queue_name),
			     queue_strategy = COALESCE(NULLIF(:s,''), queue_strategy),
			     queue_moh_sound = :m
			 WHERE call_center_queue_uuid = :id AND domain_uuid = :d"
		)->execute([':n' => $name, ':s' => $strategy, ':m' => $moh, ':id' => $id, ':d' => $du]);
		if (array_key_exists('required_skill', $body) || array_key_exists('skill', $body)) {
			sc_ops_set_queue_skill($db, $du, $id, (string)($body['required_skill'] ?? $body['skill'] ?? ''));
			sc_ops_sync_skill_queues($db, $du, $dom);
		}
		echo json_encode(['ok' => true]);
		exit;
	}

	if ($op === 'flow_save' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_ops_need(['admin', 'superadmin']);
		$du = sc_ops_domain_uuid($db, $dom);
		$id = trim((string)($body['call_flow_uuid'] ?? ''));
		if (!$du) {
			echo json_encode(['ok' => false, 'error' => 'Domain not found']);
			exit;
		}
		$status = sc_ops_truthy($body['call_flow_status'] ?? true) ? 'true' : 'false';
		$label = trim((string)($body['call_flow_label'] ?? ''));
		if ($id === '') {
			$name = trim((string)($body['call_flow_name'] ?? ''));
			if ($name === '') {
				echo json_encode(['ok' => false, 'error' => 'Flow name required']);
				exit;
			}
			$ext = preg_replace('/\D+/', '', (string)($body['call_flow_extension'] ?? ''));
			if ($ext === '') {
				$ext = sc_ops_next_service_ext($db, $du, 9020);
			}
			$feat = trim((string)($body['call_flow_feature_code'] ?? ''));
			if ($feat === '') {
				$feat = '*28';
			}
			$day = trim((string)($body['call_flow_data'] ?? ''));
			$night = trim((string)($body['call_flow_alternate_data'] ?? ''));
			if ($day === '') {
				$day = 'transfer:9000 XML ' . $dom;
			}
			if ($night === '') {
				$night = $day;
			}
			if ($label === '') {
				$label = 'Day';
			}
			$altLabel = trim((string)($body['call_flow_alternate_label'] ?? 'Night'));
			$id = sc_ops_uuid();
			$dp = sc_ops_uuid();
			$xml = "<extension name=\"".sc_ops_esc_xml($name)."\" continue=\"false\" uuid=\"".sc_ops_esc_xml($dp)."\">\n"
				."	<condition field=\"destination_number\" expression=\"^".sc_ops_esc_xml($ext)."\$\">\n"
				."		<action application=\"set\" data=\"call_flow_uuid=".sc_ops_esc_xml($id)."\"/>\n"
				."		<action application=\"lua\" data=\"call_flow.lua\"/>\n"
				."	</condition>\n"
				."</extension>\n";
			try {
				sc_ops_put_dialplan($db, $du, $dom, $dp, $name, $ext, $xml, '141', 'b1b70f85-e0e3-4c22-8b25-1d40b4e4c44d');
			} catch (Throwable $e) {
				$dp = '';
			}
			$db->prepare(
				"INSERT INTO v_call_flows (
					call_flow_uuid, domain_uuid, dialplan_uuid, call_flow_name, call_flow_extension,
					call_flow_feature_code, call_flow_context, call_flow_status, call_flow_label,
					call_flow_app, call_flow_data, call_flow_alternate_label, call_flow_alternate_app, call_flow_alternate_data
				) VALUES (
					:id, :d, :dp, :n, :e, :f, :ctx, :st, :lb, 'transfer', :day, :al, 'transfer', :night
				)"
			)->execute([
				':id' => $id,
				':d' => $du,
				':dp' => $dp !== '' ? $dp : null,
				':n' => $name,
				':e' => $ext,
				':f' => $feat,
				':ctx' => $dom,
				':st' => $status,
				':lb' => $label,
				':day' => preg_replace('/^transfer:/', '', $day),
				':al' => $altLabel,
				':night' => preg_replace('/^transfer:/', '', $night),
			]);
			echo json_encode(['ok' => true, 'call_flow_uuid' => $id, 'created' => true]);
			exit;
		}
		$db->prepare(
			"UPDATE v_call_flows SET call_flow_status = :s, call_flow_label = COALESCE(NULLIF(:l,''), call_flow_label)
			 WHERE call_flow_uuid = :id AND domain_uuid = :d"
		)->execute([':s' => $status, ':l' => $label, ':id' => $id, ':d' => $du]);
		echo json_encode(['ok' => true]);
		exit;
	}

	if ($op === 'verification_set' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_ops_need(['admin', 'superadmin', 'supervisor']);
		$rawPhone = trim((string)($body['phone'] ?? ''));
		$phone = preg_replace('/\D+/', '', $rawPhone);
		if ($phone === '') {
			echo json_encode(['ok' => false, 'error' => 'Phone required']);
			exit;
		}
		$flag = sc_ops_truthy($body['fayda_verified'] ?? false) ? 1 : 0;
		$name = trim((string)($body['full_name'] ?? $body['name'] ?? ''));
		if ($name === '') {
			$name = $phone;
		}
		$lang = trim((string)($body['language'] ?? 'English')) ?: 'English';
		sc_ops_ensure_fayda($db);
		$found = false;
		foreach ([$phone, $rawPhone] as $p) {
			try {
				$chk = $db->prepare('SELECT contact_id, phone FROM skykin_contacts WHERE phone = :p LIMIT 1');
				$chk->execute([':p' => $p]);
				if ($chk->fetch(PDO::FETCH_ASSOC)) {
					$found = true;
					$db->prepare('UPDATE skykin_contacts SET full_name = :n, language = :l, fayda_verified = :f WHERE phone = :p')
						->execute([':n' => $name, ':l' => $lang, ':f' => $flag, ':p' => $p]);
					break;
				}
			} catch (Throwable $e) {
				try {
					$db->prepare('UPDATE skykin_contacts SET full_name = :n, language = :l WHERE phone = :p')
						->execute([':n' => $name, ':l' => $lang, ':p' => $p]);
					$found = true;
					break;
				} catch (Throwable $e2) {
					/* try insert */
				}
			}
		}
		if (!$found) {
			$okIns = false;
			try {
				$db->prepare(
					'INSERT INTO skykin_contacts (phone, full_name, language, account_type, fayda_verified)
					 VALUES (:p, :n, :l, :a, :f)'
				)->execute([':p' => $phone, ':n' => $name, ':l' => $lang, ':a' => 'Customer', ':f' => $flag]);
				$okIns = true;
			} catch (Throwable $e) {
				try {
					$db->prepare(
						'INSERT INTO skykin_contacts (phone, full_name, language, account_type)
						 VALUES (:p, :n, :l, :a)'
					)->execute([':p' => $phone, ':n' => $name, ':l' => $lang, ':a' => 'Customer']);
					$okIns = true;
					try {
						$db->prepare('UPDATE skykin_contacts SET fayda_verified = :f WHERE phone = :p')
							->execute([':f' => $flag, ':p' => $phone]);
					} catch (Throwable $e3) {
						/* no column */
					}
				} catch (Throwable $e2) {
					echo json_encode(['ok' => false, 'error' => 'Could not add contact: ' . $e2->getMessage()]);
					exit;
				}
			}
			if (!$okIns) {
				echo json_encode(['ok' => false, 'error' => 'Could not add contact']);
				exit;
			}
		}
		$pack = sc_ops_list_contacts($db);
		echo json_encode(['ok' => true, 'created' => !$found] + $pack);
		exit;
	}

	if ($op === 'recording_save' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_ops_need(['admin', 'superadmin']);
		$du = sc_ops_domain_uuid($db, $dom);
		if (!$du) {
			echo json_encode(['ok' => false, 'error' => 'Domain not found']);
			exit;
		}
		$file = $_FILES['file'] ?? $_FILES['recording'] ?? null;
		if (!is_array($file) || (int)($file['error'] ?? UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_OK) {
			echo json_encode(['ok' => false, 'error' => 'Choose an audio file (wav/mp3)']);
			exit;
		}
		$orig = strtolower((string)($file['name'] ?? 'prompt.wav'));
		$ext = pathinfo($orig, PATHINFO_EXTENSION);
		if (!in_array($ext, ['wav', 'mp3', 'ogg'], true)) {
			echo json_encode(['ok' => false, 'error' => 'Use wav, mp3, or ogg']);
			exit;
		}
		$label = trim((string)($body['recording_name'] ?? $_POST['recording_name'] ?? ''));
		if ($label === '') {
			$label = pathinfo($orig, PATHINFO_FILENAME);
		}
		$safe = preg_replace('/[^a-z0-9_\-]+/i', '_', $label) . '.' . $ext;
		$dir = '/var/lib/freeswitch/recordings/' . $dom;
		if (!is_dir($dir)) {
			@mkdir($dir, 0775, true);
		}
		$dest = $dir . '/' . $safe;
		if (!move_uploaded_file((string)$file['tmp_name'], $dest)) {
			echo json_encode(['ok' => false, 'error' => 'Could not store recording on this host']);
			exit;
		}
		@chmod($dest, 0664);
		$id = sc_ops_uuid();
		try {
			$db->prepare(
				"INSERT INTO v_recordings (recording_uuid, domain_uuid, recording_filename, recording_name, recording_description)
				 VALUES (:id, :d, :f, :n, :ds)"
			)->execute([':id' => $id, ':d' => $du, ':f' => $safe, ':n' => $label, ':ds' => 'SkyConnect']);
		} catch (Throwable $e) {
			echo json_encode(['ok' => false, 'error' => 'Saved file but database insert failed']);
			exit;
		}
		echo json_encode(['ok' => true, 'recording_uuid' => $id, 'recording_filename' => $safe]);
		exit;
	}

	if ($op === 'verification') {
		sc_ops_need(['admin', 'superadmin', 'supervisor']);
		$pack = sc_ops_list_contacts($db);
		echo json_encode(['ok' => true] + $pack);
		exit;
	}

	if ($op === 'queue_agent_save' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_ops_need(['admin', 'superadmin']);
		$du = sc_ops_domain_uuid($db, $dom);
		$qid = trim((string)($body['call_center_queue_uuid'] ?? ''));
		if (!$du || $qid === '') {
			echo json_encode(['ok' => false, 'error' => 'Queue required']);
			exit;
		}
		$qrow = $db->prepare(
			'SELECT call_center_queue_uuid, queue_name FROM v_call_center_queues WHERE call_center_queue_uuid = :id AND domain_uuid = :d LIMIT 1'
		);
		$qrow->execute([':id' => $qid, ':d' => $du]);
		$queue = $qrow->fetch(PDO::FETCH_ASSOC);
		if (!$queue) {
			echo json_encode(['ok' => false, 'error' => 'Queue not found']);
			exit;
		}
		$want = $body['user_uuids'] ?? $body['members'] ?? [];
		if (is_string($want)) {
			$want = array_filter(array_map('trim', explode(',', $want)));
		}
		if (!is_array($want)) {
			$want = [];
		}
		$pack = sc_ops_set_queue_members($db, $du, $dom, $qid, $want);
		echo json_encode(['ok' => true, 'members' => $pack['members'], 'skipped' => $pack['skipped']]);
		exit;
	}

	if ($op === 'skill_save' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_ops_need(['admin', 'superadmin']);
		$du = sc_ops_domain_uuid($db, $dom);
		if (!$du) {
			echo json_encode(['ok' => false, 'error' => 'Domain not found']);
			exit;
		}
		sc_ops_ensure_skill_tables($db);
		$uid = trim((string)($body['user_uuid'] ?? ''));
		if ($uid === '') {
			echo json_encode(['ok' => false, 'error' => 'User required']);
			exit;
		}
		$keys = $body['skills'] ?? [];
		if (is_string($keys)) {
			$keys = array_filter(array_map('trim', explode(',', $keys)));
		}
		if (!is_array($keys)) {
			$keys = [];
		}
		$allowed = [];
		foreach (sc_ops_skill_catalog($db) as $sk) {
			$allowed[(string)$sk['skill_key']] = true;
		}
		$keys = array_values(array_unique(array_filter(array_map(static function ($k) use ($allowed) {
			$k = strtolower(trim((string)$k));
			return isset($allowed[$k]) ? $k : '';
		}, $keys))));
		try {
			$db->prepare('DELETE FROM skykin_user_skills WHERE user_uuid = :u AND domain_uuid = :d')->execute([':u' => $uid, ':d' => $du]);
		} catch (Throwable $e) {
			$db->prepare('DELETE FROM skykin_user_skills WHERE user_uuid = :u')->execute([':u' => $uid]);
		}
		$ins = $db->prepare('INSERT INTO skykin_user_skills (user_uuid, skill_key, domain_uuid) VALUES (:u,:k,:d)');
		foreach ($keys as $k) {
			try {
				$ins->execute([':u' => $uid, ':k' => $k, ':d' => $du]);
			} catch (Throwable $e) {
				/* ignore dup */
			}
		}
		$synced = sc_ops_sync_skill_queues($db, $du, $dom);
		echo json_encode(['ok' => true, 'skills' => $keys, 'queues_synced' => $synced, 'reload' => sc_ops_reload_xml()]);
		exit;
	}

	if ($op === 'did_save' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_ops_need(['admin', 'superadmin']);
		sc_ops_ensure_did_table($db);
		$did = preg_replace('/\D+/', '', (string)($body['did'] ?? ''));
		$ext = preg_replace('/\D+/', '', (string)($body['dest_ext'] ?? ''));
		$kind = trim((string)($body['dest_kind'] ?? 'ivr'));
		if (!in_array($kind, ['ivr', 'queue', 'flow'], true)) {
			$kind = 'ivr';
		}
		if (strlen($did) < 8 || $ext === '') {
			echo json_encode(['ok' => false, 'error' => 'DID (8+ digits) and destination extension required']);
			exit;
		}
		try {
			$db->prepare(
				"INSERT INTO skykin_did_routes (domain_name, did, dest_ext, dest_kind, updated_at)
				 VALUES (:n, :did, :e, :k, NOW())
				 ON CONFLICT (domain_name, did) DO UPDATE SET dest_ext = EXCLUDED.dest_ext, dest_kind = EXCLUDED.dest_kind, updated_at = NOW()"
			)->execute([':n' => $dom, ':did' => $did, ':e' => $ext, ':k' => $kind]);
		} catch (Throwable $e) {
			$up = $db->prepare('UPDATE skykin_did_routes SET dest_ext = :e, dest_kind = :k, updated_at = NOW() WHERE domain_name = :n AND did = :did');
			$up->execute([':e' => $ext, ':k' => $kind, ':n' => $dom, ':did' => $did]);
			if ($up->rowCount() < 1) {
				$db->prepare(
					'INSERT INTO skykin_did_routes (domain_name, did, dest_ext, dest_kind) VALUES (:n, :did, :e, :k)'
				)->execute([':n' => $dom, ':did' => $did, ':e' => $ext, ':k' => $kind]);
			}
		}
		sc_ops_write_did_map($db);
		$ds = $db->prepare('SELECT route_id, did, dest_ext, dest_kind FROM skykin_did_routes WHERE domain_name = :n ORDER BY did');
		$ds->execute([':n' => $dom]);
		echo json_encode(['ok' => true, 'did_routes' => $ds->fetchAll(PDO::FETCH_ASSOC)]);
		exit;
	}

	if ($op === 'did_delete' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_ops_need(['admin', 'superadmin']);
		sc_ops_ensure_did_table($db);
		$rid = (int)($body['route_id'] ?? 0);
		$did = preg_replace('/\D+/', '', (string)($body['did'] ?? ''));
		if ($rid > 0) {
			$db->prepare('DELETE FROM skykin_did_routes WHERE route_id = :id AND domain_name = :n')->execute([':id' => $rid, ':n' => $dom]);
		} elseif ($did !== '') {
			$db->prepare('DELETE FROM skykin_did_routes WHERE did = :did AND domain_name = :n')->execute([':did' => $did, ':n' => $dom]);
		} else {
			echo json_encode(['ok' => false, 'error' => 'Route required']);
			exit;
		}
		sc_ops_write_did_map($db);
		$ds = $db->prepare('SELECT route_id, did, dest_ext, dest_kind FROM skykin_did_routes WHERE domain_name = :n ORDER BY did');
		$ds->execute([':n' => $dom]);
		echo json_encode(['ok' => true, 'did_routes' => $ds->fetchAll(PDO::FETCH_ASSOC)]);
		exit;
	}

	if ($op === 'studio_delete' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_ops_need(['admin', 'superadmin']);
		$du = sc_ops_domain_uuid($db, $dom);
		$kind = trim((string)($body['kind'] ?? $body['type'] ?? ''));
		$id = trim((string)($body['id'] ?? $body['uuid'] ?? ''));
		if (!$du || $kind === '' || $id === '') {
			echo json_encode(['ok' => false, 'error' => 'What to delete?']);
			exit;
		}
		if ($kind === 'option' || $kind === 'ivr_option') {
			$db->prepare('DELETE FROM v_ivr_menu_options WHERE ivr_menu_option_uuid = :id AND domain_uuid = :d')
				->execute([':id' => $id, ':d' => $du]);
			echo json_encode(['ok' => true]);
			exit;
		}
		if ($kind === 'ivr') {
			$row = $db->prepare('SELECT dialplan_uuid FROM v_ivr_menus WHERE ivr_menu_uuid = :id AND domain_uuid = :d LIMIT 1');
			$row->execute([':id' => $id, ':d' => $du]);
			$dp = (string)($row->fetchColumn() ?: '');
			$db->prepare('DELETE FROM v_ivr_menu_options WHERE ivr_menu_uuid = :id')->execute([':id' => $id]);
			$db->prepare('DELETE FROM v_ivr_menus WHERE ivr_menu_uuid = :id AND domain_uuid = :d')->execute([':id' => $id, ':d' => $du]);
			sc_ops_drop_dialplan($db, $du, $dp);
			echo json_encode(['ok' => true]);
			exit;
		}
		if ($kind === 'queue') {
			$row = $db->prepare('SELECT dialplan_uuid FROM v_call_center_queues WHERE call_center_queue_uuid = :id AND domain_uuid = :d LIMIT 1');
			$row->execute([':id' => $id, ':d' => $du]);
			$dp = (string)($row->fetchColumn() ?: '');
			try {
				$db->prepare('DELETE FROM v_call_center_tiers WHERE call_center_queue_uuid = :id')->execute([':id' => $id]);
			} catch (Throwable $e) {
				/* ignore */
			}
			$db->prepare('DELETE FROM v_call_center_queues WHERE call_center_queue_uuid = :id AND domain_uuid = :d')->execute([':id' => $id, ':d' => $du]);
			sc_ops_drop_dialplan($db, $du, $dp);
			echo json_encode(['ok' => true]);
			exit;
		}
		if ($kind === 'flow') {
			$row = $db->prepare('SELECT dialplan_uuid FROM v_call_flows WHERE call_flow_uuid = :id AND domain_uuid = :d LIMIT 1');
			$row->execute([':id' => $id, ':d' => $du]);
			$dp = (string)($row->fetchColumn() ?: '');
			$db->prepare('DELETE FROM v_call_flows WHERE call_flow_uuid = :id AND domain_uuid = :d')->execute([':id' => $id, ':d' => $du]);
			sc_ops_drop_dialplan($db, $du, $dp);
			echo json_encode(['ok' => true]);
			exit;
		}
		if ($kind === 'recording') {
			$row = $db->prepare('SELECT recording_filename FROM v_recordings WHERE recording_uuid = :id AND domain_uuid = :d LIMIT 1');
			$row->execute([':id' => $id, ':d' => $du]);
			$fn = (string)($row->fetchColumn() ?: '');
			$db->prepare('DELETE FROM v_recordings WHERE recording_uuid = :id AND domain_uuid = :d')->execute([':id' => $id, ':d' => $du]);
			if ($fn !== '' && strpos($fn, '..') === false) {
				@unlink('/var/lib/freeswitch/recordings/' . $dom . '/' . $fn);
			}
			echo json_encode(['ok' => true]);
			exit;
		}
		if ($kind === 'user') {
			$meUuid = (string)($_SESSION['user_uuid'] ?? '');
			if ($id === $meUuid) {
				echo json_encode(['ok' => false, 'error' => 'Cannot delete your own login']);
				exit;
			}
			$urow = $db->prepare('SELECT username FROM v_users WHERE user_uuid = :id AND domain_uuid = :d LIMIT 1');
			$urow->execute([':id' => $id, ':d' => $du]);
			$uname = strtolower((string)($urow->fetchColumn() ?: ''));
			if ($uname === '') {
				echo json_encode(['ok' => false, 'error' => 'User not found']);
				exit;
			}
			$gchk = $db->prepare(
				"SELECT COALESCE(NULLIF(ug.group_name,''), g.group_name) AS group_name
				 FROM v_user_groups ug LEFT JOIN v_groups g ON g.group_uuid = ug.group_uuid
				 WHERE ug.user_uuid = :u"
			);
			$gchk->execute([':u' => $id]);
			foreach ($gchk->fetchAll(PDO::FETCH_COLUMN) as $gn) {
				if (strtolower((string)$gn) === 'superadmin') {
					echo json_encode(['ok' => false, 'error' => 'Cannot delete a superadmin']);
					exit;
				}
			}
			try {
				$db->prepare('DELETE FROM v_user_groups WHERE user_uuid = :u')->execute([':u' => $id]);
			} catch (Throwable $e) {
				/* ignore */
			}
			try {
				$db->prepare('DELETE FROM v_extension_users WHERE user_uuid = :u')->execute([':u' => $id]);
			} catch (Throwable $e) {
				/* ignore */
			}
			try {
				$ag = $db->prepare('SELECT call_center_agent_uuid FROM v_call_center_agents WHERE user_uuid = :u');
				$ag->execute([':u' => $id]);
				foreach ($ag->fetchAll(PDO::FETCH_COLUMN) as $aid) {
					$db->prepare('DELETE FROM v_call_center_tiers WHERE call_center_agent_uuid = :a')->execute([':a' => $aid]);
					$db->prepare('DELETE FROM v_call_center_agents WHERE call_center_agent_uuid = :a')->execute([':a' => $aid]);
				}
			} catch (Throwable $e) {
				/* ignore */
			}
			$db->prepare('DELETE FROM v_users WHERE user_uuid = :u AND domain_uuid = :d')->execute([':u' => $id, ':d' => $du]);
			echo json_encode(['ok' => true]);
			exit;
		}
		echo json_encode(['ok' => false, 'error' => 'Unknown delete kind']);
		exit;
	}

	if ($op === 'live_transcribe' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		require_once __DIR__ . '/skykin_ai.php';
		if (!skykin_ai_ready()) {
			echo json_encode(['ok' => false, 'error' => 'ai_off']);
			exit;
		}
		$file = $_FILES['chunk'] ?? $_FILES['file'] ?? null;
		if (!is_array($file) || (int)($file['error'] ?? UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_OK) {
			echo json_encode(['ok' => false, 'error' => 'No audio chunk']);
			exit;
		}
		$tmp = (string)($file['tmp_name'] ?? '');
		if ($tmp === '' || !is_uploaded_file($tmp)) {
			echo json_encode(['ok' => false, 'error' => 'Bad upload']);
			exit;
		}
		$ext = 'webm';
		$name = strtolower((string)($file['name'] ?? ''));
		if (substr($name, -4) === '.ogg') {
			$ext = 'ogg';
		} elseif (substr($name, -4) === '.wav') {
			$ext = 'wav';
		} elseif (substr($name, -4) === '.mp3') {
			$ext = 'mp3';
		}
		$dest = sys_get_temp_dir() . '/sc_live_' . bin2hex(random_bytes(8)) . '.' . $ext;
		if (!move_uploaded_file($tmp, $dest)) {
			echo json_encode(['ok' => false, 'error' => 'Could not store chunk']);
			exit;
		}
		$lang = trim((string)($_POST['lang'] ?? $body['lang'] ?? ''));
		try {
			$res = skykin_ai_transcribe($dest, $lang !== '' ? $lang : null, 25);
			$err = strtolower((string)($res['error'] ?? ''));
			if (empty($res['ok']) && (strpos($err, 'empty') !== false || strpos($err, 'too short') !== false)) {
				echo json_encode(['ok' => true, 'text' => '']);
			} else {
				echo json_encode($res);
			}
		} finally {
			@unlink($dest);
		}
		exit;
	}

	if ($op === 'live_suggest' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		require_once __DIR__ . '/skykin_ai.php';
		$tr = trim((string)($body['transcript'] ?? $body['q'] ?? $_POST['transcript'] ?? ''));
		if (function_exists('skykin_crm_suggest_from_transcript')) {
			echo json_encode(skykin_crm_suggest_from_transcript($db, $tr));
		} else {
			echo json_encode(skykin_crm_search_knowledge($db, $tr));
		}
		exit;
	}

	if ($op === 'reloadxml' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_ops_need(['admin', 'superadmin']);
		$r = sc_ops_reload_xml();
		echo json_encode(['ok' => true, 'reload' => $r]);
		exit;
	}

	if ($op === 'settings_save' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_ops_need(['admin', 'superadmin']);
		$who = (string)($_SESSION['username'] ?? '');
		if (array_key_exists('session_idle_minutes', $body)) {
			$minutes = (int)$body['session_idle_minutes'];
			if ($minutes < 0) {
				$minutes = 0;
			}
			if ($minutes > 1440) {
				$minutes = 1440;
			}
			skykin_setting_set('session_idle_minutes', (string)$minutes, $who);
		}
		if (isset($body['biz_hours']) && is_array($body['biz_hours'])) {
			$bh = $body['biz_hours'];
			$pack = [
				'enabled' => sc_ops_truthy($bh['enabled'] ?? false),
				'tz' => (string)($bh['tz'] ?? 'Africa/Addis_Ababa'),
				'open' => preg_replace('/\D+/', '', (string)($bh['open'] ?? '0800')) ?: '0800',
				'close' => preg_replace('/\D+/', '', (string)($bh['close'] ?? '1900')) ?: '1900',
				'days' => preg_replace('/[^\d,]/', '', (string)($bh['days'] ?? '1,2,3,4,5,6,7')) ?: '1,2,3,4,5,6,7',
			];
			skykin_setting_set(sc_ops_biz_hours_key($dom), json_encode($pack), $who);
			sc_ops_write_biz_hours($db);
		}
		echo json_encode([
			'ok' => true,
			'session_idle_minutes' => skykin_idle_timeout_minutes(),
			'biz_hours' => sc_ops_biz_hours_get($dom),
		]);
		exit;
	}

	if ($op === 'ai_health') {
		require_once __DIR__ . '/skykin_ai.php';
		echo json_encode(skykin_ai_health());
		exit;
	}

	if ($op === 'knowledge') {
		$kid = (int)($_GET['id'] ?? $body['article_id'] ?? 0);
		$q = trim((string)($_GET['q'] ?? $body['q'] ?? ''));
		echo json_encode(skykin_crm_search_knowledge($db, $q, $kid));
		exit;
	}

	if ($op === 'knowledge_save' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
		sc_ops_need(['admin', 'superadmin', 'supervisor']);
		skykin_crm_ensure_knowledge($db);
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

	http_response_code(400);
	echo json_encode(['ok' => false, 'error' => 'Unknown op']);
} catch (Throwable $e) {
	http_response_code(500);
	echo json_encode(['ok' => false, 'error' => $e->getMessage()]);
}
