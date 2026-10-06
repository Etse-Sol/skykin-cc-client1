#!/usr/bin/env python3
"""Decline fix v4: b_uuid B-leg detect + channel-count fallback. Run on ecs-cc."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

INDEX = Path("/opt/skykin/app/app/agent_dashboard/index.php")
BACKUP = INDEX.with_name("index.php.bak-decline-v4")

PHP_LIVE = r"""// ── Outbound: B-leg state for answer (ACTIVE) and decline detection ─────────
// SKYKIN_SAFE_DECLINE_v2
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
        $state = strtoupper((string)($row['callstate'] ?? ''));
        return !in_array($state, ['HANGUP', 'DOWN'], true);
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
            (string)($row['application_data'] ?? ''),
            (string)($row['name'] ?? ''),
        ] as $field) {
            $digits = preg_replace('/\D+/', '', $field);
            if ($digits === '') continue;
            if (str_ends_with($digits, $destTail) || str_ends_with($destTail, substr($digits, -9))) {
                return true;
            }
        }
        return false;
    };
    foreach ($rows as $row) {
        if (!is_array($row) || !$isLiveRow($row) || !$isAgentRow($row)) continue;
        $agentLive = true;
        $agentUuid = (string)($row['uuid'] ?? '');
        $callUuid = trim((string)($row['call_uuid'] ?? $agentUuid));
        $partnerUuid = trim((string)($row['b_uuid'] ?? $row['bridge_uuid'] ?? ''));
    }
    if ($partnerUuid !== '') {
        foreach ($rows as $row) {
            if (!is_array($row) || !$isLiveRow($row)) continue;
            if ((string)($row['uuid'] ?? '') === $partnerUuid) {
                $markBleg($row);
                break;
            }
        }
    }
    if (!$blegLive && $callUuid !== '') {
        foreach ($rows as $row) {
            if (!is_array($row) || !$isLiveRow($row) || $isAgentRow($row)) continue;
            if (trim((string)($row['call_uuid'] ?? '')) === $callUuid) {
                $markBleg($row);
                break;
            }
        }
    }
    if (!$blegLive) {
        foreach ($rows as $row) {
            if (!is_array($row) || !$isLiveRow($row) || $isAgentRow($row)) continue;
            $name = strtolower((string)($row['name'] ?? ''));
            $dir = strtolower((string)($row['direction'] ?? ''));
            $isGateway = (strpos($name, 'sofia/external/') !== false)
                || (strpos($name, 'sofia/gateway/') !== false)
                || (strpos($name, 'gateway/') !== false)
                || $dir === 'outbound';
            if ($isGateway && ($destTail === '' || $destMatches($row))) {
                $markBleg($row);
            }
        }
    }
    echo json_encode([
        'agent' => $agentLive,
        'bleg' => $blegLive,
        'bleg_state' => $blegState,
        'channels' => count($rows),
        'partner_uuid' => $partnerUuid,
    ]);
    exit;
}
"""

JS_POLL_BODY = r"""                if (!d || d.ok === false) return;
                var bst = String(d.bleg_state || '').toUpperCase();
                var ch = (typeof d.channels === 'number') ? d.channels : 0;
                if (ch >= 2) {
                    window._outMaxCh = Math.max(window._outMaxCh || 0, ch);
                }
                if (d.bleg) {
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
                var partnerGone = window._outboundRingPhase && !callStartTime && !answered && (
                    (window._outSawBlegRing && !d.bleg)
                    || (window._outMaxCh >= 2 && ch <= 1 && d.agent && !d.bleg)
                );
                if (partnerGone) {
                    window._outDeclineTicks = (window._outDeclineTicks || 0) + 1;
                    if (window._outDeclineTicks >= 1) endOutboundRing(false);
                } else if (!answered) {
                    window._outDeclineTicks = 0;
                }"""


def main() -> None:
    t = INDEX.read_text(encoding="utf-8", errors="replace")
    if "SKYKIN_SAFE_DECLINE_v2" in t and "_outMaxCh" in t:
        print("Already v2")
        return
    shutil.copy2(INDEX, BACKUP)
    print("Backup:", BACKUP)

    t, n1 = re.subn(
        r"// ── Outbound: B-leg state.*?if \(isset\(\$_GET\['action'\]\) && \$_GET\['action'\] === 'outbound_live'\) \{.*?\n    exit;\n\}",
        PHP_LIVE.rstrip(),
        t,
        count=1,
        flags=re.DOTALL,
    )
    print("PHP replaced:", n1)

    t = t.replace("// SKYKIN_SAFE_DECLINE_v1", "// SKYKIN_SAFE_DECLINE_v2")
    if "window._outMaxCh = 0" not in t:
        t = t.replace(
            "window._outDeclineTicks = 0;\n    window.stopRingback",
            "window._outDeclineTicks = 0;\n    window._outMaxCh = 0;\n    window.stopRingback",
        )
        t = t.replace(
            "window._outDeclineTicks = 0;\n    window._outboundPoll = setInterval",
            "window._outDeclineTicks = 0;\n    window._outMaxCh = 0;\n    window._outboundPoll = setInterval",
        )
        t = t.replace(
            "window._outboundRingPhase = true;\n        window.setSipStatus",
            "window._outboundRingPhase = true;\n        window._outMaxCh = 0;\n        window.setSipStatus",
            1,
        )

    t, n2 = re.subn(
        r"if \(!d \|\| d\.ok === false\) return;.*?window\._outDeclineTicks = 0;\n                \}",
        JS_POLL_BODY,
        t,
        count=1,
        flags=re.DOTALL,
    )
    print("JS poll replaced:", n2)

    INDEX.write_text(t, encoding="utf-8")
    print("DONE v4 — hard refresh browser (Ctrl+Shift+R)")
    print("Restore:", BACKUP)


if __name__ == "__main__":
    main()
