import { Fragment, useMemo, useState, type ComponentType } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { SIGNIN } from '../services/session';
import {
  BookOpen,
  Bot,
  Calendar,
  ClipboardCheck,
  FolderKanban,
  GitBranch,
  GraduationCap,
  Headphones,
  Home,
  LayoutDashboard,
  ListOrdered,
  LogOut,
  Megaphone,
  MessageSquare,
  PhoneCall,
  PieChart,
  Settings,
  ShieldCheck,
  Users,
  ChevronDown,
  Monitor,
  Layers,
  FileBarChart,
  UserRound,
  Building2,
  PhoneForwarded,
} from 'lucide-react';

type Icon = ComponentType<{ size?: number; className?: string; strokeWidth?: number }>;

type Leaf = { to: string; label: string; icon: Icon };
type Group = { label: string; icon: Icon; sec?: string; children: Leaf[] };
type Item = (Leaf & { sec?: string }) | Group;

const agentNav: Item[] = [
  { to: '/agent/home', label: 'Home', icon: Home, sec: 'WORKSPACE (AGENT)' },
  {
    label: 'Calls',
    icon: PhoneCall,
    children: [
      { to: '/agent/interaction', label: 'Interaction', icon: Headphones },
      { to: '/agent/wrap-up', label: 'Wrap-up', icon: ClipboardCheck },
      { to: '/agent/history', label: 'History', icon: ListOrdered },
    ],
  },
  {
    label: 'Customers',
    icon: UserRound,
    sec: 'MORE',
    children: [
      { to: '/agent/customers', label: 'Customer 360', icon: Building2 },
      { to: '/agent/cases', label: 'Cases', icon: FolderKanban },
    ],
  },
  { to: '/agent/knowledge', label: 'Knowledge', icon: BookOpen },
  { to: '/agent/schedule', label: 'Schedule', icon: Calendar },
  { to: '/agent/learning', label: 'Learning', icon: GraduationCap },
];

const supervisorNav: Item[] = [
  {
    label: 'Live',
    icon: Monitor,
    sec: 'SUPERVISE',
    children: [
      { to: '/supervisor/team', label: 'Team real-time', icon: Users },
      { to: '/supervisor/floor', label: 'AI live floor', icon: Headphones },
      { to: '/supervisor/wallboard', label: 'Wallboard', icon: LayoutDashboard },
      { to: '/supervisor/dashboard', label: 'Dashboard', icon: PieChart },
    ],
  },
  {
    label: 'Quality',
    icon: ClipboardCheck,
    children: [
      { to: '/supervisor/quality', label: 'Call review', icon: ClipboardCheck },
      { to: '/supervisor/evaluation', label: 'AI evaluation', icon: Bot },
    ],
  },
  { to: '/supervisor/schedule', label: 'Workforce', icon: Calendar },
  {
    label: 'Reports',
    icon: FileBarChart,
    sec: 'BUILD AND REPORT',
    children: [
      { to: '/supervisor/reports', label: 'IVR report', icon: PieChart },
      { to: '/supervisor/surveys', label: 'Surveys', icon: MessageSquare },
    ],
  },
  { to: '/supervisor/learning', label: 'Learning', icon: GraduationCap },
];

const adminNav: Item[] = [
  { to: '/admin/console', label: 'Console', icon: LayoutDashboard },
  {
    label: 'Channels',
    icon: Layers,
    children: [
      { to: '/admin/ivr', label: 'Visual IVR', icon: PhoneForwarded },
      { to: '/admin/chatbot', label: 'Chatbot', icon: Bot },
      { to: '/admin/flows', label: 'Flows', icon: GitBranch },
      { to: '/admin/queues', label: 'Queues', icon: ListOrdered },
      { to: '/admin/announcements', label: 'Announcements', icon: Megaphone },
      { to: '/admin/verification', label: 'Verification', icon: ShieldCheck },
    ],
  },
  { to: '/admin/knowledge', label: 'Knowledge', icon: BookOpen },
  {
    label: 'Users',
    icon: Users,
    children: [
      { to: '/admin/users', label: 'Accounts', icon: UserRound },
      { to: '/admin/skills', label: 'Skills', icon: Headphones },
      { to: '/admin/roles', label: 'Roles', icon: ShieldCheck },
    ],
  },
  {
    label: 'Reports',
    icon: FileBarChart,
    sec: 'REPORTS',
    children: [
      { to: '/admin/reports/ivr', label: 'IVR report', icon: PieChart },
      { to: '/admin/reports/reasons', label: 'Call reasons', icon: FolderKanban },
    ],
  },
  { to: '/admin/settings', label: 'Settings', icon: Settings },
];

const byRole = {
  agent: agentNav,
  supervisor: supervisorNav,
  admin: adminNav,
} as const;

type Role = keyof typeof byRole;

function isGroup(item: Item): item is Group {
  return 'children' in item && Array.isArray((item as Group).children);
}

function childActive(item: Group, path: string) {
  return item.children.some((c) => path === c.to || path.startsWith(c.to + '/'));
}

function NavIcon({ icon: Icon }: { icon: Icon }) {
  return <Icon size={16} strokeWidth={2.2} className="sc-nav-icon" />;
}

function LeafLink({ item }: { item: Leaf }) {
  return (
    <NavLink to={item.to} className={({ isActive }) => `sc-nav-link ${isActive ? 'sc-nav-link-active' : ''}`}>
      <NavIcon icon={item.icon} />
      <span>{item.label}</span>
    </NavLink>
  );
}

function DropGroup({ item }: { item: Group }) {
  const loc = useLocation();
  const on = childActive(item, loc.pathname);
  const [open, setOpen] = useState(on);
  const shown = open || on;

  return (
    <div>
      <button
        type="button"
        className={`sc-nav-link sc-nav-drop ${on ? 'sc-nav-link-active' : ''}`}
        aria-expanded={shown}
        onClick={() => setOpen((v) => !v)}
      >
        <NavIcon icon={item.icon} />
        <span className="flex-1 text-left">{item.label}</span>
        <ChevronDown size={14} className={`sc-nav-chevron ${shown ? 'sc-nav-chevron-open' : ''}`} />
      </button>
      {shown ? (
        <div className="sc-nav-sub">
          {item.children.map((c) => (
            <LeafLink key={c.to} item={c} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

type Props = {
  role: Role;
  logout?: string;
  onLogout?: () => void;
};

export default function RoleNav({ role, logout, onLogout }: Props) {
  const items = byRole[role];
  const label = role === 'agent' ? 'Agent' : role === 'supervisor' ? 'Supervisor' : 'Admin';
  const keys = useMemo(() => items.map((it) => (isGroup(it) ? it.label : it.to)), [items]);

  return (
    <>
      <nav className="flex flex-col gap-0.5">
        {items.map((item, i) => (
          <Fragment key={keys[i]}>
            {'sec' in item && item.sec ? <p className="sc-nav-sec">{item.sec}</p> : null}
            {isGroup(item) ? <DropGroup item={item} /> : <LeafLink item={item} />}
          </Fragment>
        ))}
      </nav>
      <div className="mt-auto border-t border-[var(--color-sc-line)] pt-3">
        <p className="sc-meta px-3">Role: {label}</p>
        <a
          className="sc-nav-link mt-1 text-[var(--color-sc-green)]"
          href={SIGNIN}
          onClick={(e) => {
            onLogout?.();
            e.preventDefault();
            void fetch('/logout.php', { credentials: 'same-origin', redirect: 'manual' }).finally(() => {
              window.location.assign(SIGNIN);
            });
          }}
        >
          <LogOut size={16} strokeWidth={2.2} className="sc-nav-icon" />
          <span>Log out</span>
        </a>
      </div>
    </>
  );
}
