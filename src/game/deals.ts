// الصفقات بين الدول، سوق السلاح، القروض، القواعد العسكرية، والمعاهدات (عدم اعتداء، تبعية، إنذار نهائي)
import { CARDS, DAYS_PER_MONTH, HAND_MAX, UNITS, emptyUnits, genMult } from './defs';
import type { Engine } from './engine';
import { addAt, homePort, stationable } from './army';
import type { CardId, CmdResult, Deal, DealSide, DealTerm, Nation, NationId, TerrId, UnitType, Units } from './types';
import { BRANCH_OF, COMBAT_UNITS, UNIT_TYPES } from './types';

const clamp = (x: number, a: number, b: number) => Math.max(a, Math.min(b, x));
export const NAP_MONTHS = 36;
export const TRIBUTE = 0.15; // التابع يدفع 15% من دخله
export const BANK_RATE = 0.2;
export const BANK_MONTHS = 24;

/** الدولة اللي تعطي هذا الجانب ومين ياخذه */
const sides = (d: Deal) => ({ give: { by: d.from, to: d.to, side: d.give }, get: { by: d.to, to: d.from, side: d.get } });

// ---------------- التقييم ----------------
export function terrValue(e: Engine, t: TerrId) {
  const T = e.s.terr[t];
  if (!T) return 0;
  const owner = T.owner ? e.s.nations[T.owner] : null;
  return (T.gdp * 6 + T.pop * 2 + 25) * (owner?.capital === t ? 3 : 1);
}

/** قيمة جانب من الصفقة بالمليار (من وجهة نظر اللي ياخذه) */
export function sideValue(e: Engine, side: DealSide, taker: Nation, giver: Nation): number {
  let v = side.money ?? 0;
  if (side.pay) v += side.pay.amt * side.pay.months * 0.8;
  if (side.units) for (const k of UNIT_TYPES) {
    const c = side.units[k] ?? 0;
    if (c > 0) v += c * e.unitCost(taker, k) * (genMult(giver.gen?.[BRANCH_OF[k]] ?? 1) / genMult(taker.gen?.[BRANCH_OF[k]] ?? 1));
  }
  for (const t of side.terrs ?? []) v += terrValue(e, t);
  v += (side.cards?.length ?? 0) * 35;
  v += (side.research ?? 0) * 0.4;
  return v;
}

/** كم يستفيد البوت من الصفقة (موجب = يقبل) */
export function dealScore(e: Engine, d: Deal, bot: Nation): number {
  const s = e.s;
  const other = s.nations[bot.id === d.to ? d.from : d.to];
  if (!other) return -1e9;
  const iAmTo = bot.id === d.to;
  const gain = sideValue(e, iAmTo ? d.give : d.get, bot, other);
  const loss = sideValue(e, iAmTo ? d.get : d.give, other, bot);
  let score = gain - loss;
  const wealth = Math.max(100, bot.treasury + bot.d.income * 12);
  const ratio = other.d.power / Math.max(1, bot.d.power);
  const r = e.peek(bot.id, other.id);
  for (const t of d.terms) {
    if (t === 'peace') score += r?.war ? (ratio > 1.2 ? 0.4 : ratio < 0.7 ? -0.25 : 0.1) * wealth : 0;
    if (t === 'ally') score += (ratio > 0.5 ? 0.08 : -0.05) * wealth * (bot.ai?.pers === 'aggressive' ? 0.5 : 1);
    if (t === 'trade') score += (bot.ai?.pers === 'economic' ? 0.1 : 0.05) * wealth;
    if (t === 'nap') score += (ratio > 1 ? 0.08 : 0.02) * wealth;
  }
  if (d.vassal) {
    const iBecome = (d.vassal === 'to') === iAmTo;
    if (iBecome) score -= ratio > 3 && r?.war ? 0.2 * wealth : 3 * wealth;
    else score += 0.4 * wealth;
  }
  if (d.base) {
    const iHost = (d.base.host === 'to') === iAmTo;
    score += iHost ? -(0.1 + (ratio > 1 ? 0.15 : 0)) * wealth : 0.05 * wealth;
  }
  if (bot.ai?.grudge === other.id) score -= 0.3 * wealth;
  if (other.trait === 'diplomat') score += 0.05 * wealth;
  if (d.ult) score += ratio > 2 ? 0.3 * wealth : ratio > 1.3 ? 0.1 * wealth : -0.2 * wealth;
  return score - 0.03 * wealth;
}

// ---------------- التحقق والتنفيذ ----------------
/** هل الدولة تقدر تعطي هذا الجانب الحين؟ */
export function canGive(e: Engine, n: Nation, side: DealSide): string | null {
  if ((side.money ?? 0) > Math.max(0, n.treasury)) return `${n.name} ما عندها فلوس كفاية`;
  if (side.units) for (const k of UNIT_TYPES) if ((side.units[k] ?? 0) > n.units[k]) return `${n.name} ما عندها وحدات كفاية`;
  for (const t of side.terrs ?? []) {
    if (e.s.terr[t]?.owner !== n.id) return `${e.tname(t)} مو لـ ${n.name}`;
    if (t === n.capital) return 'ما ينفع تعطي العاصمة';
    if (e.s.battles.some((b) => b.terr === t)) return `${e.tname(t)} فيها معركة`;
  }
  const have = [...n.cards];
  for (const c of side.cards ?? []) {
    const i = have.indexOf(c);
    if (i < 0) return `${n.name} ما عندها البطاقة`;
    have.splice(i, 1);
  }
  if ((side.research ?? 0) > 0 && n.tech <= 1 && n.research < (side.research ?? 0)) return `${n.name} ما عندها أبحاث كفاية`;
  return null;
}

function clean(side: DealSide): DealSide {
  const out: DealSide = {};
  if ((side.money ?? 0) > 0) out.money = Math.round(side.money!);
  if (side.pay && side.pay.amt > 0 && side.pay.months > 0) out.pay = { amt: Math.round(side.pay.amt * 10) / 10, months: clamp(Math.round(side.pay.months), 1, 60) };
  if (side.units) {
    const u: Partial<Units> = {};
    for (const k of UNIT_TYPES) if ((side.units[k] ?? 0) > 0) u[k] = Math.floor(side.units[k]!);
    if (Object.keys(u).length) out.units = u;
  }
  if (side.terrs?.length) out.terrs = [...new Set(side.terrs)].slice(0, 6);
  if (side.cards?.length) out.cards = side.cards.slice(0, HAND_MAX);
  if ((side.research ?? 0) > 0) out.research = Math.round(side.research!);
  return out;
}

export const sideEmpty = (side: DealSide) => !side.money && !side.pay && !side.units && !side.terrs?.length && !side.cards?.length && !side.research;

export function proposeDeal(e: Engine, n: Nation, c: Omit<Deal, 'id' | 'from' | 'day'>): CmdResult {
  const s = e.s;
  const B = s.nations[c.to];
  if (!B?.alive || B.id === n.id) return { ok: false };
  const d: Deal = {
    id: e.id(), from: n.id, to: B.id, day: s.day, give: clean(c.give ?? {}), get: clean(c.get ?? {}),
    terms: [...new Set((c.terms ?? []).filter((t): t is DealTerm => ['peace', 'ally', 'trade', 'nap'].includes(t)))],
    vassal: c.vassal === 'from' || c.vassal === 'to' ? c.vassal : undefined, ult: !!c.ult, counter: c.counter,
  };
  if (c.base && s.terr[c.base.terr]) d.base = { host: c.base.host === 'from' ? 'from' : 'to', terr: c.base.terr };
  if (sideEmpty(d.give) && sideEmpty(d.get) && !d.terms.length && !d.vassal && !d.base) return { ok: false, msg: 'الصفقة فاضية' };
  const why = canGive(e, n, d.give);
  if (why) return { ok: false, msg: why };
  const r = e.peek(n.id, B.id);
  if (r?.war && (d.terms.includes('ally') || d.terms.includes('trade') || d.terms.includes('nap')) && !d.terms.includes('peace')) return { ok: false, msg: 'أنتم في حرب: لازم تحط «سلام» في الصفقة' };
  if (d.terms.includes('peace') && !r?.war) d.terms = d.terms.filter((t) => t !== 'peace');
  if (d.base) {
    const host = d.base.host === 'from' ? n : B;
    if (s.terr[d.base.terr]?.owner !== host.id) return { ok: false, msg: 'القاعدة لازم تكون في أرض الدولة المستضيفة' };
  }
  if (s.deals.filter((x) => x.from === n.id && x.to === B.id).length >= 2) return { ok: false, msg: 'عندك صفقات معلقة مع هذي الدولة' };
  s.deals.push(d);
  B.lastProp = s.day;
  e.news(d.ult ? '📜' : '🤝', `${n.name} ${d.ult ? 'ترسل لك إنذار نهائي!' : 'ترسل لك عرض صفقة'}`, 'diplo', { to: [B.id] });
  if ((B.kind === 'bot' || B.aiControl) && B.ai) B.ai.next = Math.min(B.ai.next, s.day + e.randInt(1, 4));
  return { ok: true, msg: d.ult ? '📜 أرسلت الإنذار' : '🤝 أرسلت العرض' };
}

export function respondDeal(e: Engine, n: Nation, id: number, accept: boolean): CmdResult {
  const s = e.s;
  const d = s.deals.find((x) => x.id === id && x.to === n.id);
  if (!d) return { ok: false, msg: 'العرض انتهى' };
  s.deals = s.deals.filter((x) => x.id !== id);
  const A = s.nations[d.from];
  if (!A?.alive) return { ok: false };
  if (!accept) {
    rejectDeal(e, d);
    return { ok: true };
  }
  const why = canGive(e, A, d.give) ?? canGive(e, n, d.get);
  if (why) return { ok: false, msg: why };
  executeDeal(e, d);
  return { ok: true, msg: '🤝 تمت الصفقة' };
}

export function rejectDeal(e: Engine, d: Deal) {
  const s = e.s;
  const A = s.nations[d.from];
  const B = s.nations[d.to];
  if (!A || !B) return;
  if (d.ult) {
    // رفض الإنذار = حرب، ومعها ذريعة حرب
    if (!e.canHit(A, B)) {
      e.declareWar(A, B, true);
      e.rel(A.id, B.id).cb = { by: A.id, until: s.day + 6 * DAYS_PER_MONTH };
      e.news('📜', `${B.name} رفضت إنذار ${A.name}.. والحرب بدأت! (هجوم ${A.name} أقوى 15% لمدة 6 شهور)`, 'war', { n: [A.id, B.id] });
    } else e.news('📜', `${B.name} رفضت إنذار ${A.name}`, 'diplo', { n: [A.id, B.id] });
    return;
  }
  e.news('❌', `${B.name} رفضت عرض الصفقة من ${A.name}`, 'diplo', { to: [A.id, B.id] });
}

/** تنفيذ الصفقة: كل طرف يعطي اللي عليه */
export function executeDeal(e: Engine, d: Deal) {
  const s = e.s;
  const A = s.nations[d.from];
  const B = s.nations[d.to];
  const parts: string[] = [];
  for (const { by, to, side } of Object.values(sides(d))) {
    const X = s.nations[by];
    const Y = s.nations[to];
    if ((side.money ?? 0) > 0) { X.treasury -= side.money!; Y.treasury += side.money!; parts.push(`${Math.round(side.money!)} مليار`); }
    if (side.pay) {
      s.pays.push({ id: e.id(), from: X.id, to: Y.id, amt: side.pay.amt, left: side.pay.months, why: 'صفقة' });
      parts.push(`${side.pay.amt} مليار شهرياً لمدة ${side.pay.months} شهر`);
    }
    if (side.units) deliverUnits(e, X, Y, side.units);
    for (const t of side.terrs ?? []) { e.transferTerr(s.terr[t], Y.id); s.terr[t].unrest = 4; parts.push(e.tname(t)); }
    for (const c of side.cards ?? []) {
      const i = X.cards.indexOf(c);
      if (i >= 0 && Y.cards.length < HAND_MAX) { X.cards.splice(i, 1); Y.cards.push(c); parts.push(`بطاقة ${CARDS[c].name}`); }
    }
    if ((side.research ?? 0) > 0) { Y.research += side.research!; parts.push(`${side.research} نقطة بحث`); }
  }
  const r = e.rel(A.id, B.id);
  for (const t of d.terms) {
    if (t === 'peace' && r.war) e.makePeace(A, B, 24, true);
    if (t === 'ally') r.ally = Math.max(1, s.day);
    if (t === 'trade') r.trade = Math.max(1, s.day);
    if (t === 'nap') r.nap = s.day + NAP_MONTHS * DAYS_PER_MONTH;
  }
  if (d.vassal) {
    const V = d.vassal === 'from' ? A : B;
    const L = d.vassal === 'from' ? B : A;
    V.lord = L.id;
    delete r.war;
    r.ally = Math.max(1, s.day);
    e.news('👑', `${V.name} صارت دولة تابعة لـ ${L.name} (تدفع ${Math.round(TRIBUTE * 100)}% من دخلها)`, 'diplo', { n: [V.id, L.id] });
  }
  if (d.base) {
    const host = d.base.host === 'from' ? A : B;
    const owner = host.id === A.id ? B : A;
    (s.bases ??= []).push({ id: e.id(), owner: owner.id, host: host.id, terr: d.base.terr });
    e.news('🏰', `${owner.name} صار عندها قاعدة عسكرية في ${e.tname(d.base.terr)} (${host.name})`, 'diplo', { n: [owner.id, host.id], terr: d.base.terr });
  }
  const termNames: Record<DealTerm, string> = { peace: 'سلام', ally: 'تحالف', trade: 'تجارة', nap: 'عدم اعتداء' };
  const all = [...parts, ...d.terms.map((t) => termNames[t])];
  e.news(d.ult ? '📜' : '🤝', `${d.ult ? `${B.name} رضخت لإنذار ${A.name}` : `صفقة بين ${A.name} و ${B.name}`}${all.length ? ': ' + all.slice(0, 6).join('، ') : ''}`, 'diplo', { n: [A.id, B.id] });
  e.recompute(A);
  e.recompute(B);
}

/** الأسلحة تنشحن من عاصمة المعطي لعاصمة الآخذ (تاخذ وقت) */
export function deliverUnits(e: Engine, X: Nation, Y: Nation, units: Partial<Units>, convert = true) {
  const u = emptyUnits();
  for (const k of UNIT_TYPES) {
    const c = clamp(Math.floor(units[k] ?? 0), 0, X.units[k]);
    if (!c) continue;
    X.units[k] -= c;
    // الأسلحة الأحدث تساوي أكثر عند دولة أجيالها أقل
    const ratio = convert ? genMult(X.gen?.[BRANCH_OF[k]] ?? 1) / genMult(Y.gen?.[BRANCH_OF[k]] ?? 1) : 1;
    u[k] = Math.max(1, Math.round(c * ratio));
  }
  e.recompute(X);
  shipTo(e, X, Y, u);
}

function shipTo(e: Engine, X: Nation | null, Y: Nation, u: Units) {
  const s = e.s;
  if (!UNIT_TYPES.some((k) => u[k] > 0)) return;
  const from = X ? X.capital : Y.capital;
  const to = u.ship > 0 ? homePort(e, Y) : Y.capital;
  const days = clamp(Math.round(e.w.centerDist(from, to) / 150) + 5, 5, 60);
  s.moves.push({ id: e.id(), owner: Y.id, from, to, units: u, depart: s.day, arrive: s.day + days, kind: 'deliver' });
}

// ---------------- سوق السلاح ----------------
/** الوحدات اللي تبيعها الدولة (حسب تخصصها) */
export function exportUnits(n: Nation): UnitType[] {
  const out: UnitType[] = [];
  for (const b of n.spec ?? []) {
    if (b === 'land') out.push('tank', 'inf');
    if (b === 'air') out.push('jet');
    if (b === 'sea') out.push('ship');
    if (b === 'rocket') out.push('missile');
  }
  return out;
}

export function marketPrice(e: Engine, seller: Nation, u: UnitType) {
  return e.unitCost(seller, u) * clamp(seller.exp?.markup ?? 1.3, 0.8, 3);
}

export interface Offer { seller: NationId; u: UnitType; price: number; gen: number }
export function marketOffers(e: Engine, buyer: Nation): Offer[] {
  const out: Offer[] = [];
  for (const n of Object.values(e.s.nations)) {
    if (!n.alive || n.id === buyer.id || !n.exp?.open || e.atWar(n.id, buyer.id)) continue;
    for (const u of exportUnits(n)) {
      if (n.tech < UNITS[u].tech) continue;
      out.push({ seller: n.id, u, price: marketPrice(e, n, u), gen: n.gen[BRANCH_OF[u]] });
    }
  }
  return out.sort((a, b) => b.gen - a.gen || a.price - b.price);
}

export function buyArms(e: Engine, buyer: Nation, sellerId: NationId, u: UnitType, count: number): CmdResult {
  const s = e.s;
  const seller = s.nations[sellerId];
  if (!seller?.alive || seller.id === buyer.id) return { ok: false };
  if (!seller.exp?.open) return { ok: false, msg: `${seller.name} وقفت تصدير السلاح` };
  if (e.atWar(seller.id, buyer.id)) return { ok: false, msg: 'ما تشتري من عدوك' };
  if (!exportUnits(seller).includes(u)) return { ok: false, msg: 'ما يبيعون هذا النوع' };
  const n = clamp(Math.floor(count), 1, u === 'inf' ? 100 : 40);
  const price = marketPrice(e, seller, u) * n;
  if (buyer.treasury < price) return { ok: false, msg: 'الخزينة ما تكفي' };
  buyer.treasury -= price;
  seller.treasury += price * 0.6; // ربح التصدير (الباقي تكلفة التصنيع)
  const ratio = genMult(seller.gen[BRANCH_OF[u]]) / genMult(buyer.gen[BRANCH_OF[u]]);
  const got = emptyUnits();
  got[u] = Math.max(1, Math.round(n * ratio));
  shipTo(e, seller, buyer, got);
  e.news('🛒', `${buyer.name} اشترت ${n} ${UNITS[u].name} (جيل ${seller.gen[BRANCH_OF[u]]}) من ${seller.name}`, 'econ', { n: [buyer.id, seller.id] });
  e.recompute(buyer);
  e.recompute(seller);
  return { ok: true, msg: `🛒 الشحنة بالطريق: ${got[u]} ${UNITS[u].name}${got[u] !== n ? ' (بعد فرق الأجيال)' : ''}` };
}

// ---------------- القروض ----------------
export function debtOf(e: Engine, n: Nation) {
  return e.s.pays.filter((p) => p.from === n.id).reduce((a, p) => a + p.amt * p.left, 0);
}
export function loanMax(e: Engine, n: Nation) {
  return Math.max(0, Math.round(Math.max(10, n.d.income) * 12 - debtOf(e, n)));
}
export function takeLoan(e: Engine, n: Nation, amount: number): CmdResult {
  const a = Math.round(amount);
  const max = loanMax(e, n);
  if (a < 5) return { ok: false, msg: 'المبلغ صغير' };
  if (a > max) return { ok: false, msg: `أقصى قرض تقدر تاخذه ${max} مليار` };
  n.treasury += a;
  e.s.pays.push({ id: e.id(), from: n.id, to: '', amt: Math.round((a * (1 + BANK_RATE) / BANK_MONTHS) * 10) / 10, left: BANK_MONTHS, why: 'البنك الدولي' });
  return { ok: true, msg: `🏦 أخذت قرض ${a} مليار، تسدده على ${BANK_MONTHS} شهر` };
}

/** شهرياً: الدفعات والجزية */
export function monthlyPays(e: Engine) {
  const s = e.s;
  for (const p of s.pays) {
    const X = s.nations[p.from];
    const Y = p.to ? s.nations[p.to] : null;
    if (!X?.alive || (p.to && !Y?.alive)) { p.left = 0; continue; }
    X.treasury -= p.amt;
    if (Y) Y.treasury += p.amt;
    p.left--;
    if (X.treasury < 0 && Y?.ai && Y.kind === 'bot' && e.rand() < 0.15) Y.ai.grudge = X.id;
  }
  s.pays = s.pays.filter((p) => p.left > 0);
  // الدول التابعة تدفع جزية
  for (const n of Object.values(s.nations)) {
    if (!n.alive || !n.lord) continue;
    const L = s.nations[n.lord];
    if (!L?.alive) { delete n.lord; continue; }
    const x = Math.max(0, n.d.income * TRIBUTE);
    n.treasury -= x;
    L.treasury += x;
  }
  // الصفقات القديمة تنتهي (والإنذار المتجاهل = رفض)
  for (const d of [...s.deals]) {
    const B = s.nations[d.to];
    if (!s.nations[d.from]?.alive || !B?.alive) { s.deals = s.deals.filter((x) => x.id !== d.id); continue; }
    if (s.day - d.day > (d.ult ? 30 : 60)) {
      s.deals = s.deals.filter((x) => x.id !== d.id);
      if (d.ult) rejectDeal(e, d);
    }
  }
}

// ---------------- القواعد والمعاهدات ----------------
export function closeBase(e: Engine, id: number, quiet = false) {
  const s = e.s;
  const b = s.bases?.find((x) => x.id === id);
  if (!b) return;
  s.bases = s.bases!.filter((x) => x.id !== id);
  const O = s.nations[b.owner];
  if (O?.alive && O.place?.[b.terr]) {
    // الجيش يرجع للوطن
    const st = O.place[b.terr];
    delete O.place[b.terr];
    for (const k of COMBAT_UNITS) O.units[k] -= st.u[k];
    s.moves.push({ id: e.id(), owner: O.id, from: b.terr, to: O.capital, units: { ...st.u }, depart: s.day, arrive: s.day + 15, kind: 'return', xp: st.xp });
    e.recompute(O);
  }
  if (!quiet && O) e.news('🏰', `انقفلت قاعدة ${O.name} في ${e.tname(b.terr)}`, 'diplo', { n: [b.owner, b.host] });
}

export function cmdCloseBase(e: Engine, n: Nation, id: number): CmdResult {
  const b = e.s.bases?.find((x) => x.id === id);
  if (!b || (b.host !== n.id && b.owner !== n.id)) return { ok: false };
  closeBase(e, id);
  return { ok: true, msg: '🏰 انقفلت القاعدة' };
}

/** الحرب تقفل القواعد بين الطرفين */
export function onWar(e: Engine, a: NationId, b: NationId) {
  for (const x of [...(e.s.bases ?? [])]) if ((x.owner === a && x.host === b) || (x.owner === b && x.host === a)) closeBase(e, x.id);
  const A = e.s.nations[a], B = e.s.nations[b];
  if (A?.lord === b) delete A.lord;
  if (B?.lord === a) delete B.lord;
}

export function breakNap(e: Engine, n: Nation, other: NationId): CmdResult {
  const r = e.peek(n.id, other);
  if (!r?.nap || r.nap <= e.s.day) return { ok: false, msg: 'ما فيه معاهدة' };
  delete r.nap;
  n.stability = clamp(n.stability - 15, 0, 100);
  const O = e.s.nations[other];
  if (O?.ai && O.kind === 'bot') O.ai.grudge = n.id;
  e.news('💔', `${n.name} نقضت معاهدة عدم الاعتداء مع ${O?.name}!`, 'diplo', { n: [n.id, other] });
  return { ok: true, msg: 'نقضت المعاهدة (الاستقرار -15)' };
}

export function independence(e: Engine, n: Nation): CmdResult {
  if (!n.lord) return { ok: false, msg: 'أنت مو دولة تابعة' };
  const L = e.s.nations[n.lord];
  delete n.lord;
  if (L?.alive) {
    const r = e.rel(n.id, L.id);
    delete r.ally;
    if (!r.team) e.declareWar(L, n, true);
    e.news('✊', `${n.name} أعلنت استقلالها عن ${L.name}! والحرب بدأت`, 'war', { n: [n.id, L.id] });
  }
  n.stability = clamp(n.stability + 10, 0, 100);
  return { ok: true, msg: '✊ أعلنت الاستقلال' };
}

// ---------------- البوتات ----------------
export function aiDeals(e: Engine, n: Nation) {
  const s = e.s;
  // الرد على العروض
  for (const d of s.deals.filter((x) => x.to === n.id)) {
    const why = canGive(e, n, d.get) ?? (s.nations[d.from] ? canGive(e, s.nations[d.from], d.give) : 'x');
    const sc = why ? -1e9 : dealScore(e, d, n);
    if (sc >= 0) respondDeal(e, n, d.id, true);
    else {
      const A = s.nations[d.from];
      respondDeal(e, n, d.id, false);
      // عرض مضاد: نطلب فلوس زيادة لو الفرق معقول
      const gap = -sc;
      if (A?.alive && !why && !d.ult && !d.counter && gap < Math.max(150, A.treasury) && e.rand() < 0.6 && !d.vassal) {
        proposeDeal(e, n, { to: A.id, give: d.get, get: { ...d.give, money: Math.round((d.give.money ?? 0) + gap * 1.15) }, terms: d.terms, base: d.base ? { host: d.base.host === 'from' ? 'to' : 'from', terr: d.base.terr } : undefined, counter: d.id });
      }
    }
  }
  const pers = n.ai?.pers ?? 'balanced';
  // سوق السلاح: لو في خطر وعنده فلوس
  if (e.enemies(n.id).length && n.treasury > 120 && e.rand() < 0.2) {
    const offers = marketOffers(e, n).filter((o) => o.gen > n.gen[BRANCH_OF[o.u]] && o.u !== 'inf');
    const o = offers[0];
    if (o) buyArms(e, n, o.seller, o.u, Math.min(10, Math.floor((n.treasury * 0.25) / o.price)));
  }
  // قرض لو مفلس
  if (n.treasury < -20 && !s.pays.some((p) => p.from === n.id && !p.to) && e.rand() < 0.5) takeLoan(e, n, Math.min(loanMax(e, n), -n.treasury + 30));
  // سلام مقابل فلوس لو خسران
  for (const id of e.enemies(n.id)) {
    const O = s.nations[id];
    if (O.d.power > n.d.power * 1.5 && n.treasury > 50 && e.rand() < 0.08 && !s.deals.some((d) => d.from === n.id && d.to === id)) {
      proposeDeal(e, n, { to: id, give: { money: Math.round(n.treasury * 0.3) }, get: {}, terms: ['peace'] });
    }
  }
  // معاهدة عدم اعتداء مع جار قوي
  if (pers === 'defensive' || pers === 'economic') {
    if (e.rand() < 0.03) {
      const near = Object.values(s.nations).filter((o) => o.alive && o.id !== n.id && !e.atWar(n.id, o.id) && !e.peek(n.id, o.id)?.nap && o.d.power > n.d.power && (o.kind === 'bot' || s.day - (o.lastProp ?? -9999) > 150));
      if (near.length) proposeDeal(e, n, { to: e.pick(near).id, give: {}, get: {}, terms: ['nap'] });
    }
  }
  // إنذار نهائي لجار ضعيف (العدوانيين)
  if (pers === 'aggressive' && e.rand() < 0.02) {
    const weak = Object.values(s.nations).filter((o) => o.alive && o.id !== n.id && !e.canHit(n, o) && o.d.power * 2.5 < n.d.power && (o.kind === 'bot' || s.day - (o.lastProp ?? -9999) > 200));
    const o = weak.length ? e.pick(weak) : null;
    if (o) {
      const t = e.owned(o.id).filter((x) => x.id !== o.capital && e.w.get(x.id).n.some((y) => s.terr[y]?.owner === n.id))[0];
      const get: DealSide = t ? { terrs: [t.id] } : { money: Math.round(Math.max(30, o.treasury * 0.4)) };
      proposeDeal(e, n, { to: o.id, give: {}, get, terms: [], ult: true });
    }
  }
  // تبيع بطاقة؟ لا. التصدير: البوتات سعرها حسب شخصيتها
  if (n.exp) n.exp.markup = pers === 'economic' ? 1.2 : pers === 'aggressive' ? 1.5 : 1.35;
}

/** وصف الصفقة بالعربي */
export function sideText(e: Engine, side: DealSide): string[] {
  const out: string[] = [];
  if (side.money) out.push(`💰 ${side.money} مليار`);
  if (side.pay) out.push(`📆 ${side.pay.amt} مليار شهرياً × ${side.pay.months} شهر`);
  if (side.units) for (const k of UNIT_TYPES) if (side.units[k]) out.push(`${UNITS[k].icon === 'tank' ? '🛞' : UNITS[k].icon} ${side.units[k]} ${UNITS[k].name}`);
  for (const t of side.terrs ?? []) out.push(`🗺️ ${e.tname(t)}`);
  for (const c of side.cards ?? []) out.push(`🃏 ${CARDS[c as CardId].name}`);
  if (side.research) out.push(`🧪 ${side.research} نقطة بحث`);
  return out;
}

export { stationable as dealStationable, addAt as dealAddAt };
