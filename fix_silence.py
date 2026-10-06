#!/usr/bin/env python3
"""Nuclear audio silence on outbound decline."""
from pathlib import Path
import shutil

P = Path("/opt/skykin/app/app/agent_dashboard/index.php")
t = P.read_text(encoding="utf-8", errors="replace")
shutil.copy2(P, str(P) + ".bak-silence")

SILENCE = """
function skykinSilenceEverything() {
    try { skykinForceStopRing(); } catch (e) {}
    try { stopRingtone(); } catch (e) {}
    try {
        if (_rbInterval) { clearInterval(_rbInterval); _rbInterval = null; }
        if (_rbCtx) { try { _rbCtx.close(); } catch (e) {} _rbCtx = null; }
        window._rbInterval = null;
        window._rbCtx = null;
    } catch (e) {}
    try {
        const el = document.getElementById('remoteAudio');
        if (el) {
            el.muted = true;
            el.volume = 0;
            el.pause();
            const so = el.srcObject;
            if (so && so.getTracks) so.getTracks().forEach(function(t) { try { t.stop(); } catch (e) {} });
            el.srcObject = null;
        }
    } catch (e) {}
}
window.skykinSilenceEverything = skykinSilenceEverything;
"""

WIRE = """
function wireOutboundRecvMute(s) {
    const pc = s && s.sessionDescriptionHandler && s.sessionDescriptionHandler.peerConnection;
    if (!pc || pc._skykinRecvMuted) return;
    pc._skykinRecvMuted = true;
    pc.ontrack = function(ev) {
        try { if (ev.track) { ev.track.enabled = false; ev.track.stop(); } } catch (e) {}
    };
    muteOutboundReceivers(s);
}
"""

if "function skykinSilenceEverything" not in t:
    t = t.replace("window.skykinForceStopRing = skykinForceStopRing;", 
        "window.skykinForceStopRing = skykinForceStopRing;" + SILENCE, 1)
    print("added skykinSilenceEverything")

if "function wireOutboundRecvMute" not in t:
    t = t.replace("function enableSenders(s) {", WIRE + "\nfunction enableSenders(s) {", 1)
    print("added wireOutboundRecvMute")

t = t.replace(
    "if (window._outboundRingPhase && window._outHadBleg && d && !d.bleg) {\n                    outboundFailHard();",
    "if (window._outboundRingPhase && window._outHadBleg && d && !d.bleg) {\n                    window.skykinSilenceEverything && window.skykinSilenceEverything();\n                    outboundFailHard();",
    1)

# onProgress / onAccept / Established: wire mute
for old, new in [
    ("muteOutboundReceivers(inv);\n                    enableSenders(inv);\n                    startOutboundPoll",
     "muteOutboundReceivers(inv);\n                    wireOutboundRecvMute(inv);\n                    enableSenders(inv);\n                    startOutboundPoll"),
    ("muteOutboundReceivers(inv);\n                    enableSenders(inv);\n                    watchOutboundPeer(inv);",
     "muteOutboundReceivers(inv);\n                    wireOutboundRecvMute(inv);\n                    enableSenders(inv);\n                    watchOutboundPeer(inv);"),
    ("muteOutboundReceivers(s);\n                watchOutboundPeer(s);",
     "muteOutboundReceivers(s);\n                wireOutboundRecvMute(s);\n                watchOutboundPeer(s);"),
]:
    if old in t and new not in t:
        t = t.replace(old, new, 1)

# resetOutboundFail: use silence helper
t = t.replace(
    "try { window.skykinForceStopRing && window.skykinForceStopRing(); } catch (e) {}\n    try { window.stopRingtone && window.stopRingtone(); } catch (e) {}\n    detachOutboundAudio();",
    "window._outHadBleg = false;\n    window.skykinSilenceEverything && window.skykinSilenceEverything();",
    1)

P.write_text(t, encoding="utf-8")
print("skykinSilenceEverything:", "function skykinSilenceEverything" in t)
print("wireOutboundRecvMute:", "function wireOutboundRecvMute" in t)
