#!/usr/bin/env python3
"""Replace startOutboundPoll on ecs-cc with decline-safe version."""
import re
import shutil
from pathlib import Path

INDEX = Path("/opt/skykin/app/app/agent_dashboard/index.php")

POLL = r"""function startOutboundPoll(ext, dest) {
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
                        startCallUI(window._outboundPollDest || window.lastDialedNumber || '');
                    }
                    return;
                }
                if (window._outboundRingPhase && window._outboundSawAgent && d && !d.agent) {
                    outboundFailHard();
                    return;
                }
                if (window._outboundRingPhase && window._outboundSawBleg && d && !d.bleg) {
                    outboundFailHard();
                    return;
                }
            }).catch(function() {});
    }, 400);
}"""

STOP = r"""function stopOutboundPoll() {
    if (window._outboundPoll) { clearInterval(window._outboundPoll); window._outboundPoll = null; }
    window._outboundSawLive = false;
    window._outboundSawBleg = false;
    window._outboundSawAgent = false;
    window._outboundIdle = 0;
}"""


def main() -> None:
    text = INDEX.read_text(encoding="utf-8", errors="replace")
    if "!d.agent" in text and "_outboundSawAgent" in text:
        print("already has decline fix")
        return

    shutil.copy2(INDEX, str(INDEX) + ".bak-poll-v2")
    if "function startOutboundPoll" in text:
        text = re.sub(
            r"function startOutboundPoll\(ext, dest\) \{.*?\n\}\n\nfunction watchOutboundPeer",
            POLL + "\n\nfunction watchOutboundPeer",
            text,
            count=1,
            flags=re.DOTALL,
        )
    else:
        print("ERROR: startOutboundPoll missing")
        return

    if "function stopOutboundPoll" in text:
        text = re.sub(
            r"function stopOutboundPoll\(\) \{.*?\n\}",
            STOP.strip(),
            text,
            count=1,
            flags=re.DOTALL,
        )

    if "bindSession(inv);\n        startOutboundPoll" not in text.replace("\r\n", "\n"):
        text = text.replace(
            "bindSession(inv);\n        return inv.invite",
            "bindSession(inv);\n        startOutboundPoll(localStorage.getItem('sip_ext') || serverExt, number);\n        return inv.invite",
            1,
        )

    INDEX.write_text(text, encoding="utf-8")
    print("!d.agent:", text.count("!d.agent"))
    print("_outboundSawAgent:", text.count("_outboundSawAgent"))
    print("startOutboundPoll calls:", text.count("startOutboundPoll(localStorage"))


if __name__ == "__main__":
    main()
