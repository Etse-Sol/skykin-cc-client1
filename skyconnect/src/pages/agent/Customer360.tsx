import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import CustomerJourneyTrack, {
  buildJourneyFromApi,
} from '../../components/CustomerJourneyTrack';
import { useSoftphone } from '../../softphone/SoftphoneContext';
import {
  initials,
  listContacts,
  lookupContact,
  refreshAiSummary,
  saveContact,
  flushWrapQueue,
  type CrmContact,
} from '../../services/crm';

export default function Customer360() {
  const phone = useSoftphone();
  const [params, setParams] = useSearchParams();
  const selectedPhone = (params.get('phone') || '').trim();

  const [query, setQuery] = useState('');
  const [contact, setContact] = useState<CrmContact | null>(null);
  const [list, setList] = useState<CrmContact[]>([]);
  const [loading, setLoading] = useState(false);
  const [listLoading, setListLoading] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [error, setError] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [newName, setNewName] = useState('');
  const [newPhone, setNewPhone] = useState('');
  const [saveMsg, setSaveMsg] = useState('');
  const [csatPath, setCsatPath] = useState('');

  const openCustomer = useCallback(
    (ph: string) => {
      const p = ph.trim();
      if (!p) return;
      setParams({ phone: p }, { replace: false });
    },
    [setParams],
  );

  const clearCustomer = useCallback(() => {
    setContact(null);
    setParams({}, { replace: true });
  }, [setParams]);

  useEffect(() => {
    void flushWrapQueue();
    try {
      setCsatPath(sessionStorage.getItem('sc_csat_url') || '');
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    if (selectedPhone) return;
    setListLoading(true);
    listContacts(query)
      .then(setList)
      .catch(() => setList([]))
      .finally(() => setListLoading(false));
  }, [query, selectedPhone]);

  useEffect(() => {
    if (selectedPhone) return;
    if (phone.remoteNumber) openCustomer(phone.remoteNumber);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phone.remoteNumber]);

  useEffect(() => {
    if (!selectedPhone) {
      setContact(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError('');
    lookupContact(selectedPhone)
      .then((row) => {
        if (!cancelled) setContact(row);
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Lookup failed');
          setContact(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedPhone]);

  const journey = useMemo(
    () => buildJourneyFromApi(contact?.journey, contact?.call_history, contact?.notes),
    [contact],
  );

  const name = contact?.full_name || (selectedPhone ? 'Unknown caller' : 'Customer');
  const tier = contact?.account_type || 'Customer';
  const lang = contact?.language || 'Amharic';
  const fayda = Boolean(contact?.fayda_verified);
  const weekContacts = contact?.contacts_this_week ?? 0;
  const csat =
    contact?.csat != null && contact.csat !== ''
      ? `CSAT ${contact.csat}`
      : 'CSAT —';
  const sentiment = contact?.sentiment || 'Neutral';
  const products = contact?.products || contact?.company || 'Prepaid plan | telebirr wallet';
  const openCount = contact?.open_case_count ?? contact?.open_cases?.length ?? 0;
  const openLabel =
    openCount > 0
      ? `${openCount} open case${openCount === 1 ? '' : 's'}: ${
          contact?.open_cases?.[0]?.issue_type ||
          contact?.open_cases?.[0]?.description ||
          'support'
        }`
      : 'No open case on file';
  const aiSummary =
    contact?.ai_summary ||
    `${weekContacts || journey.length} recent contact(s) for ${name}.`;
  const nextAction =
    contact?.next_best_action || 'Confirm the issue and help with context from the journey.';

  const runAi = async () => {
    if (!selectedPhone) return;
    setAiBusy(true);
    try {
      const r = await refreshAiSummary(selectedPhone);
      setContact((prev) =>
        prev
          ? {
              ...prev,
              ai_summary: r.ai_summary || prev.ai_summary,
              next_best_action: r.next_best_action || prev.next_best_action,
            }
          : prev,
      );
    } catch {
      /* keep rules summary */
    } finally {
      setAiBusy(false);
    }
  };

  const onAddContact = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaveMsg('');
    const ph = newPhone.trim();
    const nm = newName.trim();
    if (!ph || !nm) {
      setSaveMsg('Name and phone are required');
      return;
    }
    try {
      await saveContact({ phone: ph, full_name: nm, language: 'Amharic' });
      setSaveMsg('Saved');
      setShowAdd(false);
      setNewName('');
      setNewPhone('');
      const rows = await listContacts(query);
      setList(rows);
      openCustomer(ph);
    } catch (err) {
      setSaveMsg(err instanceof Error ? err.message : 'Save failed');
    }
  };

  if (!selectedPhone) {
    return (
      <div className="mx-auto max-w-4xl">
        <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="sc-page-title">Customers</h1>
            <p className="mt-1 text-sm text-[var(--color-sc-muted)]">
              Select a customer to open Customer 360 — or add a name in CRM
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <input
              className="w-full max-w-xs rounded-lg border border-[var(--color-sc-line)] bg-white px-3 py-2 text-sm sm:w-56"
              placeholder="Search name, phone, company…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Search customers"
            />
            <button
              type="button"
              onClick={() => setShowAdd((v) => !v)}
              className="rounded-lg bg-[var(--color-sc-green)] px-3 py-2 text-xs font-bold text-white"
            >
              {showAdd ? 'Cancel' : 'Quick add'}
            </button>
            <Link
              to="/agent/crm"
              className="rounded-lg border border-[var(--color-sc-line)] bg-white px-3 py-2 text-xs font-bold text-[var(--color-sc-forest)] hover:bg-[var(--color-sc-soft)]"
            >
              Open CRM
            </Link>
          </div>
        </div>

        {showAdd ? (
          <form
            onSubmit={onAddContact}
            className="mb-4 grid gap-3 rounded-xl border border-[var(--color-sc-line)] bg-[var(--color-sc-soft)] p-4 sm:grid-cols-[1fr_1fr_auto]"
          >
            <input
              className="rounded-lg border border-[var(--color-sc-line)] bg-white px-3 py-2 text-sm"
              placeholder="Full name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              required
            />
            <input
              className="rounded-lg border border-[var(--color-sc-line)] bg-white px-3 py-2 text-sm"
              placeholder="Phone e.g. 0911234567"
              value={newPhone}
              onChange={(e) => setNewPhone(e.target.value)}
              required
            />
            <button
              type="submit"
              className="rounded-lg bg-[var(--color-sc-forest)] px-4 py-2 text-xs font-bold text-white"
            >
              Save to CRM
            </button>
            {saveMsg ? (
              <p className="sm:col-span-3 text-xs font-semibold text-[var(--color-sc-ink)]">{saveMsg}</p>
            ) : null}
          </form>
        ) : null}

        <div className="overflow-hidden rounded-xl border border-[var(--color-sc-line)] bg-white">
          {listLoading ? (
            <p className="p-6 text-sm text-[var(--color-sc-muted)]">Loading contacts…</p>
          ) : list.length === 0 ? (
            <p className="p-6 text-sm text-[var(--color-sc-muted)]">
              No contacts found. Use <strong>Quick add</strong> or open{' '}
              <Link className="font-bold text-[var(--color-sc-green)] underline" to="/agent/crm">
                CRM
              </Link>
              .
            </p>
          ) : (
            <ul className="divide-y divide-[var(--color-sc-line)]">
              {list.map((c) => {
                const label = c.full_name || c.phone || 'Contact';
                return (
                  <li key={c.contact_id ?? `${c.phone}-${c.full_name}`}>
                    <button
                      type="button"
                      className="flex w-full items-center gap-4 px-4 py-3 text-left transition hover:bg-[var(--color-sc-soft)]"
                      onClick={() => openCustomer(c.phone || '')}
                      disabled={!c.phone}
                    >
                      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[var(--color-sc-green)] text-sm font-bold text-white">
                        {initials(label)}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block text-[14px] font-semibold text-[var(--color-sc-ink)]">{label}</span>
                        <span className="mt-0.5 block text-[13px] text-[var(--color-sc-muted)]">
                          {c.phone || '—'}
                          {c.account_type ? ` · ${c.account_type}` : ''}
                          {c.language ? ` · ${c.language}` : ''}
                          {c.fayda_verified ? ' · Fayda' : ''}
                        </span>
                      </span>
                      <span className="text-xs font-bold text-[var(--color-sc-green)]">Open 360 →</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl">
      {csatPath ? (
        <p className="mb-3 rounded-lg border border-[var(--color-sc-line)] bg-white px-3 py-2 text-sm">
          Post-call survey:{' '}
          <a className="font-bold underline" href={csatPath} target="_blank" rel="noreferrer">
            {csatPath}
          </a>
        </p>
      ) : null}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <button
            type="button"
            onClick={clearCustomer}
            className="mb-1 text-xs font-bold text-[var(--color-sc-green)] hover:underline"
          >
            ← Back to list
          </button>
          <h1 className="sc-page-title">
            Customer 360: the whole story in one screen.
          </h1>
          <Link
            to="/agent/crm"
            className="mt-1 inline-block text-xs font-bold text-[var(--color-sc-green)] hover:underline"
          >
            Edit in CRM →
          </Link>
          <p className="mt-1 text-sm text-[var(--color-sc-muted)]">
            Every interaction, product and open case, so agents help with context from the first word.
          </p>
        </div>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            const fd = new FormData(e.currentTarget);
            const ph = String(fd.get('phone') || '').trim();
            if (ph) openCustomer(ph);
          }}
        >
          <input
            name="phone"
            defaultValue={selectedPhone}
            className="w-40 rounded-lg border border-[var(--color-sc-line)] px-2 py-1.5 text-sm"
            placeholder="Phone"
            aria-label="Lookup phone"
          />
          <button
            type="submit"
            className="rounded-lg bg-[var(--color-sc-green)] px-3 text-xs font-bold text-white"
          >
            Find
          </button>
        </form>
      </div>

      {error ? (
        <p className="mb-3 text-sm font-semibold text-[var(--color-sc-warn)]">{error}</p>
      ) : null}
      {loading ? (
        <p className="mb-3 text-sm text-[var(--color-sc-muted)]">Loading profile…</p>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[240px_minmax(0,1.2fr)_280px]">
        <aside className="rounded-2xl bg-[var(--color-sc-soft)] p-6">
          <div className="flex h-20 w-20 items-center justify-center rounded-full bg-[var(--color-sc-green)] text-2xl font-bold text-white">
            {initials(name)}
          </div>
          <h2 className="mt-4 sc-section-title">{name}</h2>
          <p className="mt-1 text-sm text-[var(--color-sc-muted)]">
            {tier} | {lang}
          </p>
          {fayda ? (
            <span className="mt-3 inline-flex rounded-full bg-[var(--color-sc-green)] px-3 py-1 text-[11px] font-bold text-white">
              Fayda verified
            </span>
          ) : null}

          <dl className="mt-6 space-y-4">
            {[
              ['Contacts this week', String(weekContacts)],
              ['Satisfaction', csat],
              ['Sentiment', sentiment],
              ['Phone', contact?.phone || selectedPhone],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-xs text-[var(--color-sc-muted)]">{label}</dt>
                <dd className="mt-0.5 break-all text-sm font-bold text-[var(--color-sc-ink)]">{value}</dd>
              </div>
            ))}
          </dl>
        </aside>

        <CustomerJourneyTrack items={journey} />

        <aside className="flex flex-col gap-3">
          <div className="rounded-2xl border border-[var(--color-sc-line)] bg-white p-4">
            <h3 className="sc-section-title">Products and cases</h3>
            <p className="mt-2 text-sm text-[var(--color-sc-ink)]">{products}</p>
            <p className="mt-2 text-sm font-semibold text-[var(--color-sc-green)]">{openLabel}</p>
          </div>

          <div className="rounded-2xl bg-[var(--color-sc-soft)] p-4">
            <div className="flex items-center justify-between gap-2">
              <h3 className="sc-section-title">AI summary</h3>
              <button
                type="button"
                onClick={runAi}
                disabled={aiBusy}
                className="text-[11px] font-bold text-[var(--color-sc-green)] hover:underline disabled:opacity-50"
              >
                {aiBusy ? '…' : 'Refresh'}
              </button>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-[var(--color-sc-ink)]">{aiSummary}</p>
          </div>

          <div className="rounded-2xl border border-[var(--color-sc-green)]/30 bg-[var(--color-sc-alert)] p-4">
            <p className="text-sm font-bold leading-snug text-[var(--color-sc-forest)]">
              Next best action: {nextAction}
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
