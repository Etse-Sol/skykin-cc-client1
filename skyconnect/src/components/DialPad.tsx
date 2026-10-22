import { Delete, Phone, X } from 'lucide-react';

const KEYS = [
  ['1', '2', '3'],
  ['4', '5', '6'],
  ['7', '8', '9'],
  ['*', '0', '#'],
] as const;

type Props = {
  value: string;
  onChange: (v: string) => void;
  onCall: () => void;
  onClose: () => void;
  canCall: boolean;
  onTone?: (k: string) => void;
  inCall?: boolean;
};

export default function DialPad({
  value,
  onChange,
  onCall,
  onClose,
  canCall,
  onTone,
  inCall,
}: Props) {
  const press = (k: string) => {
    if (onTone) onTone(k);
    else onChange(value + k);
  };

  return (
    <div className="w-[220px] rounded-2xl border border-[var(--color-sc-border)] bg-white p-3 shadow-[0_12px_40px_rgba(14,59,43,0.18)]">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-xs font-bold uppercase tracking-wide text-[var(--color-sc-muted)]">
          {inCall ? 'Keypad' : 'Dialpad'}
        </p>
        <button type="button" onClick={onClose} className="rounded-full p-1 text-[var(--color-sc-muted)] hover:bg-[var(--color-sc-soft)]" aria-label="Close dialpad">
          <X size={14} />
        </button>
      </div>

      <div className="mb-2 rounded-xl border border-[var(--color-sc-line)] bg-[var(--color-sc-soft)] px-3 py-2 text-center font-mono text-lg font-bold tracking-wider text-[var(--color-sc-forest)] min-h-[42px]">
        {value || <span className="font-sans text-sm font-medium text-[var(--color-sc-muted)]">Enter number</span>}
      </div>

      <div className="grid gap-1.5">
        {KEYS.map((row) => (
          <div key={row.join('')} className="grid grid-cols-3 gap-1.5">
            {row.map((k) => (
              <button
                key={k}
                type="button"
                onClick={() => press(k)}
                className="rounded-xl bg-[var(--color-sc-soft)] py-2.5 text-[15px] font-bold text-[var(--color-sc-forest)] hover:bg-[var(--color-sc-nav-active)] active:scale-95"
              >
                {k}
              </button>
            ))}
          </div>
        ))}
      </div>

      <div className="mt-2 grid grid-cols-3 gap-1.5">
        <button
          type="button"
          onClick={() => onChange(value.slice(0, -1))}
          className="flex items-center justify-center rounded-xl bg-[var(--color-sc-soft)] py-2.5 text-[var(--color-sc-muted)] hover:bg-[var(--color-sc-nav-active)]"
          aria-label="Backspace"
        >
          <Delete size={16} />
        </button>
        <button
          type="button"
          onClick={inCall ? onClose : onCall}
          disabled={inCall ? false : !canCall || !value.trim()}
          className="col-span-2 flex items-center justify-center gap-1.5 rounded-xl bg-[var(--color-sc-green)] py-2.5 text-sm font-bold text-white disabled:opacity-40"
        >
          <Phone size={14} fill="currentColor" />
          {inCall ? 'Done' : 'Call'}
        </button>
      </div>
    </div>
  );
}
