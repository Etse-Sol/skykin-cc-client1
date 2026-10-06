#!/usr/bin/env python3
"""
Safe outbound decline fix (pre_answer). Backs up current index.php first.

Apply:  sudo python3 apply_safe_decline.py
Restore: sudo python3 apply_safe_decline.py --restore

Marker: SKYKIN_SAFE_DECLINE_v1
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

INDEX = Path("/opt/skykin/app/app/agent_dashboard/index.php")
BACKUP = INDEX.with_name("index.php.bak-safe-rollback")
MARKER = "SKYKIN_SAFE_DECLINE_v1"

PHP_LIVE = r"""// SKYKIN_SAFE_DECLINE_v1 — outbound_live
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
    echo json_encode(['agent' => $agentLive, 'bleg' => $blegLive, 'bleg_state' => $blegState, 'channels' => count($rows)]);
    exit;
}
"""

PHP_STOP = r"""// SKYKIN_SAFE_DECLINE_v1 — outbound_stop
if (isset($_GET['action']) && $_GET['action'] === 'outbound_stop') {
    error_reporting(0);
    header('Content-Type: application/json');
    $ext = preg_replace('/\D+/', '', (string)($_GET['ext'] ?? ''));
    $dest = preg_replace('/\D+/', '', (string)($_GET['dest'] ?? ''));
    $destTail = strlen($dest) >= 9 ? substr($dest, -9) : $dest;
    $killed = [];
    $callUuid = '';
    if ($ext !== '') {
        $json = json_decode(skykin_fs_api('show channels as json'), true);
        $rows = (is_array($json) ? ($json['rows'] ?? []) : []);
        foreach ($rows as $row) {
            if (!is_array($row)) continue;
            $uuid = (string)($row['uuid'] ?? '');
            $name = strtolower((string)($row['name'] ?? ''));
            $presence = strtolower((string)($row['presence_id'] ?? ''));
            $cid = preg_replace('/\D+/', '', (string)($row['cid_num'] ?? $row['cid_number'] ?? ''));
            $isAgent = (bool)preg_match('#(^|[/@])' . preg_quote($ext, '#') . '(@|$|-)#', $name)
                || strpos($presence, $ext . '@') !== false || $cid === $ext;
            if ($isAgent && $uuid !== '') {
                $callUuid = trim((string)($row['call_uuid'] ?? $uuid));
                skykin_fs_api('uuid_kill ' . $uuid);
                $killed[] = $uuid;
            }
        }
        foreach ($rows as $row) {
            if (!is_array($row)) continue;
            $uuid = (string)($row['uuid'] ?? '');
            if ($uuid === '' || in_array($uuid, $killed, true)) continue;
            $sameCall = ($callUuid !== '' && trim((string)($row['call_uuid'] ?? '')) === $callUuid);
            $name = strtolower((string)($row['name'] ?? ''));
            $blob = preg_replace('/\D+/', '', $name . ($row['dest'] ?? '') . ($row['callee_num'] ?? ''));
            $isExternal = (strpos($name, 'external') !== false || strpos($name, 'gateway') !== false);
            $numMatch = ($destTail !== '' && strlen($destTail) >= 9 && strpos($blob, $destTail) !== false);
            if ($sameCall || ($isExternal && ($numMatch || $callUuid !== ''))) {
                skykin_fs_api('uuid_kill ' . $uuid);
                $killed[] = $uuid;
            }
        }
    }
    echo json_encode(['ok' => true, 'killed' => $killed]);
    exit;
}
"""

JS_BLOCK = r"""// SKYKIN_SAFE_DECLINE_v1
function stopOutboundPoll() {
    if (window._outboundPoll) { clearInterval(window._outboundPoll); window._outboundPoll = null; }
}
function resetOutboundRingUi() {
    stopOutboundPoll();
    window._outboundRingPhase = false;
    window._outSawBlegRing = false;
    window._outAnswerTicks = 0;
    window._outDeclineTicks = 0;
    window.stopRingback && window.stopRingback();
    window.stopRingtone && window.stopRingtone();
    try {
        document.getElementById('btnHangup').style.display = 'none';
        document.getElementById('btnCall').style.display = 'block';
        document.getElementById('phonePopup').classList.remove('call-active');
        document.getElementById('callTimer').style.display = 'none';
    } catch (e) {}
    const ext = localStorage.getItem('sip_ext') || serverExt || '';
    window.setSipStatus && window.setSipStatus('registered', 'Registered (' + ext + ')');
}
function endOutboundRing(agentHangup) {
    const ext = localStorage.getItem('sip_ext') || serverExt || '';
    const dest = window._outboundPollDest || window.lastDialedNumber || '';
    fetch('index.php?action=outbound_stop&ext=' + encodeURIComponent(ext)
        + '&dest=' + encodeURIComponent(dest)
        + '&domain=' + encodeURIComponent(domain), { credentials: 'same-origin' }).catch(function() {});
    const s = session;
    try {
        if (s && !(s instanceof Invitation)
            && s.state !== SessionState.Terminated
            && s.state !== SessionState.Terminating) {
            try { s.bye(); } catch (e) { try { s.cancel && s.cancel(); } catch (e2) {} }
            try { s.dispose && s.dispose(); } catch (e) {}
        }
    } catch (e) {}
    if (session === s) session = null;
    if (callStartTime) { if (window.endCall) window.endCall(); }
    else { resetOutboundRingUi(); }
}
window.endOutboundRing = endOutboundRing;
function startOutboundPoll(ext, dest) {
    stopOutboundPoll();
    ext = ext || localStorage.getItem('sip_ext') || serverExt || '';
    dest = dest || window.lastDialedNumber || '';
    window._outboundPollDest = dest;
    window._outSawBlegRing = false;
    window._outAnswerTicks = 0;
    window._outDeclineTicks = 0;
    window._outboundPoll = setInterval(function() {
        if (!session || session instanceof Invitation) { stopOutboundPoll(); return; }
        if (session.state === SessionState.Terminated || session.state === SessionState.Terminating) {
            stopOutboundPoll(); return;
        }
        if (!window._outboundRingPhase && callStartTime) { stopOutboundPoll(); return; }
        fetch('index.php?action=outbound_live&ext=' + encodeURIComponent(ext)
            + '&dest=' + encodeURIComponent(dest)
            + '&domain=' + encodeURIComponent(domain), { credentials: 'same-origin' })
            .then(function(r) { return r.json(); })
            .then(function(d) {
                if (!d || d.ok === false) return;
                var bst = String(d.bleg_state || '').toUpperCase();
                if (d.bleg && (bst === 'RINGING' || bst === 'EARLY' || bst === 'DIALING')) {
                    window._outSawBlegRing = true;
                }
                var answered = !!(d.bleg && (bst === 'ACTIVE' || bst === 'ANSWER' || bst === 'EXECUTE'));
                if (answered && !callStartTime) {
                    window._outAnswerTicks = (window._outAnswerTicks || 0) + 1;
                    if (window._outAnswerTicks >= 2) {
                        window._outboundRingPhase = false;
                        stopOutboundPoll();
                        window.stopRingback && window.stopRingback();
                        enableSenders(session);
                        if (!session._skykinAudioAttached) attachAudio(session);
                        window.startCallUI && window.startCallUI(dest || window.lastDialedNumber || '');
                        window.showToast && window.showToast('Call connected');
                    }
                    return;
                }
                window._outAnswerTicks = 0;
                if (window._outboundRingPhase && window._outSawBlegRing && !d.bleg) {
                    window._outDeclineTicks = (window._outDeclineTicks || 0) + 1;
                    if (window._outDeclineTicks >= 2) endOutboundRing(false);
                } else if (!answered) {
                    window._outDeclineTicks = 0;
                }
            }).catch(function() {});
    }, 400);
}
"""


def restore() -> int:
    if not BACKUP.is_file():
        print("ERROR: no backup at", BACKUP)
        return 1
    shutil.copy2(BACKUP, INDEX)
    print("RESTORED from", BACKUP)
    return 0


def apply() -> int:
    if not INDEX.is_file():
        print("ERROR: missing", INDEX)
        return 1
    t = INDEX.read_text(encoding="utf-8", errors="replace")
    if MARKER in t and "function endOutboundRing" in t and "_outDeclineTicks" in t:
        print("Already applied (", MARKER, ")")
        return 0
    shutil.copy2(INDEX, BACKUP)
    print("Backup:", BACKUP)

    anchor = "// ── Softphone client diagnostics"
    if anchor not in t:
        print("ERROR: PHP anchor not found")
        return 1
    if "outbound_live" not in t:
        t = t.replace(anchor, PHP_LIVE + "\n" + PHP_STOP + "\n" + anchor, 1)
    elif MARKER not in t:
        # Upgrade existing outbound_live block header only
        t = t.replace(
            "if (isset($_GET['action']) && $_GET['action'] === 'outbound_live') {",
            "// SKYKIN_SAFE_DECLINE_v1\nif (isset($_GET['action']) && $_GET['action'] === 'outbound_live') {",
            1,
        )

    if "window.stopRingback = stopRingback" not in t:
        m = re.search(r"function stopRingback\(\) \{.*?\n\}", t, re.DOTALL)
        if m:
            t = t[: m.end()] + "\nwindow.stopRingback = stopRingback;\nwindow.startRingback = startRingback;\n" + t[m.end() :]

    if "window._outboundRingPhase && window.endOutboundRing" not in t:
        t = t.replace(
            "function hangupCall() {\n    if (sipBridge.hangup) sipBridge.hangup();",
            "function hangupCall() {\n    if (window._outboundRingPhase && window.endOutboundRing) {\n        window.endOutboundRing(true);\n        return;\n    }\n    if (sipBridge.hangup) sipBridge.hangup();",
            1,
        )

    if "function startOutboundPoll" not in t:
        for needle in (
            "let ua = null, reg = null, session = null;\n\n// Chrome gathers",
            "let ua = null, reg = null, session = null;\n\n// SKYKIN_SAFE_DECLINE",
        ):
            if needle in t:
                t = t.replace(needle, "let ua = null, reg = null, session = null;\n\n" + JS_BLOCK + "\n// Chrome gathers", 1)
                break
        else:
            t = t.replace(
                "let ua = null, reg = null, session = null;\n",
                "let ua = null, reg = null, session = null;\n\n" + JS_BLOCK + "\n",
                1,
            )
    elif "_outDeclineTicks" not in t and "function stopOutboundPoll" in t:
        t = re.sub(
            r"function stopOutboundPoll\(\) \{.*?\n\}\n\n// Chrome gathers",
            JS_BLOCK + "\n// Chrome gathers",
            t,
            count=1,
            flags=re.DOTALL,
        )

    old_bind = """            window.startCallUI && window.startCallUI(num);
            attachAudio(s);
            window.showToast && window.showToast('Call connected');

            // Pre-fill escalation form with the caller's details
            autofillEscalationForm(num);"""
    new_bind = """            if (!(s instanceof Invitation)) {
                window._outboundRingPhase = true;
                startOutboundPoll(localStorage.getItem('sip_ext') || serverExt, num);
                return;
            }
            window.startCallUI && window.startCallUI(num);
            attachAudio(s);
            window.showToast && window.showToast('Call connected');

            // Pre-fill escalation form with the caller's details
            autofillEscalationForm(num);"""
    if "!(s instanceof Invitation)" not in t.split("function bindSession")[1].split("ua.delegate")[0]:
        t = t.replace(old_bind, new_bind, 1)

    if "if (s instanceof Invitation) {" not in t.split("function bindSession")[1].split("if (state === SessionState.Established)")[0]:
        t = t.replace(
            "        if (state === SessionState.Established || state === SessionState.Terminated\n            || state === SessionState.Terminating) {\n            window.stopRingback && window.stopRingback();\n        }",
            "        if (state === SessionState.Established || state === SessionState.Terminated\n            || state === SessionState.Terminating) {\n            if (s instanceof Invitation) {\n                window.stopRingback && window.stopRingback();\n            }\n        }",
            1,
        )

    old_term = """            if (s._skykinEstablished) {
                if (window.endCall) window.endCall();
            } else {
                window.stopRingtone && window.stopRingtone();
                if (window.resetMissedRing) window.resetMissedRing();
            }"""
    new_term = """            if (!(s instanceof Invitation) && !callStartTime) {
                resetOutboundRingUi();
            } else if (s._skykinEstablished) {
                if (window.endCall) window.endCall();
            } else {
                window.stopRingtone && window.stopRingtone();
                if (window.resetMissedRing) window.resetMissedRing();
            }"""
    if "resetOutboundRingUi()" not in t:
        t = t.replace(old_term, new_term, 1)

    old_make = """        session = inv;
        window.setSipStatus && window.setSipStatus('calling', 'Calling ' + number);
        bindSession(inv);
        return inv.invite({"""
    new_make = """        session = inv;
        window.lastDialedNumber = number;
        window.lastCallType = 'Outbound';
        window._outboundRingPhase = true;
        window.setSipStatus && window.setSipStatus('calling', 'Calling ' + number);
        bindSession(inv);
        startOutboundPoll(localStorage.getItem('sip_ext') || serverExt, number);
        return inv.invite({"""
    make_chunk = t.split("session = inv")
    if len(make_chunk) > 1 and "window._outboundRingPhase = true" not in make_chunk[1].split("return inv.invite")[0]:
        t = t.replace(old_make, new_make, 1)

    old_accept = """                onAccept: function() {
                    window.stopRingback && window.stopRingback();
                    window.startCallUI && window.startCallUI(number);
                    enableSenders(inv);
                    attachAudio(inv);
                }"""
    new_accept = """                onAccept: function() {
                    enableSenders(inv);
                    if (!inv._skykinAudioAttached) attachAudio(inv);
                    startOutboundPoll(localStorage.getItem('sip_ext') || serverExt, number);
                }"""
    if old_accept in t:
        t = t.replace(old_accept, new_accept, 1)

    if "onProgress: function" in t:
        prog = t.split("onProgress: function")[1].split("onAccept")[0]
        if "startOutboundPoll(localStorage.getItem('sip_ext') || serverExt, number);" not in prog:
            t = t.replace(
                "                    enableSenders(inv);\n                },\n                onAccept:",
                "                    enableSenders(inv);\n                    startOutboundPoll(localStorage.getItem('sip_ext') || serverExt, number);\n                },\n                onAccept:",
                1,
            )

    t = re.sub(r"\s*outboundFailHard\(\);\s*", "\n", t)
    t = t.replace("outboundFailHard", "endOutboundRing")

    INDEX.write_text(t, encoding="utf-8")
    print("APPLIED", MARKER)
    print("Restore: sudo python3", Path(__file__).name, "--restore")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--restore", action="store_true")
    args = p.parse_args()
    return restore() if args.restore else apply()


if __name__ == "__main__":
    sys.exit(main())
