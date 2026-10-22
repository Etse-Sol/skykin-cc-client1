import { useCallback, useEffect, useRef, useState } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { fetchLastCall, usableCallNumber, type HistoryRow } from '../services/callHistory';
import BrowserShell from '../components/BrowserShell';
import IncomingCallBanner from '../components/IncomingCallBanner';
import RoleGuard from '../components/RoleGuard';
import RoleNav from '../components/RoleNav';
import SkyConnectLogo from '../components/SkyConnectLogo';
import { useSoftphone } from '../softphone/SoftphoneContext';
import { fetchAgentSession, type AgentSession } from '../services/session';
import {
  fpbxToUi,
  getAgentStatus,
  myLeaveRequest,
  requestBreak,
  setAgentStatus,
  type UiStatus,
} from '../services/agentStatus';

function initials(name: string) {
  const p = name.trim().split(/\s+/).filter(Boolean);
  if (p.length >= 2) return (p[0][0] + p[1][0]).toUpperCase();
  return (name.slice(0, 2) || 'A').toUpperCase();
}

export default function AgentLayout() {
  const navigate = useNavigate();
  const phone = useSoftphone();
  const [session, setSession] = useState<AgentSession | null>(null);
  const [status, setStatus] = useState<UiStatus>('Available');
  const [pendingBreak, setPendingBreak] = useState(false);
  const [busy, setBusy] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [dial, setDial] = useState('');
  const [lastCall, setLastCall] = useState<HistoryRow | null>(null);
  const handledLeave = useRef<string>('');
  const prevPhase = useRef(phone.phase);

  useEffect(() => {
    fetchAgentSession().then(setSession).catch(() => {});
  }, []);

  const loadLastCall = useCallback(async () => {
    const ext = phone.creds.extension || session?.extension;
    const domain = phone.creds.domain || session?.domain;
    if (!ext) return;
    try {
      const row = await fetchLastCall({ ext, domain });
      setLastCall(row);
    } catch {
      /* keep previous */
    }
  }, [phone.creds.extension, phone.creds.domain, session?.extension, session?.domain]);

  useEffect(() => {
    void loadLastCall();
    const t = window.setInterval(() => void loadLastCall(), 20000);
    return () => window.clearInterval(t);
  }, [loadLastCall]);

  useEffect(() => {
    const wasLive =
      prevPhase.current === 'in_call' ||
      prevPhase.current === 'calling' ||
      prevPhase.current === 'ringing';
    const nowIdle =
      phone.phase === 'registered' || phone.phase === 'idle' || phone.phase === 'failed';
    if (wasLive && nowIdle) {
      window.setTimeout(() => void loadLastCall(), 2000);
      window.setTimeout(() => void loadLastCall(), 8000);
    }
    prevPhase.current = phone.phase;
  }, [phone.phase, loadLastCall]);

  useEffect(() => {
    const ext = phone.creds.extension || session?.extension;
    const domain = phone.creds.domain || session?.domain;
    if (!ext || !domain) return;
    getAgentStatus(ext, domain)
      .then((r) => {
        if (r.ok && r.agent_status != null) setStatus(fpbxToUi(r.agent_status));
      })
      .catch(() => {});
    myLeaveRequest(ext, domain).then((r) => {
      if (r.request?.status === 'pending') {
        setPendingBreak(true);
        setStatusMsg('Break request pending supervisor approval');
      }
    });
  }, [phone.creds.extension, phone.creds.domain, session?.extension, session?.domain]);

  useEffect(() => {
    if (!pendingBreak) return;
    const ext = phone.creds.extension || session?.extension || '';
    const domain = phone.creds.domain || session?.domain || '';
    if (!ext || !domain) return;
    const tick = () => {
      myLeaveRequest(ext, domain).then((r) => {
        const req = r.request;
        if (!req) return;
        const key = `${req.id}:${req.status}`;
        if (req.status === 'pending') return;
        if (handledLeave.current === key) return;
        handledLeave.current = key;
        setPendingBreak(false);
        if (req.status === 'approved') {
          setStatus('Break');
          setStatusMsg('Break approved — you are On Break');
        } else if (req.status === 'denied') {
          setStatus('Available');
          setStatusMsg('Break denied — you remain Available');
        } else if (req.status === 'cancelled') {
          setStatus('Available');
          setStatusMsg('Break request cancelled');
        }
      });
    };
    tick();
    const t = window.setInterval(tick, 5000);
    return () => clearInterval(t);
  }, [pendingBreak, phone.creds.extension, phone.creds.domain, session]);

  const changeStatus = useCallback(
    async (next: UiStatus) => {
      const ext = phone.creds.extension || session?.extension || '';
      const domain = phone.creds.domain || session?.domain || '';
      const name = session?.display_name || session?.username || '';
      if (!ext || !domain) {
        setStatusMsg('No extension — cannot set queue status');
        return;
      }
      const prev = status;
      setBusy(true);
      setStatusMsg('');
      try {
        if (next === 'Break') {
          const r = await requestBreak({ ext, domain, name });
          if (!r.ok) {
            setStatusMsg(r.error || 'Break request failed');
            return;
          }
          setPendingBreak(true);
          handledLeave.current = '';
          setStatusMsg('Break requested — waiting for supervisor');
          return;
        }

        setStatus(next);
        const r = await setAgentStatus(ext, domain, next);
        if (!r.ok) {
          setStatus(prev);
          setStatusMsg(r.error || 'Status update failed');
          return;
        }
        setPendingBreak(false);
        setStatusMsg(
          next === 'Available' ? 'Ready — queues can ring you' : 'Logged Out of queue',
        );
        if (next === 'Available') {
          if (phone.phase === 'idle' || phone.phase === 'failed') phone.register();
          navigate('/agent/interaction');
        }
        if (next === 'Offline') phone.unregister();
      } catch {
        setStatus(prev);
        setStatusMsg('Could not reach status API');
      } finally {
        setBusy(false);
        window.setTimeout(() => setStatusMsg(''), 5000);
      }
    },
    [phone, session, status, navigate],
  );

  const name = session?.display_name || session?.username || 'Agent';
  const ext = phone.creds.extension || '—';
  const onCall = phone.phase === 'in_call' || phone.phase === 'ringing' || phone.phase === 'calling';
  const canCall = phone.phase === 'registered';
  const breakActive = pendingBreak || status === 'Break';
  const lastNumber =
    usableCallNumber(lastCall?.number) || usableCallNumber(phone.lastRemoteNumber);

  const redialLast = () => {
    if (!lastNumber) return;
    setDial(lastNumber);
    if (canCall) {
      phone.dial(lastNumber);
      navigate('/agent/interaction');
    }
  };

  const sidebar = (
    <>
      <div className="mb-2.5 px-3">
        <SkyConnectLogo />
      </div>
      <RoleNav
        role="agent"
        logout={session?.logout}
        onLogout={() => {
          const e = phone.creds.extension || session?.extension;
          const d = phone.creds.domain || session?.domain;
          if (e && d) setAgentStatus(e, d, 'Offline').catch(() => {});
        }}
      />
    </>
  );

  const header = (
    <header className="flex flex-wrap items-center justify-between gap-3 bg-[var(--color-sc-page)] px-7 pt-5 pb-0">
      <form
        className="flex items-center gap-2.5"
        onSubmit={(e) => {
          e.preventDefault();
          if (canCall && dial.trim()) {
            phone.dial(dial.trim());
            navigate('/agent/interaction');
          }
        }}
      >
        <label htmlFor="sc-dial" className="sr-only">
          Dial number
        </label>
        <input
          id="sc-dial"
          className="sc-input w-[220px]"
          placeholder="Enter number"
          value={dial}
          onChange={(e) => setDial(e.target.value)}
        />
        <button type="submit" className="sc-btn" disabled={!canCall || !dial.trim()}>
          Call
        </button>
      </form>
      <div className="flex flex-wrap items-center gap-3">
        <span className="sc-meta">{phone.statusLabel}</span>
        {onCall ? (
          <span className="sc-chip sc-chip-call">On call</span>
        ) : status === 'Available' && !pendingBreak ? (
          <span className="sc-chip sc-chip-ready">Ready</span>
        ) : (
          <span className="sc-chip bg-[var(--color-sc-soft)] text-[var(--color-sc-muted)]">
            {pendingBreak ? 'Pending' : status}
          </span>
        )}
        <button
          type="button"
          disabled={busy}
          onClick={() => changeStatus('Available')}
          className={`rounded-full px-3 py-1.5 text-[12px] font-bold ${
            status === 'Available' && !pendingBreak
              ? 'bg-[var(--color-sc-green)] text-white'
              : 'bg-[var(--color-sc-soft)] text-[var(--color-sc-ink)]'
          }`}
        >
          Ready
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => changeStatus('Break')}
          className={`rounded-full px-3 py-1.5 text-[12px] font-bold ${
            breakActive
              ? 'bg-[var(--color-sc-forest)] text-white'
              : 'bg-[var(--color-sc-soft)] text-[var(--color-sc-ink)]'
          }`}
        >
          {pendingBreak ? 'Pending…' : 'Break'}
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => changeStatus('Offline')}
          className={`rounded-full px-3 py-1.5 text-[12px] font-bold ${
            status === 'Offline'
              ? 'bg-[var(--color-sc-forest)] text-white'
              : 'bg-[var(--color-sc-soft)] text-[var(--color-sc-ink)]'
          }`}
        >
          Offline
        </button>
        <span className="sc-avatar" title={name}>
          {initials(name)}
        </span>
      </div>
    </header>
  );

  return (
    <RoleGuard allow="agent">
      <BrowserShell
        sidebar={sidebar}
        header={
          <>
            {header}
            {statusMsg ? (
              <p className="px-7 pt-2 sc-meta">{statusMsg}</p>
            ) : null}
            <IncomingCallBanner />
          </>
        }
      >
        <Outlet
          context={{
            session,
            name,
            status,
            changeStatus,
            initials: initials(name),
            ext,
            lastCall,
            lastNumber,
            onRedialLast: redialLast,
          }}
        />
      </BrowserShell>
    </RoleGuard>
  );
}
