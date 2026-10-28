import { useCallback, useEffect, useMemo, useState } from 'react';
import StatusPill from '../../components/StatusPill';
import { fetchAgentSession } from '../../services/session';
import { fetchReportSummary, opsGet, opsPost, todayRange } from '../../services/ops';
import {
  fetchSupAgents,
  fetchSupQueue,
  floorSnapshot,
  fmtSec,
  initials,
  statusLabel,
  statusTone,
  type SupAgent,
} from '../../services/supervisorApi';

const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const DAY_VALS = [1, 2, 3, 4, 5, 6, 7];

type Shift = {
  shift_id: number;
  name: string;
  start_hm: string;
  end_hm: string;
  days: string;
  notes?: string;
};
type Holiday = { holiday_id: number; holiday_date: string; name: string };
type Assign = { agent_ext: string; agent_name?: string; shift_id: number; weekend_off?: string };

function mondayYmd(): string {
  const d = new Date();
  const day = d.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + diff);
  return d.toISOString().slice(0, 10);
}

function addDays(ymd: string, n: number): string {
  const d = new Date(ymd + 'T12:00:00');
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}

function cellFor(shift: Shift | undefined, weekendOff: boolean, holidays: Record<string, string>, dow: number, ymd: string) {
  if (holidays[ymd]) return { label: 'Holiday', off: true, note: holidays[ymd] };
  const days = (shift?.days || '')
    .split(',')
    .map((x) => parseInt(x, 10))
    .filter((n) => n >= 1 && n <= 7);
  if (shift && days.includes(dow)) {
    return { label: `${shift.start_hm}–${shift.end_hm}`, off: false, note: shift.name };
  }
  if (weekendOff && (dow === 6 || dow === 7)) return { label: 'Off', off: true, note: 'Weekend' };
  return { label: 'Off', off: true, note: '' };
}

export default function WfmSchedule() {
  const [agents, setAgents] = useState<SupAgent[]>([]);
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [holidays, setHolidays] = useState<Holiday[]>([]);
  const [assign, setAssign] = useState<Assign[]>([]);
  const [bulkShift, setBulkShift] = useState('');
  const [bulkWeekendOff, setBulkWeekendOff] = useState(true);
  const [hDate, setHDate] = useState('');
  const [hName, setHName] = useState('');
  const [shiftForm, setShiftForm] = useState({ name: '', start_hm: '08:00', end_hm: '16:00', days: ['1', '2', '3', '4', '5'] });
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [domain, setDomain] = useState('');
  const [waiting, setWaiting] = useState(0);
  const [perf, setPerf] = useState({ inbound: 0, answered: 0, missed: 0, abandoned: 0, avgTalk: 0, sla: 0 });

  const applyPack = (data: any) => {
    setShifts(Array.isArray(data.shifts) ? data.shifts : []);
    setHolidays(Array.isArray(data.holidays) ? data.holidays : []);
    setAssign(Array.isArray(data.assign) ? data.assign : []);
  };

  const load = useCallback(async () => {
    const s = await fetchAgentSession();
    setDomain(s.domain);
    const { from, to } = todayRange();
    const [ags, wfm, q, sm] = await Promise.all([
      fetchSupAgents(s.domain),
      opsGet('wfm', { domain: s.domain }),
      fetchSupQueue(s.domain).catch(() => null),
      fetchReportSummary(s.domain, from, to).catch(() => ({})),
    ]);
    setAgents(ags);
    applyPack(wfm);
    setBulkShift((cur) => cur || (wfm.shifts?.[0] ? String(wfm.shifts[0].shift_id) : ''));
    const waitN =
      q?.waiting_callers?.length ?? Number(q?.queues?.reduce((n, r) => n + (r.waiting || 0), 0) || 0);
    setWaiting(waitN);
    const inbound = Number(sm.inbound ?? q?.inbound_today ?? 0);
    const answered = Number(sm.answered ?? q?.answered_today ?? 0);
    const missed = Number(sm.missed ?? q?.missed_today ?? 0);
    const abandoned = Number(sm.abandoned ?? q?.abandoned_today ?? 0);
    setPerf({
      inbound,
      answered,
      missed,
      abandoned,
      avgTalk: Number(sm.avg_talk ?? q?.avg_talk ?? 0),
      sla: inbound > 0 ? Math.round((answered / inbound) * 100) : Number(q?.sla ?? 0),
    });
    setErr('');
  }, []);

  useEffect(() => {
    load().catch((e) => setErr(e instanceof Error ? e.message : 'Workforce load failed'));
    const t = window.setInterval(() => load().catch(() => {}), 8000);
    return () => window.clearInterval(t);
  }, [load]);

  const asgByExt = useMemo(() => {
    const m: Record<string, Assign> = {};
    for (const a of assign) m[String(a.agent_ext)] = a;
    return m;
  }, [assign]);
  const shiftById = useMemo(() => {
    const m: Record<string, Shift> = {};
    for (const s of shifts) m[String(s.shift_id)] = s;
    return m;
  }, [shifts]);
  const holidayMap = useMemo(() => {
    const m: Record<string, string> = {};
    for (const h of holidays) m[h.holiday_date] = h.name;
    return m;
  }, [holidays]);

  const weekStart = mondayYmd();
  const unassigned = agents.filter((a) => !asgByExt[a.ext]);
  const floor = floorSnapshot(agents);
  const jsDow = new Date().getDay();
  const todayDow = jsDow === 0 ? 7 : jsDow;
  const todayYmd = new Date().toISOString().slice(0, 10);
  const scheduled = agents.filter((a) => {
    const asg = asgByExt[a.ext];
    const sh = asg ? shiftById[String(asg.shift_id)] : undefined;
    if (holidayMap[todayYmd]) return false;
    const days = (sh?.days || '')
      .split(',')
      .map((x) => parseInt(x, 10))
      .filter((n) => n >= 1 && n <= 7);
    return !!sh && days.includes(todayDow);
  }).length;

  const saveShift = async () => {
    if (!shiftForm.name.trim()) return;
    const data = await opsPost(
      'wfm_shift_save',
      {
        name: shiftForm.name.trim(),
        start_hm: shiftForm.start_hm,
        end_hm: shiftForm.end_hm,
        days: shiftForm.days.join(','),
        notes: shiftForm.days.includes('6') || shiftForm.days.includes('7') ? 'Includes weekend' : 'Weekdays',
      },
      { domain },
    );
    applyPack(data);
    setShiftForm({ ...shiftForm, name: '' });
    setMsg('Shift saved');
  };

  const assignAgents = async (list: { ext: string; name: string }[], shiftId: string, weekendOff: boolean) => {
    if (!shiftId || list.length === 0) {
      setMsg('Pick a shift and at least one agent');
      return;
    }
    const data = await opsPost(
      'wfm_assign',
      { shift_id: Number(shiftId), weekend_off: weekendOff, agents: list },
      { domain },
    );
    applyPack(data);
    setMsg(`Assigned ${list.length} agent(s)`);
  };

  return (
    <div className="flex flex-col gap-[18px]">
      <div>
        <h1 className="text-[24px] font-bold">Workforce</h1>
        <p className="sc-meta mt-1">
          Intraday floor plus weekly roster. Weekends and holidays are off unless the shift includes those days.
        </p>
      </div>
      {err ? <p className="text-sm text-[var(--color-sc-warn)]">{err}</p> : null}
      {msg ? <p className="text-sm font-bold">{msg}</p> : null}

      <section className="sc-card">
        <h2 className="text-[16px] font-bold">Intraday</h2>
        <p className="sc-meta mt-1">Live online count versus today&apos;s actual performance</p>
        <div className="mt-3 grid gap-3 sm:grid-cols-4 lg:grid-cols-8">
          {[
            ['Online now', String(floor.online)],
            ['Ready', String(floor.ready)],
            ['On call', String(floor.onCall)],
            ['On break', String(floor.onBreak)],
            ['Scheduled today', String(scheduled)],
            ['In queue', String(waiting)],
            ['Answered', String(perf.answered)],
            ['SLA', `${perf.sla || 0}%`],
          ].map(([k, v]) => (
            <div key={k} className="rounded-[12px] border border-[var(--color-sc-line)] bg-[var(--color-sc-soft)] px-3 py-2">
              <p className="text-[11px] font-bold uppercase tracking-wide text-[var(--color-sc-muted)]">{k}</p>
              <p className="mt-1 text-[22px] font-extrabold tabular-nums">{v}</p>
            </div>
          ))}
        </div>
        <p className="sc-meta mt-3">
          Missed {perf.missed} · abandoned {perf.abandoned} · inbound {perf.inbound} · avg talk {fmtSec(perf.avgTalk)} ·{' '}
          {floor.online} of {scheduled || floor.total} scheduled are online
        </p>
        <ul className="mt-3 grid gap-1 sm:grid-cols-2 lg:grid-cols-3">
          {agents.map((a) => (
            <li key={a.ext} className="flex items-center justify-between gap-2 text-sm">
              <span>
                {a.name || a.ext}
                <span className="sc-meta"> · {a.ext}</span>
              </span>
              <StatusPill label={statusLabel(a)} tone={statusTone(a.status)} />
            </li>
          ))}
        </ul>
      </section>

      <div className="flex flex-wrap items-start gap-4">
        <section className="sc-card min-w-[260px] flex-[1_1_280px]">
          <h2 className="text-[16px] font-bold">Shifts</h2>
          <ul className="mt-2 space-y-2 text-sm">
            {shifts.map((s) => (
              <li key={s.shift_id} className="flex items-start justify-between gap-2 rounded-lg border border-[var(--color-sc-line)] p-2">
                <span>
                  <b>{s.name}</b>
                  <span className="sc-meta block">
                    {s.start_hm}–{s.end_hm} · days {s.days}
                  </span>
                </span>
                <button
                  type="button"
                  className="sc-b2"
                  onClick={async () => {
                    applyPack(await opsPost('wfm_shift_delete', { shift_id: s.shift_id }, { domain }));
                  }}
                >
                  Del
                </button>
              </li>
            ))}
          </ul>
          <input
            className="sc-input mt-3 w-full"
            placeholder="New shift name"
            value={shiftForm.name}
            onChange={(e) => setShiftForm({ ...shiftForm, name: e.target.value })}
          />
          <div className="mt-2 flex gap-2">
            <input className="sc-input" type="time" value={shiftForm.start_hm} onChange={(e) => setShiftForm({ ...shiftForm, start_hm: e.target.value })} />
            <input className="sc-input" type="time" value={shiftForm.end_hm} onChange={(e) => setShiftForm({ ...shiftForm, end_hm: e.target.value })} />
          </div>
          <div className="mt-2 flex flex-wrap gap-1">
            {DAY_VALS.map((d, i) => {
              const on = shiftForm.days.includes(String(d));
              return (
                <button
                  key={d}
                  type="button"
                  className={`sc-chip ${on ? 'sc-chip-call' : 'sc-chip-ready'}`}
                  onClick={() =>
                    setShiftForm((p) => ({
                      ...p,
                      days: on ? p.days.filter((x) => x !== String(d)) : [...p.days, String(d)],
                    }))
                  }
                >
                  {DAY_NAMES[i]}
                </button>
              );
            })}
          </div>
          <button type="button" className="sc-btn mt-3 w-full" onClick={() => void saveShift()}>
            Add shift
          </button>
        </section>

        <section className="sc-card min-w-[260px] flex-[1_1_280px]">
          <h2 className="text-[16px] font-bold">Holidays</h2>
          <ul className="mt-2 max-h-48 space-y-1 overflow-auto text-sm">
            {holidays.map((h) => (
              <li key={h.holiday_id} className="flex justify-between gap-2">
                <span>
                  {h.holiday_date} · {h.name}
                </span>
                <button
                  type="button"
                  className="sc-b2"
                  onClick={async () => applyPack(await opsPost('wfm_holiday_delete', { holiday_id: h.holiday_id }, { domain }))}
                >
                  Del
                </button>
              </li>
            ))}
          </ul>
          <div className="mt-3 flex flex-col gap-2">
            <input className="sc-input" type="date" value={hDate} onChange={(e) => setHDate(e.target.value)} />
            <input className="sc-input" placeholder="Holiday name" value={hName} onChange={(e) => setHName(e.target.value)} />
            <button
              type="button"
              className="sc-btn"
              onClick={async () => {
                if (!hDate) return;
                applyPack(await opsPost('wfm_holiday_save', { holiday_date: hDate, name: hName || 'Holiday' }, { domain }));
                setHName('');
              }}
            >
              Add holiday
            </button>
          </div>
        </section>

        <section className="sc-card min-w-[260px] flex-[1_1_280px]">
          <h2 className="text-[16px] font-bold">Assign all agents</h2>
          <p className="sc-meta mt-1">
            {unassigned.length} unassigned of {agents.length}
          </p>
          <select className="sc-input mt-3 w-full" value={bulkShift} onChange={(e) => setBulkShift(e.target.value)}>
            <option value="">Choose shift</option>
            {shifts.map((s) => (
              <option key={s.shift_id} value={s.shift_id}>
                {s.name} ({s.start_hm}–{s.end_hm})
              </option>
            ))}
          </select>
          <label className="mt-3 flex items-center gap-2 text-sm">
            <input type="checkbox" checked={bulkWeekendOff} onChange={(e) => setBulkWeekendOff(e.target.checked)} />
            Weekend off (Sat–Sun) unless the shift includes those days
          </label>
          <button
            type="button"
            className="sc-btn mt-3 w-full"
            onClick={() =>
              void assignAgents(
                agents.map((a) => ({ ext: a.ext, name: a.name || a.ext })),
                bulkShift,
                bulkWeekendOff,
              )
            }
          >
            Assign all agents
          </button>
          <button
            type="button"
            className="sc-b2 mt-2 w-full"
            onClick={() =>
              void assignAgents(
                unassigned.map((a) => ({ ext: a.ext, name: a.name || a.ext })),
                bulkShift,
                bulkWeekendOff,
              )
            }
          >
            Assign unassigned only
          </button>
        </section>
      </div>

      <section className="overflow-x-auto rounded-[14px] border border-[var(--color-sc-line)] bg-white">
        <p className="bg-[var(--color-sc-soft)] px-3 py-2 text-[16px] font-bold">This week · from {weekStart}</p>
        <table className="w-full min-w-[920px] text-left text-sm">
          <thead className="text-[11px] uppercase text-[var(--color-sc-muted)]">
            <tr>
              <th className="px-3 py-2">Agent</th>
              <th className="px-3 py-2">Shift</th>
              {DAY_NAMES.map((d, i) => (
                <th key={d} className="px-2 py-2 text-center">
                  {d}
                  <span className="sc-meta block">{addDays(weekStart, i).slice(5)}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {agents.map((a) => {
              const asg = asgByExt[a.ext];
              const sh = asg ? shiftById[String(asg.shift_id)] : undefined;
              const woff = !asg || String(asg.weekend_off) !== 'false';
              return (
                <tr key={a.ext} className="border-t border-[var(--color-sc-line)]">
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      <span className="sc-avatar">{initials(a.name || a.ext)}</span>
                      <span>
                        <b className="block">{a.name || a.ext}</b>
                        <span className="sc-meta">{a.ext}</span>
                      </span>
                    </div>
                  </td>
                  <td className="px-3 py-2">
                    <select
                      className="sc-input min-h-[36px] py-1"
                      value={asg ? String(asg.shift_id) : ''}
                      onChange={(e) =>
                        void assignAgents([{ ext: a.ext, name: a.name || a.ext }], e.target.value, woff)
                      }
                    >
                      <option value="">Unassigned</option>
                      {shifts.map((s) => (
                        <option key={s.shift_id} value={s.shift_id}>
                          {s.name}
                        </option>
                      ))}
                    </select>
                  </td>
                  {DAY_VALS.map((dow, i) => {
                    const c = cellFor(sh, woff, holidayMap, dow, addDays(weekStart, i));
                    return (
                      <td key={dow} className="px-1 py-2 text-center">
                        <StatusPill label={c.label} tone={c.off ? 'idle' : 'ok'} />
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </div>
  );
}
