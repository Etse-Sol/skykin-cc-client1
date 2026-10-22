import { useState } from 'react';
import StudioPage from './StudioPage';
import { useStudio } from './useStudio';

function flowOn(n: any) {
  return String(n.call_flow_status || '').toLowerCase() === 'true';
}

export default function AdminFlows() {
  const { data, err, save } = useStudio();
  const flows = data?.flows || [];
  const [msg, setMsg] = useState('');
  const [create, setCreate] = useState({
    call_flow_name: '',
    call_flow_extension: '',
    call_flow_feature_code: '*28',
    call_flow_data: '',
    call_flow_alternate_data: '',
  });
  return (
    <StudioPage
      title="Flows"
      path="/admin/flows"
      blurb="Toggle FusionPBX day/night call flows used by the inbound path"
    >
      {err ? <p className="text-sm text-[var(--color-sc-warn)]">{err}</p> : null}
      {msg ? <p className="text-sm font-bold">{msg}</p> : null}
      <section className="sc-card">
        <h2 className="mb-3 text-[16px] font-bold">Add call flow</h2>
        <p className="sc-meta mb-2">Day/night toggle: calls to the extension follow the day destination until you switch to night.</p>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          <input
            className="sc-input"
            placeholder="Name (Office hours)"
            value={create.call_flow_name}
            onChange={(e) => setCreate({ ...create, call_flow_name: e.target.value })}
          />
          <input
            className="sc-input"
            placeholder={data?.next_service_extension ? `Extension (${data.next_service_extension})` : 'Extension (9020)'}
            value={create.call_flow_extension}
            onChange={(e) => setCreate({ ...create, call_flow_extension: e.target.value.replace(/\D/g, '').slice(0, 8) })}
          />
          <input
            className="sc-input"
            placeholder="Feature code (*28)"
            value={create.call_flow_feature_code}
            onChange={(e) => setCreate({ ...create, call_flow_feature_code: e.target.value })}
          />
          <input
            className="sc-input"
            placeholder="Day dest (9000 XML domain)"
            value={create.call_flow_data}
            onChange={(e) => setCreate({ ...create, call_flow_data: e.target.value })}
          />
          <input
            className="sc-input"
            placeholder="Night dest (voicemail XML domain)"
            value={create.call_flow_alternate_data}
            onChange={(e) => setCreate({ ...create, call_flow_alternate_data: e.target.value })}
          />
        </div>
        <button
          type="button"
          className="sc-btn mt-3"
          onClick={() => {
            setMsg('');
            save('flow_save', {
              ...create,
              call_flow_status: true,
              call_flow_label: 'Day',
              call_flow_alternate_label: 'Night',
            })
              .then(() => {
                setMsg('Call flow created');
                setCreate({
                  call_flow_name: '',
                  call_flow_extension: '',
                  call_flow_feature_code: '*28',
                  call_flow_data: '',
                  call_flow_alternate_data: '',
                });
              })
              .catch((e) => setMsg(e instanceof Error ? e.message : 'Save failed'));
          }}
        >
          Create call flow
        </button>
      </section>
      <div className="flex flex-wrap gap-3">
        {flows.map((n) => {
          const on = flowOn(n);
          return (
            <div key={n.call_flow_uuid || n.call_flow_extension + n.call_flow_name} className="sc-card w-[240px]">
              <p className="text-[11px] font-bold tracking-wide text-[var(--color-sc-muted)]">
                {on ? 'DAY / OPEN' : 'NIGHT / CLOSED'}
              </p>
              <p className="mt-2 text-sm font-bold">{n.call_flow_name}</p>
              <p className="sc-meta mt-1">
                Ext {n.call_flow_extension}
                {n.call_flow_feature_code ? ` · ${n.call_flow_feature_code}` : ''}
              </p>
              {n.call_flow_label ? <p className="mt-1 text-sm">{n.call_flow_label}</p> : null}
              <button
                type="button"
                className="sc-btn mt-3 w-full"
                onClick={() => {
                  setMsg('');
                  save('flow_save', {
                    call_flow_uuid: n.call_flow_uuid,
                    call_flow_status: !on,
                    call_flow_label: n.call_flow_label || '',
                  })
                    .then(() => setMsg(on ? 'Switched to night/closed' : 'Switched to day/open'))
                    .catch((e) => setMsg(e instanceof Error ? e.message : 'Save failed'));
                }}
              >
                Switch to {on ? 'night' : 'day'}
              </button>
              <button
                type="button"
                className="sc-b2 mt-2 w-full"
                onClick={() => {
                  if (!window.confirm(`Delete flow ${n.call_flow_name}?`)) return;
                  setMsg('');
                  save('studio_delete', { kind: 'flow', id: n.call_flow_uuid })
                    .then(() => setMsg('Deleted'))
                    .catch((e) => setMsg(e instanceof Error ? e.message : 'Delete failed'));
                }}
              >
                Delete
              </button>
            </div>
          );
        })}
        {flows.length === 0 ? <p className="sc-meta">No call flows on this domain</p> : null}
      </div>
    </StudioPage>
  );
}
