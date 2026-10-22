import { useCallback, useEffect, useMemo, useState } from 'react';
import StatusPill from '../../components/StatusPill';
import { fetchAgentSession } from '../../services/session';
import {
  fetchEvalCalls,
  recUrl,
  saveEvaluation,
  todayRange,
  type EvalCall,
} from '../../services/ops';
import { fetchCallHistoryAll } from '../../services/supervisorApi';

const CRITERIA = [
  ['greeting', 'Greeting'],
  ['knowledge', 'Knowledge'],
  ['resolution', 'Resolution'],
  ['tone', 'Tone / empathy'],
  ['procedure', 'Procedure'],
  ['closing', 'Closing'],
] as const;

type Hist = {
  time?: string;
  caller?: string;
  destination?: string;
  agent?: string;
  direction?: string;
  duration?: string;
  status?: string;
  cause?: string;
};

function sentimentChip(status?: string, cause?: string) {
  const s = (status || '').toLowerCase();
  const c = (cause || '').toLowerCase();
  if (s.includes('abandon') || s.includes('miss')) return { label: 'negative', tone: 'warn' as const };
  if (c.includes('busy') || c.includes('cancel') || c.includes('no_answer')) {
    return { label: 'negative', tone: 'warn' as const };
  }
  if (s.includes('answer')) return { label: 'neutral', tone: 'idle' as const };
  return { label: s || '—', tone: 'idle' as const };
}

export default function Quality() {
  const [rows, setRows] = useState<Hist[]>([]);
  const [evals, setEvals] = useState<EvalCall[]>([]);
  const [sel, setSel] = useState<Hist | null>(null);
  const [q, setQ] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');
  const [from, setFrom] = useState(() => todayRange().from);
  const [to, setTo] = useState(() => todayRange().to);
  const [scores, setScores] = useState<Record<string, number>>({});
  const [notes, setNotes] = useState('');
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');

  const load = useCallback(async () => {
    const s = await fetchAgentSession();
    const [hist, ev] = await Promise.all([
      fetchCallHistoryAll(s.domain, from, to, q),
      fetchEvalCalls(s.domain, from, to).catch(() => [] as EvalCall[]),
    ]);
    setRows(hist as Hist[]);
    setEvals(ev);
    setErr('');
  }, [from, to, q]);

  useEffect(() => {
    load().catch((e) => setErr(e instanceof Error ? e.message : 'Could not load calls'));
  }, [load]);

  const shown = useMemo(() => {
    return rows.filter((r) => {
      if (statusFilter === 'All') return true;
      return (r.status || '').toLowerCase().includes(statusFilter.toLowerCase());
    });
  }, [rows, statusFilter]);

  useEffect(() => {
    if (!sel && shown[0]) setSel(shown[0]);
  }, [shown, sel]);

  const evalHit = useMemo(() => {
    if (!sel) return null;
    const caller = (sel.caller || '').replace(/\D/g, '').slice(-9);
    return (
      evals.find((e) => {
        const c = (e.caller_id_number || '').replace(/\D/g, '').slice(-9);
        const t = (e.call_time || '').slice(0, 16);
        const st = (sel.time || '').slice(0, 16);
        return (caller && c && caller === c) || (t && st && t === st);
      }) || null
    );
  }, [evals, sel]);

  const play = recUrl(evalHit?.record_name);

  const submit = async () => {
    if (!sel) return;
    setMsg('');
    try {
      const s = await fetchAgentSession();
      const payload: Record<string, unknown> = {
        cdr_uuid: evalHit?.cdr_uuid || `${sel.time}-${sel.caller}`,
        call_uuid: evalHit?.cdr_uuid || `${sel.time}-${sel.caller}`,
        agent_ext: sel.agent,
        caller_number: sel.caller,
        call_time: sel.time,
        duration: sel.duration,
        notes,
        domain: s.domain,
      };
      for (const [k] of CRITERIA) payload[`score_${k}`] = scores[k] || 0;
      const r = await saveEvaluation(payload);
      const n = Array.isArray(r.learning) ? r.learning.length : 0;
      setMsg(
        n
          ? `Saved ${r.grade || ''} ${r.pct || ''}% · ${n} learning course${n === 1 ? '' : 's'} assigned`
          : `Saved ${r.grade || ''} ${r.pct || ''}%`,
      );
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Save failed');
    }
  };

  const sent = sentimentChip(sel?.status, sel?.cause);
  const alertN = sent.tone === 'warn' ? 1 : 0;

  return (
    <div className="flex flex-col gap-[18px]">
      <h1 className="text-[22px] font-bold">Call review</h1>
      {err ? <p className="text-sm text-[var(--color-sc-warn)]">{err}</p> : null}

      <div className="flex flex-wrap items-start gap-4">
        <div className="sc-card min-w-0 flex-[2_1_520px]">
          <div className="flex flex-wrap items-end gap-3">
            <label className="min-w-[150px] flex-1 text-xs font-bold text-[var(--color-sc-muted)]">
              Search
              <input
                className="sc-input mt-1 w-full"
                placeholder="agent, caller, queue"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            </label>
            <label className="min-w-[150px] flex-1 text-xs font-bold text-[var(--color-sc-muted)]">
              Status
              <select
                className="sc-input mt-1 w-full"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                {['All', 'Answered', 'Abandoned', 'Missed'].map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </label>
            <label className="min-w-[130px] text-xs font-bold text-[var(--color-sc-muted)]">
              From
              <input className="sc-input mt-1" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
            </label>
            <label className="min-w-[130px] text-xs font-bold text-[var(--color-sc-muted)]">
              To
              <input className="sc-input mt-1" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
            </label>
          </div>

          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[700px] text-left text-sm">
              <thead className="text-[11px] uppercase text-[var(--color-sc-muted)]">
                <tr>
                  <th className="px-2 py-2">Ended</th>
                  <th className="px-2 py-2">Agent</th>
                  <th className="px-2 py-2">Customer</th>
                  <th className="px-2 py-2">Queue</th>
                  <th className="px-2 py-2 text-right">Duration</th>
                  <th className="px-2 py-2">Sentiment</th>
                  <th className="px-2 py-2 text-right">Alerts</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((r, i) => {
                  const chip = sentimentChip(r.status, r.cause);
                  const active =
                    sel &&
                    sel.time === r.time &&
                    sel.caller === r.caller &&
                    sel.agent === r.agent;
                  return (
                    <tr
                      key={`${r.time}-${r.caller}-${i}`}
                      className={`cursor-pointer border-t border-[var(--color-sc-line)] ${
                        active ? 'bg-[var(--color-sc-nav-active)]' : 'hover:bg-[var(--color-sc-soft)]'
                      }`}
                      onClick={() => {
                        setSel(r);
                        setScores({});
                        setNotes('');
                        setMsg('');
                      }}
                    >
                      <td className="px-2 py-2">{r.time || '—'}</td>
                      <td className="px-2 py-2">{r.agent || '—'}</td>
                      <td className="px-2 py-2">{r.caller || '—'}</td>
                      <td className="px-2 py-2">{r.destination || '—'}</td>
                      <td className="px-2 py-2 text-right font-bold tabular-nums">{r.duration || '—'}</td>
                      <td className="px-2 py-2">
                        <StatusPill label={chip.label} tone={chip.tone} />
                      </td>
                      <td className="px-2 py-2 text-right font-bold">{chip.tone === 'warn' ? 1 : '–'}</td>
                    </tr>
                  );
                })}
                {shown.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-2 py-6 text-[var(--color-sc-muted)]">
                      No calls in this range
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </div>

        <aside className="sc-card flex min-w-[280px] flex-[1_1_320px] flex-col gap-3">
          {sel ? (
            <>
              <b className="text-[17px]">
                Call summary · {sel.duration || '—'}
              </b>
              <div className="flex flex-wrap gap-2">
                <span className="sc-chip sc-chip-call">{sel.direction || 'call'}</span>
                <span className={`sc-chip ${sent.tone === 'warn' ? 'sc-chip-warn' : 'sc-chip-ready'}`}>
                  {sel.status || sent.label}
                </span>
              </div>
              <p className="text-sm">
                {sel.agent || 'Agent'} handled {sel.caller || 'the customer'} to {sel.destination || 'the queue'}.{' '}
                {sel.cause ? `Hangup: ${sel.cause}.` : ''}
              </p>
              {alertN ? (
                <p className="text-[13px]">
                  <b>Follow-up:</b> abandoned or missed — coach the agent on wrap-up and callback.
                </p>
              ) : (
                <p className="text-[13px]">
                  <b>Coaching:</b> score greeting, knowledge, and closing on the form below.
                </p>
              )}
              {play ? (
                <audio className="w-full" controls src={play}>
                  <track kind="captions" />
                </audio>
              ) : (
                <p className="sc-meta">Recording appears when the CDR has a file</p>
              )}
              {evalHit?.eval ? (
                <StatusPill label={`Grade ${evalHit.eval.grade}`} tone="ok" />
              ) : null}
              <p className="text-[11px] font-bold uppercase tracking-wide text-[var(--color-sc-muted)]">
                Evaluation
              </p>
              <ul className="space-y-2">
                {CRITERIA.map(([k, label]) => (
                  <li key={k} className="flex items-center justify-between text-sm">
                    <span>{label}</span>
                    <select
                      className="rounded-lg border border-[var(--color-sc-line)] px-2 py-1"
                      value={scores[k] || 0}
                      onChange={(e) => setScores((p) => ({ ...p, [k]: Number(e.target.value) }))}
                    >
                      {[0, 1, 2, 3, 4, 5].map((n) => (
                        <option key={n} value={n}>
                          {n}/5
                        </option>
                      ))}
                    </select>
                  </li>
                ))}
              </ul>
              <textarea
                className="w-full rounded-lg border border-[var(--color-sc-line)] p-2 text-sm"
                rows={3}
                placeholder="Notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
              {msg ? <p className="text-sm font-bold">{msg}</p> : null}
              <button type="button" onClick={() => void submit()} className="sc-btn w-full">
                Save score
              </button>
            </>
          ) : (
            <p className="sc-meta">Select a call</p>
          )}
        </aside>
      </div>
    </div>
  );
}
