import { useCallback, useEffect, useRef, useState } from 'react';
import CallsTabs from '../../components/CallsTabs';
import { useSoftphone } from '../../softphone/SoftphoneContext';
import { fetchAgentSession } from '../../services/session';
import { fetchCallHistory, localDayISO, type HistoryRow } from '../../services/callHistory';

function todayISO() {
  return localDayISO();
}

export default function CallHistory() {
  const phone = useSoftphone();
  const [from, setFrom] = useState(todayISO);
  const [to, setTo] = useState(todayISO);
  const [rows, setRows] = useState<HistoryRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [source, setSource] = useState('');
  const [playing, setPlaying] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const prevPhase = useRef(phone.phase);

  const load = useCallback(
    async (f: string, t: string) => {
      setLoading(true);
      setError('');
      try {
        const session = await fetchAgentSession();
        const data = await fetchCallHistory({
          from: f,
          to: t,
          domain: session.domain || phone.creds.domain,
          ext: phone.creds.extension || session.extension,
        });
        setRows(data.calls || []);
        setSource(data.source || 'php');
        if (data.error) setError(data.error);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load');
        setRows([]);
        setSource('');
      } finally {
        setLoading(false);
      }
    },
    [phone.creds.domain, phone.creds.extension],
  );

  useEffect(() => {
    load(from, to);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps — initial

  // After a live call ends, poll history (XML CDR can lag; ESL is faster)
  useEffect(() => {
    const wasLive =
      prevPhase.current === 'in_call' ||
      prevPhase.current === 'calling' ||
      prevPhase.current === 'ringing';
    const nowIdle =
      phone.phase === 'registered' || phone.phase === 'idle' || phone.phase === 'failed';
    if (wasLive && nowIdle) {
      window.setTimeout(() => load(from, to), 2000);
      window.setTimeout(() => load(from, to), 6000);
      window.setTimeout(() => load(from, to), 12000);
    }
    prevPhase.current = phone.phase;
  }, [phone.phase, from, to, load]);

  useEffect(() => {
    const onVis = () => {
      if (document.visibilityState === 'visible') load(from, to);
    };
    document.addEventListener('visibilitychange', onVis);
    return () => document.removeEventListener('visibilitychange', onVis);
  }, [from, to, load]);

  const statusTone = (s: string) => {
    if (s === 'Answered') return 'text-[var(--color-sc-green)]';
    if (s === 'Abandoned' || s === 'Missed' || s === 'Agent Busy') return 'text-[#D9534F]';
    if (s === 'Busy' || s === 'Declined' || s === 'No Answer' || s === 'Call cancelled') {
      return 'text-[var(--color-sc-warn)]';
    }
    return 'text-[var(--color-sc-muted)]';
  };

  const togglePlay = (url: string) => {
    if (!url) return;
    if (playing === url && audioRef.current) {
      audioRef.current.pause();
      setPlaying(null);
      return;
    }
    if (!audioRef.current) {
      audioRef.current = new Audio();
      audioRef.current.addEventListener('ended', () => setPlaying(null));
    }
    audioRef.current.src = url;
    audioRef.current.play().catch(() => setPlaying(null));
    setPlaying(url);
  };

  return (
    <div>
      <CallsTabs />

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <label className="text-sm">
          <span className="mb-1 block text-xs font-semibold text-[var(--color-sc-muted)]">From</span>
          <input
            type="date"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            className="rounded-lg border border-[var(--color-sc-line)] px-3 py-2 text-sm"
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-xs font-semibold text-[var(--color-sc-muted)]">To</span>
          <input
            type="date"
            value={to}
            onChange={(e) => setTo(e.target.value)}
            className="rounded-lg border border-[var(--color-sc-line)] px-3 py-2 text-sm"
          />
        </label>
        <button
          type="button"
          onClick={() => load(from, to)}
          className="rounded-lg bg-[var(--color-sc-green)] px-4 py-2 text-sm font-bold text-white"
        >
          Filter
        </button>
        <button
          type="button"
          onClick={() => {
            const t = todayISO();
            setFrom(t);
            setTo(t);
            load(t, t);
          }}
          className="rounded-lg border border-[var(--color-sc-line)] bg-white px-4 py-2 text-sm font-semibold text-[var(--color-sc-forest)]"
        >
          Today
        </button>
        <span className="text-xs text-[var(--color-sc-muted)]">
          {loading ? 'Loading…' : `${rows.length} calls`}
          {source ? ` · ${source}` : ''}
          {phone.creds.extension ? ` · ext ${phone.creds.extension}` : ''}
        </span>
      </div>

      {error ? (
        <div className="mb-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          {error}
        </div>
      ) : null}

      <div className="overflow-hidden rounded-xl border border-[var(--color-sc-line)] bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-[var(--color-sc-soft)] text-[11px] font-semibold uppercase tracking-wide text-[var(--color-sc-muted)]">
            <tr>
              <th className="px-4 py-3">Date &amp; Time</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Number</th>
              <th className="px-4 py-3">Duration</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Disposition</th>
              <th className="px-4 py-3">Voice</th>
            </tr>
          </thead>
          <tbody>
            {!loading && rows.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-[var(--color-sc-muted)]">
                  No calls for ext {phone.creds.extension || '—'} in this range.
                  Wait a few seconds after hangup, then click Filter.
                </td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr
                  key={`${r.time}-${r.number}-${r.disposition}-${r.record_name || ''}`}
                  className="border-t border-[var(--color-sc-line)]"
                >
                  <td className="px-4 py-3 font-mono text-xs">{r.time}</td>
                  <td className="px-4 py-3">{r.type}</td>
                  <td className="px-4 py-3 font-semibold">{r.number}</td>
                  <td className="px-4 py-3 font-mono text-xs">{r.duration}</td>
                  <td className={`px-4 py-3 font-semibold ${statusTone(r.status)}`}>{r.status}</td>
                  <td className="px-4 py-3 text-[var(--color-sc-muted)]">{r.disposition}</td>
                  <td className="px-4 py-3">
                    {r.recording ? (
                      <button
                        type="button"
                        onClick={() => togglePlay(r.recording!)}
                        className="rounded-lg bg-[var(--color-sc-forest)] px-3 py-1 text-xs font-bold text-white"
                      >
                        {playing === r.recording ? 'Stop' : 'Play'}
                      </button>
                    ) : (
                      <span className="text-xs text-[var(--color-sc-muted)]">—</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
