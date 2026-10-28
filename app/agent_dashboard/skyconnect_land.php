<?php
/**
 * After Sign in, send each FusionPBX group to the right board.
 * Must use resources/require.php (same session as login.php).
 */
require_once dirname(__DIR__, 2) . '/resources/require.php';
require_once __DIR__ . '/skykin_config.php';

if (empty($_SESSION['authorized']) || empty($_SESSION['user_uuid'])) {
	header('Location: /');
	exit;
}

$sc = '/app/agent_dashboard/skyconnect/';
$pack = ['role' => 'agent'];
try {
	$pack = skykin_app_role_from_groups(
		skykin_pdo_fusionpbx(),
		(string)$_SESSION['user_uuid'],
		$_SESSION['groups'] ?? ($_SESSION['user']['groups'] ?? [])
	);
} catch (Throwable $e) {
	$pack = skykin_app_role_from_groups(null, null, $_SESSION['groups'] ?? []);
}
$role = $pack['role'] ?? 'agent';

header('Cache-Control: no-store');
if ($role === 'superadmin') {
	header('Location: /core/dashboard/');
} elseif ($role === 'admin') {
	header('Location: ' . $sc . 'admin/console');
} elseif ($role === 'supervisor') {
	header('Location: ' . $sc . 'supervisor/team');
} else {
	header('Location: ' . $sc . 'agent/home');
}
exit;
