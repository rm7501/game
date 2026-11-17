// الجيوش المتمركزة: كل أرض فيها جيش، والجيش يتحرك وينتشر ويكسب خبرة، ومعه جنرالات
// n.units = مجموع الجيش الموجود في الأراضي (مو بالطريق ولا بمعركة)، و n.place = توزيعه على الأراضي
import {
  BRANCH_DEFS, GENERALS, GENERAL_NAMES, GEN_COST, GEN_DAYS, MAX_GENERALS, MAX_GEN, MAX_SPECS, SPEC_PROJECT, UNITS, emptyUnits,
  generalCost, genMult, xpMult,
} from './defs';
import type { Engine } from './engine';
import type { Branch, CmdResult, General, GeneralKind, Nation, TerrId, Units } from './types';
import { BRANCH_OF, COMBAT_UNITS } from './types';

const clamp = (x: number, a: number, b: number) => Math.max(a, Math.min(b, x));
/** الوحدات اللي تتمركز في الأراضي (الصواريخ والنووي مخزون وطني) */
export const STATIONED = COMBAT_UNITS;

export const unitCount = (u: Partial<Units>) => STATIONED.reduce((a, k) => a + (u[k] ?? 0), 0);

/** مضاعف قوة نوع وحدة حسب جيل فرعها وتخصص الدولة */
export function unitMult(n: Nation, k: keyof Units): number {
  const b = BRANCH_OF[k];
  return genMult(n.gen?.[b] ?? 1) * (n.spec?.includes(b) ? 1.1 : 1);
}

/** القوة القتالية لمجموعة وحدات */
export function stackPower(n: Nation, u: Partial<Units>, xp = 0): number {
  let p = 0;
  for (const k of STATIONED) p += (u[k] ?? 0) * ((UNITS[k].atk + UNITS[k].def) / 2) * unitMult(n, k);
  return p * xpMult(xp);
}

/** الأراضي اللي تقدر الدولة تتمركز فيها (أراضيها + قواعدها العسكرية) */
export function stationable(e: Engine, n: Nation): Set<TerrId> {
  const set = new Set<TerrId>();
  for (const t of e.owned(n.id)) set.add(t.id);
  for (const b of e.s.bases ?? []) if (b.owner === n.id && e.s.terr[b.terr]?.owner === b.host) set.add(b.terr);
  return set;
}

/** الميناء الرئيسي: العاصمة لو ساحلية، وإلا أكبر أرض ساحلية */
export function homePort(e: Engine, n: Nation): TerrId {
  if (e.w.get(n.capital).c) return n.capital;
  const ports = e.owned(n.id).filter((t) => e.w.get(t.id).c).sort((a, b) => b.gdp - a.gdp);
  return ports[0]?.id ?? n.capital;
}

function stackOf(n: Nation, t: TerrId) {
  return (n.place[t] ??= { u: emptyUnits(), xp: 0 });
}

/** دمج خبرة: متوسط موزون بعدد الوحدات */
function mergeXp(curCount: number, curXp: number, addCount: number, addXp: number) {
  const tot = curCount + addCount;
  return tot > 0 ? (curCount * curXp + addCount * addXp) / tot : 0;
}

/** نضيف وحدات لأرض (ولو مو لك نوديها العاصمة) */
export function addAt(e: Engine, n: Nation, t: TerrId, u: Partial<Units>, xp = 0) {
  const ok = stationable(e, n);
  const at = ok.has(t) ? t : n.capital;
  const st = stackOf(n, at);
  const add = unitCount(u);
  st.xp = mergeXp(unitCount(st.u), st.xp, add, xp);
  for (const k of STATIONED) {
    const x = Math.max(0, Math.floor(u[k] ?? 0));
    st.u[k] += x;
    n.units[k] += x;
  }
  for (const k of ['missile', 'nuke'] as const) n.units[k] += Math.max(0, Math.floor(u[k] ?? 0));
}

/** نسحب وحدات من أرض (بحدود الموجود). يرجع اللي انسحب فعلاً */
export function takeAt(n: Nation, t: TerrId, u: Partial<Units>): Units {
  const out = emptyUnits();
  const st = n.place[t];
  if (!st) return out;
  for (const k of STATIONED) {
    const x = clamp(Math.floor(u[k] ?? 0), 0, Math.min(st.u[k], n.units[k]));
    st.u[k] -= x;
    n.units[k] -= x;
    out[k] = x;
  }
  return out;
}

/**
 * نخلي التوزيع يطابق المجموع: أي زيادة بالمجموع (تجنيد، مكافآت) تروح للعاصمة (السفن للميناء)،
 * وأي نقص (خسائر عامة، تسريح) ينسحب بالتناسب، والجيوش في أراضي ما عادت لك ترجع للعاصمة
 */
export function syncPlaces(e: Engine, n: Nation) {
  if (!n.place) n.place = {};
  if (!n.alive) { n.place = {}; return; }
  const ok = stationable(e, n);
  if (!ok.has(n.capital)) return;
  for (const t of Object.keys(n.place)) {
    if (ok.has(t)) continue;
    const st = n.place[t];
    delete n.place[t];
    const cap = stackOf(n, n.capital);
    cap.xp = mergeXp(unitCount(cap.u), cap.xp, unitCount(st.u), st.xp);
    for (const k of STATIONED) cap.u[k] += st.u[k];
  }
  const port = homePort(e, n);
  for (const k of STATIONED) {
    let sum = 0;
    for (const st of Object.values(n.place)) sum += st.u[k];
    let diff = n.units[k] - sum;
    if (diff > 0) {
      const st = stackOf(n, k === 'ship' ? port : n.capital);
      st.xp = mergeXp(unitCount(st.u), st.xp, diff, 0);
      st.u[k] += diff;
    } else if (diff < 0) {
      // نسحب من أكبر الجيوش أول
      const stacks = Object.values(n.place).filter((st) => st.u[k] > 0).sort((a, b) => b.u[k] - a.u[k]);
      for (const st of stacks) {
        if (diff >= 0) break;
        const x = Math.min(st.u[k], Math.ceil((-diff * st.u[k]) / Math.max(1, sum)) || 1, -diff);
        st.u[k] -= x;
        diff += x;
      }
      for (const st of stacks) {
        if (diff >= 0) break;
        const x = Math.min(st.u[k], -diff);
        st.u[k] -= x;
        diff += x;
      }
    }
  }
  for (const [t, st] of Object.entries(n.place)) if (t !== n.capital && unitCount(st.u) <= 0) delete n.place[t];
}

/** التوزيع الأول للجيش وقت ما تبدأ الدولة: نص بالعاصمة والباقي على المناطق */
export function initialPlaces(e: Engine, n: Nation) {
  n.place = {};
  const terrs = e.owned(n.id);
  const others = terrs.filter((t) => t.id !== n.capital);
  const cap = stackOf(n, n.capital);
  for (const k of STATIONED) {
    let left = n.units[k];
    if (others.length && k !== 'ship') {
      const share = Math.floor((left * 0.5) / others.length);
      for (const t of others) {
        if (share <= 0) break;
        stackOf(n, t.id).u[k] += share;
        left -= share;
      }
    }
    cap.u[k] += left;
  }
  syncPlaces(e, n);
}

// ---------------- الحركة ----------------
export function deployDays(e: Engine, n: Nation, from: TerrId, to: TerrId, gen?: General): number {
  let speed = (1 + 0.12 * n.b.infra) * (gen?.kind === 'speed' ? 1.5 : 1);
  if ((n.fx.blitz ?? 0) > e.s.day) speed *= 2;
  const d = e.w.centerDist(from, to);
  return clamp(Math.round(d / (60 * speed)), 3, 45);
}

export function generalAt(n: Nation, t: TerrId): General | undefined {
  return n.generals?.find((g) => g.at === t);
}

/** نقل قوات بين أراضيك */
export function cmdMove(e: Engine, n: Nation, from: TerrId, to: TerrId, req: Partial<Units>, withGen = false): CmdResult {
  const s = e.s;
  const ok = stationable(e, n);
  if (from === to) return { ok: false, msg: 'اختر أرض ثانية' };
  if (!ok.has(from) || !ok.has(to)) return { ok: false, msg: 'تقدر تنقل قوات بين أراضيك وقواعدك بس' };
  if (s.battles.some((b) => b.terr === from && b.def === n.id)) return { ok: false, msg: 'الجيش هنا في معركة' };
  const st = n.place[from];
  if (!st) return { ok: false, msg: 'ما فيه قوات هنا' };
  const want: Partial<Units> = {};
  for (const k of STATIONED) want[k] = clamp(Math.floor(req[k] ?? 0), 0, st.u[k]);
  if (!e.w.get(to).c) want.ship = 0;
  if (unitCount(want) < 1) return { ok: false, msg: 'اختر قوات تنقلها' };
  const xp = st.xp;
  const u = takeAt(n, from, want);
  const gen = withGen ? generalAt(n, from) : undefined;
  const days = deployDays(e, n, from, to, gen);
  const units = { ...emptyUnits(), ...u };
  const naval = !e.w.isLandNeighbor(from, to) && !!e.w.get(from).c && !!e.w.get(to).c && e.w.centerDist(from, to) > 1500;
  s.moves.push({ id: e.id(), owner: n.id, from, to, units, depart: s.day, arrive: s.day + days, kind: 'deploy', xp, gen: gen?.id, naval });
  if (gen) gen.at = '';
  syncPlaces(e, n);
  return { ok: true, msg: `🚚 القوات بالطريق، توصل بعد ${days} يوم` };
}

// ---------------- التطوير والتخصص ----------------
export function upgradeCost(n: Nation, b: Branch) {
  const next = (n.gen[b] ?? 1) + 1;
  const spec = n.spec.includes(b) ? 0.65 : n.spec.length === 0 ? 0.85 : 1;
  return { cost: Math.round((GEN_COST[next] ?? 0) * spec), days: Math.round((GEN_DAYS[next] ?? 0) * (n.spec.includes(b) ? 0.7 : 1)) };
}

export function cmdUpgrade(e: Engine, n: Nation, b: Branch): CmdResult {
  if (!BRANCH_DEFS[b]) return { ok: false };
  const g = n.gen[b] ?? 1;
  if (g >= MAX_GEN) return { ok: false, msg: 'وصلت لأعلى جيل' };
  if (n.tech < g + 1) return { ok: false, msg: `تحتاج تكنولوجيا مستوى ${g + 1} على الأقل` };
  if (n.q.some((q) => q.kind === 'project' && q.type === 'gen:' + b)) return { ok: false, msg: 'التطوير شغال' };
  const { cost, days } = upgradeCost(n, b);
  if (n.treasury < cost) return { ok: false, msg: 'الخزينة ما تكفي' };
  n.treasury -= cost;
  n.q.push({ id: e.id(), kind: 'project', type: 'gen:' + b, count: 1, left: days, total: days, cost });
  return { ok: true, msg: `🔧 بدأ تطوير ${BRANCH_DEFS[b].name} للجيل ${g + 1}` };
}

export function cmdSpecialize(e: Engine, n: Nation, b: Branch): CmdResult {
  if (!BRANCH_DEFS[b]) return { ok: false };
  if (n.spec.includes(b)) return { ok: false, msg: 'هذا تخصصك أصلاً' };
  if (n.spec.length >= MAX_SPECS) return { ok: false, msg: `أقصى شي ${MAX_SPECS} تخصصات` };
  if (n.q.some((q) => q.kind === 'project' && q.type.startsWith('spec:'))) return { ok: false, msg: 'فيه مجمع صناعات قيد البناء' };
  const cost = SPEC_PROJECT.cost;
  if (n.treasury < cost) return { ok: false, msg: 'الخزينة ما تكفي' };
  n.treasury -= cost;
  n.q.push({ id: e.id(), kind: 'project', type: 'spec:' + b, count: 1, left: SPEC_PROJECT.days, total: SPEC_PROJECT.days, cost });
  return { ok: true, msg: `🏭 بدأ بناء مجمع ${BRANCH_DEFS[b].name}` };
}

/** لما يخلص مشروع تطوير أو تخصص */
export function finishProject(e: Engine, n: Nation, type: string) {
  const [kind, b] = type.split(':') as [string, Branch];
  if (kind === 'gen') {
    n.gen[b] = Math.min(MAX_GEN, (n.gen[b] ?? 1) + 1);
    e.news(BRANCH_DEFS[b].icon, `${n.name} طوّرت ${BRANCH_DEFS[b].name} للجيل ${n.gen[b]} (${BRANCH_DEFS[b].gens[n.gen[b]]})`, 'econ', { n: [n.id] });
  } else if (kind === 'spec') {
    if (!n.spec.includes(b)) n.spec.push(b);
    n.gen[b] = Math.min(MAX_GEN, Math.max(n.gen[b] ?? 1, Math.min(n.tech, (n.gen[b] ?? 1) + 1)));
    e.news('🏭', `${n.name} صار عندها تخصص جديد: ${BRANCH_DEFS[b].name}`, 'econ', { n: [n.id] });
  }
}

// ---------------- الجنرالات ----------------
export function cmdGeneral(e: Engine, n: Nation, act: 'hire' | 'fire' | 'station', id?: number, at?: TerrId): CmdResult {
  n.generals ??= [];
  if (act === 'hire') {
    if (n.generals.length >= MAX_GENERALS) return { ok: false, msg: `أقصى عدد ${MAX_GENERALS} جنرالات` };
    const cost = generalCost(n.generals.length, n.d.gdp);
    if (n.treasury < cost) return { ok: false, msg: 'الخزينة ما تكفي' };
    n.treasury -= cost;
    const g = newGeneral(e, n);
    n.generals.push(g);
    return { ok: true, msg: `${GENERALS[g.kind].icon} انضم ${g.name} (${GENERALS[g.kind].name}) لجيشك` };
  }
  const g = n.generals.find((x) => x.id === id);
  if (!g) return { ok: false };
  if (act === 'fire') {
    n.generals = n.generals.filter((x) => x.id !== id);
    return { ok: true, msg: `تقاعد ${g.name}` };
  }
  if (!g.at) return { ok: false, msg: 'الجنرال مع جيش بالطريق' };
  if (!at || !stationable(e, n).has(at)) return { ok: false, msg: 'اختر أرض من أراضيك' };
  g.at = at;
  return { ok: true, msg: `${g.name} انتقل لـ ${e.tname(at)}` };
}

export function newGeneral(e: Engine, n: Nation, kind?: GeneralKind): General {
  const kinds = Object.keys(GENERALS) as GeneralKind[];
  const used = new Set((n.generals ?? []).map((g) => g.name));
  const names = GENERAL_NAMES.filter((x) => !used.has(x));
  return { id: e.id(), name: names.length ? e.pick(names) : 'جنرال ' + e.randInt(1, 99), kind: kind ?? e.pick(kinds), lvl: 1, wins: 0, at: n.capital };
}

/** قوة الجنرال حسب مستواه */
export const genLevel = (g?: General) => (g ? 1 + 0.25 * (g.lvl - 1) : 0);

/** الجنرال انتصر: يكسب خبرة ومستوى */
export function generalWon(e: Engine, n: Nation, g?: General) {
  if (!g) return;
  g.wins++;
  if (g.lvl < 5 && g.wins >= g.lvl * 2) {
    g.lvl++;
    e.news('🎖️', `${g.name} ترقّى للمستوى ${g.lvl}!`, 'battle', { to: [n.id] });
  }
}

/** الجنرال خسر: ممكن يموت أو ينأسر */
export function generalLost(e: Engine, n: Nation, g: General | undefined, p: number): boolean {
  if (!g || e.rand() >= p) return false;
  n.generals = n.generals.filter((x) => x.id !== g.id);
  e.news('🪦', `${g.name} سقط في المعركة!`, 'battle', { to: [n.id] });
  return true;
}

/** الجيوش المتمركزة كقائمة (للواجهة والبوتات) */
export function armies(e: Engine, n: Nation) {
  return Object.entries(n.place ?? {})
    .map(([t, st]) => ({ t, st, power: stackPower(n, st.u, st.xp), gen: generalAt(n, t) }))
    .filter((a) => a.power > 0 || a.gen)
    .sort((a, b) => b.power - a.power);
}

export { clamp as armyClamp };
