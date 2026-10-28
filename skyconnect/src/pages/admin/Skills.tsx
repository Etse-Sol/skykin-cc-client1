import { useMemo, useState } from 'react';
import StudioPage from './StudioPage';
import { useStudio, type StudioUser } from './useStudio';

type Skill = { skill_key: string; label: string; kind?: string };

function skillsOf(u: StudioUser): string[] {
  return (u.skills || []).map((s) => s.toLowerCase());
}

export default function AdminSkills() {
  const { data, err, loading, save } = useStudio();
  const catalog: Skill[] = data?.skills?.length
    ? data.skills
    : [
        { skill_key: 'amharic', label: 'Amharic', kind: 'language' },
        { skill_key: 'english', label: 'English', kind: 'language' },
        { skill_key: 'oromo', label: 'Afaan Oromo', kind: 'language' },
        { skill_key: 'sim', label: 'SIM / identity', kind: 'product' },
        { skill_key: 'telebirr', label: 'telebirr', kind: 'product' },
        { skill_key: 'billing', label: 'Billing', kind: 'product' },
        { skill_key: 'general', label: 'General', kind: 'product' },
      ];
  const agents = useMemo(
    () => (data?.users || []).filter((u) => u.user_uuid && u.extension),
    [data?.users],
  );
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState('');

  const toggle = (u: StudioUser, key: string, on: boolean) => {
    const id = u.user_uuid || '';
    const next = new Set(skillsOf(u));
    if (on) next.add(key);
    else next.delete(key);
    setBusy(id);
    setMsg('');
    void save('skill_save', { user_uuid: id, skills: [...next] })
      .then(() => setMsg(`Saved skills for ${u.username}. Matching queues now ring this agent.`))
      .catch((e) => setMsg(e instanceof Error ? e.message : 'Save failed'))
      .finally(() => setBusy(''));
  };

  const languages = catalog.filter((s) => s.kind === 'language');
  const products = catalog.filter((s) => s.kind !== 'language');

  return (
    <StudioPage
      title="Agent skills"
      path="/admin/skills"
      blurb="Tick languages and products on each agent. Queues that require a skill only ring agents who have it."
    >
      {err ? <p className="text-sm text-[var(--color-sc-warn)]">{err}</p> : null}
      {msg ? <p className="text-sm font-bold">{msg}</p> : null}
      <p className="sc-meta mb-3">
        Then open Queues and set <strong>Required skill</strong> (Amharic, English, SIM…). Callers in that queue are served only by matching agents.
      </p>
      <div className="overflow-x-auto overflow-hidden rounded-[14px] border border-[var(--color-sc-line)] bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-[var(--color-sc-soft)] text-[11px] uppercase text-[var(--color-sc-muted)]">
            <tr>
              <th className="px-3 py-2">Agent</th>
              <th className="px-3 py-2">Ext</th>
              {languages.map((s) => (
                <th key={s.skill_key} className="px-3 py-2">
                  {s.label}
                </th>
              ))}
              {products.map((s) => (
                <th key={s.skill_key} className="px-3 py-2">
                  {s.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && agents.length === 0 ? (
              <tr>
                <td colSpan={3 + catalog.length} className="px-3 py-6 text-[var(--color-sc-muted)]">
                  Loading agents…
                </td>
              </tr>
            ) : agents.length === 0 ? (
              <tr>
                <td colSpan={3 + catalog.length} className="px-3 py-6 text-[var(--color-sc-muted)]">
                  No agents with a SIP extension. Create accounts first.
                </td>
              </tr>
            ) : (
              agents.map((u) => {
                const have = skillsOf(u);
                const id = u.user_uuid || '';
                return (
                  <tr key={id} className="border-t border-[var(--color-sc-line)]">
                    <td className="px-3 py-2.5 font-semibold">{u.username}</td>
                    <td className="px-3 py-2.5">{u.extension}</td>
                    {[...languages, ...products].map((s) => (
                      <td key={s.skill_key} className="px-3 py-2.5">
                        <input
                          type="checkbox"
                          checked={have.includes(s.skill_key)}
                          disabled={busy === id}
                          onChange={(e) => toggle(u, s.skill_key, e.target.checked)}
                        />
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </StudioPage>
  );
}
