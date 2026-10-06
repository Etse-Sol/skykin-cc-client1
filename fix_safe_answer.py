#!/usr/bin/env python3
"""Stop call drop on answer: safe poll + remove outboundFailHard + fix bindSession."""
from pathlib import Path
import re
import shutil

P = Path("/opt/skykin/app/app/agent_dashboard/index.php")
t = P.read_text(encoding="utf-8", errors="replace")
shutil.copy2(P, str(P) + ".bak-safe-answer")

JS = r'''function stopOutboundPoll() {
    if (window._outboundPoll) { clearInterval(window._outboundPoll); window._outboundPoll = null; }
}
function startOutboundPoll(ext, dest) {
    stopOutboundPoll();
    ext = ext || localStorage.getItem('sip_ext') || serverExt || '';
    dest = dest || window.lastDialedNumber || '';
    window._outboundPollDest = dest;
    window._outAnswerTicks = 0;
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
                var answered = !!(d.bleg && (bst === 'ACTIVE' || bst === 'ANSWER' || bst === 'EXECUTE'));
                if (!answered) { window._outAnswerTicks = 0; return; }
                window._outAnswerTicks = (window._outAnswerTicks || 0) + 1;
                if (window._outAnswerTicks < 2 || callStartTime || !session) return;
                stopOutboundPoll();
                window.stopRingback && window.stopRingback();
                enableSenders(session);
                if (!session._skykinAudioAttached) attachAudio(session);
                window.startCallUI && window.startCallUI(dest || window.lastDialedNumber || '');
                window.showToast && window.showToast('Call connected');
            }).catch(function() {});
    }, 400);
}'''

t2, n = re.subn(
    r"function stopOutboundPoll\(\) \{.*?^function startOutboundPoll\(ext, dest\) \{.*?^\}",
    JS.strip(), t, count=1, flags=re.DOTALL | re.MULTILINE)
if n == 0:
    t2, n = re.subn(
        r"function startOutboundPoll\(ext, dest\) \{.*?^\}",
        JS.split("function startOutboundPoll", 1)[1].strip(), t, count=1, flags=re.DOTALL | re.MULTILINE)

# Remove outboundFailHard poll triggers (cause drop on answer)
for pat in [
    r"\s*if \(window\._outboundRingPhase && window\._outHadBleg && d && !d\.bleg\) \{.*?\n\s*\}",
    r"\s*if \(window\._outFsSeen && ch >= 0 && prevCh >= 2 && ch < 2\) \{.*?\n\s*\}",
    r"\s*if \(window\._outFsSeen && ch === 0\) \{.*?\n\s*\}",
    r"\s*outboundFailHard\(\);\s*\n\s*return;\s*\n\s*\}\s*\n\s*var ch",
]:
    t2 = re.sub(pat, "\n                var ch", t2, count=1, flags=re.DOTALL)

# bindSession: outbound Established — poll only, no startOutboundRingUI
t2 = t2.replace(
    "if (!(s instanceof Invitation)) { startOutboundRingUI(num); startOutboundPoll",
    "if (!(s instanceof Invitation)) { startOutboundPoll",
)
t2 = t2.replace(
    "if (!(s instanceof Invitation)) {\n                startOutboundRingUI(num);\n                startOutboundPoll",
    "if (!(s instanceof Invitation)) {\n                startOutboundPoll",
)

# onAccept: attach audio once at pre_answer (do not re-attach on answer)
OLD_ACCEPT = """                onAccept: function() {
                    enableSenders(inv);
                    startOutboundPoll(localStorage.getItem('sip_ext') || serverExt, number);
                }"""
NEW_ACCEPT = """                onAccept: function() {
                    enableSenders(inv);
                    if (!inv._skykinAudioAttached) attachAudio(inv);
                    startOutboundPoll(localStorage.getItem('sip_ext') || serverExt, number);
                }"""
if OLD_ACCEPT in t2:
    t2 = t2.replace(OLD_ACCEPT, NEW_ACCEPT, 1)

P.write_text(t2, encoding="utf-8")
print("poll replaced:", n)
print("outboundFailHard in poll:", "outboundFailHard" in t2.split("startOutboundPoll")[1].split("function watch")[0] if "startOutboundPoll" in t2 else "n/a")
print("_outAnswerTicks:", "_outAnswerTicks" in t2)
print("onAccept attachAudio:", "inv._skykinAudioAttached" in t2)
