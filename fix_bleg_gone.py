#!/usr/bin/env python3
"""B-leg gone detection for outbound decline (pre_answer keeps agent leg up)."""
from pathlib import Path
import shutil

P = Path("/opt/skykin/app/app/agent_dashboard/index.php")
t = P.read_text(encoding="utf-8", errors="replace")
shutil.copy2(P, str(P) + ".bak-bleg-gone")

MUTE_FN = """function muteOutboundReceivers(s) {
    const pc = s && s.sessionDescriptionHandler && s.sessionDescriptionHandler.peerConnection;
    if (!pc) return;
    pc.getReceivers().forEach(function(r) {
        try { if (r.track) { r.track.enabled = false; r.track.stop(); } } catch (e) {}
    });
}

"""

if "function muteOutboundReceivers" not in t:
    t = t.replace("function enableSenders(s) {", MUTE_FN + "function enableSenders(s) {", 1)
    print("added muteOutboundReceivers")
else:
    print("muteOutboundReceivers exists")

t = t.replace(
    "    window._outFsGone = 0;\n    window._outboundPoll = setInterval(function() {",
    "    window._outFsGone = 0;\n    window._outHadBleg = false;\n    window._outboundPoll = setInterval(function() {",
    1,
)

OLD_THEN = """            .then(function(d) {
                if (d && d.ok === false) return;
                var ch = (d && typeof d.channels === 'number') ? d.channels : -1;
                var alive = !!(d && (d.agent || d.bleg)) || ch > 0;"""

NEW_THEN = """            .then(function(d) {
                if (d && d.ok === false) return;
                if (d && d.bleg) window._outHadBleg = true;
                if (window._outboundRingPhase && window._outHadBleg && d && !d.bleg) {
                    outboundFailHard();
                    return;
                }
                var ch = (d && typeof d.channels === 'number') ? d.channels : -1;
                var alive = !!(d && (d.agent || d.bleg)) || ch > 0;"""

if OLD_THEN in t:
    t = t.replace(OLD_THEN, NEW_THEN, 1)
    print("patched poll bleg-gone check")
else:
    print("WARN: poll block not found — may already be patched")

if "if (session) muteOutboundReceivers(session);" not in t:
    t = t.replace(
        "function detachOutboundAudio() {\n    try {\n        const el = document.getElementById('remoteAudio');\n        if (el) { el.muted = true; el.pause(); el.srcObject = null; }\n    } catch (e) {}\n    try {",
        "function detachOutboundAudio() {\n    try {\n        const el = document.getElementById('remoteAudio');\n        if (el) { el.muted = true; el.pause(); el.srcObject = null; }\n    } catch (e) {}\n    try {\n        if (session) muteOutboundReceivers(session);\n    } catch (e) {}\n    try {",
        1,
    )
    print("patched detachOutboundAudio")

t = t.replace(
    "onProgress: function() {\n                    window.setSipStatus && window.setSipStatus('calling', 'Ringing ' + number);\n                    window.startRingback && window.startRingback();\n                    enableSenders(inv);",
    "onProgress: function() {\n                    window.startOutboundRingUI && window.startOutboundRingUI(number);\n                    window.startRingback && window.startRingback();\n                    muteOutboundReceivers(inv);\n                    enableSenders(inv);",
    1,
)

t = t.replace(
    "onAccept: function() {\n                    // pre_answer 200 — not mobile answer; keep local ringback only, no RTP attach.\n                    enableSenders(inv);",
    "onAccept: function() {\n                    // pre_answer 200 — not mobile answer; mute FS ringback RTP.\n                    muteOutboundReceivers(inv);\n                    enableSenders(inv);",
    1,
)

t = t.replace(
    "                startOutboundPoll(localStorage.getItem('sip_ext') || serverExt, num);\n                watchOutboundPeer(s);",
    "                startOutboundPoll(localStorage.getItem('sip_ext') || serverExt, num);\n                muteOutboundReceivers(s);\n                watchOutboundPeer(s);",
    1,
)

P.write_text(t, encoding="utf-8")
print("_outHadBleg:", "_outHadBleg" in t)
print("bleg-gone check:", "_outHadBleg && d && !d.bleg" in t)
print("muteOutboundReceivers:", "function muteOutboundReceivers" in t)
