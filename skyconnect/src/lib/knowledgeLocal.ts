import type { LiveSuggest } from '../services/ops';

type LocalArticle = {
  title: string;
  tag: string;
  excerpt: string;
  keys: string[];
};

const ARTICLES: LocalArticle[] = [
  {
    title: 'Lost or stolen phone checklist',
    tag: 'Guide',
    excerpt:
      'Advise SIM block, capture IMEI, then SIM swap with Fayda OTP. Warn about telebirr PIN if the old phone may be unlocked.',
    keys: ['stolen', 'steal', 'theft', 'lost', 'imei', 'ተሰረቀ', 'ተሰርቋል', 'የተሰረቀ', 'ስርቆት', 'ጠፍቷል', 'ጠፋ'],
  },
  {
    title: 'SIM swap with Fayda OTP',
    tag: 'Updated',
    excerpt:
      'Verify name + Fayda, send OTP, block the old SIM, issue a replacement, confirm telebirr and packages restore.',
    keys: ['sim', 'swap', 'fayda', 'otp', 'ሲም', 'ምትክ', 'ፋይዳ'],
  },
  {
    title: 'telebirr daily limit',
    tag: 'Popular',
    excerpt: 'Confirm the wallet number, explain daily limits, retry after midnight EAT or split the transfer.',
    keys: ['telebirr', 'limit', 'pin', 'wallet', 'ቴሌብር', 'ፒን'],
  },
  {
    title: 'Package dispute handling',
    tag: 'Guide',
    excerpt: 'Confirm package, purchase time, and amount. Open a case as Escalated if it did not activate.',
    keys: ['package', 'billing', 'charge', 'dispute', 'ፓኬጅ', 'ክፍያ'],
  },
];

export function suggestFromLiveText(raw: string): LiveSuggest {
  const q = (raw || '').replace(/\s+/g, ' ').trim();
  if (!q) return { ok: true, articles: [] };
  const hay = q.toLowerCase();
  const scored = ARTICLES.map((a) => {
    const score = a.keys.reduce((n, k) => (hay.includes(k.toLowerCase()) ? n + 10 : n), 0);
    return { a, score };
  })
    .filter((x) => x.score > 0)
    .sort((x, y) => y.score - x.score)
    .slice(0, 4);
  const articles = scored.map((x) => ({
    title: x.a.title,
    tag: x.a.tag,
    excerpt: x.a.excerpt,
    score: x.score,
  }));
  const top = scored[0]?.a;
  return {
    ok: true,
    articles,
    say_next: top?.excerpt || '',
    why: top ? `Matched live captions: ${top.title}` : '',
    ai: false,
  };
}
