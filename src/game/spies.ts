// الاستخبارات: تجنيد الجواسيس وعملياتهم (كشف أسرار، سرقة، تخريب، فتنة)
import { BUILDINGS, MAX_AGENTS_BASE, MAX_TECH, SPY_OPS, TECH_COST, agentCost } from './defs';
import type { Engine } from './engine';
import type { BuildingType, CmdResult, Nation, NationId, SpyOp, SpyOpId } from './types';

const clamp = (x: number, a: number, b: number) => Math.max(a, Math.min(b, x));

export const maxAgents = (n: Nation) => MAX_AGENTS_BASE + (n.b.intel ?? 0);
export const busyAgents = (e: Engine, n: Nation) => e.s.ops.filter((o) => o.owner === n.id).length;

/** هل عندك معلومات استخباراتية عن الدولة الحين؟ */
export const hasIntel = (e: Engine, me: Nation | undefined, id: NationId) => !!me && (me.intel?.[id] ?? 0) > e.s.day;

/** احتمال نجاح العملية */
export function spyChance(A: Nation, T: Nation, op: SpyOpId): number {
  let p = SPY_OPS[op].base + 0.05 * (A.b.intel ?? 0) - 0.06 * (T.b.intel ?? 0) + 0.03 * (A.tech - T.tech);
  if (A.trait === 'diplomat') p += 0.05;
  if (T.trait === 'guardian') p -= 0.05;
  if ((A.space ?? 0) >= 1) p += 0.08;
  return clamp(p, 0.1, 0.92);
}

export function recruitAgent(e: Engine, n: Nation): CmdResult {
  if (n.agents + busyAgents(e, n) >= maxAgents(n)) return { ok: false, msg: 'وصلت للحد الأقصى من الجواسيس، ابنِ «جهاز الاستخبارات» عشان تزيدهم' };
  const cost = agentCost(n.d.gdp);
  if (n.treasury < cost) return { ok: false, msg: 'الخزينة ما تكفي' };
  n.treasury -= cost;
  n.agents++;
  return { ok: true, msg: '🕵️ جندت جاسوس جديد' };
}

export function startOp(e: Engine, n: Nation, op: SpyOpId, targetId: NationId): CmdResult {
  const s = e.s;
  const T = s.nations[targetId];
  if (!T?.alive || T.id === n.id || !SPY_OPS[op]) return { ok: false };
  if (n.team && T.team === n.team) return { ok: false, msg: 'ما تتجسس على فريقك!' };
  if (n.agents < 1) return { ok: false, msg: 'ما عندك جواسيس جاهزين' };
  if (s.ops.some((o) => o.owner === n.id && o.target === T.id)) return { ok: false, msg: 'عندك عملية شغالة ضد هذي الدولة' };
  const cost = SPY_OPS[op].cost;
  if (n.treasury < cost) return { ok: false, msg: 'الخزينة ما تكفي' };
  n.treasury -= cost;
  n.agents--;
  const days = SPY_OPS[op].days + e.randInt(0, 6);
  s.ops.push({ id: e.id(), owner: n.id, target: T.id, op, start: s.day, done: s.day + days });
  return { ok: true, msg: `🕵️ الجاسوس انطلق لـ ${T.name}، النتيجة بعد ${days} يوم تقريباً` };
}

/** يومياً: نشوف العمليات اللي خلصت */
export function tickOps(e: Engine) {
  const s = e.s;
  if (!s.ops.length) return;
  const due = s.ops.filter((o) => o.done <= s.day);
  if (!due.length) return;
  s.ops = s.ops.filter((o) => o.done > s.day);
  for (const o of due) resolveOp(e, o);
}

function grudge(e: Engine, T: Nation, A: Nation, p: number) {
  if (!T.ai || T.kind !== 'bot' || (T.team && T.team === A.team) || e.allied(T.id, A.id)) return;
  if (e.rand() < p) T.ai.grudge = A.id;
}

function resolveOp(e: Engine, o: SpyOp) {
  const s = e.s;
  const A = s.nations[o.owner];
  const T = s.nations[o.target];
  if (!A?.alive) return;
  if (!T?.alive) { A.agents++; return; }
  const def = SPY_OPS[o.op];
  if (e.rand() >= spyChance(A, T, o.op)) {
    const caught = e.rand() < 0.55 + 0.05 * (T.b.intel ?? 0);
    if (caught) {
      e.news('🕵️', `القبض على جاسوس من ${A.name} في ${T.name}! كان يحاول «${def.name}»`, 'diplo', { n: [A.id, T.id] });
      T.stability = clamp(T.stability + 3, 0, 100);
      const r = e.peek(A.id, T.id);
      if (r?.trade && e.rand() < 0.5) {
        delete r.trade;
        e.news('📦', `${T.name} ألغت التجارة مع ${A.name} بعد فضيحة التجسس`, 'diplo', { n: [A.id, T.id] });
      }
      grudge(e, T, A, 0.5);
    } else {
      A.agents++;
      e.news('🕵️', `عملية «${def.name}» ضد ${T.name} فشلت، بس الجاسوس رجع سالم`, 'diplo', { to: [A.id] });
    }
    return;
  }
  A.agents++;
  let text = '';
  let victim = '';
  switch (o.op) {
    case 'reveal':
      A.intel[T.id] = s.day + 360;
      text = `انكشفت أسرار ${T.name}: مهمتها السرية وبطاقاتها وجيشها (لمدة سنة)`;
      break;
    case 'tech': {
      if (A.tech >= MAX_TECH) {
        const x = Math.round(Math.max(20, T.d.income * 2));
        A.treasury += x;
        text = `ما فيه شي نتعلمه من ${T.name}، فبعنا الأبحاث بـ ${x} مليار`;
      } else {
        const next = TECH_COST[A.tech + 1];
        const k = T.tech > A.tech ? 0.6 : T.tech === A.tech ? 0.35 : 0.15;
        const pts = Math.round(Math.max(30, next * k));
        A.research += pts;
        text = `سرقنا أبحاث من ${T.name}: +${pts} نقطة بحث`;
      }
      victim = 'جواسيس سرقوا أبحاث من مختبراتك!';
      break;
    }
    case 'money': {
      const x = Math.min(300, Math.round(Math.max(0, T.treasury) * 0.1));
      T.treasury -= x;
      A.treasury += x;
      text = `سرقنا ${x} مليار من خزينة ${T.name}`;
      victim = `اختفى ${x} مليار من خزينتك!`;
      break;
    }
    case 'sabotage': {
      const opts = (['industry', 'research', 'milfac', 'fort', 'airdef', 'infra'] as BuildingType[]).filter((b) => T.b[b] > 0);
      if (opts.length) {
        const b = e.pick(opts);
        T.b[b]--;
        text = `خربنا ${BUILDINGS[b].name} في ${T.name} (نزلت مستوى)`;
        victim = `تخريب! ${BUILDINGS[b].name} نزلت مستوى`;
      } else {
        const x = Math.round(Math.max(0, T.treasury) * 0.08);
        T.treasury -= x;
        text = `ما لقينا مصانع نخربها، بس كبّدنا ${T.name} خسائر ${x} مليار`;
        victim = `تخريب في منشآتك! خسرت ${x} مليار`;
      }
      for (const q of T.bq) q.left += 20;
      break;
    }
    case 'revolt': {
      T.stability = clamp(T.stability - 18, 0, 100);
      const occ = e.owned(T.id).filter((t) => t.id !== T.capital && (t.unrest > 0 || e.w.parentOf(t.id) !== T.home));
      if (T.stability < 40 && occ.length && e.rand() < 0.6) {
        const t = e.pick(occ);
        e.revolt(t, T);
        text = `الفتنة نجحت! ${e.tname(t.id)} ثارت على ${T.name}`;
      } else text = `أشعلنا الفتنة في ${T.name}: استقرارها -18`;
      victim = 'مظاهرات واضطرابات بتحريض خارجي! الاستقرار -18';
      break;
    }
  }
  e.news(def.icon, `🕵️ ${text}`, 'diplo', { to: [A.id] });
  if (victim) {
    const exposed = e.rand() < 0.25 + 0.06 * (T.b.intel ?? 0);
    e.news('🕵️', `${victim}${exposed ? ` المخابرات كشفت إن ${A.name} وراها` : ' (المنفذ مجهول)'}`, 'event', { to: [T.id] });
    if (exposed) grudge(e, T, A, 0.6);
  }
  e.recompute(A);
  e.recompute(T);
}

/** البوتات: تجند جواسيس وتنفذ عمليات أحياناً */
export function aiSpy(e: Engine, n: Nation, atWar: NationId[]) {
  const s = e.s;
  const pers = n.ai?.pers ?? 'balanced';
  if (n.agents + busyAgents(e, n) < maxAgents(n) && n.treasury > agentCost(n.d.gdp) * 4 && e.rand() < (pers === 'economic' ? 0.12 : 0.25)) {
    recruitAgent(e, n);
  }
  if (n.agents < 1 || e.rand() > (pers === 'aggressive' ? 0.3 : 0.18)) return;
  const alive = Object.values(s.nations).filter((x) => x.alive && x.id !== n.id && !(n.team && x.team === n.team) && !e.allied(n.id, x.id));
  if (!alive.length) return;
  const leader = [...alive].sort((a, b) => b.d.score - a.d.score)[0];
  const target =
    (n.ai?.grudge && s.nations[n.ai.grudge]?.alive ? s.nations[n.ai.grudge] : null) ??
    (atWar.length ? s.nations[e.pick(atWar)] : null) ??
    (leader.d.score > n.d.score * 1.2 ? leader : null);
  if (!target || (target.team && target.team === n.team)) return;
  let op: SpyOpId;
  if (target.tech > n.tech) op = 'tech';
  else if (target.stability < 45) op = 'revolt';
  else if (e.atWar(n.id, target.id)) op = e.rand() < 0.5 ? 'sabotage' : 'revolt';
  else op = e.pick(['money', 'sabotage', 'reveal'] as SpyOpId[]);
  if (n.treasury < SPY_OPS[op].cost * 2) return;
  startOp(e, n, op, target.id);
}
