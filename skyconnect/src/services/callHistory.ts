/** Call History via PHP — same CDR labels as old agent dashboard. */

export type HistoryRow = {
  time: string;
  type: string;
  number: string;
  duration: string;
  status: string;
  disposition: string;
  recording?: string;
  record_name?: string;
};

export type HistoryResponse = {
  ok?: boolean;
  calls: HistoryRow[];
  count: number;
  source?: string;
  error?: string;
  extension?: string;
};

export function localDayISO(d = new Date()): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function usableCallNumber(raw: string | undefined | null): string {
  const n = String(raw || '').trim();
  if (!n) return '';
  if (/^(unknown|anonymous|restricted|n\/a|-)$/i.test(n)) return '';
  return n;
}

export async function fetchLastCall(opts: {
  domain?: string;
  ext?: string;
}): Promise<HistoryRow | null> {
  const to = localDayISO();
  const fromD = new Date();
  fromD.setDate(fromD.getDate() - 7);
  const data = await fetchCallHistory({
    from: localDayISO(fromD),
    to,
    domain: opts.domain,
    ext: opts.ext,
  });
  for (const row of data.calls) {
    const num = usableCallNumber(row.number);
    if (num) return { ...row, number: num };
  }
  return null;
}

export async function fetchCallHistory(opts: {
  from: string;
  to: string;
  domain?: string;
  ext?: string;
}): Promise<HistoryResponse> {
  const q = new URLSearchParams({
    from: opts.from,
    to: opts.to,
  });
  if (opts.domain) q.set('domain', opts.domain);
  if (opts.ext) q.set('ext', opts.ext);

  const r = await fetch(`/app/agent_dashboard/skyconnect_history.php?${q}`, {
    credentials: 'same-origin',
    cache: 'no-store',
  });
  if (r.status === 401) {
    window.location.href = '/';
    throw new Error('Session expired');
  }
  if (!r.ok) throw new Error(`history ${r.status}`);
  const data = (await r.json()) as HistoryResponse;
  return {
    ...data,
    calls: data.calls || [],
    count: data.count ?? (data.calls || []).length,
  };
}
