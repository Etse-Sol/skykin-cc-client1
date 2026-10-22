import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { saveWrapUp } from '../../services/api';
import { addJourneyEvent, saveCase } from '../../services/crm';
import { useSoftphone } from '../../softphone/SoftphoneContext';

type Tree = Record<string, Record<string, string[]>>;

const tree: Tree = {
  'Service request': {
    'SIM and identity': ['SIM swap', 'Lost or stolen phone', 'Fayda verification'],
    telebirr: ['Wrong transfer', 'PIN reset', 'Limit inquiry'],
  },
  'Fault and complaint': {
    Network: ['No service', 'Slow data'],
    Billing: ['Unexpected charge', 'Package dispute'],
  },
};

export default function WrapUp() {
  const navigate = useNavigate();
  const phone = useSoftphone();
  const [l1, setL1] = useState('Service request');
  const [l2, setL2] = useState('SIM and identity');
  const [l3, setL3] = useState('SIM swap');
  const [outcome, setOutcome] = useState('Resolved');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState<Record<string, boolean>>({
    'Service request': true,
    'Fault and complaint': false,
    'SIM and identity': true,
    telebirr: true,
  });

  const selectedPath = useMemo(
    () => [l1, l2, l3].filter(Boolean).join(' > '),
    [l1, l2, l3],
  );

  const toggle = (key: string) =>
    setExpanded((prev) => ({ ...prev, [key]: !prev[key] }));

  const onSave = async () => {
    const ext = phone.creds.extension;
    if (!ext) {
      setError('No extension — cannot save wrap-up');
      return;
    }
    if (!selectedPath) {
      setError('Select a call reason');
      return;
    }
    setSaving(true);
    setError('');
    try {
      await saveWrapUp({
        extension: ext,
        reason: selectedPath,
        outcome,
        notes,
      });
      // Number survives hangup via lastRemoteNumber (live board clears remoteNumber)
      const customerPhone = (phone.remoteNumber || phone.lastRemoteNumber || '').trim();
      if (customerPhone) {
        // Full call-reason path on the Customer 360 track (not hangup status)
        const summary = notes.trim()
          ? `${selectedPath} · ${outcome} — ${notes.trim()}`.slice(0, 200)
          : `${selectedPath} · ${outcome}`;
        try {
          await addJourneyEvent({
            phone: customerPhone,
            channel: 'Voice',
            summary,
          });
        } catch (je) {
          setError(
            je instanceof Error
              ? `Reason saved, but journey failed: ${je.message}`
              : 'Reason saved, but journey failed — redeploy crm.php',
          );
          setSaving(false);
          return;
        }
        // Case row: reason + status (from outcome) for Cases page / Customer 360
        try {
          await saveCase({
            phone: customerPhone,
            reason: selectedPath,
            outcome,
            notes: notes.trim(),
            agent_id: ext,
          });
        } catch (ce) {
          setError(
            ce instanceof Error
              ? `Journey saved, but case failed: ${ce.message}`
              : 'Journey saved, but case failed — redeploy crm.php',
          );
          setSaving(false);
          return;
        }
        phone.clearLastRemoteNumber();
        navigate(`/agent/customers?phone=${encodeURIComponent(customerPhone)}`);
        return;
      }
      setError('No customer number from the call — journey not linked. Search Customers by that phone.');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed — check Go API');
    } finally {
      setSaving(false);
    }
  };

  const wrapNumber = (phone.remoteNumber || phone.lastRemoteNumber || '').trim();

  return (
    <div className="grid gap-5 lg:grid-cols-[1.05fr_1fr]">
      <section className="rounded-xl bg-[#E8F2E4] p-5">
        <h1 className="mb-4 sc-page-title">Call reasons</h1>
        {wrapNumber ? (
          <p className="mb-3 rounded-lg bg-white/70 px-3 py-2 text-sm text-[var(--color-sc-ink)]">
            Customer number: <strong>{wrapNumber}</strong>
          </p>
        ) : (
          <p className="mb-3 text-sm font-semibold text-[var(--color-sc-warn)]">
            No number remembered from the call — open Customers and search the phone after save.
          </p>
        )}

        <ul className="space-y-1 text-sm text-[var(--color-sc-ink)]">
          {Object.entries(tree).map(([cat, subs]) => {
            const catOpen = expanded[cat] !== false;
            return (
              <li key={cat}>
                <button
                  type="button"
                  onClick={() => {
                    setL1(cat);
                    toggle(cat);
                    const firstSub = Object.keys(subs)[0];
                    if (firstSub) {
                      setL2(firstSub);
                      setL3(subs[firstSub][0] || '');
                    }
                  }}
                  className="flex w-full items-center gap-2 rounded-lg px-1 py-1.5 text-left font-semibold hover:bg-white/40"
                >
                  <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-[var(--color-sc-forest)]" />
                  {cat}
                </button>

                {catOpen ? (
                  <ul className="ml-4 space-y-0.5 border-l border-[var(--color-sc-border)]/50 pl-3">
                    {Object.entries(subs).map(([sub, leaves]) => {
                      const subOpen = expanded[sub] !== false;
                      return (
                        <li key={sub}>
                          <button
                            type="button"
                            onClick={() => {
                              setL1(cat);
                              setL2(sub);
                              toggle(sub);
                              setL3(leaves[0] || '');
                            }}
                            className="flex w-full items-center gap-2 rounded-lg px-1 py-1.5 text-left font-medium hover:bg-white/40"
                          >
                            <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-[var(--color-sc-green)]" />
                            {sub}
                          </button>

                          {subOpen ? (
                            <ul className="ml-4 space-y-0.5">
                              {leaves.map((leaf) => {
                                const active = l1 === cat && l2 === sub && l3 === leaf;
                                return (
                                  <li key={leaf}>
                                    <button
                                      type="button"
                                      onClick={() => {
                                        setL1(cat);
                                        setL2(sub);
                                        setL3(leaf);
                                      }}
                                      className={`flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left ${
                                        active
                                          ? 'bg-[var(--color-sc-nav-active)] font-semibold text-[var(--color-sc-forest)]'
                                          : 'hover:bg-white/50'
                                      }`}
                                    >
                                      <span className="h-2 w-2 shrink-0 rounded-full bg-[var(--color-sc-green)]" />
                                      {leaf}
                                    </button>
                                  </li>
                                );
                              })}
                            </ul>
                          ) : null}
                        </li>
                      );
                    })}
                  </ul>
                ) : null}
              </li>
            );
          })}
        </ul>
      </section>

      <section className="rounded-xl border border-[var(--color-sc-line)] bg-white p-5">
        <p className="text-sm font-bold text-[var(--color-sc-ink)]">Selected reason</p>
        <p className="mt-2 rounded-lg bg-[var(--color-sc-nav-active)] px-3 py-2.5 text-sm font-semibold text-[var(--color-sc-forest)]">
          {selectedPath || '—'}
        </p>

        <p className="mt-5 text-sm font-bold text-[var(--color-sc-ink)]">Outcome</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {['Resolved', 'Follow-up', 'Escalated'].map((o) => (
            <button
              key={o}
              type="button"
              onClick={() => setOutcome(o)}
              className={`rounded-full px-4 py-1.5 text-sm font-semibold text-white ${
                outcome === o ? 'bg-[var(--color-sc-green)]' : 'bg-[#9AA89F]'
              }`}
            >
              {o}
            </button>
          ))}
        </div>

        <p className="mt-5 text-sm font-bold text-[var(--color-sc-ink)]">Notes</p>
        <textarea
          className="mt-2 min-h-[120px] w-full resize-y rounded-lg border border-[var(--color-sc-line)] bg-white p-3 text-sm text-[var(--color-sc-ink)] outline-none focus:border-[var(--color-sc-green)]"
          value={notes}
          placeholder="Optional notes…"
          onChange={(e) => setNotes(e.target.value)}
        />

        {error ? (
          <p className="mt-3 text-sm font-semibold text-[var(--color-sc-warn)]">{error}</p>
        ) : null}

        <button
          type="button"
          disabled={saving}
          onClick={onSave}
          className="mt-5 w-full rounded-lg bg-[var(--color-sc-green)] py-3 text-sm font-bold text-white hover:bg-[#159a42] disabled:opacity-60"
        >
          {saving ? 'Saving…' : 'Save and close'}
        </button>
      </section>
    </div>
  );
}
