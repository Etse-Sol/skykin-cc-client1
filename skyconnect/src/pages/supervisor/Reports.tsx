import { useEffect, useMemo, useState } from 'react';
import { fetchAgentSession } from '../../services/session';
import {
  fetchAgentPerformance,
  fetchCallList,
  fetchHourlyVolume,
  fetchQueueSla,
  fetchReportSummary,
  opsGet,
  type ReportSummary,
} from '../../services/ops';
import { fmtHms, fmtSec } from '../../services/supervisorApi';

type Tab = 'kpi' | 'hourly' | 'queues' | 'reasons' | 'agents';

export default function Reports() {
  const [tab, setTab] = useState<Tab>('hourly');
  const week = (() => {
    const t = new Date();
    const to = t.toISOString().slice(0, 10);
    t.setDate(t.getDate() - 6);
    return { from: t.toISOString().slice(0, 10), to };
  })();
  const [from, setFrom] = useState(week.from);
  const [to, setTo] = useState(week.to);
  const [domain, setDomain] = useState('ahununu');
  const [sum, setSum] = useState<ReportSummary | null>(null);
  const [hourly, setHourly] = useState<{ hour: number; total: number; answered: number; abandoned?: number; missed?: number }[]>([]);
  const [perf, setPerf] = useState<any[]>([]);
  const [reasons, setReasons] = useState<{ reason: string; calls: number }[]>([]);
  const [calls, setCalls] = useState<any[]>([]);
  const [queues, setQueues] = useState<any[]>([]);
  const [q, setQ] = useState('');
  const [err, setErr] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const s = await fetchAgentSession();
        const dom = domain || s.domain;
        const [summary, hv, agents, rs, list, slaRows] = await Promise.all([
          fetchReportSummary(dom, from, to),
          fetchHourlyVolume(dom, from, to),
          fetchAgentPerformance(dom, from, to),
          opsGet('reasons', { domain: dom }).catch(() => ({ reasons: [] })),
          fetchCallList(dom, from, to),
          fetchQueueSla(dom, from, to).catch(() => []),
        ]);
        setSum(summary);
        setHourly(Array.isArray(hv) ? hv : []);
        setPerf(agents);
        setReasons(Array.isArray(rs.reasons) ? rs.reasons : []);
        setCalls(list);
        setQueues(Array.isArray(slaRows) ? slaRows : []);
        setErr('');
      } catch (e) {
        setErr(e instanceof Error ? e.message : 'Reports failed');
      }
    })();
  }, [from, to, domain]);

  const total = Number(sum?.total ?? 0);
  const answered = Number(sum?.answered ?? 0);
  const abandoned = Number(sum?.abandoned ?? 0);
  const hangPct = total ? ((abandoned / total) * 100).toFixed(2) : '0';
  const xferPct = total ? ((answered / total) * 100).toFixed(2) : '0';
  const aht = Number(sum?.avg_talk ?? 0);
  const asa = Number(sum?.avg_wait ?? 0);
  const slaPct = Number(sum?.sla ?? 0);
  const exportUrl = `/app/agent_dashboard/reports.php?api=export_excel&domain=${encodeURIComponent(domain)}&from=${from}&to=${to}`;

  const hoursDesc = useMemo(
    () => [...hourly].sort((a, b) => b.hour - a.hour),
    [hourly],
  );

  const needle = q.trim().toLowerCase();
  const reasonRows = useMemo(() => {
    return calls.filter((c) => {
      if (!needle) return true;
      return `${c.caller_id_number} ${c.destination_number} ${c.result}`.toLowerCase().includes(needle);
    });
  }, [calls, needle]);

  const maxReason = Math.max(1, ...reasons.map((r) => Number(r.calls || 0)));

  return (
    <div className="flex flex-col gap-[18px]">
      <h1 className="text-[22px] font-bold">IVR call history report · {domain}</h1>
      {err ? <p className="text-sm text-[var(--color-sc-warn)]">{err}</p> : null}

      <div className="sc-card">
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-xs font-bold text-[var(--color-sc-muted)]">
            Domain
            <select className="sc-input mt-1" value={domain} onChange={(e) => setDomain(e.target.value)}>
              <option value="ahununu">ahununu</option>
              <option value="client1.skykin.local">client1.skykin.local</option>
            </select>
          </label>
          <label className="text-xs font-bold text-[var(--color-sc-muted)]">
            From
            <input className="sc-input mt-1" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
          </label>
          <label className="text-xs font-bold text-[var(--color-sc-muted)]">
            To
            <input className="sc-input mt-1" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
          </label>
          <a className="sc-b2" href={exportUrl}>
            Export Excel
          </a>
        </div>

        <div className="mt-3.5 flex flex-wrap gap-2">
          {(
            [
              ['kpi', 'Summary KPI'],
              ['hourly', 'Hourly table'],
              ['queues', 'Queue SLA'],
              ['reasons', 'Call reasons'],
              ['agents', 'By agent'],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              className={`sc-chip ${tab === id ? 'sc-chip-call' : 'sc-chip-ready'}`}
              onClick={() => setTab(id)}
            >
              {label}
            </button>
          ))}
        </div>

        {tab === 'kpi' ? (
          <div className="mt-4 grid gap-3 sm:grid-cols-5">
            {[
              ['Total calls', String(total)],
              ['Answered / transferred', String(answered)],
              ['Hang-up in IVR', String(abandoned)],
              ['Hang-up %', hangPct],
              ['Transfer %', xferPct],
              ['Answered AHT', fmtHms(aht)],
              ['ASA', fmtHms(asa)],
              ['SLA %', String(slaPct)],
              ['Inbound', String(sum?.inbound ?? '—')],
              ['Outbound', String(sum?.outbound ?? '—')],
            ].map(([k, v]) => (
              <div key={k} className="rounded-[12px] border border-[var(--color-sc-line)] p-3">
                <p className="sc-meta">{k}</p>
                <p className="mt-1 text-[22px] font-extrabold tabular-nums">{v}</p>
              </div>
            ))}
          </div>
        ) : null}

        {tab === 'hourly' ? (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[860px] text-left text-sm">
              <thead className="text-[11px] uppercase text-[var(--color-sc-muted)]">
                <tr>
                  <th className="px-2 py-2">Interval</th>
                  <th className="px-2 py-2 text-right">Total calls</th>
                  <th className="px-2 py-2">Answered AHT</th>
                  <th className="px-2 py-2 text-right">Hang-up in IVR</th>
                  <th className="px-2 py-2 text-right">Transferred</th>
                  <th className="px-2 py-2 text-right">Hang-up %</th>
                  <th className="px-2 py-2 text-right">Transfer %</th>
                </tr>
              </thead>
              <tbody>
                {hoursDesc.map((h) => {
                  const tot = Number(h.total || 0);
                  const ans = Number(h.answered || 0);
                  const abd = Number(h.abandoned || 0);
                  return (
                    <tr key={h.hour} className="border-t border-[var(--color-sc-line)]">
                      <td className="px-2 py-2">
                        {String(h.hour).padStart(2, '0')}:00 - {String(h.hour).padStart(2, '0')}:59
                      </td>
                      <td className="px-2 py-2 text-right font-bold tabular-nums">{tot}</td>
                      <td className="px-2 py-2 tabular-nums">{fmtHms(aht)}</td>
                      <td className="px-2 py-2 text-right tabular-nums">{abd}</td>
                      <td className="px-2 py-2 text-right tabular-nums">{ans}</td>
                      <td className="px-2 py-2 text-right tabular-nums">{tot ? ((abd / tot) * 100).toFixed(2) : '0'}</td>
                      <td className="px-2 py-2 text-right tabular-nums">{tot ? ((ans / tot) * 100).toFixed(2) : '0'}</td>
                    </tr>
                  );
                })}
                <tr className="border-t border-[var(--color-sc-line)]">
                  <td className="px-2 py-2 font-bold">Summary</td>
                  <td className="px-2 py-2 text-right font-bold">{total}</td>
                  <td className="px-2 py-2 font-bold">{fmtHms(aht)}</td>
                  <td className="px-2 py-2 text-right font-bold">{abandoned}</td>
                  <td className="px-2 py-2 text-right font-bold">{answered}</td>
                  <td className="px-2 py-2 text-right font-bold">{hangPct}</td>
                  <td className="px-2 py-2 text-right font-bold">{xferPct}</td>
                </tr>
                {hoursDesc.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-2 py-6 text-[var(--color-sc-muted)]">
                      No hourly volume in this range
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        ) : null}

        {tab === 'reasons' ? (
          <div className="mt-4">
            <h2 className="mb-3 text-[16px] font-bold">Call reason report</h2>
            <div className="mb-4 flex h-36 items-end gap-2">
              {reasons.slice(0, 10).map((r) => (
                <div key={r.reason} className="flex min-w-0 flex-1 flex-col items-center gap-1">
                  <div
                    className="w-full rounded-t bg-[var(--color-sc-green)]"
                    style={{ height: `${(Number(r.calls) / maxReason) * 110}px` }}
                  />
                  <span className="truncate text-[10px]">{r.reason}</span>
                </div>
              ))}
              {reasons.length === 0 ? <p className="sc-meta">No wrap-up reasons yet</p> : null}
            </div>
            <input
              className="sc-input mb-3 max-w-sm"
              placeholder="Search caller, dest, result"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <div className="overflow-x-auto">
              <table className="w-full min-w-[820px] text-left text-sm">
                <thead className="text-[11px] uppercase text-[var(--color-sc-muted)]">
                  <tr>
                    <th className="px-2 py-2">Date</th>
                    <th className="px-2 py-2">Customer</th>
                    <th className="px-2 py-2 text-right">Duration</th>
                    <th className="px-2 py-2">Queue</th>
                    <th className="px-2 py-2">Result</th>
                  </tr>
                </thead>
                <tbody>
                  {reasonRows.slice(0, 80).map((c, i) => (
                    <tr key={`${c.call_time}-${i}`} className="border-t border-[var(--color-sc-line)]">
                      <td className="px-2 py-2">{c.call_time}</td>
                      <td className="px-2 py-2">{c.caller_id_number}</td>
                      <td className="px-2 py-2 text-right tabular-nums">{fmtSec(Number(c.billsec || c.duration || 0))}</td>
                      <td className="px-2 py-2">{c.destination_number}</td>
                      <td className="px-2 py-2">{c.result}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}

        {tab === 'queues' ? (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-[11px] uppercase text-[var(--color-sc-muted)]">
                <tr>
                  <th className="px-2 py-2">Queue</th>
                  <th className="px-2 py-2 text-right">Offered</th>
                  <th className="px-2 py-2 text-right">Answered</th>
                  <th className="px-2 py-2 text-right">Answer %</th>
                  <th className="px-2 py-2 text-right">AHT</th>
                </tr>
              </thead>
              <tbody>
                {queues.map((row) => {
                  const tot = Number(row.total || 0);
                  const ans = Number(row.answered || 0);
                  return (
                    <tr key={String(row.queue_num)} className="border-t border-[var(--color-sc-line)]">
                      <td className="px-2 py-2 font-bold">{row.queue_num}</td>
                      <td className="px-2 py-2 text-right tabular-nums">{tot}</td>
                      <td className="px-2 py-2 text-right tabular-nums">{ans}</td>
                      <td className="px-2 py-2 text-right tabular-nums">{tot ? ((ans / tot) * 100).toFixed(1) : '0'}%</td>
                      <td className="px-2 py-2 text-right tabular-nums">{fmtHms(Number(row.avg_dur || 0))}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {!queues.length ? <p className="sc-meta mt-3">No queue traffic in this range.</p> : null}
          </div>
        ) : null}

        {tab === 'agents' ? (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-[11px] uppercase text-[var(--color-sc-muted)]">
                <tr>
                  <th className="px-2 py-2">Agent</th>
                  <th className="px-2 py-2 text-right">Total</th>
                  <th className="px-2 py-2 text-right">Answered</th>
                  <th className="px-2 py-2 text-right">Missed</th>
                  <th className="px-2 py-2 text-right">Talk</th>
                  <th className="px-2 py-2 text-right">Answer %</th>
                </tr>
              </thead>
              <tbody>
                {perf.map((p) => (
                  <tr key={p.ext} className="border-t border-[var(--color-sc-line)]">
                    <td className="px-2 py-2 font-bold">
                      {p.name || p.ext} <span className="sc-meta">{p.ext}</span>
                    </td>
                    <td className="px-2 py-2 text-right tabular-nums">{p.total}</td>
                    <td className="px-2 py-2 text-right tabular-nums">{p.answered}</td>
                    <td className="px-2 py-2 text-right tabular-nums">{p.missed}</td>
                    <td className="px-2 py-2 text-right tabular-nums">{fmtSec(Number(p.total_talk || 0))}</td>
                    <td className="px-2 py-2 text-right font-bold">{p.answer_rate}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
    </div>
  );
}
