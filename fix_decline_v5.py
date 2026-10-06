#!/usr/bin/env python3
"""Decline fix v5 — run on ecs-cc. Backs up then patches index.php."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

P = Path("/opt/skykin/app/app/agent_dashboard/index.php")
BAK = P.with_name("index.php.bak-decline-v5")

PHP = r"""// ── Outbound: B-leg state for answer (ACTIVE) and decline detection ─────────
// SKYKIN_SAFE_DECLINE_v3
if (isset($_GET['action']) && $_GET['action'] === 'outbound_live') {
    error_reporting(0);
    header('Content-Type: application/json');
    $ext = preg_replace('/\D+/', '', (string)($_GET['ext'] ?? ''));
    $dest = preg_replace('/\D+/', '', (string)($_GET['dest'] ?? ''));
    $destTail = strlen($dest) >= 9 ? substr($dest, -9) : $dest;
    $blegLive = false; $agentLive = false; $blegState = '';
    $callUuid = ''; $partnerUuid = '';
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
        foreach ([
            (string)($row['dest'] ?? ''),
            (string)($row['callee_num'] ?? $row['callee_id_number'] ?? ''),
            (string)($row['name'] ?? ''),
        ] as $field) {
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
                && ($destTail === '' || $destMatches($row))) {
                $markBleg($row);
            }
        }
    }
    echo json_encode(['agent' => $agentLive, 'bleg' => $blegLive, 'bleg_state' => $blegState, 'channels' => count($rows)]);
    exit;
}
"""


def main() -> None:
    t = P.read_text(encoding="utf-8", errors="replace")
    if "SKYKIN_SAFE_DECLINE_v3" in t and "agentHangup && callStartTime" in t:
        print("Already v5/v3")
        return
    shutil.copy2(P, BAK)
    print("Backup:", BAK)

    if "outbound_live" not in t:
        anchor = "// ── Softphone client diagnostics"
        t = t.replace(anchor, PHP + "\n" + anchor, 1)
    else:
        t, n = re.subn(
            r"// ── Outbound:.*?outbound_live'\) \{.*?\n    exit;\n\}",
            lambda _m: PHP.rstrip(),
            t,
            count=1,
            flags=re.DOTALL,
        )
        print("PHP block:", n)

    t = re.sub(r"// SKYKIN_SAFE_DECLINE_v[0-9]+", "// SKYKIN_SAFE_DECLINE_v3", t)

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
        print("fixed onAccept")

    t = t.replace(
        "window._outboundRingPhase && !callStartTime && !answered",
        "window._outboundRingPhase && !answered",
    )

    t = t.replace(
        "if (callStartTime) {\n        if (window.endCall) window.endCall();\n    } else {\n        resetOutboundRingUi();\n    }",
        "if (agentHangup && callStartTime) {\n        if (window.endCall) window.endCall();\n    } else {\n        resetOutboundRingUi();\n    }",
    )

    if "_outMaxCh" not in t:
        t = t.replace(
            "if (d.bleg && (bst === 'RINGING'",
            "if (d.bleg) { window._outSawBlegRing = true; }\n                if (d.bleg && (bst === 'RINGING'",
            1,
        )
        t = t.replace(
            "window._outDeclineTicks = 0;\n    window._outboundPoll = setInterval",
            "window._outDeclineTicks = 0;\n    window._outMaxCh = 0;\n    window._outboundPoll = setInterval",
            1,
        )
        t = t.replace(
            "var bst = String(d.bleg_state || '').toUpperCase();",
            "var bst = String(d.bleg_state || '').toUpperCase();\n                var ch = (typeof d.channels === 'number') ? d.channels : 0;\n                if (ch >= 2) window._outMaxCh = Math.max(window._outMaxCh || 0, ch);\n                if (d.bleg) window._outSawBlegRing = true;",
            1,
        )
        t = t.replace(
            "if (window._outboundRingPhase && window._outSawBlegRing && !d.bleg)",
            "var partnerGone = window._outboundRingPhase && !answered && ((window._outSawBlegRing && !d.bleg) || (window._outMaxCh >= 2 && ch <= 1 && d.agent && !d.bleg));\n                if (partnerGone",
            1,
        )

    if "function startOutboundPoll" not in t:
        print("ERROR: no startOutboundPoll — run apply_safe_decline.py first")
        return

    if "window.stopRingback = stopRingback" not in t:
        m = re.search(r"function stopRingback\(\) \{.*?\n\}", t, re.DOTALL)
        if m:
            t = t[:m.end()] + "\nwindow.stopRingback = stopRingback;\nwindow.startRingback = startRingback;\n" + t[m.end():]

    P.write_text(t, encoding="utf-8")
    print("DONE — Ctrl+Shift+R in browser")
    print("Test API:")
    print("  docker exec skykin-web php -r \"require 'skykin_config.php'; \\$_GET=['ext'=>'201','dest'=>'0902925776'];\" ...")
    print("Restore:", BAK)


if __name__ == "__main__":
    main()
