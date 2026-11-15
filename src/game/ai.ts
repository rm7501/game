// ذكاء البوتات (وأيضاً يلعب عن اللاعب اللي فصل)
import { BUILDINGS, NUKE_PROJECT, SHIP_CAPACITY, UNITS, emptyUnits, missileRange } from './defs';
import { estimate } from './battle';
import type { Engine } from './engine';
import { spinFortune } from './events';
import { aiCards } from './cards';
import { aiSpy } from './spies';
import { aiVote } from './un';
import type { BuildingType, Nation, Personality, Proposal, TerrId, UnitType, Units } from './types';
import { COMBAT_UNITS } from './types';

const PRIORITY: Record<Personality, Partial<Record<BuildingType, number>>> = {
  economic: { industry: 6, research: 4, infra: 3, mining: 3, health: 2, fort: 1, airdef: 1, milfac: 1, intel: 0.5 },
  aggressive: { milfac: 5, industry: 5, research: 3, infra: 2, fort: 1, mining: 2, health: 1, airdef: 1, intel: 1.5 },
  defensive: { fort: 5, industry: 5, airdef: 3, research: 3, health: 2, mining: 2, infra: 1, milfac: 1, intel: 1.5 },
  balanced: { industry: 6, research: 4, infra: 2, fort: 2, milfac: 2, mining: 2, health: 2, airdef: 1, intel: 1 },
};

export function aiRespond(e: Engine, n: Nation, p: Proposal) {
  const s = e.s;
  const from = s.nations[p.from];
  s.props = s.props.filter((x) => x.id !== p.id);
  if (!from?.alive) return;
  const pers = n.ai?.pers ?? 'balanced';
  const grudge = n.ai?.grudge === from.id;
  const charm = from.trait === 'diplomat' ? 0.25 : 0;
  let accept = false;
  if (p.type === 'trade') accept = !grudge && e.rand() < 0.75 + charm;
  else if (p.type === 'ally') {
    const base = pers === 'defensive' ? 0.45 : pers === 'aggressive' ? 0.15 : 0.3;
    const strong = from.d.power > n.d.power * 0.7 ? 0.15 : 0;
    accept = !grudge && e.rand() < base + strong + charm;
  } else if (p.type === 'peace') {
    const r = e.peek(n.id, from.id);
    const enemyStronger = from.d.power > n.d.power * 1.1;
    const long = r?.war !== undefined && s.day - r.war > 240;
    accept = !grudge && (enemyStronger || n.stability < 35 || (long && e.rand() < 0.5) || (pers !== 'aggressive' && e.rand() < 0.3 + charm));
  }
  if (accept) {
    e.acceptProposal(p);
  } else {
    const names = { ally: 'طلب التحالف', trade: 'الاتفاقية التجارية', peace: 'طلب السلام' };
    e.news('❌', `${n.name} رفضت ${names[p.type]} من ${from.name}`, 'diplo', { to: [from.id] });
  }
}

function recruit(e: Engine, n: Nation, u: UnitType, budget: number): number {
  const cost = e.unitCost(n, u);
  let cnt = Math.floor(budget / cost);
  if (u === 'inf') cnt = Math.min(cnt, 40);
  else cnt = Math.min(cnt, 20);
  const man = UNITS[u].man;
  if (man > 0) cnt = Math.min(cnt, Math.floor(n.d.manpower / man));
  if (cnt < 1) return 0;
  const r = e.command(n.id, { t: 'recruit', u, n: cnt });
  return r.ok ? cost * cnt : 0;
}

export function aiThink(e: Engine, n: Nation) {
  const s = e.s;
  const ai = n.ai!;
  const pers = ai.pers;
  const diff = n.kind === 'bot' ? s.settings.difficulty : 'normal';
  e.recompute(n);

  // الرد على الاقتراحات
  for (const p of s.props.filter((x) => x.to === n.id)) aiRespond(e, n, p);

  // عجلة الحظ
  if (s.day >= n.fortuneNext) spinFortune(e, n);

  // التصويت في الأمم المتحدة
  if (s.un && !s.un.votes[n.id]) s.un.votes[n.id] = aiVote(e, n, s.un);

  // الضرائب
  let tax = { aggressive: 0.25, balanced: 0.22, economic: 0.2, defensive: 0.22 }[pers];
  if (n.stability < 35) tax = 0.14;
  else if (n.treasury < 0) tax = 0.3;
  n.tax = tax;
  if (diff === 'hard') n.treasury += Math.max(0, n.d.income) * 0.15;
  if (diff === 'easy') n.treasury -= Math.max(0, n.d.income) * 0.1;

  // تقدير الخطر
  const myTerrs = e.owned(n.id);
  const neighborNations = new Set<string>();
  for (const t of myTerrs) for (const nb of e.w.get(t.id).n) {
    const o = s.terr[nb]?.owner;
    if (o && o !== n.id) neighborNations.add(o);
  }
  let threat = 0;
  for (const id of neighborNations) {
    const o = s.nations[id];
    if (!o?.alive || e.allied(n.id, id)) continue;
    threat = Math.max(threat, o.d.power * (e.atWar(n.id, id) ? 1.5 : 1));
  }
  const atWar = e.enemies(n.id);

  // الميزانية
  const reserve = Math.max(4, n.d.upkeep * 3);
  let budget = Math.max(0, n.treasury - reserve);
  const milShare0 = { aggressive: 0.65, balanced: 0.5, economic: 0.3, defensive: 0.45 }[pers];
  const danger = n.d.power < threat * (pers === 'defensive' ? 1.3 : 1) || atWar.length > 0;
  const milShare = danger ? Math.min(0.85, milShare0 + 0.25) : milShare0;
  let econBudget = budget * (1 - milShare);
  const milBudget = budget * milShare;

  // البناء
  const par = 2 + (n.gov === 'planned' ? 1 : 0);
  if (n.bq.length < par && n.d.used < n.d.slots && econBudget > 1) {
    const prio = { ...PRIORITY[pers] };
    if (n.stability < 40) prio.health = 8;
    if (n.res === 'none') prio.mining = 0;
    const enemyMissiles = atWar.some((id) => s.nations[id].units.missile > 2);
    if (enemyMissiles) prio.airdef = 6;
    let best: BuildingType | null = null;
    let bs = -1;
    for (const [b, w] of Object.entries(prio) as [BuildingType, number][]) {
      if (!w) continue;
      const lvl = n.b[b] + n.bq.filter((q) => q.type === b).length;
      const sc = w / (1 + lvl * 0.9) + e.rand() * 0.4;
      if (sc > bs) { bs = sc; best = b; }
    }
    if (best) {
      const cost = e.buildCost(n, best);
      if (cost <= econBudget && BUILDINGS[best]) {
        const r = e.command(n.id, { t: 'build', b: best });
        if (r.ok) econBudget -= cost;
      }
    }
  }

  // برنامج نووي
  if (!n.nukeProg && n.tech >= NUKE_PROJECT.tech && diff !== 'easy' && pers !== 'economic' && n.treasury > NUKE_PROJECT.cost * 2.5 && e.rand() < 0.15) {
    e.command(n.id, { t: 'project', p: 'nuke' });
  }

  // التجنيد
  let mb = milBudget + (danger ? 0 : 0);
  const unitOrders = n.q.filter((q) => q.kind === 'unit').length;
  if (mb > 1.5 && unitOrders < 4) {
    const island = myTerrs.every((t) => e.w.get(t.id).n.every((x) => s.terr[x]?.owner === n.id));
    const mix: [UnitType, number][] = [];
    if (n.tech >= 2) mix.push(['tank', 0.4], ['inf', 0.25], ['jet', 0.2]);
    else mix.push(['tank', 0.5], ['inf', 0.4]);
    if (island || myTerrs.some((t) => !e.w.get(t.id).n.length)) mix.push(['ship', 0.25]);
    else if (e.rand() < 0.2) mix.push(['ship', 0.1]);
    if (n.tech >= 2 && (atWar.length || pers === 'aggressive')) mix.push(['missile', 0.12]);
    if (n.nukeProg && n.tech >= 3 && diff === 'hard' && n.units.nuke < 2 && n.treasury > 400 && e.rand() < 0.1 && !((s.mods.nukeBan ?? 0) > s.day)) mix.push(['nuke', 0.3]);
    const tot = mix.reduce((a, b) => a + b[1], 0);
    for (const [u, w] of mix) {
      if (n.tech < UNITS[u].tech && u !== 'nuke') continue;
      mb -= recruit(e, n, u, (milBudget * w) / tot);
    }
  }

  // البطاقات والجواسيس
  aiCards(e, n, atWar, danger);
  aiSpy(e, n, atWar);

  // الهجوم
  const myMoves = s.moves.filter((m) => m.owner === n.id && m.kind === 'attack').length;
  if (myMoves < (pers === 'aggressive' ? 2 : 1) && s.day >= (ai.cool ?? 0)) planAttack(e, n, diff, pers);

  // الصواريخ
  if (n.units.missile > 0 && atWar.length && e.rand() < 0.5) {
    const targets: TerrId[] = [];
    for (const id of atWar) for (const t of e.owned(id)) if (e.strikeRange(n, t.id) <= missileRange(n.tech)) targets.push(t.id);
    if (targets.length) {
      const t = targets.sort((a, b) => (s.terr[b].owner && s.nations[s.terr[b].owner].capital === b ? 1 : 0) - (s.terr[a].owner && s.nations[s.terr[a].owner].capital === a ? 1 : 0))[0];
      e.command(n.id, { t: 'strike', to: t, kind: 'missile', n: Math.min(n.units.missile, 1 + Math.floor(e.rand() * 4)) });
    }
  }

  // النووي
  if (n.units.nuke > 0 && atWar.length && diff !== 'easy' && !((s.mods.nukeBan ?? 0) > s.day)) {
    const enemy = atWar.map((id) => s.nations[id]).sort((a, b) => b.d.power - a.d.power)[0];
    const desperate = enemy.d.power > n.d.power * 1.5 || ai.grudge === enemy.id;
    const p = diff === 'hard' ? 0.12 : 0.04;
    if (desperate && e.rand() < p) e.command(n.id, { t: 'strike', to: enemy.capital, kind: 'nuke', n: 1 });
  }

  // دبلوماسية
  diplomacy(e, n, neighborNations, atWar);
}

function planAttack(e: Engine, n: Nation, diff: string, pers: Personality) {
  const s = e.s;
  const commit = { aggressive: 0.7, balanced: 0.6, economic: 0.5, defensive: 0.45 }[pers];
  // أقل فرصة فوز يقبل فيها البوت يهاجم
  let pThr = { aggressive: 0.62, balanced: 0.74, economic: 0.84, defensive: 0.87 }[pers];
  if (diff === 'easy') pThr += 0.08;
  if (diff === 'hard') pThr -= 0.07;
  const cands = new Set<TerrId>();
  for (const t of e.owned(n.id)) {
    const m = e.w.get(t.id);
    for (const x of m.n) if (s.terr[x] && s.terr[x].owner !== n.id) cands.add(x);
    if (n.units.ship >= 2 && m.c) for (const x of Object.keys(m.s)) if (s.terr[x] && s.terr[x].owner !== n.id) cands.add(x);
  }
  let best: { to: TerrId; units: Units; score: number } | null = null;
  const already = new Set([...s.moves.filter((m) => m.owner === n.id).map((m) => m.to), ...s.battles.map((b) => b.terr)]);
  const noNeutrals = ![...cands].some((x) => s.terr[x].owner === '');
  let checked = 0;
  for (const to of cands) {
    if (already.has(to) || checked > 14) continue;
    const T = s.terr[to];
    if (T.owner) {
      const D = s.nations[T.owner];
      if (e.canHit(n, D)) continue;
      const war = e.atWar(n.id, D.id);
      const grudge = n.ai?.grudge === D.id;
      if (!war && !grudge) {
        // إعلان حرب جديدة: العدوانيين أكثر، والباقين أحياناً لو الفرصة حلوة
        const p = { aggressive: 0.8, balanced: 0.3, economic: 0.1, defensive: 0.08 }[pers] * (noNeutrals ? 2 : 1);
        if (e.rand() > p) continue;
        if (D.d.power > n.d.power * 1.05) continue;
        if (e.allies(D.id).length && e.rand() < 0.5) continue;
      }
    }
    const route = e.route(n, to);
    if (!route) continue;
    const units = emptyUnits();
    for (const k of COMBAT_UNITS) units[k] = Math.floor(n.units[k] * commit);
    if (route.naval) {
      const cap = units.ship * SHIP_CAPACITY;
      if (cap < 2) continue;
      const land = units.inf + units.tank;
      if (land > cap) {
        const f = cap / land;
        units.inf = Math.floor(units.inf * f);
        units.tank = Math.floor(units.tank * f);
      }
    }
    if (units.inf + units.tank < 1) continue;
    checked++;
    let est = estimate(e, n, units, to, 10);
    if (est.p < pThr || est.aLoss > 0.55) continue;
    // نرسل اللي يكفي بس لو الفوز مضمون
    if (est.p >= 0.99 && est.aLoss < 0.2) {
      const small = { ...units };
      for (const k of COMBAT_UNITS) small[k] = Math.ceil(units[k] * 0.6);
      if (route.naval) small.ship = Math.max(small.ship, Math.ceil((small.inf + small.tank) / SHIP_CAPACITY));
      const est2 = estimate(e, n, small, to, 10);
      if (est2.p >= Math.min(0.97, pThr + 0.15)) { Object.assign(units, small); est = est2; }
    }
    const mt = e.w.get(to);
    let value = T.gdp / 40 + T.pop / 4 + mt.area / 150000 + 2;
    if (T.owner) value *= n.ai?.grudge === T.owner ? 2.5 : 1.3;
    const sc = (value * est.p * (1 - est.aLoss * 0.5)) / (route.naval ? 1.5 : 1);
    if (!best || sc > best.score) best = { to, units, score: sc };
  }
  if (best) e.command(n.id, { t: 'attack', to: best.to, units: best.units });
}

function diplomacy(e: Engine, n: Nation, neighbors: Set<string>, atWar: string[]) {
  const s = e.s;
  // طلب سلام لو خسران
  for (const id of atWar) {
    const o = s.nations[id];
    const r = e.peek(n.id, id);
    if (!r?.war) continue;
    const losing = o.d.power > n.d.power * 1.3;
    if ((losing || n.stability < 30) && s.day - r.war > 120 && e.rand() < 0.25) {
      e.command(n.id, { t: 'propose', to: id, type: 'peace' });
    }
  }
  if (e.rand() < 0.06) {
    const asked = (n.ai!.asked ??= {});
    // اللاعبين الحقيقيين: ما نرسل لهم اقتراح إذا وصلهم واحد قبل أقل من 5 شهور
    const others = Object.values(s.nations).filter(
      (o) =>
        o.alive && o.id !== n.id && !e.atWar(n.id, o.id) && !e.trading(n.id, o.id) && s.day - (asked[o.id] ?? -9999) > 360 &&
        (o.kind === 'bot' || s.day - (o.lastProp ?? -9999) > 150),
    );
    if (others.length) {
      const o = e.pick(others);
      asked[o.id] = s.day;
      e.command(n.id, { t: 'propose', to: o.id, type: 'trade' });
    }
  }
  if (e.rand() < 0.02 && n.ai?.pers !== 'aggressive') {
    const near = [...neighbors]
      .map((id) => s.nations[id])
      .filter((o) => o?.alive && !e.atWar(n.id, o.id) && !e.allied(n.id, o.id) && (o.kind === 'bot' || s.day - (o.lastProp ?? -9999) > 150));
    if (near.length) e.command(n.id, { t: 'propose', to: e.pick(near).id, type: 'ally' });
  }
  // خيانة: فسخ التحالف مع حليف ضعيف مجاور
  if ((n.ai?.pers === 'aggressive' || n.ai?.pers === 'balanced') && e.rand() < 0.015) {
    const weak = e.allies(n.id).map((id) => s.nations[id]).filter((o) => neighbors.has(o.id) && o.d.power < n.d.power * 0.5 && !e.peek(n.id, o.id)?.team);
    if (weak.length) e.command(n.id, { t: 'breakAlly', with: weak[0].id });
  }
}
