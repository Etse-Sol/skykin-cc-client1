import { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import BrowserShell from '../components/BrowserShell';
import RoleGuard from '../components/RoleGuard';
import RoleNav from '../components/RoleNav';
import SkyConnectLogo from '../components/SkyConnectLogo';
import { fetchAgentSession, type AgentSession } from '../services/session';

function initials(name: string) {
  const p = name.trim().split(/\s+/).filter(Boolean);
  if (p.length >= 2) return (p[0][0] + p[1][0]).toUpperCase();
  return (name.slice(0, 2) || 'A').toUpperCase();
}

export default function AdminLayout() {
  const [session, setSession] = useState<AgentSession | null>(null);

  useEffect(() => {
    fetchAgentSession().then(setSession).catch(() => {});
  }, []);

  const name = session?.display_name || session?.username || 'Admin';

  const sidebar = (
    <>
      <div className="mb-2.5 px-3">
        <SkyConnectLogo />
      </div>
      <RoleNav role="admin" logout={session?.logout} />
    </>
  );

  const header = (
    <header className="flex items-center justify-end gap-3 bg-[var(--color-sc-page)] px-7 pt-5 pb-0">
      <span className="sc-meta">{name}</span>
      <span className="sc-avatar">{initials(name)}</span>
    </header>
  );

  return (
    <RoleGuard allow="admin">
      <BrowserShell sidebar={sidebar} header={header}>
        <Outlet />
      </BrowserShell>
    </RoleGuard>
  );
}
