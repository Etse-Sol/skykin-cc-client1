/** FusionPBX call-center agent status (same API as old agent_dashboard). */

export type UiStatus = 'Available' | 'Break' | 'Offline';
export type FpbxStatus = 'Available' | 'On Break' | 'Logged Out' | 'Available (On Demand)';

const STATUS_URL = '/app/agent_dashboard/index.php';

export function uiToFpbx(ui: UiStatus): FpbxStatus {
  if (ui === 'Break') return 'On Break';
  if (ui === 'Offline') return 'Logged Out';
  return 'Available';
}

export function fpbxToUi(fpbx: string): UiStatus {
  const s = (fpbx || '').trim();
  if (s === 'On Break') return 'Break';
  if (s === 'Logged Out' || s === '') return 'Offline';
  return 'Available'; // Available, Available (On Demand), etc.
}

export async function getAgentStatus(ext: string, domain: string): Promise<{ ok: boolean; agent_status?: string; error?: string }> {
  const q = new URLSearchParams({ action: 'get_agent_status', ext, domain });
  const r = await fetch(`${STATUS_URL}?${q}`, { credentials: 'same-origin', cache: 'no-store' });
  return r.json();
}

export async function setAgentStatus(
  ext: string,
  domain: string,
  ui: UiStatus,
): Promise<{ ok: boolean; status?: string; error?: string; esl_connected?: boolean; esl_error?: string }> {
  const r = await fetch(`${STATUS_URL}?action=set_agent_status`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      agent_ext: ext,
      new_status: uiToFpbx(ui),
      domain,
    }),
  });
  return r.json();
}

/** Ask supervisor for On Break (stays Available until approved). */
export async function requestBreak(opts: {
  ext: string;
  domain: string;
  name?: string;
  reason?: string;
}): Promise<{ ok: boolean; id?: number; error?: string }> {
  const r = await fetch(`${STATUS_URL}?action=request_leave`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      agent_ext: opts.ext,
      agent_name: opts.name || `Ext ${opts.ext}`,
      domain: opts.domain,
      request_type: 'On Break',
      reason: opts.reason || '',
    }),
  });
  return r.json();
}

export async function myLeaveRequest(
  ext: string,
  domain: string,
): Promise<{ ok: boolean; request?: { id: number; status: string; request_type?: string } | null }> {
  const q = new URLSearchParams({ action: 'my_leave_request', agent_ext: ext, domain });
  const r = await fetch(`${STATUS_URL}?${q}`, { credentials: 'same-origin', cache: 'no-store' });
  return r.json();
}
