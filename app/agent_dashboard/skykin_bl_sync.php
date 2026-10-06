<?php
/** Push dashboard blacklist to FreeSWITCH. Hash keys are domain-scoped (`domain~digits`). */

function skykin_bl_digit_keys(string $num): array {
	$d = preg_replace('/\D+/', '', $num) ?? '';
	if (strlen($d) >= 12 && substr($d, 0, 3) === '251') {
		$d = substr($d, 3);
	}
	if (strlen($d) === 10 && isset($d[0]) && $d[0] === '0') {
		$d = substr($d, 1);
	}
	if ($d === '') {
		return [];
	}
	$keys = [$d, '251' . $d, '0' . $d];
	foreach ([7, 8, 9, 10] as $n) {
		if (strlen($d) >= $n) {
			$keys[] = substr($d, -$n);
		}
	}
	$out = [];
	foreach ($keys as $k) {
		$k = preg_replace('/\D+/', '', (string)$k) ?? '';
		if ($k !== '') {
			$out[$k] = $k;
		}
	}
	return array_values($out);
}

function skykin_bl_domain_clean(string $domain): string {
	return str_replace(['/', ' ', '|', '~'], '', $domain);
}

/** Delete every hash variant for a number (scoped + legacy unscoped). */
function skykin_bl_hash_clear_number(string $domain, string $num): void {
	if (!function_exists('skykin_fs_api')) {
		return;
	}
	$domain = skykin_bl_domain_clean($domain);
	foreach (skykin_bl_digit_keys($num) as $k) {
		skykin_fs_api('hash delete/skykin_bl/' . $k);
		if ($domain !== '') {
			skykin_fs_api('hash delete/skykin_bl/' . $domain . '~' . $k);
		}
	}
}

function skykin_bl_hash_scope(string $domain, string $num, bool $block): void {
	if (!function_exists('skykin_fs_api')) {
		return;
	}
	$domain = skykin_bl_domain_clean($domain);
	// Always clear first so remove never leaves stale suffix keys behind.
	skykin_bl_hash_clear_number($domain, $num);
	if (!$block || $domain === '') {
		return;
	}
	foreach (skykin_bl_digit_keys($num) as $k) {
		skykin_fs_api('hash insert/skykin_bl/' . $domain . '~' . $k . '/1');
	}
}

/**
 * Drop any skykin_bl hash keys for known domains that are not in $rows.
 * Catches orphans left by older delete paths.
 */
function skykin_bl_hash_prune_orphans(array $rows): void {
	if (!function_exists('skykin_fs_api')) {
		return;
	}
	$keep = [];
	$domains = [];
	foreach ($rows as $r) {
		$dom = skykin_bl_domain_clean((string)($r['domain_name'] ?? $r['domain'] ?? ''));
		$digits = (string)($r['digits'] ?? '');
		if ($dom === '' || $digits === '') {
			continue;
		}
		$domains[$dom] = true;
		foreach (skykin_bl_digit_keys($digits) as $k) {
			$keep[$dom . '~' . $k] = true;
		}
	}
	if (!$domains) {
		return;
	}
	$dump = (string)skykin_fs_api('hash dump/skykin_bl');
	if ($dump === '' || stripos($dump, '-ERR') === 0) {
		return;
	}
	foreach (preg_split('/\r\n|\r|\n/', $dump) as $line) {
		$line = trim($line);
		if ($line === '' || $line[0] === '-') {
			continue;
		}
		// Formats: "key,value" | "key=value" | "key : value"
		if (!preg_match('/^([^\s,=]+)[,=\s]/', $line, $m)) {
			continue;
		}
		$key = trim($m[1]);
		$pos = strpos($key, '~');
		if ($pos === false) {
			continue;
		}
		$dom = substr($key, 0, $pos);
		if (!isset($domains[$dom])) {
			continue;
		}
		if (!isset($keep[$key])) {
			skykin_fs_api('hash delete/skykin_bl/' . $key);
		}
	}
}

function skykin_bl_ensure_table(PDO $db): void {
	$db->exec("CREATE TABLE IF NOT EXISTS skykin_blacklist (
		digits text NOT NULL,
		domain_name text NOT NULL DEFAULT '*',
		display text, reason text, agent text, ts bigint)");
	try {
		$db->exec('ALTER TABLE skykin_blacklist DROP CONSTRAINT IF EXISTS skykin_blacklist_pkey');
	} catch (Throwable $e) {
	}
	try {
		$db->exec('ALTER TABLE skykin_blacklist ADD PRIMARY KEY (digits, domain_name)');
	} catch (Throwable $e) {
	}
}

function skykin_bl_upsert(PDO $db, string $num, string $domain, string $display, string $reason, string $agent): void {
	$ts = time();
	$vals = [$num, $domain, $display, $reason, $agent, $ts];
	$sqls = [
		'INSERT INTO skykin_blacklist (digits, domain_name, display, reason, agent, ts) VALUES (?,?,?,?,?,?) ON CONFLICT (digits, domain_name) DO UPDATE SET display=EXCLUDED.display, reason=EXCLUDED.reason, agent=EXCLUDED.agent, ts=EXCLUDED.ts',
		'INSERT INTO skykin_blacklist (digits, domain_name, display, reason, agent, ts) VALUES (?,?,?,?,?,?) ON CONFLICT (digits) DO UPDATE SET domain_name=EXCLUDED.domain_name, display=EXCLUDED.display, reason=EXCLUDED.reason, agent=EXCLUDED.agent, ts=EXCLUDED.ts',
	];
	foreach ($sqls as $sql) {
		try {
			$st = $db->prepare($sql);
			$st->execute($vals);
			return;
		} catch (Throwable $e) {
		}
	}
	$st = $db->prepare('DELETE FROM skykin_blacklist WHERE digits=? AND domain_name=?');
	$st->execute([$num, $domain]);
	$st = $db->prepare('INSERT INTO skykin_blacklist (digits, domain_name, display, reason, agent, ts) VALUES (?,?,?,?,?,?)');
	$st->execute($vals);
}

function skykin_bl_push(PDO $db, string $num = '', bool $block = true, string $domain = ''): void {
	$rows = [];
	try {
		skykin_bl_ensure_table($db);
		foreach ($db->query('SELECT digits, domain_name, display, reason, agent, ts FROM skykin_blacklist ORDER BY ts DESC') as $r) {
			$rows[] = $r;
		}
	} catch (Throwable $e) {
		$rows = [];
	}
	$buf = "# domain|digits|display|reason|agent|unix\n";
	foreach ($rows as $r) {
		$buf .= implode('|', [
			str_replace('|', '', (string)($r['domain_name'] ?? '*')),
			str_replace('|', '', (string)($r['digits'] ?? '')),
			str_replace('|', '', (string)($r['display'] ?? $r['digits'] ?? '')),
			str_replace('|', '', (string)($r['reason'] ?? '')),
			str_replace('|', '', (string)($r['agent'] ?? '')),
			(string)((int)($r['ts'] ?? time())),
		]) . "\n";
	}
	$rec = '/var/lib/freeswitch/recordings/skykin_blacklist.txt';
	@file_put_contents($rec, $buf, LOCK_EX);
	@chmod($rec, 0666);

	if (!function_exists('skykin_fs_api')) {
		return;
	}
	$b64 = base64_encode($buf);
	skykin_fs_api('system sh -c "printf %s ' . $b64 . ' | base64 -d > /etc/freeswitch/scripts/skykin_blacklist.txt && chmod 666 /etc/freeswitch/scripts/skykin_blacklist.txt"');
	skykin_fs_api('system sh -c "printf %s ' . $b64 . ' | base64 -d > ' . $rec . ' && chmod 666 ' . $rec . '"');

	// Explicit add/remove for the touched number first (remove must clear hash entirely).
	if ($num !== '') {
		skykin_bl_hash_scope($domain, $num, $block);
	}

	foreach ($rows as $r) {
		$dname = (string)($r['domain_name'] ?? '');
		$digits = (string)($r['digits'] ?? '');
		if ($dname === '' || $digits === '') {
			continue;
		}
		if (!$block && $num !== '' && $digits === $num && strcasecmp($dname, $domain) === 0) {
			continue;
		}
		skykin_bl_hash_scope($dname, $digits, true);
	}

	skykin_bl_hash_prune_orphans($rows);
}
