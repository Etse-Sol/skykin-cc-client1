import { useEffect, useState } from 'react';
import {
  enableHeadsetHid,
  getMicDeviceId,
  getSpeakerDeviceId,
  listAudioDevices,
  saveHeadsetDevices,
  type AudioDevice,
} from '../lib/headset';
import { useSoftphone } from '../softphone/SoftphoneContext';

export default function HeadsetPicker() {
  const phone = useSoftphone();
  const [mics, setMics] = useState<AudioDevice[]>([]);
  const [speakers, setSpeakers] = useState<AudioDevice[]>([]);
  const [mic, setMic] = useState(getMicDeviceId);
  const [spk, setSpk] = useState(getSpeakerDeviceId);
  const [hidNote, setHidNote] = useState('');

  const refresh = () => {
    void listAudioDevices().then((d) => {
      setMics(d.mics);
      setSpeakers(d.speakers);
    });
  };

  useEffect(() => {
    refresh();
    navigator.mediaDevices?.addEventListener?.('devicechange', refresh);
    return () => navigator.mediaDevices?.removeEventListener?.('devicechange', refresh);
  }, []);

  const persist = (nextMic: string, nextSpk: string) => {
    setMic(nextMic);
    setSpk(nextSpk);
    saveHeadsetDevices(nextMic, nextSpk);
    phone.applyHeadsetAudio();
  };

  return (
    <div className="flex flex-wrap items-center gap-2 text-[11px]">
      <label className="font-bold text-[var(--color-sc-muted)]">
        Headset mic
        <select
          className="ml-1 max-w-[180px] rounded-md border border-[var(--color-sc-line)] bg-white px-1.5 py-1 font-semibold"
          value={mic}
          onChange={(e) => persist(e.target.value, spk)}
        >
          <option value="">System default</option>
          {mics.map((d) => (
            <option key={d.id} value={d.id}>
              {d.label}
            </option>
          ))}
        </select>
      </label>
      <label className="font-bold text-[var(--color-sc-muted)]">
        Earpiece
        <select
          className="ml-1 max-w-[180px] rounded-md border border-[var(--color-sc-line)] bg-white px-1.5 py-1 font-semibold"
          value={spk}
          onChange={(e) => persist(mic, e.target.value)}
        >
          <option value="">System default</option>
          {speakers.map((d) => (
            <option key={d.id} value={d.id}>
              {d.label}
            </option>
          ))}
        </select>
      </label>
      <button
        type="button"
        className="sc-b2"
        onClick={() => {
          void enableHeadsetHid()
            .then((name) => setHidNote(`Buttons: ${name}`))
            .catch((e) => setHidNote(e instanceof Error ? e.message : 'Headset buttons failed'));
        }}
      >
        Headset buttons
      </button>
      {hidNote ? <span className="text-[var(--color-sc-forest)]">{hidNote}</span> : null}
    </div>
  );
}
