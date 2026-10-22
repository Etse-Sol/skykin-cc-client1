import { useEffect, useMemo, useState } from 'react';
import { fetchAgentSession } from '../../services/session';
import { opsGet, opsPost } from '../../services/ops';

export default function Surveys() {
  const [csat, setCsat] = useState('—');
  const [nps, setNps] = useState('—');
  const [n, setN] = useState(0);
  const [resolved, setResolved] = useState(0);
  const [rows, setRows] = useState<any[]>([]);
  const [msg, setMsg] = useState('');
  const [rating, setRating] = useState(4);
  const [ok, setOk] = useState('yes');
  const [comment, setComment] = useState('');
  const [channel, setChannel] = useState('Voice');

  const reload = async () => {
    const s = await fetchAgentSession();
    const data = await opsGet('surveys', { domain: s.domain });
    setCsat(String(data.csat ?? '—'));
    setNps(String(data.nps ?? '—'));
    setN(Number(data.response_n || 0));
    setResolved(Number(data.resolved_rate || 0));
    setRows(Array.isArray(data.rows) ? data.rows : []);
  };

  useEffect(() => {
    reload().catch((e) => setMsg(e instanceof Error ? e.message : 'Load failed'));
  }, []);

  const byCh = useMemo(() => {
    const m: Record<string, number> = {};
    for (const r of rows) {
      const c = String(r.channel || 'Voice');
      m[c] = (m[c] || 0) + 1;
    }
    return Object.entries(m).sort((a, b) => b[1] - a[1]);
  }, [rows]);

  const submit = async () => {
    setMsg('');
    try {
      const s = await fetchAgentSession();
      await opsPost(
        'survey_submit',
        { rating, resolved: ok, comment, channel, agent_ext: s.extension },
        { domain: s.domain },
      );
      setComment('');
      setMsg('Logged');
      await reload();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Save failed');
    }
  };

  const npsLabel = nps === '—' ? '—' : Number(nps) >= 0 ? `+${nps}` : String(nps);

  return (
    <div className="flex flex-col gap-[18px]">
      <div>
        <h1 className="text-[22px] font-bold">Surveys</h1>
        <p className="sc-meta mt-1">Live CSAT / NPS from post-call responses</p>
      </div>
      {msg ? <p className="text-sm font-bold">{msg}</p> : null}

      <div className="grid gap-3 sm:grid-cols-4">
        {[
          ['CSAT', String(csat)],
          ['NPS', npsLabel],
          ['Responses', String(n)],
          ['Resolved', `${resolved}%`],
        ].map(([k, v]) => (
          <div key={k} className="sc-card">
            <p className="text-[11px] font-bold tracking-wide text-[var(--color-sc-muted)]">{k}</p>
            <p className="mt-1 text-[26px] font-extrabold tabular-nums">{v}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-start gap-4">
        <div className="sc-card min-w-0 flex-[2_1_520px]">
          <h2 className="mb-3 text-[16px] font-bold">Recent responses</h2>
          <div className="mb-3 flex flex-wrap gap-2">
            {byCh.map(([c, cnt]) => (
              <span key={c} className="sc-chip sc-chip-ready">
                {c} {cnt}
              </span>
            ))}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead className="text-[11px] uppercase text-[var(--color-sc-muted)]">
                <tr>
                  <th className="px-2 py-2">When</th>
                  <th className="px-2 py-2">Agent</th>
                  <th className="px-2 py-2">Channel</th>
                  <th className="px-2 py-2 text-right">Rating</th>
                  <th className="px-2 py-2">Resolved</th>
                  <th className="px-2 py-2">Comment</th>
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, 80).map((r) => (
                  <tr key={r.survey_id} className="border-t border-[var(--color-sc-line)]">
                    <td className="px-2 py-2">{String(r.created_at || '').slice(0, 16)}</td>
                    <td className="px-2 py-2">{r.agent_name || r.agent_ext || '—'}</td>
                    <td className="px-2 py-2">{r.channel}</td>
                    <td className="px-2 py-2 text-right font-bold">{r.rating}</td>
                    <td className="px-2 py-2">{r.resolved}</td>
                    <td className="px-2 py-2">{r.comment || '—'}</td>
                  </tr>
                ))}
                {rows.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-2 py-6 text-[var(--color-sc-muted)]">
                      No survey rows yet
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </div>

        <aside className="sc-card min-w-[260px] flex-[1_1_280px]">
          <h2 className="text-[16px] font-bold">Log a response</h2>
          <p className="sc-meta mt-1">Supervisor capture when the IVR survey is not wired</p>
          <p className="mt-3 text-sm">Rating</p>
          <div className="mt-2 flex gap-2">
            {[1, 2, 3, 4, 5].map((num) => (
              <button
                key={num}
                type="button"
                onClick={() => setRating(num)}
                className={`h-10 w-10 rounded-full text-sm font-bold ${
                  rating === num ? 'bg-[var(--color-sc-green)] text-white' : 'bg-[var(--color-sc-soft)]'
                }`}
              >
                {num}
              </button>
            ))}
          </div>
          <p className="mt-3 text-sm">Resolved</p>
          <div className="mt-2 flex gap-2">
            {['yes', 'no'].map((v) => (
              <button
                key={v}
                type="button"
                className={`sc-chip ${ok === v ? 'sc-chip-call' : 'sc-chip-ready'}`}
                onClick={() => setOk(v)}
              >
                {v}
              </button>
            ))}
          </div>
          <select className="sc-input mt-3 w-full" value={channel} onChange={(e) => setChannel(e.target.value)}>
            {['Voice', 'SMS', 'WhatsApp', 'App'].map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
          <textarea
            className="mt-3 w-full rounded-lg border border-[var(--color-sc-line)] p-2 text-sm"
            rows={2}
            placeholder="Comments"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
          <button type="button" className="sc-btn mt-3 w-full" onClick={() => void submit()}>
            Save
          </button>
        </aside>
      </div>
    </div>
  );
}
