import { useCallback, useEffect, useMemo, useState } from 'react';
import { fetchAgentSession } from '../../services/session';
import { fetchHourlyVolume, fetchReportSummary, todayRange } from '../../services/ops';
import BreakRequests from '../../components/BreakRequests';
import {
  fetchLeaveRequests,
  fetchSupAgents,
  fetchSupQueue,
  fmtHms,
  fmtSec,
  statusLabel,
  type LeaveRequest,
  type SupAgent,
  type SupQueuePayload,
} from '../../services/supervisorApi';

function waitSeconds(waitFmt?: string): number {
  const wf = String(waitFmt || '');
  const parts = wf.split(':').map((x) => parseInt(x, 10));
  if (parts.length === 3 && !Number.isNaN(parts[0])) return parts[0] * 3600 + parts[1] * 60 + (parts[2] || 0);
  if (parts.length === 2 && !Number.isNaN(parts[0])) return parts[0] * 60 + (parts[1] || 0);
  if (parts.length === 1 && !Number.isNaN(parts[0])) return parts[0];
  return 0;
}

function Donut({ pct, color, label }: { pct: number; color: string; label: string }) {
  const n = Math.max(0, Math.min(100, Math.round(pct || 0)));
  return (
    <div className="flex min-w-[160px] flex-[1_1_160px] flex-col items-center gap-2 rounded-[14px] border border-[var(--color-sc-line)] bg-white p-3.5">
      <p className="text-[13px] text-[var(--color-sc-muted)]">{label}</p>
      <div
        className="flex h-[110px] w-[110px] items-center justify-center rounded-full"
        style={{ background: `conic-gradient(${color} 0 ${n}%, #E8EDE9 0)` }}
      >
        <div className="flex h-[82px] w-[82px] items-center justify-center rounded-full bg-white text-[24px] font-extrabold tabular-nums">
          {n}%
        </div>
      </div>
    </div>
  );
}

function Tile({
  label,
  value,
  bg,
  fg = '#fff',
}: {
  label: string;
  value: string;
  bg: string;
  fg?: string;
}) {
  return (
    <div className="min-w-[160px] flex-[1_1_160px] rounded-[14px] border border-[var(--color-sc-line)] bg-white p-3.5">
      <p className="mb-2.5 text-center text-[13px] text-[var(--color-sc-muted)]">{label}</p>
      <div
        className="flex h-[110px] items-center justify-center rounded-[10px] text-[44px] font-extrabold tabular-nums"
        style={{ background: bg, color: fg }}
      >
        {value}
      </div>
    </div>
  );
}

export default function Wallboard() {
  const [slide, setSlide] = useState(0);
  const [paused, setPaused] = useState(false);
  const [domain, setDomain] = useState('');
  const [agents, setAgents] = useState<SupAgent[]>([]);
  const [queue, setQueue] = useState<SupQueuePayload | null>(null);
  const [leaves, setLeaves] = useState<LeaveRequest[]>([]);
  const [hourly, setHourly] = useState<{ hour: number; total: number; answered: number }[]>([]);
  const [sumTotal, setSumTotal] = useState(0);
  const [sumAns, setSumAns] = useState(0);
  const [sumAbd, setSumAbd] = useState(0);
  const [avgTalk, setAvgTalk] = useState(0);
  const [sla, setSla] = useState(0);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');

  const load = useCallback(async () => {
    const s = await fetchAgentSession();
    setDomain(s.domain);
    const { from, to } = todayRange();
    const [a, q, lv, hr, sm] = await Promise.all([
      fetchSupAgents(s.domain),
      fetchSupQueue(s.domain),
      fetchLeaveRequests(s.domain),
      fetchHourlyVolume(s.domain, from, to).catch(() => []),
      fetchReportSummary(s.domain, from, to).catch(() => ({})),
    ]);
    setAgents(a);
    setQueue(q);
    setLeaves(lv);
    setHourly(Array.isArray(hr) ? hr : []);
    setSumTotal(Number(sm.total ?? q.total_today ?? 0));
    setSumAns(Number(sm.answered ?? q.answered_today ?? 0));
    setSumAbd(Number(sm.abandoned ?? q.abandoned_today ?? 0));
    setAvgTalk(Number(sm.avg_talk ?? q.avg_talk ?? 0));
    const inbound = Number(sm.inbound ?? q.inbound_today ?? 0);
    const unhandled = Number(sm.missed ?? 0) + Number(sm.abandoned ?? q.abandoned_today ?? 0);
    setSla(inbound > 0 ? Math.round(((inbound - unhandled) / inbound) * 100) : Number(q.sla ?? sm.sla ?? 0));
    setErr('');
  }, []);

  useEffect(() => {
    load().catch((e) => setErr(e instanceof Error ? e.message : 'Load failed'));
    const t = window.setInterval(() => load().catch(() => {}), 8000);
    return () => window.clearInterval(t);
  }, [load]);

  useEffect(() => {
    if (paused) return;
    const t = window.setInterval(() => setSlide((n) => (n + 1) % 3), 12000);
    return () => window.clearInterval(t);
  }, [paused]);

  const waiting = queue?.waiting_callers?.length ?? Number(queue?.queues?.reduce((n, r) => n + (r.waiting || 0), 0) || 0);
  let maxWait = 0;
  for (const c of queue?.waiting_callers || []) {
    const sec = waitSeconds(c.wait_fmt);
    if (sec > maxWait) maxWait = sec;
  }

  const ready = agents.filter((a) => {
    const s = (a.status || '').toLowerCase();
    return s === 'ready' || s === 'available';
  }).length;
  const notReady = agents.filter((a) => {
    const s = (a.status || '').toLowerCase();
    return s === 'break' || s === 'offline' || s === 'logged_out';
  }).length;
  const onCall = agents.filter((a) => (a.call_duration || 0) > 0 || !!a.on_call_with).length;
  const duty = Math.max(1, agents.filter((a) => a.registered).length);
  const occ = Math.round((onCall / duty) * 100);
  const eff = sumTotal > 0 ? Math.round((sumAns / sumTotal) * 100) : 0;

  const chart = useMemo(() => {
    const pts = hourly.length ? hourly : [];
    const max = Math.max(1, ...pts.map((p) => Number(p.total || 0)));
    const w = 700;
    const h = 160;
    const n = Math.max(pts.length, 2);
    const offered = pts
      .map((p, i) => {
        const x = (i / (n - 1)) * w;
        const y = h - 20 - (Number(p.total || 0) / max) * (h - 40);
        return `${x},${y}`;
      })
      .join(' ');
    const answered = pts
      .map((p, i) => {
        const x = (i / (n - 1)) * w;
        const y = h - 20 - (Number(p.answered || 0) / max) * (h - 40);
        return `${x},${y}`;
      })
      .join(' ');
    return { offered, answered };
  }, [hourly]);

  return (
    <div className="flex min-h-[70vh] flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-[12px] text-[#4D5F57]">
            SKYCONNECT · LIVE VIEW · {slide + 1} / 3
          </p>
          <h1 className="text-[24px] font-bold">
            {slide === 0 ? 'Summary dashboard' : slide === 1 ? 'Agents and queue' : 'Breaks and queues'}
          </h1>
        </div>
        <div className="flex gap-2">
          <button type="button" className="sc-b2" onClick={() => setSlide((n) => (n + 2) % 3)}>
            Prev
          </button>
          <button type="button" className="sc-b2" onClick={() => setPaused((p) => !p)}>
            {paused ? 'Play' : 'Pause'}
          </button>
          <button type="button" className="sc-b2" onClick={() => setSlide((n) => (n + 1) % 3)}>
            Next
          </button>
        </div>
      </div>
      {err ? <p className="text-sm text-[var(--color-sc-warn)]">{err}</p> : null}
      {msg ? <p className="text-sm font-bold">{msg}</p> : null}

      {slide === 0 ? (
        <>
          <div className="flex flex-wrap gap-4">
            <Tile label="Total calls" value={String(sumTotal)} bg="#0B7A5A" />
            <Tile label="Answered" value={String(sumAns)} bg="#1E8E4E" />
            <Tile label="Abandoned" value={String(sumAbd)} bg="#B3261E" />
            <Tile label="Waiting" value={String(waiting)} bg="#E0A21B" fg="#10261F" />
            <Tile label="Longest wait" value={fmtHms(maxWait)} bg="#1F5F7A" />
            <Tile label="ACD avg" value={fmtHms(avgTalk)} bg="#1D3A30" />
          </div>
          <div className="flex flex-wrap gap-4">
            <Tile label="Agents available" value={String(ready)} bg="#9BE3B0" fg="#10261F" />
            <Tile label="Not ready" value={String(notReady)} bg="#E54B4B" />
            <Tile label="On call" value={String(onCall)} bg="#F2D54B" fg="#10261F" />
            <Donut pct={eff} color="#34C28F" label="Efficiency" />
            <Donut pct={sla} color="#E8A317" label="SLA" />
            <Donut pct={occ} color="#E0A21B" label="Occupancy" />
          </div>
          <div className="rounded-[14px] border border-[var(--color-sc-line)] bg-white p-4">
            <p className="mb-2.5 text-[13px] text-[#4D5F57]">Offered vs answered by hour</p>
            {hourly.length === 0 ? (
              <p className="sc-meta">No hourly volume yet today</p>
            ) : (
              <svg viewBox="0 0 700 160" className="h-40 w-full" role="img" aria-label="Offered and answered calls by hour">
                <polyline fill="none" stroke="#E8A317" strokeWidth="3" points={chart.offered} />
                <polyline fill="none" stroke="#34C28F" strokeWidth="3" points={chart.answered} />
              </svg>
            )}
          </div>
        </>
      ) : null}

      {slide === 1 ? (
        <>
          <div className="flex flex-wrap gap-4">
            <Tile label="Waiting" value={String(waiting)} bg="#E0A21B" fg="#10261F" />
            <Tile label="Longest wait" value={fmtHms(maxWait)} bg="#1F5F7A" />
            <Tile label="On call" value={String(onCall)} bg="#F2D54B" fg="#10261F" />
            <Tile label="SIP online" value={String(agents.filter((a) => a.registered).length)} bg="#0B7A5A" />
          </div>
          <div className="overflow-hidden rounded-[14px] border border-[var(--color-sc-line)] bg-white">
            <table className="w-full text-left text-sm">
              <thead className="bg-[var(--color-sc-soft)] text-[11px] uppercase text-[var(--color-sc-muted)]">
                <tr>
                  <th className="px-3 py-2">Agent</th>
                  <th className="px-3 py-2">State</th>
                  <th className="px-3 py-2">Customer</th>
                  <th className="px-3 py-2">Time</th>
                </tr>
              </thead>
              <tbody>
                {agents.map((a) => (
                  <tr key={a.ext} className="border-t border-[var(--color-sc-line)]">
                    <td className="px-3 py-2.5 font-bold">
                      {a.name || a.ext} <span className="sc-meta">{a.ext}</span>
                    </td>
                    <td className="px-3 py-2.5">{statusLabel(a)}</td>
                    <td className="px-3 py-2.5">{a.on_call_with || '—'}</td>
                    <td className="px-3 py-2.5 tabular-nums">
                      {a.on_call_with ? fmtSec(a.call_duration || 0) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {(queue?.waiting_callers || []).length > 0 ? (
            <div className="sc-card">
              <h2 className="mb-2 text-[16px] font-bold">Waiting callers</h2>
              <ul className="space-y-1 text-sm">
                {(queue?.waiting_callers || []).map((c, i) => (
                  <li key={`${c.number}-${i}`} className="flex justify-between gap-2">
                    <span>{c.number}</span>
                    <span className="sc-meta">
                      q{c.queue} · {c.wait_fmt || c.state}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      ) : null}

      {slide === 2 ? (
        <>
          <div className="flex flex-wrap gap-4">
            {(queue?.queues || []).length === 0 ? (
              <p className="sc-meta">No queues configured</p>
            ) : (
              (queue?.queues || []).map((q) => (
                <Tile key={q.extension} label={q.name || q.extension} value={String(q.waiting)} bg="#0B7A5A" />
              ))
            )}
          </div>
          <BreakRequests
            domain={domain}
            leaves={leaves}
            agents={agents}
            waiting={queue?.waiting_callers?.length ?? Number(queue?.queues?.reduce((n, r) => n + (r.waiting || 0), 0) || 0)}
            onDone={(m) => {
              setMsg(m);
              void load();
            }}
          />
        </>
      ) : null}
    </div>
  );
}
