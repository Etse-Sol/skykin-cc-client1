export const REASON_TREE: Record<string, Record<string, string[]>> = {
  'Service request': {
    'SIM and identity': ['SIM swap', 'Lost or stolen phone', 'Fayda verification'],
    telebirr: ['Wrong transfer', 'PIN reset', 'Limit inquiry'],
  },
  'Fault and complaint': {
    Network: ['No service', 'Slow data'],
    Billing: ['Unexpected charge', 'Package dispute'],
  },
};

export type WrapGuess = {
  l1: string;
  l2: string;
  l3: string;
  path: string;
  outcome: string;
  notes: string;
};

const RULES: { keys: string[]; l1: string; l2: string; l3: string; outcome: string }[] = [
  {
    keys: ['stolen', 'steal', 'theft', 'lost phone', 'imei', 'ተሰረቀ', 'ተሰርቋል', 'የተሰረቀ', 'ስርቆት', 'ጠፍቷል', 'ጠፋ'],
    l1: 'Service request',
    l2: 'SIM and identity',
    l3: 'Lost or stolen phone',
    outcome: 'Follow-up',
  },
  {
    keys: ['fayda', 'otp', 'identity', 'ፋይዳ'],
    l1: 'Service request',
    l2: 'SIM and identity',
    l3: 'Fayda verification',
    outcome: 'Resolved',
  },
  {
    keys: ['sim swap', 'sim replacement', 'ሲም', 'ምትክ'],
    l1: 'Service request',
    l2: 'SIM and identity',
    l3: 'SIM swap',
    outcome: 'Follow-up',
  },
  {
    keys: ['pin reset', 'pin', 'ፒን'],
    l1: 'Service request',
    l2: 'telebirr',
    l3: 'PIN reset',
    outcome: 'Resolved',
  },
  {
    keys: ['wrong transfer', 'telebirr', 'ቴሌብር'],
    l1: 'Service request',
    l2: 'telebirr',
    l3: 'Wrong transfer',
    outcome: 'Follow-up',
  },
  {
    keys: ['limit', 'package'],
    l1: 'Service request',
    l2: 'telebirr',
    l3: 'Limit inquiry',
    outcome: 'Resolved',
  },
  {
    keys: ['no service', 'no network', 'coverage'],
    l1: 'Fault and complaint',
    l2: 'Network',
    l3: 'No service',
    outcome: 'Follow-up',
  },
  {
    keys: ['slow data', 'slow internet'],
    l1: 'Fault and complaint',
    l2: 'Network',
    l3: 'Slow data',
    outcome: 'Follow-up',
  },
  {
    keys: ['unexpected charge', 'billing', 'bill', 'ክፍያ'],
    l1: 'Fault and complaint',
    l2: 'Billing',
    l3: 'Unexpected charge',
    outcome: 'Follow-up',
  },
  {
    keys: ['package dispute', 'dispute'],
    l1: 'Fault and complaint',
    l2: 'Billing',
    l3: 'Package dispute',
    outcome: 'Escalated',
  },
];

export function guessWrapFromTranscript(raw: string): WrapGuess | null {
  const text = (raw || '')
    .split('\n')
    .map((line) => line.replace(/^(You|Caller)\s*:\s*/i, '').trim())
    .filter(Boolean)
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim();
  if (!text || text === ':') return null;
  const hay = text.toLowerCase();
  const hit = RULES.find((r) => r.keys.some((k) => hay.includes(k.toLowerCase())));
  if (!hit) return null;
  return {
    l1: hit.l1,
    l2: hit.l2,
    l3: hit.l3,
    path: `${hit.l1} > ${hit.l2} > ${hit.l3}`,
    outcome: hit.outcome,
    notes: text.slice(0, 800),
  };
}
