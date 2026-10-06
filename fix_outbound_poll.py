#!/usr/bin/env python3
"""Fix outbound decline poll on ecs-cc (wire startOutboundPoll + B-leg detect)."""
import re
import shutil
from pathlib import Path

INDEX = Path("/opt/skykin/app/app/agent_dashboard/index.php")

PHP = r"""// Outbound live check (B-leg gone = mobile declined; agent may stay pre_answer)
if (isset($_GET['action']) && $_GET['action'] === 'outbound_live') {
    error_reporting(0);
    header('Content-Type: application/json');
    $ext = preg_replace('/\D+/', '', (string)($_GET['ext'] ?? ''));
    $dest = preg_replace('/\D+/', '', (string)($_GET['dest'] ?? ''));
    $destTail = strlen($dest) >= 9 ? substr($dest, -9) : $dest;
    $blegLive = false;
    $agentLive = false;
    if ($ext !== '' || $destTail !== '') {
        $json = json_decode(skykin_fs_api('show channels as json'), true);
        foreach ((is_array($json) ? ($json['rows'] ?? []) : []) as $row) {
            if (!is_array($row)) {
                continue;
            }
            $name = strtolower((string)($row['name'] ?? ''));
            $presence = strtolower((string)($row['presence_id'] ?? ''));
            $rowDest = preg_replace('/\D+/', '', (string)($row['dest'] ?? ''));
            $cid = preg_replace('/\D+/', '', (string)($row['cid_num'] ?? $row['cid_number'] ?? ''));
            $state = strtoupper((string)($row['callstate'] ?? ''));
            if ($ext !== ''
                && ((strpos($name, 'user/' . $ext . '@') !== false)
                    || (strpos($presence, $ext . '@') !== false)
                    || $cid === $ext)
                && !in_array($state, ['HANGUP', 'DOWN'], true)) {
                $agentLive = true;
            }
            if ($destTail !== '' && $rowDest !== ''
                && (str_ends_with($rowDest, $destTail) || str_ends_with($destTail, substr($rowDest, -9)))) {
                if (!in_array($state, ['HANGUP', 'DOWN'], true)) {
                    $blegLive = true;
                }
            }
        }
    }
    echo json_encode(['live' => $blegLive, 'agent' => $agentLive, 'bleg' => $blegLive]);
    exit;
}"""

JS_POLL = r"""function stopOutboundPoll() {
    if (window._outboundPoll) { clearInterval(window._outboundPoll); window._outboundPoll = null; }
    window._outboundSawLive = false;
    window._outboundIdle = 0;
}
function startOutboundPoll(ext, dest) {
    stopOutboundPoll();
    ext = ext || localStorage.getItem('sip_ext') || serverExt || '';
    window._outboundPollDest = dest || '';
    window._outboundPoll = setInterval(function() {
        if (!session || session instanceof Invitation) { stopOutboundPoll(); return; }
        fetch('index.php?action=outbound_live&ext=' + encodeURIComponent(ext)
            + '&dest=' + encodeURIComponent(window._outboundPollDest || dest || '')
            + '&domain=' + encodeURIComponent(domain), { credentials: 'same-origin' })
            .then(function(r) { return r.json(); })
            .then(function(d) {
                var live = !!(d && (d.live || d.bleg));
                if (live) {
                    window._outboundSawLive = true;
                    window._outboundIdle = 0;
                    return;
                }
                if (!window._outboundSawLive) return;
                window._outboundIdle = (window._outboundIdle || 0) + 1;
                if (window._outboundIdle >= 2) {
                    resetOutboundFail();
                    stopOutboundPoll();
                    try { sipBridge.hangup && sipBridge.hangup(); } catch (e) {}
                }
            }).catch(function() {});
    }, 500);
}"""


def main() -> None:
    text = INDEX.read_text(encoding="utf-8", errors="replace")
    shutil.copy2(INDEX, str(INDEX) + ".bak-fix-poll")

    text = re.sub(
        r"//[^\n]*Outbound live check.*?\nif \(isset\(\$_GET\['action'\]\) && \$_GET\['action'\] === 'outbound_live'\) \{.*?\n    exit;\n\}",
        PHP,
        text,
        count=1,
        flags=re.DOTALL,
    )

    text = re.sub(
        r"function stopOutboundPoll\(\) \{.*?^\}",
        JS_POLL.strip(),
        text,
        count=1,
        flags=re.DOTALL | re.MULTILINE,
    )

    if "startOutboundPoll(localStorage" not in text:
        text = re.sub(
            r"(bindSession\(inv\);\s*\n)(\s*return inv\.invite)",
            r"\1        startOutboundPoll(localStorage.getItem('sip_ext') || serverExt, number);\n\2",
            text,
            count=1,
        )

    if text.count("startOutboundPoll(localStorage") < 2:
        text = re.sub(
            r"(window\.startRingback && window\.startRingback\(\);\s*\n\s*enableSenders\(inv\);)",
            r"\1\n                    startOutboundPoll(localStorage.getItem('sip_ext') || serverExt, number);",
            text,
            count=1,
        )

    INDEX.write_text(text, encoding="utf-8")
    print("startOutboundPoll calls:", text.count("startOutboundPoll(localStorage"))
    print("outbound_live count:", text.count("outbound_live"))
    print("bleg in PHP:", "blegLive" in text)


if __name__ == "__main__":
    main()
