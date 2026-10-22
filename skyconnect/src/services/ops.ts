const OPS = '/app/agent_dashboard/skyconnect_ops.php';
const REPORTS = '/app/agent_dashboard/reports.php';
const EVALS = '/app/agent_dashboard/evaluation.php';

async function getJson(url: string): Promise<any> {
  const r = await fetch(url, { credentials: 'same-origin', cache: 'no-store' });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || `${r.status}`);
  return data;
}

async function postJson(url: string, body: unknown): Promise<any> {
  const r = await fetch(url, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok || data.ok === false) throw new Error(data.error || `${r.status}`);
  return data;
}

export type ReportSummary = {
  total?: number;
  answered?: number;
  missed?: number;
  abandoned?: number;
  inbound?: number;
  outbound?: number;
  avg_talk?: number;
  sla?: number;
};

export async function fetchReportSummary(domain: string, from?: string, to?: string): Promise<ReportSummary> {
  const q = new URLSearchParams({ api: 'summary', domain });
  if (from) q.set('from', from);
  if (to) q.set('to', to);
  return getJson(`${REPORTS}?${q}`);
}

export async function fetchAgentPerformance(domain: string, from?: string, to?: string): Promise<any[]> {
  const q = new URLSearchParams({ api: 'agent_performance', domain });
  if (from) q.set('from', from);
  if (to) q.set('to', to);
  const data = await getJson(`${REPORTS}?${q}`);
  return Array.isArray(data) ? data : [];
}

export async function fetchHourlyVolume(domain: string, from?: string, to?: string): Promise<any[]> {
  const q = new URLSearchParams({ api: 'hourly_volume', domain });
  if (from) q.set('from', from);
  if (to) q.set('to', to);
  const data = await getJson(`${REPORTS}?${q}`);
  return Array.isArray(data) ? data : [];
}

export async function fetchCallList(domain: string, from?: string, to?: string): Promise<any[]> {
  const q = new URLSearchParams({ api: 'call_list', domain, type: 'all' });
  if (from) q.set('from', from);
  if (to) q.set('to', to);
  const data = await getJson(`${REPORTS}?${q}`);
  return Array.isArray(data) ? data : [];
}

export type EvalCall = {
  cdr_uuid?: string;
  call_time?: string;
  caller_id_number?: string;
  caller_id_name?: string;
  destination_number?: string;
  billsec?: number;
  record_name?: string;
  eval?: { total_score?: number; max_score?: number; grade?: string } | null;
};

export async function fetchEvalCalls(domain: string, from?: string, to?: string): Promise<EvalCall[]> {
  const q = new URLSearchParams({ api: 'calls', domain });
  if (from) q.set('from', from);
  if (to) q.set('to', to);
  const data = await getJson(`${EVALS}?${q}`);
  return Array.isArray(data) ? data : [];
}

export async function saveEvaluation(input: Record<string, unknown>): Promise<any> {
  const d = String(input.domain || '');
  const q = d ? `?api=save&domain=${encodeURIComponent(d)}` : '?api=save';
  return postJson(`${EVALS}${q}`, input);
}

export async function fetchEvalHistory(domain: string, from?: string, to?: string): Promise<any[]> {
  const q = new URLSearchParams({ api: 'history', domain });
  if (from) q.set('from', from);
  if (to) q.set('to', to);
  const data = await getJson(`${EVALS}?${q}`);
  return Array.isArray(data) ? data : [];
}

export async function fetchQaAgentSummary(domain: string, from?: string, to?: string): Promise<any[]> {
  const q = new URLSearchParams({ api: 'agent_summary', domain });
  if (from) q.set('from', from);
  if (to) q.set('to', to);
  const data = await getJson(`${EVALS}?${q}`);
  return Array.isArray(data) ? data : [];
}

export async function opsGet(op: string, extra: Record<string, string> = {}): Promise<any> {
  const q = new URLSearchParams({ op, ...extra });
  return getJson(`${OPS}?${q}`);
}

export async function opsPost(op: string, body: unknown, extra: Record<string, string> = {}): Promise<any> {
  const q = new URLSearchParams({ op, ...extra });
  return postJson(`${OPS}?${q}`, body);
}

export async function opsUpload(op: string, fd: FormData, extra: Record<string, string> = {}): Promise<any> {
  const q = new URLSearchParams({ op, ...extra });
  const r = await fetch(`${OPS}?${q}`, { method: 'POST', credentials: 'same-origin', body: fd });
  const data = await r.json().catch(() => ({}));
  if (!r.ok || data.ok === false) throw new Error(data.error || `${r.status}`);
  return data;
}

export type LiveSuggest = {
  ok?: boolean;
  say_next?: string;
  why?: string;
  ai?: boolean;
  articles?: Array<{
    article_id?: number;
    title?: string;
    tag?: string;
    excerpt?: string;
    score?: number;
  }>;
};

export async function suggestFromTranscript(transcript: string): Promise<LiveSuggest> {
  return postJson(`${OPS}?op=live_suggest`, { transcript });
}

export async function transcribeLiveChunk(blob: Blob, lang: string): Promise<string> {
  const fd = new FormData();
  const ext = blob.type.includes('ogg') ? 'ogg' : 'webm';
  fd.append('chunk', blob, `live.${ext}`);
  fd.append('lang', lang);
  const r = await fetch(`${OPS}?op=live_transcribe`, {
    method: 'POST',
    credentials: 'same-origin',
    body: fd,
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok || data.ok === false) {
    throw new Error(data.error || `${r.status}`);
  }
  return String(data.text || data.transcript || '').trim();
}

export function recUrl(name?: string): string {
  if (!name) return '';
  return `/app/agent_dashboard/play_recording.php?f=${encodeURIComponent(name)}`;
}

export function todayRange(): { from: string; to: string } {
  const t = new Date();
  const iso = t.toISOString().slice(0, 10);
  return { from: iso, to: iso };
}

export function weekRange(): { from: string; to: string } {
  const t = new Date();
  const to = t.toISOString().slice(0, 10);
  t.setDate(t.getDate() - 6);
  return { from: t.toISOString().slice(0, 10), to };
}
