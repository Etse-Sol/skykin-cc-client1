import { useCallback, useEffect, useMemo, useState } from 'react';
import StatusPill from '../../components/StatusPill';
import { fetchAgentSession } from '../../services/session';
import {
  fetchSupAgents,
  fetchSupQueue,
  forceAgentStatus,
  initials,
  monitorAgent,
  statusLabel,
  statusTone,
  type SupAgent,
  type SupQueueRow,
} from '../../services/supervisorApi';
import { useSoftphone } from '../../softphone/SoftphoneContext';

function timeline(a: SupAgent) {
  const st = (a.status || '').toLowerCase();
  if (st === 'incall' || st.includes('call')) {
    return [
      ['#0B7A5A', 40],
      ['#E58A2E', 30],
      ['#0B7A5A', 20],
      ['#C23B3B', 10],
    ];
  }
  if (st === 'ready' || st === 'available') {
    return [
      ['#0B7A5A', 55],
      ['#B9C7BE', 20],
      ['#E8EDE9', 25],
    ];
  }
  if (st === 'break') {
    return [
      ['#E58A2E', 25],
      ['#E8EDE9', 75],
    ];
  }
  return [['#E8EDE9', 100]];
}

export default function TeamRealtime() {
  const phone = useSoftphone();
  const [agents, setAgents] = useState<SupAgent[]>([]);
  const [queues, setQueues] = useState<SupQueueRow[]>([]);
  const [domain, setDomain] = useState('');
  const [team, setTeam] = useState('all');
  const [msg, setMsg] = useState('');

  const load = useCallback(async () => {
    const s = await fetchAgentSession();
    setDomain(s.domain);
    const [ags, q] = await Promise.all([fetchSupAgents(s.domain), fetchSupQueue(s.domain)]);
    setAgents(ags);
    setQueues(q.queues || []);
  }, []);

  useEffect(() => {
    load().catch((e) => setMsg(e instanceof Error ? e.message : 'Load failed'));
    const t = window.setInterval(() => load().catch(() => {}), 8000);
    return () => window.clearInterval(t);
  }, [load]);

  const teams = useMemo(
    () => [{ name: 'All agents', key: 'all', n: agents.length }, ...queues.map((q) => ({ name: q.name || q.extension, key: q.extension, n: q.waiting }))],
    [agents.length, queues],
  );

  const rows = agents;
  const title = team === 'all' ? `All agents (${rows.length})` : `${teams.find((t) => t.key === team)?.name || team}`;

  const runMon = async (mode: 'listen' | 'whisper' | 'barge', ext: string) => {
    const sup = phone.creds.extension;
    if (!sup) {
      setMsg('Supervisor SIP extension missing');
      return;
    }
    const r = await monitorAgent({ mode, agentExt: ext, supExt: sup, domain });
    setMsg(r.ok ? `${mode} ${ext}` : r.error || 'Monitor failed');
  };

  return (
    <div className="flex flex-col gap-[18px]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-[24px] font-bold">{title}</h1>
          <p className="sc-meta mt-1">Roster and performance insights · live from the PBX</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="sc-b2" onClick={() => void load()}>
            Refresh
          </button>
          <button
            type="button"
            className="sc-btn"
            onClick={() => setMsg('Use Whisper on an agent who is on a call')}
          >
            Send message
          </button>
        </div>
      </div>
      {msg ? <p className="text-sm font-bold">{msg}</p> : null}

      <div className="flex flex-wrap items-start gap-4">
        <aside className="sc-card w-full min-w-[220px] max-w-[260px] flex-[0_1_240px]">
          <h2 className="mb-3 text-[16px] font-bold">Teams</h2>
          {teams.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setTeam(t.key)}
              className={`mb-1 flex w-full items-center gap-2.5 rounded-[10px] px-2.5 py-2.5 text-left ${
                team === t.key ? 'bg-[var(--color-sc-nav-active)]' : 'hover:bg-[var(--color-sc-soft)]'
              }`}
            >
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ background: t.key === 'all' ? 'var(--color-sc-gold)' : 'var(--color-sc-green)' }}
              />
              <span>
                <b className="block text-sm">{t.name}</b>
                <span className="sc-meta">{t.key === 'all' ? `${t.n} members` : `${t.n} waiting`}</span>
              </span>
            </button>
          ))}
        </aside>

        <div className="min-w-0 flex-1 overflow-x-auto overflow-hidden rounded-[14px] border border-[var(--color-sc-line)] bg-white">
          <table className="w-full min-w-[820px] text-left text-sm">
            <thead className="bg-[var(--color-sc-soft)] text-[11px] uppercase text-[var(--color-sc-muted)]">
              <tr>
                <th className="px-3 py-2">Member</th>
                <th className="px-3 py-2">State timeline</th>
                <th className="px-3 py-2 text-right">Answered</th>
                <th className="px-3 py-2 text-right">Transferred</th>
                <th className="px-3 py-2 text-right">Conference</th>
                <th className="px-3 py-2">Current state</th>
                <th className="px-3 py-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((a) => (
                <tr key={a.ext} className="border-t border-[var(--color-sc-line)]">
                  <td className="px-3 py-2.5">
                    <div className="flex items-center gap-2">
                      <span className="sc-avatar">{initials(a.name || a.ext)}</span>
                      <span>
                        <b className="block">{a.name || a.ext}</b>
                        <span className="sc-meta">Agent · {a.ext}</span>
                      </span>
                    </div>
                  </td>
                  <td className="px-3 py-2.5">
                    <div className="flex h-2.5 min-w-[160px] overflow-hidden rounded-md bg-[#E8EDE9]">
                      {timeline(a).map(([color, w], i) => (
                        <div key={i} style={{ width: `${w}%`, background: color }} />
                      ))}
                    </div>
                  </td>
                  <td className="px-3 py-2.5 text-right font-bold tabular-nums">{a.answered ?? 0}</td>
                  <td className="px-3 py-2.5 text-right font-bold tabular-nums">{a.transferred ?? 0}</td>
                  <td className="px-3 py-2.5 text-right font-bold tabular-nums">{a.conference ?? 0}</td>
                  <td className="px-3 py-2.5">
                    <StatusPill label={statusLabel(a)} tone={statusTone(a.status)} />
                    {a.on_call_with ? <p className="sc-meta mt-1">{a.on_call_with}</p> : null}
                  </td>
                  <td className="px-3 py-2.5">
                    <div className="flex flex-wrap gap-1">
                      <button type="button" className="sc-b2" onClick={() => void runMon('listen', a.ext)}>
                        Monitor
                      </button>
                      <button
                        type="button"
                        className="sc-b2"
                        onClick={() =>
                          void forceAgentStatus(domain, a.ext, 'Available').then((r) => {
                            setMsg(r.ok ? `${a.ext} Ready` : r.error || 'Failed');
                            return load();
                          })
                        }
                      >
                        Ready
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-3 py-6 text-[var(--color-sc-muted)]">
                    No agents on this domain
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
          <p className="sc-meta px-3 py-2">Total: {rows.length}</p>
        </div>
      </div>
    </div>
  );
}
