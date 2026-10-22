import { useCallback, useEffect, useState } from 'react';
import StatusPill from '../../components/StatusPill';
import { fetchAgentSession } from '../../services/session';
import { opsGet, opsPost } from '../../services/ops';

type Skill = { label: string; pct: number; samples: number };
type Assignment = {
  assign_id?: number;
  course_id: number;
  title: string;
  skill?: string;
  skill_key?: string;
  body?: string;
  source?: string;
  status?: string;
  last_pct?: number;
  quiz_count?: number;
};
type QuizQ = { i?: number; q: string; choices: string[] };

function toneFor(status?: string): 'ok' | 'warn' | 'idle' | 'blue' {
  if (status === 'passed') return 'ok';
  if (status === 'failed') return 'warn';
  if (status === 'assigned') return 'blue';
  return 'idle';
}

export default function AgentLearning() {
  const [name, setName] = useState('');
  const [ext, setExt] = useState('');
  const [domain, setDomain] = useState('');
  const [skills, setSkills] = useState<Skill[]>([]);
  const [rows, setRows] = useState<Assignment[]>([]);
  const [passed, setPassed] = useState(0);
  const [assigned, setAssigned] = useState(0);
  const [count, setCount] = useState(0);
  const [err, setErr] = useState('');
  const [open, setOpen] = useState<Assignment | null>(null);
  const [quiz, setQuiz] = useState<QuizQ[]>([]);
  const [picks, setPicks] = useState<Record<number, number>>({});
  const [result, setResult] = useState<{ pct: number; passed: boolean; right: number; total: number } | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const s = await fetchAgentSession();
    setName(s.display_name || s.username);
    setExt(s.extension);
    setDomain(s.domain);
    const data = await opsGet('me_learning', { domain: s.domain, ext: s.extension });
    setSkills(Array.isArray(data.skills) ? data.skills : []);
    setCount(Number(data.count || 0));
    const pack = data.learning || {};
    setRows(Array.isArray(pack.assignments) ? pack.assignments : []);
    setPassed(Number(pack.passed || 0));
    setAssigned(Number(pack.assigned || 0));
  }, []);

  useEffect(() => {
    load().catch((e) => setErr(e instanceof Error ? e.message : 'Could not load learning'));
  }, [load]);

  const openCourse = async (row: Assignment) => {
    setErr('');
    setResult(null);
    setPicks({});
    try {
      const data = await opsGet('learn_course', {
        domain,
        ext,
        course_id: String(row.course_id),
      });
      const c = data.course || {};
      setOpen({ ...row, title: c.title || row.title, body: c.body || row.body, skill: c.skill || row.skill });
      setQuiz(Array.isArray(c.quiz) ? c.quiz : []);
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Could not open course');
    }
  };

  const submitQuiz = async () => {
    if (!open) return;
    setBusy(true);
    setErr('');
    try {
      const answers = quiz.map((_, i) => (picks[i] ?? -1));
      const r = await opsPost('learn_quiz', { course_id: open.course_id, agent_ext: ext, answers }, { domain });
      setResult({
        pct: Number(r.pct || 0),
        passed: !!r.passed,
        right: Number(r.right || 0),
        total: Number(r.total || 0),
      });
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Quiz could not be scored');
    } finally {
      setBusy(false);
    }
  };

  const weak = skills.filter((s) => s.samples > 0 && s.pct < 70).map((s) => s.label);
  const recommended = rows.filter((r) => r.status !== 'passed');

  return (
    <div className="flex flex-col gap-[18px]">
      <div>
        <h1 className="text-[22px] font-bold">Learning</h1>
        <p className="sc-meta mt-1">
          {name || '—'} · {count ? `${count} quality reviews` : 'No reviews yet'}
          {weak.length ? ` · Focus: ${weak.join(', ')}` : ''}
        </p>
      </div>
      {err ? <p className="text-sm text-[var(--color-sc-warn)]">{err}</p> : null}

      <div className="grid grid-cols-3 gap-3">
        <div className="sc-card">
          <p className="text-[11px] font-bold tracking-wide text-[var(--color-sc-muted)]">ASSIGNED</p>
          <p className="mt-1 text-[22px] font-extrabold">{assigned}</p>
        </div>
        <div className="sc-card">
          <p className="text-[11px] font-bold tracking-wide text-[var(--color-sc-muted)]">PASSED</p>
          <p className="mt-1 text-[22px] font-extrabold">{passed}</p>
        </div>
        <div className="sc-card">
          <p className="text-[11px] font-bold tracking-wide text-[var(--color-sc-muted)]">PROGRESS</p>
          <p className="mt-1 text-[22px] font-extrabold">{assigned ? Math.round((passed / assigned) * 100) : 0}%</p>
        </div>
      </div>

      <div className="grid items-start gap-4 grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
        <div className="flex min-w-0 flex-col gap-4">
          <section className="sc-card">
            <h2 className="mb-3 text-[16px] font-bold">Skill from evaluations</h2>
            <div className="space-y-3">
              {skills.map((s) => (
                <div key={s.label}>
                  <div className="mb-1 flex justify-between text-sm">
                    <span className="font-medium">{s.label}</span>
                    <span className="font-bold">{s.samples ? `${s.pct}%` : '—'}</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-[var(--color-sc-soft)]">
                    <div
                      className={`h-full rounded-full ${s.pct < 70 && s.samples ? 'bg-[var(--color-sc-warn)]' : 'bg-[var(--color-sc-green)]'}`}
                      style={{ width: `${s.pct}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="sc-card">
            <h2 className="mb-3 text-[16px] font-bold">Recommended courses</h2>
            {recommended.length === 0 ? (
              <p className="text-sm text-[var(--color-sc-muted)]">
                No open courses. After a quality review, weak skills are assigned here.
              </p>
            ) : (
              <ul className="space-y-2">
                {rows.map((r) => (
                  <li key={r.assign_id || r.course_id}>
                    <button
                      type="button"
                      className={`w-full rounded-[12px] border p-3 text-left ${
                        open?.course_id === r.course_id
                          ? 'border-[var(--color-sc-green)] bg-[#f7fbf8]'
                          : 'border-[var(--color-sc-line)]'
                      }`}
                      onClick={() => void openCourse(r)}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <p className="text-sm font-bold">{r.title}</p>
                          <p className="sc-meta mt-0.5">
                            {r.skill} · {r.source === 'supervisor' ? 'Assigned by supervisor' : 'From evaluation'}
                          </p>
                        </div>
                        <StatusPill
                          label={
                            r.status === 'passed'
                              ? `Passed ${r.last_pct || 0}%`
                              : r.status === 'failed'
                                ? `Retry ${r.last_pct || 0}%`
                                : 'To do'
                          }
                          tone={toneFor(r.status)}
                        />
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        <div className="min-w-0">
          {!open ? (
            <section className="sc-card min-h-[280px]">
              <h2 className="text-[16px] font-bold">Lesson and quiz</h2>
              <p className="sc-meta mt-2">Open a course on the left. Read the lesson, then take the quiz (pass mark 70%).</p>
            </section>
          ) : (
            <div className="flex flex-col gap-4">
              <section className="sc-card">
                <p className="text-[11px] font-bold tracking-wide text-[var(--color-sc-muted)]">LESSON</p>
                <h2 className="mt-1 text-[16px] font-bold">{open.title}</h2>
                <p className="sc-meta mt-1">{open.skill}</p>
                <p className="mt-3 whitespace-pre-wrap text-sm leading-snug">{open.body}</p>
              </section>
              <section className="sc-card">
                <h2 className="text-[16px] font-bold">Quiz</h2>
                <p className="sc-meta mt-1">Choose one answer per question, then submit.</p>
                <ol className="mt-3 space-y-4">
                  {quiz.map((q, i) => (
                    <li key={i}>
                      <p className="text-sm font-bold">
                        {i + 1}. {q.q}
                      </p>
                      <div className="mt-2 grid gap-1.5">
                        {(q.choices || []).map((ch, ci) => (
                          <label
                            key={ci}
                            className={`flex cursor-pointer items-center gap-2 rounded-[10px] border px-3 py-2 text-sm ${
                              picks[i] === ci
                                ? 'border-[var(--color-sc-green)] bg-[#f7fbf8]'
                                : 'border-[var(--color-sc-line)]'
                            }`}
                          >
                            <input
                              type="radio"
                              name={`q${i}`}
                              checked={picks[i] === ci}
                              onChange={() => setPicks((p) => ({ ...p, [i]: ci }))}
                            />
                            {ch}
                          </label>
                        ))}
                      </div>
                    </li>
                  ))}
                </ol>
                <button type="button" className="sc-btn mt-4" disabled={busy || quiz.length === 0} onClick={() => void submitQuiz()}>
                  {busy ? 'Scoring…' : 'Submit quiz'}
                </button>
                {result ? (
                  <p className={`mt-3 text-sm font-bold ${result.passed ? 'text-[var(--color-sc-green)]' : 'text-[var(--color-sc-warn)]'}`}>
                    {result.passed ? 'Passed' : 'Not yet'} · {result.right}/{result.total} · {result.pct}%
                    {result.passed ? '' : ' · Review the lesson and try again.'}
                  </p>
                ) : null}
              </section>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
