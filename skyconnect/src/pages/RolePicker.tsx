import { Link } from 'react-router-dom';

const agentModules = [
  'Landing page and in-call desktop',
  'Tree-based call reason registration',
  'Customer 360 and consultation table',
];

const opsModules = [
  'Configurable reporting module',
  'Real-time supervisor wallboard',
  'Workforce management (WFM)',
];

const qualityModules = [
  'AI quality management with screen recording',
  'Learning and coaching',
  'Customer satisfaction surveys',
];

export default function RolePicker() {
  return (
    <div className="min-h-full bg-[#e8efe6] px-6 py-10">
      <div className="mx-auto max-w-4xl">
        <p className="text-sm font-bold uppercase tracking-wider text-[var(--color-sc-green)]">SkyConnect</p>
        <h1 className="mt-2 font-display text-4xl font-bold text-[var(--color-sc-forest)]">
          Agent Desktop and Operations Suite for Ethio Telecom
        </h1>
        <p className="mt-3 max-w-2xl text-[var(--color-sc-muted)]">
          One workspace for agents, supervisors and planners — ten modules sharing one customer record and one set of reports.
        </p>

        <div className="mt-8 grid gap-4 md:grid-cols-3">
          <section className="rounded-2xl border border-[var(--color-sc-border)] bg-white p-5">
            <p className="text-xs font-bold uppercase tracking-wide text-[var(--color-sc-green)]">Agent experience</p>
            <ul className="mt-3 space-y-2 text-sm text-[var(--color-sc-ink)]">
              {agentModules.map((m) => (
                <li key={m}>• {m}</li>
              ))}
            </ul>
            <Link
              to="/agent/home"
              className="mt-5 inline-flex rounded-full bg-[var(--color-sc-green)] px-4 py-2 text-sm font-bold text-white"
            >
              Open agent desktop
            </Link>
          </section>
          <section className="rounded-2xl border border-[var(--color-sc-border)] bg-white p-5">
            <p className="text-xs font-bold uppercase tracking-wide text-[var(--color-sc-green)]">Operations</p>
            <ul className="mt-3 space-y-2 text-sm text-[var(--color-sc-ink)]">
              {opsModules.map((m) => (
                <li key={m}>• {m}</li>
              ))}
            </ul>
            <Link
              to="/supervisor/wallboard"
              className="mt-5 inline-flex rounded-full bg-[var(--color-sc-forest)] px-4 py-2 text-sm font-bold text-white"
            >
              Open operations
            </Link>
          </section>
          <section className="rounded-2xl border border-[var(--color-sc-border)] bg-white p-5">
            <p className="text-xs font-bold uppercase tracking-wide text-[var(--color-sc-green)]">Quality and growth</p>
            <ul className="mt-3 space-y-2 text-sm text-[var(--color-sc-ink)]">
              {qualityModules.map((m) => (
                <li key={m}>• {m}</li>
              ))}
            </ul>
            <Link
              to="/supervisor/quality"
              className="mt-5 inline-flex rounded-full border border-[var(--color-sc-border)] px-4 py-2 sc-section-title"
            >
              Open quality
            </Link>
          </section>
        </div>
      </div>
    </div>
  );
}
