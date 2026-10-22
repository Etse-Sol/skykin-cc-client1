/**
 * Local telephony tones (same cadence as legacy agent dashboard).
 * Inbound: ringtone while agent phone rings.
 * Outbound: PSTN ringback while waiting for answer (WebRTC early media is often silent).
 */

let ringCtx: AudioContext | null = null;
let ringInterval: number | null = null;

let rbCtx: AudioContext | null = null;
let rbInterval: number | null = null;
let rbMode: '' | 'ring' | 'busy' | 'cong' = '';

function ensureCtx(existing: AudioContext | null): AudioContext | null {
  if (existing && existing.state !== 'closed') {
    if (existing.state === 'suspended') existing.resume().catch(() => {});
    return existing;
  }
  try {
    const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const ctx = new Ctx();
    if (ctx.state === 'suspended') ctx.resume().catch(() => {});
    return ctx;
  } catch {
    return null;
  }
}

function playDualTone(
  ctx: AudioContext,
  freqs: number[],
  durationSec: number,
  gainVal = 0.18,
) {
  const t0 = ctx.currentTime;
  const g = ctx.createGain();
  g.connect(ctx.destination);
  g.gain.setValueAtTime(0.0001, t0);
  g.gain.exponentialRampToValueAtTime(gainVal, t0 + 0.02);
  g.gain.setValueAtTime(gainVal, t0 + Math.max(0.05, durationSec - 0.04));
  g.gain.exponentialRampToValueAtTime(0.0001, t0 + durationSec);
  freqs.forEach((hz) => {
    try {
      const o = ctx.createOscillator();
      o.type = 'sine';
      o.frequency.value = hz;
      o.connect(g);
      o.start(t0);
      o.stop(t0 + durationSec + 0.02);
    } catch {
      /* ignore */
    }
  });
}

/** Inbound: two short beeps every 2.5s while the agent’s line is ringing. */
export function startRingtone() {
  stopRingtone();
  ringCtx = ensureCtx(null);
  if (!ringCtx) return;
  const ctx = ringCtx;
  const beep = () => {
    if (!ringCtx) return;
    try {
      [0, 0.15].forEach((offset) => {
        const o = ctx.createOscillator();
        const g = ctx.createGain();
        o.connect(g);
        g.connect(ctx.destination);
        o.type = 'sine';
        o.frequency.value = 440;
        g.gain.setValueAtTime(0.4, ctx.currentTime + offset);
        g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + offset + 0.12);
        o.start(ctx.currentTime + offset);
        o.stop(ctx.currentTime + offset + 0.13);
      });
    } catch {
      /* ignore */
    }
  };
  beep();
  ringInterval = window.setInterval(beep, 2500);
}

export function stopRingtone() {
  if (ringInterval) {
    clearInterval(ringInterval);
    ringInterval = null;
  }
  if (ringCtx) {
    try {
      ringCtx.close();
    } catch {
      /* ignore */
    }
    ringCtx = null;
  }
}

function ensureRingbackCtx(): AudioContext | null {
  rbCtx = ensureCtx(rbCtx);
  return rbCtx;
}

export function stopRingback() {
  if (rbInterval) {
    clearInterval(rbInterval);
    rbInterval = null;
  }
  rbMode = '';
}

/** Classic PSTN ringback: 2s dual-tone (440+480), 4s silence. */
export function startRingback() {
  if (rbMode === 'ring' && rbInterval) return;
  stopRingback();
  const ctx = ensureRingbackCtx();
  if (!ctx) return;
  rbMode = 'ring';
  const pulse = () => {
    if (rbMode !== 'ring' || !rbCtx) return;
    try {
      if (rbCtx.state === 'suspended') rbCtx.resume();
    } catch {
      /* ignore */
    }
    playDualTone(rbCtx, [440, 480], 2.0, 0.32);
  };
  pulse();
  rbInterval = window.setInterval(pulse, 6000);
}

export function startBusyTone() {
  stopRingback();
  if (!ensureRingbackCtx() || !rbCtx) return;
  rbMode = 'busy';
  const pulse = () => {
    if (rbMode !== 'busy' || !rbCtx) return;
    playDualTone(rbCtx, [480, 620], 0.45, 0.2);
  };
  pulse();
  rbInterval = window.setInterval(pulse, 1000);
  window.setTimeout(() => {
    if (rbMode === 'busy') stopAllCallTones();
  }, 3500);
}

export function startCongestionTone() {
  stopRingback();
  if (!ensureRingbackCtx() || !rbCtx) return;
  rbMode = 'cong';
  const pulse = () => {
    if (rbMode !== 'cong' || !rbCtx) return;
    playDualTone(rbCtx, [480, 620], 0.25, 0.18);
  };
  pulse();
  rbInterval = window.setInterval(pulse, 500);
  window.setTimeout(() => {
    if (rbMode === 'cong') stopAllCallTones();
  }, 3000);
}

export function stopAllCallTones() {
  stopRingtone();
  stopRingback();
  if (rbCtx) {
    try {
      rbCtx.close();
    } catch {
      /* ignore */
    }
    rbCtx = null;
  }
}

export function playOutboundFailTone(label: string) {
  const L = String(label || '').toLowerCase();
  if (L.includes('busy') || L.includes('declined') || L.includes('reject')) {
    startBusyTone();
  } else if (L.includes('cancel')) {
    stopAllCallTones();
  } else {
    startCongestionTone();
  }
}
