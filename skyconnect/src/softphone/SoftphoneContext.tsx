import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import {
  Invitation,
  Inviter,
  Registerer,
  Session,
  SessionState,
  UserAgent,
  Web,
} from 'sip.js';
import {
  playOutboundFailTone,
  startRingback,
  startRingtone,
  stopAllCallTones,
  stopRingback,
  stopRingtone,
} from '../lib/callTones';
import {
  applyAudioContextSink,
  applySpeakerSink,
  bindHeadsetButtons,
  micConstraints,
} from '../lib/headset';
import {
  ICE_GATHERING_TIMEOUT_MS,
  ICE_PC_CONFIG,
  SDP_MODIFIERS,
  webAudioSessionDescriptionHandlerFactory,
} from '../lib/sipMedia';
import { fetchAgentSession } from '../services/session';

export type SipPhase =
  | 'idle'
  | 'connecting'
  | 'registered'
  | 'calling'
  | 'ringing'
  | 'in_call'
  | 'failed';

export type SoftphoneCreds = {
  extension: string;
  password: string;
  domain: string;
  wss?: string;
};

export type CallAudioStreams = {
  local: MediaStream | null;
  remote: MediaStream | null;
};

const LAST_NUM_KEY = 'skyconnect_last_remote';

type SoftphoneApi = {
  phase: SipPhase;
  statusLabel: string;
  remoteNumber: string;
  /** Survives hangup so Wrap-up can save journey for this customer. */
  lastRemoteNumber: string;
  muted: boolean;
  onHold: boolean;
  inConference: boolean;
  conferenceTarget: string;
  callSeconds: number;
  creds: SoftphoneCreds;
  setCreds: (c: SoftphoneCreds) => void;
  register: () => void;
  unregister: () => void;
  dial: (number: string) => void;
  answer: () => void;
  decline: () => void;
  hangup: () => void;
  transfer: (extension: string) => Promise<void>;
  conference: (extension: string) => Promise<void>;
  toggleMute: () => void;
  toggleHold: () => void;
  clearLastRemoteNumber: () => void;
  getCallAudio: () => CallAudioStreams;
  sendDtmf: (tone: string) => void;
  applyHeadsetAudio: () => void;
};

const HOLD_MODIFIER = (desc: RTCSessionDescriptionInit) => {
  if (desc.sdp) {
    desc.sdp = desc.sdp
      .replace(/a=sendrecv/g, 'a=sendonly')
      .replace(/a=recvonly/g, 'a=inactive');
  }
  return Promise.resolve(desc);
};

async function setSessionHold(session: Session, hold: boolean): Promise<void> {
  if (session.state !== SessionState.Established) return;
  if (hold) {
    await session.invite({
      sessionDescriptionHandlerModifiers: [...SDP_MODIFIERS, HOLD_MODIFIER],
    });
  } else {
    await session.invite({ sessionDescriptionHandlerModifiers: SDP_MODIFIERS });
  }
}

function endOneSession(session: Session | null) {
  if (!session) return;
  try {
    if (session.state === SessionState.Established) {
      session.bye().catch(() => {});
    } else if (session instanceof Invitation) {
      session.reject().catch(() => {});
    } else if (session instanceof Inviter) {
      session.cancel().catch(() => {});
    }
  } catch {
    /* ignore */
  }
}

const STORAGE_KEY = 'skyconnect_sip';

const defaults: SoftphoneCreds = {
  extension: '101',
  password: '',
  domain: 'client1.skykin.local',
};

/** Always same-origin /wss/ on current host (nginx → ws-sip). Never :8088 — browsers get 1006. */
function sameOriginWss(): string {
  const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
  return `${scheme}://${location.host}/wss/`;
}

function loadCreds(): SoftphoneCreds {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaults;
    const parsed = { ...defaults, ...JSON.parse(raw) } as SoftphoneCreds;
    // Drop cached :8088 / stale wss from earlier builds
    parsed.wss = sameOriginWss();
    return parsed;
  } catch {
    return defaults;
  }
}

function wsUri(_creds: SoftphoneCreds): string {
  return sameOriginWss();
}

const SoftphoneContext = createContext<SoftphoneApi | null>(null);

export function SoftphoneProvider({ children }: { children: ReactNode }) {
  const [creds, setCredsState] = useState<SoftphoneCreds>(loadCreds);
  const [phase, setPhase] = useState<SipPhase>('idle');
  const [statusLabel, setStatusLabel] = useState('Not registered');
  const [remoteNumber, setRemoteNumber] = useState('');
  const [lastRemoteNumber, setLastRemoteNumber] = useState(
    () => sessionStorage.getItem(LAST_NUM_KEY) || '',
  );
  const [muted, setMuted] = useState(false);
  const [onHold, setOnHold] = useState(false);
  const [inConference, setInConference] = useState(false);
  const [conferenceTarget, setConferenceTarget] = useState('');
  const [callSeconds, setCallSeconds] = useState(0);

  const uaRef = useRef<UserAgent | null>(null);
  const regRef = useRef<Registerer | null>(null);
  const sessionRef = useRef<Session | null>(null);
  const consultSessionRef = useRef<Session | null>(null);
  const remoteAudioRef = useRef<HTMLAudioElement | null>(null);
  const callTickRef = useRef<number | null>(null);

  const setCreds = useCallback((c: SoftphoneCreds) => {
    setCredsState(c);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(c));
  }, []);

  const stopTimer = useCallback(() => {
    if (callTickRef.current) {
      clearInterval(callTickRef.current);
      callTickRef.current = null;
    }
  }, []);

  const startTimer = useCallback(() => {
    stopTimer();
    setCallSeconds(0);
    callTickRef.current = window.setInterval(() => {
      setCallSeconds((s) => s + 1);
    }, 1000);
  }, [stopTimer]);

  const ensureRemoteAudioEl = useCallback(() => {
    let el = remoteAudioRef.current;
    if (!el) {
      el = document.createElement('audio');
      el.autoplay = true;
      el.muted = false;
      el.volume = 1;
      el.setAttribute('playsinline', 'true');
      document.body.appendChild(el);
      remoteAudioRef.current = el;
    }
    el.muted = false;
    el.volume = 1;
    void applySpeakerSink(el);
    return el;
  }, []);

  const attachRemoteAudio = useCallback(
    (session: Session) => {
      try {
        const ctx = Web.WebAudioSessionDescriptionHandler.audioContext;
        if (ctx && ctx.state === 'suspended') void ctx.resume();
      } catch {
        /* ignore */
      }
      const sdh = session.sessionDescriptionHandler as
        | { peerConnection?: RTCPeerConnection; remoteMediaStream?: MediaStream }
        | undefined;
      const el = ensureRemoteAudioEl();
      const apply = (stream: MediaStream | null | undefined) => {
        if (!stream) return;
        const tracks = stream.getAudioTracks().filter((t) => t.readyState !== 'ended');
        if (!tracks.length) return;
        const playable = new MediaStream(tracks);
        el.srcObject = playable;
        el.muted = false;
        el.volume = 1;
        void applySpeakerSink(el);
        void el.play().catch(() => {});
      };
      const pc = sdh?.peerConnection;
      if (pc) {
        pc.ontrack = (e) => apply(e.streams?.[0] || (e.track ? new MediaStream([e.track]) : null));
        const remote = new MediaStream();
        pc.getReceivers().forEach((r) => {
          if (r.track && r.track.kind === 'audio') remote.addTrack(r.track);
        });
        apply(remote);
      }
      apply(sdh?.remoteMediaStream);
    },
    [ensureRemoteAudioEl],
  );

  /** Mix both remote legs into one playback stream for the agent. */
  const attachConferenceAudio = useCallback(
    (sessions: Session[]) => {
      const ctx =
        Web.WebAudioSessionDescriptionHandler.audioContext || new AudioContext();
      Web.WebAudioSessionDescriptionHandler.audioContext = ctx;
      const dest = ctx.createMediaStreamDestination();
      for (const session of sessions) {
        const sdh = session.sessionDescriptionHandler as
          | { remoteMediaStream?: MediaStream }
          | undefined;
        if (!sdh?.remoteMediaStream) continue;
        try {
          ctx.createMediaStreamSource(sdh.remoteMediaStream).connect(dest);
        } catch {
          /* ignore */
        }
      }
      const el = ensureRemoteAudioEl();
      el.srcObject = dest.stream;
      void applySpeakerSink(el);
      void applyAudioContextSink(ctx);
      el.play().catch(() => {});
    },
    [ensureRemoteAudioEl],
  );

  const rememberRemote = useCallback((num: string) => {
    const n = num.trim();
    if (!n) return;
    setRemoteNumber(n);
    setLastRemoteNumber(n);
    try {
      sessionStorage.setItem(LAST_NUM_KEY, n);
    } catch {
      /* ignore */
    }
  }, []);

  const clearLastRemoteNumber = useCallback(() => {
    setLastRemoteNumber('');
    try {
      sessionStorage.removeItem(LAST_NUM_KEY);
    } catch {
      /* ignore */
    }
  }, []);

  const getCallAudio = useCallback((): CallAudioStreams => {
    const session = sessionRef.current;
    const empty: CallAudioStreams = { local: null, remote: null };
    if (!session) return empty;
    const sdh = session.sessionDescriptionHandler as
      | {
          localMediaStream?: MediaStream;
          remoteMediaStream?: MediaStream;
          peerConnection?: RTCPeerConnection;
        }
      | undefined;
    let remote = sdh?.remoteMediaStream ?? null;
    let local = sdh?.localMediaStream ?? null;
    const pc = sdh?.peerConnection;
    if ((!remote || remote.getAudioTracks().length === 0) && pc) {
      remote = new MediaStream();
      pc.getReceivers().forEach((r) => {
        if (r.track && r.track.kind === 'audio') remote!.addTrack(r.track);
      });
    }
    if ((!local || local.getAudioTracks().length === 0) && pc) {
      local = new MediaStream();
      pc.getSenders().forEach((s) => {
        if (s.track && s.track.kind === 'audio') local!.addTrack(s.track);
      });
    }
    return { local, remote };
  }, []);

  const sendDtmf = useCallback((tone: string) => {
    const t = tone.trim();
    if (!t) return;
    const sessions = [sessionRef.current, consultSessionRef.current].filter(
      Boolean,
    ) as Session[];
    for (const session of sessions) {
      if (session.state !== SessionState.Established) continue;
      const sdh = session.sessionDescriptionHandler as
        | { sendDtmf?: (digit: string) => boolean }
        | undefined;
      try {
        sdh?.sendDtmf?.(t);
      } catch {
        /* ignore */
      }
    }
  }, []);

  const clearSession = useCallback(() => {
    sessionRef.current = null;
    consultSessionRef.current = null;
    setMuted(false);
    setOnHold(false);
    setInConference(false);
    setConferenceTarget('');
    stopTimer();
    // Keep lastRemoteNumber for Wrap-up / Customer 360 after hangup
    setRemoteNumber('');
    if (remoteAudioRef.current) {
      remoteAudioRef.current.srcObject = null;
    }
  }, [stopTimer]);

  const resetToRegistered = useCallback(() => {
    stopAllCallTones();
    clearSession();
    setPhase(regRef.current ? 'registered' : 'idle');
    setStatusLabel(regRef.current ? `Registered (${creds.extension})` : 'Not registered');
  }, [clearSession, creds.extension]);

  const bindSession = useCallback(
    (session: Session) => {
      // Remote CANCEL while we are still ringing — clear UI + stop ringtone
      if (session instanceof Invitation) {
        session.delegate = {
          ...(session.delegate || {}),
          onCancel: () => {
            if (sessionRef.current === session) {
              resetToRegistered();
            }
          },
        };
      }

      session.stateChange.addListener((state) => {
        if (state === SessionState.Establishing) {
          // Outbound Progress / early media — keep ringback if already calling
        } else if (state === SessionState.Established) {
          stopAllCallTones();
          setPhase('in_call');
          setStatusLabel('Connected');
          startTimer();
          attachRemoteAudio(session);
          window.setTimeout(() => attachRemoteAudio(session), 400);
          window.setTimeout(() => attachRemoteAudio(session), 1500);
        } else if (state === SessionState.Terminated) {
          // If primary ended, also drop consult (customer gone → no orphan consult).
          // If only consult ended, conference listener keeps primary — skip here.
          if (sessionRef.current === session) {
            if (consultSessionRef.current && consultSessionRef.current !== session) {
              endOneSession(consultSessionRef.current);
            }
            resetToRegistered();
          } else if (consultSessionRef.current === session) {
            consultSessionRef.current = null;
            setInConference(false);
            setConferenceTarget('');
            if (sessionRef.current?.state === SessionState.Established) {
              attachRemoteAudio(sessionRef.current);
              setStatusLabel('Other party left — caller still connected');
            }
          }
        }
      });
    },
    [attachRemoteAudio, creds.extension, resetToRegistered, startTimer],
  );

  const unregister = useCallback(() => {
    try {
      regRef.current?.unregister().catch(() => {});
      uaRef.current?.stop().catch(() => {});
    } catch {
      /* ignore */
    }
    uaRef.current = null;
    regRef.current = null;
    clearSession();
    setPhase('idle');
    setStatusLabel('Not registered');
  }, [clearSession]);

  const register = useCallback(() => {
    unregister();
    if (!creds.extension || !creds.password || !creds.domain) {
      setPhase('failed');
      setStatusLabel('Enter extension, password and domain');
      return;
    }

    const uri = UserAgent.makeURI(`sip:${creds.extension}@${creds.domain}`);
    if (!uri) {
      setPhase('failed');
      setStatusLabel('Bad SIP address');
      return;
    }

    setPhase('connecting');
    setStatusLabel('Connecting...');

    const ua = new UserAgent({
      uri,
      transportOptions: {
        server: wsUri(creds),
        connectionTimeout: 8,
      },
      authorizationUsername: creds.extension,
      authorizationPassword: creds.password,
      contactParams: { transport: 'wss' },
      logLevel: 'error',
      // WebAudio SDH required for local 3-way conference mixing
      sessionDescriptionHandlerFactory: webAudioSessionDescriptionHandlerFactory,
      sessionDescriptionHandlerFactoryOptions: {
        iceGatheringTimeout: ICE_GATHERING_TIMEOUT_MS,
        peerConnectionConfiguration: ICE_PC_CONFIG,
      },
    });

    const reg = new Registerer(ua, { expires: 300 });
    uaRef.current = ua;
    regRef.current = reg;

    const failTimer = window.setTimeout(() => {
      setPhase('failed');
      setStatusLabel('Phone sign-in timed out');
    }, 20000);

    reg.stateChange.addListener((state) => {
      if (state === 'Registered') {
        clearTimeout(failTimer);
        setPhase('registered');
        setStatusLabel(`Registered (${creds.extension})`);
      } else if (state === 'Unregistered') {
        setPhase('idle');
        setStatusLabel('Not registered');
      } else if (state === 'Terminated') {
        clearTimeout(failTimer);
        setPhase('failed');
        setStatusLabel('Registration failed');
      }
    });

    ua.delegate = {
      onInvite(inv) {
        if (
          sessionRef.current &&
          sessionRef.current !== inv &&
          (sessionRef.current.state === SessionState.Established ||
            sessionRef.current.state === SessionState.Establishing)
        ) {
          inv.reject({ statusCode: 486 }).catch(() => {});
          return;
        }
        sessionRef.current = inv;
        const num =
          inv.remoteIdentity?.uri?.user ||
          inv.remoteIdentity?.displayName ||
          'Unknown';
        rememberRemote(num);
        setPhase('ringing');
        setStatusLabel(`Incoming: ${num}`);
        stopRingback();
        startRingtone();
        inv.progress({ statusCode: 180 }).catch(() => {});
        bindSession(inv);
      },
    };

    ua.start()
      .then(() => reg.register())
      .catch((err: Error) => {
        clearTimeout(failTimer);
        setPhase('failed');
        setStatusLabel(err?.message || 'WebSocket failed');
      });
  }, [bindSession, creds, rememberRemote, unregister]);

  const dial = useCallback(
    async (number: string) => {
      const ua = uaRef.current;
      if (!ua) {
        setStatusLabel('Register first');
        return;
      }
      const dest = number.trim();
      if (!dest) return;

      if (sessionRef.current) {
        const prev = sessionRef.current;
        if (prev.state === SessionState.Established) {
          setStatusLabel('Already on a call — use Transfer or Conference for another agent');
          return;
        }
        sessionRef.current = null;
        try {
          if (prev instanceof Inviter) prev.cancel().catch(() => {});
          else if (prev instanceof Invitation) prev.reject().catch(() => {});
          else prev.bye().catch(() => {});
        } catch {
          /* ignore */
        }
      }

      try {
        await navigator.mediaDevices.getUserMedia(micConstraints());
      } catch {
        setPhase('failed');
        setStatusLabel('Microphone permission required');
        return;
      }

      const target = UserAgent.makeURI(`sip:${dest}@${creds.domain}`);
      if (!target) return;

      const inv = new Inviter(ua, target, {
        sessionDescriptionHandlerOptions: {
          constraints: micConstraints(),
          iceGatheringTimeout: ICE_GATHERING_TIMEOUT_MS,
          peerConnectionConfiguration: ICE_PC_CONFIG,
        },
      });
      sessionRef.current = inv;
      rememberRemote(dest);
      setPhase('calling');
      setStatusLabel(`Calling ${dest}`);
      stopRingtone();
      startRingback();
      bindSession(inv);

      // Short extensions (101/102): Established is enough — do not wait for
      // mobile/Ethio B-leg signals that never fire on agent-to-agent.
      inv.invite().catch((err: Error) => {
        playOutboundFailTone(err?.message || 'failed');
        setPhase('registered');
        setStatusLabel(err?.message || 'Call failed');
        clearSession();
      });
    },
    [bindSession, clearSession, creds.domain, rememberRemote],
  );

  const answer = useCallback(async () => {
    const session = sessionRef.current;
    if (!(session instanceof Invitation)) return;
    stopRingtone();
    try {
      await navigator.mediaDevices.getUserMedia(micConstraints());
      await session.accept({
        sessionDescriptionHandlerOptions: {
          constraints: micConstraints(),
          iceGatheringTimeout: ICE_GATHERING_TIMEOUT_MS,
          peerConnectionConfiguration: ICE_PC_CONFIG,
        },
      });
      attachRemoteAudio(session);
      window.setTimeout(() => attachRemoteAudio(session), 400);
    } catch (err) {
      setStatusLabel(err instanceof Error ? err.message : 'Answer failed');
    }
  }, [attachRemoteAudio]);

  const decline = useCallback(() => {
    const session = sessionRef.current;
    if (session instanceof Invitation) {
      session.reject({ statusCode: 486 }).catch(() => {});
    }
    stopAllCallTones();
    clearSession();
    setPhase('registered');
    setStatusLabel(`Registered (${creds.extension})`);
  }, [clearSession, creds.extension]);

  const hangup = useCallback(() => {
    const primary = sessionRef.current;
    const consult = consultSessionRef.current;
    if (!primary && !consult) return;

    // Conference / consult: first End drops the other party only — customer stays.
    if (
      consult &&
      primary &&
      primary.state === SessionState.Established &&
      (inConference || consult.state === SessionState.Established || consult.state === SessionState.Establishing)
    ) {
      endOneSession(consult);
      consultSessionRef.current = null;
      setInConference(false);
      setConferenceTarget('');
      try {
        attachRemoteAudio(primary);
      } catch {
        /* ignore */
      }
      setStatusLabel('Other party ended — caller still connected');
      return;
    }

    endOneSession(consult);
    endOneSession(primary);
    stopAllCallTones();
    clearSession();
    setPhase('registered');
    setStatusLabel(`Registered (${creds.extension})`);
  }, [attachRemoteAudio, clearSession, creds.extension, inConference]);

  /** Blind transfer (SIP REFER) to another extension — same idea as old dashboard Transfer. */
  const transfer = useCallback(
    async (extension: string) => {
      const dest = extension.trim();
      const session = sessionRef.current;
      if (!dest) {
        setStatusLabel('Enter transfer target');
        return;
      }
      if (!session || session.state !== SessionState.Established) {
        setStatusLabel('No active call to transfer');
        return;
      }
      const uri = UserAgent.makeURI(`sip:${dest}@${creds.domain}`);
      if (!uri) {
        setStatusLabel('Bad transfer target');
        return;
      }
      try {
        setStatusLabel(`Transferring to ${dest}…`);
        await session.refer(uri, {
          requestDelegate: {
            onAccept: () => {
              setStatusLabel(`Transferred to ${dest}`);
            },
            onReject: () => {
              setStatusLabel(`Transfer rejected (${dest})`);
            },
          },
        });
        // Blind transfer: drop our leg after REFER is sent
        window.setTimeout(() => {
          try {
            if (sessionRef.current?.state === SessionState.Established) {
              sessionRef.current.bye().catch(() => {});
            }
          } catch {
            /* ignore */
          }
          clearSession();
          setPhase('registered');
          setStatusLabel(`Registered (${creds.extension})`);
        }, 800);
      } catch (err) {
        setStatusLabel(err instanceof Error ? err.message : 'Transfer failed');
      }
    },
    [clearSession, creds.domain, creds.extension],
  );

  const reusePrimaryMic = (from: Session, to: Session) => {
    const src = (
      from.sessionDescriptionHandler as { localMediaStream?: MediaStream } | undefined
    )?.localMediaStream;
    const track = src?.getAudioTracks()[0];
    const pc = (
      to.sessionDescriptionHandler as { peerConnection?: RTCPeerConnection } | undefined
    )?.peerConnection;
    if (!track || !pc) return;
    const sender = pc.getSenders().find((s) => s.track?.kind === 'audio' || !s.track);
    if (sender) sender.replaceTrack(track).catch(() => {});
    else pc.addTrack(track);
  };

  /**
   * 3-way conference: dial B without SIP hold/re-INVITE (that drops WebRTC here),
   * reuse the live mic track, then mix both legs.
   */
  const conference = useCallback(
    async (extension: string) => {
      const dest = extension.trim();
      const ua = uaRef.current;
      const primary = sessionRef.current;
      if (!dest) {
        setStatusLabel('Enter conference target');
        return;
      }
      if (!ua) {
        setStatusLabel('Register first');
        return;
      }
      if (!primary || primary.state !== SessionState.Established) {
        setStatusLabel('Need an active call for conference');
        return;
      }
      if (inConference || consultSessionRef.current) {
        setStatusLabel('Already in conference / consulting');
        return;
      }

      const target = UserAgent.makeURI(`sip:${dest}@${creds.domain}`);
      if (!target) {
        setStatusLabel('Bad conference target');
        return;
      }

      try {
        setConferenceTarget(dest);
        setStatusLabel(`Conference: calling ${dest}…`);

        const inv = new Inviter(ua, target, {
          sessionDescriptionHandlerOptions: {
            constraints: micConstraints(),
            iceGatheringTimeout: ICE_GATHERING_TIMEOUT_MS,
            peerConnectionConfiguration: ICE_PC_CONFIG,
          },
          sessionDescriptionHandlerModifiers: SDP_MODIFIERS,
        });
        consultSessionRef.current = inv;
        inv.stateChange.addListener((state) => {
          if (state === SessionState.Establishing || state === SessionState.Established) {
            reusePrimaryMic(primary, inv);
          }
        });

        await new Promise<void>((resolve, reject) => {
          const onState = (state: SessionState) => {
            if (state === SessionState.Established) {
              inv.stateChange.removeListener(onState);
              resolve();
            } else if (state === SessionState.Terminated) {
              inv.stateChange.removeListener(onState);
              reject(new Error('Conference party hung up'));
            }
          };
          inv.stateChange.addListener(onState);
          inv.invite().catch((err: Error) => {
            inv.stateChange.removeListener(onState);
            reject(err);
          });
        });

        reusePrimaryMic(primary, inv);
        Web.startLocalConference([primary, inv]);
        setInConference(true);
        attachConferenceAudio([primary, inv]);
        // Display both parties; keep lastRemoteNumber as the original customer
        setRemoteNumber((prev) => (prev ? `${prev} + ${dest}` : dest));
        setStatusLabel(`Conference with ${dest}`);

        inv.stateChange.addListener((state) => {
          if (state === SessionState.Terminated) {
            consultSessionRef.current = null;
            setInConference(false);
            setConferenceTarget('');
            if (sessionRef.current?.state === SessionState.Established) {
              attachRemoteAudio(sessionRef.current);
              setStatusLabel('Conference ended — caller still connected');
            }
          }
        });
      } catch (err) {
        endOneSession(consultSessionRef.current);
        consultSessionRef.current = null;
        setInConference(false);
        setConferenceTarget('');
        try {
          if (sessionRef.current?.state === SessionState.Established) {
            attachRemoteAudio(sessionRef.current);
          }
        } catch {
          /* ignore */
        }
        setStatusLabel(err instanceof Error ? err.message : 'Conference failed');
      }
    },
    [attachConferenceAudio, attachRemoteAudio, creds.domain, inConference],
  );

  const toggleMute = useCallback(() => {
    const sessions = [sessionRef.current, consultSessionRef.current].filter(
      Boolean,
    ) as Session[];
    if (!sessions.length) return;
    const next = !muted;
    for (const session of sessions) {
      const sdh = session.sessionDescriptionHandler;
      if (sdh instanceof Web.WebAudioSessionDescriptionHandler) {
        try {
          sdh.enableSenderTracks(!next);
          continue;
        } catch {
          /* fall through */
        }
      }
      const pc = (sdh as { peerConnection?: RTCPeerConnection } | undefined)
        ?.peerConnection;
      pc?.getSenders().forEach((s) => {
        if (s.track?.kind === 'audio') s.track.enabled = !next;
      });
    }
    setMuted(next);
  }, [muted]);

  const applyHeadsetAudio = useCallback(() => {
    void applySpeakerSink(remoteAudioRef.current);
    try {
      void applyAudioContextSink(Web.WebAudioSessionDescriptionHandler.audioContext);
    } catch {
      /* ignore */
    }
  }, []);

  const toggleHold = useCallback(async () => {
    const session = sessionRef.current;
    if (!session || session.state !== SessionState.Established) return;
    if (inConference) {
      setStatusLabel('Leave conference (End) before Hold');
      return;
    }
    try {
      await setSessionHold(session, !onHold);
      setOnHold(!onHold);
    } catch {
      /* hold optional */
    }
  }, [inConference, onHold]);

  const phaseRef = useRef(phase);
  phaseRef.current = phase;
  const answerRef = useRef(answer);
  answerRef.current = answer;
  const hangupRef = useRef(hangup);
  hangupRef.current = hangup;
  const muteRef = useRef(toggleMute);
  muteRef.current = toggleMute;

  useEffect(
    () =>
      bindHeadsetButtons({
        ringing: () => phaseRef.current === 'ringing',
        inCall: () => phaseRef.current === 'in_call' || phaseRef.current === 'calling',
        answer: () => void answerRef.current(),
        hangup: () => hangupRef.current(),
        toggleMute: () => muteRef.current(),
      }),
    [],
  );

  // Load SIP creds from FusionPBX login session (same source as old dashboard)
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const s = await fetchAgentSession();
        if (cancelled) return;
        if (!s.extension || !s.password) {
          setPhase('failed');
          setStatusLabel('No extension linked to this user');
          return;
        }
        setCreds({
          extension: s.extension,
          password: s.password,
          domain: s.domain,
          wss: sameOriginWss(),
        });
      } catch {
        /* session.ts redirects to login on 401 */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [setCreds]);

  // Auto-register once session creds are present
  useEffect(() => {
    if (creds.extension && creds.password && creds.domain && phase === 'idle') {
      register();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only when creds identity changes
  }, [creds.extension, creds.password, creds.domain, creds.wss]);

  useEffect(() => {
    const onUnload = () => {
      try {
        regRef.current?.unregister().catch(() => {});
        uaRef.current?.stop().catch(() => {});
      } catch {
        /* ignore */
      }
    };
    window.addEventListener('beforeunload', onUnload);
    return () => window.removeEventListener('beforeunload', onUnload);
  }, []);

  const api = useMemo<SoftphoneApi>(
    () => ({
      phase,
      statusLabel,
      remoteNumber,
      lastRemoteNumber,
      muted,
      onHold,
      inConference,
      conferenceTarget,
      callSeconds,
      creds,
      setCreds,
      register,
      unregister,
      dial,
      answer,
      decline,
      hangup,
      transfer,
      conference,
      toggleMute,
      toggleHold,
      clearLastRemoteNumber,
      getCallAudio,
      sendDtmf,
      applyHeadsetAudio,
    }),
    [
      phase,
      statusLabel,
      remoteNumber,
      lastRemoteNumber,
      muted,
      onHold,
      inConference,
      conferenceTarget,
      callSeconds,
      creds,
      setCreds,
      register,
      unregister,
      dial,
      answer,
      decline,
      hangup,
      transfer,
      conference,
      toggleMute,
      toggleHold,
      clearLastRemoteNumber,
      getCallAudio,
      sendDtmf,
      applyHeadsetAudio,
    ],
  );

  return <SoftphoneContext.Provider value={api}>{children}</SoftphoneContext.Provider>;
}

export function useSoftphone() {
  const ctx = useContext(SoftphoneContext);
  if (!ctx) throw new Error('useSoftphone requires SoftphoneProvider');
  return ctx;
}
