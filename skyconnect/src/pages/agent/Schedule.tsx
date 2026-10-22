import { useEffect, useState } from 'react';
import { fetchAgentSession } from '../../services/session';
import { myLeaveRequest } from '../../services/agentStatus';
import { opsGet } from '../../services/ops';

type Day = { day: string; shift: string; note: string; today?: boolean };

export default function AgentSchedule() {
  const [days, setDays] = useState<Day[]>([]);
  const [leave, setLeave] = useState<string>('');
  const [err, setErr] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const s = await fetchAgentSession();
        const data = await opsGet('me_schedule', { domain: s.domain, ext: s.extension });
        setDays(Array.isArray(data.week) ? data.week : []);
        const lr = await myLeaveRequest(s.extension, s.domain);
        if (lr.request) {
          setLeave(`${lr.request.request_type || 'Request'} · ${lr.request.status}`);
        }
      } catch (e) {
        setErr(e instanceof Error ? e.message : 'Could not load schedule');
      }
    })();
  }, []);

  return (
    <div>
      <h1 className="mb-1 sc-page-title">My schedule</h1>
      <p className="mb-4 text-sm text-[var(--color-sc-muted)]">
        Live roster from your queue hours and leave requests
        {leave ? ` · ${leave}` : ''}
      </p>
      {err ? <p className="mb-3 text-sm text-[var(--color-sc-warn)]">{err}</p> : null}
      <div className="grid gap-2 sm:grid-cols-7">
        {days.map((d) => (
          <div
            key={d.day}
            className={`rounded-xl border p-3 text-center ${
              d.today
                ? 'border-[var(--color-sc-green)] bg-[var(--color-sc-nav-active)]'
                : 'border-[var(--color-sc-line)] bg-[var(--color-sc-soft)]'
            }`}
          >
            <p className="text-xs font-bold uppercase text-[var(--color-sc-muted)]">{d.day}</p>
            <p className="mt-2 sc-section-title">{d.shift}</p>
            <p className="mt-1 text-[11px] text-[var(--color-sc-muted)]">{d.note}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
