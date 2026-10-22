import { useCallback, useEffect, useRef, useState } from 'react';
import { transcribeLiveChunk } from '../services/ops';
import type { CallAudioStreams } from '../softphone/SoftphoneContext';

export type TranscriptLine = {
  id: string;
  speaker: 'you' | 'caller';
  text: string;
  at: number;
};

function pickRecorderMime(): string {
  const types = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus'];
  for (const t of types) {
    if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(t)) return t;
  }
  return '';
}

function cloneAudio(stream: MediaStream | null): MediaStream | null {
  if (!stream) return null;
  const live = stream.getAudioTracks().filter((t) => t.readyState === 'live');
  if (!live.length) return null;
  return new MediaStream(live.map((t) => t.clone()));
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

let lineSeq = 0;

function isAmharic(lang: string): boolean {
  return /^am/i.test((lang || '').trim());
}

/** Captions from live SIP tracks (cloned). Browser speech is fallback for the agent only if server STT is off. */
export function useLiveTranscript(opts: {
  active: boolean;
  muted: boolean;
  onHold: boolean;
  lang: string;
  getAudio: () => CallAudioStreams;
}) {
  const { active, muted, onHold, lang, getAudio } = opts;
  const [lines, setLines] = useState<TranscriptLine[]>([]);
  const [interim, setInterim] = useState('');
  const [status, setStatus] = useState<'idle' | 'live' | 'blocked' | 'unsupported'>('idle');
  const [callerHint, setCallerHint] = useState('');
  const mrsRef = useRef<MediaRecorder[]>([]);
  const clonesRef = useRef<MediaStream[]>([]);
  const callerOffRef = useRef(false);
  const listRef = useRef<HTMLDivElement | null>(null);
  const wasActiveRef = useRef(false);
  const mutedRef = useRef(muted);
  mutedRef.current = muted;

  const pushLine = useCallback((speaker: 'you' | 'caller', text: string) => {
    const t = text.replace(/\s+/g, ' ').trim();
    if (!t) return;
    setLines((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.speaker === speaker && Date.now() - last.at < 3500) {
        return prev.map((row, i) =>
          i === prev.length - 1 ? { ...row, text: `${row.text} ${t}`.trim(), at: Date.now() } : row,
        );
      }
      return [...prev, { id: `t${++lineSeq}`, speaker, text: t, at: Date.now() }].slice(-80);
    });
  }, []);

  const stopAll = useCallback(() => {
    for (const mr of mrsRef.current) {
      try {
        if (mr.state !== 'inactive') mr.stop();
      } catch {
        /* ignore */
      }
    }
    mrsRef.current = [];
    for (const s of clonesRef.current) {
      s.getTracks().forEach((t) => {
        try {
          t.stop();
        } catch {
          /* ignore */
        }
      });
    }
    clonesRef.current = [];
  }, []);

  const startChunk = useCallback(
    (stream: MediaStream | null, speaker: 'you' | 'caller') => {
      const cloned = cloneAudio(stream);
      if (!cloned) return false;
      if (speaker === 'you' && mutedRef.current) {
        cloned.getTracks().forEach((t) => t.stop());
        return false;
      }
      const mime = pickRecorderMime();
      let mr: MediaRecorder;
      try {
        mr = mime ? new MediaRecorder(cloned, { mimeType: mime }) : new MediaRecorder(cloned);
      } catch {
        cloned.getTracks().forEach((t) => t.stop());
        return false;
      }
      clonesRef.current.push(cloned);
      mrsRef.current.push(mr);
      mr.ondataavailable = (ev) => {
        if (!ev.data || ev.data.size < 800 || callerOffRef.current) return;
        transcribeLiveChunk(ev.data, lang)
          .then((text) => {
            if (text) {
              pushLine(speaker, text);
              setCallerHint('');
            }
          })
          .catch((e: Error) => {
            const msg = String(e?.message || e);
            if (/too short|empty transcript/i.test(msg)) return;
            if (msg.includes('ai_off')) {
              setCallerHint('Caption AI is off on the server.');
              return;
            }
            setCallerHint(`Caption service: ${msg.slice(0, 140)}`);
          });
      };
      try {
        mr.start(2000);
        return true;
      } catch {
        return false;
      }
    },
    [lang, pushLine],
  );

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [lines, interim]);

  useEffect(() => {
    if (active && !wasActiveRef.current) {
      setLines([]);
      setInterim('');
      setCallerHint('');
      callerOffRef.current = false;
    }
    if (!active) {
      wasActiveRef.current = false;
      stopAll();
      setStatus('idle');
      setInterim('');
      return;
    }
    wasActiveRef.current = true;
    if (onHold) {
      stopAll();
      setStatus('idle');
      setInterim('');
      return;
    }

    let cancelled = false;
    const attach = async () => {
      for (let i = 0; i < 40 && !cancelled; i++) {
        const { local, remote } = getAudio();
        const have =
          (local?.getAudioTracks().some((t) => t.readyState === 'live') ? 1 : 0) +
          (remote?.getAudioTracks().some((t) => t.readyState === 'live') ? 1 : 0);
        if (have > 0) {
          stopAll();
          const gotYou = startChunk(local, 'you');
          const gotCaller = startChunk(remote, 'caller');
          if (gotYou || gotCaller) {
            setStatus('live');
            setCallerHint(
              gotYou && gotCaller
                ? isAmharic(lang)
                  ? 'Both sides on Whisper (አማርኛ). You + Caller. A few seconds delay.'
                  : 'Both sides on Whisper. You + Caller. A few seconds delay.'
                : gotCaller
                  ? 'Caller audio on. Waiting for your mic track…'
                  : 'Your mic on. Waiting for the other side’s audio…',
            );
            return;
          }
        }
        await sleep(400);
      }
      if (!cancelled) {
        setStatus(typeof MediaRecorder === 'undefined' ? 'unsupported' : 'blocked');
        setCallerHint('Waiting for call audio… captions start once the stream is up.');
      }
    };
    void attach();

    return () => {
      cancelled = true;
      stopAll();
    };
  }, [active, muted, onHold, lang, getAudio, startChunk, stopAll]);

  const [needGesture, setNeedGesture] = useState(false);

  const startSpeech = useCallback(() => {
    setCallerHint('Restarting both-side captions from the call audio…');
    stopAll();
    const { local, remote } = getAudio();
    const gotYou = startChunk(local, 'you');
    const gotCaller = startChunk(remote, 'caller');
    if (gotYou || gotCaller) {
      setStatus('live');
      setCallerHint(
        gotYou && gotCaller
          ? 'Both sides on Whisper. You + Caller.'
          : gotCaller
            ? 'Caller audio on. Your mic track is missing.'
            : 'Your mic on. Other side’s audio is missing.',
      );
    } else {
      setNeedGesture(true);
      setCallerHint('No call audio yet. Stay on the live call, then click Start captions.');
    }
  }, [getAudio, startChunk, stopAll]);

  return {
    lines,
    interim,
    status,
    callerHint,
    needGesture,
    startSpeech,
    listRef,
  };
}
