import { useState } from 'react';
import StudioPage from './StudioPage';
import { useStudio } from './useStudio';

export default function AdminRoles() {
  const { data, err, loading, save } = useStudio();
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setMsg('');
    try {
      await fn();
      setMsg((cur) => cur || 'Saved');
      return true;
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Save failed');
      return false;
    } finally {
      setBusy(false);
    }
  };

  return (
    <StudioPage
      title="Roles"
      path="/admin/roles"
      blurb="Permission sets for SkyConnect users — clone agent / supervisor / admin, then assign on Accounts"
    >
      {err ? <p className="text-sm text-[var(--color-sc-warn)]">{err}</p> : null}
      {loading && !(data?.roles || []).length ? <p className="sc-meta">Loading roles…</p> : null}
      {msg ? <p className="text-sm font-bold">{msg}</p> : null}
      <RoleBuilder
        catalog={data?.permission_catalog || []}
        roles={data?.roles || []}
        busy={busy}
        onSave={async (body) => {
          await run(async () => {
            await save('group_save', body);
          });
        }}
        onDelete={async (body) =>
          run(async () => {
            await save('group_delete', body);
          })
        }
      />
    </StudioPage>
  );
}

function RoleBuilder({
  catalog,
  roles,
  busy,
  onSave,
  onDelete,
}: {
  catalog: { application_name: string; permission_name: string }[];
  roles: {
    group_uuid: string;
    group_name: string;
    group_level: number;
    group_description: string;
    global?: boolean;
    protected?: boolean;
    permissions: string[];
  }[];
  busy: boolean;
  onSave: (body: Record<string, unknown>) => Promise<void>;
  onDelete: (body: Record<string, unknown>) => Promise<boolean>;
}) {
  const [editId, setEditId] = useState('');
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [level, setLevel] = useState(20);
  const [clone, setClone] = useState('');
  const [filter, setFilter] = useState('');
  const [picked, setPicked] = useState<string[]>([]);
  const apps = Array.from(new Set(catalog.map((c) => c.application_name || 'other')));
  const q = filter.toLowerCase();
  const shown = catalog.filter(
    (c) =>
      !q ||
      c.permission_name.toLowerCase().includes(q) ||
      (c.application_name || '').toLowerCase().includes(q),
  );

  const loadRole = (id: string) => {
    setEditId(id);
    const r = roles.find((x) => x.group_uuid === id);
    if (!r) {
      setName('');
      setDesc('');
      setLevel(20);
      setPicked([]);
      return;
    }
    setName(r.group_name);
    setDesc(r.group_description);
    setLevel(r.group_level || 20);
    setPicked(r.permissions || []);
  };

  const applyClone = (id: string) => {
    setClone(id);
    const r = roles.find((x) => x.group_uuid === id);
    if (r?.permissions?.length) setPicked(r.permissions);
  };

  const editing = roles.find((x) => x.group_uuid === editId);
  const lockedNames = ['superadmin', 'public', 'agent', 'supervisor', 'admin'];
  const canDelete = Boolean(
    editing &&
      !editing.global &&
      !editing.protected &&
      !lockedNames.includes(editing.group_name.toLowerCase()),
  );

  return (
    <section className="sc-card">
      <h2 className="mb-1 text-[16px] font-bold">Roles from permissions</h2>
      <p className="sc-meta mb-3">
        FusionPBX permissions from <code>v_permissions</code>. Clone agent / supervisor / admin, tick what this role may
        do, then save.
      </p>
      <div className="mb-3 flex flex-wrap gap-2">
        {roles.map((r) => (
          <button
            key={r.group_uuid}
            type="button"
            className={`sc-b2 ${editId === r.group_uuid ? '!bg-[#d6efe4]' : ''}`}
            onClick={() => loadRole(r.group_uuid)}
          >
            {r.group_name}
            <span className="ml-1 sc-meta">{r.permissions?.length || 0}</span>
          </button>
        ))}
        <button type="button" className="sc-b2" onClick={() => loadRole('')}>
          New role
        </button>
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <input
          className="sc-input"
          placeholder="Role name (qa, team_lead)"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <input className="sc-input" placeholder="Description" value={desc} onChange={(e) => setDesc(e.target.value)} />
        <select className="sc-input" value={level} onChange={(e) => setLevel(Number(e.target.value))}>
          <option value={20}>Level 20 · like agent</option>
          <option value={30}>Level 30 · like user</option>
          <option value={40}>Level 40 · like supervisor</option>
          <option value={50}>Level 50 · like admin</option>
        </select>
        <select className="sc-input" value={clone} onChange={(e) => applyClone(e.target.value)}>
          <option value="">Start from empty, or clone…</option>
          {roles.map((r) => (
            <option key={r.group_uuid} value={r.group_uuid}>
              Clone {r.group_name} ({r.permissions?.length || 0} perms)
            </option>
          ))}
        </select>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <input
          className="sc-input max-w-sm"
          placeholder="Filter permissions (ivr, queue, cdr…)"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        <span className="sc-meta">
          {picked.length} selected · {shown.length} shown
        </span>
        <button
          type="button"
          className="sc-btn"
          disabled={busy || name.trim() === ''}
          onClick={() =>
            void onSave({
              group_uuid: editId,
              group_name: name,
              group_description: desc,
              group_level: level,
              clone_from: picked.length ? '' : clone,
              permissions: picked,
            })
          }
        >
          Save role
        </button>
        {canDelete ? (
          <button
            type="button"
            className="sc-b2"
            disabled={busy}
            onClick={() => {
              if (!window.confirm(`Delete role “${editing?.group_name}”? Users keep their accounts; this role is removed.`)) {
                return;
              }
              void onDelete({ group_uuid: editId }).then((ok) => {
                if (ok) loadRole('');
              });
            }}
          >
            Delete role
          </button>
        ) : editId ? (
          <span className="sc-meta">Built-in / global roles cannot be deleted</span>
        ) : null}
      </div>
      <div className="mt-3 max-h-[360px] overflow-auto rounded-[10px] border border-[var(--color-sc-line)] p-3">
        {apps.map((app) => {
          const items = shown.filter((c) => (c.application_name || 'other') === app);
          if (!items.length) return null;
          const allOn = items.every((i) => picked.includes(i.permission_name));
          return (
            <div key={app} className="mb-3">
              <label className="mb-1 flex items-center gap-2 text-sm font-bold">
                <input
                  type="checkbox"
                  checked={allOn}
                  onChange={(e) => {
                    const next = new Set(picked);
                    items.forEach((i) => {
                      if (e.target.checked) next.add(i.permission_name);
                      else next.delete(i.permission_name);
                    });
                    setPicked([...next]);
                  }}
                />
                {app}
              </label>
              <div className="grid gap-1 sm:grid-cols-2 lg:grid-cols-3">
                {items.map((i) => (
                  <label key={i.permission_name} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={picked.includes(i.permission_name)}
                      onChange={(e) => {
                        const next = new Set(picked);
                        if (e.target.checked) next.add(i.permission_name);
                        else next.delete(i.permission_name);
                        setPicked([...next]);
                      }}
                    />
                    {i.permission_name}
                  </label>
                ))}
              </div>
            </div>
          );
        })}
        {catalog.length === 0 ? <p className="sc-meta">Permission catalog not loaded</p> : null}
      </div>
    </section>
  );
}
