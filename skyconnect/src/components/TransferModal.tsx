import { useEffect, useState } from 'react';
import { fetchAvailableAgents, type AvailableAgent } from '../services/agents';
import { useSoftphone } from '../softphone/SoftphoneContext';

type Props = {
  open: boolean;
  onClose: () => void;
};

export default function TransferModal({ open, onClose }: Props) {
  const phone = useSoftphone();
  const [target, setTarget] = useState('');
  const [agents, setAgents] = useState<AvailableAgent[]>([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => {
    if (!open) return;
    setErr('');
    setLoading(true);
    fetchAvailableAgents(phone.creds.domain, phone.creds.extension)
      .then(setAgents)
      .catch((e) => setErr(e instanceof Error ? e.message : 'Could not load agents'))
      .finally(() => setLoading(false));
  }, [open, phone.creds.domain, phone.creds.extension]);

  if (!open) return null;

  const doTransfer = async (ext: string) => {
    setBusy(true);
    setErr('');
    try {
      await phone.transfer(ext);
      onClose();
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Transfer failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-[var(--color-sc-line)] px-4 py-3">
          <h2 className="sc-section-title">Transfer call</h2>
          <button type="button" onClick={onClose} className="text-sm text-[var(--color-sc-muted)]">
            Close
          </button>
        </div>
        <div className="p-4">
          <div className="flex gap-2">
            <input
              className="min-w-0 flex-1 rounded-lg border border-[var(--color-sc-line)] px-3 py-2 text-sm"
              placeholder="Extension"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              inputMode="numeric"
            />
            <button
              type="button"
              disabled={busy || !target.trim()}
              onClick={() => doTransfer(target)}
              className="rounded-lg bg-[var(--color-sc-green)] px-4 text-sm font-bold text-white disabled:opacity-50"
            >
              Transfer
            </button>
          </div>

          <p className="mt-4 text-xs font-bold uppercase tracking-wide text-[var(--color-sc-muted)]">
            Available agents
          </p>
          {loading ? (
            <p className="mt-2 text-sm text-[var(--color-sc-muted)]">Loading…</p>
          ) : agents.length === 0 ? (
            <p className="mt-2 text-sm text-[var(--color-sc-muted)]">No other Available agents</p>
          ) : (
            <ul className="mt-2 max-h-56 space-y-1 overflow-auto">
              {agents.map((a) => (
                <li key={a.extension}>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => doTransfer(a.extension)}
                    className="flex w-full items-center justify-between rounded-lg border border-[var(--color-sc-line)] px-3 py-2 text-left hover:bg-[var(--color-sc-nav-active)] disabled:opacity-50"
                  >
                    <span>
                      <span className="block text-sm font-semibold text-[var(--color-sc-ink)]">
                        {a.name}
                      </span>
                      <span className="text-[11px] text-[var(--color-sc-muted)]">ext {a.extension}</span>
                    </span>
                    <span className="rounded-full bg-[var(--color-sc-green)] px-2 py-0.5 text-[10px] font-bold text-white">
                      {a.status}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          {err ? <p className="mt-3 text-sm font-semibold text-[var(--color-sc-warn)]">{err}</p> : null}
        </div>
      </div>
    </div>
  );
}
