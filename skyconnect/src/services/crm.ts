/** CRM APIs (crm.php JSON backend for SkyConnect CRM / Customer 360). */

export type CrmCallHistory = {
  call_time?: string;
  direction?: string;
  billsec?: number | string;
  destination_number?: string;
  hangup_cause?: string;
};

export type CrmJourneyEvent = {
  event_at?: string;
  channel?: string;
  summary?: string;
  source?: string;
  status?: string;
};

export type CrmCase = {
  case_id?: number | string;
  customer_name?: string;
  customer_phone?: string;
  issue_type?: string;
  description?: string;
  status?: string;
  priority?: string;
  created_at?: string;
};

export type CrmContact = {
  contact_id?: number;
  phone?: string;
  alt_phone?: string;
  full_name?: string;
  email?: string;
  company?: string;
  language?: string;
  account_type?: string;
  notes?: string;
  fayda_verified?: number | boolean;
  csat?: number | string | null;
  sentiment?: string;
  products?: string;
  contacts_this_week?: number;
  call_history?: CrmCallHistory[];
  journey?: CrmJourneyEvent[];
  cases?: CrmCase[];
  open_cases?: CrmCase[];
  open_case_count?: number;
  ai_summary?: string;
  next_best_action?: string;
};

const CRM = '/app/agent_dashboard/crm.php';

export async function lookupContact(phone: string): Promise<CrmContact | null> {
  const q = phone.trim();
  if (!q) return null;
  const r = await fetch(`${CRM}?api=360&phone=${encodeURIComponent(q)}`, {
    credentials: 'same-origin',
    cache: 'no-store',
  });
  if (!r.ok) throw new Error(`crm lookup ${r.status}`);
  const data = await r.json();
  return data && typeof data === 'object' ? (data as CrmContact) : null;
}

export async function refreshAiSummary(phone: string): Promise<{
  ai_summary: string;
  next_best_action: string;
  provider: string;
}> {
  const r = await fetch(`${CRM}?api=ai_summary`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone }),
  });
  if (!r.ok) throw new Error(`ai_summary ${r.status}`);
  const data = await r.json();
  return {
    ai_summary: String(data.ai_summary || ''),
    next_best_action: String(data.next_best_action || ''),
    provider: String(data.provider || 'rules'),
  };
}

/** Insert a real journey row (e.g. after wrap-up on a live call). */
export async function addJourneyEvent(input: {
  phone: string;
  channel?: string;
  summary: string;
  event_at?: string;
}): Promise<void> {
  const r = await fetch(`${CRM}?api=journey_add`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      phone: input.phone,
      channel: input.channel || 'Voice',
      summary: input.summary,
      event_at: input.event_at || '',
    }),
  });
  if (!r.ok) throw new Error(`journey_add ${r.status}`);
  const data = await r.json();
  if (data && data.ok === false) throw new Error(data.error || 'journey_add failed');
}

export async function listContacts(search = ''): Promise<CrmContact[]> {
  const q = new URLSearchParams({ api: 'list' });
  if (search.trim()) q.set('search', search.trim());
  const r = await fetch(`${CRM}?${q}`, { credentials: 'same-origin', cache: 'no-store' });
  if (!r.ok) throw new Error(`crm list ${r.status}`);
  const data = await r.json();
  return Array.isArray(data) ? data : [];
}

/** Create / update a CRM contact (name is stored here). */
export async function saveContact(input: {
  contact_id?: number;
  phone: string;
  full_name: string;
  alt_phone?: string;
  email?: string;
  company?: string;
  language?: string;
  account_type?: string;
  notes?: string;
  products?: string;
  fayda_verified?: boolean | number;
  csat?: number | string | null;
  sentiment?: string;
}): Promise<{ contact_id?: number; phone?: string }> {
  const r = await fetch(`${CRM}?api=save`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!r.ok) throw new Error(`crm save ${r.status}`);
  const data = await r.json();
  if (data && data.ok === false) throw new Error(data.error || 'Save failed');
  return data || {};
}

export async function deleteContact(id: number): Promise<void> {
  const r = await fetch(`${CRM}?api=delete&id=${encodeURIComponent(String(id))}`, {
    credentials: 'same-origin',
  });
  if (!r.ok) throw new Error(`crm delete ${r.status}`);
  const data = await r.json();
  if (data && data.ok === false) throw new Error(data.error || 'Delete failed');
}

export type CrmCaseRow = {
  case_id?: number | string;
  created_at?: string;
  customer_name?: string;
  customer_phone?: string;
  issue_type?: string;
  description?: string;
  status?: string;
  priority?: string;
  agent_id?: string;
  department?: string;
};

/** Cases list — reason (issue_type) + status from wrap-up / CRM. */
export async function listCases(opts?: {
  phone?: string;
  status?: string;
}): Promise<CrmCaseRow[]> {
  const q = new URLSearchParams({ api: 'cases' });
  if (opts?.phone?.trim()) q.set('phone', opts.phone.trim());
  if (opts?.status?.trim()) q.set('status', opts.status.trim());
  const r = await fetch(`${CRM}?${q}`, { credentials: 'same-origin', cache: 'no-store' });
  const text = await r.text();
  if (!r.ok) throw new Error(`crm cases ${r.status}`);
  if (!text.trim()) return [];
  try {
    const data = JSON.parse(text) as { cases?: CrmCaseRow[]; error?: string };
    return Array.isArray(data?.cases) ? data.cases : [];
  } catch {
    return [];
  }
}

/** Save case from wrap-up: call reason + outcome/status. */
export async function saveCase(input: {
  phone: string;
  reason: string;
  outcome?: string;
  status?: string;
  notes?: string;
  customer_name?: string;
  agent_id?: string;
  priority?: string;
}): Promise<{ case_id?: number; status?: string; updated?: boolean }> {
  const r = await fetch(`${CRM}?api=case_save`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!r.ok) throw new Error(`case_save ${r.status}`);
  const data = await r.json();
  if (data && data.ok === false) throw new Error(data.error || 'case_save failed');
  return data || {};
}

export async function updateCaseStatus(
  caseId: number,
  status: string,
): Promise<void> {
  const r = await fetch(`${CRM}?api=case_status`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ case_id: caseId, status }),
  });
  if (!r.ok) throw new Error(`case_status ${r.status}`);
  const data = await r.json();
  if (data && data.ok === false) throw new Error(data.error || 'case_status failed');
}

export type KnowledgeArticle = {
  article_id?: number;
  title?: string;
  tag?: string;
  body?: string;
  excerpt?: string;
  keywords?: string;
  updated_at?: string;
};

export async function listKnowledge(search = ''): Promise<KnowledgeArticle[]> {
  const q = new URLSearchParams({ op: 'knowledge' });
  if (search.trim()) q.set('q', search.trim());
  const r = await fetch(`/app/agent_dashboard/skyconnect_ops.php?${q}`, {
    credentials: 'same-origin',
    cache: 'no-store',
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok || data.ok === false) throw new Error(data.error || `knowledge ${r.status}`);
  return Array.isArray(data?.articles) ? data.articles : [];
}

export async function saveKnowledge(input: {
  article_id?: number;
  title: string;
  tag?: string;
  body: string;
  keywords?: string;
}): Promise<{ article_id?: number }> {
  const r = await fetch(`${CRM}?api=knowledge_save`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  const data = await r.json();
  if (!r.ok || data.ok === false) throw new Error(data.error || 'knowledge_save failed');
  return data;
}

export async function getKnowledgeArticle(id: number): Promise<KnowledgeArticle | null> {
  const r = await fetch(
    `/app/agent_dashboard/skyconnect_ops.php?op=knowledge&id=${encodeURIComponent(String(id))}`,
    { credentials: 'same-origin', cache: 'no-store' },
  );
  const data = await r.json().catch(() => ({}));
  if (!r.ok || data.ok === false) throw new Error(data.error || `knowledge ${r.status}`);
  return data?.article && typeof data.article === 'object' ? data.article : null;
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

export function fmtBillsec(v: number | string | undefined): string {
  const n = Number(v || 0);
  if (!n) return '00:00';
  const m = Math.floor(n / 60)
    .toString()
    .padStart(2, '0');
  const s = Math.floor(n % 60)
    .toString()
    .padStart(2, '0');
  return `${m}:${s}`;
}
