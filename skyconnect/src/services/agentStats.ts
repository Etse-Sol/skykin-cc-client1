/** Agent dashboard stats — same PHP action=stats as the old UI. */

export type WaitingCaller = {
  number?: string;
  name?: string;
  queue?: string;
  state?: string;
  wait_seconds?: number;
  wait_fmt?: string;
};

export type AgentQueue = {
  queue_name?: string;
  queue_extension?: string;
  tier_level?: string | number;
  tier_position?: string | number;
};

export type AgentStats = {
  total_calls?: number;
  inbound_calls?: number;
  outbound_calls?: number;
  answered_calls?: number;
  avg_duration?: number;
  queue_waiting?: number;
  agents_online?: number;
  agent_queues?: AgentQueue[];
  waiting_callers?: WaitingCaller[];
  resolved_ext?: string;
  db_error?: string;
};

function fmtDur(sec: number): string {
  if (!sec || sec <= 0) return '00:00';
  const m = Math.floor(sec / 60)
    .toString()
    .padStart(2, '0');
  const s = Math.floor(sec % 60)
    .toString()
    .padStart(2, '0');
  return `${m}:${s}`;
}

export async function fetchAgentStats(opts: {
  agent: string;
  domain: string;
  ext?: string;
}): Promise<AgentStats> {
  const q = new URLSearchParams({
    action: 'stats',
    agent: opts.agent,
    domain: opts.domain,
  });
  if (opts.ext) q.set('ext', opts.ext);
  const r = await fetch(`/app/agent_dashboard/index.php?${q}`, {
    credentials: 'same-origin',
    cache: 'no-store',
  });
  if (!r.ok) throw new Error(`stats ${r.status}`);
  return r.json();
}

export function avgHandleLabel(stats: AgentStats): string {
  return fmtDur(Number(stats.avg_duration || 0));
}

/** Group waiting callers by queue extension for Home “My queues”. */
export function queuesWithWaiting(stats: AgentStats): { name: string; ext: string; waiting: number }[] {
  const byExt: Record<string, number> = {};
  for (const c of stats.waiting_callers || []) {
    const q = String(c.queue || '8000');
    byExt[q] = (byExt[q] || 0) + 1;
  }
  const rows: { name: string; ext: string; waiting: number }[] = [];
  const seen = new Set<string>();
  for (const q of stats.agent_queues || []) {
    const ext = String(q.queue_extension || '');
    if (!ext || seen.has(ext)) continue;
    seen.add(ext);
    rows.push({
      name: q.queue_name || `Queue ${ext}`,
      ext,
      waiting: byExt[ext] || 0,
    });
  }
  // Always surface 8000 / any waiting queue not in tiers
  for (const [ext, waiting] of Object.entries(byExt)) {
    if (seen.has(ext)) continue;
    rows.push({ name: `Queue ${ext}`, ext, waiting });
  }
  if (rows.length === 0) {
    rows.push({ name: 'Voice | Care', ext: '8000', waiting: byExt['8000'] || stats.queue_waiting || 0 });
  }
  return rows;
}
