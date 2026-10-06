#!/usr/bin/env python3
"""Apply decline fix v3 to live index.php on ecs-cc."""
import re
import shutil
from pathlib import Path

INDEX = Path("/opt/skykin/app/app/agent_dashboard/index.php")

PHP_LIVE = r"""// Outbound live check (B-leg state; agent may stay up after pre_answer)
if (isset($_GET['action']) && $_GET['action'] === 'outbound_live') {
    error_reporting(0);
    header('Content-Type: application/json');
    $ext = preg_replace('/\D+/', '', (string)($_GET['ext'] ?? ''));
    $dest = preg_replace('/\D+/', '', (string)($_GET['dest'] ?? ''));
    $destTail = strlen($dest) >= 9 ? substr($dest, -9) : $dest;
    $blegLive = false;
    $agentLive = false;
    $blegState = '';
    $agentUuid = '';
    if ($ext !== '' || $destTail !== '') {
        $json = json_decode(skykin_fs_api('show channels as json'), true);
        foreach ((is_array($json) ? ($json['rows'] ?? []) : []) as $row) {
            if (!is_array($row)) continue;
            $uuid = (string)($row['uuid'] ?? '');
            $name = strtolower((string)($row['name'] ?? ''));
            $presence = strtolower((string)($row['presence_id'] ?? ''));
            $rowDest = preg_replace('/\D+/', '', (string)($row['dest'] ?? ''));
            $callee = preg_replace('/\D+/', '', (string)($row['callee_num'] ?? $row['callee_id_number'] ?? ''));
            $appdata = preg_replace('/\D+/', '', (string)($row['application_data'] ?? ''));
            $cid = preg_replace('/\D+/', '', (string)($row['cid_num'] ?? $row['cid_number'] ?? ''));
            $dir = strtolower((string)($row['direction'] ?? ''));
            $state = strtoupper((string)($row['callstate'] ?? ''));
            if (in_array($state, ['HANGUP', 'DOWN'], true)) continue;
            $isAgent = false;
            if ($ext !== '') {
                $isAgent = (bool)preg_match('#(^|[/@])' . preg_quote($ext, '#') . '(@|$|-)#', $name)
                    || strpos($presence, $ext . '@') !== false || $cid === $ext;
            }
            if ($isAgent) {
                $agentLive = true;
                if ($agentUuid === '' && $uuid !== '') $agentUuid = $uuid;
                continue;
            }
            $numMatch = false;
            if ($destTail !== '') {
                foreach ([$rowDest, $callee, $appdata] as $digits) {
                    if ($digits === '') continue;
                    if (str_ends_with($digits, $destTail) || str_ends_with($destTail, substr($digits, -9))) {
                        $numMatch = true; break;
                    }
                }
            }
            $isGateway = (strpos($name, 'sofia/external/') !== false)
                || (strpos($name, 'gateway/') !== false)
                || ($dir === 'outbound' && $numMatch);
            if ($isGateway && ($numMatch || $destTail === '')) {
                $blegLive = true;
                $blegState = $state;
            }
        }
    }
    echo json_encode(['live' => $blegLive, 'agent' => $agentLive, 'bleg' => $blegLive,
        'bleg_state' => $blegState, 'agent_uuid' => $agentUuid]);
    exit;
}

// Force-hangup agent FS leg when mobile declined
if (isset($_GET['action']) && $_GET['action'] === 'outbound_stop') {
    error_reporting(0);
    header('Content-Type: application/json');
    $ext = preg_replace('/\D+/', '', (string)($_GET['ext'] ?? ''));
    $killed = '';
    if ($ext !== '') {
        $json = json_decode(skykin_fs_api('show channels as json'), true);
        foreach ((is_array($json) ? ($json['rows'] ?? []) : []) as $row) {
            if (!is_array($row)) continue;
            $uuid = (string)($row['uuid'] ?? '');
            $name = strtolower((string)($row['name'] ?? ''));
            $presence = strtolower((string)($row['presence_id'] ?? ''));
            $cid = preg_replace('/\D+/', '', (string)($row['cid_num'] ?? $row['cid_number'] ?? ''));
            $isAgent = (bool)preg_match('#(^|[/@])' . preg_quote($ext, '#') . '(@|$|-)#', $name)
                || strpos($presence, $ext . '@') !== false || $cid === $ext;
            if ($isAgent && $uuid !== '') {
                skykin_fs_api('uuid_kill ' . $uuid);
                $killed = $uuid;
                break;
            }
        }
    }
    echo json_encode(['ok' => true, 'killed' => $killed]);
    exit;
}"""

JS_BLOCK = r"""function outboundFailHard() {
    if (window._outboundFailBusy) return;
    window._outboundFailBusy = true;
    stopOutboundPoll();
    window._outboundRingPhase = false;
    window._outboundSawBleg = false;
    try { stopRingback(); } catch (e) {}
    try { stopRingtone(); } catch (e) {}
    try {
        const el = document.getElementById('remoteAudio');
        if (el) { el.muted = true; el.pause(); el.srcObject = null; }
    } catch (e) {}
    const ext = localStorage.getItem('sip_ext') || serverExt || '';
    fetch('index.php?action=outbound_stop&ext=' + encodeURIComponent(ext)
        + '&domain=' + encodeURIComponent(domain), { credentials: 'same-origin' }).catch(function() {});
    try {
        if (session && !(session instanceof Invitation)
            && session.state !== SessionState.Terminated
            && session.state !== SessionState.Terminating) {
            sipBridge.hangup && sipBridge.hangup();
        }
    } catch (e) {}
    resetOutboundFail();
    window._outboundFailBusy = false;
}
window.outboundFailHard = outboundFailHard;

function stopOutboundPoll() {
    if (window._outboundPoll) { clearInterval(window._outboundPoll); window._outboundPoll = null; }
    window._outboundSawLive = false;
    window._outboundSawBleg = false;
    window._outboundIdle = 0;
}
function startOutboundRingUI(number) {
    window._outboundRingPhase = true;
    stopRingtone();
    stopRingback();
    setSipStatus('calling', 'Ringing ' + number);
    document.getElementById('btnCall').style.display = 'none';
    document.getElementById('btnHangup').style.display = 'block';
    document.getElementById('phonePopup').classList.add('call-active');
    document.getElementById('btnHold').style.display = 'none';
    document.getElementById('btnMute').style.display = 'none';
    document.getElementById('callTimer').style.display = 'none';
}
function startOutboundPoll(ext, dest) {
    stopOutboundPoll();
    ext = ext || localStorage.getItem('sip_ext') || serverExt || '';
    window._outboundPollDest = dest || window.lastDialedNumber || '';
    window._outboundPoll = setInterval(function() {
        if (!session || session instanceof Invitation) { stopOutboundPoll(); return; }
        fetch('index.php?action=outbound_live&ext=' + encodeURIComponent(ext)
            + '&dest=' + encodeURIComponent(window._outboundPollDest || dest || '')
            + '&domain=' + encodeURIComponent(domain), { credentials: 'same-origin' })
            .then(function(r) { return r.json(); })
            .then(function(d) {
                var bleg = !!(d && d.bleg);
                var bst = ((d && d.bleg_state) || '').toUpperCase();
                if (bleg) {
                    window._outboundSawBleg = true;
                    window._outboundIdle = 0;
                    if (window._outboundRingPhase && bst === 'ACTIVE') {
                        window._outboundRingPhase = false;
                        startCallUI(window._outboundPollDest || window.lastDialedNumber || '');
                    }
                    return;
                }
                if (window._outboundSawBleg) { outboundFailHard(); return; }
                if (d && d.agent && window._outboundRingPhase) {
                    window._outboundIdle = (window._outboundIdle || 0) + 1;
                    if (window._outboundIdle >= 8) outboundFailHard();
                }
            }).catch(function() {});
    }, 400);
}"""


def main() -> None:
    text = INDEX.read_text(encoding="utf-8", errors="replace")
    shutil.copy2(INDEX, str(INDEX) + ".bak-decline-v3")

    # PHP: replace outbound_live block through before client_log
    text = re.sub(
        r"//[^\n]*Outbound live check.*?\nif \(isset\(\$_GET\['action'\]\) && \$_GET\['action'\] === 'outbound_live'\) \{.*?\n    exit;\n\}\n*(//[^\n]*outbound_stop.*?\n    exit;\n\})?",
        PHP_LIVE + "\n\n",
        text,
        count=1,
        flags=re.DOTALL,
    )
    if "outbound_stop" not in text:
        text = text.replace(
            "// ── Softphone client diagnostics",
            PHP_LIVE + "\n\n// ── Softphone client diagnostics",
            1,
        )

    if "function outboundFailHard" not in text:
        text = text.replace(
            "// Outbound failed/declined:",
            JS_BLOCK + "\n\n// Outbound failed/declined:",
            1,
        )
    else:
        text = re.sub(
            r"function outboundFailHard\(\) \{.*?^window\.outboundFailHard = outboundFailHard;",
            JS_BLOCK.split("function stopOutboundPoll")[0].strip(),
            text,
            count=1,
            flags=re.DOTALL | re.MULTILINE,
        )
        text = re.sub(
            r"function stopOutboundPoll\(\) \{.*?function startOutboundPoll\(ext, dest\) \{.*?\n\}",
            "\n".join(JS_BLOCK.split("\n")[JS_BLOCK.split("\n").index("function stopOutboundPoll()"):]),
            text,
            count=1,
            flags=re.DOTALL,
        )

    if "window._outboundRingPhase = false" not in text.split("function resetOutboundFail")[1].split("}", 1)[0]:
        text = text.replace(
            "function resetOutboundFail() {\n    stopOutboundPoll();",
            "function resetOutboundFail() {\n    stopOutboundPoll();\n    window._outboundRingPhase = false;\n    window._outboundSawBleg = false;",
            1,
        )

    # bindSession outbound ring UI
    old_est = "window.startCallUI && window.startCallUI(num);\n            attachAudio(s);\n            watchOutboundPeer(s);"
    new_est = """attachAudio(s);
            watchOutboundPeer(s);
            if (!(s instanceof Invitation)) {
                startOutboundRingUI(num);
                startOutboundPoll(localStorage.getItem('sip_ext') || serverExt, num);
            } else {
                window.startCallUI && window.startCallUI(num);
                window.showToast && window.showToast('Call connected');
            }"""
    if "startOutboundRingUI(num)" not in text and old_est in text:
        text = text.replace(old_est, new_est, 1)

    # onProgress: remove local ringback
    text = re.sub(
        r"window\.startRingback && window\.startRingback\(\);\s*\n\s*enableSenders\(inv\);",
        "enableSenders(inv);",
        text,
    )

    # onAccept: no premature startCallUI
    text = re.sub(
        r"onAccept: function\(\) \{\s*\n\s*window\.stopRingback.*?\n\s*window\.startCallUI && window\.startCallUI\(number\);\s*\n",
        "onAccept: function() {\n                    window.stopRingback && window.stopRingback();\n",
        text,
        count=1,
        flags=re.DOTALL,
    )
    text = text.replace("resetOutboundFail();", "outboundFailHard();", 1)  # onReject only risky
    text = text.replace("onReject: function(response) {\n                    var code = response && response.message && response.message.statusCode;\n                    if (code === 401 || code === 407) return;\n                    outboundFailHard();", 
                        "onReject: function(response) {\n                    var code = response && response.message && response.message.statusCode;\n                    if (code === 401 || code === 407) return;\n                    outboundFailHard();")

    if "bindSession(inv);\n        startOutboundPoll" not in text:
        text = text.replace(
            "bindSession(inv);\n        return inv.invite",
            "bindSession(inv);\n        startOutboundPoll(localStorage.getItem('sip_ext') || serverExt, number);\n        return inv.invite",
            1,
        )

    INDEX.write_text(text, encoding="utf-8")
    print("outbound_stop:", text.count("outbound_stop"))
    print("outboundFailHard:", text.count("outboundFailHard"))
    print("startOutboundRingUI:", text.count("startOutboundRingUI"))
    print("startOutboundPoll calls:", text.count("startOutboundPoll(localStorage"))


if __name__ == "__main__":
    main()
