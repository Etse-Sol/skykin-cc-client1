import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import StatusPill from '../../components/StatusPill';
import { fetchAgentSession } from '../../services/session';
import {
  fetchAiEvalDraft,
  fetchEvalCalls,
  fetchEvalHistory,
  recUrl,
  saveEvaluation,
  weekRange,
  type EvalCall,
} from '../../services/ops';
import { fetchCallHistoryAll, fetchRecordingsAll } from '../../services/supervisorApi';

const CRITERIA = [
  ['greeting', 'Greeting'],
  ['knowledge', 'Knowledge'],
  ['resolution', 'Resolution'],
  ['tone', 'Tone / empathy'],
  ['procedure', 'Procedure'],
  ['closing', 'Closing'],
] as const;

export default function Evaluation() {
  const [from, setFrom] = useState(() => weekRange().from);
  const [to, setTo] = useState(() => weekRange().to);
  const [calls, setCalls] = useState<EvalCall[]>([]);
  const [hist, setHist] = useState<Record<string, unknown>[]>([]);
  const [sel, setSel] = useState<EvalCall | null>(null);
  const [scores, setScores] = useState<Record<string, number>>({});
  const [notes, setNotes] = useState('');
  const [transcript, setTranscript] = useState('');
  const [aiMsg, setAiMsg] = useState('');
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState('');
  const [assigned, setAssigned] = useState<{ title?: string; skill?: string; course_id?: number; score?: number }[]>(
    [],
  );

  const agentExt = (row: EvalCall | null) =>
    String(row?.agent_ext || row?.destination_number || '')
      .replace(/\D/g, '')
      .slice(0, 8);

  const load = useCallback(async () => {
    const s = await fetchAgentSession();
    const [evals, recs, histRows, saved] = await Promise.all([
      fetchEvalCalls(s.domain, from, to).catch(() => [] as EvalCall[]),
      fetchRecordingsAll(s.domain, from, to).catch(() => [] as any[]),
      fetchCallHistoryAll(s.domain, from, to).catch(() => [] as any[]),
      fetchEvalHistory(s.domain, from, to).catch(() => []),
    ]);
    const byKey = new Map<string, EvalCall>();
    const put = (row: EvalCall) => {
      const key =
        String(row.cdr_uuid || '') ||
        `${row.call_time || ''}|${row.caller_id_number || ''}|${row.destination_number || ''}`;
      const prev = byKey.get(key) || {};
      byKey.set(key, { ...prev, ...row, record_name: row.record_name || prev.record_name });
    };
    for (const r of Array.isArray(evals) ? evals : []) put(r);
    for (const r of recs) {
      put({
        cdr_uuid: `${r.time}-${r.caller}-${r.file}`,
        call_time: r.time,
        caller_id_number: r.caller,
        destination_number: r.destination,
        agent_ext: String(r.destination || '').replace(/\D/g, '').slice(0, 4),
        record_name: r.file,
        billsec: Number(String(r.duration || '').split(':').reduce((a: number, p: string) => a * 60 + Number(p || 0), 0)),
      });
    }
    for (const r of histRows) {
      put({
        cdr_uuid: `${r.time}-${r.caller}-${r.destination}`,
        call_time: r.time,
        caller_id_number: r.caller,
        destination_number: r.destination,
        agent_ext: String(r.agent || '').replace(/\D/g, '').slice(0, 4) || undefined,
      });
    }
    setCalls([...byKey.values()]);
    setHist(Array.isArray(saved) ? saved : []);
    setErr('');
  }, [from, to]);

  useEffect(() => {
    load().catch((e) => setErr(e instanceof Error ? e.message : 'Could not load evaluations'));
  }, [load]);

  useEffect(() => {
    if (!sel && calls[0]) setSel(calls[0]);
  }, [calls, sel]);

  const play = recUrl(sel?.record_name);

  const pick = (row: EvalCall) => {
    setSel(row);
    setScores({});
    setNotes('');
    setTranscript('');
    setAiMsg('');
    setMsg('');
    setAssigned([]);
  };

  const runAi = async () => {
    if (!sel?.record_name) {
      setAiMsg('No recording on this call');
      return;
    }
    setBusy('ai');
    setAiMsg('SkyKin AI is transcribing and scoring… this can take up to a minute.');
    try {
      const s = await fetchAgentSession();
      const r = await fetchAiEvalDraft({
        domain: s.domain,
        record_name: sel.record_name,
        record_path: String((sel as EvalCall & { record_path?: string }).record_path || ''),
        caller_number: sel.caller_id_number,
        agent_ext: sel.destination_number,
        duration: Number(sel.billsec || 0),
        call_time: sel.call_time,
      });
      const sc = r.scores || {};
      const next: Record<string, number> = {};
      for (const [k] of CRITERIA) next[k] = Number(sc[k] || 0);
      setScores(next);
      if (r.notes) setNotes(`[SkyKin AI] ${r.notes}`);
      if (r.transcript) setTranscript(r.transcript);
      setAiMsg('AI filled the scores. Review them, then save.');
    } catch (e) {
      setAiMsg(e instanceof Error ? e.message : 'AI draft failed');
    } finally {
      setBusy('');
    }
  };

  const submit = async () => {
    if (!sel) return;
    setBusy('save');
    setMsg('');
    try {
      const s = await fetchAgentSession();
      const ext = agentExt(sel);
      const payload: Record<string, unknown> = {
        cdr_uuid: sel.cdr_uuid,
        call_uuid: sel.cdr_uuid,
        agent_ext: ext,
        agent_name: ext,
        caller_number: sel.caller_id_number,
        call_time: sel.call_time,
        duration: sel.billsec,
        notes,
        domain: s.domain,
      };
      for (const [k] of CRITERIA) payload[`score_${k}`] = scores[k] || 0;
      const r = await saveEvaluation(payload);
      const learn = Array.isArray(r.learning) ? r.learning : [];
      setAssigned(learn);
      const n = learn.length;
      setMsg(
        n
          ? `Saved ${r.grade || ''} ${r.pct || ''}% · ${n} learning course${n === 1 ? '' : 's'} assigned for ext ${ext}`
          : `Saved ${r.grade || ''} ${r.pct || ''}% · no weak skills (4+/5), so no course assigned`,
      );
      await load();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setBusy('');
    }
  };

  const total = useMemo(
    () => CRITERIA.reduce((n, [k]) => n + (Number(scores[k]) || 0), 0),
    [scores],
  );

  return (
    <div className="flex flex-col gap-[18px]">
      <div>
        <h1 className="text-[22px] font-bold">AI evaluation</h1>
        <p className="sc-meta mt-1">
          Pick a recorded call. SkyKin AI transcribes it, fills greeting / knowledge / tone scores. You review, then save.
        </p>
      </div>
      {err ? <p className="text-sm text-[var(--color-sc-warn)]">{err}</p> : null}

      <div className="flex flex-wrap gap-3">
        <label className="text-xs font-bold text-[var(--color-sc-muted)]">
          From
          <input className="sc-input mt-1" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        </label>
        <label className="text-xs font-bold text-[var(--color-sc-muted)]">
          To
          <input className="sc-input mt-1" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
        </label>
      </div>

      <div className="flex flex-wrap items-start gap-4">
        <section className="sc-card min-w-0 flex-[1.1_1_420px]">
          <h2 className="mb-2 text-[16px] font-bold">Calls</h2>
          <div className="max-h-[520px] overflow-auto">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 bg-white text-[11px] uppercase text-[var(--color-sc-muted)]">
                <tr>
                  <th className="px-2 py-2">Time</th>
                  <th className="px-2 py-2">Caller</th>
                  <th className="px-2 py-2">Agent / dest</th>
                  <th className="px-2 py-2">Grade</th>
                </tr>
              </thead>
              <tbody>
                {calls.map((row) => {
                  const on = sel?.cdr_uuid === row.cdr_uuid;
                  return (
                    <tr
                      key={String(row.cdr_uuid)}
                      className={`cursor-pointer border-t border-[var(--color-sc-line)] ${
                        on ? 'bg-[var(--color-sc-nav-active)]' : 'hover:bg-[var(--color-sc-soft)]'
                      }`}
                      onClick={() => pick(row)}
                    >
                      <td className="px-2 py-2">{row.call_time || '—'}</td>
                      <td className="px-2 py-2">{row.caller_id_number || '—'}</td>
                      <td className="px-2 py-2">{row.destination_number || '—'}</td>
                      <td className="px-2 py-2">
                        {row.eval?.grade ? (
                          <StatusPill label={String(row.eval.grade)} tone="ok" />
                        ) : row.record_name ? (
                          <span className="sc-meta">recording</span>
                        ) : (
                          <span className="sc-meta">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
                {calls.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-2 py-6 text-[var(--color-sc-muted)]">
                      No calls in this range. Open Call review to confirm CDR, or widen the dates. Echo tests with 0 talk time are hidden until a call is answered.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>

        <aside className="sc-card flex min-w-[300px] flex-[1_1_360px] flex-col gap-3">
          {sel ? (
            <>
              <b className="text-[17px]">
                {sel.caller_id_number || 'Caller'} → {sel.destination_number || 'agent'}
              </b>
              <p className="sc-meta">
                {sel.call_time} · {sel.billsec || 0}s
              </p>
              {play ? (
                <audio className="w-full" controls src={play}>
                  <track kind="captions" />
                </audio>
              ) : (
                <p className="sc-meta">No recording file on this CDR — AI needs a recording.</p>
              )}
              <button type="button" className="sc-btn" disabled={busy === 'ai' || !sel.record_name} onClick={() => void runAi()}>
                {busy === 'ai' ? 'Scoring…' : 'Auto-score with SkyKin AI'}
              </button>
              {aiMsg ? <p className="text-sm font-semibold">{aiMsg}</p> : null}
              <p className="text-[11px] font-bold uppercase tracking-wide text-[var(--color-sc-muted)]">
                Scores · {total}/30
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
                rows={4}
                placeholder="Coach notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
              {transcript ? (
                <p className="max-h-40 overflow-auto whitespace-pre-wrap rounded-lg bg-[var(--color-sc-soft)] p-2 text-[12px] leading-snug">
                  {transcript}
                </p>
              ) : null}
              {msg ? <p className="text-sm font-bold">{msg}</p> : null}
              {assigned.length ? (
                <div className="rounded-lg bg-[var(--color-sc-soft)] p-3">
                  <p className="text-[12px] font-bold">Assigned to Learning</p>
                  <ul className="mt-1 space-y-1 text-sm">
                    {assigned.map((a) => (
                      <li key={String(a.course_id || a.skill)}>
                        {a.title || a.skill}
                        {a.skill ? <span className="sc-meta"> · {a.skill}</span> : null}
                      </li>
                    ))}
                  </ul>
                  <Link
                    className="mt-2 inline-block text-sm font-bold text-[var(--color-sc-green)] underline"
                    to={`/supervisor/learning?ext=${encodeURIComponent(agentExt(sel))}`}
                  >
                    Open Learning for this agent
                  </Link>
                </div>
              ) : null}
              <button type="button" className="sc-btn w-full" disabled={busy === 'save'} onClick={() => void submit()}>
                {busy === 'save' ? 'Saving…' : 'Save evaluation'}
              </button>
            </>
          ) : (
            <p className="sc-meta">Select a call</p>
          )}
        </aside>
      </div>

      <section className="sc-card">
        <h2 className="mb-2 text-[16px] font-bold">Saved this period</h2>
        <ul className="space-y-1 text-sm">
          {hist.slice(0, 20).map((r) => (
            <li key={String(r.eval_id || r.cdr_uuid)} className="flex flex-wrap justify-between gap-2 border-t border-[var(--color-sc-line)] py-2">
              <span>
                {String(r.call_time || '')} · {String(r.agent_ext || '')} ← {String(r.caller_number || '')}
              </span>
              <span className="font-bold">
                {String(r.grade || '')}{' '}
                {r.max_score ? `${Math.round((Number(r.total_score) / Number(r.max_score)) * 100)}%` : ''}
              </span>
            </li>
          ))}
          {hist.length === 0 ? <li className="sc-meta">No saved evaluations yet</li> : null}
        </ul>
      </section>
    </div>
  );
}
