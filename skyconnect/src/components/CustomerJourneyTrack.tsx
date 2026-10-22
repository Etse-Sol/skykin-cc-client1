import type { CrmCallHistory, CrmJourneyEvent } from '../services/crm';
import { fmtBillsec } from '../services/crm';

export type JourneyItem = {
  when: string;
  channel: string;
  text: string;
  tone: 'green' | 'mint' | 'blue' | 'forest' | 'grey';
};

function channelTone(channel: string): JourneyItem['tone'] {
  const c = channel.toLowerCase();
  if (c.includes('voice') || c.includes('inbound') || c.includes('outbound')) return 'green';
  if (c.includes('chat') || c.includes('web')) return 'mint';
  if (c.includes('whatsapp')) return 'blue';
  if (c.includes('app')) return 'forest';
  if (c.includes('sms') || c.includes('survey') || c.includes('shop') || c.includes('case') || c.includes('crm')) {
    return 'grey';
  }
  return 'grey';
}

function dotClass(tone: JourneyItem['tone']): string {
  switch (tone) {
    case 'green':
      return 'bg-[var(--color-sc-green)]';
    case 'mint':
      return 'bg-[#8fd18a]';
    case 'blue':
      return 'bg-[var(--color-sc-blue)]';
    case 'forest':
      return 'bg-[var(--color-sc-green-deep)]';
    default:
      return 'bg-[#9aab9f]';
  }
}

/** "Today 10:12" / "Yesterday" / "3 days ago" style labels. */
export function relativeWhen(callTime?: string): string {
  if (!callTime) return '—';
  const raw = callTime.trim();
  const d = new Date(raw.includes('T') ? raw : raw.replace(' ', 'T'));
  if (Number.isNaN(d.getTime())) return raw.slice(0, 16);

  const now = new Date();
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startThat = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const dayDiff = Math.round((startToday.getTime() - startThat.getTime()) / 86400000);
  const hm = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;

  if (dayDiff === 0) return `Today ${hm}`;
  if (dayDiff === 1) return `Yesterday ${hm}`;
  if (dayDiff > 1 && dayDiff < 7) return `${dayDiff} days ago ${hm}`;
  if (dayDiff >= 7 && dayDiff < 14) return `Last week ${hm}`;
  if (dayDiff >= 14 && dayDiff < 45) return `Last month ${hm}`;
  return raw.slice(0, 16);
}

export function buildJourneyFromApi(
  journey?: CrmJourneyEvent[],
  history?: CrmCallHistory[],
  notes?: string,
): JourneyItem[] {
  if (journey && journey.length > 0) {
    return journey.slice(0, 16).map((j) => {
      const channel = j.channel || 'CRM';
      return {
        when: relativeWhen(j.event_at),
        channel,
        text: j.summary || '—',
        tone: channelTone(channel),
      };
    });
  }

  const items: JourneyItem[] = (history || []).slice(0, 12).map((h) => {
    const dir = (h.direction || 'call').toLowerCase();
    const channel = 'Voice';
    const bill = Number(h.billsec || 0);
    // Hangup cause is SIP status — call reason comes from wrap-up / journey API.
    let text = `${dir || 'Call'} · ${fmtBillsec(h.billsec)}`;
    if (dir === 'inbound' && bill > 0) text = `Inbound call — awaiting call reason`;
    else if (dir === 'outbound' && bill > 0) text = `Outbound call — awaiting call reason`;
    else if (dir === 'inbound') text = `Missed / short inbound — awaiting call reason`;
    else text = `${dir || 'Call'} — awaiting call reason`;
    return {
      when: relativeWhen(h.call_time),
      channel,
      text,
      tone: channelTone(channel),
    };
  });

  if (notes?.trim()) {
    items.push({
      when: 'On file',
      channel: 'CRM',
      text: notes.trim().slice(0, 140),
      tone: 'grey',
    });
  }
  return items;
}

/** @deprecated use buildJourneyFromApi */
export function buildJourneyFromCdr(history: CrmCallHistory[], notes?: string): JourneyItem[] {
  return buildJourneyFromApi(undefined, history, notes);
}

type Props = {
  items: JourneyItem[];
  title?: string;
  emptyText?: string;
  className?: string;
};

/** Vertical history track — matches Customer 360 journey mockup. */
export default function CustomerJourneyTrack({
  items,
  title = 'Customer journey',
  emptyText = 'No history track for this customer yet.',
  className = '',
}: Props) {
  return (
    <section className={`rounded-2xl border border-[var(--color-sc-line)] bg-white p-6 ${className}`}>
      <h3 className="mb-6 sc-section-title">{title}</h3>
      {items.length === 0 ? (
        <p className="text-sm text-[var(--color-sc-muted)]">{emptyText}</p>
      ) : (
        <ol className="relative ml-2 border-l-2 border-[var(--color-sc-line)] pl-7">
          {items.map((j, i) => (
            <li key={`${j.when}-${j.channel}-${i}`} className="relative pb-6 last:pb-0">
              <span
                className={`absolute -left-[37px] top-1 h-4 w-4 rounded-full border-[3px] border-white shadow-sm ${dotClass(j.tone)}`}
                aria-hidden
              />
              <p className="text-[12px] leading-none text-[var(--color-sc-muted)]">
                <span>{j.when}</span>
                <span className="mx-1.5 text-[var(--color-sc-border)]">|</span>
                <span>{j.channel}</span>
              </p>
              <p className="mt-1.5 text-[15px] font-semibold leading-snug text-[var(--color-sc-ink)]">
                {j.text}
              </p>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
