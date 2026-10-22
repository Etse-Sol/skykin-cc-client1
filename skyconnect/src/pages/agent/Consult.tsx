import { useEffect, useState } from 'react';
import { useSoftphone } from '../../softphone/SoftphoneContext';
import { fetchAvailableAgents, type AvailableAgent } from '../../services/agents';

export default function Consult() {
  const phone = useSoftphone();
  const [agents, setAgents] = useState<AvailableAgent[]>([]);
  const [err, setErr] = useState('');
  const [msg, setMsg] = useState('');

  useEffect(() => {
    if (!phone.creds.domain) return;
    fetchAvailableAgents(phone.creds.domain, phone.creds.extension)
      .then(setAgents)
      .catch((e) => setErr(e instanceof Error ? e.message : 'Load failed'));
  }, [phone.creds.domain, phone.creds.extension]);

  const consultDial = async (ext: string) => {
    if (phone.phase === 'in_call') {
      // On an active call → 3-way conference (hold + dial + mix)
      setMsg(`Starting conference with ${ext}…`);
      try {
        await phone.conference(ext);
        setMsg(`Conference with ${ext}`);
      } catch (e) {
        setMsg(e instanceof Error ? e.message : 'Conference failed');
      }
      return;
    }
    if (phone.phase !== 'registered') {
      setMsg('Register softphone first (Available)');
      return;
    }
    phone.dial(ext);
    setMsg(`Calling ${ext} for consult…`);
  };

  return (
    <div>
      <section className="overflow-hidden rounded-xl border border-[var(--color-sc-line)] bg-white">
        <div className="border-b border-[var(--color-sc-line)] bg-[var(--color-sc-soft)] px-4 py-3">
          <h1 className="sc-section-title">Consult — Available agents</h1>
          <p className="mt-0.5 text-[11px] text-[var(--color-sc-muted)]">
            On a live call: Conference (3-way). Idle: dial the expert.
          </p>
        </div>
        <table className="w-full text-left text-sm">
          <thead className="text-[11px] font-semibold uppercase tracking-wide text-[var(--color-sc-muted)]">
            <tr>
              <th className="px-4 py-3">Agent</th>
              <th className="px-4 py-3">Extension</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Action</th>
            </tr>
          </thead>
          <tbody>
            {agents.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-[var(--color-sc-muted)]">
                  {err || 'No other Available agents right now'}
                </td>
              </tr>
            ) : (
              agents.map((a) => (
                <tr key={a.extension} className="border-t border-[var(--color-sc-line)]">
                  <td className="px-4 py-3 font-semibold text-[var(--color-sc-ink)]">{a.name}</td>
                  <td className="px-4 py-3 text-[var(--color-sc-ink)]">{a.extension}</td>
                  <td className="px-4 py-3 text-[var(--color-sc-ink)]">{a.status}</td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => consultDial(a.extension)}
                      className="rounded-lg bg-[var(--color-sc-green)] px-3 py-1.5 text-xs font-bold text-white"
                    >
                      {phone.phase === 'in_call' ? 'Conference' : 'Call'}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>
      {msg ? <p className="mt-3 text-sm text-[var(--color-sc-muted)]">{msg}</p> : null}
      {err ? <p className="mt-2 text-sm text-[var(--color-sc-warn)]">{err}</p> : null}
    </div>
  );
}
