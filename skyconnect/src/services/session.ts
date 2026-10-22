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
    throw new Error('Sign-in timed out. Go to sign in and try again.');
  }
  const data = (await r.json()) as AgentSession;
  if (r.status === 401 || data.ok === false) {
    const login = import.meta.env.DEV
      ? '/app/agent_dashboard/skyconnect_signin.php'
      : data.login || '/';
    if (window.location.pathname !== new URL(login, window.location.origin).pathname) {
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
