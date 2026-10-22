/** ICE / SDP helpers mirrored from the working agent dashboard softphone. */

import type { Session } from 'sip.js';
import { Web } from 'sip.js';

export const ICE_GATHERING_TIMEOUT_MS = 8000;

export const ICE_PC_CONFIG: RTCConfiguration = {
  iceServers: [
    { urls: 'stun:stun.cloudflare.com:3478' },
    { urls: 'stun:stun.l.google.com:19302' },
  ],
};

export const MIC_CONSTRAINTS: MediaStreamConstraints = {
  audio: true,
  video: false,
};

/**
 * MediaStream factory that wraps getUserMedia through WebAudio proxy streams
 * so startLocalConference / joinWith can mix legs.
 */
const baseMediaStreamFactory = Web.defaultMediaStreamFactory();

export function webAudioMediaStreamFactory(
  constraints: MediaStreamConstraints,
  sdh: unknown,
): Promise<MediaStream> {
  return baseMediaStreamFactory(constraints).then((stream) => {
    if (sdh instanceof Web.WebAudioSessionDescriptionHandler) {
      return sdh.initLocalMediaStream(stream);
    }
    return stream;
  });
}

/** SessionDescriptionHandlerFactory that creates WebAudio handlers (required for 3-way). */
export function webAudioSessionDescriptionHandlerFactory(
  session: Session,
  options?: Web.SessionDescriptionHandlerFactoryOptions,
): Web.WebAudioSessionDescriptionHandler {
  const iceGatheringTimeout =
    options?.iceGatheringTimeout !== undefined ? options.iceGatheringTimeout : 5000;
  const sessionDescriptionHandlerConfiguration = {
    iceGatheringTimeout,
    peerConnectionConfiguration: {
      ...Web.defaultPeerConnectionConfiguration(),
      ...options?.peerConnectionConfiguration,
    },
  };
  const logger = session.userAgent.getLogger('sip.SessionDescriptionHandler');
  return new Web.WebAudioSessionDescriptionHandler(
    logger,
    webAudioMediaStreamFactory as Web.MediaStreamFactory,
    sessionDescriptionHandlerConfiguration,
  );
}

function isVirtualHostIp(ip: string): boolean {
  const p = ip.split('.').map(Number);
  if (p.length !== 4 || p.some((n) => Number.isNaN(n))) return false;
  if (p[0] === 169 && p[1] === 254) return true;
  if (p[0] === 172 && p[1] >= 16 && p[1] <= 31) return true;
  if (
    p[0] === 192 &&
    p[1] === 168 &&
    [56, 59, 137, 211, 215, 221, 243].includes(p[2])
  ) {
    return true;
  }
  return false;
}

export function stripVirtualNicModifier(description: RTCSessionDescriptionInit) {
  if (!description?.sdp) return Promise.resolve(description);
  const lines = description.sdp.split(/\r?\n/);
  const kept = lines.filter((line) => {
    if (!line.startsWith('a=candidate:')) return true;
    if (/\stcp\s/.test(line)) return false;
    const m = line.match(/\s(\d{1,3}(?:\.\d{1,3}){3})\s/);
    if (m && isVirtualHostIp(m[1])) return false;
    return true;
  });
  if (!kept.some((line) => line.startsWith('a=candidate:'))) {
    return Promise.resolve(description);
  }
  description.sdp = kept.join('\r\n');
  if (!/\r\n$/.test(description.sdp)) description.sdp += '\r\n';
  return Promise.resolve(description);
}

export function opusMonoFmtpModifier(description: RTCSessionDescriptionInit) {
  if (!description?.sdp) return Promise.resolve(description);
  description.sdp = description.sdp.replace(
    /^a=fmtp:(\d+) (.*)$/gm,
    (_line, pt: string, params: string) => {
      if (!/minptime|useinbandfec|stereo/.test(params)) return `a=fmtp:${pt} ${params}`;
      if (/stereo=/.test(params)) {
        params = params
          .replace(/sprop-stereo=\d+/g, 'sprop-stereo=0')
          .replace(/stereo=\d+/g, 'stereo=0');
        if (!/sprop-stereo=/.test(params)) params += ';sprop-stereo=0';
        if (!/(^|;)stereo=/.test(params)) params += ';stereo=0';
        return `a=fmtp:${pt} ${params}`;
      }
      return `a=fmtp:${pt} ${params};stereo=0;sprop-stereo=0`;
    },
  );
  return Promise.resolve(description);
}

export const SDP_MODIFIERS = [stripVirtualNicModifier, opusMonoFmtpModifier];
