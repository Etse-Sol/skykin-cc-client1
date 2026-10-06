#!/usr/bin/env python3
"""Patch startOutboundPoll on ecs-cc for mobile-answer -> In Call UI."""
from pathlib import Path
import re
import shutil

P = Path("/opt/skykin/app/app/agent_dashboard/index.php")
t = P.read_text(encoding="utf-8", errors="replace")
shutil.copy2(P, str(P) + ".bak-answer-poll")

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
            stopOutboundPoll();
            return;
        }
        fetch('index.php?action=outbound_live&ext=' + encodeURIComponent(ext)
            + '&dest=' + encodeURIComponent(dest)
            + '&domain=' + encodeURIComponent(domain), { credentials: 'same-origin' })
            .then(function(r) { return r.json(); })
            .then(function(d) {
                if (!d || d.ok === false) return;
                var bst = String(d.bleg_state || '').toUpperCase();
                var ringing = (bst === 'RINGING' || bst === 'EARLY' || bst === 'DIALING' || bst === 'DOWN');
                var answered = !!(d.bleg && !ringing && bst !== '' && bst !== 'HANGUP');
                if (!answered && d.bleg) {
                    answered = (bst === 'ACTIVE' || bst === 'ANSWER' || bst === 'EXECUTE');
                }
                if (answered && !callStartTime && session) {
                    stopOutboundPoll();
                    window.stopRingback && window.stopRingback();
                    attachAudio(session);
                    window.startCallUI && window.startCallUI(dest || window.lastDialedNumber || '');
                    window.showToast && window.showToast('Call connected');
                }
            }).catch(function() {});
    }, 400);
}"""

t2, n = re.subn(
    r"function stopOutboundPoll\(\) \{.*?^function startOutboundPoll\(ext, dest\) \{.*?^\}",
    JS_POLL.strip(),
    t,
    count=1,
    flags=re.DOTALL | re.MULTILINE,
)

if n == 0:
    t2, n = re.subn(
        r"function startOutboundPoll\(ext, dest\) \{.*?^\}",
        JS_POLL.split("function startOutboundPoll", 1)[1].strip(),
        t,
        count=1,
        flags=re.DOTALL | re.MULTILINE,
    )
    if n and "function stopOutboundPoll" not in t2:
        t2 = t2.replace(
            "function startOutboundPoll(ext, dest)",
            JS_POLL.strip().split("function startOutboundPoll", 1)[0] + "function startOutboundPoll(ext, dest)",
            1,
        )

if n == 0:
    print("ERROR: could not find startOutboundPoll to replace")
    raise SystemExit(1)

t = t2

# PHP: ensure bleg_state comes from external leg (not stuck RINGING)
PHP_SNIP = """        if ($isExternal && ($numMatch || $destTail === '')) {
            $blegLive = true;
            $blegState = strtoupper((string)($row['callstate'] ?? ''));
        }"""

if "strpos($name, 'external')" in t and "bleg_state" in t:
    pass  # already has external detection
else:
    print("WARN: check outbound_live PHP manually")

P.write_text(t, encoding="utf-8")
print("startOutboundPoll replaced:", n)
print("ACTIVE answer check:", "bst === 'ACTIVE'" in t)
print("startCallUI on answer:", "window.startCallUI" in t.split("startOutboundPoll")[1][:2500])
