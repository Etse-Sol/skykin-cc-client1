import { useCallback, useEffect, useState } from 'react';
import { fetchAgentSession } from '../../services/session';
import { opsGet, opsPost } from '../../services/ops';

type Thread = {
  thread_id: number;
  channel?: string;
  customer_key?: string;
  customer_name?: string;
  status?: string;
  agent_ext?: string;
};
type Msg = { msg_id: number; role: string; body: string; created_at?: string };

export default function Inbox() {
  const [domain, setDomain] = useState('');
  const [ext, setExt] = useState('');
  const [threads, setThreads] = useState<Thread[]>([]);
  const [sel, setSel] = useState<number | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState('');
  const [err, setErr] = useState('');

  const load = useCallback(async () => {
    const s = await fetchAgentSession();
    setDomain(s.domain);
    setExt(s.extension);
    const data = await opsGet('omni_inbox', { domain: s.domain });
    setThreads(Array.isArray(data.threads) ? data.threads : []);
  }, []);

  const open = useCallback(
    async (id: number) => {
      setSel(id);
      const data = await opsGet('omni_thread', { domain, thread_id: String(id) });
      setMsgs(Array.isArray(data.messages) ? data.messages : []);
    },
    [domain],
  );

  useEffect(() => {
    load().catch((e) => setErr(e instanceof Error ? e.message : 'Inbox failed'));
    const t = window.setInterval(() => {
      load().catch(() => {});
      if (sel && domain) open(sel).catch(() => {});
    }, 3000);
    return () => window.clearInterval(t);
  }, [load, open, sel]);

  const send = async () => {
    if (!sel || !text.trim()) return;
    const data = await opsPost('omni_reply', { thread_id: sel, text: text.trim(), agent_ext: ext }, { domain });
    setText('');
    setMsgs(Array.isArray(data.messages) ? data.messages : []);
    await load();
  };

  return (
    <div>
      <h1 className="sc-page-title">Inbox</h1>
      <p className="sc-meta mt-1">Web chat and WhatsApp. Bot answers from Knowledge; you take over anytime.</p>
      {err ? <p className="mt-2 text-sm text-[var(--color-sc-warn)]">{err}</p> : null}
      <div className="mt-4 grid gap-3 lg:grid-cols-[280px_1fr]">
        <ul className="sc-card max-h-[70vh] overflow-auto p-0">
          {threads.map((t) => (
            <li key={t.thread_id}>
              <button
                type="button"
                className={`w-full px-3 py-2 text-left text-sm ${sel === t.thread_id ? 'bg-[var(--color-sc-nav-active)]' : ''}`}
                onClick={() => void open(t.thread_id)}
              >
                <b>{t.customer_name || t.customer_key}</b>
                <span className="sc-meta block">
                  {t.channel} · {t.status}
                  {t.agent_ext ? ` · ${t.agent_ext}` : ''}
                </span>
              </button>
            </li>
          ))}
          {!threads.length ? <li className="sc-meta p-3">No open chats.</li> : null}
        </ul>
        <section className="sc-card flex min-h-[70vh] flex-col">
          <div className="min-h-0 flex-1 space-y-2 overflow-auto">
            {msgs.map((m) => (
              <div
                key={m.msg_id}
                className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                  m.role === 'agent' ? 'ml-auto bg-[var(--color-sc-green)] text-white' : 'bg-[var(--color-sc-soft)]'
                }`}
              >
                <p className="text-[10px] uppercase opacity-70">{m.role}</p>
                <p className="whitespace-pre-wrap">{m.body}</p>
              </div>
            ))}
          </div>
          {sel ? (
            <div className="mt-3 flex gap-2">
              <input
                className="sc-input flex-1"
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    void send();
                  }
                }}
                placeholder="Reply…"
              />
              <button type="button" className="sc-btn" onClick={() => void send()}>
                Send
              </button>
              <button
                type="button"
                className="sc-b2"
                onClick={() => void opsPost('omni_close', { thread_id: sel }, { domain }).then(load)}
              >
                Close
              </button>
            </div>
          ) : (
            <p className="sc-meta mt-3">Select a thread.</p>
          )}
        </section>
      </div>
    </div>
  );
}
