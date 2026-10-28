/** Talks to the Go middle tier (/skyconnect/api). Softphone uses FreeSWITCH WSS directly. */
import { getCachedSession } from './session';

function apiBase(): string {
  return getCachedSession()?.api_base || import.meta.env.VITE_API_BASE || '/skyconnect/api/v1';
}

export type CdrRow = {
  time: string;
  type: string;
  number: string;
  duration: string;
  status: string;
  disposition: string;
};

export async function fetchHealth() {
  const r = await fetch(`${apiBase()}/health`, { credentials: 'same-origin' });
  if (!r.ok) throw new Error(`health ${r.status}`);
  return r.json() as Promise<{ ok: boolean; esl_connected: boolean }>;
}

export async function fetchCdr(from: string, to: string) {
  const q = new URLSearchParams({ from, to });
  const r = await fetch(`${apiBase()}/cdr?${q}`, { credentials: 'same-origin' });
  if (!r.ok) throw new Error(`cdr ${r.status}`);
  return r.json() as Promise<{ calls: CdrRow[]; count: number; source?: string; warning?: string }>;
}

export async function saveWrapUp(payload: {
  extension: string;
  reason: string;
  outcome: string;
  notes: string;
}) {
  const r = await fetch(`${apiBase()}/wrap-up`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(6000),
  });
  if (!r.ok) throw new Error(`wrap-up ${r.status}`);
  return r.json();
}
