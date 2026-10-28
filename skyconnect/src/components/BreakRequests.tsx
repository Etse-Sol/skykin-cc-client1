import StatusPill from './StatusPill';
import {
  floorSnapshot,
  isLoggedIn,
  isOnCall,
  isReady,
  resolveLeave,
  statusLabel,
  statusTone,
  type LeaveRequest,
  type SupAgent,
} from '../services/supervisorApi';

type Props = {
  domain: string;
  leaves: LeaveRequest[];
  agents: SupAgent[];
  waiting: number;
  onDone: (msg: string) => void;
};

export default function BreakRequests({ domain, leaves, agents, waiting, onDone }: Props) {
  const floor = floorSnapshot(agents);

  const decide = async (lv: LeaveRequest, decision: 'approved' | 'denied') => {
    const r = await resolveLeave(domain, lv.id, decision);
    onDone(r.ok ? `${decision === 'approved' ? 'Approved' : 'Denied'} ${lv.agent_ext}` : r.error || 'Request failed');
  };

  return (
    <section className="rounded-xl border border-[var(--color-sc-line)] bg-white p-4">
      <h2 className="text-[16px] font-bold">Break requests</h2>
      <p className="sc-meta mt-1">
        Review coverage before you accept. Floor now: {floor.online} online · {floor.ready} ready · {floor.onCall}{' '}
        on call · {waiting} in queue
      </p>
      {leaves.length === 0 ? (
        <p className="mt-2 text-sm text-[var(--color-sc-muted)]">No pending break requests</p>
      ) : (
        <ul className="mt-3 space-y-3">
          {leaves.map((lv) => {
            const others = agents.filter((a) => a.ext !== lv.agent_ext);
            const remainReady = others.filter(isReady).length;
            const remainOnline = others.filter(isLoggedIn).length;
            const remainOnCall = others.filter(isOnCall).length;
            const tight = remainReady <= 0 || (waiting > 0 && remainReady < 2);
            return (
              <li key={lv.id} className="rounded-lg border border-[var(--color-sc-line)] px-3 py-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
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
                      title={tight ? 'Coverage is thin — confirm you still want to approve' : 'Approve'}
                      onClick={() => {
                        if (tight && !window.confirm('Few agents would remain ready. Approve this break anyway?')) {
                          return;
                        }
                        void decide(lv, 'approved');
                      }}
                    >
                      Approve
                    </button>
                    <button type="button" className="sc-b2" onClick={() => void decide(lv, 'denied')}>
                      Deny
                    </button>
                  </div>
                </div>
                <p className={`mt-2 text-sm ${tight ? 'font-bold text-[var(--color-sc-warn)]' : ''}`}>
                  If approved: {remainOnline} still online · {remainReady} ready · {remainOnCall} on call · {waiting}{' '}
                  waiting
                  {tight ? ' — coverage is thin.' : ''}
                </p>
                <ul className="mt-2 grid gap-1 sm:grid-cols-2">
                  {agents.map((a) => (
                    <li key={a.ext} className="flex items-center justify-between gap-2 text-sm">
                      <span>
                        {a.name || a.ext}
                        <span className="sc-meta"> · {a.ext}</span>
                        {a.ext === lv.agent_ext ? <span className="sc-meta"> · this request</span> : null}
                      </span>
                      <StatusPill label={statusLabel(a)} tone={statusTone(a.status)} />
                    </li>
                  ))}
                </ul>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
