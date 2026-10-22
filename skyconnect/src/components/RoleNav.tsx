import { Fragment } from 'react';
import { NavLink } from 'react-router-dom';

const agentLinks = [
  { to: '/agent/home', label: 'Home', sec: 'WORKSPACE (AGENT)' },
  { to: '/agent/interaction', label: 'Interaction' },
  { to: '/agent/wrap-up', label: 'Wrap-up' },
  { to: '/agent/customers', label: 'Customers', sec: 'MORE' },
  { to: '/agent/cases', label: 'Cases' },
  { to: '/agent/knowledge', label: 'Knowledge' },
  { to: '/agent/schedule', label: 'Schedule' },
  { to: '/agent/learning', label: 'Learning' },
];

const supervisorLinks = [
  { to: '/supervisor/team', label: 'Team real-time', sec: 'SUPERVISE' },
  { to: '/supervisor/floor', label: 'AI live floor' },
  { to: '/supervisor/quality', label: 'Call review' },
  { to: '/supervisor/wallboard', label: 'Wallboard' },
  { to: '/supervisor/schedule', label: 'Workforce' },
  { to: '/supervisor/reports', label: 'IVR report', sec: 'BUILD AND REPORT' },
  { to: '/supervisor/surveys', label: 'Surveys' },
  { to: '/supervisor/learning', label: 'Learning' },
];

const adminLinks = [
  { to: '/admin/console', label: 'Console' },
  { to: '/admin/ivr', label: 'Visual IVR' },
  { to: '/admin/chatbot', label: 'Chatbot' },
  { to: '/admin/flows', label: 'Flows' },
  { to: '/admin/queues', label: 'Queues' },
  { to: '/admin/announcements', label: 'Announcements' },
  { to: '/admin/verification', label: 'Verification' },
  { to: '/admin/knowledge', label: 'Knowledge' },
  { to: '/admin/users', label: 'Users' },
  { to: '/admin/reports/ivr', label: 'IVR report', sec: 'REPORTS' },
  { to: '/admin/reports/reasons', label: 'Call reasons' },
  { to: '/admin/settings', label: 'Settings' },
];

const byRole = {
  agent: agentLinks,
  supervisor: supervisorLinks,
  admin: adminLinks,
} as const;

type Role = keyof typeof byRole;

type Props = {
  role: Role;
  logout?: string;
  onLogout?: () => void;
};

export default function RoleNav({ role, logout, onLogout }: Props) {
  const links = byRole[role];
  const label = role === 'agent' ? 'Agent' : role === 'supervisor' ? 'Supervisor' : 'Admin';
  return (
    <>
      <nav className="flex flex-col gap-0.5">
        {links.map((l) => (
          <Fragment key={l.to}>
            {'sec' in l && l.sec ? <p className="sc-nav-sec">{l.sec}</p> : null}
            <NavLink
              to={l.to}
              className={({ isActive }) => `sc-nav-link ${isActive ? 'sc-nav-link-active' : ''}`}
            >
              {l.label}
            </NavLink>
          </Fragment>
        ))}
      </nav>
      <div className="mt-auto border-t border-[var(--color-sc-line)] pt-3">
        <p className="sc-meta px-3">Role: {label}</p>
        <a
          className="sc-meta mt-1 inline-block px-3 text-[var(--color-sc-green)] hover:underline"
          href={logout || '/logout.php'}
          onClick={onLogout}
        >
          Log out
        </a>
      </div>
    </>
  );
}
