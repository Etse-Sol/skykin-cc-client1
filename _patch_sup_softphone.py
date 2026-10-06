#!/usr/bin/env python3
"""Patch supervisor.php softphone outbound to match agent."""
from pathlib import Path

NEW = r'''
// ── Match agent outbound softphone (SKYKIN_SUP_OUT_v1) ───────────────────────
let _rbCtx = null, _rbInterval = null, _rbMode = '';
function _ensureToneCtx() {
    if (_rbCtx && _rbCtx.state !== 'closed') {
        if (_rbCtx.state === 'suspended') { try { _rbCtx.resume(); } catch (e) {} }
        return _rbCtx;
    }
    try {
        _rbCtx = new (window.AudioContext || window.webkitAudioContext)();
        if (_rbCtx.state === 'suspended') { _rbCtx.resume(); }
        return _rbCtx;
    } catch (e) { return null; }
}
function _playDualTone(freqs, durationSec, gainVal) {
    const ctx = _ensureToneCtx();
    if (!ctx) return;
    const t0 = ctx.currentTime;
    const g = ctx.createGain();
    g.connect(ctx.destination);
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(gainVal || 0.18, t0 + 0.02);
    g.gain.setValueAtTime(gainVal || 0.18, t0 + Math.max(0.05, durationSec - 0.04));
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + durationSec);
    (freqs || [425]).forEach(function(hz) {
        try {
            const o = ctx.createOscillator();
            o.type = 'sine'; o.frequency.value = hz; o.connect(g);
            o.start(t0); o.stop(t0 + durationSec + 0.02);
        } catch (e) {}
    });
}
function stopRingback() {
    if (_rbInterval) { clearInterval(_rbInterval); _rbInterval = null; }
    _rbMode = '';
}
function stopAllCallTones() {
    stopRingback();
    if (_rbCtx) { try { _rbCtx.close(); } catch (e) {} _rbCtx = null; }
}
function startRingback() {
    if (_rbMode === 'ring' && _rbInterval) return;
    stopRingback();
    const ctx = _ensureToneCtx();
    if (!ctx) return;
    try { ctx.resume(); } catch (e) {}
    _rbMode = 'ring';
    function pulse() {
        if (_rbMode !== 'ring') return;
        try { if (ctx.state === 'suspended') ctx.resume(); } catch (e) {}
        _playDualTone([440, 480], 2.0, 0.32);
    }
    pulse();
    _rbInterval = setInterval(pulse, 6000);
}
function enterOutboundRinging(dest) {
    dest = dest || window._outboundPollDest || window.lastDialedNumber || '';
    if (!window._outboundRingPhase || callStartTime || window._outboundFailDone) return;
    if (!window._outSawActualRing) {
        window._outSawActualRing = true;
        window._outRingStartedAt = Date.now();
    }
    window.setSipStatus && window.setSipStatus('calling', 'Ringing: ' + dest);
    startRingback();
}
function startBusyTone() {
    stopRingback();
    if (!_ensureToneCtx()) return;
    _rbMode = 'busy';
    function pulse() {
        if (_rbMode !== 'busy') return;
        _playDualTone([480, 620], 0.45, 0.2);
    }
    pulse();
    _rbInterval = setInterval(pulse, 1000);
    setTimeout(function() { if (_rbMode === 'busy') stopAllCallTones(); }, 3500);
}
function startCongestionTone() {
    stopRingback();
    if (!_ensureToneCtx()) return;
    _rbMode = 'cong';
    function pulse() {
        if (_rbMode !== 'cong') return;
        _playDualTone([480, 620], 0.25, 0.18);
    }
    pulse();
    _rbInterval = setInterval(pulse, 500);
    setTimeout(function() { if (_rbMode === 'cong') stopAllCallTones(); }, 3000);
}
function playOutboundFailTone(label) {
    var L = String(label || '').toLowerCase();
    if (L.indexOf('busy') >= 0 || L.indexOf('declined') >= 0) startBusyTone();
    else if (L.indexOf('cancel') >= 0) stopAllCallTones();
    else startCongestionTone();
}
window.startRingback = startRingback;
window.stopRingback = stopRingback;
window.stopAllCallTones = stopAllCallTones;
window.playOutboundFailTone = playOutboundFailTone;
window.enterOutboundRinging = enterOutboundRinging;

function skykinGetSupExt() {
    return localStorage.getItem('sup_sip_ext') || localStorage.getItem('sip_ext')
        || (typeof serverExt !== 'undefined' ? serverExt : '') || '';
}
function skykinOutboundFailLabel(cause, sipCode, opts) {
    var c = String(cause || '').toUpperCase().replace(/[^A-Z0-9_]/g, '');
    var code = parseInt(sipCode, 10) || 0;
    opts = opts || {};
    var sawRing = !!(opts.sawRing || window._outSawActualRing);
    var ringMs = parseInt(window._outRingStartedAt ? (Date.now() - window._outRingStartedAt) : 0, 10) || 0;
    if (code === 486 || c === 'USER_BUSY') return 'Busy';
    if (code === 603 || c === 'CALL_REJECTED') return 'Declined';
    if (code === 487 || c === 'ORIGINATOR_CANCEL') return 'Call cancelled';
    if (sawRing && ringMs >= 2500) return 'No answer';
    if (!sawRing && (c === 'NO_USER_RESPONSE' || c === 'NO_ANSWER' || c === 'SUBSCRIBER_ABSENT'
        || c === 'USER_NOT_REGISTERED' || c === 'NORMAL_TEMPORARY_FAILURE'
        || c === 'DESTINATION_OUT_OF_ORDER' || c === 'NO_RESPONSE' || c === 'ALLOTTED_TIMEOUT'
        || code === 480 || code === 408)) return 'Switched off';
    if (c === 'NORMAL_TEMPORARY_FAILURE' || c === 'DESTINATION_OUT_OF_ORDER'
        || c === 'ALLOTTED_TIMEOUT' || c === 'NO_RESPONSE') return 'No answer';
    if (c === 'NO_USER_RESPONSE' || c === 'NO_ANSWER' || c === 'SUBSCRIBER_ABSENT'
        || c === 'USER_NOT_REGISTERED' || code === 480) return 'Switched off';
    if (code === 404 || c === 'UNALLOCATED_NUMBER' || c === 'NO_ROUTE_DESTINATION'
        || c === 'INVALID_NUMBER_FORMAT') return 'Number not in service';
    if (code === 503 || c === 'NETWORK_OUT_OF_ORDER') return 'Network unavailable';
    if (c === 'NORMAL_CLEARING') return 'Call ended';
    if (sawRing) return 'No answer';
    if (c) return 'Call ended (' + c.replace(/_/g, ' ').toLowerCase() + ')';
    if (code) return 'Call ended (SIP ' + code + ')';
    return 'Call ended';
}
window.skykinOutboundFailLabel = skykinOutboundFailLabel;
function skykinRestoreRegisteredStatus() {
    const ext = skykinGetSupExt();
    window.setSipStatus && window.setSipStatus('registered', 'Registered (' + ext + ')');
}
window.restoreIdlePhoneUi = function(statusText, opts) {
    opts = opts || {};
    try {
        if (typeof stopRingtone === 'function') stopRingtone();
        stopRingback();
        stopOutboundPoll();
        window._outboundRingPhase = false;
        document.getElementById('incomingScreen').style.display = 'none';
        document.getElementById('dpPanel').style.display = 'block';
        document.getElementById('btnHangup').style.display = 'none';
        document.getElementById('btnHold').style.display = 'none';
        document.getElementById('btnMute').style.display = 'none';
        document.getElementById('btnKeypad').style.display = 'none';
        document.getElementById('callTimer').style.display = 'none';
        document.getElementById('phonePopup').classList.remove('call-active');
        clearInterval(callTimerInterval); callStartTime = null;
        if (!opts.skipStatus) {
            const ext = skykinGetSupExt();
            setSipStatus('registered', statusText || ('Registered (' + ext + ')'));
        }
        window._callEnded = false;
    } catch (e) {}
};
function stopOutboundPoll() {
    if (window._outboundPoll) { clearInterval(window._outboundPoll); window._outboundPoll = null; }
}
window.stopOutboundPoll = stopOutboundPoll;
function resetOutboundRingUi() {
    stopOutboundPoll();
    if (window._outRingArmTimer) { clearTimeout(window._outRingArmTimer); window._outRingArmTimer = null; }
    window._outboundRingPhase = false;
    window._outSawBlegRing = false;
    window._outSawActualRing = false;
    window._outRingStartedAt = 0;
    window._outAnswerTicks = 0;
    window._outDeclineTicks = 0;
    window._outMaxCh = 0;
    window._outLastCause = '';
    if (window.restoreIdlePhoneUi) window.restoreIdlePhoneUi();
}
function endOutboundRing(agentHangup) {
    if (agentHangup) window._agentEndedOutbound = true;
    const ext = skykinGetSupExt();
    const dest = window._outboundPollDest || window.lastDialedNumber || '';
    fetch('index.php?action=outbound_stop&ext=' + encodeURIComponent(ext)
        + '&dest=' + encodeURIComponent(dest)
        + '&domain=' + encodeURIComponent(domain), { credentials: 'same-origin' }).catch(function() {});
    const s = session;
    try {
        if (s && !(s instanceof Invitation)
            && s.state !== SessionState.Terminated && s.state !== SessionState.Terminating) {
            try { s.bye(); } catch (e) { try { s.cancel && s.cancel(); } catch (e2) {} }
            try { s.dispose && s.dispose(); } catch (e) {}
        }
    } catch (e) {}
    if (session === s) session = null;
    if (agentHangup && callStartTime) {
        if (window.endCall) window.endCall();
    } else if (agentHangup) {
        window.showToast && window.showToast('Call cancelled');
        resetOutboundRingUi();
    } else {
        resetOutboundRingUi();
    }
}
window.endOutboundRing = endOutboundRing;
function finishOutboundFail(label) {
    if (window._outboundFailDone) return;
    window._outboundFailDone = true;
    label = label || window._lastOutboundFail || 'Call ended';
    window._lastOutboundFail = label;
    stopRingback();
    if (window._outRingArmTimer) { clearTimeout(window._outRingArmTimer); window._outRingArmTimer = null; }
    endOutboundRing(false);
    playOutboundFailTone(label);
    window.showToast && window.showToast(label);
    window.setSipStatus && window.setSipStatus('registered', label);
    if (window._outFailClearTimer) clearTimeout(window._outFailClearTimer);
    window._outFailClearTimer = setTimeout(skykinRestoreRegisteredStatus, 2800);
}
window.finishOutboundFail = finishOutboundFail;

function startOutboundPoll(ext, dest) {
    stopOutboundPoll();
    ext = ext || skykinGetSupExt();
    dest = dest || window.lastDialedNumber || '';
    window._outboundPollDest = dest;
    window._outSawBlegRing = false;
    window._outSawActualRing = false;
    window._outRingStartedAt = 0;
    window._outAnswerTicks = 0;
    window._outDeclineTicks = 0;
    window._outMaxCh = 0;
    window._outboundPoll = setInterval(function() {
        if (!session || session instanceof Invitation) { stopOutboundPoll(); return; }
        if (session.state === SessionState.Terminated || session.state === SessionState.Terminating) {
            stopOutboundPoll(); return;
        }
        if (!window._outboundRingPhase && callStartTime) { stopOutboundPoll(); return; }
        fetch('index.php?action=outbound_live&ext=' + encodeURIComponent(ext)
            + '&dest=' + encodeURIComponent(dest)
            + '&domain=' + encodeURIComponent(domain), { credentials: 'same-origin' })
            .then(function(r) { return r.json(); })
            .then(function(d) {
                if (!d || d.ok === false) return;
                var bst = String(d.bleg_state || '').toUpperCase();
                var ch = (typeof d.channels === 'number') ? d.channels : 0;
                if (ch >= 2) window._outMaxCh = Math.max(window._outMaxCh || 0, ch);
                if (d.hangup_cause) window._outLastCause = String(d.hangup_cause);
                var answered = !!(d.bleg && (bst === 'ACTIVE' || bst === 'ANSWER' || bst === 'EXECUTE'));
                if (!answered && (d.bleg || ch >= 2 || (window._outMaxCh >= 2 && d.agent))) {
                    if (d.bleg || ch >= 2) window._outSawBlegRing = true;
                    enterOutboundRinging(dest);
                }
                if (answered && !callStartTime) {
                    window._outAnswerTicks = (window._outAnswerTicks || 0) + 1;
                    if (window._outAnswerTicks >= 2) {
                        window._outboundRingPhase = false;
                        stopOutboundPoll();
                        stopRingback();
                        if (window._outRingArmTimer) { clearTimeout(window._outRingArmTimer); window._outRingArmTimer = null; }
                        enableSenders(session);
                        if (!session._skykinAudioAttached) attachAudio(session);
                        window.startCallUI && window.startCallUI(dest || window.lastDialedNumber || '');
                        window.showToast && window.showToast('Call connected');
                    }
                    return;
                }
                window._outAnswerTicks = 0;
                var partnerGone = window._outboundRingPhase && !answered && (
                    (window._outSawBlegRing && !d.bleg)
                    || (window._outMaxCh >= 2 && ch <= 1 && d.agent && !d.bleg)
                );
                if (partnerGone) {
                    window._outDeclineTicks = (window._outDeclineTicks || 0) + 1;
                    if (window._outDeclineTicks >= 1) {
                        finishOutboundFail(skykinOutboundFailLabel(d.hangup_cause || window._outLastCause || '', 0, {
                            sawRing: !!window._outSawActualRing
                        }));
                    }
                } else if (!answered) {
                    window._outDeclineTicks = 0;
                }
            }).catch(function() {});
    }, 400);
}
window.startOutboundPoll = startOutboundPoll;

function enableSenders(s) {
    try {
        const pc = s && s.sessionDescriptionHandler && s.sessionDescriptionHandler.peerConnection;
        if (!pc) return;
        pc.getSenders().forEach(function(sender) {
            if (sender.track && sender.track.kind === 'audio') sender.track.enabled = true;
        });
    } catch (e) {}
}
function attachAudio(s) {
    const sdh = s.sessionDescriptionHandler;
    if (!sdh || !sdh.peerConnection) return;
    enableSenders(s);
    if (s._skykinAudioAttached) return;
    s._skykinAudioAttached = true;
    const remote = new MediaStream();
    sdh.peerConnection.getReceivers().forEach(r => { if (r.track) remote.addTrack(r.track); });
    const el = document.getElementById('remoteAudio');
    if (el) { el.srcObject = remote; el.play().catch(function(){}); }
    sdh.peerConnection.ontrack = function(ev) {
        if (ev.track && ev.track.kind === 'audio') {
            remote.addTrack(ev.track);
            if (el) { el.srcObject = remote; el.play().catch(function(){}); }
        }
    };
}

function bindSession(s) {
    s.stateChange.addListener(state => {
        if (state === SessionState.Established) {
            s._skykinEstablished = true;
            window._callEnded = false;
            const num = s instanceof Invitation
                ? (s.remoteIdentity && s.remoteIdentity.uri && s.remoteIdentity.uri.user) || window.lastDialedNumber || ''
                : (window.lastDialedNumber || '');
            if (s instanceof Invitation) {
                window.startCallUI && window.startCallUI(num);
                attachAudio(s);
                window.showToast && window.showToast('Call connected');
            } else {
                window._outboundRingPhase = true;
                window.setSipStatus && window.setSipStatus('calling', 'Calling: ' + num);
                enableSenders(s);
                if (!s._skykinAudioAttached) attachAudio(s);
                startOutboundPoll(skykinGetSupExt(), num);
            }
        }
        if (state === SessionState.Terminated || state === SessionState.Terminating) {
            if (session && session !== s) return;
            if (session === s) session = null;
            if (!(s instanceof Invitation) && !callStartTime) {
                if (window._agentEndedOutbound || window._outboundFailDone) {
                    window._agentEndedOutbound = false;
                    if (!window._outboundFailDone) resetOutboundRingUi();
                } else if (window._outboundRingPhase || window._outLastCause || window._lastOutboundFail) {
                    finishOutboundFail(skykinOutboundFailLabel(window._outLastCause || '', window._lastOutboundSipCode, {
                        sawRing: !!window._outSawActualRing
                    }));
                } else {
                    resetOutboundRingUi();
                }
            } else if (window.endCall) {
                window.endCall();
            }
        }
    });
}

window.sipBridge.init = function(ext, pass, server, port, dom) {
    if (ua) { try { reg && reg.unregister(); ua.stop(); } catch(e) {} }
    let wsUri = server;
    if (!wsUri.startsWith('wss://') && !wsUri.startsWith('ws://')) {
        wsUri = (location.protocol === 'https:' ? 'wss://' : 'ws://') + wsUri;
    }
    const hostPart = wsUri.replace(/^wss?:\/\//i, '');
    if (!hostPart.includes('/') && !hostPart.includes(':')) {
        const pagePort = location.port ? (':' + location.port) : '';
        wsUri = wsUri.replace(/^(wss?:\/\/)([^/:]+)$/i, '$1$2' + pagePort) + '/wss/';
    } else if (!hostPart.includes('/') && hostPart.endsWith(':' + (port || '5066'))) {
        wsUri = (location.protocol === 'https:' ? 'wss://' : 'ws://')
            + location.hostname + (location.port ? ':' + location.port : '') + '/wss/';
    }
    const sipUri = UserAgent.makeURI('sip:' + ext + '@' + dom);
    if (!sipUri) {
        window.setSipStatus('failed', 'Bad SIP address');
        return;
    }
    ua = new UserAgent({
        uri: sipUri,
        transportOptions: { server: wsUri, connectionTimeout: 8, traceSip: false },
        authorizationUsername: ext,
        authorizationPassword: pass,
        contactParams: { transport: 'wss' },
        logLevel: 'error',
        logConfiguration: false,
        sessionDescriptionHandlerFactoryOptions: {
            iceGatheringTimeout: ICE_GATHERING_TIMEOUT_MS,
            peerConnectionConfiguration: ICE_PC_CONFIG,
            modifiers: SDP_MODIFIERS
        }
    });
    reg = new Registerer(ua, { expires: 300, logConfiguration: false });
    reg.stateChange.addListener(state => {
        if (state === 'Registered') {
            window.setSipStatus('registered', 'Registered (' + ext + ')');
            window.ensureMic && window.ensureMic().catch(function(){});
        } else if (state === 'Unregistered') {
            window.setSipStatus('unregistered', 'Not Registered');
        } else if (state === 'Terminated') {
            window.setSipStatus('failed', 'Registration Failed');
        }
    });
    ua.delegate = {
        onInvite(inv) {
            if (session && session !== inv
                && (session.state === SessionState.Established
                    || (session.state === SessionState.Establishing && !(session instanceof Invitation)))) {
                try { inv.reject({ statusCode: 486 }); } catch (e) {}
                return;
            }
            session = inv;
            window._callEnded = false;
            const num = inv.remoteIdentity?.uri?.user
                || inv.remoteIdentity?.displayName
                || 'Unknown';
            window.lastDialedNumber = num;
            try { inv.progress({ statusCode: 180 }).catch(function(){}); } catch (e) {}
            window.handleIncoming && window.handleIncoming(num);
            bindSession(inv);
        }
    };
    ua.start().then(() => reg.register()).catch(err => {
        window.setSipStatus('failed', 'Error: ' + err.message);
    });
};

window.ensureMic = function() {
    if (window._micStream) return Promise.resolve(window._micStream);
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        return Promise.reject(new Error('Microphone needs HTTPS'));
    }
    return navigator.mediaDevices.getUserMedia(MIC_CONSTRAINTS)
        .then(function(stream) { window._micStream = stream; return stream; });
};

window.sipBridge.makeCall = function(number) {
    if (!ua) { window.showToast && window.showToast('SIP not initialized — open phone settings'); return; }
    number = (window.skykinNormalizeEtDial && window.skykinNormalizeEtDial(number)) || number;
    const uri = UserAgent.makeURI('sip:' + number + '@' + pbxDomain());
    if (!uri) return;
    if (session) { try { session.dispose && session.dispose(); } catch(e) {} session = null; }
    window.ensureMic().then(function() {
        const inv = new Inviter(ua, uri, {
            sessionDescriptionHandlerOptions: {
                constraints: MIC_CONSTRAINTS,
                iceGatheringTimeout: ICE_GATHERING_TIMEOUT_MS,
                peerConnectionConfiguration: ICE_PC_CONFIG
            },
            sessionDescriptionHandlerModifiers: SDP_MODIFIERS
        });
        session = inv;
        window.lastDialedNumber = number;
        window._outboundRingPhase = true;
        window._outboundFailDone = false;
        window._agentEndedOutbound = false;
        window._outLastCause = '';
        window._lastOutboundFail = '';
        window._lastOutboundSipCode = 0;
        window._outSawActualRing = false;
        window._outRingStartedAt = 0;
        window._callEnded = false;
        window.setSipStatus && window.setSipStatus('calling', 'Calling: ' + number);
        try {
            var _ac = window.AudioContext || window.webkitAudioContext;
            if (_ac) {
                if (!_rbCtx || _rbCtx.state === 'closed') _rbCtx = new _ac();
                _rbCtx.resume && _rbCtx.resume();
            }
        } catch (e) {}
        if (window._outRingArmTimer) clearTimeout(window._outRingArmTimer);
        window._outRingArmTimer = setTimeout(function() {
            enterOutboundRinging(number);
        }, 1200);
        bindSession(inv);
        startOutboundPoll(skykinGetSupExt(), number);
        return inv.invite({
            requestDelegate: {
                onProgress: function() {
                    enableSenders(inv);
                    startOutboundPoll(skykinGetSupExt(), number);
                },
                onAccept: function() {
                    enableSenders(inv);
                    if (!inv._skykinAudioAttached) attachAudio(inv);
                    if (!window._outSawActualRing) {
                        window.setSipStatus && window.setSipStatus('calling', 'Calling: ' + number);
                    }
                    startOutboundPoll(skykinGetSupExt(), number);
                },
                onReject: function(response) {
                    var code = 0;
                    try {
                        code = (response && response.message && response.message.statusCode)
                            || (response && response.statusCode) || 0;
                    } catch (e) {}
                    window._lastOutboundSipCode = code;
                    if (window._outRingArmTimer) { clearTimeout(window._outRingArmTimer); window._outRingArmTimer = null; }
                    var label = skykinOutboundFailLabel('', code, { sawRing: !!window._outSawActualRing });
                    window._lastOutboundFail = label;
                    stopRingback();
                    playOutboundFailTone(label);
                    window.showToast && window.showToast(label);
                    if (window.restoreIdlePhoneUi) window.restoreIdlePhoneUi(null, { skipStatus: true });
                    window.setSipStatus && window.setSipStatus('registered', label);
                    if (window._outFailClearTimer) clearTimeout(window._outFailClearTimer);
                    window._outFailClearTimer = setTimeout(skykinRestoreRegisteredStatus, 2800);
                }
            }
        }).catch(function(err) {
            stopRingback();
            stopOutboundPoll();
            window.showToast && window.showToast('Call failed: ' + (err && err.message ? err.message : err));
            if (window.restoreIdlePhoneUi) window.restoreIdlePhoneUi(null, { skipStatus: true });
            window.setSipStatus && window.setSipStatus('registered', 'Call failed');
            setTimeout(skykinRestoreRegisteredStatus, 2800);
        });
    }).catch(function() {
        window.showToast && window.showToast('Microphone blocked — allow mic and reload');
    });
};

'''

p = Path(r"C:\Users\hp\skykin-fusionpbx\app\agent_dashboard\supervisor.php")
t = p.read_text(encoding="utf-8")
start = t.find("let _rbCtx = null, _rbInterval = null;")
end = t.find("window.sipBridge.hangup = function()")
if start < 0 or end < 0:
    raise SystemExit(f"markers not found start={start} end={end}")
t2 = t[:start] + NEW + "\n" + t[end:]
t2 = t2.replace(
    "function hangupCall() { if (sipBridge.hangup) sipBridge.hangup(); endCall(); }",
    "function hangupCall() {\n"
    "    if (window._outboundRingPhase && window.endOutboundRing) {\n"
    "        window.endOutboundRing(true);\n"
    "        return;\n"
    "    }\n"
    "    if (sipBridge.hangup) sipBridge.hangup();\n"
    "    endCall();\n"
    "}",
)
p.write_text(t2, encoding="utf-8")
print("OK marker", t2.count("SKYKIN_SUP_OUT_v1"), "hangup", "endOutboundRing(true)" in t2)
