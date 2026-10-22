import { useCallback, useEffect, useMemo, useState } from 'react';
import { fetchAgentSession } from '../../services/session';
import {
  fetchSupAgents,
  fmtSec,
  monitorAgent,
  statusLabel,
  type SupAgent,
} from '../../services/supervisorApi';
import { useSoftphone } from '../../softphone/SoftphoneContext';

export default function AiLiveFloor() {
  const phone = useSoftphone();
  const [agents, setAgents] = useState<SupAgent[]>([]);
  const [domain, setDomain] = useState('');
  const [msg, setMsg] = useState('');
  const [note, setNote] = useState('');
  const [sel, setSel] = useState('');
  const [q, setQ] = useState('');
  const [view, setView] = useState<'cards' | 'table'>('cards');

  const load = useCallback(async () => {
    const s = await fetchAgentSession();
    setDomain(s.domain);
    setAgents(await fetchSupAgents(s.domain));
  }, []);

  useEffect(() => {
    load().catch(() => {});
    const t = window.setInterval(() => load().catch(() => {}), 8000);
    return () => window.clearInterval(t);
  }, [load]);

  const live = agents.filter((a) => (a.call_duration || 0) > 0 || a.on_call_with);
  const alerts = agents.filter((a) => !a.registered).length;
  const picked = live.find((a) => a.ext === sel) || live[0];
  const needle = q.trim().toLowerCase();
  const shown = useMemo(
    () =>
      live.filter((a) => {
        if (!needle) return true;
        return `${a.name} ${a.ext} ${a.on_call_with || ''}`.toLowerCase().includes(needle);
      }),
    [live, needle],
  );

  const run = async (mode: 'listen' | 'whisper' | 'barge') => {
    if (!picked) return;
    const sup = phone.creds.extension;
    if (!sup) {
      setMsg('Supervisor SIP missing');
      return;
    }
    const r = await monitorAgent({ mode, agentExt: picked.ext, supExt: sup, domain });
    setMsg(r.ok ? `${mode} ${picked.ext}` : r.error || 'Failed');
  };

  return (
    <div className="flex flex-col gap-[18px]">
      <div className="grid gap-3 sm:grid-cols-4">
        {[
          ['LIVE CONTACTS', String(live.length)],
          ['AVERAGE SENTIMENT NOW', '—'],
          ['OPEN ALERTS', String(alerts)],
          ['ALERTS NOT PICKED UP', String(alerts)],
        ].map(([k, v]) => (
          <div key={k} className="sc-card">
            <p className="text-[11px] font-bold tracking-wide text-[var(--color-sc-muted)]">{k}</p>
            <p className="mt-1 text-[26px] font-extrabold tabular-nums">{v}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="sc-chip sc-chip-call">Live {live.length}</span>
        <span className="sc-chip sc-chip-ready">SIP down {alerts}</span>
        <button type="button" className={`sc-chip ${view === 'table' ? 'sc-chip-call' : 'sc-chip-ready'}`} onClick={() => setView('table')}>
          Table
        </button>
        <button type="button" className={`sc-chip ${view === 'cards' ? 'sc-chip-call' : 'sc-chip-ready'}`} onClick={() => setView('cards')}>
          Cards
        </button>
        <input
          className="sc-input min-w-[220px] flex-1"
          placeholder="Search agent, caller, queue"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>
      {msg ? <p className="text-sm font-bold">{msg}</p> : null}

      <div className="flex flex-wrap items-start gap-4">
        <div className="flex min-w-0 flex-[2_1_460px] flex-wrap gap-4">
          {shown.length === 0 ? <p className="sc-meta">No live contacts right now.</p> : null}
          {view === 'cards'
            ? shown.map((a) => (
                <button
                  key={a.ext}
                  type="button"
                  onClick={() => setSel(a.ext)}
                  className={`sc-card flex-[1_1_220px] text-left ${picked?.ext === a.ext ? 'ring-1 ring-[var(--color-sc-green)]' : ''} ${
                    !a.registered ? 'border-[var(--color-sc-warn)]' : ''
                  }`}
                >
                  <div className="flex justify-between gap-2">
                    <b>
                      {a.name || a.ext} · {a.ext}
                    </b>
                    <span className="sc-meta tabular-nums">{fmtSec(a.call_duration || 0)}</span>
                  </div>
                  <p className="sc-meta mt-1">
                    {a.on_call_with || '—'} · {statusLabel(a)}
                  </p>
                  <div className="my-2.5 flex h-2.5 overflow-hidden rounded-md bg-[#E8EDE9]">
                    <div className="bg-[var(--color-sc-green)]" style={{ width: `${Math.min(90, 20 + (a.call_duration || 0) / 4)}%` }} />
                  </div>
                  <p className="text-[13px]">
                    <b>Customer</b> {a.on_call_with ? `Connected ${a.on_call_with}` : 'Waiting for audio'}
                  </p>
                </button>
              ))
            : (
              <table className="w-full text-sm">
                <tbody>
                  {shown.map((a) => (
                    <tr key={a.ext} className="border-t border-[var(--color-sc-line)]">
                      <td className="py-2 font-bold">
                        {a.name} · {a.ext}
                      </td>
                      <td>{a.on_call_with}</td>
                      <td>{fmtSec(a.call_duration || 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
        </div>

        <aside className="sc-card min-w-[280px] flex-[1_1_320px]">
          {picked ? (
            <>
              <div className="flex justify-between gap-2">
                <b className="text-[17px]">
                  {picked.name} · {picked.ext}
                </b>
                <span className="sc-meta">{statusLabel(picked)}</span>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button type="button" className="sc-b2" onClick={() => void run('listen')}>
                  Observe
                </button>
                <button type="button" className="sc-b2" onClick={() => void run('whisper')}>
                  Whisper
                </button>
                <button type="button" className="sc-b2" onClick={() => void run('barge')}>
                  Barge in
                </button>
              </div>
              <div className="mt-3 flex gap-2">
                <input className="sc-input flex-1" placeholder="Note (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
                <button type="button" className="sc-btn whitespace-nowrap" onClick={() => setMsg(note ? `Noted: ${note}` : 'I have got this')}>
                  I have got this
                </button>
              </div>
              <div className="mt-4">
                <p className="text-[11px] font-bold uppercase tracking-wide text-[var(--color-sc-muted)]">Live summary</p>
                <p className="mt-2 text-sm">
                  {picked.on_call_with
                    ? `Live with ${picked.on_call_with} for ${fmtSec(picked.call_duration || 0)}. Observe / whisper / barge uses the supervisor softphone.`
                    : 'No customer leg yet.'}
                </p>
              </div>
              <div className="mt-4">
                <p className="text-[11px] font-bold uppercase tracking-wide text-[var(--color-sc-muted)]">Conversation</p>
                <div className="mt-2 flex h-2.5 overflow-hidden rounded-md bg-[#E8EDE9]">
                  <div className="w-[38%] bg-[#1F5F7A]" />
                  <div className="w-[52%] bg-[var(--color-sc-green)]" />
                  <div className="w-[10%] bg-[#B9C7BE]" />
                </div>
                <p className="sc-meta mt-1.5">Customer 38% · Agent 52% · Silence 10% (layout — STT when a transcript is available)</p>
              </div>
            </>
          ) : (
            <p className="sc-meta">Select a live contact</p>
          )}
        </aside>
      </div>
    </div>
  );
}
