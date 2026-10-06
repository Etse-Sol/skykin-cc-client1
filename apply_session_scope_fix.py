#!/usr/bin/env python3
"""Fix session is not defined — move outbound poll inside SIP IIFE."""
import re
import shutil
from pathlib import Path

INDEX = Path("/opt/skykin/app/app/agent_dashboard/index.php")

SIP_BLOCK = r"""
// Outbound decline helpers — must live in this closure (session/Invitation are here).
function stopOutboundPoll() {
    if (window._outboundPoll) { clearInterval(window._outboundPoll); window._outboundPoll = null; }
    window._outboundSawLive = false;
    window._outboundSawBleg = false;
    window._outboundSawAgent = false;
    window._outboundIdle = 0;
}
function startOutboundRingUI(number) {
    window._outboundRingPhase = true;
    window.stopRingtone && window.stopRingtone();
    window.stopRingback && window.stopRingback();
    window.setSipStatus && window.setSipStatus('calling', 'Ringing ' + number);
    document.getElementById('btnCall').style.display = 'none';
    document.getElementById('btnHangup').style.display = 'block';
    document.getElementById('phonePopup').classList.add('call-active');
    document.getElementById('btnHold').style.display = 'none';
    document.getElementById('btnMute').style.display = 'none';
    document.getElementById('callTimer').style.display = 'none';
}
function resetOutboundFail() {
    stopOutboundPoll();
    window._outboundRingPhase = false;
    window._outboundSawBleg = false;
    window._outboundSawAgent = false;
    try { window.stopRingback && window.stopRingback(); } catch (e) {}
    try { window.stopRingtone && window.stopRingtone(); } catch (e) {}
    try {
        const el = document.getElementById('remoteAudio');
        if (el) { el.pause(); el.srcObject = null; el.muted = false; }
    } catch (e) {}
    try {
        document.getElementById('btnHangup').style.display = 'none';
        document.getElementById('btnCall').style.display = 'block';
        document.getElementById('btnHold').style.display = 'none';
        document.getElementById('btnMute').style.display = 'none';
        document.getElementById('btnKeypad').style.display = 'none';
        document.getElementById('btnKeypad').classList.remove('active');
        document.getElementById('phonePopup').classList.remove('call-active');
        document.getElementById('callTimer').style.display = 'none';
        document.getElementById('callTimer').textContent = '00:00';
        clearInterval(callTimerInterval);
        callStartTime = null;
        isRecording = false;
        onHold = false;
        isMuted = false;
    } catch (e) {}
    const ext = localStorage.getItem('sip_ext') || serverExt || '';
    window.setSipStatus && window.setSipStatus('registered', 'Registered (' + ext + ')');
}
function outboundFailHard() {
    if (window._outboundFailBusy) return;
    window._outboundFailBusy = true;
    stopOutboundPoll();
    window._outboundRingPhase = false;
    try { window.stopRingback && window.stopRingback(); } catch (e) {}
    try { window.stopRingtone && window.stopRingtone(); } catch (e) {}
    try {
        const el = document.getElementById('remoteAudio');
        if (el) { el.muted = true; el.pause(); el.srcObject = null; }
    } catch (e) {}
    const ext = localStorage.getItem('sip_ext') || serverExt || '';
    fetch('index.php?action=outbound_stop&ext=' + encodeURIComponent(ext)
        + '&domain=' + encodeURIComponent(domain), { credentials: 'same-origin' }).catch(function() {});
    try {
        if (session && !(session instanceof Invitation)
            && session.state !== SessionState.Terminated
            && session.state !== SessionState.Terminating) {
            const pc = session.sessionDescriptionHandler && session.sessionDescriptionHandler.peerConnection;
            if (pc) {
                pc.getReceivers().forEach(function(r) { try { r.track && r.track.stop(); } catch (e) {} });
                try { pc.close(); } catch (e) {}
            }
            try { session.bye(); } catch (e) {}
            try { session.dispose && session.dispose(); } catch (e) {}
            session = null;
        }
    } catch (e) {}
    resetOutboundFail();
    window._outboundFailBusy = false;
}
window.resetOutboundFail = resetOutboundFail;
window.outboundFailHard = outboundFailHard;
function startOutboundPoll(ext, dest) {
    stopOutboundPoll();
    ext = ext || localStorage.getItem('sip_ext') || serverExt || '';
    window._outboundPollDest = dest || window.lastDialedNumber || '';
    window._outboundPoll = setInterval(function() {
        if (!session || session instanceof Invitation) { stopOutboundPoll(); return; }
        fetch('index.php?action=outbound_live&ext=' + encodeURIComponent(ext)
            + '&dest=' + encodeURIComponent(window._outboundPollDest || dest || '')
            + '&domain=' + encodeURIComponent(domain), { credentials: 'same-origin' })
            .then(function(r) { return r.json(); })
            .then(function(d) {
                if (d && d.ok === false) return;
                var bleg = !!(d && d.bleg);
                var bst = ((d && d.bleg_state) || '').toUpperCase();
                if (d && d.agent) {
                    window._outboundSawAgent = true;
                    window._outboundIdle = 0;
                }
                if (bleg) {
                    window._outboundSawBleg = true;
                    if (window._outboundRingPhase && bst === 'ACTIVE') {
                        window._outboundRingPhase = false;
                        window.startCallUI && window.startCallUI(window._outboundPollDest || window.lastDialedNumber || '');
                    }
                    return;
                }
                if (window._outboundSawAgent && d && !d.agent) {
                    outboundFailHard();
                    return;
                }
                if (window._outboundSawBleg && d && !d.bleg) {
                    outboundFailHard();
                }
            }).catch(function() {});
    }, 400);
}
function watchOutboundPeer(s) {
    if (!s || s instanceof Invitation) return;
    const pc = s.sessionDescriptionHandler && s.sessionDescriptionHandler.peerConnection;
    if (!pc || s._skykinPeerWatched) return;
    s._skykinPeerWatched = true;
    const fail = function() {
        if (session !== s) return;
        outboundFailHard();
    };
    pc.onconnectionstatechange = function() {
        if (pc.connectionState === 'disconnected' || pc.connectionState === 'failed'
            || pc.connectionState === 'closed') {
            fail();
        }
    };
    pc.getReceivers().forEach(function(r) {
        if (r.track) {
            r.track.onended = fail;
        }
    });
}
"""


def main() -> None:
    text = INDEX.read_text(encoding="utf-8", errors="replace")
    marker = "// Outbound decline helpers — must live in this closure"
    if marker in text:
        print("already fixed (inside IIFE)")
        return

    shutil.copy2(INDEX, str(INDEX) + ".bak-session-scope")

    # Remove wrongly-placed global outbound block (before startCallUI in outer script).
    text = re.sub(
        r"\n// Outbound failed/declined:.*?\nfunction watchOutboundPeer\(s\) \{.*?\n\}\n\nfunction startCallUI",
        "\nfunction startCallUI",
        text,
        count=1,
        flags=re.DOTALL,
    )
    # Also remove if comment differs.
    text = re.sub(
        r"\nfunction outboundFailHard\(\) \{.*?window\.outboundFailHard = outboundFailHard;\n\nfunction resetOutboundFail\(\) \{.*?\nwindow\.resetOutboundFail = resetOutboundFail;\n\nfunction stopOutboundPoll\(\) \{.*?\nfunction startOutboundPoll\(ext, dest\) \{.*?\n\}\n\nfunction watchOutboundPeer\(s\) \{.*?\n\}\n\nfunction startCallUI",
        "\nfunction startCallUI",
        text,
        count=1,
        flags=re.DOTALL,
    )

    anchor = "let ua = null, reg = null, session = null;"
    if anchor not in text:
        print("ERROR: SIP anchor not found")
        return
    text = text.replace(anchor, anchor + SIP_BLOCK, 1)

    INDEX.write_text(text, encoding="utf-8")
    print("OK — inside IIFE:", marker in text)
    print("global outboundFailHard before sipjs:", text.find("function outboundFailHard")
          < text.find("sipjs.bundle.js"))


if __name__ == "__main__":
    main()
