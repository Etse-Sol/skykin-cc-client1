<?php
/**
 * Direct SkyConnect login using PDO (FusionPBX $database->select was missing @domain users).
 */
require_once dirname(__DIR__, 2) . '/resources/require.php';

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
	header('Location: /');
	exit;
}

$username = trim((string)($_POST['username'] ?? ''));
$password = (string)($_POST['password'] ?? '');
$login_domain = '';
if (strpos($username, '@') !== false) {
	$parts = explode('@', $username);
	$login_domain = trim((string)array_pop($parts));
	$username = trim(implode('@', $parts));
}
$username = preg_replace('/\s+/', ' ', $username);
if ($username === '' || $password === '') {
	header('Location: /?e=missing');
	exit;
}

$conf = (string)@file_get_contents('/etc/fusionpbx/config.conf');
$host = 'skykin-db';
$name = 'fusionpbx';
$user = 'fusionpbx';
$pass = 'fusionpbx';
if (preg_match('/database\.0\.host\s*=\s*(\S+)/', $conf, $m)) { $host = $m[1]; }
if (preg_match('/database\.0\.name\s*=\s*(\S+)/', $conf, $m)) { $name = $m[1]; }
if (preg_match('/database\.0\.username\s*=\s*(\S+)/', $conf, $m)) { $user = $m[1]; }
if (preg_match('/database\.0\.password\s*=\s*(\S+)/', $conf, $m)) { $pass = $m[1]; }

$row = false;
try {
	$pdo = new PDO('pgsql:host=' . $host . ';dbname=' . $name, $user, $pass, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
	$sql = "SELECT u.user_uuid, u.username, u.password, u.user_email, u.contact_uuid,
		        d.domain_uuid, d.domain_name
		 FROM v_users u
		 JOIN v_domains d ON d.domain_uuid = u.domain_uuid
		 WHERE lower(u.username) = lower(:u)
		   AND (u.user_enabled = true OR u.user_enabled IS NULL)";
	$params = [':u' => $username];
	if ($login_domain !== '') {
		$sql .= " AND lower(d.domain_name) = lower(:d)";
		$params[':d'] = $login_domain;
	}
	$sql .= " LIMIT 1";
	$s = $pdo->prepare($sql);
	$s->execute($params);
	$row = $s->fetch(PDO::FETCH_ASSOC);
} catch (Throwable $e) {
	@file_put_contents('/tmp/skykin_dologin.log', date('c') . ' sql ' . $e->getMessage() . "\n", FILE_APPEND);
	header('Location: /?e=db');
	exit;
}

$hash = (string)($row['password'] ?? '');
$ok = is_array($row) && $hash !== '' && password_verify($password, $hash);
@file_put_contents(
	'/tmp/skykin_dologin.log',
	date('c') . ' user=' . str_replace(' ', '_', $username) . ' found=' . (is_array($row) && $row ? '1' : '0') . ' verify=' . ($ok ? '1' : '0') . "\n",
	FILE_APPEND
);
if (!$ok) {
	header('Location: /?e=auth');
	exit;
}

try {
	global $database;
	$settings = new settings([
		'database' => $database,
		'domain_uuid' => $row['domain_uuid'],
		'user_uuid' => $row['user_uuid'],
	]);
	authentication::create_user_session($row, $settings);
} catch (Throwable $e) {
	@file_put_contents('/tmp/skykin_dologin.log', date('c') . ' session ' . $e->getMessage() . "\n", FILE_APPEND);
}

$_SESSION['authorized'] = true;
$_SESSION['username'] = $row['username'];
$_SESSION['user_uuid'] = $row['user_uuid'];
$_SESSION['domain_uuid'] = $row['domain_uuid'];
$_SESSION['domain_name'] = $row['domain_name'];
$_SESSION['user_email'] = $row['user_email'] ?? '';
if (empty($_SESSION['groups'])) {
	try {
		$gs = $pdo->prepare(
			"SELECT g.group_name, g.group_level, ug.group_uuid
			 FROM v_user_groups ug
			 JOIN v_groups g ON g.group_uuid = ug.group_uuid
			 WHERE ug.user_uuid = :u"
		);
		$gs->execute([':u' => $row['user_uuid']]);
		$_SESSION['groups'] = $gs->fetchAll(PDO::FETCH_ASSOC) ?: [];
		$_SESSION['user']['groups'] = $_SESSION['groups'];
	} catch (Throwable $e) {
		$_SESSION['groups'] = $_SESSION['groups'] ?? [];
	}
}
session_write_close();
header('Location: /app/agent_dashboard/skyconnect_land.php');
exit;
