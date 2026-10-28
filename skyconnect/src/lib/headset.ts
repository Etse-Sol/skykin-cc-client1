const MIC_KEY = 'skyconnect_headset_mic';
const SPK_KEY = 'skyconnect_headset_spk';

export type AudioDevice = { id: string; label: string };

function read(key: string): string {
  try {
    return localStorage.getItem(key) || '';
  } catch {
    return '';
  }
}

export function getMicDeviceId(): string {
  return read(MIC_KEY);
}

export function getSpeakerDeviceId(): string {
  return read(SPK_KEY);
}

export function saveHeadsetDevices(micId: string, speakerId: string) {
  try {
    if (micId) localStorage.setItem(MIC_KEY, micId);
    else localStorage.removeItem(MIC_KEY);
    if (speakerId) localStorage.setItem(SPK_KEY, speakerId);
    else localStorage.removeItem(SPK_KEY);
  } catch {
    /* ignore */
  }
}

export function micConstraints(): MediaStreamConstraints {
  const id = getMicDeviceId();
  return {
    audio: id
      ? {
          deviceId: { ideal: id },
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      : { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    video: false,
  };
}

export async function listAudioDevices(): Promise<{ mics: AudioDevice[]; speakers: AudioDevice[] }> {
  if (!navigator.mediaDevices?.enumerateDevices) return { mics: [], speakers: [] };
  try {
    await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
  } catch {
    /* labels may be empty without permission */
  }
  const all = await navigator.mediaDevices.enumerateDevices();
  const mics = all
    .filter((d) => d.kind === 'audioinput')
    .map((d, i) => ({ id: d.deviceId, label: d.label || `Microphone ${i + 1}` }));
  const speakers = all
    .filter((d) => d.kind === 'audiooutput')
    .map((d, i) => ({ id: d.deviceId, label: d.label || `Speaker ${i + 1}` }));
  return { mics, speakers };
}

export async function applySpeakerSink(el: HTMLMediaElement | null) {
  if (!el) return;
  const id = getSpeakerDeviceId();
  const setSink = (el as HTMLMediaElement & { setSinkId?: (sinkId: string) => Promise<void> }).setSinkId;
  if (!id || typeof setSink !== 'function') return;
  try {
    await setSink.call(el, id);
  } catch {
    /* headset unplugged */
  }
}

export async function applyAudioContextSink(ctx: AudioContext | null) {
  if (!ctx) return;
  const id = getSpeakerDeviceId();
  const setSink = (ctx as AudioContext & { setSinkId?: (id: string) => Promise<void> }).setSinkId;
  if (!id || typeof setSink !== 'function') return;
  try {
    await setSink.call(ctx, id);
  } catch {
    /* ignore */
  }
}

type HidNav = {
  hid?: {
    requestDevice: (opts: { filters: Array<{ usagePage?: number; vendorId?: number }> }) => Promise<HidDev[]>;
    getDevices?: () => Promise<HidDev[]>;
  };
};

type HidDev = {
  opened: boolean;
  productName?: string;
  open: () => Promise<void>;
  close?: () => Promise<void>;
  addEventListener: (type: 'inputreport', fn: (ev: { data: DataView }) => void) => void;
  removeEventListener: (type: 'inputreport', fn: (ev: { data: DataView }) => void) => void;
};

export type HeadsetCallActions = {
  ringing: () => boolean;
  inCall: () => boolean;
  answer: () => void;
  hangup: () => void;
  toggleMute: () => void;
};

let liveActions: HeadsetCallActions | null = null;

function act(): HeadsetCallActions | null {
  return liveActions;
}

/** Media keys + USB telephony HID (hook switch / mute). Requires a click for HID permission. */
export function bindHeadsetButtons(actions: HeadsetCallActions): () => void {
  liveActions = actions;
  const onKey = (e: KeyboardEvent) => {
    const code = e.code;
    if (code === 'MediaPlayPause' || code === 'MediaTrackNext') {
      const a = act();
      if (a?.ringing()) {
        e.preventDefault();
        a.answer();
      }
      return;
    }
    if (code === 'MediaStop') {
      const a = act();
      if (a && (a.inCall() || a.ringing())) {
        e.preventDefault();
        a.hangup();
      }
      return;
    }
    if (code === 'MicrophoneMuteToggle') {
      const a = act();
      if (a?.inCall()) {
        e.preventDefault();
        a.toggleMute();
      }
    }
  };
  window.addEventListener('keydown', onKey);

  const ms = navigator.mediaSession;
  if (ms?.setActionHandler) {
    try {
      ms.setActionHandler('hangup', () => act()?.hangup());
    } catch {
      /* not supported */
    }
    try {
      ms.setActionHandler('togglemicrophone' as MediaSessionAction, () => act()?.toggleMute());
    } catch {
      /* not supported */
    }
    try {
      ms.setActionHandler('pause', () => {
        const a = act();
        if (a?.inCall()) a.toggleMute();
      });
    } catch {
      /* ignore */
    }
    try {
      ms.setActionHandler('play', () => {
        const a = act();
        if (a?.ringing()) a.answer();
      });
    } catch {
      /* ignore */
    }
  }

  return () => {
    window.removeEventListener('keydown', onKey);
    if (!ms?.setActionHandler) return;
    ['hangup', 'togglemicrophone', 'pause', 'play'].forEach((a) => {
      try {
        ms.setActionHandler(a as MediaSessionAction, null);
      } catch {
        /* ignore */
      }
    });
  };
}

let hidListener: ((ev: { data: DataView }) => void) | null = null;
let hidDev: HidDev | null = null;

export async function enableHeadsetHid(): Promise<string> {
  const hid = (navigator as unknown as HidNav).hid;
  if (!hid) throw new Error('This browser does not allow USB headset buttons (use Chrome/Edge).');
  const picked = await hid.requestDevice({
    filters: [
      { usagePage: 0x0b },
      { vendorId: 0x0b0e },
      { vendorId: 0x047f },
      { vendorId: 0x0557 },
      { vendorId: 0x046d },
    ],
  });
  const device = picked[0];
  if (!device) throw new Error('No headset selected');
  if (!device.opened) await device.open();
  if (hidListener && hidDev) {
    hidDev.removeEventListener('inputreport', hidListener);
  }
  hidListener = (ev) => {
    const a = act();
    if (!a) return;
    const bytes = new Uint8Array(ev.data.buffer);
    const v = bytes[0] || 0;
    if (v & 0x01) {
      if (a.ringing()) a.answer();
      return;
    }
    if (v & 0x02) {
      if (a.inCall()) a.toggleMute();
      return;
    }
    if (v === 0 && a.inCall()) a.hangup();
  };
  device.addEventListener('inputreport', hidListener);
  hidDev = device;
  return device.productName || 'Headset';
}
