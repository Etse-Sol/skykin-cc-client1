#!/usr/bin/env python3
"""Brute-force decline patch — brace-counting, no fragile regex. Run on ecs-cc."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

P = Path("/opt/skykin/app/app/agent_dashboard/index.php")
BAK = P.with_name("index.php.bak-brute-v3")

PHP_LIVE = r"""// ── Outbound: B-leg state for answer (ACTIVE) and decline detection ─────────
// SKYKIN_SAFE_DECLINE_v3
if (isset($_GET['action']) && $_GET['action'] === 'outbound_live') {
    error_reporting(0);
    header('Content-Type: application/json');
    $ext = preg_replace('/\D+/', '', (string)($_GET['ext'] ?? ''));
    $dest = preg_replace('/\D+/', '', (string)($_GET['dest'] ?? ''));
    $destTail = strlen($dest) >= 9 ? substr($dest, -9) : $dest;
    $blegLive = false;
    $agentLive = false;
    $blegState = '';
    $callUuid = '';
    $partnerUuid = '';
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
        return !in_array(strtoupper((string)($row['callstate'] ?? '')), ['HANGUP', 'DOWN'], true);
    };
    $markBleg = static function (array $row) use (&$blegLive, &$blegState): void {
        $blegLive = true;
        $blegState = strtoupper((string)($row['callstate'] ?? ''));
    };
    $destMatches = static function (array $row) use ($destTail): bool {
        if ($destTail === '' || strlen($destTail) < 9) return false;
        foreach ([(string)($row['dest'] ?? ''), (string)($row['callee_num'] ?? ''), (string)($row['name'] ?? '')] as $field) {
            $digits = preg_replace('/\D+/', '', $field);
            if ($digits !== '' && str_ends_with($digits, $destTail)) return true;
        }
        return false;
    };
    foreach ($rows as $row) {
        if (!is_array($row) || !$isLiveRow($row) || !$isAgentRow($row)) continue;
        $agentLive = true;
        $callUuid = trim((string)($row['call_uuid'] ?? $row['uuid'] ?? ''));
        $partnerUuid = trim((string)($row['b_uuid'] ?? $row['bridge_uuid'] ?? ''));
    }
    if ($partnerUuid !== '') {
        foreach ($rows as $row) {
            if (is_array($row) && $isLiveRow($row) && (string)($row['uuid'] ?? '') === $partnerUuid) {
                $markBleg($row); break;
            }
        }
    }
    if (!$blegLive && $callUuid !== '') {
        foreach ($rows as $row) {
            if (!is_array($row) || !$isLiveRow($row) || $isAgentRow($row)) continue;
            if (trim((string)($row['call_uuid'] ?? '')) === $callUuid) { $markBleg($row); break; }
        }
    }
    if (!$blegLive) {
        foreach ($rows as $row) {
            if (!is_array($row) || !$isLiveRow($row) || $isAgentRow($row)) continue;
            $name = strtolower((string)($row['name'] ?? ''));
            $dir = strtolower((string)($row['direction'] ?? ''));
            if ((strpos($name, 'sofia/external/') !== false || strpos($name, 'gateway/') !== false || $dir === 'outbound')
                && ($destTail === '' || $destMatches($row))) { $markBleg($row); }
        }
    }
    echo json_encode(['agent' => $agentLive, 'bleg' => $blegLive, 'bleg_state' => $blegState, 'channels' => count($rows)]);
    exit;
}

"""

POLL_FN = r"""function startOutboundPoll(ext, dest) {
    stopOutboundPoll();
    ext = ext || localStorage.getItem('sip_ext') || serverExt || '';
    dest = dest || window.lastDialedNumber || '';
    window._outboundPollDest = dest;
    window._outSawBlegRing = false;
    window._outAnswerTicks = 0;
    window._outDeclineTicks = 0;
    window._outMaxCh = 0;
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
                var ch = (typeof d.channels === 'number') ? d.channels : 0;
                if (ch >= 2) window._outMaxCh = Math.max(window._outMaxCh || 0, ch);
                if (d.bleg) window._outSawBlegRing = true;
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
                var partnerGone = window._outboundRingPhase && !answered && (
                    (window._outSawBlegRing && !d.bleg)
                    || (window._outMaxCh >= 2 && ch <= 1 && d.agent && !d.bleg)
                );
                if (partnerGone) {
                    window._outDeclineTicks = (window._outDeclineTicks || 0) + 1;
                    if (window._outDeclineTicks >= 1) endOutboundRing(false);
                } else if (!answered) {
                    window._outDeclineTicks = 0;
                }
            }).catch(function() {});
    }, 400);
}"""


def block_end(text: str, open_brace: int) -> int:
    depth = 0
    i = open_brace
    while i < len(text):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                if end < len(text) and text[end] == "\n":
                    end += 1
                return end
        i += 1
    return -1


def strip_php_action(text: str, action: str) -> tuple[str, bool]:
    needle = f"if (isset($_GET['action']) && $_GET['action'] === '{action}')"
    idx = text.find(needle)
    if idx < 0:
        return text, False
    line_start = text.rfind("\n", 0, idx) + 1
    pos = line_start
    while pos > 0:
        prev = text.rfind("\n", 0, pos - 1)
        if prev < 0:
            break
        line = text[prev + 1 : pos].strip()
        if line.startswith("//") or line == "":
            line_start = prev + 1
            pos = line_start
        else:
            break
    brace = text.find("{", idx)
    end = block_end(text, brace)
    if end < 0:
        return text, False
    return text[:line_start] + text[end:], True


def replace_fn(text: str, name: str, new_body: str) -> tuple[str, bool]:
    needle = f"function {name}("
    idx = text.find(needle)
    if idx < 0:
        return text, False
    brace = text.find("{", idx)
    end = block_end(text, brace)
    if end < 0:
        return text, False
    return text[:idx] + new_body + "\n" + text[end:], True


def main() -> int:
    t = P.read_text(encoding="utf-8", errors="replace")
    print("file:", P, "bytes:", len(t))
    if "SKYKIN_SAFE_DECLINE_v3" in t and "partnerGone" in t and "agentHangup && callStartTime" in t:
        print("Already patched")
        return 0

    shutil.copy2(P, BAK)
    print("Backup:", BAK)

    t, rm = strip_php_action(t, "outbound_live")
    print("removed old outbound_live:", rm)

    anchor = "// ── Softphone client diagnostics"
    if anchor not in t:
        print("ERROR: missing anchor:", anchor)
        return 1
    t = t.replace(anchor, PHP_LIVE + anchor, 1)
    print("inserted new outbound_live")

    t, rp = replace_fn(t, "startOutboundPoll", POLL_FN)
    print("replaced startOutboundPoll:", rp)

    old_end = (
        "if (callStartTime) {\n        if (window.endCall) window.endCall();\n"
        "    } else {\n        resetOutboundRingUi();\n    }"
    )
    new_end = (
        "if (agentHangup && callStartTime) {\n        if (window.endCall) window.endCall();\n"
        "    } else {\n        resetOutboundRingUi();\n    }"
    )
    if old_end in t:
        t = t.replace(old_end, new_end, 1)
        print("fixed endOutboundRing")
    elif "agentHangup && callStartTime" not in t:
        print("WARN: endOutboundRing pattern not found")

    old_accept = "window.startCallUI && window.startCallUI(number);"
    if old_accept in t and "pre_answer" in t:
        # only fix outbound onAccept block — look near startOutboundPoll after onAccept
        t = t.replace(
            "window.stopRingback && window.stopRingback();\n                    window.startCallUI && window.startCallUI(number);",
            "// pre_answer: no startCallUI here",
            1,
        )
        print("stripped early startCallUI from onAccept")

    if "window.stopRingback = stopRingback" not in t:
        idx = t.find("function stopRingback()")
        if idx >= 0:
            end = block_end(t, t.find("{", idx))
            if end > 0:
                t = t[:end] + "\nwindow.stopRingback = stopRingback;\nwindow.startRingback = startRingback;\n" + t[end:]
                print("exported stopRingback")

    P.write_text(t, encoding="utf-8")
    print("written", P)

    checks = [
        ("host SKYKIN_SAFE_DECLINE_v3", ["grep", "-c", "SKYKIN_SAFE_DECLINE_v3", str(P)]),
        ("host partnerGone", ["grep", "-c", "partnerGone", str(P)]),
        ("host agentHangup", ["grep", "-c", "agentHangup && callStartTime", str(P)]),
        (
            "container SKYKIN_SAFE_DECLINE_v3",
            [
                "docker",
                "exec",
                "skykin-web",
                "grep",
                "-c",
                "SKYKIN_SAFE_DECLINE_v3",
                "/var/www/fusionpbx/app/agent_dashboard/index.php",
            ],
        ),
    ]
    for label, cmd in checks:
        r = subprocess.run(cmd, capture_output=True, text=True)
        print(label, r.stdout.strip() or r.stderr.strip())

    return 0


if __name__ == "__main__":
    sys.exit(main())
