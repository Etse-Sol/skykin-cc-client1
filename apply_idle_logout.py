#!/usr/bin/env python3
"""Apply idle-logout on ecs-cc. Run on the server as root:
   python3 /tmp/apply_idle_logout.py
"""
from pathlib import Path

D = Path("/opt/skykin/app/app/agent_dashboard")
if not D.is_dir():
    raise SystemExit("missing " + str(D))

def write(name, text):
    p = D / name
    p.write_text(text.replace("\r\n", "\n"), encoding="utf-8")
    print("wrote", p)

def patch(name, old, new, label):
    p = D / name
    t = p.read_text(encoding="utf-8")
    if new.strip()[:40] in t and old not in t:
        print("skip (already)", label)
        return
    if old not in t:
        raise SystemExit("not found in %s: %s" % (name, label))
    p.write_text(t.replace(old, new, 1), encoding="utf-8")
    print("patched", label)

write("session_bootstrap.php", r"""<?php
/**
 * Shared FusionPBX session bootstrap for SkyKin dashboards.
 * Idle logout is enforced in skykin_config.php from the admin setting.
 */
if (session_status() === PHP_SESSION_NONE) {
	$fpbx_session_path = '/var/lib/php/sessions';
	if (is_dir($fpbx_session_path)) {
		session_save_path($fpbx_session_path);
	}
	ini_set('session.gc_maxlifetime', '86400');
	ini_set('session.use_strict_mode', '1');

	$https = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off')
		|| (isset($_SERVER['SERVER_PORT']) && (string)$_SERVER['SERVER_PORT'] === '443')
		|| (isset($_SERVER['HTTP_X_FORWARDED_PROTO']) && strtolower((string)$_SERVER['HTTP_X_FORWARDED_PROTO']) === 'https');

	ini_set('session.cookie_httponly', '1');
	ini_set('session.cookie_secure', $https ? '1' : '0');
	ini_set('session.cookie_samesite', 'Lax');

	session_name('PHPSESSID');
	session_set_cookie_params([
		'lifetime' => 0,
		'path' => '/',
		'domain' => '',
		'secure' => $https,
		'httponly' => true,
		'samesite' => 'Lax',
	]);
	session_start();
}
""")

write("session_ping.php", r"""<?php
require_once __DIR__ . '/session_bootstrap.php';
require_once __DIR__ . '/skykin_config.php';

header('Content-Type: application/json');
skykin_session_enforce_idle();
if (empty($_SESSION['user_uuid']) || empty($_SESSION['authorized'])) {
	http_response_code(401);
	echo json_encode(['ok' => false, 'error' => 'Session expired', 'login' => '/logout.php']);
	exit;
}
skykin_session_touch();
echo json_encode([
	'ok' => true,
	'idleTimeoutMinutes' => skykin_idle_timeout_minutes(),
]);
""")

write("idle_watch.js", r"""(function () {
	var mins = (window.SKYKIN && Number(SKYKIN.idleTimeoutMinutes)) || 0;
	if (mins <= 0) {
		return;
	}
	var pingUrl = (window.SKYKIN && SKYKIN.idlePingUrl) || 'session_ping.php';
	var last = Date.now();
	var lastPing = 0;
	var leaving = false;

	function logoutIdle() {
		if (leaving) {
			return;
		}
		leaving = true;
		window.location = '/logout.php';
	}

	function onCall() {
		try {
			if (typeof currentAgentStatus !== 'undefined' && currentAgentStatus === 'incall') {
				return true;
			}
			if (typeof session !== 'undefined' && session) {
				return true;
			}
		} catch (e) {}
		return false;
	}

	function ping() {
		if (Date.now() - lastPing < 25000) {
			return;
		}
		lastPing = Date.now();
		fetch(pingUrl, { credentials: 'same-origin' }).then(function (res) {
			if (res.status === 401) {
				logoutIdle();
			}
		}).catch(function () {});
	}

	function mark() {
		last = Date.now();
		ping();
	}

	['click', 'keydown', 'mousemove', 'scroll', 'touchstart'].forEach(function (ev) {
		document.addEventListener(ev, mark, { passive: true });
	});

	setInterval(function () {
		if (onCall()) {
			mark();
			return;
		}
		if (Date.now() - last > mins * 60 * 1000) {
			logoutIdle();
		}
	}, 10000);
})();
""")

HELPERS = r'''
function skykin_ensure_settings_table(PDO $db): void {
	$db->exec("CREATE TABLE IF NOT EXISTS skykin_settings (
		setting_key VARCHAR(64) PRIMARY KEY,
		setting_value TEXT NOT NULL,
		updated_at TIMESTAMP DEFAULT NOW(),
		updated_by VARCHAR(255)
	)");
}

function skykin_setting_get(string $key, string $default = ''): string {
	static $cache = [];
	if (array_key_exists($key, $cache)) {
		return $cache[$key];
	}
	try {
		$db = skykin_pdo_fusionpbx();
		skykin_ensure_settings_table($db);
		$s = $db->prepare('SELECT setting_value FROM skykin_settings WHERE setting_key = :k');
		$s->execute([':k' => $key]);
		$v = $s->fetchColumn();
		$cache[$key] = ($v === false) ? $default : (string) $v;
	} catch (Throwable $e) {
		$cache[$key] = $default;
	}
	return $cache[$key];
}

function skykin_setting_set(string $key, string $value, string $by = ''): void {
	$db = skykin_pdo_fusionpbx();
	skykin_ensure_settings_table($db);
	$s = $db->prepare(
		"INSERT INTO skykin_settings (setting_key, setting_value, updated_at, updated_by)
		 VALUES (:k, :v, NOW(), :by)
		 ON CONFLICT (setting_key) DO UPDATE
		 SET setting_value = EXCLUDED.setting_value,
		     updated_at = NOW(),
		     updated_by = EXCLUDED.updated_by"
	);
	$s->execute([':k' => $key, ':v' => $value, ':by' => $by]);
}

function skykin_idle_timeout_minutes(): int {
	$n = (int) skykin_setting_get('session_idle_minutes', '30');
	if ($n < 0) { $n = 0; }
	if ($n > 1440) { $n = 1440; }
	return $n;
}

function skykin_session_clear_auth(): void {
	$_SESSION['authorized'] = false;
	unset($_SESSION['user_uuid'], $_SESSION['authorized'], $_SESSION['user']);
}

function skykin_session_enforce_idle(): void {
	if (empty($_SESSION['authorized']) && empty($_SESSION['user_uuid'])) {
		return;
	}
	$minutes = skykin_idle_timeout_minutes();
	if ($minutes <= 0) {
		return;
	}
	$last = (int) ($_SESSION['session']['last_activity'] ?? 0);
	if ($last <= 0) {
		$_SESSION['session']['last_activity'] = time();
		return;
	}
	if ((time() - $last) > ($minutes * 60)) {
		skykin_session_clear_auth();
	}
}

function skykin_session_touch(): void {
	if (empty($_SESSION['authorized']) && empty($_SESSION['user_uuid'])) {
		return;
	}
	$_SESSION['session']['last_activity'] = time();
}

'''

cfg = D / "skykin_config.php"
ct = cfg.read_text(encoding="utf-8")
if "function skykin_idle_timeout_minutes" not in ct:
    needle = "/**\n * Emit window.SKYKIN = {...} for dashboard JS.\n */"
    if needle not in ct:
        needle = "function skykin_js_bootstrap(): string {"
        ct = ct.replace(needle, HELPERS + needle, 1)
    else:
        ct = ct.replace(needle, HELPERS + needle, 1)
    print("inserted idle helpers into skykin_config.php")
else:
    print("skip helpers (already)")

if "'idleTimeoutMinutes'" not in ct:
    old_pay = "'wssPath'           => $c['wss_path'],"
    new_pay = (
        "'wssPath'             => $c['wss_path'],\n"
        "\t\t'idleTimeoutMinutes'  => skykin_idle_timeout_minutes(),\n"
        "\t\t'idlePingUrl'         => 'session_ping.php',"
    )
    if old_pay not in ct:
        raise SystemExit("wssPath payload not found")
    ct = ct.replace(old_pay, new_pay, 1)
    print("updated SKYKIN payload")
else:
    print("skip payload (already)")

old_req = """function skykin_require_login(bool $json = false): void {
	if (!empty($_SESSION['user_uuid']) && !empty($_SESSION['authorized'])) {
		return;
	}"""
new_req = """function skykin_require_login(bool $json = false): void {
	skykin_session_enforce_idle();
	if (!empty($_SESSION['user_uuid']) && !empty($_SESSION['authorized'])) {
		if (!$json) {
			skykin_session_touch();
		}
		return;
	}"""
old_req8 = """function skykin_require_login(bool $json = false): void {
	$max_age = defined('SKYKIN_SESSION_MAX_AGE') ? SKYKIN_SESSION_MAX_AGE : 28800;
	$created = (int) ($_SESSION['session']['created'] ?? 0);
	if ($created > 0 && (time() - $created) > $max_age) {
		$_SESSION['authorized'] = false;
		unset($_SESSION['user_uuid'], $_SESSION['authorized'], $_SESSION['user']);
	}
	if (!empty($_SESSION['user_uuid']) && !empty($_SESSION['authorized'])) {
		return;
	}"""
if "skykin_session_enforce_idle();" not in ct.split("function skykin_require_login", 1)[-1][:400]:
    if old_req8 in ct:
        ct = ct.replace(old_req8, new_req, 1)
        print("updated require_login (8h)")
    elif old_req in ct:
        ct = ct.replace(old_req, new_req, 1)
        print("updated require_login")
    else:
        raise SystemExit("require_login block not found")
else:
    print("skip require_login (already)")
cfg.write_text(ct, encoding="utf-8")

# index.php
idx = (D / "index.php").read_text(encoding="utf-8")
if "skykin_session_enforce_idle();" not in idx:
    old = "require_once __DIR__ . '/skykin_config.php';\n\n// Session expired / not logged in"
    new = "require_once __DIR__ . '/skykin_config.php';\n\nskykin_session_enforce_idle();\n\n// Session expired / not logged in"
    if old not in idx:
        old = "require_once __DIR__ . '/skykin_config.php';\n\n// Session expired"
        new = "require_once __DIR__ . '/skykin_config.php';\n\nskykin_session_enforce_idle();\n\n// Session expired"
    if old not in idx:
        raise SystemExit("index.php header not found")
    idx = idx.replace(old, new, 1)
    print("index enforce")
else:
    print("skip index enforce")

if "skykin_session_touch();" not in idx:
    old = """    exit;
}

// Release session lock so background polls / other tabs are not blocked
session_write_close();"""
    new = """    exit;
}

if (!isset($_GET['action'])) {
    skykin_session_touch();
}

// Release session lock so background polls / other tabs are not blocked
session_write_close();"""
    if old not in idx:
        raise SystemExit("index.php session_write_close not found")
    idx = idx.replace(old, new, 1)
    print("index touch")
else:
    print("skip index touch")

if "idle_watch.js" not in idx:
    old = """<script src="https://cdn.jsdelivr.net/npm/socket.io-client@4.8.1/dist/socket.io.min.js"></script>
<script>
<?php echo skykin_js_bootstrap(); ?>
const agentName"""
    new = """<script src="https://cdn.jsdelivr.net/npm/socket.io-client@4.8.1/dist/socket.io.min.js"></script>
<script>
<?php echo skykin_js_bootstrap(); ?>
</script>
<script src="idle_watch.js?v=20260818"></script>
<script>
const agentName"""
    if old not in idx:
        raise SystemExit("index.php script bootstrap not found")
    idx = idx.replace(old, new, 1)
    print("index idle_watch")
else:
    print("skip index idle_watch")
(D / "index.php").write_text(idx, encoding="utf-8")

# supervisor.php
sup = (D / "supervisor.php").read_text(encoding="utf-8")
if "action'] === 'save_settings'" not in sup and "action']==='save_settings'" not in sup:
    old = """    } catch(Exception $e) { echo json_encode(['rows'=>[],'error'=>$e->getMessage()]); }
    exit;
}

?>
<!DOCTYPE html>"""
    new = """    } catch(Exception $e) { echo json_encode(['rows'=>[],'error'=>$e->getMessage()]); }
    exit;
}

if (isset($_GET['action']) && $_GET['action'] === 'get_settings') {
    header('Content-Type: application/json');
    echo json_encode([
        'ok' => true,
        'session_idle_minutes' => skykin_idle_timeout_minutes(),
    ]);
    exit;
}

if (isset($_GET['action']) && $_GET['action'] === 'save_settings' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    header('Content-Type: application/json');
    $body = json_decode(file_get_contents('php://input'), true) ?: [];
    $minutes = (int) ($body['session_idle_minutes'] ?? 0);
    if ($minutes < 0) { $minutes = 0; }
    if ($minutes > 1440) { $minutes = 1440; }
    try {
        $who = (string) ($_SESSION['username'] ?? '');
        skykin_setting_set('session_idle_minutes', (string) $minutes, $who);
        echo json_encode(['ok' => true, 'session_idle_minutes' => $minutes]);
    } catch (Exception $e) {
        echo json_encode(['ok' => false, 'error' => $e->getMessage()]);
    }
    exit;
}

?>
<!DOCTYPE html>"""
    if old not in sup:
        raise SystemExit("supervisor.php voice_quality exit not found")
    sup = sup.replace(old, new, 1)
    print("supervisor APIs")
else:
    print("skip supervisor APIs")

if 'data-tab="settings"' not in sup:
    old = """            <button class="tab-btn" data-tab="skills" onclick="showTab('skills')">Agent Skills</button>
            <button class="tab-btn" data-tab="ahununu" onclick="showTab('ahununu')">&#127760; Ahununu.com</button>"""
    new = """            <button class="tab-btn" data-tab="skills" onclick="showTab('skills')">Agent Skills</button>
            <button class="tab-btn" data-tab="settings" onclick="showTab('settings')">Settings</button>
            <button class="tab-btn" data-tab="ahununu" onclick="showTab('ahununu')">&#127760; Ahununu.com</button>"""
    if old not in sup:
        raise SystemExit("supervisor.php skills tab not found")
    sup = sup.replace(old, new, 1)
    print("supervisor tab button")
else:
    print("skip supervisor tab button")

if 'id="tab-settings"' not in sup:
    old = """        </div>
    </div>
        <div class="tab-content" id="tab-ahununu" style="padding:0;height:700px">"""
    new = """        </div>
        </div>

        <div class="tab-content" id="tab-settings" style="padding:24px;max-width:560px">
            <h4 style="margin:0 0 8px;color:#333;font-size:16px">Login session</h4>
            <p style="font-size:13px;color:#666;margin:0 0 18px;line-height:1.5">
                Agents and supervisors are logged out after this many minutes with no mouse, keyboard, or active call.
                Background dashboard refresh does not count as activity. Set <strong>0</strong> to disable auto-logout.
            </p>
            <label style="display:block;font-size:12px;font-weight:700;color:#555;margin-bottom:6px">Idle logout (minutes)</label>
            <input type="number" id="idleMinutes" min="0" max="1440" step="1" value="<?php echo (int) skykin_idle_timeout_minutes(); ?>"
                   style="width:160px;padding:10px 12px;border:1px solid #d0d5dd;border-radius:8px;font-size:14px">
            <div style="margin-top:16px;display:flex;align-items:center;gap:12px">
                <button class="btn-save-settings" style="width:auto;margin:0;padding:10px 22px" onclick="saveIdleSettings()">Save</button>
                <span id="idleSaveMsg" style="font-size:12px;color:#64748b"></span>
            </div>
        </div>
    </div>
        <div class="tab-content" id="tab-ahununu" style="padding:0;height:700px">"""
    if old not in sup:
        raise SystemExit("supervisor.php ahununu tab insert point not found")
    sup = sup.replace(old, new, 1)
    print("supervisor settings panel")
else:
    print("skip supervisor settings panel")

if "idle_watch.js" not in sup:
    old = """<script>
<?php echo skykin_js_bootstrap(); ?>
const domain"""
    new = """<script>
<?php echo skykin_js_bootstrap(); ?>
</script>
<script src="idle_watch.js?v=20260818"></script>
<script>
const domain"""
    if old not in sup:
        raise SystemExit("supervisor.php js bootstrap not found")
    sup = sup.replace(old, new, 1)
    print("supervisor idle_watch")
else:
    print("skip supervisor idle_watch")

if "function saveIdleSettings()" not in sup:
    old = """    if(name==='skills') fetchSkillsAgents();
    if(name==='ahununu') {
        const f = document.getElementById('ahununuFrame');
        if (f.src === 'about:blank') f.src = (window.SKYKIN && SKYKIN.ahununuUrl) || 'https://ahununu.com/';
    }
}"""
    new = """    if(name==='skills') fetchSkillsAgents();
    if(name==='settings') loadIdleSettings();
    if(name==='ahununu') {
        const f = document.getElementById('ahununuFrame');
        if (f.src === 'about:blank') f.src = (window.SKYKIN && SKYKIN.ahununuUrl) || 'https://ahununu.com/';
    }
}"""
    if old not in sup:
        raise SystemExit("supervisor.php showTab skills not found")
    sup = sup.replace(old, new, 1)
    old2 = """    if(name==='skills') fetchSkillsAgents();
    if(name==='ahununu') {
        const f = document.getElementById('ahununuFrame');
        if (f && f.src === 'about:blank') f.src = (window.SKYKIN && SKYKIN.ahununuUrl) || 'https://ahununu.com/';
    }
}"""
    new2 = """    if(name==='skills') fetchSkillsAgents();
    if(name==='settings') loadIdleSettings();
    if(name==='ahununu') {
        const f = document.getElementById('ahununuFrame');
        if (f && f.src === 'about:blank') f.src = (window.SKYKIN && SKYKIN.ahununuUrl) || 'https://ahununu.com/';
    }
}"""
    if old2 in sup:
        sup = sup.replace(old2, new2, 1)
    js = r'''
function loadIdleSettings(){
    fetch('supervisor.php?action=get_settings', {credentials:'same-origin'})
        .then(function(r){ return r.json(); })
        .then(function(d){
            if (!d || !d.ok) return;
            var el = document.getElementById('idleMinutes');
            if (el) el.value = d.session_idle_minutes;
        }).catch(function(){});
}

function saveIdleSettings(){
    var el = document.getElementById('idleMinutes');
    var msg = document.getElementById('idleSaveMsg');
    var minutes = parseInt(el && el.value, 10);
    if (isNaN(minutes) || minutes < 0) minutes = 0;
    if (minutes > 1440) minutes = 1440;
    if (msg) msg.textContent = 'Saving...';
    fetch('supervisor.php?action=save_settings', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({session_idle_minutes: minutes})
    }).then(function(r){ return r.json(); }).then(function(d){
        if (!d || !d.ok) {
            if (msg) msg.textContent = (d && d.error) ? d.error : 'Save failed';
            return;
        }
        if (el) el.value = d.session_idle_minutes;
        if (window.SKYKIN) SKYKIN.idleTimeoutMinutes = d.session_idle_minutes;
        if (msg) msg.textContent = d.session_idle_minutes === 0
            ? 'Saved. Auto-logout is off.'
            : 'Saved. Logout after ' + d.session_idle_minutes + ' minutes idle.';
    }).catch(function(){
        if (msg) msg.textContent = 'Save failed';
    });
}

'''
    marker = "// ── Init & auto-refresh"
    if marker not in sup:
        marker = "fetchQueue();"
        if marker not in sup:
            raise SystemExit("supervisor.php init marker not found")
        sup = sup.replace(marker, js + marker, 1)
    else:
        sup = sup.replace(marker, js + marker, 1)
    print("supervisor save JS")
else:
    print("skip supervisor save JS")

(D / "supervisor.php").write_text(sup, encoding="utf-8")

WATCH = """
<script>
<?php echo skykin_js_bootstrap(); ?>
</script>
<script src="idle_watch.js?v=20260818"></script>
"""
for extra in ("evaluation.php", "tickets.php", "reports.php", "crm.php", "billing.php"):
    p = D / extra
    if not p.exists():
        print("missing", extra)
        continue
    t = p.read_text(encoding="utf-8")
    if "idle_watch.js" in t:
        print("skip", extra)
        continue
    if "</body>" not in t:
        print("no body", extra)
        continue
    t = t.replace("</body>", WATCH + "</body>", 1)
    p.write_text(t, encoding="utf-8")
    print("idle_watch", extra)

print("DONE")
print("ls ping/watch:", (D / "session_ping.php").exists(), (D / "idle_watch.js").exists())
