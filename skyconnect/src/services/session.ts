/** FusionPBX session bootstrap — extension + WSS for softphone. */

export type AgentSession = {
  ok: boolean;
  username: string;
  display_name: string;
  extension: string;
  password: string;
  domain: string;
  wss: string;
  api_base: string;
  is_supervisor: boolean;
  is_admin: boolean;
  is_superadmin?: boolean;
  role: 'agent' | 'supervisor' | 'admin' | 'superadmin';
  groups?: string[];
  legacy_dashboard: string;
  logout: string;
  error?: string;
  login?: string;
};

let cached: AgentSession | null = null;

export const SIGNIN = '/app/agent_dashboard/skyconnect_signin.php';

export function demoSession(): AgentSession {
  return {
    ok: true,
    username: 'local-admin',
    display_name: 'Local admin',
    extension: '100',
    password: '',
    domain: 'client1.skykin.local',
    wss: '',
    api_base: '',
    is_supervisor: true,
    is_admin: true,
    is_superadmin: false,
    role: 'admin',
    groups: ['admin'],
    legacy_dashboard: '',
    logout: SIGNIN,
  };
}

export function setCachedSession(s: AgentSession | null) {
  cached = s;
}

export async function fetchAgentSession(force = false): Promise<AgentSession> {
  if (cached && !force) return cached;
  let r: Response;
  try {
    r = await fetch('/app/agent_dashboard/skyconnect_session.php', {
      credentials: 'same-origin',
      cache: 'no-store',
      signal: AbortSignal.timeout(12000),
    });
  } catch {
    throw new Error(
      'Cannot reach the testbed (196.189.236.103). The UI is local; login needs that server.',
    );
  }
  const raw = await r.text();
  let data: AgentSession;
  try {
    data = JSON.parse(raw) as AgentSession;
  } catch {
    const proxyDown = /server is not|ECONNREFUSED|proxy error|not reachable/i.test(raw);
    throw new Error(
      proxyDown
        ? 'Cannot reach the testbed (196.189.236.103). The UI is local; login needs that server.'
        : `Sign-in failed (${r.status}). The session service did not return JSON.`,
    );
  }
  if (r.status === 401 || data.ok === false) {
    const login = import.meta.env.DEV ? SIGNIN : data.login || SIGNIN;
    const here = window.location.pathname;
    if (here !== new URL(login, window.location.origin).pathname && !here.includes('/skyconnect')) {
      window.location.replace(login);
    }
    throw new Error(data.error || 'Not logged in');
  }
  cached = data;
  return data;
}

export function getCachedSession(): AgentSession | null {
  return cached;
}
