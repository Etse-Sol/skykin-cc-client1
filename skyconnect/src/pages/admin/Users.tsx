import { Fragment, useState } from 'react';
import StudioPage from './StudioPage';
import { useStudio, type StudioUser } from './useStudio';

const ROLE_KEYS = ['agent', 'supervisor', 'admin'] as const;
const PASS_MIN = 12;

function passwordScore(p: string) {
  const checks = [
    { ok: p.length >= PASS_MIN, label: `At least ${PASS_MIN} characters` },
    { ok: /[a-z]/.test(p), label: 'Lowercase letter' },
    { ok: /[A-Z]/.test(p), label: 'Uppercase letter' },
    { ok: /\d/.test(p), label: 'Number' },
    { ok: /[^A-Za-z0-9]/.test(p), label: 'Special character' },
  ];
  const score = checks.filter((c) => c.ok).length;
  const label = score <= 1 ? 'Very weak' : score === 2 ? 'Weak' : score === 3 ? 'Fair' : score === 4 ? 'Strong' : 'Very strong';
  return { checks, score, label, ready: p.length >= PASS_MIN };
}

function PasswordMeter({ value }: { value: string }) {
  const s = passwordScore(value);
  if (!value) return null;
  const colors = ['#c45c4a', '#c45c4a', '#c9a227', '#3d8b6e', '#1f6b4a'];
  return (
    <div className="mt-2">
      <div className="flex gap-1">
        {[0, 1, 2, 3, 4].map((i) => (
          <span
            key={i}
            className="h-1.5 flex-1 rounded-full"
            style={{ background: i < s.score ? colors[s.score - 1] : 'var(--color-sc-line)' }}
          />
        ))}
      </div>
      <p className="mt-1 text-[12px] font-bold" style={{ color: colors[Math.max(0, s.score - 1)] }}>
        {s.label}
      </p>
      <ul className="mt-1 space-y-0.5 text-[11px] text-[var(--color-sc-muted)]">
        {s.checks.map((c) => (
          <li key={c.label}>
            {c.ok ? '✓' : '○'} {c.label}
          </li>
        ))}
      </ul>
    </div>
  );
}

function enabledOf(u: StudioUser) {
  return String(u.user_enabled || '').toLowerCase() === 'true';
}

function groupsOf(u: StudioUser) {
  if (u.group_list?.length) return u.group_list.map((g) => g.toLowerCase());
  return String(u.groups || '')
    .split(',')
    .map((g) => g.trim().toLowerCase())
    .filter(Boolean);
}

export default function AdminUsers() {
  const { data, err, loading, save } = useStudio();
  const rows = data?.users || [];
  const extraRoles = (data?.roles || []).filter(
    (r) => !['agent', 'supervisor', 'admin', 'superadmin', 'public'].includes(r.group_name.toLowerCase()),
  );
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState('');
  const [editId, setEditId] = useState('');
  const [edit, setEdit] = useState({
    password: '',
    password2: '',
    extension: '',
    sip_password: '',
    sip_password2: '',
  });
  const [form, setForm] = useState({
    username: '',
    password: '',
    password2: '',
    user_email: '',
    extension: '',
    create_extension: true,
    sip_password: '',
    sip_password2: '',
    group_list: ['agent'] as string[],
  });
  const nextExt = data?.next_extension || '103';
  const setF = (patch: Partial<typeof form>) => setForm({ ...form, ...patch });
  const emptyForm = {
    username: '',
    password: '',
    password2: '',
    user_email: '',
    extension: '',
    create_extension: true,
    sip_password: '',
    sip_password2: '',
    group_list: ['agent'] as string[],
  };

  const run = async (label: string, fn: () => Promise<void>) => {
    setBusy(label);
    setMsg('');
    try {
      await fn();
      setMsg((cur) => cur || 'Saved');
      return true;
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Save failed');
      return false;
    } finally {
      setBusy('');
    }
  };

  const toggleRole = (u: StudioUser, role: string, on: boolean) => {
    const next = new Set(groupsOf(u));
    if (on) next.add(role);
    else next.delete(role);
    void run(u.user_uuid || u.username || '', async () => {
      await save('user_save', {
        user_uuid: u.user_uuid,
        username: u.username,
        user_email: u.user_email,
        user_enabled: enabledOf(u),
        group_list: [...next],
        extension: u.extension || '',
      });
    });
  };

  return (
    <StudioPage
      title="Accounts"
      path="/admin/users"
      blurb="Create accounts, assign Agent / Supervisor / Admin, enable or disable — saved to FusionPBX"
    >
      {err ? <p className="text-sm text-[var(--color-sc-warn)]">{err}</p> : null}
      {data?.notes?.length ? <p className="text-sm text-[var(--color-sc-warn)]">{data.notes.join(' · ')}</p> : null}
      {msg ? <p className="text-sm font-bold">{msg}</p> : null}

      <section className="sc-card">
        <h2 className="mb-1 text-[16px] font-bold">Add user</h2>
        <p className="sc-meta mb-5">Same pattern as FusionPBX: username, password, confirm, then extension.</p>

        <h3 className="mb-3 text-[12px] font-bold uppercase tracking-wide text-[var(--color-sc-muted)]">Account</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="flex flex-col gap-1.5">
            <span className="text-[12px] font-bold">Username</span>
            <input className="sc-input" autoComplete="off" value={form.username} onChange={(e) => setF({ username: e.target.value })} />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-[12px] font-bold">Email</span>
            <input className="sc-input" autoComplete="off" value={form.user_email} onChange={(e) => setF({ user_email: e.target.value })} />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-[12px] font-bold">Password</span>
            <input className="sc-input" type="password" autoComplete="new-password" value={form.password} onChange={(e) => setF({ password: e.target.value })} />
            <PasswordMeter value={form.password} />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-[12px] font-bold">Confirm password</span>
            <input className="sc-input" type="password" autoComplete="new-password" value={form.password2} onChange={(e) => setF({ password2: e.target.value })} />
            {form.password2 ? (
              <p className={`text-[12px] font-bold ${form.password === form.password2 ? 'text-[var(--color-sc-green)]' : 'text-[var(--color-sc-warn)]'}`}>
                {form.password === form.password2 ? 'Passwords match' : 'Passwords do not match'}
              </p>
            ) : null}
          </label>
        </div>

        <h3 className="mb-3 mt-6 text-[12px] font-bold uppercase tracking-wide text-[var(--color-sc-muted)]">Extension</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="flex flex-col gap-1.5">
            <span className="text-[12px] font-bold">Extension number</span>
            <input
              className="sc-input"
              type="text"
              autoComplete="off"
              placeholder={`e.g. ${nextExt}`}
              value={form.extension}
              onChange={(e) => setF({ extension: e.target.value.replace(/[^\d]/g, '').slice(0, 8) })}
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-[12px] font-bold">SIP password</span>
            <input
              className="sc-input"
              type="password"
              autoComplete="new-password"
              placeholder="Leave blank to generate"
              value={form.sip_password}
              onChange={(e) => setF({ sip_password: e.target.value })}
            />
          </label>
          <label className="flex items-center gap-2 pt-6 text-sm">
            <input type="checkbox" checked={form.create_extension} onChange={(e) => setF({ create_extension: e.target.checked })} />
            Create this extension if it does not exist
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-[12px] font-bold">Confirm SIP password</span>
            <input
              className="sc-input"
              type="password"
              autoComplete="new-password"
              placeholder="Required only if you typed a SIP password"
              value={form.sip_password2}
              onChange={(e) => setF({ sip_password2: e.target.value })}
            />
          </label>
        </div>

        <h3 className="mb-3 mt-6 text-[12px] font-bold uppercase tracking-wide text-[var(--color-sc-muted)]">Workspace role</h3>
        <div className="flex flex-wrap gap-6 text-sm">
          {ROLE_KEYS.map((r) => (
            <label key={r} className="flex items-center gap-2 capitalize">
              <input
                type="checkbox"
                checked={form.group_list.includes(r)}
                onChange={(e) => {
                  const next = new Set(form.group_list);
                  if (e.target.checked) next.add(r);
                  else next.delete(r);
                  setF({ group_list: [...next] });
                }}
              />
              {r}
            </label>
          ))}
        </div>
        {extraRoles.length ? (
          <div className="mt-4">
            <h3 className="mb-2 text-[12px] font-bold uppercase tracking-wide text-[var(--color-sc-muted)]">Additional groups</h3>
            <div className="flex flex-wrap gap-4 text-sm">
              {extraRoles.map((r) => (
                <label key={r.group_uuid} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={form.group_list.includes(r.group_name.toLowerCase())}
                    onChange={(e) => {
                      const next = new Set(form.group_list);
                      const n = r.group_name.toLowerCase();
                      if (e.target.checked) next.add(n);
                      else next.delete(n);
                      setF({ group_list: [...next] });
                    }}
                  />
                  {r.group_name}
                </label>
              ))}
            </div>
          </div>
        ) : null}

        <button
          type="button"
          className="sc-btn mt-6"
          disabled={!!busy}
          onClick={() => {
            if (!form.username.trim() || !form.password) {
              setMsg('Username and password are required');
              return;
            }
            if (form.password.length < PASS_MIN) {
              setMsg(`Password must be at least ${PASS_MIN} characters (FusionPBX default)`);
              return;
            }
            if (form.password !== form.password2) {
              setMsg('Password and confirm password do not match');
              return;
            }
            if (form.sip_password && form.sip_password !== form.sip_password2) {
              setMsg('SIP password and confirm do not match');
              return;
            }
            if (!form.extension.trim()) {
              setMsg('Type the extension number you want');
              return;
            }
            void run('new', async () => {
              const r = await save('user_save', {
                username: form.username,
                password: form.password,
                user_email: form.user_email,
                extension: form.extension,
                create_extension: form.create_extension,
                sip_password: form.sip_password,
                group_list: form.group_list,
                user_enabled: true,
              });
              const sip = r?.extension?.sip_password;
              setMsg(
                r?.extension?.created
                  ? `Created user and extension ${r.extension.extension}. SIP password: ${sip}`
                  : 'User saved',
              );
              setForm(emptyForm);
            });
          }}
        >
          Create user
        </button>
      </section>

      <div className="overflow-x-auto overflow-hidden rounded-[14px] border border-[var(--color-sc-line)] bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-[var(--color-sc-soft)] text-[11px] uppercase text-[var(--color-sc-muted)]">
            <tr>
              <th className="px-3 py-2">Username</th>
              <th className="px-3 py-2">Ext</th>
              <th className="px-3 py-2">Agent</th>
              <th className="px-3 py-2">Supervisor</th>
              <th className="px-3 py-2">Admin</th>
              <th className="px-3 py-2">Skills</th>
              <th className="px-3 py-2">Enabled</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {loading && rows.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-3 py-6 text-[var(--color-sc-muted)]">
                  Loading users…
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-3 py-6 text-[var(--color-sc-muted)]">
                  No users on this domain
                </td>
              </tr>
            ) : (
              rows.map((u) => {
                const g = groupsOf(u);
                const id = u.user_uuid || u.username || '';
                return (
                  <Fragment key={id}>
                  <tr className="border-t border-[var(--color-sc-line)]">
                    <td className="px-3 py-2.5 font-semibold">
                      {u.username}
                      {g.includes('superadmin') ? (
                        <span className="ml-2 sc-meta">superadmin</span>
                      ) : null}
                      {extraRoles.length ? (
                        <div className="mt-1 flex flex-wrap gap-2 font-medium">
                          {extraRoles.map((r) => {
                            const n = r.group_name.toLowerCase();
                            return (
                              <label key={r.group_uuid} className="sc-meta flex items-center gap-1">
                                <input
                                  type="checkbox"
                                  checked={g.includes(n)}
                                  disabled={busy === id}
                                  onChange={(e) => toggleRole(u, n, e.target.checked)}
                                />
                                {r.group_name}
                              </label>
                            );
                          })}
                        </div>
                      ) : null}
                    </td>
                    <td className="px-3 py-2.5">{u.extension || '—'}</td>
                    {ROLE_KEYS.map((r) => (
                      <td key={r} className="px-3 py-2.5">
                        <input
                          type="checkbox"
                          checked={g.includes(r)}
                          disabled={busy === id}
                          onChange={(e) => toggleRole(u, r, e.target.checked)}
                        />
                      </td>
                    ))}
                    <td className="px-3 py-2.5">
                      {(u.skills || []).length ? (u.skills || []).join(', ') : '—'}
                    </td>
                    <td className="px-3 py-2.5">
                      <button
                        type="button"
                        className="sc-b2"
                        disabled={busy === id}
                        onClick={() =>
                          void run(id, async () => {
                            await save('user_save', {
                              user_uuid: u.user_uuid,
                              username: u.username,
                              user_email: u.user_email,
                              user_enabled: !enabledOf(u),
                              group_list: g,
                              extension: u.extension || '',
                            });
                          })
                        }
                      >
                        {enabledOf(u) ? 'On' : 'Off'}
                      </button>
                    </td>
                    <td className="px-3 py-2.5">
                      <button
                        type="button"
                        className="sc-b2"
                        onClick={() => {
                          setEditId(id);
                          setEdit({
                            password: '',
                            password2: '',
                            extension: (u.extension || '').split(',')[0],
                            sip_password: '',
                            sip_password2: '',
                          });
                        }}
                      >
                        Edit
                      </button>
                    </td>
                  </tr>
                  {editId === id ? (
                    <tr className="border-t border-[var(--color-sc-line)] bg-[var(--color-sc-soft)]">
                      <td colSpan={8} className="px-3 py-4">
                        <p className="mb-3 text-sm font-bold">Edit {u.username}</p>
                        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                          <label className="flex flex-col gap-1 text-[12px] font-bold">
                            New login password
                            <input className="sc-input font-medium" type="password" autoComplete="new-password" value={edit.password} onChange={(e) => setEdit({ ...edit, password: e.target.value })} />
                          </label>
                          <label className="flex flex-col gap-1 text-[12px] font-bold">
                            Confirm login password
                            <input className="sc-input font-medium" type="password" autoComplete="new-password" value={edit.password2} onChange={(e) => setEdit({ ...edit, password2: e.target.value })} />
                          </label>
                          <label className="flex flex-col gap-1 text-[12px] font-bold">
                            Extension
                            <input className="sc-input font-medium" value={edit.extension} onChange={(e) => setEdit({ ...edit, extension: e.target.value.replace(/[^\d]/g, '').slice(0, 8) })} />
                          </label>
                          <label className="flex flex-col gap-1 text-[12px] font-bold">
                            New SIP password
                            <input className="sc-input font-medium" type="password" autoComplete="new-password" placeholder="Blank = keep current" value={edit.sip_password} onChange={(e) => setEdit({ ...edit, sip_password: e.target.value })} />
                          </label>
                          <label className="flex flex-col gap-1 text-[12px] font-bold">
                            Confirm SIP password
                            <input className="sc-input font-medium" type="password" autoComplete="new-password" value={edit.sip_password2} onChange={(e) => setEdit({ ...edit, sip_password2: e.target.value })} />
                          </label>
                        </div>
                        <div className="mt-3 flex gap-2">
                          <button
                            type="button"
                            className="sc-btn"
                            disabled={busy === id}
                            onClick={() => {
                              if (edit.password && edit.password.length < PASS_MIN) {
                                setMsg(`Login password must be at least ${PASS_MIN} characters`);
                                return;
                              }
                              if (edit.password !== edit.password2) {
                                setMsg('Login passwords do not match');
                                return;
                              }
                              if (edit.sip_password && edit.sip_password !== edit.sip_password2) {
                                setMsg('SIP passwords do not match');
                                return;
                              }
                              void run(id, async () => {
                                const r = await save('user_save', {
                                  user_uuid: u.user_uuid,
                                  username: u.username,
                                  user_email: u.user_email,
                                  user_enabled: enabledOf(u),
                                  group_list: g,
                                  password: edit.password,
                                  extension: edit.extension,
                                  create_extension: true,
                                  sip_password: edit.sip_password,
                                });
                                setMsg(
                                  r?.extension?.sip_updated
                                    ? `Updated ${u.username}. New SIP password saved for ${edit.extension}.`
                                    : `Updated ${u.username}`,
                                );
                                setEditId('');
                              });
                            }}
                          >
                            Save changes
                          </button>
                          <button type="button" className="sc-b2" onClick={() => setEditId('')}>
                            Cancel
                          </button>
                          <button
                            type="button"
                            className="sc-b2"
                            disabled={busy === id}
                            onClick={() => {
                              if (!window.confirm(`Delete user ${u.username}? SIP extension is kept.`)) return;
                              void run(id, async () => {
                                await save('studio_delete', { kind: 'user', id: u.user_uuid });
                                setMsg(`Deleted ${u.username}`);
                                setEditId('');
                              });
                            }}
                          >
                            Delete user
                          </button>
                        </div>
                      </td>
                    </tr>
                  ) : null}
                  </Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>
      <p className="sc-meta">
        SkyConnect menus follow Agent / Supervisor / Admin. Extra roles are built under Users → Roles, then ticked on a person here.
      </p>
    </StudioPage>
  );
}
