import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listCases, updateCaseStatus, type CrmCaseRow } from '../../services/crm';

const STATUSES = ['Open', 'Follow-up', 'Escalated', 'In Progress', 'Resolved', 'Closed'] as const;

function statusSelectClass(s: string): string {
  const x = s.toLowerCase();
  if (x === 'resolved' || x === 'closed') {
    return 'border-[var(--color-sc-line)] bg-[var(--color-sc-idle-btn)] text-white';
  }
  if (x === 'escalated' || x === 'follow-up') {
    return 'border-orange-300 bg-orange-100 text-orange-900';
  }
  return 'border-[var(--color-sc-green)] bg-[var(--color-sc-green)] text-white';
}

function ageLabel(created?: string): string {
  if (!created) return '—';
  const d = new Date(created.includes('T') ? created : created.replace(' ', 'T'));
  if (Number.isNaN(d.getTime())) return created.slice(0, 16);
  const mins = Math.round((Date.now() - d.getTime()) / 60000);
  if (mins < 60) return `${Math.max(0, mins)}m`;
  const hrs = Math.round(mins / 60);
  if (hrs < 48) return `${hrs}h`;
  return `${Math.round(hrs / 24)}d`;
}

export default function Cases() {
  const [rows, setRows] = useState<CrmCaseRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('All');
  const [query, setQuery] = useState('');

  const reload = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const list = await listCases({
        phone: query.trim() || undefined,
        status: filter === 'All' ? undefined : filter,
      });
      setRows(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load cases');
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [filter, query]);

  useEffect(() => {
    const t = window.setTimeout(() => {
      void reload();
    }, 200);
    return () => clearTimeout(t);
  }, [reload]);

  const onStatus = async (caseId: number, status: string) => {
    try {
      await updateCaseStatus(caseId, status);
      setRows((prev) =>
        prev.map((r) => (Number(r.case_id) === caseId ? { ...r, status } : r)),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Status update failed');
    }
  };

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="sc-page-title">Cases</h1>
          <p className="mt-1 text-sm text-[var(--color-sc-muted)]">
            Call reason and status from wrap-up — update status here anytime
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <input
            className="w-40 rounded-lg border border-[var(--color-sc-line)] bg-white px-3 py-2 text-sm"
            placeholder="Phone filter"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Filter by phone"
          />
          <select
            className="rounded-lg border border-[var(--color-sc-line)] bg-white px-3 py-2 text-sm"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            aria-label="Filter by status"
          >
            <option value="All">All statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => void reload()}
            className="rounded-lg border border-[var(--color-sc-line)] bg-white px-3 py-2 text-xs font-bold text-[var(--color-sc-forest)]"
          >
            Refresh
          </button>
        </div>
      </div>

      {error ? (
        <p className="mb-3 text-sm font-semibold text-[var(--color-sc-warn)]">{error}</p>
      ) : null}

      <div className="overflow-hidden rounded-xl border border-[var(--color-sc-line)] bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-[var(--color-sc-soft)] text-[11px] uppercase text-[var(--color-sc-muted)]">
            <tr>
              <th className="px-3 py-2">Case</th>
              <th className="px-3 py-2">Reason</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Customer</th>
              <th className="px-3 py-2">Agent</th>
              <th className="px-3 py-2">Age</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-[var(--color-sc-muted)]">
                  Loading…
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-[var(--color-sc-muted)]">
                  No cases yet. Save a call reason on Wrap-up after a call — reason and status land
                  here.
                </td>
              </tr>
            ) : (
              rows.map((c) => {
                const id = Number(c.case_id);
                const reason = c.issue_type || c.description || '—';
                const st = c.status || 'Open';
                const phone = c.customer_phone || '';
                return (
                  <tr key={c.case_id ?? reason} className="border-t border-[var(--color-sc-line)]">
                    <td className="px-3 py-2.5 font-semibold text-[var(--color-sc-green)]">
                      C-{id || '—'}
                    </td>
                    <td className="px-3 py-2.5">
                      <p className="font-medium text-[var(--color-sc-ink)]">{reason}</p>
                      {c.description && c.description !== reason ? (
                        <p className="mt-0.5 text-xs text-[var(--color-sc-muted)]">
                          {c.description}
                        </p>
                      ) : null}
                    </td>
                    <td className="w-[1%] whitespace-nowrap px-3 py-2.5 align-middle">
                      {id > 0 ? (
                        <select
                          className={`rounded-full px-3 py-1 text-[11px] font-bold ${statusSelectClass(st)}`}
                          value={STATUSES.includes(st as (typeof STATUSES)[number]) ? st : 'Open'}
                          onChange={(e) => void onStatus(id, e.target.value)}
                          aria-label={`Status for case ${id}`}
                        >
                          {STATUSES.map((s) => (
                            <option key={s} value={s} className="bg-white text-[var(--color-sc-ink)]">
                              {s}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <span className="text-xs text-[var(--color-sc-muted)]">{st}</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5">
                      <p className="font-medium">{c.customer_name || '—'}</p>
                      {phone ? (
                        <Link
                          to={`/agent/customers?phone=${encodeURIComponent(phone)}`}
                          className="text-xs font-bold text-[var(--color-sc-green)] hover:underline"
                        >
                          {phone}
                        </Link>
                      ) : (
                        <span className="text-xs text-[var(--color-sc-muted)]">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5">{c.agent_id || '—'}</td>
                    <td className="px-3 py-2.5">{ageLabel(c.created_at)}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
