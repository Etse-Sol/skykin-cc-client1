import { useCallback, useEffect, useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import StatusPill from '../../components/StatusPill';
import { useSoftphone } from '../../softphone/SoftphoneContext';
import { fetchAgentSession, type AgentSession } from '../../services/session';
import {
  avgHandleLabel,
  fetchAgentStats,
  queuesWithWaiting,
  type AgentStats,
} from '../../services/agentStats';
import type { UiStatus } from '../../services/agentStatus';
import type { HistoryRow } from '../../services/callHistory';

type Ctx = {
  session: AgentSession | null;
  name: string;
  status: UiStatus;
  changeStatus: (s: UiStatus) => Promise<void>;
  initials: string;
  ext: string;
  lastCall: HistoryRow | null;
  lastNumber: string;
  onRedialLast: () => void;
};

function fmtClock(sec: number) {
  const n = Math.max(0, Math.floor(sec || 0));
  const h = Math.floor(n / 3600)
    .toString()
    .padStart(2, '0');
  const m = Math.floor((n % 3600) / 60)
    .toString()
    .padStart(2, '0');
  const s = (n % 60).toString().padStart(2, '0');
  return `${h}:${m}:${s}`;
}

export default function AgentHome() {
  const { name, status, changeStatus, initials, ext, lastCall, lastNumber, onRedialLast } =
    useOutletContext<Ctx>();
  const phone = useSoftphone();
  const [stats, setStats] = useState<AgentStats | null>(null);
  const [err, setErr] = useState('');
  const [since, setSince] = useState(0);

  const load = useCallback(async () => {
    try {
      const session = await fetchAgentSession();
      const s = await fetchAgentStats({
        agent: session.username,
        domain: session.domain,
        ext: phone.creds.extension || session.extension,
      });
      setStats(s);
      setErr(s.db_error || '');
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Stats failed');
    }
  }, [phone.creds.extension]);

  useEffect(() => {
    load();
    const t = window.setInterval(load, 10000);
    return () => clearInterval(t);
  }, [load]);

  useEffect(() => {
    const t0 = Date.now();
    const t = window.setInterval(() => setSince(Math.floor((Date.now() - t0) / 1000)), 1000);
    return () => clearInterval(t);
  }, []);

  const queues = stats ? queuesWithWaiting(stats) : [];
  const total = Number(stats?.total_calls ?? 0);
  const inbound = Number(stats?.inbound_calls ?? 0);
  const outbound = Number(stats?.outbound_calls ?? 0);
  const answered = Number(stats?.answered_calls ?? 0);
  const missed = Math.max(0, inbound > 0 ? inbound - answered : total - answered);
  const aht = stats ? avgHandleLabel(stats) : '00:00';
  const ready = status === 'Available';

  return (
    <div className="flex flex-col gap-[18px]">
      <div className="sc-hero">
        <span className="inline-flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-white text-[22px] font-extrabold text-[#0B5C44]">
          {initials}
        </span>
        <div className="min-w-0 flex-[1_1_300px]">
          <h1 className="sc-hero-name">
            {name}
            <span className="sc-hero-role">Agent</span>
          </h1>
          <p className="sc-hero-meta">
            Extension {ext} · Logged in {fmtClock(since)} · {ready ? 'Ready' : status} {fmtClock(since)}
          </p>
        </div>
        <button type="button" className="sc-hero-go" onClick={() => void changeStatus('Available')}>
          Go Ready
        </button>
      </div>

      <div className="sc-kpi-row">
        <div className="sc-kpi" style={{ background: 'linear-gradient(135deg,#0B6B50,#12957A)' }}>
          <p className="lbl">TOTAL CALLS</p>
          <p className="n">{stats ? total || inbound + outbound : '—'}</p>
          <p className="mt-1 text-[13px]">{inbound} inbound</p>
        </div>
        <div className="sc-kpi" style={{ background: 'linear-gradient(135deg,#7A4F00,#A66A00)' }}>
          <p className="lbl">DIGITAL</p>
          <p className="n">{outbound}</p>
          <p className="mt-1 text-[13px]">{outbound} outbound</p>
        </div>
        <div className="sc-kpi" style={{ background: 'linear-gradient(135deg,#1F5F7A,#2A7897)' }}>
          <p className="lbl">TRANSFERS</p>
          <p className="n">0</p>
          <p className="mt-1 text-[13px]">0 conferences</p>
        </div>
        <div className="sc-kpi" style={{ background: 'linear-gradient(135deg,#A12B2B,#C03A34)' }}>
          <p className="lbl">MISSED</p>
          <p className="n">{stats ? missed : '—'}</p>
          <p className="mt-1 text-[13px]">{stats?.queue_waiting ?? 0} waiting now</p>
        </div>
      </div>
      {err ? <p className="text-[12px] text-[var(--color-sc-warn)]">{err}</p> : null}

      <section className="sc-card">
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2 className="text-[16px] font-bold">Last call</h2>
          <Link
            to="/agent/history"
            className="text-[12px] font-bold text-[var(--color-sc-green)] hover:underline"
          >
            Full history
          </Link>
        </div>
        {lastNumber ? (
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-[22px] font-extrabold tracking-tight text-[var(--color-sc-forest)]">
                {lastNumber}
              </p>
              <p className="mt-1 text-[13px] text-[var(--color-sc-muted)]">
                {lastCall
                  ? `${lastCall.type} · ${lastCall.status} · ${lastCall.duration || '—'} · ${lastCall.time}`
                  : 'Last number on this phone (CDR still catching up)'}
              </p>
            </div>
            <button type="button" className="sc-btn" onClick={onRedialLast}>
              Call back
            </button>
          </div>
        ) : (
          <p className="text-sm text-[var(--color-sc-muted)]">
            No last call yet. After you finish a call, the number appears here.
          </p>
        )}
      </section>

      <div className="sc-kpi-row">
        <section className="sc-card min-w-0 flex-[2_1_460px]">
          <h2 className="mb-[14px] text-[16px] font-bold">Session efficiency</h2>
          <div className="grid grid-cols-2 gap-[14px] sm:grid-cols-4">
            {[
              ['AVG ACTIVE', aht.length === 5 ? `00:${aht}` : aht],
              ['TOTAL ACTIVE', fmtClock(Number(stats?.avg_duration || 0) * answered)],
              ['ANSWERED', String(answered)],
              ['WAITING', String(stats?.queue_waiting ?? 0)],
            ].map(([k, v]) => (
              <div key={k}>
                <p className="text-[11px] font-bold tracking-wide text-[var(--color-sc-muted)]">{k}</p>
                <p className="mt-1 text-[18px] font-bold">{v}</p>
              </div>
            ))}
          </div>
        </section>
        <section className="sc-card min-w-0 flex-[1_1_280px]">
          <h2 className="mb-3 text-[16px] font-bold">My queues</h2>
          <div className="space-y-3">
            {queues.length === 0 ? (
              <p className="text-sm text-[var(--color-sc-muted)]">Loading queues…</p>
            ) : (
              queues.map((q) => (
                <div key={q.ext} className="flex items-center justify-between">
                  <span className="text-sm">
                    {q.name}
                    <span className="text-[var(--color-sc-muted)]"> · {q.ext}</span>
                  </span>
                  <StatusPill label={`${q.waiting} waiting`} tone={q.waiting > 0 ? 'ok' : 'blue'} />
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
