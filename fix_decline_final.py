#!/usr/bin/env python3
"""Fix outbound decline on ecs-cc: correct outbound_live PHP + poll JS."""
import re
import shutil
from pathlib import Path

INDEX = Path("/opt/skykin/app/app/agent_dashboard/index.php")

PHP_BLOCK = r"""// ── Outbound live check (B-leg state; agent may stay up after pre_answer) ───
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
        if ($ext === '') {
            return false;
        }
        $name = strtolower((string)($row['name'] ?? ''));
        $presence = strtolower((string)($row['presence_id'] ?? ''));
        $cid = preg_replace('/\D+/', '', (string)($row['cid_num'] ?? $row['cid_number'] ?? ''));
        $state = strtoupper((string)($row['callstate'] ?? ''));
        if (in_array($state, ['HANGUP', 'DOWN'], true)) {
            return false;
        }
        return (bool)preg_match('#(^|[/@])' . preg_quote($ext, '#') . '(@|$|-)#', $name)
            || strpos($presence, $ext . '@') !== false
            || $cid === $ext;
    };
    $isLiveRow = static function (array $row): bool {
        $state = strtoupper((string)($row['callstate'] ?? ''));
        return !in_array($state, ['HANGUP', 'DOWN'], true);
    };
    foreach ($rows as $row) {
        if (!is_array($row)) {
            continue;
        }
        if ($isAgentRow($row)) {
            $agentLive = true;
        }
        if ($destTail !== '' && $isLiveRow($row) && !$isAgentRow($row)) {
            $name = strtolower((string)($row['name'] ?? ''));
            $blob = preg_replace('/\D+/', '', $name . ($row['dest'] ?? '') . ($row['callee_num'] ?? ''));
            $dir = strtolower((string)($row['direction'] ?? ''));
            if ((strpos($name, 'sofia/external/') !== false || $dir === 'outbound')
                && strlen($destTail) >= 9 && strpos($blob, $destTail) !== false) {
                $blegLive = true;
                $blegState = strtoupper((string)($row['callstate'] ?? ''));
            }
        }
    }
    echo json_encode([
        'live' => $blegLive || $agentLive || count($rows) > 0,
        'agent' => $agentLive,
        'bleg' => $blegLive,
        'bleg_state' => $blegState,
        'channels' => count($rows),
    ]);
    exit;
}"""

JS_POLL = r"""function startOutboundPoll(ext, dest) {
    stopOutboundPoll();
    ext = ext || localStorage.getItem('sip_ext') || serverExt || '';
    window._outboundPollDest = dest || window.lastDialedNumber || '';
    window._outFsSeen = false;
    window._outFsGone = 0;
    window._outboundPoll = setInterval(function() {
        if (!session || session instanceof Invitation) { stopOutboundPoll(); return; }
        if (session.state === SessionState.Terminated || session.state === SessionState.Terminating) {
            resetOutboundFail();
            stopOutboundPoll();
            return;
        }
        fetch('index.php?action=outbound_live&ext=' + encodeURIComponent(ext)
            + '&dest=' + encodeURIComponent(window._outboundPollDest || dest || '')
            + '&domain=' + encodeURIComponent(domain), { credentials: 'same-origin' })
            .then(function(r) { return r.json(); })
            .then(function(d) {
                if (d && d.ok === false) return;
                var ch = (d && typeof d.channels === 'number') ? d.channels : -1;
                var alive = !!(d && (d.agent || d.bleg)) || ch > 0;
                if (alive) {
                    window._outFsSeen = true;
                    window._outFsGone = 0;
                    return;
                }
                if (window._outFsSeen || window._outboundRingPhase) {
                    window._outFsGone = (window._outFsGone || 0) + 1;
                    if (window._outFsGone >= 1) {
                        outboundFailHard();
                    }
                }
            }).catch(function() {});
    }, 300);
}"""

PHP_PATTERN = (
    r"//[^\n]*Outbound live[^\n]*\n"
    r"if \(isset\(\$_GET\['action'\]\) && \$_GET\['action'\] === 'outbound_live'\) \{.*?\n    exit;\n\}"
)
JS_PATTERN = r"function startOutboundPoll\(ext, dest\) \{.*?^\}"


def main() -> None:
    text = INDEX.read_text(encoding="utf-8", errors="replace")
    shutil.copy2(INDEX, str(INDEX) + ".bak-decline-final")

    text, n1 = re.subn(PHP_PATTERN, lambda _m: PHP_BLOCK, text, count=1, flags=re.DOTALL)
    print("PHP outbound_live replaced:", n1 == 1)

    text, n2 = re.subn(
        JS_PATTERN,
        lambda _m: JS_POLL.strip(),
        text,
        count=1,
        flags=re.DOTALL | re.MULTILINE,
    )
    print("JS startOutboundPoll replaced:", n2 == 1)

    INDEX.write_text(text, encoding="utf-8")
    print("preg_match agent:", "preg_match('#(^|[/@])'" in text)
    print("_outFsSeen:", "_outFsSeen" in text)
    print("outboundFailHard in poll:", "outboundFailHard()" in text)


if __name__ == "__main__":
    main()
