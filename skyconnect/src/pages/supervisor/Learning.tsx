import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import StatusPill from '../../components/StatusPill';
import { fetchAgentSession } from '../../services/session';
import { fetchQaAgentSummary, opsGet, opsPost, weekRange } from '../../services/ops';
import { fetchSupAgents, type SupAgent } from '../../services/supervisorApi';

type Skill = { label: string; pct: number; samples: number };
type Assignment = {
  assign_id?: number;
  course_id: number;
  title: string;
  skill?: string;
  source?: string;
  status?: string;
  last_pct?: number;
};
type Course = {
  course_id: number;
  title: string;
  skill_key: string;
  skill?: string;
  body: string;
  quiz_count?: number;
  quiz?: { q: string; choices: string[]; answer: number }[];
};
type TeamRow = { agent_ext: string; agent_name?: string; assigned?: number; passed?: number; best_pct?: number };

type QuizQ = { q: string; choices: string[]; answer: number };

function blankQuestion(): QuizQ {
  return { q: '', choices: ['', ''], answer: 0 };
}

export default function SupervisorLearning() {
  const [tab, setTab] = useState<'progress' | 'courses'>('progress');
  const [domain, setDomain] = useState('');
  const [qa, setQa] = useState<any[]>([]);
  const [floor, setFloor] = useState<SupAgent[]>([]);
  const [team, setTeam] = useState<TeamRow[]>([]);
  const [ext, setExt] = useState('');
  const [skills, setSkills] = useState<Skill[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [skillsMap, setSkillsMap] = useState<Record<string, string>>({});
  const [count, setCount] = useState(0);
  const [err, setErr] = useState('');
  const [msg, setMsg] = useState('');
  const [assignCourse, setAssignCourse] = useState('');
  const [form, setForm] = useState({
    title: '',
    skill_key: 'knowledge',
    body: '',
    quiz: [blankQuestion()],
  });
  const range = weekRange();

  const loadCatalog = useCallback(async (dom: string) => {
    const cat = await opsGet('learn_catalog', { domain: dom });
    setCourses(Array.isArray(cat.courses) ? cat.courses : []);
    setSkillsMap(cat.skills && typeof cat.skills === 'object' ? cat.skills : {});
  }, []);

  const loadTeam = useCallback(async (dom: string) => {
    const t = await opsGet('learn_team', { domain: dom });
    setTeam(Array.isArray(t.team) ? t.team : []);
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const s = await fetchAgentSession();
        setDomain(s.domain);
        const [list, ags] = await Promise.all([
          fetchQaAgentSummary(s.domain, range.from, range.to).catch(() => [] as any[]),
          fetchSupAgents(s.domain).catch(() => [] as SupAgent[]),
        ]);
        setQa(list);
        setFloor(ags);
        await loadCatalog(s.domain);
        await loadTeam(s.domain);
        const first = ags[0]?.ext || list[0]?.agent_ext || '';
        if (first) setExt(String(first));
      } catch (e) {
        setErr(e instanceof Error ? e.message : 'Learning load failed');
      }
    })();
  }, [loadCatalog, loadTeam, range.from, range.to]);

  useEffect(() => {
    if (!ext || !domain) return;
    (async () => {
      try {
        const data = await opsGet('me_learning', { domain, ext });
        setSkills(Array.isArray(data.skills) ? data.skills : []);
        setCount(Number(data.count || 0));
        setAssignments(Array.isArray(data.learning?.assignments) ? data.learning.assignments : []);
      } catch {
        setSkills([]);
        setAssignments([]);
      }
    })();
  }, [ext, domain]);

  const picked = qa.find((r) => String(r.agent_ext) === ext) || team.find((r) => r.agent_ext === ext);
  const floorHit = floor.find((a) => a.ext === ext);
  const name = picked?.agent_name || floorHit?.name || ext || '—';
  const skillKeys = useMemo(() => Object.entries(skillsMap), [skillsMap]);
  const roster = useMemo(() => {
    const map = new Map<string, { ext: string; name: string; assigned: number; passed: number; qa?: number }>();
    for (const a of floor) {
      if (!a.ext) continue;
      map.set(a.ext, { ext: a.ext, name: a.name || a.ext, assigned: 0, passed: 0 });
    }
    for (const t of team) {
      const id = String(t.agent_ext || '');
      if (!id) continue;
      const cur = map.get(id) || { ext: id, name: t.agent_name || id, assigned: 0, passed: 0 };
      cur.name = t.agent_name || cur.name;
      cur.assigned = Number(t.assigned || 0);
      cur.passed = Number(t.passed || 0);
      map.set(id, cur);
    }
    for (const r of qa) {
      const id = String(r.agent_ext || '');
      if (!id) continue;
      const cur = map.get(id) || { ext: id, name: r.agent_name || id, assigned: 0, passed: 0 };
      cur.name = r.agent_name || cur.name;
      cur.qa = Number(r.avg_pct);
      map.set(id, cur);
    }
    return [...map.values()].sort((a, b) => a.name.localeCompare(b.name) || a.ext.localeCompare(b.ext));
  }, [floor, team, qa]);

  const saveCourse = async () => {
    setErr('');
    setMsg('');
    try {
      await opsPost('learn_save', form, { domain });
      setMsg('Course saved.');
      setForm({ title: '', skill_key: 'knowledge', body: '', quiz: [blankQuestion()] });
      await loadCatalog(domain);
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Could not save course');
    }
  };

  const assign = async () => {
    if (!ext || !assignCourse) return;
    setErr('');
    setMsg('');
    try {
      const r = await opsPost(
        'learn_assign',
        { agent_ext: ext, agent_name: name, course_id: Number(assignCourse) },
        { domain },
      );
      setAssignments(Array.isArray(r.assignments) ? r.assignments : assignments);
      setMsg('Course assigned.');
      await loadTeam(domain);
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Assign failed');
    }
  };

  return (
    <div className="flex flex-col gap-[18px]">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-bold">Learning</h1>
          <p className="sc-meta mt-1">
            Courses from quality scores · agents take a quiz · you track progress
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            className={`sc-chip ${tab === 'progress' ? 'sc-chip-call' : 'bg-[var(--color-sc-soft)] text-[var(--color-sc-ink)]'}`}
            onClick={() => setTab('progress')}
          >
            Team progress
          </button>
          <button
            type="button"
            className={`sc-chip ${tab === 'courses' ? 'sc-chip-call' : 'bg-[var(--color-sc-soft)] text-[var(--color-sc-ink)]'}`}
            onClick={() => setTab('courses')}
          >
            Courses
          </button>
        </div>
      </div>
      {err ? <p className="text-sm text-[var(--color-sc-warn)]">{err}</p> : null}
      {msg ? <p className="text-sm text-[var(--color-sc-green)]">{msg}</p> : null}

      {tab === 'progress' ? (
        <div className="grid items-start gap-4 grid-cols-1 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.95fr)]">
          <section className="sc-card min-w-0">
            <h2 className="mb-3 text-[16px] font-bold">Team</h2>
            <table className="w-full text-left text-sm">
              <thead className="text-[11px] uppercase text-[var(--color-sc-muted)]">
                <tr>
                  <th className="px-2 py-2">Agent</th>
                  <th className="px-2 py-2 text-right">QA</th>
                  <th className="px-2 py-2 text-right">Courses</th>
                  <th className="px-2 py-2">Progress</th>
                </tr>
              </thead>
              <tbody>
                {roster.map((r) => {
                  const asg = r.assigned;
                  const pass = r.passed;
                  return (
                    <tr
                      key={r.ext}
                      className={`cursor-pointer border-t border-[var(--color-sc-line)] ${
                        r.ext === ext ? 'bg-[var(--color-sc-nav-active)]' : ''
                      }`}
                      onClick={() => setExt(r.ext)}
                    >
                      <td className="px-2 py-2 font-bold">
                        {r.name} <span className="sc-meta">{r.ext}</span>
                      </td>
                      <td className="px-2 py-2 text-right tabular-nums">
                        {r.qa != null && !Number.isNaN(r.qa) ? `${r.qa}%` : '—'}
                      </td>
                      <td className="px-2 py-2 text-right tabular-nums">
                        {pass}/{asg || 0}
                      </td>
                      <td className="px-2 py-2">
                        <StatusPill
                          label={asg ? `${Math.round((pass / asg) * 100)}%` : 'None'}
                          tone={!asg ? 'idle' : pass === asg ? 'ok' : 'blue'}
                        />
                      </td>
                    </tr>
                  );
                })}
                {roster.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-2 py-6 text-[var(--color-sc-muted)]">
                      No agents found on this domain. Check Users, then assign by extension below.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </section>

          <aside className="flex min-w-0 flex-col gap-4">
            <section className="sc-card">
              <h2 className="text-[16px] font-bold">{name}</h2>
              <p className="sc-meta mt-1">{count ? `${count} reviews` : 'No reviews'}</p>
              <div className="mt-3 space-y-2">
                {skills.map((s) => (
                  <div key={s.label}>
                    <div className="mb-1 flex justify-between text-sm">
                      <span>{s.label}</span>
                      <span className="font-bold">{s.samples ? `${s.pct}%` : '—'}</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-[var(--color-sc-soft)]">
                      <div
                        className={`h-full ${s.pct < 70 && s.samples ? 'bg-[var(--color-sc-warn)]' : 'bg-[var(--color-sc-green)]'}`}
                        style={{ width: `${s.pct}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="sc-card">
              <h2 className="mb-2 text-[16px] font-bold">Assigned courses</h2>
              {assignments.length === 0 ? (
                <p className="text-sm text-[var(--color-sc-muted)]">None yet. Assign below or score a weak skill.</p>
              ) : (
                <ul className="space-y-2">
                  {assignments.map((a) => (
                    <li key={a.assign_id || a.course_id} className="flex items-start justify-between gap-2 text-sm">
                      <span>
                        <b>{a.title}</b>
                        <span className="sc-meta ml-1">{a.skill}</span>
                      </span>
                      <StatusPill
                        label={a.status === 'passed' ? `${a.last_pct}%` : a.status || 'assigned'}
                        tone={a.status === 'passed' ? 'ok' : a.status === 'failed' ? 'warn' : 'blue'}
                      />
                    </li>
                  ))}
                </ul>
              )}
              <label className="mt-3 block text-[11px] font-bold tracking-wide text-[var(--color-sc-muted)]">
                Agent (name · number)
                <select className="sc-input mt-1.5 w-full" value={ext} onChange={(e) => setExt(e.target.value)}>
                  <option value="">Select agent…</option>
                  {roster.map((r) => (
                    <option key={r.ext} value={r.ext}>
                      {r.name} · {r.ext}
                    </option>
                  ))}
                </select>
              </label>
              <div className="mt-2 flex flex-wrap gap-2">
                <select
                  className="sc-input min-w-0 flex-1"
                  value={assignCourse}
                  onChange={(e) => setAssignCourse(e.target.value)}
                >
                  <option value="">Add a course…</option>
                  {courses.map((c) => (
                    <option key={c.course_id} value={c.course_id}>
                      {c.title}
                    </option>
                  ))}
                </select>
                <button type="button" className="sc-b2" disabled={!assignCourse || !ext} onClick={() => void assign()}>
                  Assign
                </button>
              </div>
              <Link className="sc-b2 mt-3 inline-block" to="/supervisor/quality">
                Open call review
              </Link>
            </section>
          </aside>
        </div>
      ) : (
        <div className="grid items-start gap-4 grid-cols-1 xl:grid-cols-[minmax(0,1fr)_minmax(340px,0.95fr)]">
          <section className="sc-card min-w-0">
            <h2 className="mb-3 text-[16px] font-bold">Library</h2>
            <div className="grid gap-2">
              {courses.map((c) => (
                <div key={c.course_id} className="rounded-[12px] border border-[var(--color-sc-line)] p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-bold">{c.title}</p>
                    <StatusPill label={c.skill || c.skill_key} tone="blue" />
                  </div>
                  <p className="sc-meta mt-1">{c.quiz_count || 0} quiz questions</p>
                  <p className="mt-2 line-clamp-3 text-sm leading-snug">{c.body}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="sc-card">
            <h2 className="text-[16px] font-bold">New course</h2>
            <p className="sc-meta mt-1">Use this when a skill needs extra coaching. Agents will quiz after they read it.</p>
            <label className="mt-3 block text-[11px] font-bold tracking-wide text-[var(--color-sc-muted)]">
              Title
              <input
                className="sc-input mt-1.5 w-full"
                value={form.title}
                onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
              />
            </label>
            <label className="mt-3 block text-[11px] font-bold tracking-wide text-[var(--color-sc-muted)]">
              Skill
              <select
                className="sc-input mt-1.5 w-full"
                value={form.skill_key}
                onChange={(e) => setForm((f) => ({ ...f, skill_key: e.target.value }))}
              >
                {(skillKeys.length ? skillKeys : [['knowledge', 'Knowledge']]).map(([k, lab]) => (
                  <option key={k} value={k}>
                    {lab}
                  </option>
                ))}
              </select>
            </label>
            <label className="mt-3 block text-[11px] font-bold tracking-wide text-[var(--color-sc-muted)]">
              Lesson
              <textarea
                className="sc-input mt-1.5 min-h-[110px] w-full py-2"
                value={form.body}
                onChange={(e) => setForm((f) => ({ ...f, body: e.target.value }))}
              />
            </label>
            <div className="mt-4 flex items-center justify-between gap-2">
              <p className="text-[11px] font-bold tracking-wide text-[var(--color-sc-muted)]">
                QUIZ · {form.quiz.length} question{form.quiz.length === 1 ? '' : 's'}
              </p>
              <button
                type="button"
                className="sc-b2"
                onClick={() => setForm((f) => ({ ...f, quiz: [...f.quiz, blankQuestion()] }))}
              >
                Add question
              </button>
            </div>
            {form.quiz.map((q, i) => (
              <div key={i} className="mt-3 rounded-[12px] border border-[var(--color-sc-line)] p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-[11px] font-bold tracking-wide text-[var(--color-sc-muted)]">QUESTION {i + 1}</p>
                  {form.quiz.length > 1 ? (
                    <button
                      type="button"
                      className="text-xs font-bold text-[var(--color-sc-warn)]"
                      onClick={() =>
                        setForm((f) => ({ ...f, quiz: f.quiz.filter((_, idx) => idx !== i) }))
                      }
                    >
                      Remove
                    </button>
                  ) : null}
                </div>
                <input
                  className="sc-input mt-1.5 w-full"
                  placeholder="Question"
                  value={q.q}
                  onChange={(e) =>
                    setForm((f) => {
                      const quiz = f.quiz.slice();
                      quiz[i] = { ...quiz[i], q: e.target.value };
                      return { ...f, quiz };
                    })
                  }
                />
                {q.choices.map((ch, ci) => (
                  <label key={ci} className="mt-1.5 flex items-center gap-2 text-sm">
                    <input
                      type="radio"
                      name={`ans${i}`}
                      checked={q.answer === ci}
                      onChange={() =>
                        setForm((f) => {
                          const quiz = f.quiz.slice();
                          quiz[i] = { ...quiz[i], answer: ci };
                          return { ...f, quiz };
                        })
                      }
                    />
                    <input
                      className="sc-input min-h-[36px] flex-1"
                      placeholder={`Choice ${ci + 1}`}
                      value={ch}
                      onChange={(e) =>
                        setForm((f) => {
                          const quiz = f.quiz.slice();
                          const choices = quiz[i].choices.slice();
                          choices[ci] = e.target.value;
                          quiz[i] = { ...quiz[i], choices };
                          return { ...f, quiz };
                        })
                      }
                    />
                    {q.choices.length > 2 ? (
                      <button
                        type="button"
                        className="text-xs font-bold text-[var(--color-sc-muted)]"
                        onClick={() =>
                          setForm((f) => {
                            const quiz = f.quiz.slice();
                            const choices = quiz[i].choices.filter((_, idx) => idx !== ci);
                            const answer = quiz[i].answer >= choices.length ? 0 : quiz[i].answer;
                            quiz[i] = { ...quiz[i], choices, answer };
                            return { ...f, quiz };
                          })
                        }
                      >
                        ×
                      </button>
                    ) : null}
                  </label>
                ))}
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    className="sc-b2"
                    onClick={() =>
                      setForm((f) => {
                        const quiz = f.quiz.slice();
                        quiz[i] = { ...quiz[i], choices: [...quiz[i].choices, ''] };
                        return { ...f, quiz };
                      })
                    }
                  >
                    Add choice
                  </button>
                  <p className="sc-meta">Marked radio is the correct answer.</p>
                </div>
              </div>
            ))}
            <button type="button" className="sc-btn mt-4" onClick={() => void saveCourse()}>
              Save course
            </button>
          </section>
        </div>
      )}
    </div>
  );
}
