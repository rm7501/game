// المعارك: تستمر عدة أيام، والخسائر تكون تدريجية، والحظ اليومي صغير
// الطرف الأقوى (بعد حساب التكنولوجيا والتحصينات والتضاريس والتفوق الجوي) يفوز غالباً
import { BATTLE, GENERALS, GOVS, TERRAINS, UNITS, emptyUnits, stars, techMult, xpMult } from './defs';
import { addAt, generalAt, generalLost, generalWon, genLevel, syncPlaces, takeAt, unitMult } from './army';
import type { Engine } from './engine';
import { drawCard } from './cards';
import type { Battle, General, Movement, Nation, NationId, Report, TerrId, Units } from './types';
import { COMBAT_UNITS, UNIT_TYPES } from './types';

const clamp = (x: number, a: number, b: number) => Math.max(a, Math.min(b, x));

export interface Setup {
  a0: number;
  d0: number;
  aBreak: number;
  dBreak: number;
  mods: string[];
  du: Units;
  allies: { id: NationId; u: Units }[];
  sup: { terr: TerrId; u: Units }[];
  dxp: number;
  dgen?: number;
}

function shipBonus(n: Nation | null) {
  return n ? 1 + TERRAINS[n.terrain].ships : 1;
}

export interface AttackOpts {
  xp?: number; // خبرة الجيش المهاجم
  gen?: General; // جنرال المهاجم
}

/** قوة الهجوم لوحدات معينة على هدف معين */
export function attackPower(e: Engine, A: Nation, units: Partial<Units>, to: TerrId, o: AttackOpts = {}): number {
  const coastal = !!e.w.get(to).c;
  const g = o.gen;
  const lv = genLevel(g);
  let raw = 0;
  for (const k of COMBAT_UNITS) {
    if (k === 'ship' && !coastal) continue;
    let m = unitMult(A, k) * (k === 'ship' ? shipBonus(A) : 1);
    if (g?.kind === 'armor' && k === 'tank') m *= 1 + 0.25 * lv;
    if (g?.kind === 'air' && k === 'jet') m *= 1 + 0.25 * lv;
    if (g?.kind === 'navy' && k === 'ship') m *= 1 + 0.25 * lv;
    raw += (units[k] ?? 0) * UNITS[k].atk * m;
  }
  const trait = A.trait === 'warlord' ? 1.15 : 1;
  const genB = g?.kind === 'attack' ? 1 + 0.12 * lv : g?.kind === 'speed' ? 1.05 : 1;
  return raw * GOVS[A.gov].atk * trait * genB * xpMult(o.xp ?? 0) * (0.85 + 0.15 * A.stability / 100);
}

/** يجهز المعركة: يحسب القوى ويحدد قوات المدافع (بدون ما يسحبها لو dry) */
export function setupBattle(e: Engine, A: Nation | null, units: Partial<Units>, to: TerrId, naval: boolean, from: TerrId, dry: boolean, o: AttackOpts = {}): Setup {
  const s = e.s;
  const T = s.terr[to];
  const m = e.w.get(to);
  const coastal = !!m.c;
  const depth = 1 + 0.08 * m.cls;
  const mods: string[] = [];
  let a0 = A ? attackPower(e, A, units, to, o) : 0;
  if (A && stars(o.xp ?? 0) > 0) mods.push(`${'⭐'.repeat(stars(o.xp ?? 0))} خبرة المهاجم`);
  if (o.gen) mods.push(`${GENERALS[o.gen.kind].icon} ${o.gen.name} (مستوى ${o.gen.lvl})`);

  // الأسلحة المشتركة: مشاة + دبابات + طيران
  const parts = (['inf', 'tank', 'jet'] as const).map((k) => (units[k] ?? 0) * UNITS[k].atk);
  const total = parts.reduce((x, y) => x + y, 0) || 1;
  const kinds = parts.filter((p) => p / total >= 0.15).length;
  if (kinds === 3) { a0 *= 1.15; mods.push('أسلحة مشتركة +15%'); }
  else if (kinds === 2) { a0 *= 1.07; mods.push('أسلحة مشتركة +7%'); }

  // الإمداد: كل ما بعدت عن أرضك ضعف جيشك
  const dist = e.w.centerDist(from, to);
  if (dist > 5000) { a0 *= 0.8; mods.push('خطوط إمداد طويلة -20%'); }
  else if (dist > 2500) { a0 *= 0.9; mods.push('خطوط إمداد طويلة -10%'); }

  const du = emptyUnits();
  const allies: { id: NationId; u: Units }[] = [];
  const sup: { terr: TerrId; u: Units }[] = [];
  let d0 = 0;
  let dBreak = BATTLE.defBreak;
  let dxp = 0;
  let dgen: General | undefined;
  const D = T.owner ? s.nations[T.owner] : null;
  if (!D) {
    const g = T.g ?? { inf: 0, tank: 0 };
    du.inf = g.inf;
    du.tank = g.tank;
    const militia = 0.5 + T.pop * 0.02;
    d0 = (g.inf * UNITS.inf.def + g.tank * UNITS.tank.def + militia) * techMult(T.nt ?? 1) * depth;
  } else {
    const isCap = to === D.capital;
    // الجيش المتمركز في الأرض يدافع عنها كامل
    const st = D.place?.[to];
    if (st) for (const k of COMBAT_UNITS) {
      if (k === 'ship' && !coastal) continue;
      du[k] = st.u[k];
    }
    dxp = st?.xp ?? 0;
    dgen = generalAt(D, to);
    const lv = genLevel(dgen);
    const umult = (X: Nation, k: keyof Units, g?: General) => {
      let mm = unitMult(X, k) * (k === 'ship' ? shipBonus(X) : 1);
      if (g?.kind === 'armor' && k === 'tank') mm *= 1 + 0.25 * genLevel(g);
      if (g?.kind === 'air' && k === 'jet') mm *= 1 + 0.25 * genLevel(g);
      if (g?.kind === 'navy' && k === 'ship') mm *= 1 + 0.25 * genLevel(g);
      return mm;
    };
    const militia = 0.5 + T.pop * 0.02;
    let raw = militia;
    for (const k of COMBAT_UNITS) raw += du[k] * UNITS[k].def * umult(D, k, dgen);
    raw *= xpMult(dxp);
    // دعم من الأراضي المجاورة (ربع جيشها البري والجوي)
    let supRaw = 0;
    for (const x of m.n) {
      if (s.terr[x]?.owner !== D.id || s.battles.some((b) => b.terr === x)) continue;
      const xs = D.place?.[x];
      if (!xs) continue;
      const u = emptyUnits();
      let r = 0;
      for (const k of ['inf', 'tank', 'jet'] as const) {
        u[k] = Math.floor(xs.u[k] * 0.25);
        r += u[k] * UNITS[k].def * umult(D, k);
      }
      if (r > 0) { sup.push({ terr: x, u }); supRaw += r * xpMult(xs.xp); }
    }
    if (sup.length) mods.push(`🛡️ دعم من ${sup.length} أراضي مجاورة`);
    raw += supRaw;
    if (stars(dxp) > 0) mods.push(`${'⭐'.repeat(stars(dxp))} خبرة المدافع`);
    if (dgen) mods.push(`${GENERALS[dgen.kind].icon} ${dgen.name} يدافع`);
    const home = e.w.parentOf(to) === D.home ? 1 + TERRAINS[D.terrain].def : 1;
    if (home > 1) mods.push(`${TERRAINS[D.terrain].icon} تضاريس صعبة +${Math.round((home - 1) * 100)}%`);
    if (home < 1) mods.push(`${TERRAINS[D.terrain].icon} أرض مكشوفة ${Math.round((home - 1) * 100)}%`);
    if (D.b.fort) mods.push(`🏰 تحصينات +${D.b.fort * 10}%`);
    const guardian = D.trait === 'guardian' ? 1.2 : 1;
    const genDef = dgen?.kind === 'defense' ? 1 + 0.15 * lv : 1;
    d0 = raw * (1 + 0.1 * D.b.fort) * depth * home * guardian * genDef * (isCap ? 1.15 : 1) * (0.85 + 0.15 * D.stability / 100);
    if (isCap) { dBreak = BATTLE.capitalBreak; mods.push('العاصمة تقاتل للنهاية'); }
    if (D.trait === 'guardian') dBreak -= 0.05;
    if (dgen?.kind === 'morale') dBreak -= 0.04 * lv;
    // الحلفاء يرسلون 15% من جيشهم
    for (const aid of e.allies(D.id)) {
      if (aid === A?.id) continue;
      const X = s.nations[aid];
      const u = emptyUnits();
      let r = 0;
      for (const k of COMBAT_UNITS) {
        if (k === 'ship' && !coastal) continue;
        u[k] = Math.floor(X.units[k] * 0.15);
        r += u[k] * UNITS[k].def * unitMult(X, k);
      }
      if (r > 0) {
        d0 += r;
        allies.push({ id: aid, u });
      }
    }
    // جيوش القواعد العسكرية في الأرض تدافع معها
    for (const bs of s.bases ?? []) {
      if (bs.terr !== to || bs.owner === A?.id || bs.host !== D.id) continue;
      const X = s.nations[bs.owner];
      const st = X?.place?.[to];
      if (!X?.alive || !st) continue;
      const u = emptyUnits();
      let r = 0;
      for (const k of COMBAT_UNITS) {
        if (k === 'ship' && !coastal) continue;
        u[k] = st.u[k];
        r += u[k] * UNITS[k].def * unitMult(X, k);
      }
      if (r > 0) { d0 += r; allies.push({ id: X.id, u }); mods.push(`🏰 قاعدة ${X.name}`); }
    }
    if (allies.length) mods.push(`🤝 دعم ${allies.length} حليف`);
  }

  // التفوق الجوي
  const aj = units.jet ?? 0;
  const dj = du.jet + allies.reduce((x, a) => x + a.u.jet, 0) + sup.reduce((x, a) => x + a.u.jet, 0);
  if (aj >= 3 && aj > 2 * dj) { a0 *= 1.15; mods.push('✈️ تفوق جوي للمهاجم +15%'); }
  else if (dj >= 3 && dj > 2 * aj) { d0 *= 1.12; mods.push('✈️ تفوق جوي للمدافع +12%'); }

  // الإنزال البحري صعب إلا لو أسطولك أكبر بكثير (أو معك أميرال)
  if (naval) {
    const as = units.ship ?? 0;
    const ds = du.ship + allies.reduce((x, a) => x + a.u.ship, 0);
    if (as > 2 * ds + 2) mods.push('🚢 سيطرة بحرية');
    else if (o.gen?.kind === 'navy') mods.push('⚓ الأميرال يقود الإنزال');
    else { a0 *= 0.85; mods.push('🚢 إنزال بحري -15%'); }
  }

  // وضع المتحكم: مضاعف قوة المعارك
  const gA = A ? s.dev?.god?.[A.id] : undefined;
  const gD = D ? s.dev?.god?.[D.id] : undefined;
  if (gA) { a0 *= gA; mods.push(`🛠️ قوة ×${gA}`); }
  if (gD) { d0 *= gD; mods.push(`🛠️ دفاع ×${gD}`); }
  // بطاقات الخطط
  if (A && (A.fx.blitz ?? 0) > s.day) { a0 *= 1.25; mods.push('⚡ هجوم خاطف +25%'); }
  if (D && (D.fx.shield ?? 0) > s.day) { d0 *= 1.3; mods.push('🛡️ درع وطني +30%'); }
  // ذريعة حرب بعد رفض إنذار نهائي
  const cb = A && D ? e.peek(A.id, D.id)?.cb : undefined;
  if (cb && cb.by === A!.id && cb.until > s.day) { a0 *= 1.15; mods.push('📜 ذريعة حرب +15%'); }
  // التحالف الدولي ضد المسيطر
  if (D && s.coalition === D.id) { a0 *= 1.2; mods.push('🌍 التحالف الدولي +20%'); }
  // الدول الأضعف تدافع عن وجودها
  if (D?.underdog) { d0 *= 1.2; mods.push('🛡️ دفاع المستضعفين +20%'); }

  let aBreak = BATTLE.attBreak;
  if (A?.trait === 'warlord') aBreak -= 0.07;
  if (o.gen?.kind === 'morale') aBreak -= 0.04 * genLevel(o.gen);

  if (!dry) {
    // نسحب القوات المشاركة من أماكنها
    if (D) {
      takeAt(D, to, du);
      for (const sp of sup) takeAt(D, sp.terr, sp.u);
    } else if (T.g) { T.g.inf -= du.inf; T.g.tank -= du.tank; }
    for (const al of allies) {
      const X = s.nations[al.id];
      // جيش القاعدة ينسحب من مكانه، والحلفاء من مجموع جيشهم
      if (X.place?.[to] && (s.bases ?? []).some((bs) => bs.terr === to && bs.owner === X.id)) takeAt(X, to, al.u);
      else {
        for (const k of COMBAT_UNITS) X.units[k] -= al.u[k];
        syncPlaces(e, X);
      }
    }
  }
  return { a0: Math.max(0.01, a0), d0: Math.max(0.01, d0), aBreak, dBreak, mods, du, allies, sup, dxp, dgen: dgen?.id };
}

/** قوة الدفاع التقريبية عن أرض (للعرض) */
export function defenseValue(e: Engine, to: TerrId, attacker: Nation | null): number {
  const route = attacker ? e.route(attacker, to) : null;
  return setupBattle(e, attacker, {}, to, !!route?.naval, route?.from ?? to, true).d0;
}

/** محاكاة سريعة للمعركة (للتقدير وللبوتات) */
export function simulate(a0: number, d0: number, aBreak: number, dBreak: number, rand?: () => number) {
  let a = a0;
  let d = d0;
  for (let day = 1; day <= BATTLE.maxDays; day++) {
    const na = rand ? 1 + (rand() * 2 - 1) * BATTLE.noise : 1;
    const nd = rand ? 1 + (rand() * 2 - 1) * BATTLE.noise : 1;
    const lossA = BATTLE.intensity * d * nd;
    const lossD = BATTLE.intensity * a * na;
    a = Math.max(0, a - lossA);
    d = Math.max(0, d - lossD);
    if (d < dBreak * d0) return { win: true, days: day, aLeft: a / a0, dLeft: d / d0 };
    if (a < aBreak * a0) return { win: false, days: day, aLeft: a / a0, dLeft: d / d0 };
  }
  return { win: false, days: BATTLE.maxDays, aLeft: a / a0, dLeft: d / d0 };
}

/** تقدير نتيجة هجوم قبل إرساله */
export function estimate(e: Engine, A: Nation, units: Partial<Units>, to: TerrId, samples = 40, from?: TerrId, withGen = false) {
  const route = e.route(A, to, from);
  const src = route?.from ?? A.capital;
  const stack = A.place?.[src];
  const st = setupBattle(e, A, units, to, !!route?.naval, src, true, { xp: stack?.xp ?? 0, gen: withGen ? generalAt(A, src) : undefined });
  let wins = 0;
  let loss = 0;
  let days = 0;
  // عشوائية ثابتة عشان التقدير ما يتغير كل ما تحرك المؤشر
  let seed = 12345;
  const rnd = () => {
    seed = (seed * 1103515245 + 12345) & 0x7fffffff;
    return seed / 0x7fffffff;
  };
  for (let i = 0; i < samples; i++) {
    const r = simulate(st.a0, st.d0, st.aBreak, st.dBreak, rnd);
    if (r.win) wins++;
    loss += 1 - r.aLeft;
    days += r.days;
  }
  return { p: wins / samples, aLoss: loss / samples, days: Math.round(days / samples), A: st.a0, D: st.d0, mods: st.mods };
}

function scale(u: Units, frac: number, rand: () => number): Units {
  const out = emptyUnits();
  for (const k of UNIT_TYPES) {
    const exact = u[k] * clamp(frac, 0, 1);
    let n = Math.floor(exact);
    if (rand() < exact - n) n++;
    out[k] = n;
  }
  return out;
}

function sub(a: Units, b: Units): Partial<Units> {
  const out: Partial<Units> = {};
  for (const k of UNIT_TYPES) if (a[k] - b[k] > 0) out[k] = a[k] - b[k];
  return out;
}

function compact(u: Units): Partial<Units> {
  const out: Partial<Units> = {};
  for (const k of UNIT_TYPES) if (u[k] > 0) out[k] = u[k];
  return out;
}

/** وصل جيش لأرض العدو: نبدأ معركة (أو نضمه لمعركة شغالة) */
export function startBattle(e: Engine, mv: Movement): void {
  const s = e.s;
  const A = s.nations[mv.owner];
  const T = s.terr[mv.to];
  const cur = s.battles.find((b) => b.terr === mv.to);
  const gen = mv.gen ? A.generals?.find((g) => g.id === mv.gen) : undefined;
  if (cur) {
    if (cur.att === A.id) {
      // تعزيزات للمعركة الشغالة
      const add = attackPower(e, A, mv.units, mv.to, { xp: mv.xp ?? 0, gen });
      const frac = cur.a / cur.a0;
      for (const k of UNIT_TYPES) cur.au[k] += mv.units[k] / Math.max(0.05, frac);
      cur.a += add;
      cur.a0 += add / Math.max(0.05, frac);
      if (gen && !cur.agen) cur.agen = gen.id;
      e.news('🪖', `تعزيزات من ${A.name} وصلت لمعركة ${e.tname(T.id)}`, 'battle', { to: [A.id, cur.def].filter(Boolean), terr: T.id });
      return;
    }
    // فيه معركة ثانية على نفس الأرض: الجيش ينتظر يومين
    mv.arrive = s.day + 2;
    s.moves.push(mv);
    return;
  }
  const D = T.owner ? s.nations[T.owner] : null;
  const st = setupBattle(e, A, mv.units, mv.to, !!mv.naval, mv.from, false, { xp: mv.xp ?? 0, gen });
  const b: Battle = {
    id: e.id(), terr: T.id, att: A.id, def: D?.id ?? '', from: mv.from, naval: !!mv.naval, start: s.day,
    au: { ...mv.units }, du: st.du, allies: st.allies, a0: st.a0, d0: st.d0, m: 0, a: st.a0, d: st.d0,
    aBreak: st.aBreak, dBreak: st.dBreak, days: 0, mods: st.mods, sup: st.sup, axp: mv.xp ?? 0, dxp: st.dxp, agen: gen?.id, dgen: st.dgen,
  };
  s.battles.push(b);
  e.news('⚔️', `معركة بدأت في ${e.tname(T.id)}: ${A.name} ضد ${D ? D.name : 'الحامية المحايدة'}`, 'battle', { n: [A.id, D?.id ?? ''], terr: T.id });
}

/** تعزيزات المدافع توصل وسط المعركة: تنضم للدفاع */
export function joinDefense(e: Engine, b: Battle, D: Nation, u: Units) {
  let r = 0;
  for (const k of COMBAT_UNITS) r += (u[k] ?? 0) * UNITS[k].def * unitMult(D, k);
  r *= 1 + 0.1 * D.b.fort;
  const frac = b.d / b.d0;
  for (const k of UNIT_TYPES) b.du[k] += (u[k] ?? 0) / Math.max(0.05, frac);
  b.d += r;
  b.d0 += r / Math.max(0.05, frac);
  e.news('🛡️', `تعزيزات من ${D.name} وصلت للدفاع عن ${e.tname(b.terr)}`, 'battle', { to: [D.id, b.att], terr: b.terr });
}

/** يوم قتال لكل المعارك */
export function tickBattles(e: Engine): void {
  const s = e.s;
  if (!s.battles.length) return;
  for (const b of [...s.battles]) {
    const A = s.nations[b.att];
    const T = s.terr[b.terr];
    const D = b.def ? s.nations[b.def] : null;
    // حالات إلغاء: سقوط دولة، تغير صاحب الأرض، سلام أو تحالف
    if (!A?.alive) { endBattle(e, b, 'cancel'); continue; }
    if (T.owner !== b.def) { endBattle(e, b, 'cancel'); continue; }
    if (D && (!D.alive || e.allied(A.id, D.id) || e.inTruce(A.id, D.id))) { endBattle(e, b, 'cancel'); continue; }
    b.days++;
    const noise = s.dev?.noise ?? BATTLE.noise;
    const na = 1 + (e.rand() * 2 - 1) * noise;
    const nd = 1 + (e.rand() * 2 - 1) * noise;
    const lossA = BATTLE.intensity * b.d * nd;
    const lossD = BATTLE.intensity * b.a * na;
    b.a = Math.max(0, b.a - lossA);
    b.d = Math.max(0, b.d - lossD);
    if (b.d < b.dBreak * b.d0) endBattle(e, b, 'att');
    else if (b.a < b.aBreak * b.a0 || b.days >= 40) endBattle(e, b, 'def');
  }
}

/** أقرب أرض للمدافع ينسحب لها جيشه */
function fallback(e: Engine, D: Nation, from: TerrId): TerrId {
  const near = e.w.get(from).n.find((x) => e.s.terr[x]?.owner === D.id);
  return near ?? D.capital;
}

/** نهاية المعركة: نوزع الناجين ونكتب التقرير */
export function endBattle(e: Engine, b: Battle, outcome: 'att' | 'def' | 'cancel'): void {
  const s = e.s;
  s.battles = s.battles.filter((x) => x.id !== b.id);
  const A = s.nations[b.att];
  const T = s.terr[b.terr];
  const D = b.def ? s.nations[b.def] : null;
  const rnd = () => e.rand();
  const aFrac = b.a / b.a0;
  const dFrac = b.d / b.d0;
  const aSurv = scale(b.au, aFrac, rnd);
  const dSurv = scale(b.du, dFrac, rnd);
  const agen = b.agen ? A?.generals?.find((g) => g.id === b.agen) : undefined;
  const dgen = b.dgen && D ? D.generals?.find((g) => g.id === b.dgen) : undefined;
  const xpGain = (base: number, g?: General) => base * (g?.kind === 'morale' ? 2 : 1);
  // الحلفاء يرجعون بالناجين
  for (const al of b.allies) {
    const X = s.nations[al.id];
    if (!X?.alive) continue;
    const surv = scale(al.u, dFrac, rnd);
    for (const k of UNIT_TYPES) X.units[k] += surv[k];
    syncPlaces(e, X);
  }
  // الدعم من الأراضي المجاورة يرجع مكانه
  if (D?.alive) for (const sp of b.sup ?? []) addAt(e, D, sp.terr, scale(sp.u, dFrac, rnd), b.dxp ?? 0);
  const giveBackDef = (won: boolean) => {
    if (D?.alive) {
      const at = won && T.owner === D.id ? T.id : fallback(e, D, T.id);
      addAt(e, D, at, dSurv, Math.min(100, (b.dxp ?? 0) + (won ? xpGain(12, dgen) : xpGain(5, dgen))));
      if (dgen) dgen.at = at;
    } else if (!D && T.owner === '') {
      T.g = T.g ?? { inf: 0, tank: 0 };
      T.g.inf += dSurv.inf;
      T.g.tank += dSurv.tank;
    }
  };
  if (outcome === 'cancel') {
    giveBackDef(true);
    if (A?.alive) retreat(e, A, b, aSurv, b.axp ?? 0, agen);
    return;
  }
  const rep: Report = {
    id: e.id(), day: s.day, kind: 'battle', att: b.att, def: b.def, terr: b.terr, from: b.from,
    A: Math.round(b.a0), D: Math.round(b.d0), la: Math.round(aFrac * 100), ld: Math.round(dFrac * 100),
    win: outcome === 'att', aUnits: compact(b.au), dUnits: compact(b.du), aLoss: sub(b.au, aSurv), dLoss: sub(b.du, dSurv),
    allies: b.allies.map((a) => a.id), days: b.days, mods: b.mods,
  };
  s.reports.push(rep);
  if (s.reports.length > 30) s.reports.splice(0, s.reports.length - 30);
  if (outcome === 'att') {
    A.st.won++;
    A.st.conq++;
    if (D) { D.st.lost++; D.st.lostT++; }
    if (A.ai) A.ai.cool = s.day + e.randInt(A.ai.pers === 'aggressive' ? 35 : 55, A.ai.pers === 'aggressive' ? 80 : 120);
    // جنرال المدافع: ممكن يسقط
    if (D && dgen && !generalLost(e, D, dgen, 0.3)) dgen.at = D.capital;
    // المدافعين الناجين ينسحبون لأقرب أرض (المحايدة تنتهي)
    if (D) giveBackDef(false);
    e.conquer(T, A, D, b.days);
    // المهاجمين يتمركزون في الأرض الجديدة ويكسبون خبرة
    addAt(e, A, T.id, aSurv, Math.min(100, (b.axp ?? 0) + xpGain(15, agen)));
    if (agen) { agen.at = T.id; generalWon(e, A, agen); }
    if (e.rand() < (D ? 0.2 : 0.08)) drawCard(e, A, 'غنيمة حرب');
  } else {
    A.st.lost++;
    if (D) { D.st.won++; D.st.held++; }
    giveBackDef(true);
    if (D) generalWon(e, D, dgen);
    e.news('🛡️', `${D ? D.name : e.tname(T.id)} صدّت هجوم ${A.name} على ${e.tname(T.id)} بعد ${b.days} يوم`, 'battle', { n: [A.id, D?.id ?? ''], terr: T.id });
    const dead = generalLost(e, A, agen, 0.2);
    retreat(e, A, b, aSurv, Math.min(100, (b.axp ?? 0) + xpGain(6, agen)), dead ? undefined : agen);
  }
  e.recompute(A);
  if (D?.alive) e.recompute(D);
}

function retreat(e: Engine, A: Nation, b: Battle, units: Units, xp: number, gen?: General) {
  const total = UNIT_TYPES.reduce((x, k) => x + units[k], 0);
  if (gen) gen.at = '';
  if (!total) {
    if (gen) gen.at = A.capital;
    return;
  }
  const back: Movement = {
    id: e.id(), owner: A.id, from: b.terr, to: b.from, units, depart: e.s.day,
    arrive: e.s.day + Math.max(4, Math.round(e.travelDays(A, b.from, b.terr, b.naval) * 0.8)), kind: 'return', naval: b.naval, xp, gen: gen?.id,
  };
  e.s.moves.push(back);
}

/** الوحدات المشغولة بمعارك (للحسابات) */
export function unitsInBattles(e: Engine, nid: NationId): Units {
  const u = emptyUnits();
  for (const b of e.s.battles) {
    if (b.att === nid) for (const k of UNIT_TYPES) u[k] += b.au[k] * (b.a / b.a0);
    if (b.def === nid) {
      for (const k of UNIT_TYPES) u[k] += b.du[k] * (b.d / b.d0);
      for (const sp of b.sup ?? []) for (const k of UNIT_TYPES) u[k] += sp.u[k] * (b.d / b.d0);
    }
    for (const al of b.allies) if (al.id === nid) for (const k of UNIT_TYPES) u[k] += al.u[k] * (b.d / b.d0);
  }
  return u;
}
