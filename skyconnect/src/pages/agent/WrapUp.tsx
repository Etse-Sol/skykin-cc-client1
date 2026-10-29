import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { guessWrapFromTranscript, REASON_TREE } from '../../lib/wrapReason';
import { addJourneyEvent, saveCase } from '../../services/crm';
import { opsPost } from '../../services/ops';
import { useSoftphone } from '../../softphone/SoftphoneContext';

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
  const [hint, setHint] = useState('');
  const autoRan = useRef(false);
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

  const persist = async (path: string, outc: string, note: string) => {
    const ext = phone.creds.extension;
    if (!ext) throw new Error('No extension — cannot save wrap-up');
    if (!path) throw new Error('Select a call reason');
    const customerPhone = (phone.remoteNumber || phone.lastRemoteNumber || '').trim();
    if (!customerPhone) {
      throw new Error('No customer number from the call — journey not linked. Search Customers by that phone.');
    }
    const summary = note.trim() ? `${path} · ${outc} — ${note.trim()}`.slice(0, 200) : `${path} · ${outc}`;
    try {
      const q = JSON.parse(sessionStorage.getItem('sc_wrap_queue') || '[]');
      q.unshift({
        phone: customerPhone,
        reason: path,
        outcome: outc,
        notes: note,
        agent_id: ext,
        at: Date.now(),
      });
      sessionStorage.setItem('sc_wrap_queue', JSON.stringify(q.slice(0, 40)));
    } catch {
      /* ignore */
    }
    void addJourneyEvent({ phone: customerPhone, channel: 'Voice', summary }).catch(() => {});
    void saveCase({
      phone: customerPhone,
      reason: path,
      outcome: outc,
      notes: note.trim(),
      agent_id: ext,
    }).catch(() => {});
    void opsPost('survey_link', { agent_ext: ext, phone: customerPhone })
      .then((r) => {
        if (r?.path) sessionStorage.setItem('sc_csat_url', r.path);
      })
      .catch(() => {});
    phone.clearLastRemoteNumber();
    navigate(`/agent/customers?phone=${encodeURIComponent(customerPhone)}`);
  };

  useEffect(() => {
    if (autoRan.current) return;
    if (!phone.creds.extension) return;
    let pending = '';
    let tr = '';
    try {
      pending = sessionStorage.getItem('sc_wrap_pending') || '';
      tr = sessionStorage.getItem('sc_last_transcript') || '';
    } catch {
      return;
    }
    if (pending !== '1') return;
    autoRan.current = true;
    try {
      sessionStorage.removeItem('sc_wrap_pending');
    } catch {
      /* ignore */
    }
    const g = guessWrapFromTranscript(tr);
    if (!g) {
      setHint(
        tr.trim()
          ? 'Captions did not match a reason — pick one, then Save and close.'
          : 'No live captions on that call — pick a reason, then Save and close.',
      );
      return;
    }
    const outc = g.outcome === 'Follow-up' ? 'Follow-up' : g.outcome === 'Escalated' ? 'Escalated' : 'Resolved';
    setL1(g.l1);
    setL2(g.l2);
    setL3(g.l3);
    setOutcome(outc);
    setNotes(g.notes);
    setExpanded((p) => ({ ...p, [g.l1]: true, [g.l2]: true }));
    setHint('Filled from live captions — saving wrap-up.');
    setSaving(true);
    void persist(g.path, outc, g.notes)
      .catch((e) => {
        setError(e instanceof Error ? e.message : 'Auto-save failed — review and save.');
        setHint('Reason was filled from captions. Check it, then Save and close.');
      })
      .finally(() => setSaving(false));
  }, [phone.creds.extension]);

  const onSave = async () => {
    setSaving(true);
    setError('');
    try {
      await persist(selectedPath, outcome, notes);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Save failed';
      setError(/timeout|timed out|abort/i.test(msg) ? 'Customer save timed out. Click Save and close again.' : msg);
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
          {Object.entries(REASON_TREE).map(([cat, subs]) => {
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

        {hint ? <p className="mt-3 text-sm font-semibold text-[var(--color-sc-forest)]">{hint}</p> : null}
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
