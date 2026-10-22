import { useCallback, useEffect, useState } from 'react';
import {
  getKnowledgeArticle,
  listKnowledge,
  saveKnowledge,
  type KnowledgeArticle,
} from '../../services/crm';

function relativeUpdated(raw?: string): string {
  if (!raw) return '—';
  const d = new Date(raw.includes('T') ? raw : raw.replace(' ', 'T'));
  if (Number.isNaN(d.getTime())) return raw.slice(0, 16);
  const dayDiff = Math.round(
    (new Date().setHours(0, 0, 0, 0) -
      new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()) /
      86400000,
  );
  if (dayDiff === 0) return 'Today';
  if (dayDiff === 1) return 'Yesterday';
  if (dayDiff > 1 && dayDiff < 7) return `${dayDiff} days ago`;
  if (dayDiff >= 7 && dayDiff < 14) return 'Last week';
  return raw.slice(0, 10);
}

export default function Knowledge({ canEdit = false }: { canEdit?: boolean }) {
  const [query, setQuery] = useState('');
  const [list, setList] = useState<KnowledgeArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [open, setOpen] = useState<KnowledgeArticle | null>(null);
  const [opening, setOpening] = useState(false);
  const [draft, setDraft] = useState({ article_id: 0, title: '', tag: 'Guide', body: '', keywords: '' });
  const [saving, setSaving] = useState('');

  const reload = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setList(await listKnowledge(query));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load knowledge');
      setList([]);
    } finally {
      setLoading(false);
    }
  }, [query]);

  useEffect(() => {
    const t = window.setTimeout(() => {
      void reload();
    }, 200);
    return () => clearTimeout(t);
  }, [reload]);

  const openArticle = async (id: number) => {
    setOpening(true);
    setError('');
    try {
      const row = await getKnowledgeArticle(id);
      setOpen(row);
      if (!row) setError('Article not found');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not open article');
    } finally {
      setOpening(false);
    }
  };

  if (open) {
    return (
      <div className="mx-auto max-w-3xl">
        <button
          type="button"
          onClick={() => setOpen(null)}
          className="mb-3 text-xs font-bold text-[var(--color-sc-green)] hover:underline"
        >
          ← Back to Knowledge
        </button>
        <div className="rounded-2xl border border-[var(--color-sc-line)] bg-white p-6">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-[var(--color-sc-nav-active)] px-2.5 py-1 text-[11px] font-bold text-[var(--color-sc-forest)]">
              {open.tag || 'Guide'}
            </span>
            <span className="text-xs text-[var(--color-sc-muted)]">
              Updated {relativeUpdated(open.updated_at)}
            </span>
          </div>
          <h1 className="sc-page-title">
            {open.title}
          </h1>
          <div className="mt-5 whitespace-pre-wrap text-sm leading-relaxed text-[var(--color-sc-ink)]">
            {open.body || '—'}
          </div>
          {canEdit ? (
            <button
              type="button"
              className="mt-4 text-sm font-bold text-[var(--color-sc-green)]"
              onClick={() => {
                setDraft({
                  article_id: Number(open.article_id || 0),
                  title: open.title || '',
                  tag: open.tag || 'Guide',
                  body: open.body || '',
                  keywords: open.keywords || '',
                });
                setOpen(null);
              }}
            >
              Load into editor
            </button>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-1 sc-page-title">
        Knowledge
      </h1>
      <p className="mb-4 text-sm text-[var(--color-sc-muted)]">
        Scripts and policies for live calls — search SIM, telebirr, Fayda, packages…
      </p>
      <input
        className="mb-4 w-full rounded-xl border border-[var(--color-sc-line)] bg-white px-4 py-2.5 text-sm"
        placeholder="Search articles, scripts, policies…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        aria-label="Search knowledge"
      />
      {error ? (
        <p className="mb-3 text-sm font-semibold text-[var(--color-sc-warn)]">{error}</p>
      ) : null}
      {canEdit ? (
        <div className="mb-4 rounded-xl border border-[var(--color-sc-line)] bg-white p-4">
          <p className="mb-2 text-sm font-bold">New / update article</p>
          <input
            className="mb-2 w-full rounded-lg border border-[var(--color-sc-line)] px-3 py-2 text-sm"
            placeholder="Title"
            value={draft.title}
            onChange={(e) => setDraft((d) => ({ ...d, title: e.target.value }))}
          />
          <input
            className="mb-2 w-full rounded-lg border border-[var(--color-sc-line)] px-3 py-2 text-sm"
            placeholder="Tag"
            value={draft.tag}
            onChange={(e) => setDraft((d) => ({ ...d, tag: e.target.value }))}
          />
          <textarea
            className="mb-2 w-full rounded-lg border border-[var(--color-sc-line)] px-3 py-2 text-sm"
            rows={5}
            placeholder="Body"
            value={draft.body}
            onChange={(e) => setDraft((d) => ({ ...d, body: e.target.value }))}
          />
          <button
            type="button"
            className="rounded-full bg-[var(--color-sc-green)] px-4 py-2 text-sm font-bold text-white"
            onClick={async () => {
              setSaving('');
              try {
                await saveKnowledge({
                  article_id: draft.article_id || undefined,
                  title: draft.title,
                  tag: draft.tag,
                  body: draft.body,
                  keywords: draft.keywords,
                });
                setSaving('Saved');
                setDraft({ article_id: 0, title: '', tag: 'Guide', body: '', keywords: '' });
                await reload();
              } catch (e) {
                setSaving(e instanceof Error ? e.message : 'Save failed');
              }
            }}
          >
            Publish
          </button>
          {saving ? <span className="ml-2 text-sm font-bold">{saving}</span> : null}
        </div>
      ) : null}
      {opening || loading ? (
        <p className="text-sm text-[var(--color-sc-muted)]">Loading…</p>
      ) : list.length === 0 ? (
        <p className="rounded-xl border border-[var(--color-sc-line)] bg-white p-5 text-sm text-[var(--color-sc-muted)]">
          No articles match. Try “SIM”, “telebirr”, or “Fayda”.
        </p>
      ) : (
        <div className="space-y-2">
          {list.map((a) => (
            <button
              key={a.article_id ?? a.title}
              type="button"
              onClick={() => {
                const id = Number(a.article_id);
                if (id > 0) void openArticle(id);
              }}
              className="flex w-full items-center justify-between gap-3 rounded-xl border border-[var(--color-sc-line)] bg-white px-4 py-3 text-left hover:bg-[var(--color-sc-soft)]"
            >
              <div className="min-w-0">
                <p className="sc-section-title">{a.title}</p>
                <p className="mt-0.5 line-clamp-2 text-xs text-[var(--color-sc-muted)]">
                  {a.excerpt || `Updated ${relativeUpdated(a.updated_at)}`}
                </p>
              </div>
              <span className="shrink-0 rounded-full bg-[var(--color-sc-nav-active)] px-2.5 py-1 text-[11px] font-bold text-[var(--color-sc-forest)]">
                {a.tag || 'Guide'}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
