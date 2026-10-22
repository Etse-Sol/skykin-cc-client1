type Props = { label: string; tone?: 'ok' | 'warn' | 'idle' | 'busy' | 'blue' };

const toneClass = {
  ok: 'bg-[var(--color-sc-green)] text-white',
  warn: 'bg-orange-100 text-orange-800',
  idle: 'bg-[var(--color-sc-idle-btn)] text-white',
  busy: 'bg-[var(--color-sc-green)] text-white',
  blue: 'bg-[var(--color-sc-blue)] text-white',
};

export default function StatusPill({ label, tone = 'idle' }: Props) {
  return (
    <span
      className={`inline-flex w-fit shrink-0 items-center justify-center whitespace-nowrap rounded-full px-2.5 py-1 text-[11px] font-bold ${toneClass[tone]}`}
    >
      {label}
    </span>
  );
}
