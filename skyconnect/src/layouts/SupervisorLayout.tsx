import { useEffect, useState } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import BrowserShell from '../components/BrowserShell';
import IncomingCallBanner from '../components/IncomingCallBanner';
import RoleGuard from '../components/RoleGuard';
import RoleNav from '../components/RoleNav';
import SkyConnectLogo from '../components/SkyConnectLogo';
import { fetchAgentSession, type AgentSession } from '../services/session';
import { useSoftphone } from '../softphone/SoftphoneContext';

function initials(name: string) {
  const p = name.trim().split(/\s+/).filter(Boolean);
  if (p.length >= 2) return (p[0][0] + p[1][0]).toUpperCase();
  return (name.slice(0, 2) || 'S').toUpperCase();
}

export default function SupervisorLayout() {
  const phone = useSoftphone();
  const navigate = useNavigate();
  const [session, setSession] = useState<AgentSession | null>(null);
  const [dial, setDial] = useState('');

  useEffect(() => {
    fetchAgentSession().then(setSession).catch(() => {});
  }, []);

  const name = session?.display_name || session?.username || 'Supervisor';
  const canCall = phone.phase === 'registered';

  const sidebar = (
    <>
      <div className="mb-2.5 px-3">
        <SkyConnectLogo />
      </div>
      <RoleNav role="supervisor" logout={session?.logout} />
    </>
  );

  const header = (
    <>
      <header className="flex flex-wrap items-center justify-between gap-3 bg-[var(--color-sc-page)] px-7 pt-5 pb-0">
        <form
          className="flex items-center gap-2.5"
          onSubmit={(e) => {
            e.preventDefault();
            if (canCall && dial.trim()) {
              phone.dial(dial.trim());
              navigate('/supervisor/floor');
            }
          }}
        >
          <label htmlFor="sc-sup-dial" className="sr-only">
            Dial number
          </label>
          <input
            id="sc-sup-dial"
            className="sc-input w-[220px]"
            placeholder="Enter number"
            value={dial}
            onChange={(e) => setDial(e.target.value)}
          />
          <button type="submit" className="sc-btn" disabled={!canCall || !dial.trim()}>
            Call
          </button>
        </form>
        <div className="flex items-center gap-3">
          <span className="sc-meta">{phone.statusLabel}</span>
          <span className="sc-chip sc-chip-ready">{phone.phase === 'in_call' ? 'On call' : 'Ready'}</span>
          <span className="sc-avatar">{initials(name)}</span>
        </div>
      </header>
      <IncomingCallBanner />
    </>
  );

  return (
    <RoleGuard allow="supervisor">
      <BrowserShell sidebar={sidebar} header={header}>
        <Outlet />
      </BrowserShell>
    </RoleGuard>
  );
}
