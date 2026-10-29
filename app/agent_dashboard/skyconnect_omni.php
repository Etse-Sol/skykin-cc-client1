<?php
/**
 * Public omnichannel: web chat widget, WhatsApp webhook, post-call CSAT.
 * No FusionPBX login.
 */
require_once __DIR__ . '/skykin_config.php';
require_once __DIR__ . '/skyconnect_omni_lib.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Headers: Content-Type');
if (($_SERVER['REQUEST_METHOD'] ?? '') === 'OPTIONS') {
	http_response_code(204);
	exit;
}

$ui = (string)($_GET['ui'] ?? '');
$op = (string)($_GET['op'] ?? '');

try {
	$db = skykin_pdo_fusionpbx();
	sc_omni_ensure($db);
} catch (Throwable $e) {
	http_response_code(500);
	header('Content-Type: application/json');
	echo json_encode(['ok' => false, 'error' => 'Database unavailable']);
	exit;
}

$defaultDom = function_exists('skykin_default_domain') ? skykin_default_domain() : 'client1.skykin.local';
$dom = preg_replace('/[^\w.\-]/', '', (string)($_GET['domain'] ?? $_POST['domain'] ?? $defaultDom)) ?: $defaultDom;

if ($ui === 'chat') {
	header('Content-Type: text/html; charset=utf-8');
	$d = htmlspecialchars($dom, ENT_QUOTES, 'UTF-8');
	echo '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">';
	echo '<title>SkyConnect chat</title><style>
body{font-family:Segoe UI,sans-serif;margin:0;background:#e8efe6;color:#163}
#log{height:70vh;overflow:auto;padding:12px}
.b{margin:8px 0;padding:8px 10px;border-radius:10px;max-width:85%}
.me{background:#1aa34a;color:#fff;margin-left:auto}
.them{background:#fff;border:1px solid #cde}
form{display:flex;gap:8px;padding:10px;background:#fff}
input,button{font:inherit} input{flex:1;padding:8px;border:1px solid #cde;border-radius:8px}
button{background:#1aa34a;color:#fff;border:0;border-radius:8px;padding:8px 14px;font-weight:700}
</style><div id="log"></div><form id="f"><input id="m" placeholder="Type a message" autocomplete="off"><button>Send</button></form>
<script>
const D=' . json_encode($dom) . ';
let key=localStorage.getItem("sc_chat_key");
if(!key){key="w"+Math.random().toString(36).slice(2)+Date.now();localStorage.setItem("sc_chat_key",key)}
const log=document.getElementById("log");
function draw(msgs){log.innerHTML=(msgs||[]).map(x=>{
 const cls=x.role==="customer"?"b me":"b them";
 const who=x.role==="customer"?"You":(x.role==="bot"?"Guide":"Agent");
 return `<div class="${cls}"><small>${who}</small><div>${(x.body||"").replace(/[<>]/g,"")}</div></div>`;
}).join(""); log.scrollTop=log.scrollHeight}
async function poll(){const r=await fetch("?op=chat_poll&domain="+encodeURIComponent(D)+"&key="+encodeURIComponent(key)); const j=await r.json(); draw(j.messages||[])}
document.getElementById("f").onsubmit=async (e)=>{e.preventDefault(); const t=document.getElementById("m").value.trim(); if(!t)return;
 document.getElementById("m").value="";
 const r=await fetch("?op=chat_send&domain="+encodeURIComponent(D),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({key,text:t})});
 const j=await r.json(); draw(j.messages||[]);};
setInterval(poll,2500); poll();
</script>';
	exit;
}

if ($ui === 'csat') {
	header('Content-Type: text/html; charset=utf-8');
	$t = htmlspecialchars((string)($_GET['t'] ?? ''), ENT_QUOTES, 'UTF-8');
	echo '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">';
	echo '<title>How was your call?</title><style>body{font-family:Segoe UI,sans-serif;background:#e8efe6;color:#163;padding:24px;max-width:420px;margin:40px auto}button{margin:4px;padding:10px 14px;border-radius:10px;border:1px solid #cde;background:#fff;font-weight:700}button.g{background:#1aa34a;color:#fff;border:0}</style>';
	echo '<h1>How was your call?</h1><p>1 = poor, 5 = excellent</p><div id="s">';
	for ($i = 1; $i <= 5; $i++) {
		echo '<button type="button" onclick="go(' . $i . ')">' . $i . '</button>';
	}
	echo '</div><p id="m"></p><script>
async function go(n){const r=await fetch("?op=csat_save",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({t:' . json_encode((string)($_GET['t'] ?? '')) . ',rating:n,resolved:"yes"})});
 const j=await r.json(); document.getElementById("m").textContent=j.ok?"Thank you.":(j.error||"Could not save");}
</script>';
	exit;
}

header('Content-Type: application/json; charset=utf-8');
$raw = file_get_contents('php://input') ?: '';
$body = json_decode($raw, true);
if (!is_array($body)) {
	$body = $_POST;
}

if ($op === 'wa' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'GET') {
	$mode = (string)($_GET['hub_mode'] ?? $_GET['hub.mode'] ?? '');
	$token = (string)($_GET['hub_verify_token'] ?? $_GET['hub.verify_token'] ?? '');
	$chal = (string)($_GET['hub_challenge'] ?? $_GET['hub.challenge'] ?? '');
	$want = getenv('SKYKIN_WA_VERIFY') ?: 'skykin';
	if ($mode === 'subscribe' && hash_equals($want, $token)) {
		header('Content-Type: text/plain');
		echo $chal;
		exit;
	}
	http_response_code(403);
	echo json_encode(['ok' => false]);
	exit;
}

if ($op === 'wa' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
	$entries = $body['entry'] ?? [];
	foreach ($entries as $en) {
		foreach (($en['changes'] ?? []) as $ch) {
			$val = $ch['value'] ?? [];
			foreach (($val['messages'] ?? []) as $m) {
				$from = (string)($m['from'] ?? '');
				$text = (string)($m['text']['body'] ?? $m['button']['text'] ?? '');
				if ($from === '' || $text === '') {
					continue;
				}
				$out = sc_omni_customer_post($db, $dom, 'whatsapp', $from, $from, $text);
				if (!empty($out['bot'])) {
					sc_omni_wa_send($from, (string)$out['bot']);
				}
			}
		}
	}
	echo json_encode(['ok' => true]);
	exit;
}

if ($op === 'chat_send' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
	$key = trim((string)($body['key'] ?? ''));
	$text = trim((string)($body['text'] ?? ''));
	if ($key === '' || $text === '') {
		echo json_encode(['ok' => false, 'error' => 'Message required']);
		exit;
	}
	echo json_encode(sc_omni_customer_post($db, $dom, 'web', $key, 'Web visitor', $text));
	exit;
}

if ($op === 'chat_poll') {
	$key = trim((string)($_GET['key'] ?? ''));
	if ($key === '') {
		echo json_encode(['ok' => true, 'messages' => []]);
		exit;
	}
	$s = $db->prepare("SELECT thread_id FROM skykin_omni_threads WHERE domain_name=:d AND channel='web' AND customer_key=:k ORDER BY thread_id DESC LIMIT 1");
	$s->execute([':d' => $dom, ':k' => $key]);
	$tid = (int)$s->fetchColumn();
	echo json_encode(['ok' => true, 'thread_id' => $tid, 'messages' => $tid ? sc_omni_msgs($db, $tid) : []]);
	exit;
}

if ($op === 'csat_save' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
	$token = trim((string)($body['t'] ?? $body['token'] ?? ''));
	$s = $db->prepare('SELECT * FROM skykin_csat_tokens WHERE token = :t LIMIT 1');
	$s->execute([':t' => $token]);
	$row = $s->fetch(PDO::FETCH_ASSOC);
	if (!$row || (int)($row['used'] ?? 0) === 1) {
		echo json_encode(['ok' => false, 'error' => 'Link already used or invalid']);
		exit;
	}
	$rating = max(1, min(5, (int)($body['rating'] ?? 0)));
	$resolved = trim((string)($body['resolved'] ?? 'yes')) ?: 'yes';
	$comment = trim((string)($body['comment'] ?? ''));
	if (function_exists('sc_ops_surveys')) {
		/* table may live only in ops — create here */
	}
	$pg = ($db->getAttribute(PDO::ATTR_DRIVER_NAME) !== 'sqlite');
	if ($pg) {
		$db->exec("CREATE TABLE IF NOT EXISTS skykin_surveys (
			survey_id SERIAL PRIMARY KEY, domain_name TEXT, agent_ext TEXT, agent_name TEXT,
			channel TEXT DEFAULT 'Voice', rating SMALLINT, resolved TEXT, comment TEXT, created_at TIMESTAMP DEFAULT NOW())");
	} else {
		$db->exec("CREATE TABLE IF NOT EXISTS skykin_surveys (
			survey_id INTEGER PRIMARY KEY AUTOINCREMENT, domain_name TEXT, agent_ext TEXT, agent_name TEXT,
			channel TEXT DEFAULT 'Voice', rating INTEGER, resolved TEXT, comment TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)");
	}
	$db->prepare("INSERT INTO skykin_surveys (domain_name, agent_ext, agent_name, channel, rating, resolved, comment)
		VALUES (:d,:e,:n,'Voice',:r,:rv,:cm)")
		->execute([
			':d' => (string)$row['domain_name'],
			':e' => (string)$row['agent_ext'],
			':n' => '',
			':r' => $rating,
			':rv' => $resolved,
			':cm' => $comment,
		]);
	$db->prepare('UPDATE skykin_csat_tokens SET used = 1 WHERE token = :t')->execute([':t' => $token]);
	echo json_encode(['ok' => true]);
	exit;
}

http_response_code(404);
echo json_encode(['ok' => false, 'error' => 'Unknown op']);
