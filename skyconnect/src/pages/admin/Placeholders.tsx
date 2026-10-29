import { useEffect, useState, type ReactNode } from 'react';
import StudioPage from './StudioPage';
import Knowledge from '../agent/Knowledge';
import { useStudio } from './useStudio';
import { fetchAgentSession } from '../../services/session';
import { listKnowledge, type KnowledgeArticle } from '../../services/crm';
import { fetchAiHealth, opsGet, opsPost, opsUpload } from '../../services/ops';

type IvrBranchDraft = { digit: string; param: string; submenu: string };

function blankBranch(digit = ''): IvrBranchDraft {
  return { digit, param: '', submenu: '' };
}

function destExtFromParam(param: string): string {
  const m = String(param || '').match(/transfer\s+(\d+)/i);
  return m ? m[1] : '';
}

export function AdminIvr() {
  const { data, err, save } = useStudio();
  const menus = data?.ivr || [];
  const opts = data?.ivr_options || [];
  const [msg, setMsg] = useState('');
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [add, setAdd] = useState({ menu: '', digits: '', param: '', submenu: '' });
  const [create, setCreate] = useState({ name: '', extension: '', greet: '' });
  const [branches, setBranches] = useState<IvrBranchDraft[]>([blankBranch('1'), blankBranch('2')]);
  const destParam = (_kind: string, ext: string) => `transfer ${ext.replace(/\D/g, '')} XML \${domain_name}`;
  const run = async (fn: () => Promise<void>) => {
    setMsg('');
    try {
      await fn();
      setMsg('Saved to FusionPBX. New calls pick up the change after the next XML cache refresh.');
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Save failed');
    }
  };
  const destSelect = (value: string, onPick: (param: string) => void) => (
    <select
      className="sc-input"
      value={value}
      onChange={(e) => onPick(e.target.value)}
    >
      <option value="">Destination…</option>
      {(data?.queues || []).map((q) => (
        <option key={q.call_center_queue_uuid} value={destParam('queue', String(q.queue_extension || ''))}>
          Queue {q.queue_name} ({q.queue_extension})
        </option>
      ))}
      {menus.map((m) => (
        <option key={m.ivr_menu_uuid} value={destParam('ivr', String(m.ivr_menu_extension || ''))}>
          IVR {m.ivr_menu_name} ({m.ivr_menu_extension})
        </option>
      ))}
      {(data?.flows || []).map((f: { call_flow_uuid?: string; call_flow_name?: string; call_flow_extension?: string }) => (
        <option key={f.call_flow_uuid} value={destParam('flow', String(f.call_flow_extension || ''))}>
          Flow {f.call_flow_name} ({f.call_flow_extension})
        </option>
      ))}
    </select>
  );
  const menuByExt: Record<string, any> = {};
  for (const m of menus) menuByExt[String(m.ivr_menu_extension || '')] = m;
  const queueByExt: Record<string, string> = {};
  for (const q of data?.queues || []) queueByExt[String(q.queue_extension || '')] = String(q.queue_name || q.queue_extension);
  const flowByExt: Record<string, string> = {};
  for (const f of data?.flows || []) flowByExt[String(f.call_flow_extension || '')] = String(f.call_flow_name || f.call_flow_extension);
  const childExts = new Set(
    opts.map((o) => destExtFromParam(o.param)).filter((e) => e && menuByExt[e]),
  );
  const roots = menus.filter((m) => !childExts.has(String(m.ivr_menu_extension || '')));
  const destLabel = (param: string) => {
    const ext = destExtFromParam(param);
    if (ext && menuByExt[ext]) return { kind: 'ivr' as const, title: menuByExt[ext].ivr_menu_name, ext };
    if (ext && queueByExt[ext]) return { kind: 'queue' as const, title: queueByExt[ext], ext };
    if (ext && flowByExt[ext]) return { kind: 'flow' as const, title: flowByExt[ext], ext };
    return { kind: 'other' as const, title: param || '—', ext };
  };
  const renderNode = (m: any, seen: Set<string>): ReactNode => {
    if (!m || seen.has(m.ivr_menu_uuid)) return null;
    const next = new Set(seen);
    next.add(m.ivr_menu_uuid);
    const digits = opts.filter((o) => o.ivr_menu_uuid === m.ivr_menu_uuid);
    return (
      <div key={m.ivr_menu_uuid} className="sc-ivr-tree">
        <div className="sc-ivr-node">
          {m.ivr_menu_name}
          <div className="mt-1 text-[11px] font-semibold text-[var(--color-sc-muted)]">ext {m.ivr_menu_extension}</div>
        </div>
        {digits.length ? (
          <>
            <div className="sc-ivr-stem" />
            <div className="sc-ivr-kids">
              {digits.map((d) => {
                const dest = destLabel(d.param);
                const child = dest.kind === 'ivr' ? menuByExt[dest.ext] : null;
                return (
                  <div key={d.ivr_menu_option_uuid || d.digits} className="sc-ivr-arm">
                    <div className="sc-ivr-stem" />
                    <span className="sc-ivr-digit">Press {d.digits}</span>
                    <div className="sc-ivr-stem" />
                    {child ? (
                      renderNode(child, next)
                    ) : (
                      <div className="sc-ivr-leaf">
                        {dest.kind === 'queue' ? 'Queue' : dest.kind === 'flow' ? 'Flow' : 'Go to'} {dest.title}
                        {dest.ext ? <div className="mt-1 text-[11px] font-semibold text-[var(--color-sc-muted)]">ext {dest.ext}</div> : null}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        ) : null}
      </div>
    );
  };
  return (
    <StudioPage title="Visual IVR" path="/admin/ivr" blurb="Create a menu, then branch each digit to a queue, flow, or another IVR">
      {err ? <p className="text-sm text-[var(--color-sc-warn)]">{err}</p> : null}
      {msg ? <p className="text-sm font-bold">{msg}</p> : null}
      <section className="sc-card">
        <h2 className="mb-3 text-[16px] font-bold">Add IVR menu</h2>
        <div className="grid gap-2 sm:grid-cols-3">
          <input
            className="sc-input"
            placeholder="Name (Main menu)"
            value={create.name}
            onChange={(e) => setCreate({ ...create, name: e.target.value })}
          />
          <input
            className="sc-input"
            placeholder={data?.next_service_extension ? `Extension (${data.next_service_extension})` : 'Extension (9000)'}
            value={create.extension}
            onChange={(e) => setCreate({ ...create, extension: e.target.value.replace(/\D/g, '').slice(0, 8) })}
          />
          <select className="sc-input" value={create.greet} onChange={(e) => setCreate({ ...create, greet: e.target.value })}>
            <option value="">Greeting (optional)</option>
            {(data?.recordings || []).map((r) => (
              <option key={r.recording_uuid || r.recording_filename} value={r.recording_filename}>
                {r.recording_name || r.recording_filename}
              </option>
            ))}
          </select>
        </div>
        <h3 className="mt-4 text-sm font-bold">Branches (digits)</h3>
        <p className="sc-meta mb-2">Each digit goes to a queue, existing IVR, flow, or a new submenu.</p>
        <ul className="space-y-2">
          {branches.map((b, i) => (
            <li key={i} className="grid gap-2 sm:grid-cols-4">
              <input
                className="sc-input"
                placeholder="Digit"
                value={b.digit}
                onChange={(e) =>
                  setBranches((rows) => rows.map((row, n) => (n === i ? { ...row, digit: e.target.value.replace(/\D/g, '').slice(0, 4) } : row)))
                }
              />
              {destSelect(b.param, (param) =>
                setBranches((rows) => rows.map((row, n) => (n === i ? { ...row, param, submenu: '' } : row))),
              )}
              <input
                className="sc-input"
                placeholder="Or new submenu name"
                value={b.submenu}
                onChange={(e) =>
                  setBranches((rows) => rows.map((row, n) => (n === i ? { ...row, submenu: e.target.value, param: '' } : row)))
                }
              />
              <button
                type="button"
                className="sc-b2"
                onClick={() => setBranches((rows) => rows.filter((_, n) => n !== i))}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
        <button type="button" className="sc-b2 mt-2" onClick={() => setBranches((rows) => [...rows, blankBranch(String(rows.length + 1))])}>
          Add branch
        </button>
        <button
          type="button"
          className="sc-btn mt-3 ml-2"
          onClick={() =>
            void run(async () => {
              await save('ivr_save', {
                ivr_menu_name: create.name,
                ivr_menu_extension: create.extension || data?.next_service_extension || '9000',
                ivr_menu_greet_long: create.greet,
                ivr_menu_enabled: true,
                branches: branches
                  .filter((b) => b.digit && (b.param || b.submenu.trim()))
                  .map((b) => ({
                    digits: b.digit,
                    param: b.param,
                    new_submenu: b.submenu.trim(),
                  })),
              });
              setCreate({ name: '', extension: '', greet: '' });
              setBranches([blankBranch('1'), blankBranch('2')]);
            })
          }
        >
          Create menu and branches
        </button>
      </section>
      <section className="sc-card overflow-x-auto">
        <h2 className="mb-3 text-[16px] font-bold">Menu tree</h2>
        <div className="flex min-w-max gap-6">
          {roots.map((m) => renderNode(m, new Set()))}
          {menus.length === 0 ? <p className="sc-meta">No IVR menus on this domain</p> : null}
        </div>
      </section>
      <div className="grid gap-3 lg:grid-cols-2">
        {menus.map((m) => {
          const digits = opts.filter((o) => o.ivr_menu_uuid === m.ivr_menu_uuid);
          const on = String(m.ivr_menu_enabled).toLowerCase() === 'true';
          return (
            <div key={m.ivr_menu_uuid} className="sc-card">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-bold">{m.ivr_menu_name}</p>
                  <p className="sc-meta mt-1">Ext {m.ivr_menu_extension}</p>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    className="sc-b2"
                    onClick={() =>
                      void run(() =>
                        save('ivr_save', {
                          ivr_menu_uuid: m.ivr_menu_uuid,
                          ivr_menu_name: m.ivr_menu_name,
                          ivr_menu_enabled: !on,
                          ivr_menu_description: m.ivr_menu_description || '',
                        }),
                      )
                    }
                  >
                    {on ? 'Enabled' : 'Disabled'}
                  </button>
                  <button
                    type="button"
                    className="sc-b2"
                    onClick={() => {
                      if (!window.confirm(`Delete IVR ${m.ivr_menu_name}?`)) return;
                      void run(() => save('studio_delete', { kind: 'ivr', id: m.ivr_menu_uuid }));
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>
              <ul className="mt-3 space-y-2 text-sm">
                {digits.map((d) => {
                  const key = d.ivr_menu_option_uuid || d.digits + d.param;
                  const val = draft[key] ?? d.param;
                  return (
                    <li key={key} className="flex flex-col gap-1">
                      <span>
                        <strong>Press {d.digits}</strong> · {d.action}
                      </span>
                      <div className="flex gap-2">
                        <input
                          className="sc-input flex-1"
                          value={val}
                          onChange={(e) => setDraft({ ...draft, [key]: e.target.value })}
                        />
                        <button
                          type="button"
                          className="sc-b2"
                          onClick={() =>
                            void run(() =>
                              save('ivr_option_save', {
                                ivr_menu_option_uuid: d.ivr_menu_option_uuid,
                                ivr_menu_uuid: m.ivr_menu_uuid,
                                digits: d.digits,
                                action: d.action,
                                param: val,
                                description: d.description || '',
                              }),
                            )
                          }
                        >
                          Save
                        </button>
                        <button
                          type="button"
                          className="sc-b2"
                          onClick={() => {
                            if (!window.confirm(`Delete digit ${d.digits}?`)) return;
                            void run(() => save('studio_delete', { kind: 'option', id: d.ivr_menu_option_uuid }));
                          }}
                        >
                          Delete
                        </button>
                      </div>
                    </li>
                  );
                })}
                {digits.length === 0 ? <li className="sc-meta">No branches yet</li> : null}
              </ul>
              {add.menu === m.ivr_menu_uuid ? (
                <div className="mt-3 grid gap-2">
                  <input
                    className="sc-input"
                    placeholder="Digit"
                    value={add.digits}
                    onChange={(e) => setAdd({ ...add, digits: e.target.value.replace(/\D/g, '').slice(0, 4) })}
                  />
                  {destSelect(add.param, (param) => setAdd({ ...add, param, submenu: '' }))}
                  <input
                    className="sc-input"
                    placeholder="Or branch to a new submenu"
                    value={add.submenu}
                    onChange={(e) => setAdd({ ...add, submenu: e.target.value, param: '' })}
                  />
                  <button
                    type="button"
                    className="sc-btn"
                    onClick={() =>
                      void run(async () => {
                        await save('ivr_option_save', {
                          ivr_menu_uuid: m.ivr_menu_uuid,
                          digits: add.digits,
                          action: 'menu-exec-app',
                          param: add.param,
                          new_submenu: add.submenu.trim(),
                        });
                        setAdd({ menu: '', digits: '', param: '', submenu: '' });
                      })
                    }
                  >
                    Save branch
                  </button>
                </div>
              ) : (
                <button type="button" className="sc-b2 mt-3" onClick={() => setAdd({ menu: m.ivr_menu_uuid, digits: '', param: '', submenu: '' })}>
                  Branch out
                </button>
              )}
            </div>
          );
        })}
        {menus.length === 0 ? <p className="sc-meta">No IVR menus on this domain</p> : null}
      </div>
    </StudioPage>
  );
}

export function AdminChatbot() {
  const [q, setQ] = useState('');
  const [hits, setHits] = useState<KnowledgeArticle[]>([]);
  const [err, setErr] = useState('');
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const [intent, setIntent] = useState({ title: '', keywords: '', body: '' });
  const test = async (query?: string) => {
    const ask = (query ?? q).trim();
    setBusy(true);
    setErr('');
    try {
      const rows = await listKnowledge(ask);
      setHits(rows);
      if (rows.length === 0) {
        setErr(ask ? 'No matching article. Save an intent with those keywords, then Test again.' : 'No articles yet. Save an intent first.');
      }
    } catch (e) {
      setHits([]);
      setErr(e instanceof Error ? e.message : 'Search failed');
    } finally {
      setBusy(false);
    }
  };
  const chatUrl = `${window.location.origin}/app/agent_dashboard/skyconnect_omni.php?ui=chat`;
  const waUrl = `${window.location.origin}/app/agent_dashboard/skyconnect_omni.php?op=wa`;
  return (
    <StudioPage
      title="Chatbot studio"
      path="/admin/chatbot"
      blurb="Intents are Knowledge articles — author and test retrieval against the live KB"
    >
      <section className="sc-card">
        <h2 className="mb-2 text-[16px] font-bold">Live channels</h2>
        <p className="text-sm">
          Web widget: <a className="underline" href={chatUrl} target="_blank" rel="noreferrer">{chatUrl}</a>
        </p>
        <p className="sc-meta mt-2">
          WhatsApp Cloud webhook: {waUrl} — set SKYKIN_WA_VERIFY, SKYKIN_WA_TOKEN, SKYKIN_WA_PHONE_ID on the host.
        </p>
      </section>
      <section className="sc-card">
        <h2 className="mb-3 text-[16px] font-bold">Add intent</h2>
        <div className="grid gap-2">
          <input
            className="sc-input"
            placeholder="Intent title"
            value={intent.title}
            onChange={(e) => setIntent({ ...intent, title: e.target.value })}
          />
          <input
            className="sc-input"
            placeholder="Keywords (comma separated)"
            value={intent.keywords}
            onChange={(e) => setIntent({ ...intent, keywords: e.target.value })}
          />
          <textarea
            className="sc-input min-h-[90px]"
            placeholder="Reply body"
            value={intent.body}
            onChange={(e) => setIntent({ ...intent, body: e.target.value })}
          />
        </div>
        <button
          type="button"
          className="sc-btn mt-3"
          onClick={() =>
            void (async () => {
              setMsg('');
              try {
                await opsPost('knowledge_save', { ...intent, tag: 'Intent' });
                const title = intent.title;
                setIntent({ title: '', keywords: '', body: '' });
                setMsg('Intent saved to Knowledge');
                setQ(title);
                await test(title);
              } catch (e) {
                setMsg(e instanceof Error ? e.message : 'Save failed');
              }
            })()
          }
        >
          Save intent
        </button>
        {msg ? <p className="mt-2 text-sm font-bold">{msg}</p> : null}
      </section>
      <div className="flex gap-2">
        <input
          className="flex-1 rounded-lg border border-[var(--color-sc-line)] px-3 py-2 text-sm"
          placeholder="Customer question (e.g. I lost my SIM)"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              void test();
            }
          }}
        />
        <button type="button" className="sc-btn" disabled={busy} onClick={() => void test()}>
          {busy ? 'Testing…' : 'Test'}
        </button>
      </div>
      {err ? <p className="text-sm text-[var(--color-sc-warn)]">{err}</p> : null}
      {hits[0]?.body ? (
        <section className="sc-card">
          <p className="text-[11px] font-bold uppercase tracking-wide text-[var(--color-sc-muted)]">Suggested reply</p>
          <p className="mt-2 text-sm font-bold">{hits[0].title}</p>
          <p className="mt-2 whitespace-pre-wrap text-sm">{hits[0].body}</p>
        </section>
      ) : null}
      <ul className="sc-card space-y-2 text-sm">
        {hits.map((h) => (
          <li key={h.article_id}>
            <strong>{h.title}</strong>
            <span className="ml-2 sc-meta">{h.tag}</span>
            <p className="sc-meta">{h.excerpt || h.body}</p>
          </li>
        ))}
        {hits.length === 0 && !err ? <li className="sc-meta">Type a question and Test — try “SIM”, “telebirr”, or “Fayda”</li> : null}
      </ul>
    </StudioPage>
  );
}

const QUEUE_STRATEGIES = [
  'longest-idle-agent',
  'round-robin',
  'ring-all',
  'top-down',
  'agent-with-least-talk-time',
  'agent-with-fewest-calls',
  'sequentially-by-agent-order',
  'random',
];

export function AdminQueues() {
  const { data, err, save } = useStudio();
  const [msg, setMsg] = useState('');
  const [moh, setMoh] = useState<Record<string, string>>({});
  const [create, setCreate] = useState({ name: '', extension: '', strategy: 'longest-idle-agent', skill: '' });
  const run = async (fn: () => Promise<void>) => {
    setMsg('');
    try {
      await fn();
      setMsg('Queue saved');
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Save failed');
    }
  };
  return (
    <StudioPage
      title="Routing and queues"
      path="/admin/queues"
      blurb="Set a required skill so only matching agents ring. Or tick staff by hand when the queue has no skill."
    >
      {err ? <p className="text-sm text-[var(--color-sc-warn)]">{err}</p> : null}
      {msg ? <p className="text-sm font-bold">{msg}</p> : null}
      <section className="sc-card">
        <h2 className="mb-3 text-[16px] font-bold">Add queue</h2>
        <div className="grid gap-2 sm:grid-cols-3">
          <input
            className="sc-input"
            placeholder="Name (Support)"
            value={create.name}
            onChange={(e) => setCreate({ ...create, name: e.target.value })}
          />
          <input
            className="sc-input"
            placeholder={data?.next_service_extension ? `Extension (${data.next_service_extension})` : 'Extension (9010)'}
            value={create.extension}
            onChange={(e) => setCreate({ ...create, extension: e.target.value.replace(/\D/g, '').slice(0, 8) })}
          />
          <select
            className="sc-input"
            value={create.strategy}
            onChange={(e) => setCreate({ ...create, strategy: e.target.value })}
          >
            {QUEUE_STRATEGIES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <select
            className="sc-input sm:col-span-3"
            value={create.skill}
            onChange={(e) => setCreate({ ...create, skill: e.target.value })}
          >
            <option value="">No required skill (manual staff)</option>
            {(data?.skills || []).map((s) => (
              <option key={s.skill_key} value={s.skill_key}>
                Skill: {s.label}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          className="sc-btn mt-3"
          onClick={() =>
            void run(async () => {
              await save('queue_save', {
                queue_name: create.name,
                queue_extension: create.extension,
                queue_strategy: create.strategy,
                queue_moh_sound: 'local_stream://default',
                required_skill: create.skill,
              });
              setCreate({ name: '', extension: '', strategy: 'longest-idle-agent', skill: '' });
            })
          }
        >
          Create queue
        </button>
      </section>
      <div className="overflow-x-auto overflow-hidden rounded-[14px] border border-[var(--color-sc-line)] bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-[var(--color-sc-soft)] text-[11px] uppercase text-[var(--color-sc-muted)]">
            <tr>
              <th className="px-3 py-2">Queue</th>
              <th className="px-3 py-2">Ext</th>
              <th className="px-3 py-2">Strategy</th>
              <th className="px-3 py-2">MOH</th>
              <th className="px-3 py-2">Required skill</th>
              <th className="px-3 py-2">Staff</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {(data?.queues || []).map((q) => {
              const id = q.call_center_queue_uuid || q.queue_extension;
              return (
                <tr key={id} className="border-t border-[var(--color-sc-line)]">
                  <td className="px-3 py-2.5 font-semibold">{q.queue_name}</td>
                  <td className="px-3 py-2.5">{q.queue_extension}</td>
                  <td className="px-3 py-2.5">
                    <select
                      className="sc-input"
                      value={q.queue_strategy || ''}
                      onChange={(e) =>
                        void run(() =>
                          save('queue_save', {
                            call_center_queue_uuid: q.call_center_queue_uuid,
                            queue_name: q.queue_name,
                            queue_strategy: e.target.value,
                            queue_moh_sound: moh[id] ?? q.queue_moh_sound ?? '',
                          }),
                        )
                      }
                    >
                      {QUEUE_STRATEGIES.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-3 py-2.5">
                    <input
                      className="sc-input"
                      value={moh[id] ?? q.queue_moh_sound ?? ''}
                      onChange={(e) => setMoh({ ...moh, [id]: e.target.value })}
                    />
                  </td>
                  <td className="px-3 py-2.5 align-top">
                    <select
                      className="sc-input"
                      value={q.required_skill || ''}
                      onChange={(e) =>
                        void run(() =>
                          save('queue_save', {
                            call_center_queue_uuid: q.call_center_queue_uuid,
                            queue_name: q.queue_name,
                            queue_strategy: q.queue_strategy,
                            queue_moh_sound: moh[id] ?? q.queue_moh_sound ?? '',
                            required_skill: e.target.value,
                          }),
                        )
                      }
                    >
                      <option value="">None (manual)</option>
                      {(data?.skills || []).map((s) => (
                        <option key={s.skill_key} value={s.skill_key}>
                          {s.label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-3 py-2.5 align-top">
                    <div className="flex max-h-36 flex-col gap-1 overflow-y-auto">
                      {(data?.users || [])
                        .filter((u) => u.user_uuid && u.extension)
                        .map((u) => {
                          const members: string[] = q.member_uuids || [];
                          const onStaff = members.includes(u.user_uuid as string);
                          return (
                            <label key={u.user_uuid} className="flex items-center gap-1 text-[12px] font-medium">
                              <input
                                type="checkbox"
                                checked={onStaff}
                                onChange={() => {
                                  const next = onStaff
                                    ? members.filter((x) => x !== u.user_uuid)
                                    : [...members, u.user_uuid as string];
                                  void run(() =>
                                    save('queue_agent_save', {
                                      call_center_queue_uuid: q.call_center_queue_uuid,
                                      user_uuids: next,
                                    }),
                                  );
                                }}
                              />
                              {u.username} ({u.extension})
                            </label>
                          );
                        })}
                      {(data?.users || []).filter((u) => u.extension).length === 0 ? (
                        <span className="sc-meta">Users need SIP extensions</span>
                      ) : null}
                    </div>
                  </td>
                  <td className="px-3 py-2.5">
                    <div className="flex flex-col gap-1">
                      <button
                        type="button"
                        className="sc-b2"
                        onClick={() =>
                          void run(() =>
                            save('queue_save', {
                              call_center_queue_uuid: q.call_center_queue_uuid,
                              queue_name: q.queue_name,
                              queue_strategy: q.queue_strategy,
                              queue_moh_sound: moh[id] ?? q.queue_moh_sound ?? '',
                            }),
                          )
                        }
                      >
                        Save
                      </button>
                      <button
                        type="button"
                        className="sc-b2"
                        onClick={() => {
                          if (!window.confirm(`Delete queue ${q.queue_name}?`)) return;
                          void run(() => save('studio_delete', { kind: 'queue', id: q.call_center_queue_uuid }));
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
            {(data?.queues || []).length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-[var(--color-sc-muted)]">
                  No queues
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </StudioPage>
  );
}

export function AdminAnnouncements() {
  const { data, err, reload, save } = useStudio();
  const domain = data?.domain || '';
  const [msg, setMsg] = useState('');
  const [name, setName] = useState('');
  const [file, setFile] = useState<File | null>(null);
  return (
    <StudioPage
      title="Announcement and music-on-hold"
      path="/admin/announcements"
      blurb="Upload and play FusionPBX recordings used as prompts and hold music"
    >
      {err ? <p className="text-sm text-[var(--color-sc-warn)]">{err}</p> : null}
      {msg ? <p className="text-sm font-bold">{msg}</p> : null}
      <section className="sc-card">
        <h2 className="mb-3 text-[16px] font-bold">Add announcement</h2>
        <div className="grid gap-2 sm:grid-cols-2">
          <input className="sc-input" placeholder="Name (welcome)" value={name} onChange={(e) => setName(e.target.value)} />
          <input
            className="sc-input"
            type="file"
            accept="audio/wav,audio/mpeg,audio/ogg,.wav,.mp3,.ogg"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
        </div>
        <button
          type="button"
          className="sc-btn mt-3"
          onClick={() => {
            if (!file) {
              setMsg('Choose a wav/mp3 file');
              return;
            }
            void (async () => {
              setMsg('');
              try {
                const s = await fetchAgentSession();
                const fd = new FormData();
                fd.append('file', file);
                fd.append('recording_name', name || file.name);
                await opsUpload('recording_save', fd, { domain: s.domain });
                await reload();
                setName('');
                setFile(null);
                setMsg('Uploaded');
              } catch (e) {
                setMsg(e instanceof Error ? e.message : 'Upload failed');
              }
            })();
          }}
        >
          Upload
        </button>
      </section>
      <ul className="space-y-2">
        {(data?.recordings || []).map((r) => (
          <li key={r.recording_uuid || r.recording_filename} className="sc-card text-sm">
            <p className="font-bold">{r.recording_name || r.recording_filename}</p>
            <p className="sc-meta">{r.recording_filename}</p>
            {r.recording_description ? <p className="mt-1">{r.recording_description}</p> : null}
            {r.recording_filename ? (
              <audio
                className="mt-2 w-full"
                controls
                src={`/app/agent_dashboard/play_recording.php?f=${encodeURIComponent(r.recording_filename)}&d=${encodeURIComponent(domain)}`}
              />
            ) : null}
            {r.recording_uuid ? (
              <button
                type="button"
                className="sc-b2 mt-2"
                onClick={() => {
                  if (!window.confirm(`Delete ${r.recording_name || r.recording_filename}?`)) return;
                  void (async () => {
                    setMsg('');
                    try {
                      await save('studio_delete', { kind: 'recording', id: r.recording_uuid });
                      setMsg('Deleted');
                    } catch (e) {
                      setMsg(e instanceof Error ? e.message : 'Delete failed');
                    }
                  })();
                }}
              >
                Delete
              </button>
            ) : null}
          </li>
        ))}
        {(data?.recordings || []).length === 0 ? <p className="sc-meta">No recordings in this domain</p> : null}
      </ul>
    </StudioPage>
  );
}

export function AdminVerification() {
  const [rows, setRows] = useState<any[]>([]);
  const [stats, setStats] = useState({ total: 0, verified: 0 });
  const [err, setErr] = useState('');
  const [msg, setMsg] = useState('');
  const [add, setAdd] = useState({ full_name: '', phone: '', language: 'English', fayda_verified: true });
  const load = () =>
    fetchAgentSession()
      .then((s) => opsGet('verification', { domain: s.domain }))
      .then((d) => {
        setRows(d.contacts || []);
        setStats({ total: d.total || 0, verified: d.verified || 0 });
      });
  useEffect(() => {
    load().catch((e) => setErr(e instanceof Error ? e.message : 'Failed'));
  }, []);
  const toggle = async (c: any) => {
    setMsg('');
    try {
      const on = !(c.fayda_verified === true || c.fayda_verified === 1 || c.fayda_verified === '1');
      await opsPost('verification_set', { phone: c.phone, fayda_verified: on });
      await load();
      setMsg('Updated');
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Save failed');
    }
  };
  return (
    <StudioPage
      title="Verification policy"
      path="/admin/verification"
      blurb="Mark CRM contacts as Fayda verified — this flag is what agents see on the customer card"
    >
      {err ? <p className="text-sm text-[var(--color-sc-warn)]">{err}</p> : null}
      {msg ? <p className="text-sm font-bold">{msg}</p> : null}
      <p className="text-sm">
        Verified {stats.verified} / {stats.total} contacts
      </p>
      <section className="sc-card">
        <h2 className="mb-3 text-[16px] font-bold">Add contact</h2>
        <div className="grid gap-2 sm:grid-cols-4">
          <input
            className="sc-input"
            placeholder="Name"
            value={add.full_name}
            onChange={(e) => setAdd({ ...add, full_name: e.target.value })}
          />
          <input
            className="sc-input"
            placeholder="Phone"
            value={add.phone}
            onChange={(e) => setAdd({ ...add, phone: e.target.value })}
          />
          <input
            className="sc-input"
            placeholder="Language"
            value={add.language}
            onChange={(e) => setAdd({ ...add, language: e.target.value })}
          />
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={add.fayda_verified}
              onChange={(e) => setAdd({ ...add, fayda_verified: e.target.checked })}
            />
            Fayda verified
          </label>
        </div>
        <button
          type="button"
          className="sc-btn mt-3"
          onClick={() =>
            void (async () => {
              setMsg('');
              try {
                const r = await opsPost('verification_set', add);
                if (r?.contacts) {
                  setRows(r.contacts);
                  setStats({ total: r.total || r.contacts.length, verified: r.verified || 0 });
                } else {
                  await load();
                }
                setAdd({ full_name: '', phone: '', language: 'English', fayda_verified: true });
                setMsg('Contact saved');
              } catch (e) {
                setMsg(e instanceof Error ? e.message : 'Save failed');
              }
            })()
          }
        >
          Add contact
        </button>
      </section>
      <div className="overflow-hidden rounded-[14px] border border-[var(--color-sc-line)] bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-[var(--color-sc-soft)] text-[11px] uppercase text-[var(--color-sc-muted)]">
            <tr>
              <th className="px-3 py-2">Name</th>
              <th className="px-3 py-2">Phone</th>
              <th className="px-3 py-2">Fayda</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.phone} className="border-t border-[var(--color-sc-line)]">
                <td className="px-3 py-2">{c.full_name}</td>
                <td className="px-3 py-2">{c.phone}</td>
                <td className="px-3 py-2">
                  <button type="button" className="sc-b2" onClick={() => void toggle(c)}>
                    {c.fayda_verified === true || c.fayda_verified === 1 || c.fayda_verified === '1' ? 'Yes' : 'No'}
                  </button>
                </td>
              </tr>
            ))}
            {rows.length === 0 ? (
              <tr>
                <td colSpan={3} className="px-3 py-6 text-[var(--color-sc-muted)]">
                  No CRM contacts yet
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </StudioPage>
  );
}

export function AdminKnowledge() {
  return (
    <StudioPage title="Knowledge" path="/admin/knowledge" blurb="Author and search SkyKnow articles">
      <Knowledge canEdit />
    </StudioPage>
  );
}

export function AdminSettings() {
  const { data, err, save } = useStudio();
  const [mins, setMins] = useState<number>(0);
  const [hours, setHours] = useState({
    enabled: false,
    tz: 'Africa/Addis_Ababa',
    open: '0800',
    close: '1900',
    days: '1,2,3,4,5,6,7',
  });
  useEffect(() => {
    if (data?.settings?.session_idle_minutes != null) {
      setMins(Number(data.settings.session_idle_minutes));
    }
    if (data?.settings?.biz_hours) {
      setHours({
        enabled: !!data.settings.biz_hours.enabled,
        tz: data.settings.biz_hours.tz || 'Africa/Addis_Ababa',
        open: data.settings.biz_hours.open || '0800',
        close: data.settings.biz_hours.close || '1900',
        days: data.settings.biz_hours.days || '1,2,3,4,5,6,7',
      });
    }
  }, [data]);
  const [msg, setMsg] = useState('');
  const [ai, setAi] = useState<{ ok?: boolean; error?: string; base?: string } | null>(null);
  useEffect(() => {
    fetchAiHealth()
      .then(setAi)
      .catch((e) => setAi({ ok: false, error: e instanceof Error ? e.message : 'AI check failed' }));
  }, []);
  const persist = async () => {
    setMsg('');
    try {
      await save('settings_save', { session_idle_minutes: mins, biz_hours: hours });
      setMsg('Settings saved');
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Save failed');
    }
  };
  return (
    <StudioPage title="Settings" path="/admin/settings" blurb="Idle logout, after-hours, and data sync">
      {err ? <p className="text-sm text-[var(--color-sc-warn)]">{err}</p> : null}
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="sc-card">
          <h2 className="mb-3 text-[16px] font-bold">Session</h2>
          <label className="text-sm">Idle logout (minutes, 0 = off)</label>
          <input
            type="number"
            className="mt-2 w-full rounded-lg border border-[var(--color-sc-line)] px-3 py-2"
            value={mins}
            onChange={(e) => setMins(Number(e.target.value))}
          />
          <button type="button" className="sc-btn mt-3" onClick={() => void persist()}>
            Save
          </button>
          {msg ? <p className="mt-2 text-sm font-bold">{msg}</p> : null}
        </section>
        <section className="sc-card">
          <h2 className="mb-3 text-[16px] font-bold">SkyKin AI</h2>
          <p className="text-sm">
            {ai == null ? 'Checking…' : ai.ok ? `Reachable · ${ai.base || 'ok'}` : ai.error || 'Not reachable'}
          </p>
          <p className="sc-meta mt-2">
            Captions and evaluation need the AI service on port 8100 of this host (listen on 0.0.0.0, not only localhost).
          </p>
          <button type="button" className="sc-btn mt-3" onClick={() => void fetchAiHealth().then(setAi)}>
            Recheck
          </button>
        </section>
        <section className="sc-card">
          <h2 className="mb-3 text-[16px] font-bold">Tenant</h2>
          <p className="text-sm">Domain {data?.domain || '—'}</p>
          <p className="sc-meta mt-2">SkyConnect studio — not FusionPBX superadmin.</p>
          <button
            type="button"
            className="sc-btn mt-3"
            onClick={() =>
              void save('reloadxml', {})
                .then(() => setMsg('Data synced'))
                .catch((e) => setMsg(e instanceof Error ? e.message : 'Sync failed'))
            }
          >
            Sync data
          </button>
        </section>
        <section className="sc-card lg:col-span-2">
          <h2 className="mb-3 text-[16px] font-bold">After hours</h2>
          <p className="sc-meta mb-3">
            When enabled, inbound Lua plays the closed prompt outside these hours. Off by default except ahununu.
          </p>
          <label className="mb-3 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={hours.enabled}
              onChange={(e) => setHours({ ...hours, enabled: e.target.checked })}
            />
            Enable after-hours drop for this domain
          </label>
          <div className="grid gap-2 sm:grid-cols-4">
            <input className="sc-input" placeholder="Timezone" value={hours.tz} onChange={(e) => setHours({ ...hours, tz: e.target.value })} />
            <input className="sc-input" placeholder="Open (0800)" value={hours.open} onChange={(e) => setHours({ ...hours, open: e.target.value.replace(/\D/g, '').slice(0, 4) })} />
            <input className="sc-input" placeholder="Close (1900)" value={hours.close} onChange={(e) => setHours({ ...hours, close: e.target.value.replace(/\D/g, '').slice(0, 4) })} />
            <input className="sc-input" placeholder="Days 1-7" value={hours.days} onChange={(e) => setHours({ ...hours, days: e.target.value })} />
          </div>
          <button type="button" className="sc-btn mt-3" onClick={() => void persist()}>
            Save hours
          </button>
        </section>
      </div>
    </StudioPage>
  );
}
