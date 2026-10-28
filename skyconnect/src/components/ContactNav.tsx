import { NavLink, useLocation } from 'react-router-dom';
import { SIGNIN } from '../services/session';

const workspace = [
  { to: '/agent/home', label: 'Home' },
  { to: '/agent/interaction', label: 'Interaction' },
  { to: '/agent/wrap-up', label: 'Wrap-up' },
];

const supervise = [
  { to: '/supervisor/team', label: 'Team real-time' },
  { to: '/supervisor/floor', label: 'AI live floor' },
  { to: '/supervisor/quality', label: 'Call review' },
  { to: '/supervisor/wallboard', label: 'Wallboard' },
];

const build = [
  { to: '/admin/flows', label: 'Voice flows' },
  { to: '/admin/reports/ivr', label: 'IVR report' },
  { to: '/admin/reports/reasons', label: 'Call reasons' },
];

type Props = {
  role: string;
  logout?: string;
  onLogout?: () => void;
};

export default function ContactNav({ role, logout, onLogout }: Props) {
  const loc = useLocation();
  const cls = (active: boolean) => `sc-nav-link ${active ? 'sc-nav-link-active' : ''}`;

  return (
    <>
      <p className="sc-nav-sec">Workspace (agent)</p>
      <nav className="flex flex-col gap-0.5">
        {workspace.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            className={({ isActive }) =>
              cls(isActive || (l.to === '/agent/interaction' && loc.pathname === '/agent/consult'))
            }
          >
            {l.label}
          </NavLink>
        ))}
      </nav>
      <p className="sc-nav-sec">Supervise</p>
      <nav className="flex flex-col gap-0.5">
        {supervise.map((l) => (
          <NavLink key={l.to} to={l.to} className={({ isActive }) => cls(isActive)}>
            {l.label}
          </NavLink>
        ))}
      </nav>
      <p className="sc-nav-sec">Build and report</p>
      <nav className="flex flex-col gap-0.5">
        {build.map((l) => (
          <NavLink key={l.to} to={l.to} className={({ isActive }) => cls(isActive)}>
            {l.label}
          </NavLink>
        ))}
      </nav>
      <div className="mt-auto border-t border-[var(--color-sc-line)] pt-3">
        <p className="sc-meta px-3">Role: {role}</p>
        <a
          className="sc-meta mt-1 inline-block px-3 text-[var(--color-sc-green)] hover:underline"
          href={SIGNIN}
          onClick={(e) => {
            onLogout?.();
            e.preventDefault();
            void fetch('/logout.php', { credentials: 'same-origin', redirect: 'manual' }).finally(() => {
              window.location.assign(SIGNIN);
            });
          }}
        >
          Log out
        </a>
      </div>
    </>
  );
}
