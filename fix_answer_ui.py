#!/usr/bin/env python3
"""Minimal fix: switch Ringing -> In Call when mobile answers (B-leg ACTIVE). No auto-drop."""
from pathlib import Path
import re
import shutil

P = Path("/opt/skykin/app/app/agent_dashboard/index.php")
t = P.read_text(encoding="utf-8", errors="replace")
shutil.copy2(P, str(P) + ".bak-answer-ui")

PHP = r"""// ── Outbound: detect mobile answer (B-leg ACTIVE); pre_answer keeps agent on Ringing ─
if (isset($_GET['action']) && $_GET['action'] === 'outbound_live') {
    error_reporting(0);
    header('Content-Type: application/json');
    $ext = preg_replace('/\D+/', '', (string)($_GET['ext'] ?? ''));
    $dest = preg_replace('/\D+/', '', (string)($_GET['dest'] ?? ''));
    $destTail = strlen($dest) >= 9 ? substr($dest, -9) : $dest;
    $blegLive = false;
    $agentLive = false;
    $blegState = '';
    $rows = [];
    if ($ext !== '' || $destTail !== '') {
        $json = json_decode(skykin_fs_api('show channels as json'), true);
        $rows = (is_array($json) ? ($json['rows'] ?? []) : []);
    }
    $isAgentRow = static function (array $row) use ($ext): bool {
        if ($ext === '') return false;
        $name = strtolower((string)($row['name'] ?? ''));
        $presence = strtolower((string)($row['presence_id'] ?? ''));
        $cid = preg_replace('/\D+/', '', (string)($row['cid_num'] ?? $row['cid_number'] ?? ''));
        $state = strtoupper((string)($row['callstate'] ?? ''));
        if (in_array($state, ['HANGUP', 'DOWN'], true)) return false;
        return (bool)preg_match('#(^|[/@])' . preg_quote($ext, '#') . '(@|$|-)#', $name)
            || strpos($presence, $ext . '@') !== false || $cid === $ext;
    };
    $isLiveRow = static function (array $row): bool {
        $state = strtoupper((string)($row['callstate'] ?? ''));
        return !in_array($state, ['HANGUP', 'DOWN'], true);
    };
    foreach ($rows as $row) {
        if (!is_array($row)) continue;
        if ($isAgentRow($row)) $agentLive = true;
        if (!$isLiveRow($row) || $isAgentRow($row)) continue;
        $name = strtolower((string)($row['name'] ?? ''));
        $dir = strtolower((string)($row['direction'] ?? ''));
        $blob = preg_replace('/\D+/', '', $name . ($row['dest'] ?? '') . ($row['callee_num'] ?? ''));
        $isExternal = (strpos($name, 'external') !== false || strpos($name, 'gateway') !== false || $dir === 'outbound');
        $numMatch = ($destTail !== '' && strlen($destTail) >= 9 && strpos($blob, $destTail) !== false);
        if ($isExternal && ($numMatch || $destTail === '')) {
            $blegLive = true;
            $blegState = strtoupper((string)($row['callstate'] ?? ''));
        }
    }
    echo json_encode([
        'live' => $blegLive || $agentLive,
        'agent' => $agentLive,
        'bleg' => $blegLive,
        'bleg_state' => $blegState,
        'channels' => count($rows),
    ]);
    exit;
}
"""

JS_POLL = r"""function stopOutboundPoll() {
    if (window._outboundPoll) { clearInterval(window._outboundPoll); window._outboundPoll = null; }
}
function startOutboundPoll(ext, dest) {
    stopOutboundPoll();
    ext = ext || localStorage.getItem('sip_ext') || serverExt || '';
    dest = dest || window.lastDialedNumber || '';
    window._outboundPollDest = dest;
    window._outboundPoll = setInterval(function() {
        if (!session || session instanceof Invitation) { stopOutboundPoll(); return; }
        if (session.state === SessionState.Terminated || session.state === SessionState.Terminating) {
            stopOutboundPoll(); return;
        }
        fetch('index.php?action=outbound_live&ext=' + encodeURIComponent(ext)
            + '&dest=' + encodeURIComponent(dest)
            + '&domain=' + encodeURIComponent(domain), { credentials: 'same-origin' })
            .then(function(r) { return r.json(); })
            .then(function(d) {
                if (!d || d.ok === false) return;
                var bst = String(d.bleg_state || '').toUpperCase();
                var answered = d.bleg && (bst === 'ACTIVE' || bst === 'ANSWER' || bst === 'EXECUTE');
                if (answered && !callStartTime && session) {
                    stopOutboundPoll();
                    window.stopRingback && window.stopRingback();
                    attachAudio(session);
                    window.startCallUI && window.startCallUI(dest || window.lastDialedNumber || '');
                    window.showToast && window.showToast('Call connected');
                }
            }).catch(function() {});
    }, 400);
}
"""

# PHP
pat = r"//[^\n]*Outbound[^\n]*\nif \(isset\(\$_GET\['action'\]\) && \$_GET\['action'\] === 'outbound_live'\) \{.*?\n    exit;\n\}"
if re.search(pat, t, re.DOTALL):
    t, n = re.subn(pat, lambda _m: PHP, t, count=1, flags=re.DOTALL)
    print("PHP outbound_live replaced:", n)
else:
    anchor = "// ── Softphone client diagnostics"
    if anchor in t:
        t = t.replace(anchor, PHP + "\n" + anchor, 1)
        print("PHP outbound_live inserted")
    else:
        print("WARN: PHP anchor not found")

# JS poll
if "function startOutboundPoll(ext, dest)" not in t:
    t = t.replace(
        "let ua = null, reg = null, session = null;\n\n// Chrome gathers",
        "let ua = null, reg = null, session = null;\n\n" + JS_POLL + "\n// Chrome gathers",
        1,
    )
    print("JS poll inserted")
else:
    t, n = re.subn(
        r"function startOutboundPoll\(ext, dest\) \{.*?^\}",
        lambda _m: JS_POLL.strip(),
        t,
        count=1,
        flags=re.DOTALL | re.MULTILINE,
    )
    print("JS poll replaced:", n)

# bindSession outbound skip early startCallUI
OLD_BIND = """            window.startCallUI && window.startCallUI(num);
            attachAudio(s);
            window.showToast && window.showToast('Call connected');

            // Pre-fill escalation form with the caller's details
            autofillEscalationForm(num);"""
NEW_BIND = """            if (!(s instanceof Invitation)) {
                startOutboundPoll(localStorage.getItem('sip_ext') || serverExt, num);
                return;
            }
            window.startCallUI && window.startCallUI(num);
            attachAudio(s);
            window.showToast && window.showToast('Call connected');

            // Pre-fill escalation form with the caller's details
            autofillEscalationForm(num);"""
if "if (!(s instanceof Invitation)) {\n                startOutboundPoll" not in t:
    t = t.replace(OLD_BIND, NEW_BIND, 1)
    print("bindSession patched")

# onAccept: no early startCallUI
t = t.replace(
    """                onAccept: function() {
                    window.stopRingback && window.stopRingback();
                    window.startCallUI && window.startCallUI(number);
                    enableSenders(inv);
                    attachAudio(inv);
                }""",
    """                onAccept: function() {
                    enableSenders(inv);
                    startOutboundPoll(localStorage.getItem('sip_ext') || serverExt, number);
                }""",
    1,
)
t = t.replace(
    """                onAccept: function() {
                    window.stopRingback && window.stopRingback();
                    enableSenders(inv);
                    attachAudio(inv);
                }""",
    """                onAccept: function() {
                    enableSenders(inv);
                    startOutboundPoll(localStorage.getItem('sip_ext') || serverExt, number);
                }""",
    1,
)

# onProgress + makeCall start poll
if "startOutboundPoll(localStorage.getItem('sip_ext')" not in t.split("onProgress: function")[1].split("onReject")[0]:
    t = t.replace(
        "                    enableSenders(inv);\n                },\n                onAccept:",
        "                    enableSenders(inv);\n                    startOutboundPoll(localStorage.getItem('sip_ext') || serverExt, number);\n                },\n                onAccept:",
        1,
    )
if "startOutboundPoll(localStorage.getItem('sip_ext')" not in t.split("bindSession(inv);")[1].split("return inv.invite")[0]:
    t = t.replace(
        "        bindSession(inv);\n        return inv.invite({",
        "        bindSession(inv);\n        startOutboundPoll(localStorage.getItem('sip_ext') || serverExt, number);\n        return inv.invite({",
        1,
    )

if "window.stopRingback = stopRingback" not in t and "function stopRingback" in t:
    t = t.replace(
        "function stopRingback() {\n    if (_rbInterval)",
        "function stopRingback() {\n    if (_rbInterval)", 1)
    m = re.search(r"function stopRingback\(\) \{.*?\n\}", t, re.DOTALL)
    if m and "window.stopRingback" not in m.group(0):
        t = t[:m.end()] + "\nwindow.stopRingback = stopRingback;\nwindow.startRingback = startRingback;\n" + t[m.end():]
        print("window ringback exports added")

P.write_text(t, encoding="utf-8")
print("bleg_state ACTIVE check:", "bst === 'ACTIVE'" in t)
print("no outboundFailHard in poll:", "outboundFailHard" not in t.split("startOutboundPoll")[1].split("function watch")[0] if "startOutboundPoll" in t else "n/a")
