import { useEffect, useState } from 'react';
import { fetchAgentSession } from '../../services/session';
import { fmtSec } from '../../services/supervisorApi';
import { fetchCallList, fetchReportSummary, opsGet, weekRange } from '../../services/ops';
import StudioPage from './StudioPage';

export function IvrReport() {
  const wr = weekRange();
  const [from, setFrom] = useState(wr.from);
  const [to, setTo] = useState(wr.to);
  const [kpis, setKpis] = useState<{ k: string; v: string }[]>([]);
  const [rows, setRows] = useState<any[]>([]);
  const [err, setErr] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const s = await fetchAgentSession();
        const [sum, list] = await Promise.all([
          fetchReportSummary(s.domain, from, to),
          fetchCallList(s.domain, from, to),
        ]);
        if (cancelled) return;
        setKpis([
          { k: 'Total', v: String(sum.total ?? 0) },
          { k: 'Answered', v: String(sum.answered ?? 0) },
          { k: 'Abandoned', v: String(sum.abandoned ?? 0) },
          { k: 'Missed', v: String(sum.missed ?? 0) },
          { k: 'Inbound', v: String(sum.inbound ?? 0) },
          { k: 'AHT', v: sum.avg_talk != null ? fmtSec(sum.avg_talk) : '—' },
        ]);
        setRows(Array.isArray(list) ? list.slice(0, 80) : []);
        setErr('');
      } catch (e) {
        if (!cancelled) setErr(e instanceof Error ? e.message : 'Report failed');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [from, to]);

  return (
    <StudioPage
      title="IVR call history report"
      path="/admin/reports/ivr"
      blurb="Inbound/outbound KPIs and call list for the selected dates"
    >
      <div className="flex flex-wrap gap-2">
        <input className="sc-input" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        <input className="sc-input" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
      </div>
      {err ? <p className="text-sm text-[var(--color-sc-warn)]">{err}</p> : null}
      <div className="flex flex-wrap gap-3">
        {kpis.map((x) => (
          <div key={x.k} className="sc-card min-w-[140px] flex-1">
            <p className="text-[11px] font-bold tracking-wide text-[var(--color-sc-muted)]">{x.k}</p>
            <p className="mt-1 text-[22px] font-extrabold">{x.v}</p>
          </div>
        ))}
      </div>
      <div className="overflow-x-auto overflow-hidden rounded-[14px] border border-[var(--color-sc-line)] bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-[var(--color-sc-soft)] text-[11px] uppercase text-[var(--color-sc-muted)]">
            <tr>
              <th className="px-3 py-2">Time</th>
              <th className="px-3 py-2">Caller</th>
              <th className="px-3 py-2">Dest</th>
              <th className="px-3 py-2">Result</th>
              <th className="px-3 py-2">Talk</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.xml_cdr_uuid || r.uuid || i} className="border-t border-[var(--color-sc-line)]">
                <td className="px-3 py-2">{r.start_stamp || r.call_time || r.start || '—'}</td>
                <td className="px-3 py-2">{r.caller_id_number || r.caller || '—'}</td>
                <td className="px-3 py-2">{r.destination_number || r.destination || '—'}</td>
                <td className="px-3 py-2">{r.result || r.status || r.hangup_cause || '—'}</td>
                <td className="px-3 py-2">{r.billsec != null ? fmtSec(Number(r.billsec)) : '—'}</td>
              </tr>
            ))}
            {rows.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-[var(--color-sc-muted)]">
                  No calls in this range
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </StudioPage>
  );
}

export function CallReasonsReport() {
  const [rows, setRows] = useState<{ reason: string; calls: number }[]>([]);
  const [err, setErr] = useState('');
  useEffect(() => {
    fetchAgentSession()
      .then((s) => opsGet('reasons', { domain: s.domain }))
      .then((d) => setRows(d.reasons || []))
      .catch((e) => setErr(e instanceof Error ? e.message : 'Failed'));
  }, []);
  return (
    <StudioPage
      title="Call reason report"
      path="/admin/reports/reasons"
      blurb="Reasons saved from wrap-up on Cases"
    >
      {err ? <p className="text-sm text-[var(--color-sc-warn)]">{err}</p> : null}
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-[var(--color-sc-muted)]">
            <th className="pb-2">Reason</th>
            <th className="pb-2">Cases</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.reason} className="border-t border-[var(--color-sc-line)]">
              <td className="py-2">{r.reason}</td>
              <td className="py-2 font-bold">{r.calls}</td>
            </tr>
          ))}
          {rows.length === 0 ? (
            <tr>
              <td colSpan={2} className="py-4 text-[var(--color-sc-muted)]">
                No wrap-up reasons yet
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </StudioPage>
  );
}
