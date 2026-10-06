#!/usr/bin/env python3
"""Stop FS ringback after Decline: no attachAudio until mobile answers."""
import re
import shutil
from pathlib import Path

INDEX = Path("/opt/skykin/app/app/agent_dashboard/index.php")

def main() -> None:
    t = INDEX.read_text(encoding="utf-8", errors="replace")
    if "detachOutboundAudio" in t and "pre_answer 200" in t:
        print("already patched")
        return
    shutil.copy2(INDEX, str(INDEX) + ".bak-no-early-audio")

    if "function detachOutboundAudio" not in t:
        ins = """function detachOutboundAudio() {
    try {
        const el = document.getElementById('remoteAudio');
        if (el) { el.muted = true; el.pause(); el.srcObject = null; }
    } catch (e) {}
    try {
        if (session && session.sessionDescriptionHandler && session.sessionDescriptionHandler.peerConnection) {
            session.sessionDescriptionHandler.peerConnection.getReceivers().forEach(function(r) {
                try { if (r.track) { r.track.stop(); } } catch (e) {}
            });
        }
    } catch (e) {}
    if (session) { session._skykinAudioAttached = false; }
}
"""
        t = t.replace("function startOutboundPoll(ext, dest)", ins + "function startOutboundPoll(ext, dest)", 1)

    t = t.replace(
        "attachAudio(inv);\n                    watchOutboundPeer(inv);",
        "// pre_answer 200 — not mobile answer; no RTP attach\n                    watchOutboundPeer(inv);",
    )
    t = t.replace(
        "attachAudio(s);\n            watchOutboundPeer(s);\n            if (!(s instanceof Invitation)) {",
        "if (!(s instanceof Invitation)) {",
    )
    if "startOutboundRingUI(num);\n                startOutboundPoll" in t and "watchOutboundPeer(s);" not in t.split("startOutboundRingUI(num)")[1].split("autofillEscalationForm")[0]:
        t = t.replace(
            "startOutboundPoll(localStorage.getItem('sip_ext') || serverExt, num);\n            } else {",
            "startOutboundPoll(localStorage.getItem('sip_ext') || serverExt, num);\n                watchOutboundPeer(s);\n            } else {\n                attachAudio(s);\n                watchOutboundPeer(s);",
            1,
        )

    t = re.sub(
        r"onProgress: function\(\) \{\s*\n\s*window\.setSipStatus[^}]+\}\s*,\s*\n\s*enableSenders\(inv\);",
        "onProgress: function() {\n                    window.setSipStatus && window.setSipStatus('calling', 'Ringing ' + number);\n                    window.startRingback && window.startRingback();\n                    enableSenders(inv);",
        t,
        count=1,
        flags=re.DOTALL,
    )

    if "window._outboundRingPhase && window.outboundFailHard" not in t:
        t = t.replace(
            "function hangupCall() {\n    if (sipBridge.hangup) sipBridge.hangup();",
            "function hangupCall() {\n    if (window._outboundRingPhase && window.outboundFailHard) {\n        if (sipBridge.hangup) sipBridge.hangup();\n        window.outboundFailHard();\n        return;\n    }\n    if (sipBridge.hangup) sipBridge.hangup();",
            1,
        )

  # poll: attachAudio when mobile ACTIVE
    t = t.replace(
        "if (d.bleg && bst === 'ACTIVE' && !callStartTime) {",
        "if (d.bleg && bst === 'ACTIVE' && !callStartTime && session) {\n                        window.stopRingback && window.stopRingback();\n                        attachAudio(session);\n                        watchOutboundPeer(session);",
        1,
    )

    t = t.replace("outboundFailHard();\n    window._outboundFailBusy = false;",
                  "detachOutboundAudio();\n    resetOutboundFail();\n    window._outboundFailBusy = false;")
    if "detachOutboundAudio();" not in t.split("function outboundFailHard")[1].split("resetOutboundFail")[0]:
        t = t.replace(
            "try { window.stopRingtone && window.stopRingtone(); } catch (e) {}\n    const ext = localStorage.getItem('sip_ext')",
            "try { window.stopRingtone && window.stopRingtone(); } catch (e) {}\n    detachOutboundAudio();\n    const ext = localStorage.getItem('sip_ext')",
            1,
        )

    INDEX.write_text(t, encoding="utf-8")
    print("detachOutboundAudio:", "detachOutboundAudio" in t)
    print("no attachAudio onAccept:", "pre_answer 200" in t or "no RTP attach" in t)
    print("startRingback onProgress:", t.count("startRingback") >= 2)


if __name__ == "__main__":
    main()
