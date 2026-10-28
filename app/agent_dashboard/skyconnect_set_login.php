<?php
/**
 * Point FusionPBX login destination at SkyConnect land.php
 * so admin/superadmin do not open core/dashboard (FreeSWITCH admin).
 * Run: php skyconnect_set_login.php
 */
if (php_sapi_name() !== 'cli') {
	http_response_code(403);
	echo "cli only\n";
	exit(1);
}

require_once __DIR__ . '/skykin_config.php';

$dest = '/app/agent_dashboard/skyconnect_land.php';
$pdo = skykin_pdo_fusionpbx();

function skykin_set_login_dest(PDO $pdo, string $dest): void {
	$tables = [
		['v_default_settings', 'default_setting'],
		['v_domain_settings', 'domain_setting'],
		['v_user_settings', 'user_setting'],
	];
	foreach ($tables as [$table, $prefix]) {
		try {
			$sql = "UPDATE {$table}
				SET {$prefix}_value = :v, {$prefix}_enabled = 'true'
				WHERE {$prefix}_category = 'login'
				AND {$prefix}_subcategory = 'destination'";
			$st = $pdo->prepare($sql);
			$st->execute([':v' => $dest]);
			echo $table . ' updated ' . $st->rowCount() . "\n";
		} catch (Throwable $e) {
			echo $table . ' skip: ' . $e->getMessage() . "\n";
		}
	}
}

skykin_set_login_dest($pdo, $dest);
echo "login destination = {$dest}\n";
echo "DONE\n";
