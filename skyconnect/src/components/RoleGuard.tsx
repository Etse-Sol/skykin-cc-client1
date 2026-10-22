import { useEffect, useState, type ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { goPbxIfSuperadmin, homeFor, sessionRole, type AppRole } from '../lib/role';
import { fetchAgentSession, type AgentSession } from '../services/session';

export default function RoleGuard({
  allow,
  children,
}: {
  allow: Exclude<AppRole, 'superadmin'>;
  children: ReactNode;
}) {
  const [session, setSession] = useState<AgentSession | null>(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    fetchAgentSession()
      .then(setSession)
      .catch((e: Error) => setErr(e.message || 'Not logged in'));
  }, []);

  if (err) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-6 text-[var(--color-sc-warn)]">
        <p>{err}</p>
        <a className="text-sm font-bold text-[var(--color-sc-green)] underline" href="/">
          Go to sign in
        </a>
      </div>
    );
  }
  if (!session) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6 sc-meta">Signing you in…</div>
    );
  }
  const role = sessionRole(session);
  if (goPbxIfSuperadmin(role)) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6 sc-meta">Opening PBX admin…</div>
    );
  }
  if (role !== allow) {
    return <Navigate to={homeFor(role)} replace />;
  }
  return <>{children}</>;
}
