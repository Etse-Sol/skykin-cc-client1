/** Live supervisor APIs — same supervisor.php actions as the old board. */

const SUP = '/app/agent_dashboard/supervisor.php';

export type SupAgent = {
  ext: string;
  name: string;
  status: string;
  cc_status?: string;
  registered?: boolean;
  call_duration?: number;
  on_call_with?: string | null;
  total_calls?: number;
  answered?: number;
  missed?: number;
  transferred?: number;
  conference?: number;
  total_talk?: number;
  leave_pending?: { id: number; request_type?: string } | null;
  break_secs?: number;
};

export type SupQueueRow = {
  name: string;
  extension: string;
  waiting: number;
};

export type SupQueuePayload = {
  queues?: SupQueueRow[];
  waiting_callers?: { number?: string; queue?: string; wait_fmt?: string; state?: string }[];
  total_today?: number;
  inbound_today?: number;
  outbound_today?: number;
  answered_today?: number;
  abandoned_today?: number;
  missed_today?: number;
  avg_talk?: number;
  sla?: number;
  agents_online?: number;
  error?: string;
};

function fmtSec(sec: number): string {
  const n = Math.max(0, Math.floor(sec || 0));
  const m = Math.floor(n / 60)
    .toString()
    .padStart(2, '0');
  const s = (n % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

export { fmtSec };

export async function fetchSupAgents(domain: string): Promise<SupAgent[]> {
  const q = new URLSearchParams({ action: 'agents', domain });
  const r = await fetch(`${SUP}?${q}`, { credentials: 'same-origin', cache: 'no-store' });
  if (!r.ok) throw new Error(`agents ${r.status}`);
  const data = await r.json();
  return Array.isArray(data?.agents) ? data.agents : [];
}

export async function fetchSupQueue(domain: string): Promise<SupQueuePayload> {
  const q = new URLSearchParams({ action: 'queue', domain });
  const r = await fetch(`${SUP}?${q}`, { credentials: 'same-origin', cache: 'no-store' });
  if (!r.ok) throw new Error(`queue ${r.status}`);
  return r.json();
}

export async function monitorAgent(opts: {
  mode: 'listen' | 'whisper' | 'barge';
  agentExt: string;
  supExt: string;
  domain: string;
}): Promise<{ ok: boolean; error?: string; result?: string }> {
  const q = new URLSearchParams({
    action: 'monitor',
    mode: opts.mode,
    agent_ext: opts.agentExt,
    sup_ext: opts.supExt,
    domain: opts.domain,
  });
  const r = await fetch(`${SUP}?${q}`, { credentials: 'same-origin', cache: 'no-store' });
  return r.json();
}

export function statusTone(status: string): 'ok' | 'idle' | 'busy' | 'warn' {
  const s = (status || '').toLowerCase();
  if (s === 'ready' || s === 'available') return 'ok';
  if (s === 'break' || s === 'offline' || s === 'logged_out') return 'idle';
  if (s === 'incall' || s === 'on_call' || s.includes('call')) return 'busy';
  return 'warn';
}

export function statusLabel(a: SupAgent): string {
  const s = (a.status || '').toLowerCase();
  if (s === 'ready' || s === 'available') return 'Ready';
  if (s === 'break') return 'Not ready';
  if (s === 'incall' || s === 'on_call') return 'On call';
  if (s === 'offline' || s === 'logged_out') return 'Logged out';
  if (a.cc_status) return a.cc_status;
  return a.status || '—';
}

export function isLoggedIn(a: SupAgent): boolean {
  const st = (a.status || '').toLowerCase();
  return !!a.registered && st !== 'offline' && st !== 'logged_out';
}

export function isReady(a: SupAgent): boolean {
  const st = (a.status || '').toLowerCase();
  return isLoggedIn(a) && (st === 'ready' || st === 'available');
}

export function isOnCall(a: SupAgent): boolean {
  const st = (a.status || '').toLowerCase();
  return (a.call_duration || 0) > 0 || !!a.on_call_with || st === 'incall' || st === 'on_call' || st.includes('call');
}

export function isOnBreak(a: SupAgent): boolean {
  return (a.status || '').toLowerCase() === 'break';
}

export function floorSnapshot(agents: SupAgent[]) {
  const online = agents.filter(isLoggedIn);
  const ready = agents.filter(isReady);
  const onCall = agents.filter(isOnCall);
  const onBreak = agents.filter(isOnBreak);
  return {
    total: agents.length,
    online: online.length,
    ready: ready.length,
    onCall: onCall.length,
    onBreak: onBreak.length,
    offline: Math.max(0, agents.length - online.length),
    onlineAgents: online,
    readyAgents: ready,
  };
}

export function initials(name: string): string {
  const p = (name || '').trim().split(/\s+/).filter(Boolean);
  if (p.length >= 2) return (p[0][0] + p[1][0]).toUpperCase();
  return (name || '?').slice(0, 2).toUpperCase();
}

export function fmtHms(sec: number): string {
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

export type LeaveRequest = {
  id: number;
  agent_ext: string;
  agent_name?: string;
  request_type?: string;
  reason?: string;
  status?: string;
  requested_at?: string;
};

export async function fetchRecordingsAll(
  domain: string,
  from: string,
  to: string,
): Promise<any[]> {
  const q = new URLSearchParams({ action: 'recordings_all', domain, from, to });
  const r = await fetch(`${SUP}?${q}`, { credentials: 'same-origin', cache: 'no-store' });
  if (!r.ok) throw new Error(`recordings ${r.status}`);
  const data = await r.json();
  return Array.isArray(data?.rows) ? data.rows : [];
}

export async function fetchCallHistoryAll(
  domain: string,
  from: string,
  to: string,
  search = '',
): Promise<any[]> {
  const q = new URLSearchParams({ action: 'call_history_all', domain, from, to });
  if (search.trim()) q.set('search', search.trim());
  const r = await fetch(`${SUP}?${q}`, { credentials: 'same-origin', cache: 'no-store' });
  if (!r.ok) throw new Error(`call history ${r.status}`);
  const data = await r.json();
  return Array.isArray(data?.rows) ? data.rows : Array.isArray(data) ? data : [];
}

export async function fetchLeaveRequests(domain: string): Promise<LeaveRequest[]> {
  const q = new URLSearchParams({ action: 'leave_requests', domain });
  const r = await fetch(`${SUP}?${q}`, { credentials: 'same-origin', cache: 'no-store' });
  if (!r.ok) throw new Error(`leave ${r.status}`);
  const data = await r.json();
  return Array.isArray(data?.requests) ? data.requests : [];
}

export async function forceAgentStatus(
  domain: string,
  agentExt: string,
  status: string,
): Promise<{ ok?: boolean; error?: string }> {
  const q = new URLSearchParams({
    action: 'force_status',
    domain,
    agent_ext: agentExt,
    status,
  });
  const r = await fetch(`${SUP}?${q}`, { credentials: 'same-origin', cache: 'no-store' });
  return r.json();
}

export async function resolveLeave(
  domain: string,
  id: number,
  decision: 'approved' | 'denied',
): Promise<{ ok: boolean; error?: string }> {
  const r = await fetch(`${SUP}?action=resolve_leave`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, decision, domain }),
  });
  return r.json();
}
