// عنصر المفاجأة: المهمات السرية، عجلة الحظ، عجلة الأحداث العالمية، والتحالف ضد المسيطر
import {
  BUILDINGS, DAYS_PER_MONTH, ECON_VALUES, FORTUNES, POP_VALUES, FORTUNE_EVERY, GOVS, GOV_SLICES, MAX_BUILDING_LEVEL, MAX_TECH, MISSIONS,
  TECH_COST, WORLD_EVENTS, WORLD_EVERY,
} from './defs';
import type { Engine } from './engine';
import type { BuildingType, CmdResult, FortuneId, GovId, MissionId, Nation, WorldEventId } from './types';
import { BUILDING_TYPES, COMBAT_UNITS } from './types';
import { REGION_NAMES } from './world';
import { drawCard } from './cards';

const clamp = (x: number, a: number, b: number) => Math.max(a, Math.min(b, x));

// ---------------- المهمات السرية ----------------
export function assignMission(e: Engine, n: Nation, id: MissionId) {
  const reg = e.w.country(n.home).reg;
  const gdp = ECON_VALUES[n.tiers.econ] ?? 100;
  const pop = POP_VALUES[n.tiers.pop] ?? 10;
  const target: Record<MissionId, number> = {
    conqueror: 8,
    empire: 10,
    tycoon: Math.max(800, Math.round(gdp * 4)),
    scholar: MAX_TECH,
    allies: 3,
    regional: 5,
    admiral: Math.max(20, n.units.ship + 12),
    giant: Math.max(150, Math.round(pop * 3)),
    fortress: 4,
  };
  n.mission = { id, target: target[id], done: false, region: id === 'regional' ? reg : undefined };
}

export function missionProgress(e: Engine, n: Nation): number {
  const m = n.mission;
  switch (m.id) {
    case 'conqueror': return n.st.won;
    case 'empire': return n.d.countries;
    case 'tycoon': return Math.round(n.d.gdp);
    case 'scholar': return n.tech;
    case 'allies': return e.allies(n.id).length;
    case 'regional': return new Set(e.owned(n.id).filter((t) => e.w.get(t.id).reg === m.region).map((t) => e.w.parentOf(t.id))).size;
    case 'admiral': return n.units.ship;
    case 'giant': return Math.round(n.d.pop);
    case 'fortress': return n.st.held;
  }
}

export function missionText(n: Nation): string {
  const m = n.mission;
  const def = MISSIONS[m.id];
  return `${def.icon} ${def.name}: ${def.desc(m.target, m.region ? REGION_NAMES[m.region] : undefined)}`;
}

export function checkMissions(e: Engine) {
  for (const n of Object.values(e.s.nations)) {
    if (!n.alive || n.mission.done) continue;
    if (missionProgress(e, n) < n.mission.target) continue;
    n.mission.done = true;
    const bonus = Math.max(300, Math.round(n.d.score * 0.2));
    n.bonus += bonus;
    const cash = Math.round(Math.max(40, n.d.income * 12));
    n.treasury += cash;
    n.fortuneNext = Math.min(n.fortuneNext, e.s.day);
    e.news('🎯', `${n.name} حققت مهمتها السرية «${MISSIONS[n.mission.id].name}» وأخذت +${bonus} نقطة و ${cash} مليار!`, 'event', { n: [n.id] });
    e.histEvent('🎯', `${n.name} حققت مهمتها السرية «${MISSIONS[n.mission.id].name}»`);
    drawCard(e, n, 'مكافأة المهمة');
    drawCard(e, n, 'مكافأة المهمة');
  }
}

// ---------------- عجلة الحظ ----------------
export function rankOf(e: Engine, n: Nation): number {
  const alive = Object.values(e.s.nations).filter((x) => x.alive).sort((a, b) => b.d.score - a.d.score);
  if (alive.length <= 1) return 0.5;
  return alive.findIndex((x) => x.id === n.id) / (alive.length - 1);
}

/** أوزان عجلة الحظ: كل ما كنت متأخر بالترتيب زادت فرصتك بالنتايج الحلوة */
export function fortuneWeights(e: Engine, n: Nation): Record<FortuneId, number> {
  const r = rankOf(e, n);
  const out = {} as Record<FortuneId, number>;
  for (const [id, f] of Object.entries(FORTUNES) as [FortuneId, (typeof FORTUNES)[FortuneId]][]) {
    let w = f.w * (e.s.dev?.wm?.fortune?.[id] ?? 1);
    if (id === 'jackpot') w *= 0.3 + 2.2 * r;
    else if (f.good === 1) w *= 0.6 + 0.9 * r;
    else if (f.good === -1) w *= 1.5 - 0.9 * r;
    out[id] = w;
  }
  return out;
}

export function spinFortune(e: Engine, n: Nation): CmdResult {
  const s = e.s;
  if (s.day < n.fortuneNext) return { ok: false, msg: 'عجلة الحظ ما توفرت لك للحين' };
  const ws = fortuneWeights(e, n);
  const ids = Object.keys(ws) as FortuneId[];
  let id = ids.some((k) => ws[k] > 0) ? ids[e.weighted(ids.map((k) => ws[k]))] : 'nothing';
  // وضع المتحكم: نتيجة مثبتة
  const rig = s.dev?.fortune?.[n.id];
  if (rig && FORTUNES[rig]) { id = rig; delete s.dev!.fortune[n.id]; }
  const mag = n.trait === 'gambler' ? 1.5 : 1;
  const terrs = e.owned(n.id);
  let text = '';
  const income = Math.max(1, n.d.income);
  const addCash = (mult: number) => {
    const x = Math.round(Math.max(25, income * 8) * mult * mag);
    n.treasury += x;
    return x;
  };
  const addTech = () => {
    if (n.tech >= MAX_TECH) return addCash(0.5);
    n.research += TECH_COST[n.tech + 1] * 0.6 * mag;
    return 0;
  };
  const addTroops = () => {
    const inf = Math.round(Math.max(5, n.units.inf * 0.15) * mag);
    const tank = Math.round(Math.max(2, n.units.tank * 0.1) * mag);
    n.units.inf += inf;
    n.units.tank += tank;
    return `${inf} مشاة و ${tank} دبابات`;
  };
  switch (id) {
    case 'cash': text = `كنز! +${addCash(1)} مليار`; break;
    case 'troops': text = `متطوعين انضموا لجيشك: ${addTroops()}`; break;
    case 'tech': { const c = addTech(); text = c ? `اختراق علمي! (+${c} مليار لأنك وصلت أعلى تكنولوجيا)` : 'اختراق علمي! تقدمت كثير نحو التكنولوجيا الجاية'; break; }
    case 'build': {
      const opts = BUILDING_TYPES.filter((b) => n.b[b] < MAX_BUILDING_LEVEL && !(b === 'mining' && n.res === 'none'));
      const b = opts.length ? (e.pick(opts) as BuildingType) : null;
      if (b) { n.b[b]++; text = `مشروع مجاني: ${BUILDINGS[b].name} صار مستوى ${n.b[b]}`; } else text = `كنز! +${addCash(1)} مليار`;
      break;
    }
    case 'festival': n.stability = clamp(n.stability + 15 * mag, 0, 100); text = `مهرجان وطني! الاستقرار +${Math.round(15 * mag)}`; break;
    case 'boom': for (const t of terrs) t.gdp *= 1 + 0.08 * mag; text = `طفرة اقتصادية! الناتج +${Math.round(8 * mag)}%`; break;
    case 'arms':
      if (n.tech >= 2) { n.units.missile += Math.round(3 * mag); n.units.jet += Math.round(2 * mag); text = 'صفقة سلاح: صواريخ وطائرات جديدة'; }
      else { n.units.tank += Math.round(5 * mag); text = 'صفقة سلاح: دبابات جديدة'; }
      break;
    case 'jackpot': { const c = addCash(3); addTech(); const tr = addTroops(); text = `🎰 الجائزة الكبرى! +${c} مليار، و${tr}، واختراق علمي`; break; }
    case 'crash': { const x = Math.round(Math.max(0, n.treasury) * 0.3 * mag); n.treasury -= x; text = `انهيار البورصة.. خسرت ${x} مليار`; break; }
    case 'riots': n.stability = clamp(n.stability - 12 * mag, 0, 100); text = `أعمال شغب! الاستقرار -${Math.round(12 * mag)}`; break;
    case 'outbreak': for (const t of terrs) t.pop *= 1 - 0.04 * mag; text = `وباء محلي: السكان -${Math.round(4 * mag)}%`; break;
    case 'mutiny': for (const k of COMBAT_UNITS) n.units[k] = Math.floor(n.units[k] * (1 - 0.15 * mag)); text = `تمرد عسكري: خسرت ${Math.round(15 * mag)}% من جيشك`; break;
    case 'nothing': text = 'ولا شي.. حظك المرة الجاية'; break;
    case 'card': {
      const a = drawCard(e, n, 'عجلة الحظ');
      const b = drawCard(e, n, 'عجلة الحظ');
      text = a || b ? 'أخذت بطاقات خطط جديدة! شوفها من زر 🃏' : `يدك مليانة بطاقات، فأخذت كنز +${addCash(0.7)} مليار`;
      break;
    }
  }
  n.fortune = { nonce: (n.fortune?.nonce ?? 0) + 1, res: id, day: s.day, text };
  n.fortuneNext = s.day + (n.trait === 'gambler' ? FORTUNE_EVERY / 2 : FORTUNE_EVERY);
  e.news(FORTUNES[id].icon, `عجلة الحظ: ${text}`, 'event', { to: [n.id] });
  e.recompute(n);
  return { ok: true };
}

// ---------------- الأحداث العالمية ----------------
export function scheduleWorld(e: Engine, first = false) {
  const s = e.s;
  const dom = first ? 1 : dominance(e);
  const months = first ? Math.max(24, s.settings.peaceMonths + 14) : dom > 1.6 ? e.randInt(24, 32) : e.randInt(WORLD_EVERY[0], WORLD_EVERY[1]);
  s.nextWorld = s.day + months * DAYS_PER_MONTH;
}

function topNations(e: Engine) {
  return Object.values(e.s.nations).filter((n) => n.alive).sort((a, b) => b.d.score - a.d.score);
}

export function dominance(e: Engine): number {
  const t = topNations(e);
  if (t.length < 2) return 1;
  return t[0].d.score / Math.max(1, t[1].d.score);
}

export function fireWorldEvent(e: Engine, forced?: WorldEventId) {
  const s = e.s;
  const alive = topNations(e);
  if (alive.length < 2) return;
  const dom = dominance(e);
  const ids = Object.keys(WORLD_EVENTS) as WorldEventId[];
  const ws = ids.map((id) => WORLD_EVENTS[id].w * (WORLD_EVENTS[id].antiLeader && dom > 1.4 ? 2.2 : 1));
  const ev = forced ?? ids[e.weighted(ws)];
  const top = alive[0];
  let text = WORLD_EVENTS[ev].desc;
  let target: string | undefined;
  let terr: string | undefined;
  switch (ev) {
    case 'coalition':
      startCoalition(e, top, false);
      target = top.id;
      text = `العالم يتحد ضد ${top.name}! البوتات تعاديها والدول المحايدة حولها تتسلح`;
      break;
    case 'crash': {
      const rich = [...alive].sort((a, b) => b.d.gdp - a.d.gdp).slice(0, 3).map((n) => n.id);
      for (const n of alive) if (n.treasury > 0) n.treasury *= rich.includes(n.id) ? 0.6 : 0.8;
      text = `كل الخزائن نقصت 20%، و ${rich.map((id) => s.nations[id].name).join('، ')} خسروا 40%`;
      break;
    }
    case 'pandemic':
      for (const t of Object.values(s.terr)) t.pop *= 0.95;
      for (const n of alive) if (n.d.terrs > 8) n.stability = clamp(n.stability - 15, 0, 100);
      break;
    case 'revolts': {
      let count = 0;
      for (const n of alive) {
        const terrs = e.owned(n.id).filter((t) => t.id !== n.capital && e.w.parentOf(t.id) !== n.home);
        if (terrs.length < 3) continue;
        let max = Math.floor(terrs.length / 3);
        for (const t of terrs) {
          if (max <= 0) break;
          const p = t.unrest > 0 ? 0.35 : terrs.length > 8 ? 0.12 : 0.05;
          if (e.rand() < p) { e.revolt(t, n); max--; count++; }
        }
      }
      text = count ? `${count} أرض أعلنت استقلالها عن الإمبراطوريات الكبيرة!` : 'الثورات قامت بس الحكومات سيطرت عليها';
      break;
    }
    case 'bailout': {
      const weak = alive.slice(Math.ceil(alive.length / 2));
      for (const n of weak) {
        n.treasury += Math.max(50, n.d.income * 12);
        n.units.inf += 10;
        n.units.tank += 3;
        n.research += 100;
      }
      text = `الدول الأضعف (${weak.map((n) => n.name).join('، ')}) أخذت دعم دولي: فلوس وجنود وأبحاث`;
      break;
    }
    case 'peace':
      for (const a of alive) for (const b of alive) {
        if (a.id < b.id && e.atWar(a.id, b.id)) e.makePeace(a, b, 12, true);
      }
      break;
    case 'energy': {
      const lucky = alive.filter((n) => n.res === 'oil' || n.res === 'gas' || n.res === 'uranium');
      for (const n of lucky) n.treasury += n.d.gdp * 0.15;
      text = lucky.length ? `أرباح ضخمة لـ ${lucky.map((n) => n.name).join('، ')}` : 'ما فيه دولة عندها نفط أو غاز.. ما استفاد أحد!';
      break;
    }
    case 'meteor': {
      const cands = alive.slice(0, 3).flatMap((n) => e.owned(n.id));
      if (cands.length) {
        const t = cands[e.weighted(cands.map((x) => Math.max(1, x.gdp)))];
        t.gdp *= 0.5;
        t.pop *= 0.8;
        const owner = s.nations[t.owner];
        if (owner) for (const k of COMBAT_UNITS) owner.units[k] = Math.floor(owner.units[k] * 0.9);
        terr = t.id;
        text = `نيزك ضرب ${e.tname(t.id)}${owner ? ` (${owner.name})` : ''}! نص الاقتصاد راح`;
      }
      break;
    }
    case 'techrev': {
      const maxT = Math.max(...alive.map((n) => n.tech));
      const up = alive.filter((n) => n.tech < maxT);
      for (const n of alive) {
        if (n.tech < maxT) { n.tech = Math.min(MAX_TECH, n.tech + 1); n.research = 0; } else n.research += 80;
      }
      text = up.length ? `${up.length} دول متأخرة قفزت مستوى تكنولوجيا` : 'كل الدول تقدمت في الأبحاث';
      break;
    }
    case 'armsrace':
      s.mods.arms = s.day + 12 * DAYS_PER_MONTH;
      break;
    case 'fortune':
      for (const n of alive) n.fortuneNext = s.day;
      break;
    case 'goldage':
      for (const n of alive) n.stability = clamp(n.stability + 10, 0, 100);
      for (const t of Object.values(s.terr)) if (t.owner) t.gdp *= 1.05;
      break;
    case 'mercsrebel': {
      const big = [...alive].sort((a, b) => b.d.power - a.d.power)[0];
      for (const k of COMBAT_UNITS) big.units[k] = Math.floor(big.units[k] * 0.8);
      target = big.id;
      text = `المرتزقة في جيش ${big.name} تمردوا! خسرت 20% من قواتها`;
      break;
    }
  }
  s.world = { id: e.id(), ev, day: s.day, text, target, terr };
  s.holdUntil = Date.now() + 7500;
  e.histEvent(WORLD_EVENTS[ev].icon, `${WORLD_EVENTS[ev].name}: ${text}`);
  e.news(WORLD_EVENTS[ev].icon, `حدث عالمي: ${WORLD_EVENTS[ev].name}! ${text}`, 'system', { terr });
  for (const n of alive) e.recompute(n);
}

/** التحالف الدولي ضد الدولة المسيطرة: البوتات تعلن الحرب عليها وتتحالف مع بعض */
export function startCoalition(e: Engine, top: Nation, announce: boolean) {
  const s = e.s;
  s.coalition = top.id;
  const members: Nation[] = [];
  for (const n of Object.values(s.nations)) {
    if (!n.alive || n.id === top.id || !n.ai || e.allied(n.id, top.id)) continue;
    n.ai.grudge = top.id;
    members.push(n);
    if (!e.canHit(n, top) && !e.atWar(n.id, top.id)) e.declareWar(n, top, true);
    // دعم التحالف: جنود إضافيين
    n.units.inf += Math.max(4, Math.round(n.units.inf * 0.15));
    n.units.tank += Math.max(1, Math.round(n.units.tank * 0.1));
  }
  // أعضاء التحالف يتحالفون مع بعض
  for (const a of members) for (const b of members) {
    if (a.id < b.id && !e.atWar(a.id, b.id)) e.rel(a.id, b.id).ally = s.day;
  }
  // الدول المحايدة حول المسيطر تتسلح
  const near = new Set<string>();
  for (const t of e.owned(top.id)) for (const x of e.w.get(t.id).n) if (s.terr[x]?.owner === '') near.add(x);
  for (const id of near) {
    const t = s.terr[id];
    if (t.g) { t.g.inf = Math.round(t.g.inf * 1.6) + 2; t.g.tank = Math.round(t.g.tank * 1.6); }
    if (t.gmax) t.gmax *= 1.6;
  }
  top.stability = clamp(top.stability - 10, 0, 100);
  e.histEvent('🌍', `تحالف دولي ضد ${top.name}`);
  if (announce || members.length) {
    e.news('🌍', `${members.length ? members.length + ' دول' : 'العالم'} تتحالف ضد ${top.name} بسبب هيمنتها! (هجوم التحالف عليها أقوى 20%)`, 'system', { n: [top.id] });
  }
}

/** فحص سنوي: لو فيه دولة مسيطرة بشكل كبير، العالم يتحالف ضدها */
export function checkCoalition(e: Engine) {
  const s = e.s;
  const top = topNations(e);
  if (top.length < 3) return;
  const dom = dominance(e);
  const peaceOver = s.day > s.settings.peaceMonths * DAYS_PER_MONTH;
  if (dom > 1.6 && peaceOver && s.coalition !== top[0].id) startCoalition(e, top[0], true);
  else if (s.coalition && dom < 1.25) {
    const old = s.nations[s.coalition];
    s.coalition = undefined;
    for (const n of Object.values(s.nations)) if (n.ai?.grudge === old?.id && n.ai) n.ai.grudge = undefined;
    if (old) e.news('🕊️', `التحالف الدولي ضد ${old.name} انحل`, 'system');
  }
}

/** الحكومة الانتقالية تنتهي وتنلف عجلة الحكم من جديد */
export function checkTransitional(e: Engine, n: Nation) {
  if (n.gov !== 'transitional' || !n.govUntil || e.s.day < n.govUntil) return;
  const opts = GOV_SLICES.filter((x) => x.v !== 'transitional');
  const g = opts[e.weighted(opts.map((x) => x.w))].v as GovId;
  n.gov = g;
  n.govUntil = undefined;
  n.stability = clamp(n.stability + 10, 0, 100);
  e.news(GOVS[g].icon, `انتهت المرحلة الانتقالية في ${n.name}: صار نظام الحكم ${GOVS[g].name}`, 'event', { n: [n.id] });
}
