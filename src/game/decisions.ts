// أحداث بقرارات (تختار ردّك) + سباق الفضاء
import { DAYS_PER_MONTH, MAX_TECH } from './defs';
import type { Engine } from './engine';
import type { CmdResult, DecisionId, Nation } from './types';
import { COMBAT_UNITS } from './types';

const clamp = (x: number, a: number, b: number) => Math.max(a, Math.min(b, x));

export interface DecisionOpt { label: string; hint: string; run: (e: Engine, n: Nation) => string }
export interface DecisionDef { icon: string; title: string; text: string; opts: DecisionOpt[]; ai: (e: Engine, n: Nation) => number }

const cash = (n: Nation, k: number) => Math.round(Math.max(10, n.d.income * k));

export const DECISIONS: Record<DecisionId, DecisionDef> = {
  quake: {
    icon: '🌋', title: 'زلزال مدمر', text: 'زلزال قوي ضرب منطقة في دولتك والناس تنتظر ردة فعل الحكومة.',
    opts: [
      { label: '🚑 إغاثة كاملة', hint: 'تكلف فلوس، والاستقرار يرتفع', run: (e, n) => { const c = cash(n, 3); n.treasury -= c; n.stability = clamp(n.stability + 8, 0, 100); return `صرفت ${c} مليار على الإغاثة، والشعب ممتن (+8 استقرار)`; } },
      { label: '🤷 نكتفي بالقليل', hint: 'توفر فلوس، والاستقرار ينزل', run: (e, n) => { n.stability = clamp(n.stability - 10, 0, 100); for (const t of e.owned(n.id)) t.gdp *= 0.98; return 'الناس زعلانين (-10 استقرار) والاقتصاد تأثر'; } },
    ],
    ai: (e, n) => (n.treasury > cash(n, 3) * 2 ? 0 : 1),
  },
  refugees: {
    icon: '🧳', title: 'لاجئين على الحدود', text: 'آلاف اللاجئين يطلبون الدخول لدولتك هرباً من الحرب.',
    opts: [
      { label: '🤝 نستقبلهم', hint: 'سكان أكثر، بس تكلفة واستقرار أقل شوي', run: (e, n) => { for (const t of e.owned(n.id)) t.pop *= 1.04; const c = cash(n, 1.5); n.treasury -= c; n.stability = clamp(n.stability - 3, 0, 100); return `السكان +4%، والتكلفة ${c} مليار`; } },
      { label: '🚧 نقفل الحدود', hint: 'ما يتغير شي، بس سمعتك تتأثر', run: (e, n) => { n.stability = clamp(n.stability + 2, 0, 100); return 'الحدود انقفلت'; } },
    ],
    ai: (e, n) => (n.ai?.pers === 'economic' ? 0 : e.rand() < 0.5 ? 0 : 1),
  },
  strike: {
    icon: '🪧', title: 'إضراب عمال', text: 'العمال مضربين ويطالبون برفع الرواتب، والمصانع واقفة.',
    opts: [
      { label: '💵 نرفع الرواتب', hint: 'تكلف، والاستقرار يرتفع', run: (e, n) => { const c = cash(n, 2); n.treasury -= c; n.stability = clamp(n.stability + 6, 0, 100); return `رفعت الرواتب (${c} مليار) والمصانع رجعت`; } },
      { label: '👮 نقمع الإضراب', hint: 'ما تدفع، بس الاستقرار ينزل كثير', run: (e, n) => { n.stability = clamp(n.stability - 12, 0, 100); return 'الإضراب انقمع.. والشعب غاضب (-12 استقرار)'; } },
    ],
    ai: (e, n) => (n.stability < 40 || n.treasury > cash(n, 4) ? 0 : 1),
  },
  scientists: {
    icon: '🔬', title: 'علماء يطلبون تمويل', text: 'فريق علماء يقول إنه قريب من اختراق كبير ويحتاج تمويل.',
    opts: [
      { label: '💰 نموّلهم', hint: 'تكلفة كبيرة مقابل أبحاث كثيرة', run: (e, n) => { const c = cash(n, 4); n.treasury -= c; if (e.rand() < 0.75) { n.research += 150; return `الاختراق نجح! +150 نقطة بحث (التكلفة ${c} مليار)`; } return `صرفت ${c} مليار.. والتجربة فشلت 😅`; } },
      { label: '🙅 مو الحين', hint: 'ما يتغير شي', run: () => 'العلماء راحوا يشتغلون لدولة ثانية' },
    ],
    ai: (e, n) => (n.tech < MAX_TECH && n.treasury > cash(n, 6) ? 0 : 1),
  },
  smuggling: {
    icon: '📦', title: 'شحنة سلاح مهربة', text: 'المخابرات مسكت شحنة سلاح مهربة على الحدود.',
    opts: [
      { label: '🪖 نضمها للجيش', hint: 'دبابات مجانية، بس فضيحة دولية', run: (e, n) => { n.units.tank += 6; n.units.inf += 10; n.stability = clamp(n.stability - 3, 0, 100); return '+6 دبابات و +10 مشاة'; } },
      { label: '🔥 نتلفها', hint: 'الاستقرار يرتفع شوي', run: (e, n) => { n.stability = clamp(n.stability + 4, 0, 100); return 'أتلفت الشحنة (+4 استقرار)'; } },
    ],
    ai: (e, n) => (e.enemies(n.id).length ? 0 : 1),
  },
  treasure: {
    icon: '🏺', title: 'كنز أثري', text: 'علماء الآثار اكتشفوا كنز تاريخي ضخم.',
    opts: [
      { label: '🏛️ نسوي متحف', hint: 'الاستقرار يرتفع ودخل سياحة', run: (e, n) => { n.stability = clamp(n.stability + 8, 0, 100); for (const t of e.owned(n.id)) t.gdp *= 1.02; return 'المتحف صار وجهة سياحية (+8 استقرار، +2% ناتج)'; } },
      { label: '💰 نبيعه', hint: 'فلوس فورية', run: (e, n) => { const c = cash(n, 5); n.treasury += c; return `بعت الكنز بـ ${c} مليار`; } },
    ],
    ai: (e, n) => (n.treasury < 50 ? 1 : 0),
  },
  coupplot: {
    icon: '🗡️', title: 'مؤامرة انقلاب', text: 'المخابرات تقول إن ضباط في الجيش يخططون لانقلاب.',
    opts: [
      { label: '⛓️ نعتقل الضباط', hint: 'تخسر جزء من الجيش، والخطر يروح', run: (e, n) => { for (const k of COMBAT_UNITS) n.units[k] = Math.floor(n.units[k] * 0.92); n.stability = clamp(n.stability + 5, 0, 100); return 'اعتقلت المتآمرين (الجيش -8%، +5 استقرار)'; } },
      { label: '🎲 نتجاهل', hint: 'لو صدقت المؤامرة.. مصيبة', run: (e, n) => { if (e.rand() < 0.4) { n.stability = clamp(n.stability - 25, 0, 100); for (const k of COMBAT_UNITS) n.units[k] = Math.floor(n.units[k] * 0.8); return 'الانقلاب صار فعلاً! (-25 استقرار، الجيش -20%)'; } return 'طلعت إشاعة، ما صار شي'; } },
    ],
    ai: (e, n) => (n.stability < 40 ? 0 : 1),
  },
  investor: {
    icon: '🏦', title: 'مستثمر أجنبي', text: 'شركة عالمية تبي تستثمر في دولتك بشرط إعفاء ضريبي.',
    opts: [
      { label: '✅ نقبل', hint: 'نمو اقتصادي، بس دخل أقل هالسنة', run: (e, n) => { for (const t of e.owned(n.id)) t.gdp *= 1.06; n.treasury -= cash(n, 1); return 'الاستثمار دخل: الناتج +6%'; } },
      { label: '❌ نرفض', hint: 'ما يتغير شي', run: () => 'الشركة راحت لدولة ثانية' },
    ],
    ai: () => 0,
  },
  protest: {
    icon: '📢', title: 'مظاهرات شبابية', text: 'الشباب بالشوارع يطالبون بفرص عمل وتعليم.',
    opts: [
      { label: '🎓 نستثمر بالتعليم', hint: 'تكلفة، وأبحاث واستقرار', run: (e, n) => { const c = cash(n, 2.5); n.treasury -= c; n.research += 40; n.stability = clamp(n.stability + 5, 0, 100); return `مشاريع تعليم (${c} مليار): +40 بحث و +5 استقرار`; } },
      { label: '📺 حملة إعلامية', hint: 'رخيصة، بس تأثيرها قليل', run: (e, n) => { const c = cash(n, 0.5); n.treasury -= c; n.stability = clamp(n.stability + 1, 0, 100); return 'الحملة هدّت الوضع شوي'; } },
    ],
    ai: (e, n) => (n.treasury > cash(n, 4) ? 0 : 1),
  },
  border: {
    icon: '🚨', title: 'حادثة حدودية', text: 'جنود من دولة مجاورة دخلوا حدودك بالغلط.. أو يمكن مو بالغلط!',
    opts: [
      { label: '🕊️ نحلها بهدوء', hint: 'العلاقات تتحسن', run: (e, n) => { n.stability = clamp(n.stability + 2, 0, 100); return 'الحادثة انحلت بالدبلوماسية'; } },
      { label: '🪖 نرد بقوة', hint: 'الجيش يكسب خبرة، والشعب يتحمس', run: (e, n) => { const st = n.place?.[n.capital]; if (st) st.xp = Math.min(100, st.xp + 15); n.stability = clamp(n.stability + 4, 0, 100); return 'الجيش رد بقوة (+خبرة، +4 استقرار)'; } },
    ],
    ai: (e, n) => (n.ai?.pers === 'aggressive' ? 1 : 0),
  },
};

/** شهرياً: أحداث جديدة، وانتهاء القرارات المعلقة */
export function monthlyDecisions(e: Engine) {
  const s = e.s;
  for (const n of Object.values(s.nations)) {
    if (!n.alive) continue;
    if (n.decision && s.day >= n.decision.until) decide(e, n, 0, true);
    if (n.decision || e.rand() > 0.035 || s.day < 60) continue;
    const ids = Object.keys(DECISIONS) as DecisionId[];
    const ev = e.pick(ids);
    if (n.kind === 'bot' || n.aiControl) {
      const r = DECISIONS[ev].opts[DECISIONS[ev].ai(e, n)].run(e, n);
      void r;
      continue;
    }
    n.decision = { id: e.id(), ev, until: s.day + 2 * DAYS_PER_MONTH };
  }
}

export function decide(e: Engine, n: Nation, i: number, timeout = false): CmdResult {
  const d = n.decision;
  if (!d) return { ok: false, msg: 'ما فيه قرار' };
  const def = DECISIONS[d.ev];
  const opt = def.opts[clamp(Math.floor(i), 0, def.opts.length - 1)];
  n.decision = undefined;
  const text = opt.run(e, n);
  if (timeout) e.news(def.icon, `${def.title}: (ما قررت، فالحكومة اختارت) ${text}`, 'event', { to: [n.id] });
  e.recompute(n);
  return { ok: true, msg: `${def.icon} ${text}` };
}

// ---------------- سباق الفضاء ----------------
export const SPACE = [
  { name: '', icon: '', tech: 0, cost: 0, days: 0, pts: 0, desc: '' },
  { name: 'قمر صناعي', icon: '🛰️', tech: 3, cost: 120, days: 300, pts: 150, desc: 'صواريخك أدق، وجواسيسك أنجح' },
  { name: 'الهبوط على القمر', icon: '🌙', tech: 5, cost: 400, days: 540, pts: 500, desc: 'فخر وطني: +10 استقرار' },
  { name: 'مستعمرة على المريخ', icon: '🔴', tech: 6, cost: 900, days: 720, pts: 1200, desc: 'أول دولة توصل تاخذ 800 نقطة زيادة' },
];

export function cmdSpace(e: Engine, n: Nation): CmdResult {
  const next = (n.space ?? 0) + 1;
  const def = SPACE[next];
  if (!def) return { ok: false, msg: 'خلصت سباق الفضاء! 🚀' };
  if (n.q.some((q) => q.type.startsWith('space:'))) return { ok: false, msg: 'المشروع شغال' };
  if (n.tech < def.tech) return { ok: false, msg: `تحتاج تكنولوجيا ${def.tech}` };
  if (n.treasury < def.cost) return { ok: false, msg: 'الخزينة ما تكفي' };
  n.treasury -= def.cost;
  n.q.push({ id: e.id(), kind: 'project', type: 'space:' + next, count: 1, left: def.days, total: def.days, cost: def.cost });
  e.news(def.icon, `${n.name} بدأت مشروع «${def.name}»!`, 'econ', { n: [n.id] });
  return { ok: true, msg: `${def.icon} بدأ مشروع ${def.name}` };
}

export function finishSpace(e: Engine, n: Nation, stage: number) {
  const def = SPACE[stage];
  if (!def) return;
  n.space = Math.max(n.space ?? 0, stage);
  n.bonus += def.pts;
  if (stage === 2) n.stability = clamp(n.stability + 10, 0, 100);
  let extra = '';
  if (stage === 3 && !Object.values(e.s.nations).some((o) => o.id !== n.id && (o.space ?? 0) >= 3)) {
    n.bonus += 800;
    extra = ' وهي أول دولة توصل! (+800 نقطة)';
  }
  e.news(def.icon, `🚀 ${n.name} نجحت في «${def.name}»! +${def.pts} نقطة${extra}`, 'system', { n: [n.id] });
  e.histEvent(def.icon, `${n.name}: ${def.name}`);
}

/** البوتات الغنية تدخل سباق الفضاء */
export function aiSpace(e: Engine, n: Nation) {
  const next = (n.space ?? 0) + 1;
  const def = SPACE[next];
  if (!def || n.tech < def.tech || n.q.some((q) => q.type.startsWith('space:'))) return;
  if (n.treasury > def.cost * (n.ai?.pers === 'economic' ? 2 : 3) && e.rand() < 0.15) cmdSpace(e, n);
}
