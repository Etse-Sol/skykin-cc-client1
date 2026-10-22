type Props = { label: string; value: string };

export default function StatCard({ label, value }: Props) {
  return (
    <div className="rounded-xl border border-[var(--color-sc-line)] bg-[var(--color-sc-soft)] px-4 py-3">
      <p className="font-display text-[1.25rem] font-bold leading-none text-[var(--color-sc-green)]">{value}</p>
      <p className="mt-0.5 text-xs text-[var(--color-sc-muted)]">{label}</p>
    </div>
  );
}
