import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Check } from 'lucide-react';
import CustomerJourneyTrack, {
  buildJourneyFromApi,
} from '../../components/CustomerJourneyTrack';
import DialPad from '../../components/DialPad';
import ConferenceModal from '../../components/ConferenceModal';
import TransferModal from '../../components/TransferModal';
import { getKnowledgeArticle, lookupContact, type CrmContact, type KnowledgeArticle } from '../../services/crm';
import { useLiveTranscript } from '../../lib/useLiveTranscript';
import { suggestFromTranscript, type LiveSuggest } from '../../services/ops';
import { useSoftphone } from '../../softphone/SoftphoneContext';

const scriptSteps = [
  'Greet and verify identity',
  'Confirm the issue',
  'Offer SIM replacement',
  'Confirm by SMS',
];

function formatTime(sec: number) {
  const n = Math.max(0, Math.floor(sec || 0));
  const h = Math.floor(n / 3600)
    .toString()
    .padStart(2, '0');
  const m = Math.floor((n % 3600) / 60)
    .toString()
    .padStart(2, '0');
  const s = (n % 60).toString().padStart(2, '0');
  return `${h}:${m}:${s}`;
}

type Tab = 'interaction' | 'caller' | 'reasons';

export default function LiveCall() {
  const phone = useSoftphone();
  const navigate = useNavigate();
  const [dial, setDial] = useState('');
  const [showPad, setShowPad] = useState(false);
  const [showTransfer, setShowTransfer] = useState(false);
  const [showConference, setShowConference] = useState(false);
  const [checked, setChecked] = useState<Record<number, boolean>>({ 0: true, 1: true });
  const [crm, setCrm] = useState<CrmContact | null>(null);
  const [tab, setTab] = useState<Tab>('interaction');
  const [sttLang, setSttLang] = useState('am-ET');
  const [lastTalkSec, setLastTalkSec] = useState(0);
  const [lastWasOutbound, setLastWasOutbound] = useState(false);
  const [kbAsk, setKbAsk] = useState('');
  const [kb, setKb] = useState<LiveSuggest | null>(null);
  const [kbOpen, setKbOpen] = useState<KnowledgeArticle | null>(null);
  const padRef = useRef<HTMLDivElement>(null);

  const inCall =
    phone.phase === 'in_call' || phone.phase === 'calling' || phone.phase === 'ringing';
  const lastPhone = (phone.lastRemoteNumber || '').trim();
  const trackPhone = (phone.remoteNumber || '').trim();
  const crmLinkPhone = trackPhone || lastPhone;

  useEffect(() => {
    if (phone.phase === 'in_call') setLastTalkSec(phone.callSeconds);
  }, [phone.phase, phone.callSeconds]);

  useEffect(() => {
    if (phone.phase === 'calling') setLastWasOutbound(true);
    if (phone.phase === 'ringing') setLastWasOutbound(false);
  }, [phone.phase]);

  const showingLast = !inCall && !!crmLinkPhone;
  const displayNumber = trackPhone || (inCall ? dial || '—' : lastPhone || 'No active call');
  const timer =
    phone.phase === 'in_call'
      ? formatTime(phone.callSeconds)
      : showingLast
        ? formatTime(lastTalkSec)
        : '00:00:00';
  const canCall = phone.phase === 'registered';
  const established = phone.phase === 'in_call';
  const stt = useLiveTranscript({
    active: established,
    muted: phone.muted,
    onHold: phone.onHold,
    lang: sttLang,
    getAudio: phone.getCallAudio,
  });

  useEffect(() => {
    if (!crmLinkPhone) {
      setCrm(null);
      return;
    }
    let cancelled = false;
    lookupContact(crmLinkPhone)
      .then((row) => {
        if (!cancelled) setCrm(row);
      })
      .catch(() => {
        if (!cancelled) setCrm(null);
      });
    return () => {
      cancelled = true;
    };
  }, [crmLinkPhone]);

  const journey = useMemo(
    () => buildJourneyFromApi(crm?.journey, crm?.call_history, crm?.notes),
    [crm],
  );

  const transcriptBlob = useMemo(() => {
    const rows = stt.lines.map((l) => l.text);
    if (stt.interim) rows.push(stt.interim);
    return rows.join(' ').replace(/\s+/g, ' ').trim();
  }, [stt.lines, stt.interim]);

  useEffect(() => {
    const typed = kbAsk.trim();
    const q = typed || transcriptBlob;
    const am = /[\u1200-\u137F]/.test(q);
    const words = q.split(/\s+/).filter((w) => w.replace(/[^\p{L}\p{N}]/gu, '').length >= 3);
    if (!q || (!typed && !am && words.length < 1)) {
      if (!typed) setKb(null);
      return;
    }
    const t = window.setTimeout(() => {
      suggestFromTranscript(q)
        .then((row) => setKb(row))
        .catch(() => {
          /* keep last match */
        });
    }, kbAsk.trim() ? 350 : 700);
    return () => window.clearTimeout(t);
  }, [kbAsk, transcriptBlob]);

  useEffect(() => {
    if (!showPad) return;
    const onDoc = (e: MouseEvent) => {
      if (padRef.current && !padRef.current.contains(e.target as Node)) {
        setShowPad(false);
      }
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [showPad]);

  const placeCall = () => {
    if (established) return;
    phone.dial(dial);
    setShowPad(false);
  };

  const padTone = (k: string) => {
    setDial((v) => v + k);
    if (established) phone.sendDtmf(k);
  };

  const chip = (id: Tab, label: string) => (
    <button
      key={id}
      type="button"
      onClick={() => setTab(id)}
      className={`sc-chip ${tab === id ? 'sc-chip-call' : 'bg-[var(--color-sc-soft)] text-[var(--color-sc-ink)]'}`}
    >
      {label}
    </button>
  );

  return (
    <div className="relative flex flex-col gap-[18px]">
      <div className="sc-card flex flex-wrap items-center gap-4">
        <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-[14px] bg-[#0B5C44] text-[18px] font-extrabold text-white">
          {(crm?.full_name || displayNumber || 'SC')
            .replace(/[^\p{L}\p{N}]+/gu, ' ')
            .trim()
            .split(/\s+/)
            .slice(0, 2)
            .map((p) => p[0])
            .join('')
            .toUpperCase() || 'SC'}
        </span>
        <div className="min-w-0 flex-1">
          <h1 className="text-[22px] font-bold leading-tight">
            {inCall || showingLast ? `Interaction · ${displayNumber}` : 'Interaction'}{' '}
            {established ? (
              <span className="sc-chip sc-chip-ready ml-1 align-middle">ESTABLISHED</span>
            ) : phone.phase === 'ringing' ? (
              <span className="sc-chip sc-chip-call ml-1 align-middle">RINGING</span>
            ) : phone.phase === 'calling' ? (
              <span className="sc-chip bg-[#e8f2ff] text-[#1f5f7a] ml-1 align-middle">DIALING</span>
            ) : showingLast ? (
              <span className="sc-chip bg-[var(--color-sc-soft)] text-[var(--color-sc-ink)] ml-1 align-middle">
                LAST CALL
              </span>
            ) : (
              <span className="sc-chip bg-[var(--color-sc-soft)] text-[var(--color-sc-muted)] ml-1 align-middle">
                IDLE
              </span>
            )}
          </h1>
          <p className="sc-meta mt-1">
            VOICE ·{' '}
            {phone.phase === 'calling' || (showingLast && lastWasOutbound)
              ? 'OUTBOUND'
              : inCall || showingLast
                ? 'INBOUND'
                : '—'}{' '}
            · {displayNumber}
            {crm?.full_name ? ` · ${crm.full_name}` : ''}
          </p>
        </div>
        <div className="grid grid-cols-3 gap-x-5 gap-y-1 text-right">
          <div>
            <p className="text-[10px] font-bold tracking-wide text-[var(--color-sc-muted)]">TALK</p>
            <p className="text-[20px] font-extrabold leading-none">{timer}</p>
          </div>
          <div>
            <p className="text-[10px] font-bold tracking-wide text-[var(--color-sc-muted)]">HOLD</p>
            <p className="text-[20px] font-extrabold leading-none">00:00:00</p>
          </div>
          <div>
            <p className="text-[10px] font-bold tracking-wide text-[var(--color-sc-muted)]">RING</p>
            <p className="text-[20px] font-extrabold leading-none">
              {phone.phase === 'ringing' || phone.phase === 'calling' ? formatTime(phone.callSeconds) : '00:00:00'}
            </p>
          </div>
        </div>
      </div>

      {phone.phase === 'ringing' ? (
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={phone.answer} className="sc-btn">
            Answer
          </button>
          <button type="button" onClick={phone.decline} className="sc-bd">
            Decline
          </button>
        </div>
      ) : phone.phase === 'calling' ? (
        <div className="flex flex-wrap items-center gap-2">
          <span className="sc-meta">Ringback playing…</span>
          <button type="button" onClick={phone.hangup} className="sc-bd">
            Cancel
          </button>
        </div>
      ) : (
        <div className="relative flex flex-wrap items-center gap-2.5" ref={padRef}>
          <button type="button" onClick={phone.toggleMute} disabled={phone.phase !== 'in_call'} className="sc-b2">
            {phone.muted ? 'Unmute' : 'Mute'}
          </button>
          <button type="button" onClick={phone.toggleHold} disabled={phone.phase !== 'in_call'} className="sc-b2">
            {phone.onHold ? 'Resume' : 'Hold'}
          </button>
          <button
            type="button"
            className="sc-b2"
            disabled={phone.phase !== 'in_call' && !canCall}
            onClick={() => setShowPad((v) => !v)}
          >
            Keypad
          </button>
          <button
            type="button"
            className="sc-b2"
            disabled={phone.phase !== 'in_call'}
            onClick={() => setShowTransfer(true)}
          >
            Transfer
          </button>
          <button
            type="button"
            className="sc-b2"
            disabled={phone.phase !== 'in_call' || phone.inConference}
            onClick={() => setShowConference(true)}
          >
            Conference
          </button>
          <button type="button" onClick={phone.hangup} disabled={!inCall} className="sc-bd">
            End call
          </button>
          {showPad ? (
            <div className="absolute left-0 top-full z-40 mt-2">
              <DialPad
                value={dial}
                onChange={setDial}
                onCall={placeCall}
                onClose={() => setShowPad(false)}
                canCall={canCall && !established}
                onTone={established ? padTone : undefined}
                inCall={established}
              />
            </div>
          ) : null}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {chip('interaction', 'Interaction')}
        {chip('caller', 'Caller details')}
        {chip('reasons', 'Call reasons')}
      </div>

      {tab === 'interaction' ? (
        <div className="grid items-start gap-4 grid-cols-1 lg:grid-cols-[minmax(0,1.35fr)_minmax(240px,0.9fr)_minmax(280px,1.05fr)]">
          <section className="sc-card flex min-h-[420px] min-w-0 flex-col">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-[16px] font-bold">Live transcript</h2>
              <div className="flex flex-wrap items-center gap-2">
                <select
                  className="rounded-lg border border-[var(--color-sc-border)] bg-white px-2 py-1 text-[12px] font-bold"
                  value={sttLang}
                  onChange={(e) => {
                    setSttLang(e.target.value);
                    window.setTimeout(() => stt.startSpeech(), 0);
                  }}
                  aria-label="Caption language"
                >
                  <option value="en-US">English</option>
                  <option value="am-ET">አማርኛ / Amharic</option>
                </select>
                {established ? (
                  <button type="button" className="sc-b2" onClick={() => stt.startSpeech()}>
                    Start both-side captions
                  </button>
                ) : null}
                {established && stt.status === 'live' ? (
                  <span className="sc-chip bg-[#fde8e6] text-[#c03a34]">Live</span>
                ) : null}
              </div>
            </div>
            {stt.callerHint ? <p className="sc-meta mt-1">{stt.callerHint}</p> : null}
            <div
              ref={stt.listRef}
              className="mt-3 min-h-[280px] flex-1 overflow-y-auto rounded-[12px] border border-[var(--color-sc-line)] bg-[#f7fbf8] px-3 py-2"
            >
              {established && stt.lines.length === 0 && !stt.interim ? (
                <p className="text-sm text-[var(--color-sc-muted)]">Listening… speak to see captions.</p>
              ) : !established && stt.lines.length === 0 ? (
                <p className="text-sm text-[var(--color-sc-muted)]">
                  {showingLast ? 'No captions were captured on this call.' : 'No live interaction.'}
                </p>
              ) : (
                <ul className="space-y-2">
                  {stt.lines.map((row) => (
                    <li key={row.id} className="text-sm leading-snug">
                      <span
                        className={`mr-2 text-[11px] font-bold ${
                          row.speaker === 'you' ? 'text-[var(--color-sc-green)]' : 'text-[var(--color-sc-blue)]'
                        }`}
                      >
                        {row.speaker === 'you' ? 'You' : 'Caller'}
                      </span>
                      {row.text}
                    </li>
                  ))}
                  {stt.interim ? (
                    <li className="text-sm italic text-[var(--color-sc-muted)]">
                      <span className="mr-2 text-[11px] font-bold text-[var(--color-sc-green)]">You</span>
                      {stt.interim}
                    </li>
                  ) : null}
                </ul>
              )}
            </div>
            <h3 className="mt-3 text-[12px] font-bold text-[var(--color-sc-muted)]">Script</h3>
            <ul className="mt-2 grid grid-cols-1 gap-x-3 gap-y-2 sm:grid-cols-2">
              {scriptSteps.map((step, i) => {
                const on = !!checked[i];
                return (
                  <li key={step}>
                    <button
                      type="button"
                      onClick={() => setChecked((prev) => ({ ...prev, [i]: !prev[i] }))}
                      className="flex w-full items-center gap-2 text-left text-[13px]"
                    >
                      <span
                        className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-[4px] border-2 ${
                          on
                            ? 'border-[var(--color-sc-green)] bg-[var(--color-sc-green)] text-white'
                            : 'border-[var(--color-sc-green)] bg-white'
                        }`}
                      >
                        {on ? <Check size={10} strokeWidth={3} /> : null}
                      </span>
                      <span>{step}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </section>

          <section className="sc-card flex min-w-0 flex-col">
            <h2 className="mb-2 text-[16px] font-bold">Suggested for this call</h2>
            {(kb?.articles || []).length === 0 ? (
              <p className="text-sm text-[var(--color-sc-muted)]">
                {established
                  ? 'Suggestions appear as you speak.'
                  : 'Hints start when the call is established.'}
              </p>
            ) : (
              <ul className="flex flex-col gap-2">
                {(kb?.articles || []).slice(0, 4).map((a, i) => (
                  <li key={String(a.article_id || a.title)}>
                    <button
                      type="button"
                      className={`w-full rounded-[12px] border p-2.5 text-left ${
                        i === 0 ? 'border-[var(--color-sc-green)]' : 'border-[var(--color-sc-line)]'
                      }`}
                      onClick={() => {
                        const id = Number(a.article_id || 0);
                        if (!id) return;
                        getKnowledgeArticle(id)
                          .then((row) => setKbOpen(row))
                          .catch(() => setKbOpen(null));
                      }}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <b className="text-[13px] leading-snug">{a.title}</b>
                        <span className="sc-chip sc-chip-ready shrink-0">{i === 0 ? 'Open' : 'Guide'}</span>
                      </div>
                      {i === 0 && kb?.say_next ? (
                        <p className="mt-1 line-clamp-3 text-[12px] leading-snug text-[var(--color-sc-ink)]">
                          {kb.say_next}
                        </p>
                      ) : a.excerpt ? (
                        <p className="sc-meta mt-1 line-clamp-2">{a.excerpt}</p>
                      ) : null}
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <label className="mt-3 block text-[11px] font-bold tracking-wide text-[var(--color-sc-muted)]">
              Ask knowledge
              <input
                className="mt-1.5 w-full rounded-lg border border-[var(--color-sc-border)] bg-white px-3 py-2 text-sm font-normal text-[var(--color-sc-ink)]"
                placeholder="SIM, stolen, telebirr…"
                value={kbAsk}
                onChange={(e) => setKbAsk(e.target.value)}
              />
            </label>
          </section>

          <div className="flex min-w-0 flex-col gap-4">
            {kbOpen ? (
              <aside className="sc-card sticky top-3 max-h-[calc(100vh-5rem)] overflow-y-auto">
                <div className="mb-2 flex items-start justify-between gap-3">
                  <div>
                    <p className="text-[11px] font-bold tracking-wide text-[var(--color-sc-muted)]">GUIDE</p>
                    <h2 className="text-[16px] font-bold leading-snug">{kbOpen.title}</h2>
                  </div>
                  <button type="button" className="sc-b2 shrink-0" onClick={() => setKbOpen(null)}>
                    Close
                  </button>
                </div>
                {kbOpen.tag ? <span className="sc-chip sc-chip-ready">{kbOpen.tag}</span> : null}
                <p className="mt-3 whitespace-pre-wrap text-sm leading-snug">{kbOpen.body}</p>
              </aside>
            ) : (
              <section className="sc-card">
                <h2 className="mb-2 text-[16px] font-bold">Interaction flow</h2>
                {established ? (
                  <>
                    <p className="text-sm font-bold">
                      Established <span className="sc-chip sc-chip-ready ml-1">Current</span>
                    </p>
                    <p className="sc-meta mb-2">Talking now</p>
                    <p className="text-sm font-bold">Ringing</p>
                    <p className="sc-meta">Answered</p>
                  </>
                ) : showingLast ? (
                  <>
                    <p className="text-sm font-bold">
                      Last call{' '}
                      <span className="sc-chip ml-1 bg-[var(--color-sc-soft)] text-[var(--color-sc-ink)]">Ended</span>
                    </p>
                    <p className="sc-meta mb-2">
                      {displayNumber} · talk {timer}
                    </p>
                    <p className="text-sm font-bold">Wrap-up</p>
                    <p className="sc-meta">Save a reason if needed, then wait for the next call.</p>
                  </>
                ) : (
                  <p className="text-sm text-[var(--color-sc-muted)]">No live interaction. Dial or wait for a queue call.</p>
                )}
              </section>
            )}
            {!kbOpen && crmLinkPhone ? (
              <CustomerJourneyTrack
                items={journey}
                title="History track"
                emptyText="No prior calls on this number yet."
              />
            ) : null}
          </div>
        </div>
      ) : null}

      {tab === 'caller' ? (
        <section className="sc-card max-w-xl">
          <h2 className="text-[16px] font-bold">Caller details</h2>
          <dl className="mt-4 space-y-3">
            {[
              ['Name', crm?.full_name || '—'],
              ['Number', displayNumber],
              ['Your extension', phone.creds.extension || '—'],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="sc-meta">{label}</dt>
                <dd className="mt-0.5 text-sm font-bold">{value}</dd>
              </div>
            ))}
          </dl>
          {crmLinkPhone ? (
            <Link
              to={`/agent/customers?phone=${encodeURIComponent(crmLinkPhone)}`}
              className="mt-4 inline-flex text-sm font-bold text-[var(--color-sc-green)] hover:underline"
            >
              {trackPhone ? 'Open full Customer 360' : `Last call 360 (${crmLinkPhone})`}
            </Link>
          ) : null}
        </section>
      ) : null}

      {tab === 'reasons' ? (
        <section className="sc-card max-w-xl">
          <h2 className="text-[16px] font-bold">Call reasons</h2>
          <p className="sc-meta mt-2">Save the wrap-up reason after the conversation.</p>
          <button
            type="button"
            onClick={() => navigate('/agent/wrap-up')}
            className="sc-btn mt-4"
          >
            Select call reason
          </button>
        </section>
      ) : null}

      <TransferModal open={showTransfer} onClose={() => setShowTransfer(false)} />
      <ConferenceModal open={showConference} onClose={() => setShowConference(false)} />
    </div>
  );
}
