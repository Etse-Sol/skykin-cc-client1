#!/usr/bin/env python3
"""Patch agent dashboard index.php for outbound decline (FS channel poll). Run on ecs-cc."""
from pathlib import Path
import shutil
import sys

INDEX = Path("/opt/skykin/app/app/agent_dashboard/index.php")

PHP_BLOCK = r"""
// ── Outbound live check (FS channel gone = mobile declined / call ended) ───
if (isset($_GET['action']) && $_GET['action'] === 'outbound_live') {
    error_reporting(0);
    header('Content-Type: application/json');
    $ext = preg_replace('/\D+/', '', (string)($_GET['ext'] ?? ''));
    $dest = preg_replace('/\D+/', '', (string)($_GET['dest'] ?? ''));
    $live = false;
    if ($ext !== '') {
        $json = json_decode(skykin_fs_api('show channels as json'), true);
        foreach ((is_array($json) ? ($json['rows'] ?? []) : []) as $row) {
            if (!is_array($row)) {
                continue;
            }
            $name = strtolower((string)($row['name'] ?? ''));
            $presence = strtolower((string)($row['presence_id'] ?? ''));
            $rowDest = preg_replace('/\D+/', '', (string)($row['dest'] ?? ''));
            $cid = preg_replace('/\D+/', '', (string)($row['cid_num'] ?? $row['cid_number'] ?? ''));
            $dir = strtolower((string)($row['direction'] ?? ''));
            $isAgent = (strpos($name, 'user/' . $ext . '@') !== false)
                || (strpos($presence, $ext . '@') !== false)
                || $cid === $ext;
            if (!$isAgent) {
                continue;
            }
            $destMatch = ($dest !== '' && $rowDest !== ''
                && (str_ends_with($rowDest, substr($dest, -9)) || str_ends_with($dest, substr($rowDest, -9))));
            if ($dir === 'outbound' || $destMatch) {
                $live = true;
                break;
            }
        }
    }
    echo json_encode(['live' => $live]);
    exit;
}
"""

JS_POLL = r"""
function stopOutboundPoll() {
    if (window._outboundPoll) { clearInterval(window._outboundPoll); window._outboundPoll = null; }
    window._outboundSawLive = false;
    window._outboundIdle = 0;
}
function startOutboundPoll(ext, dest) {
    stopOutboundPoll();
    ext = ext || localStorage.getItem('sip_ext') || serverExt || '';
    window._outboundPoll = setInterval(function() {
        if (!session || session instanceof Invitation) { stopOutboundPoll(); return; }
        fetch('index.php?action=outbound_live&ext=' + encodeURIComponent(ext)
            + '&dest=' + encodeURIComponent(dest || '')
            + '&domain=' + encodeURIComponent(domain), { credentials: 'same-origin' })
            .then(function(r) { return r.json(); })
            .then(function(d) {
                if (d.live) {
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
    }, 700);
}
"""


def main() -> int:
    if not INDEX.is_file():
        print("missing:", INDEX, file=sys.stderr)
        return 1

    text = INDEX.read_text(encoding="utf-8", errors="replace")
    if "outbound_live" in text:
        print("already patched, count:", text.count("outbound_live"))
        return 0

    backup = INDEX.with_suffix(".php.bak-outbound-live")
    shutil.copy2(INDEX, backup)
    print("backup:", backup)

    markers = [
        "// ── Softphone client diagnostics (temporary)",
        "if (isset($_GET['action']) && $_GET['action'] === 'client_log'",
    ]
    inserted = False
    for marker in markers:
        if marker in text:
            text = text.replace(marker, PHP_BLOCK.strip() + "\n\n" + marker, 1)
            inserted = True
            break
    if not inserted:
        print("ERROR: could not find PHP insert point", file=sys.stderr)
        return 1

    if "function stopOutboundPoll" not in text:
        wp = "function watchOutboundPeer(s)"
        if wp not in text:
            wp = "function startCallUI(number)"
        if wp not in text:
            print("ERROR: could not find JS insert point", file=sys.stderr)
            return 1
        text = text.replace(wp, JS_POLL.strip() + "\n\n" + wp, 1)

    if "function resetOutboundFail()" in text:
        if "stopOutboundPoll();" not in text.split("function resetOutboundFail()")[1].split("}", 1)[0]:
            text = text.replace(
                "function resetOutboundFail() {\n    try { stopRingback();",
                "function resetOutboundFail() {\n    stopOutboundPoll();\n    try { stopRingback();",
                1,
            )
    else:
        print("WARN: resetOutboundFail not found — add decline JS manually if needed")

    needle = (
        "                    window.startRingback && window.startRingback();\n"
        "                    enableSenders(inv);\n"
        "                },\n"
        "                onAccept:"
    )
    repl = (
        "                    window.startRingback && window.startRingback();\n"
        "                    enableSenders(inv);\n"
        "                    startOutboundPoll(localStorage.getItem('sip_ext') || serverExt, number);\n"
        "                },\n"
        "                onAccept:"
    )
    if "startOutboundPoll" not in text and needle in text:
        text = text.replace(needle, repl, 1)
    elif "startOutboundPoll" not in text:
        print("WARN: onProgress startOutboundPoll not inserted — check makeCall manually")

    INDEX.write_text(text, encoding="utf-8")
    print("OK patched. outbound_live count:", text.count("outbound_live"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
