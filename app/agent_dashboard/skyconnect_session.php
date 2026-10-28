<?php
/**
 * Bootstrap for SkyConnect React UI.
 * Requires FusionPBX agent session. Returns SIP + WSS creds (same source as index.php).
 */
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
require_once dirname(__DIR__, 2) . '/resources/require.php';
require_once __DIR__ . '/skykin_config.php';

if (empty($_SESSION['user_uuid']) || empty($_SESSION['authorized'])) {
	http_response_code(401);
	echo json_encode([
		'ok' => false,
		'error' => 'Session expired. Please log in again.',
		'login' => '/',
	]);
	exit;
}

skykin_session_touch();

$agent_name = $_SESSION['username'] ?? ($_SESSION['user']['username'] ?? '');
$domain = $_SESSION['domain_name'] ?? skykin_domain_param(null);
$user_uuid = (string)($_SESSION['user_uuid'] ?? '');
$session_groups = $_SESSION['groups'] ?? ($_SESSION['user']['groups'] ?? []);
$display = $_SESSION['user']['contact_name'] ?? $agent_name;

$agent_ext = '';
$agent_password = '';
$host = $_SERVER['HTTP_HOST'] ?? '127.0.0.1';
$https = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off')
	|| ((int)($_SERVER['SERVER_PORT'] ?? 0) === 443)
	|| (($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https');
$agent_wss = ($https ? 'wss' : 'ws') . '://' . $host . '/wss/';

$role_pack = [
	'role' => 'agent',
	'groups' => [],
	'is_superadmin' => false,
	'is_admin' => false,
	'is_supervisor' => false,
];
try {
	$pdb = skykin_pdo_fusionpbx();
	$role_pack = skykin_app_role_from_groups($pdb, $user_uuid, $session_groups);

	$s = $pdb->prepare(
		"SELECT e.extension, e.password FROM v_extensions e
		 JOIN v_extension_users eu ON eu.extension_uuid = e.extension_uuid
		 JOIN v_users u ON u.user_uuid = eu.user_uuid
		 JOIN v_domains d ON d.domain_uuid = e.domain_uuid
		 WHERE LOWER(u.username) = LOWER(:a) AND d.domain_name = :d LIMIT 1"
	);
	$s->execute([':a' => $agent_name, ':d' => $domain]);
	$row = $s->fetch(PDO::FETCH_ASSOC);
	if ($row) {
		$agent_ext = $row['extension'];
		$agent_password = $row['password'];
	}

	if (!$agent_ext) {
		$s2 = $pdb->prepare(
			"SELECT e.extension, e.password FROM v_extensions e
			 JOIN v_domains d ON d.domain_uuid = e.domain_uuid
			 WHERE d.domain_name = :d
			 AND (LOWER(e.description) LIKE :p OR LOWER(e.effective_caller_id_name) LIKE :p)
			 LIMIT 1"
		);
		$s2->execute([':d' => $domain, ':p' => '%' . strtolower($agent_name) . '%']);
		$row2 = $s2->fetch(PDO::FETCH_ASSOC);
		if ($row2) {
			$agent_ext = $row2['extension'];
			$agent_password = $row2['password'];
		}
	}

	if (!$agent_ext && preg_match('/^\d{2,6}$/', $agent_name)) {
		$agent_ext = $agent_name;
	}
} catch (Throwable $e) {
	$role_pack = skykin_app_role_from_groups(null, null, $session_groups);
}

session_write_close();

echo json_encode([
	'ok' => true,
	'username' => $agent_name,
	'display_name' => is_string($display) && trim($display) !== '' ? trim($display) : $agent_name,
	'extension' => $agent_ext,
	'password' => $agent_password,
	'domain' => $domain,
	'wss' => $agent_wss,
	'api_base' => '/skyconnect/api/v1',
	'is_supervisor' => !empty($role_pack['is_supervisor']),
	'is_admin' => !empty($role_pack['is_admin']),
	'is_superadmin' => !empty($role_pack['is_superadmin']),
	'role' => $role_pack['role'] ?? 'agent',
	'groups' => $role_pack['groups'] ?? [],
	'legacy_dashboard' => '/app/agent_dashboard/index.php?legacy=1',
	'logout' => '/logout.php',
]);
