#!/usr/bin/env python3
"""Fix pre_answer outbound: Ringing UI + mute FS RTP + better decline detect."""
from pathlib import Path
import shutil

P = Path("/opt/skykin/app/app/agent_dashboard/index.php")
t = P.read_text(encoding="utf-8", errors="replace")
shutil.copy2(P, str(P) + ".bak-preanswer")

# 1) makeCall: show Ringing immediately, not Calling
t = t.replace(
    "        session = inv;\n        window.setSipStatus && window.setSipStatus('calling', 'Calling ' + number);\n        bindSession(inv);",
    "        session = inv;\n        window.lastDialedNumber = number;\n        window.lastCallType = 'Outbound';\n        window.startOutboundRingUI && window.startOutboundRingUI(number);\n        try {\n            const ra = document.getElementById('remoteAudio');\n            if (ra) { ra.muted = true; ra.volume = 0; ra.pause(); ra.srcObject = null; }\n        } catch (e) {}\n        bindSession(inv);",
    1,
)

# 2) onAccept: main ring path for pre_answer
t = t.replace(
    "                onAccept: function() {\n                    // pre_answer 200 — not mobile answer; mute FS ringback RTP.\n                    muteOutboundReceivers(inv);\n                    wireOutboundRecvMute(inv);\n                    enableSenders(inv);\n                    watchOutboundPeer(inv);\n                },",
    "                onAccept: function() {\n                    window.startOutboundRingUI && window.startOutboundRingUI(number);\n                    muteOutboundReceivers(inv);\n                    wireOutboundRecvMute(inv);\n                    enableSenders(inv);\n                    window.startRingback && window.startRingback();\n                    startOutboundPoll(localStorage.getItem('sip_ext') || serverExt, number);\n                    watchOutboundPeer(inv);\n                },",
    1,
)
# alternate onAccept comment variants
t = t.replace(
    "                onAccept: function() {\n                    muteOutboundReceivers(inv);\n                    wireOutboundRecvMute(inv);\n                    enableSenders(inv);\n                    watchOutboundPeer(inv);\n                },",
    "                onAccept: function() {\n                    window.startOutboundRingUI && window.startOutboundRingUI(number);\n                    muteOutboundReceivers(inv);\n                    wireOutboundRecvMute(inv);\n                    enableSenders(inv);\n                    window.startRingback && window.startRingback();\n                    startOutboundPoll(localStorage.getItem('sip_ext') || serverExt, number);\n                    watchOutboundPeer(inv);\n                },",
    1,
)

# 3) poll: channel-count fallback
OLD_POLL = """            .then(function(d) {
                if (d && d.ok === false) return;
                if (d && d.bleg) window._outHadBleg = true;
                if (window._outboundRingPhase && window._outHadBleg && d && !d.bleg) {
                    window.skykinSilenceEverything && window.skykinSilenceEverything();
                    outboundFailHard();
                    return;
                }
                var ch = (d && typeof d.channels === 'number') ? d.channels : -1;
                var alive = !!(d && (d.agent || d.bleg)) || ch > 0;"""

NEW_POLL = """            .then(function(d) {
                if (d && d.ok === false) return;
                var ch = (d && typeof d.channels === 'number') ? d.channels : -1;
                var prevCh = window._outPrevCh;
                window._outPrevCh = ch;
                if (d && d.bleg) window._outHadBleg = true;
                if (window._outboundRingPhase) {
                    if (window._outHadBleg && d && !d.bleg) {
                        window.skykinSilenceEverything && window.skykinSilenceEverything();
                        outboundFailHard();
                        return;
                    }
                    if (window._outFsSeen && ch >= 0 && prevCh >= 2 && ch < 2) {
                        window.skykinSilenceEverything && window.skykinSilenceEverything();
                        outboundFailHard();
                        return;
                    }
                    if (window._outFsSeen && ch === 0) {
                        window.skykinSilenceEverything && window.skykinSilenceEverything();
                        outboundFailHard();
                        return;
                    }
                }
                var alive = !!(d && (d.agent || d.bleg)) || ch > 0;"""

if OLD_POLL in t:
    t = t.replace(OLD_POLL, NEW_POLL, 1)
    print("poll patched")
else:
    print("poll: already patched or manual check needed")

t = t.replace(
    "    window._outHadBleg = false;\n    window._outboundPoll = setInterval(function() {",
    "    window._outHadBleg = false;\n    window._outPrevCh = -1;\n    window._outboundPoll = setInterval(function() {",
    1,
)

# 4) PHP: any external channel = bleg when agent up
PHP_SNIP = """    if ($agentLive && !$blegLive) {
        foreach ($rows as $row) {
            if (!is_array($row) || !$isLiveRow($row) || $isAgentRow($row)) {
                continue;
            }
            $name = strtolower((string)($row['name'] ?? ''));
            if (strpos($name, 'external') !== false || strpos($name, 'gateway') !== false) {
                $blegLive = true;
                $blegState = strtoupper((string)($row['callstate'] ?? ''));
                break;
            }
        }
    }
    echo json_encode(["""

if "if ($agentLive && !$blegLive)" not in t:
    t = t.replace(
        "    echo json_encode([\n        'live' => $blegLive || $agentLive",
        PHP_SNIP + "\n        'live' => $blegLive || $agentLive",
        1,
    )
    print("PHP bleg fallback added")

P.write_text(t, encoding="utf-8")
print("startOutboundRingUI at call:", "startOutboundRingUI(number)" in t.split("session = inv")[1][:800])
print("_outPrevCh:", "_outPrevCh" in t)
print("onAccept ringback:", "window.startRingback && window.startRingback()" in t)
