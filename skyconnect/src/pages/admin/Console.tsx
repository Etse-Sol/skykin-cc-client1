import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { fetchAgentSession } from '../../services/session';
import { fetchLeaveRequests, fetchSupAgents, fetchSupQueue } from '../../services/supervisorApi';
import { useStudio } from './useStudio';

export default function AdminConsole() {
  const { data, err, save } = useStudio();
  const [waiting, setWaiting] = useState(0);
  const [online, setOnline] = useState(0);
  const [pending, setPending] = useState(0);
  const [qErr, setQErr] = useState('');
  const [did, setDid] = useState({ did: '', dest_ext: '', dest_kind: 'ivr' });
  const [didMsg, setDidMsg] = useState('');
  const [reloadMsg, setReloadMsg] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const s = await fetchAgentSession();
        const [q, agents, leaves] = await Promise.all([
          fetchSupQueue(s.domain),
          fetchSupAgents(s.domain),
          fetchLeaveRequests(s.domain),
        ]);
        setWaiting(q.waiting_callers?.length || q.queues?.reduce((n, r) => n + (r.waiting || 0), 0) || 0);
        setOnline(agents.filter((a) => !['offline', 'logged_out'].includes((a.status || '').toLowerCase())).length);
        setPending(leaves.filter((l) => (l.status || '').toLowerCase() === 'pending').length);
      } catch (e) {
        setQErr(e instanceof Error ? e.message : 'Live board failed');
      }
    })();
  }, []);

  const channels = [
    { name: 'Voice / FreeSWITCH', state: `${online} agents · ${waiting} waiting`, ok: true },
    { name: 'IVR menus', state: `${data?.ivr?.length ?? 0} published`, ok: (data?.ivr?.length || 0) > 0 },
    { name: 'Queues', state: `${data?.queues?.length ?? 0} queues`, ok: (data?.queues?.length || 0) > 0 },
    { name: 'Call flows', state: `${data?.flows?.length ?? 0} flows`, ok: true },
  ];

  return (
    <div className="flex flex-col gap-[18px]">
      <div>
        <h1 className="text-[24px] font-bold">Admin console</h1>
        <p className="sc-meta mt-1">
          Live channel health from this tenant · {data?.domain || '—'}
        </p>
        <button
          type="button"
          className="sc-btn mt-3"
          onClick={() => {
            setReloadMsg('');
            save('reloadxml', {})
              .then(() => setReloadMsg('Dialplan reloaded'))
              .catch((e) => setReloadMsg(e instanceof Error ? e.message : 'Reload failed'));
          }}
        >
          Reload dialplan
        </button>
        {reloadMsg ? <p className="mt-2 text-sm font-bold">{reloadMsg}</p> : null}
      </div>
      {err || qErr ? <p className="text-sm text-[var(--color-sc-warn)]">{err || qErr}</p> : null}
      <div className="flex flex-wrap gap-4">
        <section className="sc-card min-w-0 flex-[1_1_300px]">
          <h2 className="mb-3 text-[16px] font-bold">Channel health</h2>
          {channels.map((h) => (
            <div
              key={h.name}
              className="flex items-center justify-between border-b border-[var(--color-sc-soft)] py-2 text-sm"
            >
              <span>{h.name}</span>
              <span className={`sc-chip ${h.ok ? 'sc-chip-ready' : 'sc-chip-call'}`}>{h.state}</span>
            </div>
          ))}
        </section>
        <section className="sc-card min-w-0 flex-[1_1_260px]">
          <h2 className="mb-3 text-[16px] font-bold">Pending approvals</h2>
          <p className="border-b border-[var(--color-sc-soft)] py-2 text-sm">
            Leave requests · {pending} pending
          </p>
          <Link to="/supervisor/team" className="mt-3 inline-block text-sm font-bold text-[var(--color-sc-green)]">
            Open team
          </Link>
        </section>
        <section className="sc-card min-w-0 flex-[1_1_300px]">
          <h2 className="mb-3 text-[16px] font-bold">Inventory</h2>
          <p className="border-b border-[var(--color-sc-soft)] py-2 text-sm">
            Users {data?.users?.length ?? 0}
          </p>
          <p className="border-b border-[var(--color-sc-soft)] py-2 text-sm">
            Recordings {data?.recordings?.length ?? 0}
          </p>
        </section>
      </div>
      <section className="sc-card">
        <h2 className="mb-3 text-[16px] font-bold">Most-used tools</h2>
        <div className="flex flex-wrap gap-2">
          <Link to="/admin/ivr" className="sc-b2">IVR designer</Link>
          <Link to="/admin/chatbot" className="sc-b2">Chatbot studio</Link>
          <Link to="/admin/queues" className="sc-b2">Queues</Link>
          <Link to="/admin/users" className="sc-b2">Users</Link>
          <Link to="/admin/reports/ivr" className="sc-b2">IVR report</Link>
          <Link to="/admin/reports/reasons" className="sc-b2">Call reasons</Link>
        </div>
      </section>
      <section className="sc-card">
        <h2 className="mb-3 text-[16px] font-bold">DID routes</h2>
        <p className="sc-meta mb-3">
          Send an inbound number to an IVR, queue, or call-flow extension. Live inbound still uses the SkyKin Lua path —
          this writes a DID map file only (no media change).
        </p>
        {didMsg ? <p className="mb-2 text-sm font-bold">{didMsg}</p> : null}
        <div className="grid gap-2 sm:grid-cols-4">
          <input
            className="sc-input"
            placeholder="DID (2519…)"
            value={did.did}
            onChange={(e) => setDid({ ...did, did: e.target.value.replace(/\D/g, '').slice(0, 15) })}
          />
          <input
            className="sc-input"
            placeholder="Dest extension (9000)"
            value={did.dest_ext}
            onChange={(e) => setDid({ ...did, dest_ext: e.target.value.replace(/\D/g, '').slice(0, 8) })}
          />
          <select className="sc-input" value={did.dest_kind} onChange={(e) => setDid({ ...did, dest_kind: e.target.value })}>
            <option value="ivr">IVR</option>
            <option value="queue">Queue</option>
            <option value="flow">Call flow</option>
          </select>
          <button
            type="button"
            className="sc-btn"
            onClick={() => {
              setDidMsg('');
              save('did_save', did)
                .then(() => {
                  setDidMsg('DID saved');
                  setDid({ did: '', dest_ext: '', dest_kind: did.dest_kind });
                })
                .catch((e) => setDidMsg(e instanceof Error ? e.message : 'Save failed'));
            }}
          >
            Save DID
          </button>
        </div>
        <ul className="mt-3 space-y-2 text-sm">
          {(data?.did_routes || []).map((r) => (
            <li key={r.route_id || r.did} className="flex items-center justify-between gap-2 border-b border-[var(--color-sc-soft)] py-2">
              <span>
                {r.did} → ext {r.dest_ext} ({r.dest_kind})
              </span>
              <button
                type="button"
                className="sc-b2"
                onClick={() => {
                  if (!window.confirm(`Remove DID ${r.did}?`)) return;
                  save('did_delete', { route_id: r.route_id, did: r.did })
                    .then(() => setDidMsg('Removed'))
                    .catch((e) => setDidMsg(e instanceof Error ? e.message : 'Delete failed'));
                }}
              >
                Remove
              </button>
            </li>
          ))}
          {(data?.did_routes || []).length === 0 ? <li className="sc-meta">No DID maps yet</li> : null}
        </ul>
      </section>
    </div>
  );
}
