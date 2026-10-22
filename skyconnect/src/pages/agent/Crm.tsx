import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  deleteContact,
  initials,
  listContacts,
  saveContact,
  type CrmContact,
} from '../../services/crm';

const emptyForm = {
  contact_id: undefined as number | undefined,
  full_name: '',
  phone: '',
  alt_phone: '',
  email: '',
  company: '',
  language: 'Amharic',
  account_type: 'Customer',
  notes: '',
  products: '',
  fayda_verified: false,
  csat: '',
  sentiment: 'Neutral',
};

const fieldLabel = 'block text-[14px] font-semibold text-[var(--color-sc-muted)]';
const fieldInput =
  'mt-1 w-full rounded-lg border border-[var(--color-sc-line)] bg-white px-3 py-2 text-[14px] font-medium text-[var(--color-sc-ink)]';

export default function Crm() {
  const [list, setList] = useState<CrmContact[]>([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ ...emptyForm });
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [saving, setSaving] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      setList(await listContacts(query));
    } catch {
      setList([]);
    } finally {
      setLoading(false);
    }
  }, [query]);

  useEffect(() => {
    const t = window.setTimeout(() => {
      reload();
    }, 200);
    return () => clearTimeout(t);
  }, [reload]);

  const setField = (key: keyof typeof emptyForm, value: string | boolean | number | undefined) => {
    setForm((f) => ({ ...f, [key]: value }));
  };

  const edit = (c: CrmContact) => {
    setErr('');
    setMsg('');
    setForm({
      contact_id: c.contact_id,
      full_name: c.full_name || '',
      phone: c.phone || '',
      alt_phone: c.alt_phone || '',
      email: c.email || '',
      company: c.company || '',
      language: c.language || 'Amharic',
      account_type: c.account_type || 'Customer',
      notes: c.notes || '',
      products: c.products || '',
      fayda_verified: Boolean(c.fayda_verified),
      csat: c.csat != null && c.csat !== '' ? String(c.csat) : '',
      sentiment: c.sentiment || 'Neutral',
    });
  };

  const reset = () => {
    setForm({ ...emptyForm });
    setErr('');
    setMsg('');
  };

  const onSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr('');
    setMsg('');
    if (!form.full_name.trim() || !form.phone.trim()) {
      setErr('Name and phone are required');
      return;
    }
    setSaving(true);
    try {
      await saveContact({
        contact_id: form.contact_id,
        full_name: form.full_name.trim(),
        phone: form.phone.trim(),
        alt_phone: form.alt_phone.trim(),
        email: form.email.trim(),
        company: form.company.trim(),
        language: form.language,
        account_type: form.account_type,
        notes: form.notes.trim(),
        products: form.products.trim(),
        fayda_verified: form.fayda_verified,
        csat: form.csat === '' ? null : Number(form.csat),
        sentiment: form.sentiment,
      });
      setMsg(form.contact_id ? 'Contact updated' : 'Contact created');
      reset();
      await reload();
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const onDelete = async () => {
    if (!form.contact_id) return;
    if (!window.confirm(`Delete ${form.full_name || form.phone}?`)) return;
    try {
      await deleteContact(form.contact_id);
      setMsg('Deleted');
      reset();
      await reload();
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : 'Delete failed');
    }
  };

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="sc-page-title">CRM</h1>
          <p className="mt-1 text-[14px] text-[var(--color-sc-muted)]">
            Save customer name and phone — used by Customer 360 and the history track
          </p>
        </div>
        <button
          type="button"
          onClick={reset}
          className="rounded-lg border border-[var(--color-sc-line)] bg-white px-3 py-2 text-[14px] font-bold text-[var(--color-sc-forest)] hover:bg-[var(--color-sc-soft)]"
        >
          New contact
        </button>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <section className="overflow-hidden rounded-2xl border border-[var(--color-sc-line)] bg-white">
          <div className="border-b border-[var(--color-sc-line)] bg-[var(--color-sc-soft)] px-4 py-3">
            <input
              className="w-full rounded-lg border border-[var(--color-sc-line)] bg-white px-3 py-2 text-[14px]"
              placeholder="Search name, phone, company…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Search CRM"
            />
          </div>
          {loading ? (
            <p className="p-5 text-[14px] text-[var(--color-sc-muted)]">Loading…</p>
          ) : list.length === 0 ? (
            <p className="p-5 text-[14px] text-[var(--color-sc-muted)]">No contacts yet — add one on the right.</p>
          ) : (
            <ul className="max-h-[70vh] divide-y divide-[var(--color-sc-line)] overflow-auto">
              {list.map((c) => {
                const label = c.full_name || c.phone || 'Contact';
                const active = form.contact_id != null && form.contact_id === c.contact_id;
                return (
                  <li key={c.contact_id ?? `${c.phone}-${label}`}>
                    <button
                      type="button"
                      onClick={() => edit(c)}
                      className={`flex w-full items-center gap-3 px-4 py-3 text-left transition ${
                        active ? 'bg-[var(--color-sc-nav-active)]' : 'hover:bg-[var(--color-sc-soft)]'
                      }`}
                    >
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--color-sc-green)] text-[13px] font-bold text-white">
                        {initials(label)}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block text-[14px] font-semibold text-[var(--color-sc-ink)]">
                          {label}
                        </span>
                        <span className="mt-0.5 block text-[13px] text-[var(--color-sc-muted)]">
                          {c.phone || '—'}
                          {c.account_type ? ` · ${c.account_type}` : ''}
                          {c.language ? ` · ${c.language}` : ''}
                          {c.fayda_verified ? ' · Fayda' : ''}
                        </span>
                      </span>
                      {c.phone ? (
                        <Link
                          to={`/agent/customers?phone=${encodeURIComponent(c.phone)}`}
                          onClick={(e) => e.stopPropagation()}
                          className="shrink-0 text-[13px] font-bold text-[var(--color-sc-green)] hover:underline"
                        >
                          360 →
                        </Link>
                      ) : null}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <aside className="rounded-2xl border border-[var(--color-sc-line)] bg-[var(--color-sc-soft)] p-5">
          <h2 className="sc-section-title">
            {form.contact_id ? 'Edit contact' : 'Add contact'}
          </h2>
          <form className="mt-4 space-y-3.5" onSubmit={onSave}>
            <label className={fieldLabel}>
              Full name
              <input
                className={fieldInput}
                value={form.full_name}
                onChange={(e) => setField('full_name', e.target.value)}
                required
              />
            </label>
            <label className={fieldLabel}>
              Phone
              <input
                className={fieldInput}
                value={form.phone}
                onChange={(e) => setField('phone', e.target.value)}
                placeholder="0911… or 101"
                required
              />
            </label>
            <label className={fieldLabel}>
              Alt phone
              <input
                className={fieldInput}
                value={form.alt_phone}
                onChange={(e) => setField('alt_phone', e.target.value)}
              />
            </label>
            <div className="grid grid-cols-2 gap-2">
              <label className={fieldLabel}>
                Language
                <select
                  className={fieldInput}
                  value={form.language}
                  onChange={(e) => setField('language', e.target.value)}
                >
                  {['Amharic', 'English', 'Oromo', 'Tigrinya', 'Other'].map((l) => (
                    <option key={l} value={l}>
                      {l}
                    </option>
                  ))}
                </select>
              </label>
              <label className={fieldLabel}>
                Tier
                <select
                  className={fieldInput}
                  value={form.account_type}
                  onChange={(e) => setField('account_type', e.target.value)}
                >
                  {['Customer', 'Gold', 'VIP', 'Silver'].map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <label className={fieldLabel}>
              Products
              <input
                className={fieldInput}
                value={form.products}
                onChange={(e) => setField('products', e.target.value)}
                placeholder="Prepaid plan | telebirr wallet"
              />
            </label>
            <label className={fieldLabel}>
              Company / email
              <input
                className={fieldInput}
                value={form.company}
                onChange={(e) => setField('company', e.target.value)}
                placeholder="Company"
              />
              <input
                className={`${fieldInput} mt-2`}
                value={form.email}
                onChange={(e) => setField('email', e.target.value)}
                placeholder="Email"
                type="email"
              />
            </label>
            <div className="grid grid-cols-2 gap-2">
              <label className={fieldLabel}>
                CSAT
                <input
                  className={fieldInput}
                  value={form.csat}
                  onChange={(e) => setField('csat', e.target.value)}
                  placeholder="5"
                  inputMode="decimal"
                />
              </label>
              <label className={fieldLabel}>
                Sentiment
                <select
                  className={fieldInput}
                  value={form.sentiment}
                  onChange={(e) => setField('sentiment', e.target.value)}
                >
                  {['Neutral', 'Positive', 'Negative'].map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <label className="flex items-center gap-2 text-[14px] font-semibold text-[var(--color-sc-ink)]">
              <input
                type="checkbox"
                checked={form.fayda_verified}
                onChange={(e) => setField('fayda_verified', e.target.checked)}
                className="h-4 w-4 accent-[var(--color-sc-green)]"
              />
              Fayda verified
            </label>
            <label className={fieldLabel}>
              Notes
              <textarea
                className={`${fieldInput} min-h-[88px] resize-y`}
                value={form.notes}
                onChange={(e) => setField('notes', e.target.value)}
              />
            </label>

            {err ? <p className="text-[14px] font-semibold text-[var(--color-sc-warn)]">{err}</p> : null}
            {msg ? <p className="text-[14px] font-semibold text-[var(--color-sc-green)]">{msg}</p> : null}

            <button
              type="submit"
              disabled={saving}
              className="w-full rounded-lg bg-[var(--color-sc-green)] py-2.5 text-[14px] font-bold text-white hover:bg-[#159a42] disabled:opacity-60"
            >
              {saving ? 'Saving…' : form.contact_id ? 'Update contact' : 'Save contact'}
            </button>
            {form.contact_id ? (
              <div className="flex gap-2">
                {form.phone ? (
                  <Link
                    to={`/agent/customers?phone=${encodeURIComponent(form.phone)}`}
                    className="flex-1 rounded-lg border border-[var(--color-sc-line)] bg-white py-2 text-center text-[14px] font-bold text-[var(--color-sc-forest)]"
                  >
                    Open 360
                  </Link>
                ) : null}
                <button
                  type="button"
                  onClick={onDelete}
                  className="flex-1 rounded-lg bg-[#D9534F] py-2 text-[14px] font-bold text-white"
                >
                  Delete
                </button>
              </div>
            ) : null}
          </form>
        </aside>
      </div>
    </div>
  );
}
