import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { goPbxIfSuperadmin, homeFor, sessionRole } from '../lib/role';
import { demoSession, fetchAgentSession, setCachedSession, SIGNIN, type AgentSession } from '../services/session';

export default function AgentGate() {
  const [session, setSession] = useState<AgentSession | null>(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get('path') || '';
    if (import.meta.env.DEV && q.includes('agent_dashboard')) {
      window.location.replace(SIGNIN);
      return;
    }
    fetchAgentSession()
      .then(setSession)
      .catch((e: Error) => setErr(e.message || 'Not logged in'));
  }, []);

  if (err) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-[#e8efe6] p-6">
        <p className="max-w-md text-center text-[var(--color-sc-forest)]">{err}</p>
        <a className="text-sm font-bold text-[var(--color-sc-green)] underline" href={SIGNIN}>
          Go to sign in
        </a>
        {import.meta.env.DEV ? (
          <button
            type="button"
            className="sc-btn"
            onClick={() => {
              setCachedSession(demoSession());
              setSession(demoSession());
              setErr('');
            }}
          >
            Continue locally (admin UI)
          </button>
        ) : null}
      </div>
    );
  }
  if (!session) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#e8efe6] p-6">
        <p className="text-[var(--color-sc-muted)]">Signing you in…</p>
      </div>
    );
  }
  const role = sessionRole(session);
  if (goPbxIfSuperadmin(role)) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6 sc-meta">
        Opening PBX admin…
      </div>
    );
  }
  return <Navigate to={homeFor(role)} replace />;
}
