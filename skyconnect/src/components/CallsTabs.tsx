import { NavLink } from 'react-router-dom';

const tabs = [
  { to: '/agent/interaction', label: 'Interaction', end: true },
  { to: '/agent/history', label: 'Call History', end: true },
];

export default function CallsTabs() {
  return (
    <div className="mb-4 flex gap-1 rounded-xl bg-[var(--color-sc-soft)] p-1">
      {tabs.map((t) => (
        <NavLink
          key={t.to}
          to={t.to}
          end={t.end}
          className={({ isActive }) =>
            `rounded-lg px-4 py-2 text-sm font-semibold ${
              isActive
                ? 'bg-white text-[var(--color-sc-forest)] shadow-sm'
                : 'text-[var(--color-sc-muted)] hover:text-[var(--color-sc-forest)]'
            }`
          }
        >
          {t.label}
        </NavLink>
      ))}
    </div>
  );
}
