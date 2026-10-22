import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import StatCard from '../../components/StatCard';
import StatusPill from '../../components/StatusPill';
import { fetchAgentSession } from '../../services/session';
import { fetchReportSummary, todayRange, type ReportSummary } from '../../services/ops';
import { useSoftphone } from '../../softphone/SoftphoneContext';
import {
  fetchLeaveRequests,
  fetchSupAgents,
  fetchSupQueue,
  forceAgentStatus,
  fmtSec,
  monitorAgent,
  resolveLeave,
  statusLabel,
  statusTone,
  type LeaveRequest,
  type SupAgent,
  type SupQueuePayload,
} from '../../services/supervisorApi';

function waitSeconds(waitFmt?: string): number {
  const wf = String(waitFmt || '');
  const parts = wf.split(':').map((x) => parseInt(x, 10));
  if (parts.length === 2 && !Number.isNaN(parts[0])) return parts[0] * 60 + (parts[1] || 0);
  if (parts.length === 1 && !Number.isNaN(parts[0])) return parts[0];
  return 0;
}

export default function SupDashboard() {
  const phone = useSoftphone();
  const [domain, setDomain] = useState('');
  const [q, setQ] = useState<SupQueuePayload | null>(null);
  const [sum, setSum] = useState<ReportSummary | null>(null);
  const [agents, setAgents] = useState<SupAgent[]>([]);
  const [leaves, setLeaves] = useState<LeaveRequest[]>([]);
  const [selected, setSelected] = useState('');
  const [err, setErr] = useState('');
  const [msg, setMsg] = useState('');

  const load = useCallback(async () => {
    const s = await fetchAgentSession();
    setDomain(s.domain);
    const { from, to } = todayRange();
    const [queue, roster, summary, lv] = await Promise.all([
      fetchSupQueue(s.domain),
      fetchSupAgents(s.domain),
      fetchReportSummary(s.domain, from, to),
      fetchLeaveRequests(s.domain),
    ]);
    setQ(queue);
    setAgents(roster);
    setSum(summary);
    setLeaves(lv);
    setErr('');
  }, []);

  useEffect(() => {
    let stop = false;
    const tick = async () => {
      try {
        await load();
      } catch (e) {
        if (!stop) setErr(e instanceof Error ? e.message : 'Dashboard failed');
      }
    };
    void tick();
    const t = window.setInterval(() => void tick(), 8000);
    return () => {
      stop = true;
      window.clearInterval(t);
    };
  }, [load]);

  const waiting = q?.waiting_callers?.length ?? Number(q?.queues?.reduce((n, r) => n + (r.waiting || 0), 0) || 0);
  const inbound = Number(sum?.inbound ?? q?.inbound_today ?? 0);
  const answered = Number(sum?.answered ?? q?.answered_today ?? 0);
  const unhandled = Number(sum?.missed ?? 0) + Number(sum?.abandoned ?? q?.abandoned_today ?? 0);
  const sla = inbound > 0 ? Math.round(((inbound - unhandled) / inbound) * 100) : Number(q?.sla ?? 0);
  const online = agents.filter((a) => {
    const st = (a.status || '').toLowerCase();
    return a.registered && st !== 'offline' && st !== 'logged_out';
  }).length;
  const longestLabel = fmtSec(Math.max(0, ...(q?.waiting_callers || []).map((c) => waitSeconds(c.wait_fmt))));
  const supExt = phone.creds.extension;

  const runMonitor = async (mode: 'listen' | 'whisper' | 'barge') => {
    if (!selected) {
      setMsg('Select an agent first');
      return;
    }
    if (!supExt) {
      setMsg('Supervisor extension missing — sign in with a SIP user');
      return;
    }
    setMsg(`${mode}…`);
    const r = await monitorAgent({ mode, agentExt: selected, supExt, domain });
    setMsg(r.ok ? `${mode} started on ${selected}` : r.error || `${mode} failed`);
  };

  const setStatus = async (ext: string, status: string) => {
    setMsg('');
    const r = await forceAgentStatus(domain, ext, status);
    setMsg(r.ok ? `${ext} → ${status}` : r.error || 'Status failed');
    await load().catch(() => {});
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="sc-page-title">Dashboard</h1>
          <p className="sc-meta mt-1">
            Live floor · {domain || '—'} · {phone.statusLabel}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {(['listen', 'whisper', 'barge'] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              className="sc-b2 capitalize"
              onClick={() => void runMonitor(mode)}
            >
              {mode === 'barge' ? 'Barge-in' : mode}
            </button>
          ))}
          <Link to="/supervisor/wallboard" className="sc-btn">
            Wallboard
          </Link>
        </div>
      </div>
      {err ? <p className="mb-3 text-sm text-[var(--color-sc-warn)]">{err}</p> : null}
      {msg ? <p className="mb-3 text-sm font-bold">{msg}</p> : null}

      <div className="grid gap-3 sm:grid-cols-4 lg:grid-cols-6">
        <StatCard label="In queue" value={String(waiting)} />
        <StatCard label="Longest wait" value={longestLabel} />
        <StatCard label="Agents online" value={String(online)} />
        <StatCard label="SLA today" value={`${sla || 0}%`} />
        <StatCard label="Answered" value={String(answered)} />
        <StatCard label="Avg talk" value={fmtSec(Number(sum?.avg_talk ?? q?.avg_talk ?? 0))} />
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        <div className="rounded-xl border border-[var(--color-sc-line)] p-4">
          <p className="text-xs uppercase text-[var(--color-sc-muted)]">Today</p>
          <p className="mt-1 sc-section-title">{Number(sum?.total ?? q?.total_today ?? 0)} calls</p>
          <p className="mt-2 text-sm">
            In {inbound} · Out {Number(sum?.outbound ?? q?.outbound_today ?? 0)}
          </p>
        </div>
        <div className="rounded-xl border border-[var(--color-sc-line)] p-4">
          <p className="text-xs uppercase text-[var(--color-sc-muted)]">Abandoned / missed</p>
          <p className="mt-1 sc-section-title">{unhandled}</p>
          <Link to="/supervisor/reports" className="mt-2 inline-block text-sm font-bold text-[var(--color-sc-green)]">
            Open reports
          </Link>
        </div>
        <div className="rounded-xl border border-[var(--color-sc-line)] p-4">
          <p className="text-xs uppercase text-[var(--color-sc-muted)]">Break requests</p>
          <p className="mt-1 sc-section-title">{leaves.length} pending</p>
        </div>
      </div>

      {(q?.waiting_callers || []).length > 0 ? (
        <div className="mt-4 rounded-xl border border-[var(--color-sc-line)] bg-white p-4">
          <h2 className="sc-section-title">Waiting callers</h2>
          <ul className="mt-2 max-h-40 space-y-1 overflow-auto text-sm">
            {(q?.waiting_callers || []).map((c, i) => (
              <li key={`${c.number}-${i}`} className="flex justify-between gap-2">
                <span>{c.number || '—'}</span>
                <span className="text-[var(--color-sc-muted)]">
                  q{c.queue} · {c.wait_fmt || c.state || ''}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mt-4 overflow-hidden rounded-xl border border-[var(--color-sc-line)] bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-[var(--color-sc-soft)] text-[11px] uppercase text-[var(--color-sc-muted)]">
            <tr>
              <th className="px-3 py-2">Agent</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">On call</th>
              <th className="px-3 py-2">Time</th>
              <th className="px-3 py-2">Today</th>
              <th className="px-3 py-2">Force</th>
            </tr>
          </thead>
          <tbody>
            {agents.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-[var(--color-sc-muted)]">
                  No agents loaded
                </td>
              </tr>
            ) : (
              agents.map((a) => {
                const onCall = (a.call_duration || 0) > 0 || !!a.on_call_with;
                const active = selected === a.ext;
                return (
                  <tr
                    key={a.ext}
                    onClick={() => setSelected(a.ext)}
                    className={`cursor-pointer border-t border-[var(--color-sc-line)] ${
                      active ? 'bg-[var(--color-sc-nav-active)]' : 'hover:bg-[var(--color-sc-soft)]'
                    }`}
                  >
                    <td className="px-3 py-2.5 font-semibold">
                      {a.name || a.ext}
                      <span className="ml-1 text-[11px] font-normal text-[var(--color-sc-muted)]">
                        {a.ext}
                        {!a.registered ? ' · SIP down' : ''}
                      </span>
                    </td>
                    <td className="px-3 py-2.5">
                      <StatusPill label={statusLabel(a)} tone={statusTone(a.status)} />
                    </td>
                    <td className="px-3 py-2.5">{a.on_call_with || '—'}</td>
                    <td className="px-3 py-2.5 font-mono text-xs">
                      {onCall ? fmtSec(a.call_duration || 0) : a.status === 'break' ? fmtSec(a.break_secs || 0) : '—'}
                    </td>
                    <td className="px-3 py-2.5 text-xs text-[var(--color-sc-muted)]">
                      {a.answered ?? 0} ans / {a.missed ?? 0} miss
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="flex flex-wrap gap-1">
                        <button
                          type="button"
                          className="sc-b2"
                          onClick={(e) => {
                            e.stopPropagation();
                            void setStatus(a.ext, 'Available');
                          }}
                        >
                          Ready
                        </button>
                        <button
                          type="button"
                          className="sc-b2"
                          onClick={(e) => {
                            e.stopPropagation();
                            void setStatus(a.ext, 'On Break');
                          }}
                        >
                          Break
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-4 rounded-xl border border-[var(--color-sc-line)] bg-white p-4">
        <h2 className="sc-section-title">Break requests</h2>
        {leaves.length === 0 ? (
          <p className="mt-2 text-sm text-[var(--color-sc-muted)]">No pending break requests</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {leaves.map((lv) => (
              <li
                key={lv.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[var(--color-sc-line)] px-3 py-2"
              >
                <div>
                  <p className="text-sm font-semibold">
                    {lv.agent_name || lv.agent_ext} · ext {lv.agent_ext}
                  </p>
                  <p className="text-[11px] text-[var(--color-sc-muted)]">
                    {lv.request_type || 'On Break'}
                    {lv.reason ? ` — ${lv.reason}` : ''}
                    {lv.requested_at ? ` · ${lv.requested_at}` : ''}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    className="sc-btn"
                    onClick={async () => {
                      const r = await resolveLeave(domain, lv.id, 'approved');
                      setMsg(r.ok ? `Approved ${lv.agent_ext}` : r.error || 'Approve failed');
                      await load().catch(() => {});
                    }}
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    className="sc-b2"
                    onClick={async () => {
                      const r = await resolveLeave(domain, lv.id, 'denied');
                      setMsg(r.ok ? `Denied ${lv.agent_ext}` : r.error || 'Deny failed');
                      await load().catch(() => {});
                    }}
                  >
                    Deny
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
