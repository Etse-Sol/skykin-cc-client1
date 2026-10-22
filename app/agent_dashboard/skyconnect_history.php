<?php
/**
 * SkyConnect Call History — FusionPBX v_xml_cdr + ESL skyconnect_calls fallback.
 */
require_once __DIR__ . '/session_bootstrap.php';
require_once __DIR__ . '/skykin_config.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

if (empty($_SESSION['user_uuid']) || empty($_SESSION['authorized'])) {
	http_response_code(401);
	echo json_encode(['ok' => false, 'error' => 'Session expired', 'calls' => [], 'login' => '/']);
	exit;
}

skykin_session_touch();

$agent_name = (string)($_SESSION['username'] ?? '');
$domain = skykin_domain_param($_GET['domain'] ?? ($_SESSION['domain_name'] ?? null));
$from = isset($_GET['from']) && $_GET['from'] !== '' ? (string)$_GET['from'] : date('Y-m-d');
$to = isset($_GET['to']) && $_GET['to'] !== '' ? (string)$_GET['to'] : $from;
$extension = preg_replace('/[^0-9]/', '', (string)($_GET['ext'] ?? ''));

$ts = strtotime($from . ' 00:00:00');
$te = strtotime($to . ' 23:59:59');
if ($ts === false || $te === false) {
	http_response_code(400);
	echo json_encode(['ok' => false, 'error' => 'Bad date', 'calls' => []]);
	exit;
}

$out = [
	'ok' => true,
	'from' => $from,
	'to' => $to,
	'extension' => $extension,
	'domain' => $domain,
	'source' => '',
	'calls' => [],
	'count' => 0,
	'xml_raw' => 0,
	'esl_raw' => 0,
];

function skyconnect_history_strip_host(string $v): string {
	return preg_replace('/@.*$/', '', trim($v));
}

function skyconnect_history_is_token(string $v): bool {
	if ($v === '' || $v === 'Unknown') {
		return false;
	}
	if (function_exists('skykin_cdr_is_webrtc_bridge_token')) {
		return skykin_cdr_is_webrtc_bridge_token($v);
	}
	return (bool)preg_match('/^[a-z0-9]{4,16}$/i', $v) && !preg_match('/^\d+$/', $v);
}

function skyconnect_history_is_ext(string $v): bool {
	return (bool)preg_match('/^\d{2,6}$/', $v);
}

function skyconnect_history_is_phone(string $v): bool {
	$d = preg_replace('/\D+/', '', $v);
	return strlen($d) >= 8 && !skyconnect_history_is_ext($d);
}

/**
 * Token → extension ONLY from the leg that owns the WebRTC contact
 * (caller is token, extension is numeric). Never map outbound callee tokens
 * to the caller — that made peer resolve to self → "Unknown".
 *
 * @param array<int,array<string,mixed>> $rows
 * @return array<string,string>
 */
function skyconnect_history_token_map_local(array $rows): array {
	$map = [];
	foreach ($rows as $r) {
		$own = skyconnect_history_strip_host((string)($r['extension'] ?? ''));
		if (!skyconnect_history_is_ext($own)) {
			continue;
		}
		$caller = skyconnect_history_strip_host((string)($r['caller'] ?? ''));
		$dir = strtolower((string)($r['direction'] ?? ''));
		// B-leg / local channel: WebRTC username is the contact token
		if (skyconnect_history_is_token($caller)) {
			$map[strtolower($caller)] = $own;
		}
		// Inbound: destination may be token on some builds — only if own matches callee side
		$callee = skyconnect_history_strip_host((string)($r['callee'] ?? ''));
		if ($dir === 'inbound' && skyconnect_history_is_token($callee) && $own !== '') {
			$map[strtolower($callee)] = $own;
		}
	}
	return $map;
}

/**
 * Pair outbound→token with another agent hangup in the same second window.
 * @param array<int,array<string,mixed>> $rows
 * @return array<string,string> token => peerExt
 */
function skyconnect_history_pair_a2a(array $rows): array {
	$map = [];
	$byExt = [];
	foreach ($rows as $r) {
		$own = skyconnect_history_strip_host((string)($r['extension'] ?? ''));
		if (!skyconnect_history_is_ext($own)) {
			continue;
		}
		$epoch = (int)($r['start_epoch'] ?? 0);
		$bill = (int)($r['billsec'] ?? 0);
		$byExt[$own][] = ['epoch' => $epoch, 'bill' => $bill, 'row' => $r];
	}
	foreach ($rows as $r) {
		$own = skyconnect_history_strip_host((string)($r['extension'] ?? ''));
		$callee = skyconnect_history_strip_host((string)($r['callee'] ?? ''));
		$dir = strtolower((string)($r['direction'] ?? ''));
		if (!skyconnect_history_is_ext($own) || !skyconnect_history_is_token($callee)) {
			continue;
		}
		if ($dir === 'inbound') {
			continue;
		}
		$epoch = (int)($r['start_epoch'] ?? 0);
		$bill = (int)($r['billsec'] ?? 0);
		$best = '';
		$bestDelta = 999;
		foreach ($byExt as $peerExt => $list) {
			if ($peerExt === $own) {
				continue;
			}
			foreach ($list as $o) {
				$delta = abs($o['epoch'] - $epoch);
				if ($delta > 5) {
					continue;
				}
				// Prefer similar talk time when both answered
				$billDelta = abs($o['bill'] - $bill);
				$score = $delta + ($billDelta > 5 ? 3 : 0);
				if ($score < $bestDelta) {
					$bestDelta = $score;
					$best = $peerExt;
				}
			}
		}
		if ($best !== '') {
			$map[strtolower($callee)] = $best;
		}
	}
	return $map;
}

/**
 * Resolve display number. Prefer real peer ext/phone; fall back to token;
 * never return the viewing agent's own extension; never invent "Unknown"
 * when any remote identity exists.
 */
function skyconnect_history_peer_number(
	string $raw,
	array $r,
	string $extension,
	array $tokenMap
): string {
	$num = skyconnect_history_strip_host($raw);
	$caller = skyconnect_history_strip_host((string)($r['caller'] ?? $r['caller_id_number'] ?? ''));
	$callee = skyconnect_history_strip_host((string)($r['callee'] ?? $r['destination_number'] ?? ''));
	$cdest = skyconnect_history_strip_host((string)($r['caller_destination'] ?? ''));
	$ani = skyconnect_history_strip_host((string)($r['ani'] ?? $r['sip_from_user'] ?? ''));
	$arg = (string)($r['last_arg'] ?? '');

	$candidates = [];
	if ($num !== '') {
		$candidates[] = $num;
	}
	foreach ([$callee, $caller, $cdest, $ani] as $c) {
		if ($c !== '' && strcasecmp($c, 'unknown') !== 0) {
			$candidates[] = $c;
		}
	}
	if ($arg !== '' && preg_match_all('/user\/(\d{2,6})@/i', $arg, $mm)) {
		foreach ($mm[1] as $ext) {
			$candidates[] = $ext;
		}
	}

	$resolved = [];
	foreach ($candidates as $c) {
		if (skyconnect_history_is_token($c)) {
			$mapped = $tokenMap[strtolower($c)] ?? '';
			if ($mapped !== '' && $mapped !== $extension) {
				$resolved[] = ['rank' => 1, 'v' => $mapped];
			} else {
				// Keep token as last resort (better than Unknown / self)
				$resolved[] = ['rank' => 9, 'v' => $c];
			}
			continue;
		}
		if ($c === $extension || $c === '' || $c === 'Unknown') {
			continue;
		}
		if (skyconnect_history_is_ext($c)) {
			$resolved[] = ['rank' => 1, 'v' => $c];
		} elseif (skyconnect_history_is_phone($c) || preg_match('/^\+?\d{7,15}$/', $c)) {
			$resolved[] = ['rank' => 2, 'v' => $c];
		} else {
			$resolved[] = ['rank' => 8, 'v' => $c];
		}
	}

	usort($resolved, static fn($a, $b) => $a['rank'] <=> $b['rank']);
	foreach ($resolved as $x) {
		if ($x['v'] !== $extension) {
			return $x['v'];
		}
	}
	return '';
}

/**
 * @param array<string,mixed> $r
 * @return array<string,mixed>|null
 */
function skyconnect_history_row_from_xml(array $r, string $extension, string $domain, array $tokenMap = []): ?array {
	$status = skykin_cdr_result_label($r);
	if ($status === 'Hunt leg') {
		return null;
	}
	$dest = (string)($r['destination_number'] ?? '');
	$dir = strtolower((string)($r['direction'] ?? ''));
	$digits = preg_replace('/\D+/', '', $dest);
	$cdest = (string)($r['caller_destination'] ?? '');
	$in = $dir === 'inbound'
		|| $dest === $extension
		|| $dest === '8000'
		|| strpos($dest, '+') === 0
		|| (function_exists('skykin_cdr_is_hunt_did') && (
			skykin_cdr_is_hunt_did($dest) || skykin_cdr_is_hunt_did($cdest)
		))
		|| (bool)preg_match('/11113875\d$/', (string)$digits);

	$arg = (string)($r['last_arg'] ?? '');
	$viaLastArg = $arg !== '' && (bool)preg_match('/user\/' . preg_quote($extension, '/') . '@/i', $arg);
	$callerId = skyconnect_history_strip_host((string)($r['caller_id_number'] ?? ''));
	if (!$in && $viaLastArg && $callerId !== '' && $callerId !== $extension) {
		$in = true;
	}

	$bill = function_exists('skykin_cdr_display_sec')
		? skykin_cdr_display_sec($r)
		: (int)($r['billsec'] ?? 0);
	$dur = (int)($r['duration'] ?? 0);
	if ($bill <= 0 && $dur > 0) {
		$bill = $dur;
	}

	if ($in) {
		$raw_num = $callerId !== '' ? $callerId : $dest;
	} else {
		$raw_num = $dest !== '' ? $dest : $callerId;
	}
	$clean_num = skyconnect_history_peer_number($raw_num, $r, $extension, $tokenMap);

	// Agent↔agent talk (peer is another short ext) is Answered — not queue Abandoned.
	if ($status === 'Abandoned' && $bill >= 3
		&& skyconnect_history_is_ext($clean_num) && skyconnect_history_is_ext($extension)
		&& $clean_num !== $extension) {
		$status = 'Answered';
	}

	$file = trim((string)($r['record_name'] ?? ''));
	$path = rtrim(trim((string)($r['record_path'] ?? '')), '/');
	$play = '';
	if ($file !== '' && function_exists('skykin_recording_path') && function_exists('skykin_recording_playable')) {
		$full = skykin_recording_path($file, $domain, $path);
		if (skykin_recording_playable($full)) {
			$play = '/app/agent_dashboard/play_recording.php?f=' . rawurlencode($file)
				. '&d=' . rawurlencode($domain)
				. ($path !== '' ? '&path=' . rawurlencode($path) : '');
		}
	}

	return [
		'time' => (string)($r['call_time'] ?? ''),
		'type' => $in ? 'Inbound' : 'Outbound',
		'number' => $clean_num,
		'duration' => function_exists('skykin_cdr_fmt_dur')
			? skykin_cdr_fmt_dur($bill)
			: sprintf('%02d:%02d', intdiv(max(0, $bill), 60), max(0, $bill) % 60),
		'status' => $status,
		'disposition' => $status === 'Answered'
			? 'Completed'
			: (string)($r['hangup_cause'] ?? $status),
		'recording' => $play,
		'record_name' => $file,
		'_epoch' => (int)($r['start_epoch'] ?? 0),
		'_key' => strtolower(($in ? 'in' : 'out') . '|' . $clean_num . '|' . (string)($r['call_time'] ?? '')),
	];
}

/**
 * @param array<string,mixed> $r
 */
function skyconnect_history_esl_involves(array $r, string $extension, array $tokenMap): bool {
	$own = skyconnect_history_strip_host((string)($r['extension'] ?? ''));
	$caller = skyconnect_history_strip_host((string)($r['caller'] ?? ''));
	$callee = skyconnect_history_strip_host((string)($r['callee'] ?? ''));
	if ($own === $extension || $caller === $extension || $callee === $extension) {
		return true;
	}
	foreach ([$caller, $callee] as $v) {
		if (skyconnect_history_is_token($v) && ($tokenMap[strtolower($v)] ?? '') === $extension) {
			return true;
		}
	}
	return false;
}

/**
 * Find the other agent extension that hung up around the same time (a2a pair).
 * @param array<int,array<string,mixed>> $all
 */
function skyconnect_history_peer_from_time(array $r, array $all, string $extension): string {
	$epoch = (int)($r['start_epoch'] ?? 0);
	$bill = (int)($r['billsec'] ?? 0);
	$own = skyconnect_history_strip_host((string)($r['extension'] ?? ''));
	if ($own === '') {
		$own = $extension;
	}
	$best = '';
	$bestScore = 999;
	foreach ($all as $o) {
		$oext = skyconnect_history_strip_host((string)($o['extension'] ?? ''));
		if (!skyconnect_history_is_ext($oext) || $oext === $own || $oext === $extension) {
			continue;
		}
		$delta = abs((int)($o['start_epoch'] ?? 0) - $epoch);
		if ($delta > 8) {
			continue;
		}
		$billDelta = abs((int)($o['billsec'] ?? 0) - $bill);
		$score = $delta + ($billDelta > 8 ? 4 : 0);
		if ($score < $bestScore) {
			$bestScore = $score;
			$best = $oext;
		}
	}
	return $best;
}

/**
 * @param array<string,mixed> $r
 * @param array<int,array<string,mixed>> $all
 * @return array<string,mixed>|null
 */
function skyconnect_history_row_from_esl(array $r, string $extension, array $tokenMap = [], array $all = []): ?array {
	$dir = strtolower((string)($r['direction'] ?? ''));
	$caller = skyconnect_history_strip_host((string)($r['caller'] ?? ''));
	$callee = skyconnect_history_strip_host((string)($r['callee'] ?? ''));
	$own = skyconnect_history_strip_host((string)($r['extension'] ?? ''));
	$bill = (int)($r['billsec'] ?? 0);
	$epoch = (int)($r['start_epoch'] ?? 0);
	$endEpoch = (int)($r['end_epoch'] ?? 0);
	if ($bill <= 0 && $epoch > 0 && $endEpoch > $epoch) {
		$bill = $endEpoch - $epoch;
	}
	$cause = (string)($r['hangup_cause'] ?? '');

	$callerR = $caller;
	$calleeR = $callee;
	if (skyconnect_history_is_token($callerR) && isset($tokenMap[strtolower($callerR)])) {
		$callerR = $tokenMap[strtolower($callerR)];
	}
	if (skyconnect_history_is_token($calleeR) && isset($tokenMap[strtolower($calleeR)])) {
		$calleeR = $tokenMap[strtolower($calleeR)];
	}

	// If callee collapsed to self / empty, recover peer from same-time other agent.
	$timedPeer = '';
	if ($calleeR === '' || $calleeR === $extension || $calleeR === $own
		|| $callerR === $calleeR || skyconnect_history_is_token($callee)) {
		$timedPeer = skyconnect_history_peer_from_time($r, $all, $extension);
		if ($timedPeer !== '' && ($calleeR === '' || $calleeR === $extension || $calleeR === $own
			|| skyconnect_history_is_token($callee))) {
			$calleeR = $timedPeer;
		}
	}

	$iAmCaller = ($callerR === $extension) || ($own === $extension && $dir !== 'inbound' && $calleeR !== $extension);
	$iAmCallee = ($calleeR === $extension)
		|| ($own === $extension && $dir === 'inbound')
		|| (skyconnect_history_is_token($callee) && ($tokenMap[strtolower($callee)] ?? '') === $extension);

	if ($iAmCallee && !$iAmCaller) {
		$in = true;
	} elseif ($iAmCaller && !$iAmCallee) {
		$in = false;
	} else {
		$in = $dir === 'inbound' || ($calleeR === $extension && $callerR !== $extension);
	}

	$fsBill = (int)($r['billsec'] ?? 0);
	if ($fsBill > 0) {
		$bill = $fsBill;
	}
	if ($bill < 0 || $bill > 86400) {
		$bill = 0;
	}

	$ctx = [
		'caller' => $callerR,
		'callee' => $calleeR,
		'caller_id_number' => $callerR,
		'destination_number' => $calleeR,
		'extension' => $own,
		'last_arg' => '',
	];
	$raw_num = $in ? $callerR : $calleeR;
	$num = skyconnect_history_peer_number((string)$raw_num, $ctx, $extension, $tokenMap);
	if ($num === 'Unknown' || $num === $extension) {
		if ($timedPeer === '') {
			$timedPeer = skyconnect_history_peer_from_time($r, $all, $extension);
		}
		if ($timedPeer !== '' && $timedPeer !== $extension) {
			$num = $timedPeer;
		} elseif ($in && $callerR !== '' && $callerR !== $extension) {
			$num = $callerR;
		} elseif (!$in && $calleeR !== '' && $calleeR !== $extension) {
			$num = $calleeR;
		}
	}

	// Agent↔agent: peer may still be a WebRTC token on callee until mapped to $num.
	// Queue Abandoned = inbound billsec with no agent bridge — must not apply to a2a talk.
	$a2a = (skyconnect_history_is_ext($callerR) && skyconnect_history_is_ext($calleeR) && $callerR !== $calleeR)
		|| (skyconnect_history_is_ext($extension) && skyconnect_history_is_ext($num)
			&& $num !== $extension && ($fsBill > 0 || $bill >= 3));

	$fake = [
		'direction' => $in ? 'inbound' : 'outbound',
		'billsec' => ($fsBill > 0 || $bill > 0) ? max($fsBill, $bill) : 0,
		'waitsec' => 0,
		'duration' => max($fsBill, $bill),
		'hangup_cause' => $cause,
		'last_arg' => $a2a ? ('user/' . ($in ? $extension : $num) . '@x') : '',
		'cc_agent' => '',
		'cc_agent_bridged' => $a2a ? ('user/' . $extension . '@x') : '',
		'bridge_uuid' => $a2a ? 'a2a' : '',
		'destination_number' => $in ? $extension : $num,
		'caller_id_number' => $in ? $num : $extension,
	];
	$status = function_exists('skykin_cdr_result_label')
		? skykin_cdr_result_label($fake)
		: (($fsBill > 0 || $bill >= 3) ? 'Answered' : 'Call ended');

	if ($a2a && ($fsBill > 0 || $bill >= 3) && in_array($status, ['Abandoned', 'Missed', 'Hunt leg', 'Call ended'], true)) {
		$status = 'Answered';
	}

	if ($status === 'Hunt leg') {
		return null;
	}
	if ($fsBill <= 0 && $bill < 3 && $in && in_array(strtoupper($cause), [
		'NORMAL_CLEARING', 'ORIGINATOR_CANCEL', 'ALLOTTED_TIMEOUT',
	], true)) {
		$peerProbe = ($callerR !== $extension) ? $callerR : $calleeR;
		if (skyconnect_history_is_ext($peerProbe) || skyconnect_history_is_ext($num)) {
			return null;
		}
	}

	$t = (string)($r['call_time'] ?? '');
	return [
		'time' => $t,
		'type' => $in ? 'Inbound' : 'Outbound',
		'number' => $num,
		'duration' => function_exists('skykin_cdr_fmt_dur')
			? skykin_cdr_fmt_dur($bill)
			: sprintf('%02d:%02d', intdiv(max(0, $bill), 60), max(0, $bill) % 60),
		'status' => $status,
		'disposition' => $status === 'Answered' ? 'Completed' : ($cause !== '' ? $cause : $status),
		'recording' => '',
		'record_name' => '',
		'_epoch' => (int)($r['start_epoch'] ?? 0),
		'_key' => strtolower(($in ? 'in' : 'out') . '|' . $num . '|' . $t),
	];
}

try {
	$db = skykin_pdo_fusionpbx();
	if (!$db) {
		$out['error'] = 'No database';
		echo json_encode($out);
		exit;
	}

	if ($extension === '') {
		$s = $db->prepare(
			"SELECT e.extension FROM v_extensions e
			 JOIN v_extension_users eu ON eu.extension_uuid = e.extension_uuid
			 JOIN v_users u ON u.user_uuid = eu.user_uuid
			 JOIN v_domains d ON d.domain_uuid = e.domain_uuid
			 WHERE LOWER(u.username)=LOWER(:a) AND d.domain_name=:d LIMIT 1"
		);
		$s->execute([':a' => $agent_name, ':d' => $domain]);
		$r = $s->fetch(PDO::FETCH_ASSOC);
		if ($r) {
			$extension = (string)$r['extension'];
		}
	}
	if ($extension === '' && preg_match('/^\d{2,6}$/', $agent_name)) {
		$extension = $agent_name;
	}
	$out['extension'] = $extension;

	if ($extension === '') {
		$out['error'] = 'No extension for user';
		echo json_encode($out);
		exit;
	}

	$byKey = [];
	$sources = [];
	$tokenMap = [];

	// ESL day dump first — builds token→ext map used by XML too
	$eslAll = [];
	try {
		$tz = function_exists('skykin_sql_tz') ? skykin_sql_tz() : 'Africa/Addis_Ababa';
		$s4 = $db->prepare(
			"SELECT to_char(timezone(:tz, COALESCE(ended_at, started_at)), 'YYYY-MM-DD HH24:MI') as call_time,
			        EXTRACT(EPOCH FROM COALESCE(started_at, ended_at))::bigint as start_epoch,
			        EXTRACT(EPOCH FROM COALESCE(ended_at, started_at))::bigint as end_epoch,
			        direction, caller, callee, billsec, hangup_cause, extension, domain
			 FROM skyconnect_calls
			 WHERE COALESCE(ended_at, started_at) >= to_timestamp(:ts)
			   AND COALESCE(ended_at, started_at) <= to_timestamp(:te)
			 ORDER BY started_at DESC
			 LIMIT 2000"
		);
		$s4->execute([':tz' => $tz, ':ts' => $ts, ':te' => $te]);
		$eslAll = $s4->fetchAll(PDO::FETCH_ASSOC);
		// pair first, then local B-leg map overwrites (more authoritative)
		$tokenMap = array_merge(
			skyconnect_history_pair_a2a($eslAll),
			skyconnect_history_token_map_local($eslAll)
		);
		$out['token_map'] = count($tokenMap);
	} catch (Throwable $e) {
		$out['esl_error'] = $e->getMessage();
	}

	// 1) XML CDR
	try {
		if (function_exists('skykin_link_archive_recordings')) {
			skykin_link_archive_recordings($db, $domain, $ts, $te);
		}
		$agent_sql = skykin_cdr_agent_sql(':e');
		$cdr_cols = skykin_cdr_time_sql('YYYY-MM-DD HH24:MI') . ' as call_time,
			direction, caller_id_number, destination_number, caller_destination,
			billsec, waitsec, duration, hangup_cause, start_epoch,
			last_arg, cc_agent, cc_agent_bridged, bridge_uuid,
			record_path, record_name';
		$s2 = $db->prepare(
			"SELECT {$cdr_cols}
			 FROM v_xml_cdr WHERE domain_name=:d
			 AND {$agent_sql}
			 AND start_epoch>=:ts AND start_epoch<=:te
			 ORDER BY start_epoch DESC LIMIT 1000"
		);
		$s2->execute([':d' => $domain, ':e' => $extension, ':ts' => $ts, ':te' => $te]);
		$raw = $s2->fetchAll(PDO::FETCH_ASSOC);
		$out['xml_raw'] = count($raw);

		if ($out['xml_raw'] === 0) {
			$s3 = $db->prepare(
				"SELECT {$cdr_cols}
				 FROM v_xml_cdr WHERE {$agent_sql}
				 AND start_epoch>=:ts AND start_epoch<=:te
				 ORDER BY start_epoch DESC LIMIT 1000"
			);
			$s3->execute([':e' => $extension, ':ts' => $ts, ':te' => $te]);
			$raw = $s3->fetchAll(PDO::FETCH_ASSOC);
			$out['xml_raw'] = count($raw);
			if ($out['xml_raw'] > 0) {
				$sources[] = 'v_xml_cdr(any-domain)';
			}
		} else {
			$sources[] = 'v_xml_cdr';
		}

		$recent = function_exists('skykin_cdr_collapse_hunt_legs')
			? skykin_cdr_collapse_hunt_legs($raw)
			: $raw;
		foreach ($recent as $row) {
			$mapped = skyconnect_history_row_from_xml($row, $extension, $domain, $tokenMap);
			if ($mapped === null) {
				continue;
			}
			$byKey[$mapped['_key']] = $mapped;
		}
	} catch (Throwable $e) {
		$out['xml_error'] = $e->getMessage();
	}

	// 2) ESL rows attributed to this agent
	try {
		$eslRows = [];
		foreach ($eslAll as $row) {
			if (skyconnect_history_esl_involves($row, $extension, $tokenMap)) {
				$eslRows[] = $row;
			}
		}
		$out['esl_raw'] = count($eslRows);
		$out['esl_day'] = count($eslAll);
		if ($out['esl_raw'] > 0) {
			$sources[] = 'skyconnect_calls';
		}
		foreach ($eslRows as $row) {
			$mapped = skyconnect_history_row_from_esl($row, $extension, $tokenMap, $eslAll);
			if ($mapped === null) {
				continue;
			}
			$key = $mapped['_key'];
			if (!isset($byKey[$key])) {
				$byKey[$key] = $mapped;
				continue;
			}
			// Prefer Answered ESL over XML Abandoned for the same a2a leg
			$prev = $byKey[$key];
			if (($mapped['status'] ?? '') === 'Answered' && ($prev['status'] ?? '') !== 'Answered') {
				if (($prev['recording'] ?? '') !== '' && ($mapped['recording'] ?? '') === '') {
					$mapped['recording'] = $prev['recording'];
					$mapped['record_name'] = $prev['record_name'] ?? '';
				}
				$byKey[$key] = $mapped;
			}
		}
	} catch (Throwable $e) {
		$out['esl_error'] = ($out['esl_error'] ?? '') . $e->getMessage();
	}

	$calls = array_values($byKey);
	usort($calls, static function ($a, $b) {
		return ((int)($b['_epoch'] ?? 0)) <=> ((int)($a['_epoch'] ?? 0));
	});
	foreach ($calls as &$c) {
		unset($c['_epoch'], $c['_key']);
	}
	unset($c);

	$out['calls'] = $calls;
	$out['count'] = count($calls);
	$out['source'] = $sources ? implode('+', $sources) : 'none';
	if ($out['count'] === 0) {
		$out['hint'] = 'No CDR for this extension in range. XML empty and ESL empty — check FreeSWITCH CDR / skyconnect-api ESL.';
	}
} catch (Throwable $e) {
	$out['ok'] = false;
	$out['error'] = $e->getMessage();
}

echo json_encode($out);
