// محرك اللعبة: يشتغل عند صاحب الغرفة (أو على جهازك في اللعب الفردي)
import {
  AREA_SLICES, BOT_NAMES, BUILDINGS, BUILD_GROWTH, MAX_BUILDING_LEVEL, DAYS_PER_MONTH, ECON_VALUES, GOVS, MAX_TECH,
  MIL_TIERS, NATION_COLORS, NUKE_PROJECT, POP_VALUES, RESOURCES, SHIP_CAPACITY, SLOTS_BY_CLASS, STATIC_SLICES,
  TECH_COST, TECH_NAMES, TERRAINS, UNITS, emptyUnits, missileRange, navalRange, techMult, type Slice,
} from './defs';
import { aiThink } from './ai';
import { endBattle, startBattle, tickBattles, unitsInBattles } from './battle';
import { assignMission, checkCoalition, checkMissions, checkTransitional, fireWorldEvent, scheduleWorld, spinFortune } from './events';
import type {
  BuildingType, CmdResult, Command, Derived, GameState, LeaderId, LuckId, MissionId, Movement, Nation, NationId, News, NewsKind,
  Player, Proposal, ProposalType, Relation, Report, Settings, TerrainId, Territory, TerrId, UnitType, Units, WheelId,
  WheelState, GovId, ResId,
} from './types';
import { BUILDING_TYPES, COMBAT_UNITS, UNIT_TYPES, WHEEL_ORDER } from './types';
import type { World } from './world';

export const STATE_VERSION = 2;

export const DEFAULT_SETTINGS: Settings = {
  bots: 6, difficulty: 'normal', win: 'score', years: 20, percent: 40, neutral: 'normal', peaceMonths: 12, speed: 1,
};

const emptyDerived = (): Derived => ({
  gdp: 0, income: 0, upkeep: 0, pop: 0, power: 0, score: 0, area: 0, terrs: 0, research: 0, slots: 0, used: 0, manpower: 0, atWar: 0,
});

export const pairKey = (a: NationId, b: NationId) => (a < b ? `${a}|${b}` : `${b}|${a}`);
const clamp = (x: number, a: number, b: number) => Math.max(a, Math.min(b, x));
const round1 = (x: number) => Math.round(x * 10) / 10;

export function newState(mode: 'single' | 'online', settings: Settings, hostId: string, seed?: number): GameState {
  return {
    v: STATE_VERSION, mode, phase: 'lobby', settings: { ...settings }, day: 0, paused: false, speed: settings.speed,
    rng: (seed ?? Math.floor(Math.random() * 2 ** 31)) >>> 0, seq: 1, hostId,
    players: {}, nations: {}, terr: {}, wheels: {}, taken: {}, moves: [], rel: {}, props: [], news: [], reports: [], chat: [],
    battles: [], nextWorld: 0, mods: {},
  };
}

export function unitPower(u: Partial<Units>, tech: number): number {
  let p = 0;
  for (const k of COMBAT_UNITS) p += (u[k] ?? 0) * (UNITS[k].atk + UNITS[k].def) / 2;
  return p * techMult(tech);
}

export class Engine {
  s: GameState;
  w: World;
  /** يُستدعى لما يصير شي مهم (للأصوات والتنبيهات عند صاحب الجهاز) */
  onNews?: (n: News) => void;

  constructor(world: World, state: GameState) {
    this.w = world;
    this.s = state;
  }

  // ---------------- أدوات ----------------
  rand(): number {
    // mulberry32
    let t = (this.s.rng = (this.s.rng + 0x6d2b79f5) >>> 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }
  randInt(a: number, b: number) { return a + Math.floor(this.rand() * (b - a + 1)); }
  pick<T>(arr: T[]): T { return arr[Math.floor(this.rand() * arr.length)]; }
  weighted(ws: number[]): number {
    const tot = ws.reduce((a, b) => a + b, 0);
    let r = this.rand() * tot;
    for (let i = 0; i < ws.length; i++) { r -= ws[i]; if (r < 0) return i; }
    return ws.length - 1;
  }
  id() { return ++this.s.seq; }

  news(icon: string, text: string, kind: NewsKind, extra: Partial<News> = {}) {
    const n: News = { id: this.id(), day: this.s.day, icon, text, kind, ...extra };
    this.s.news.push(n);
    if (this.s.news.length > 70) this.s.news.splice(0, this.s.news.length - 70);
    this.onNews?.(n);
    return n;
  }

  tname(t: TerrId) { return this.w.name(t); }
  nname(id: NationId) { return id ? this.s.nations[id]?.name ?? '؟' : 'دولة محايدة'; }

  // ---------------- اللاعبين واللوبي ----------------
  addPlayer(id: string, name: string): Player {
    const ex = this.s.players[id];
    if (ex) { ex.name = name || ex.name; ex.online = true; ex.lastSeen = Date.now(); return ex; }
    const num = Object.keys(this.s.players).length + 1;
    let nid = `P${num}`;
    while (this.s.wheels[nid] || this.s.nations[nid] || Object.values(this.s.players).some((p) => p.nation === nid)) nid = `P${num}${this.randInt(1, 999)}`;
    const p: Player = { id, name: name.slice(0, 20) || `لاعب ${num}`, nation: nid, online: true, joinedAt: Date.now(), lastSeen: Date.now() };
    this.s.players[id] = p;
    // لو دخل وقت العجلات أو وسط اللعبة يلف عجلاته (ولو اللعبة منتهية يتفرج بس)
    if (this.s.phase === 'wheels' || this.s.phase === 'playing') {
      this.s.wheels[nid] = { res: {}, respins: 1, done: false, ready: false };
      this.news('👋', `${p.name} انضم للعبة ويلف عجلاته الحين`, 'join');
    }
    return p;
  }

  removePlayer(id: string) {
    const p = this.s.players[id];
    if (!p) return;
    if (this.s.phase === 'lobby') delete this.s.players[id];
    else p.online = false;
  }

  setOnline(id: string, online: boolean) {
    const p = this.s.players[id];
    if (!p) return;
    p.online = online;
    p.lastSeen = Date.now();
    const n = this.s.nations[p.nation];
    if (n && n.alive) n.aiControl = !online;
    const ws = this.s.wheels[p.nation];
    if (!online && ws && !ws.ready && (this.s.phase === 'playing' || this.s.phase === 'wheels')) {
      // لاعب طلع وهو يلف: نكمل عنه
      this.autospin(p.nation);
      this.ready(p.nation);
    }
  }

  // ---------------- العجلات ----------------
  startWheels() {
    const s = this.s;
    s.phase = 'wheels';
    this.generateNeutrals();
    for (const p of Object.values(s.players)) s.wheels[p.nation] = { res: {}, respins: 1, done: false, ready: false };
    for (let i = 1; i <= s.settings.bots; i++) {
      const nid = `B${i}`;
      s.wheels[nid] = { res: {}, respins: 0, done: false, ready: true };
      this.autospin(nid);
    }
  }

  generateNeutrals() {
    const POP_RANGE = [[0.2, 3], [2, 15], [6, 45], [15, 90], [20, 160], [60, 600]];
    const str = { weak: 0.6, normal: 1, strong: 1.6 }[this.s.settings.neutral];
    for (const m of this.w.list) {
      const [lo, hi] = POP_RANGE[m.cls];
      const pop = round1(Math.exp(Math.log(lo) + this.rand() * (Math.log(hi) - Math.log(lo))));
      const pc = 2 + this.rand() ** 2 * 30;
      const gdp = Math.max(1, Math.round(pop * pc));
      const inf = Math.max(2, Math.round((4 + m.cls * 6 + Math.sqrt(pop) * 1.5) * (0.8 + this.rand() * 0.5) * str));
      const tank = Math.round((m.cls * 4 + this.rand() * m.cls * 3) * str);
      const t: Territory = { id: m.id, owner: '', pop, gdp, unrest: 0, nuked: 0, g: { inf, tank }, nt: this.rand() < 0.35 ? 2 : 1 };
      t.gmax = inf * 2 + tank * 3.5;
      this.s.terr[m.id] = t;
    }
  }

  nextWheel(nid: NationId): WheelId | null {
    const ws = this.s.wheels[nid];
    if (!ws) return null;
    for (const w of WHEEL_ORDER) if (ws.res[w] === undefined) return w;
    return null;
  }

  /** الخيارات المتاحة لعجلة المكان */
  countryCandidates(nid: NationId): TerrId[] {
    const ws = this.s.wheels[nid];
    const cls = ws?.res.area as number;
    const free = (c: number) =>
      this.w.list.filter((m) => m.p && m.cls === c && this.s.terr[m.id]?.owner === '' && !this.s.taken[m.id]).map((m) => m.id);
    let list = free(cls);
    // لو خلصت الدول بهذا الحجم نروح لأقرب حجم فيه دول
    for (let d = 1; !list.length && d < 6; d++) list = [...free(cls - d), ...free(cls + d)];
    return list;
  }

  slicesFor(nid: NationId, wheel: WheelId): Slice[] {
    if (wheel === 'country') {
      return this.countryCandidates(nid).map((id) => ({ label: this.tname(id), icon: '', w: 1, v: id }));
    }
    if (wheel === 'area') {
      return AREA_SLICES.map((sl) => {
        const avail = this.w.list.some((m) => m.p && m.cls === sl.v && this.s.terr[m.id]?.owner === '' && !this.s.taken[m.id]);
        return { ...sl, w: avail ? sl.w : 0 };
      });
    }
    return STATIC_SLICES[wheel]!;
  }

  private doSpin(nid: NationId, wheel: WheelId, exclude?: number | string) {
    const ws = this.s.wheels[nid];
    let slices = this.slicesFor(nid, wheel);
    if (exclude !== undefined && slices.filter((x) => x.w > 0).length > 1) slices = slices.map((x) => (x.v === exclude ? { ...x, w: 0 } : x));
    if (!slices.length) return;
    const i = this.weighted(slices.map((x) => x.w));
    const v = slices[i].v;
    ws.res[wheel] = v;
    if (wheel === 'country') this.s.taken[v as string] = nid;
    if (wheel === 'luck' && v === 'respin') ws.respins += 2;
    ws.last = { wheel, nonce: (ws.last?.nonce ?? 0) + 1 };
    ws.done = this.nextWheel(nid) === null;
  }

  /** اللاعب شاف بطاقة دولته وضغط «جاهز» */
  ready(nid: NationId): CmdResult {
    const ws = this.s.wheels[nid];
    if (!ws) return { ok: false };
    if (!ws.done) return { ok: false, msg: 'كمّل عجلاتك أول' };
    if (ws.ready && this.s.phase !== 'playing') return { ok: true };
    ws.ready = true;
    if (this.s.phase === 'playing' && !this.s.nations[nid]) this.spawnLate(nid);
    return { ok: true };
  }

  /** صاحب الغرفة يبدأ بدون انتظار: نكمل عجلات الكل */
  readyAll() {
    for (const nid of Object.keys(this.s.wheels)) {
      this.autospin(nid);
      this.s.wheels[nid].ready = true;
    }
  }

  spin(nid: NationId, wheel: WheelId): CmdResult {
    const ws = this.s.wheels[nid];
    if (!ws) return { ok: false, msg: 'ما عندك عجلات' };
    const next = this.nextWheel(nid);
    if (next !== wheel) return { ok: false, msg: 'مو دور هذي العجلة' };
    this.doSpin(nid, wheel);
    return { ok: true };
  }

  respin(nid: NationId, wheel: WheelId): CmdResult {
    const ws = this.s.wheels[nid];
    if (!ws || ws.res[wheel] === undefined) return { ok: false, msg: 'لازم تلف العجلة أول' };
    if (ws.respins <= 0) return { ok: false, msg: 'خلصت إعادات اللف' };
    if (ws.ready) return { ok: false, msg: 'أكدت جاهزيتك خلاص' };
    if (wheel === 'luck' && ws.res.luck === 'respin') return { ok: false, msg: 'ما تقدر تعيد عجلة "فرصة ثانية"' };
    ws.respins--;
    const old = ws.res[wheel];
    if (wheel === 'area' || wheel === 'country') {
      const c = ws.res.country as string | undefined;
      if (c && this.s.taken[c] === nid) delete this.s.taken[c];
    }
    if (wheel === 'area') {
      delete ws.res.country;
      delete ws.res.area;
      this.doSpin(nid, 'area', old);
    } else {
      delete ws.res[wheel];
      this.doSpin(nid, wheel, old);
    }
    return { ok: true };
  }

  autospin(nid: NationId) {
    let w: WheelId | null;
    let guard = 0;
    while ((w = this.nextWheel(nid)) && guard++ < 20) this.doSpin(nid, w);
  }

  allWheelsDone(): boolean {
    return Object.values(this.s.wheels).every((w) => w.done && w.ready);
  }

  /** بداية اللعبة بعد ما يخلص الكل من العجلات */
  finishWheels() {
    const s = this.s;
    if (s.phase !== 'wheels') return;
    for (const nid of Object.keys(s.wheels)) if (!s.wheels[nid].done) this.autospin(nid);
    let i = 0;
    for (const [nid, ws] of Object.entries(s.wheels)) {
      this.createNation(nid, ws, i++);
    }
    s.wheels = {};
    s.taken = {};
    s.phase = 'playing';
    s.day = 0;
    s.battles = [];
    scheduleWorld(this, true);
    this.news('🌍', 'بدأت اللعبة! ابنِ اقتصادك وجهّز جيشك', 'system');
    if (s.settings.peaceMonths > 0) this.news('🕊️', `فترة سلام ${s.settings.peaceMonths} شهر: ما أحد يقدر يهاجم دولة لاعب أو بوت، بس تقدر تحتل الدول المحايدة`, 'system');
    for (const n of Object.values(s.nations)) this.recompute(n);
  }

  private spawnLate(nid: NationId) {
    const ws = this.s.wheels[nid];
    const used = Object.keys(this.s.nations).length;
    this.createNation(nid, ws, used);
    delete this.s.wheels[nid];
    const c = ws.res.country as string;
    delete this.s.taken[c];
    this.recompute(this.s.nations[nid]);
  }

  private createNation(nid: NationId, ws: WheelState, idx: number) {
    const s = this.s;
    const r = ws.res;
    const isBot = nid.startsWith('B');
    const player = Object.values(s.players).find((p) => p.nation === nid);
    const country = r.country as TerrId;
    const t = s.terr[country];
    const cls = this.w.get(country).cls;
    const popTier = r.pop as number;
    const econTier = r.econ as number;
    const milTier = r.mil as number;
    t.owner = nid;
    t.pop = POP_VALUES[popTier];
    t.gdp = ECON_VALUES[econTier];
    t.unrest = 0;
    delete t.g; delete t.gmax; delete t.nt;
    const gov = r.gov as GovId;
    const res = r.res as ResId;
    const luck = r.luck as LuckId;
    const units = { ...emptyUnits(), ...MIL_TIERS[milTier] };
    const usedColors = new Set(Object.values(s.nations).map((n) => n.color));
    const color = NATION_COLORS.find((c) => !usedColors.has(c)) ?? NATION_COLORS[idx % NATION_COLORS.length];
    const leader = isBot ? BOT_NAMES[(parseInt(nid.slice(1)) - 1 + Math.floor(s.rng % 7)) % BOT_NAMES.length] : player?.name ?? 'لاعب';
    const trait = r.leader as LeaderId;
    const now = s.phase === 'playing' ? s.day : 0;
    const n: Nation = {
      id: nid, kind: isBot ? 'bot' : 'player', name: this.tname(country), leader, color, home: country, capital: country,
      alive: true, treasury: Math.round(15 + 0.1 * t.gdp), tax: 0.22,
      stability: clamp(62 + GOVS[gov].stab + RESOURCES[res].stab + (trait === 'populist' ? 12 : 0), 5, 100),
      tech: r.tech as number, research: 0, units, q: [], bq: [],
      b: Object.fromEntries(BUILDING_TYPES.map((b) => [b, 0])) as Record<BuildingType, number>,
      gov, res, luck, nukeProg: res === 'uranium',
      trait, terrain: r.terrain as TerrainId, mission: { id: r.mission as MissionId, target: 0, done: false },
      fortuneNext: now + 180, bonus: 0, govUntil: gov === 'transitional' ? now + 48 * DAYS_PER_MONTH : undefined,
      st: { won: 0, lost: 0, conq: 0, lostT: 0, held: 0 },
      tiers: { area: cls, pop: popTier, econ: econTier, mil: milTier },
      d: emptyDerived(), joinDay: s.phase === 'playing' ? s.day : 0,
    };
    if (isBot) {
      const pers = this.pick(['aggressive', 'balanced', 'balanced', 'economic', 'defensive'] as const);
      n.ai = { pers, next: this.randInt(3, 20) + s.day };
    }
    // تأثير عجلة المفاجأة
    switch (luck) {
      case 'treasure': n.treasury += Math.round(0.25 * t.gdp + 30); break;
      case 'nuke': n.units.nuke += 1; break;
      case 'mercs': n.units.inf += 20; n.units.tank += 8; break;
      case 'genius': n.tech = Math.min(MAX_TECH, n.tech + 1); break;
      case 'fortress': n.b.fort += 3; break;
      case 'missiles': n.units.missile += 8; break;
      case 'aid': n.treasury += 80; n.stability = clamp(n.stability + 10, 0, 100); break;
      case 'plague': t.pop = round1(t.pop * 0.75); break;
      case 'civilwar':
        for (const u of UNIT_TYPES) n.units[u] = Math.floor(n.units[u] * 0.6);
        n.stability = clamp(n.stability - 20, 5, 100);
        break;
      case 'crisis': t.gdp = Math.round(t.gdp * 0.75); n.treasury = Math.round(n.treasury * 0.5); break;
      case 'satellite': n.research += (TECH_COST[n.tech + 1] ?? 0) * 0.5; n.units.missile += 3; break;
      case 'worldcup': n.treasury += 60; n.stability = clamp(n.stability + 15, 0, 100); break;
      case 'braindrain': n.research += 150; t.pop = round1(t.pop * 1.05); break;
      case 'oilfield': if (n.res === 'none') n.res = 'oil'; else t.gdp = Math.round(t.gdp * 1.1); break;
      case 'traitor': for (const u of COMBAT_UNITS) n.units[u] = Math.floor(n.units[u] * 0.75); break;
      case 'volcano': t.gdp = Math.round(t.gdp * 0.85); t.pop = round1(t.pop * 0.95); break;
    }
    assignMission(this, n, n.mission.id);
    s.nations[nid] = n;
    if (s.phase === 'playing') {
      this.news('🎉', `${leader} دخل اللعبة ويحكم ${n.name}`, 'join', { n: [nid], terr: country });
    }
  }

  // ---------------- العلاقات ----------------
  rel(a: NationId, b: NationId): Relation {
    const k = pairKey(a, b);
    return this.s.rel[k] ?? (this.s.rel[k] = {});
  }
  peek(a: NationId, b: NationId): Relation | undefined { return this.s.rel[pairKey(a, b)]; }
  atWar(a: NationId, b: NationId) { return !!this.peek(a, b)?.war; }
  allied(a: NationId, b: NationId) { return !!this.peek(a, b)?.ally; }
  trading(a: NationId, b: NationId) { return !!this.peek(a, b)?.trade; }
  inTruce(a: NationId, b: NationId) { const r = this.peek(a, b); return !!r?.truce && r.truce > this.s.day; }
  allies(a: NationId): NationId[] {
    return Object.values(this.s.nations).filter((n) => n.alive && n.id !== a && this.allied(a, n.id)).map((n) => n.id);
  }
  enemies(a: NationId): NationId[] {
    return Object.values(this.s.nations).filter((n) => n.alive && n.id !== a && this.atWar(a, n.id)).map((n) => n.id);
  }
  peaceEnd(a: Nation, b: Nation) {
    return Math.max(a.joinDay, b.joinDay) + this.s.settings.peaceMonths * DAYS_PER_MONTH;
  }

  /** هل تقدر الدولة a تهاجم الدولة b؟ */
  canHit(a: Nation, b: Nation): string | null {
    if (a.id === b.id) return 'هذي دولتك!';
    if (!b.alive) return 'الدولة سقطت';
    if (this.allied(a.id, b.id)) return 'هذي دولة حليفة، لازم تفسخ التحالف أول';
    if (this.inTruce(a.id, b.id)) return 'بينكم هدنة لين ' + this.dateStr(this.peek(a.id, b.id)!.truce!);
    if (this.s.day < this.peaceEnd(a, b)) return 'فترة السلام ما خلصت (لين ' + this.dateStr(this.peaceEnd(a, b)) + ')';
    return null;
  }

  dateStr(day: number) {
    const m = Math.floor(day / DAYS_PER_MONTH);
    const months = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'];
    return `${months[m % 12]} ${2026 + Math.floor(m / 12)}`;
  }

  declareWar(a: Nation, b: Nation, quiet = false) {
    const r = this.rel(a.id, b.id);
    if (r.war) return;
    r.war = this.s.day;
    delete r.trade;
    delete r.ally;
    this.s.props = this.s.props.filter((p) => !((p.from === a.id && p.to === b.id) || (p.from === b.id && p.to === a.id)));
    if (!quiet) this.news('⚔️', `${a.name} أعلنت الحرب على ${b.name}!`, 'war', { n: [a.id, b.id] });
  }

  makePeace(a: Nation, b: Nation, months = 24, quiet = false) {
    const r = this.rel(a.id, b.id);
    delete r.war;
    r.truce = this.s.day + months * DAYS_PER_MONTH;
    // نرجع الجيوش المتجهة لبعض ونوقف المعارك بينهم
    for (const m of [...this.s.moves]) {
      if (m.kind === 'attack' && ((m.owner === a.id && this.s.terr[m.to].owner === b.id) || (m.owner === b.id && this.s.terr[m.to].owner === a.id))) {
        this.startReturn(m);
      }
    }
    for (const bt of [...this.s.battles]) {
      if ((bt.att === a.id && bt.def === b.id) || (bt.att === b.id && bt.def === a.id)) endBattle(this, bt, 'cancel');
    }
    if (!quiet) this.news('🕊️', `سلام بين ${a.name} و ${b.name} (هدنة ${months === 24 ? 'سنتين' : months + ' شهر'})`, 'diplo', { n: [a.id, b.id] });
  }

  // ---------------- حسابات الدولة ----------------
  owned(nid: NationId): Territory[] {
    return Object.values(this.s.terr).filter((t) => t.owner === nid);
  }

  movingUnits(nid: NationId): Units {
    const u = emptyUnits();
    for (const m of this.s.moves) if (m.owner === nid) for (const k of UNIT_TYPES) u[k] += m.units[k];
    return u;
  }

  unitCost(n: Nation, u: UnitType) {
    let c = UNITS[u].cost * GOVS[n.gov].unitCost * Math.max(0.5, 1 - 0.06 * n.b.milfac);
    if (n.trait === 'warlord') c *= 0.9;
    if (n.underdog) c *= 0.85;
    if (this.s.mods.arms && this.s.day < this.s.mods.arms) c *= 0.65;
    if (u === 'ship' && n.res === 'ports') c *= 0.75;
    if (u === 'nuke' && n.res === 'uranium') c *= 0.6;
    return c;
  }

  buildCost(n: Nation, b: BuildingType) {
    const def = BUILDINGS[b];
    const lvl = n.b[b] + n.bq.filter((q) => q.type === b).length;
    return Math.max(def.min, def.k * n.d.gdp) * BUILD_GROWTH ** lvl * GOVS[n.gov].buildCost * RESOURCES[n.res].buildCost * (n.trait === 'builder' ? 0.8 : 1);
  }

  buildDays(n: Nation, b: BuildingType) {
    const lvl = n.b[b] + n.bq.filter((q) => q.type === b).length;
    return Math.round((BUILDINGS[b].days * (1 + 0.25 * lvl)) / (GOVS[n.gov].buildSpeed * (n.trait === 'builder' ? 1.2 : 1)));
  }

  prodDays(n: Nation, u: UnitType, count: number) {
    return Math.max(5, Math.round(UNITS[u].days * (1 + 0.15 * (count - 1)) / (GOVS[n.gov].prod * (1 + 0.15 * n.b.milfac))));
  }

  recompute(n: Nation) {
    const d = n.d;
    const terrs = this.owned(n.id);
    let gdpBase = 0, pop = 0, area = 0, slots = 0;
    for (const t of terrs) {
      gdpBase += t.gdp * (t.unrest > 0 ? 0.6 : 1) * (t.nuked > 0 ? 0.5 : 1);
      pop += t.pop;
      const m = this.w.get(t.id);
      area += m.area;
      slots += SLOTS_BY_CLASS[m.cls];
    }
    const resB = RESOURCES[n.res].gdp * (1 + 0.3 * n.b.mining);
    const trades = Object.values(this.s.nations).filter((o) => o.alive && o.id !== n.id && this.trading(n.id, o.id)).length;
    const tradeB = Math.min(0.3, trades * (n.res === 'ports' ? 0.05 : 0.03) * (n.trait === 'diplomat' ? 2 : 1));
    d.gdp = gdpBase * Math.max(0.3, 1 + 0.08 * n.b.industry + 0.04 * (n.tech - 1) + resB + tradeB + TERRAINS[n.terrain].gdp);
    const eff = (0.55 + 0.45 * n.stability / 100) * Math.max(0.6, 1 - 0.012 * Math.max(0, terrs.length - 3));
    d.income = (d.gdp * n.tax * eff * GOVS[n.gov].income * (n.trait === 'economist' ? 1.08 : 1)) / 12 + (n.res === 'gold' ? gdpBase * 0.002 * (1 + 0.3 * n.b.mining) : 0);
    const all = this.movingUnits(n.id);
    const inb = unitsInBattles(this, n.id);
    for (const k of UNIT_TYPES) all[k] += n.units[k] + inb[k];
    for (const q of n.q) if (q.kind === 'unit') all[q.type as UnitType] += q.count;
    let up = 0, man = 0;
    for (const k of UNIT_TYPES) { up += all[k] * UNITS[k].upkeep; man += all[k] * UNITS[k].man; }
    d.upkeep = up;
    d.pop = pop;
    d.area = area;
    d.terrs = terrs.length;
    d.slots = slots + (n.luck === 'fortress' ? 3 : 0);
    d.used = BUILDING_TYPES.reduce((s, b) => s + n.b[b], 0) + n.bq.length;
    d.manpower = Math.round(pop * 40 - man);
    d.research = (1.5 + 2.5 * n.b.research + Math.sqrt(Math.max(0, d.gdp)) / 6) * GOVS[n.gov].research * RESOURCES[n.res].research * (n.trait === 'scientist' ? 1.3 : 1);
    d.power = unitPower(all, n.tech);
    d.atWar = this.enemies(n.id).length;
    d.score = Math.round(area / 20000 + pop + d.gdp * 0.2 + d.power * 0.5 + n.tech * 40 + n.st.won * 3 + n.st.conq * 8 + n.bonus);
  }

  // ---------------- الوقت ----------------
  private acc = 0;
  /** تقديم الوقت بعدد أيام (ممكن كسور) */
  advance(days: number) {
    if (this.s.phase !== 'playing' || this.s.paused) return;
    this.acc += Math.min(days, 12);
    while (this.acc >= 1) {
      this.acc -= 1;
      this.dayTick();
      if (this.s.phase !== 'playing') { this.acc = 0; break; }
    }
  }

  dayTick() {
    const s = this.s;
    s.day++;
    for (const n of Object.values(s.nations)) {
      if (!n.alive) continue;
      // إنتاج الوحدات
      const prodRate = 1;
      for (const q of n.q) q.left -= prodRate;
      const doneUnits = n.q.filter((q) => q.left <= 0);
      if (doneUnits.length) {
        n.q = n.q.filter((q) => q.left > 0);
        for (const q of doneUnits) {
          if (q.kind === 'unit') n.units[q.type as UnitType] += q.count;
          else if (q.kind === 'project' && q.type === 'nuke') {
            n.nukeProg = true;
            this.news('☢️', `${n.name} نجحت في برنامجها النووي!`, 'nuke', { n: [n.id] });
          }
        }
      }
      // البناء (عدد محدود بنفس الوقت)
      const par = 2 + GOVS[n.gov].parallel;
      for (let i = 0; i < Math.min(par, n.bq.length); i++) n.bq[i].left -= 1;
      const doneB = n.bq.filter((q) => q.left <= 0);
      if (doneB.length) {
        n.bq = n.bq.filter((q) => q.left > 0);
        for (const q of doneB) {
          n.b[q.type as BuildingType]++;
          this.news(BUILDINGS[q.type as BuildingType].icon, `اكتمل بناء ${BUILDINGS[q.type as BuildingType].name} (مستوى ${n.b[q.type as BuildingType]})`, 'econ', { to: [n.id] });
        }
        this.recompute(n);
      }
      // الذكاء الاصطناعي
      if ((n.kind === 'bot' || n.aiControl) && s.day >= (n.ai?.next ?? 0)) {
        if (!n.ai) n.ai = { pers: 'balanced', next: s.day };
        aiThink(this, n);
        const diff = n.kind === 'bot' ? s.settings.difficulty : 'normal';
        n.ai.next = s.day + (diff === 'easy' ? 30 : diff === 'hard' ? 16 : 22) + this.randInt(0, 6);
      }
    }
    // الحركات
    const arrived = s.moves.filter((m) => m.arrive <= s.day);
    if (arrived.length) {
      s.moves = s.moves.filter((m) => m.arrive > s.day);
      for (const m of arrived) this.resolveMove(m);
    }
    tickBattles(this);
    if (s.day % DAYS_PER_MONTH === 0) this.monthly();
  }

  monthly() {
    const s = this.s;
    // الدول الأضعف (آخر 40% بالترتيب) تاخذ دعم: جيش أرخص ونمو أسرع
    const ranked = Object.values(s.nations).filter((n) => n.alive).sort((a, b) => b.d.score - a.d.score);
    ranked.forEach((n, i) => { n.underdog = ranked.length >= 3 && i >= Math.ceil(ranked.length * 0.6); });
    for (const n of Object.values(s.nations)) if (n.alive) this.monthlyNation(n);
    // المحايدة: نمو بطيء وتعويض الحامية
    const str = { weak: 0.6, normal: 1, strong: 1.6 }[s.settings.neutral];
    for (const t of Object.values(s.terr)) {
      t.unrest = Math.max(0, t.unrest - 1);
      t.nuked = Math.max(0, t.nuked - 1);
      if (t.owner !== '') continue;
      if (s.battles.some((b) => b.terr === t.id)) continue;
      t.gdp *= 1 + 0.015 / 12;
      t.pop *= 1 + 0.01 / 12;
      if (t.g && t.gmax) {
        // تعويض الحامية (5% شهرياً) والمحايدة تتقوى مع الوقت
        let room = t.gmax - (t.g.inf * 2 + t.g.tank * 3.5);
        let add = t.gmax * 0.05;
        while (room > 0 && add > 0) {
          if (this.rand() < 0.7) { t.g.inf += 1; room -= 2; add -= 2; } else { t.g.tank += 1; room -= 3.5; add -= 3.5; }
        }
        if (s.day % (DAYS_PER_MONTH * 12) === 0) t.gmax *= 1 + 0.06 * str;
      }
    }
    // انتهاء الاقتراحات القديمة
    s.props = s.props.filter((p) => s.day - p.day < 60 && s.nations[p.from]?.alive && s.nations[p.to]?.alive);
    // الأحداث العشوائية
    for (const n of Object.values(s.nations)) if (n.alive && this.rand() < 0.025) this.randomEvent(n);
    for (const n of Object.values(s.nations)) if (n.alive) this.recompute(n);
    checkMissions(this);
    if (s.day % (6 * DAYS_PER_MONTH) === 0) checkCoalition(this);
    if (s.mods.arms && s.day >= s.mods.arms) {
      delete s.mods.arms;
      this.news('⚔️', 'انتهى سباق التسلح، الأسلحة رجعت لأسعارها', 'system');
    }
    if (s.nextWorld > 0 && s.day >= s.nextWorld) {
      fireWorldEvent(this);
      scheduleWorld(this);
    }
    this.checkWin();
  }

  private monthlyNation(n: Nation) {
    this.recompute(n);
    const d = n.d;
    const terrs = this.owned(n.id);
    if (!terrs.length) { this.eliminate(n, null); return; }
    n.treasury += d.income - d.upkeep;
    // الديون
    if (n.treasury < 0) {
      if (n.treasury < -Math.max(20, d.income * 6)) {
        for (const k of COMBAT_UNITS) n.units[k] = Math.floor(n.units[k] * 0.93);
        this.news('💸', `${n.name} مفلسة! تم تسريح جزء من الجيش`, 'econ', { to: [n.id] });
      }
    }
    // النمو
    const pc = d.gdp / Math.max(0.1, d.pop);
    const catchup = pc < 5 ? 0.01 : pc < 15 ? 0.005 : 0;
    const war = d.atWar > 0 ? 0.005 : 0;
    const bonusG = (n.trait === 'economist' ? 0.01 : 0) + TERRAINS[n.terrain].growth + (n.underdog ? 0.01 : 0);
    const g = clamp(0.02 + Math.min(0.02, 0.004 * n.b.infra) + GOVS[n.gov].growth + ((n.stability - 50) / 50) * 0.008 + catchup - war + bonusG, -0.05, 0.07);
    const pg = clamp(0.01 + 0.003 * n.b.health + RESOURCES[n.res].popGrowth + TERRAINS[n.terrain].popGrowth - (war ? 0.002 : 0), -0.02, 0.04);
    for (const t of terrs) {
      t.gdp *= 1 + g / 12;
      t.pop *= 1 + pg / 12;
    }
    // الاستقرار
    const occupied = terrs.filter((t) => t.unrest > 0).length;
    const populist = n.trait === 'populist';
    const target =
      55 + GOVS[n.gov].stab + RESOURCES[n.res].stab + 4 * n.b.health + (populist ? 12 : 0) - (n.tax - 0.2) * 150 * (populist ? 0.5 : 1) -
      d.atWar * 5 * GOVS[n.gov].weariness - occupied * 2 - (n.treasury < 0 ? 15 : 0) - Math.max(0, terrs.length - 5) * 1.5;
    n.stability = clamp(n.stability + (target - n.stability) * 0.15, 0, 100);
    // البحث
    n.research += d.research;
    while (n.tech < MAX_TECH && n.research >= TECH_COST[n.tech + 1]) {
      n.research -= TECH_COST[n.tech + 1];
      n.tech++;
      this.news('🧪', `${n.name} وصلت لتكنولوجيا ${TECH_NAMES[n.tech]} (مستوى ${n.tech})`, 'econ', { n: [n.id] });
    }
    if (n.tech >= MAX_TECH) n.research = Math.min(n.research, 999);
    // مقاومة شعبية: الأراضي المحتلة حديثاً تثور لو الاستقرار ضعيف
    if (n.stability < 50) {
      const p = ((50 - n.stability) / 50) * 0.06;
      let max = 2;
      for (const t of terrs) {
        if (max <= 0) break;
        if (t.unrest > 0 && t.id !== n.capital && this.rand() < p) { this.revolt(t, n); max--; }
      }
    }
    // ثورة: الإمبراطوريات غير المستقرة تخسر أراضي
    if (n.stability < 30 && terrs.length > 1 && this.rand() < 0.1) {
      const cands = terrs.filter((t) => t.id !== n.capital).sort((a, b) => b.unrest - a.unrest);
      const t = cands[0];
      if (t) {
        this.revolt(t, n);
        n.stability += 10;
      }
    }
    checkTransitional(this, n);
  }

  /** أرض تعلن استقلالها وتصير محايدة */
  revolt(t: Territory, n: Nation) {
    t.owner = '';
    t.unrest = 0;
    const inf = Math.max(3, Math.round(Math.sqrt(t.pop) * 2));
    t.g = { inf, tank: Math.round(inf / 4) };
    t.gmax = t.g.inf * 2 + t.g.tank * 3.5;
    t.nt = Math.max(1, n.tech - 1);
    this.news('✊', `ثورة في ${this.tname(t.id)}! أعلنت استقلالها عن ${n.name}`, 'event', { n: [n.id], terr: t.id });
  }

  private randomEvent(n: Nation) {
    const terrs = this.owned(n.id);
    if (!terrs.length) return;
    const t = this.pick(terrs);
    const events: [number, () => void][] = [
      [10, () => { for (const x of terrs) x.gdp *= 1.06; this.news('📈', `طفرة اقتصادية في ${n.name}! الناتج +6%`, 'event', { n: [n.id] }); }],
      [8, () => { t.gdp *= 0.95; t.pop *= 0.995; this.news('🌋', `زلزال قوي ضرب ${this.tname(t.id)} (${n.name})`, 'event', { n: [n.id], terr: t.id }); }],
      [7, () => { for (const x of terrs) x.pop *= 0.97; n.stability -= 5; this.news('🦠', `وباء ينتشر في ${n.name}`, 'event', { n: [n.id] }); }],
      [8, () => { n.stability = Math.max(0, n.stability - 10); this.news('📢', `احتجاجات شعبية في ${n.name}`, 'event', { n: [n.id] }); }],
      [8, () => { n.research += 50; this.news('💡', `اختراق علمي في ${n.name}!`, 'event', { n: [n.id] }); }],
      [7, () => { const x = Math.round(Math.max(5, n.d.income * 3)); n.treasury += x; this.news('🎁', `${n.name} حصلت على استثمارات أجنبية (+${x} مليار)`, 'event', { n: [n.id] }); }],
      [6, () => { const x = Math.round(Math.max(0, n.treasury) * 0.1); n.treasury -= x; this.news('🕵️', `فضيحة فساد في ${n.name}! اختفى ${x} مليار`, 'event', { n: [n.id] }); }],
      [5, () => {
        if (n.res === 'none') { n.res = 'oil'; this.news('🛢️', `${n.name} اكتشفت حقول نفط!`, 'event', { n: [n.id] }); }
        else { t.gdp *= 1.08; this.news('⛏️', `اكتشاف معادن جديدة في ${this.tname(t.id)}`, 'event', { n: [n.id] }); }
      }],
      [5, () => { t.pop *= 1.03; this.news('🧳', `موجة مهاجرين وصلت ${n.name}`, 'event', { n: [n.id] }); }],
      [n.stability < 30 ? 6 : 0, () => {
        for (const k of COMBAT_UNITS) n.units[k] = Math.floor(n.units[k] * 0.9);
        n.stability = Math.max(0, n.stability - 12);
        this.news('🪖', `محاولة انقلاب فاشلة في ${n.name}`, 'event', { n: [n.id] });
      }],
    ];
    const i = this.weighted(events.map((e) => e[0]));
    events[i][1]();
  }

  // ---------------- الحرب ----------------
  /** يحدد من وين تنطلق القوات وهل الهجوم بحري */
  route(n: Nation, to: TerrId): { from: TerrId; naval: boolean; dist: number } | null {
    const terrs = this.owned(n.id);
    let best: { from: TerrId; naval: boolean; dist: number } | null = null;
    for (const t of terrs) {
      if (this.w.isLandNeighbor(t.id, to)) {
        const d = this.w.centerDist(t.id, to);
        if (!best || best.naval || d < best.dist) best = { from: t.id, naval: false, dist: d };
      }
    }
    if (best) return best;
    if (!this.w.get(to).c) return null;
    const range = navalRange(n.tech);
    for (const t of terrs) {
      if (!this.w.get(t.id).c) continue;
      const d = this.w.dist(t.id, to);
      if (d <= range && (!best || d < best.dist)) best = { from: t.id, naval: true, dist: d };
    }
    return best;
  }

  travelDays(n: Nation, from: TerrId, to: TerrId, naval: boolean) {
    const speed = 1 + 0.12 * n.b.infra;
    if (naval) return clamp(Math.round((this.w.dist(from, to) + 400) / (110 * speed)), 8, 75);
    return clamp(Math.round(this.w.centerDist(from, to) / (45 * speed)), 6, 60);
  }

  strikeRange(n: Nation, to: TerrId): number {
    let best = Infinity;
    for (const t of this.owned(n.id)) best = Math.min(best, this.w.dist(t.id, to));
    return best;
  }

  private applyLoss(units: Partial<Units>, frac: number, target: Units | Partial<Units>): Partial<Units> {
    const loss: Partial<Units> = {};
    for (const k of COMBAT_UNITS) {
      const have = units[k] ?? 0;
      if (!have) continue;
      const exact = have * frac;
      let l = Math.floor(exact);
      if (this.rand() < exact - l) l++;
      l = Math.min(l, have, (target[k] ?? 0));
      if (l > 0) { loss[k] = l; target[k] = (target[k] ?? 0) - l; }
    }
    return loss;
  }

  startReturn(m: Movement) {
    const total = UNIT_TYPES.reduce((s, k) => s + m.units[k], 0);
    if (!total) return;
    const dur = Math.max(3, Math.round((m.arrive - m.depart) * 0.8));
    const back: Movement = { id: this.id(), owner: m.owner, from: m.to, to: m.from, units: m.units, depart: this.s.day, arrive: this.s.day + dur, kind: 'return', naval: m.naval };
    // نشيلها من الحركات الحالية لو كانت موجودة
    this.s.moves = this.s.moves.filter((x) => x.id !== m.id);
    this.s.moves.push(back);
  }

  private resolveMove(m: Movement) {
    const s = this.s;
    const A = s.nations[m.owner];
    if (!A || !A.alive) return;
    if (m.kind === 'return') {
      for (const k of UNIT_TYPES) A.units[k] += m.units[k];
      return;
    }
    if (m.kind === 'missile' || m.kind === 'nuke') return this.resolveStrike(m, A);
    const T = s.terr[m.to];
    if (T.owner === A.id) { for (const k of UNIT_TYPES) A.units[k] += m.units[k]; return; }
    const D = T.owner ? s.nations[T.owner] : null;
    if (D && (this.allied(A.id, D.id) || this.inTruce(A.id, D.id))) {
      this.startReturn(m);
      return;
    }
    if (D && !this.atWar(A.id, D.id)) this.declareWar(A, D);
    startBattle(this, m);
  }

  conquer(T: Territory, A: Nation, D: Nation | null, days = 0) {
    T.owner = A.id;
    T.unrest = D ? 12 : 8;
    T.pop *= 0.97;
    T.gdp *= 0.9;
    delete T.g; delete T.gmax; delete T.nt;
    this.news('🏴', `${A.name} احتلت ${this.tname(T.id)}${D ? ` من ${D.name}` : ''}${days ? ` بعد معركة ${days} يوم` : ''}`, 'battle', { n: [A.id, D?.id ?? ''], terr: T.id });
    if (D) {
      D.stability = clamp(D.stability - (T.id === D.capital ? 15 : 8), 0, 100);
      const rest = this.owned(D.id);
      if (!rest.length) this.eliminate(D, A);
      else if (T.id === D.capital) {
        D.capital = rest.sort((a, b) => b.gdp - a.gdp)[0].id;
        this.news('🏛️', `${D.name} نقلت عاصمتها إلى ${this.tname(D.capital)}`, 'battle', { n: [D.id] });
      }
    }
  }

  private eliminate(D: Nation, by: Nation | null) {
    const s = this.s;
    if (!D.alive) return;
    D.alive = false;
    D.elimDay = s.day;
    D.units = emptyUnits();
    D.q = []; D.bq = [];
    s.moves = s.moves.filter((m) => m.owner !== D.id);
    s.battles = s.battles.filter((b) => b.att !== D.id);
    s.props = s.props.filter((p) => p.from !== D.id && p.to !== D.id);
    for (const k of Object.keys(s.rel)) if (k.split('|').includes(D.id)) delete s.rel[k];
    this.news('💀', `${D.name} (${D.leader}) سقطت${by ? ` على يد ${by.name}` : ''}!`, 'war', { n: [D.id] });
  }

  private resolveStrike(m: Movement, A: Nation) {
    const s = this.s;
    const T = s.terr[m.to];
    const D = T.owner ? s.nations[T.owner] : null;
    if (T.owner === A.id || (D && (this.allied(A.id, D.id) || this.inTruce(A.id, D.id)))) {
      for (const k of UNIT_TYPES) A.units[k] += m.units[k];
      return;
    }
    if (D && !this.atWar(A.id, D.id)) this.declareWar(A, D);
    const airdef = D ? D.b.airdef : 0;
    if (m.kind === 'missile') {
      const n = m.units.missile;
      const p = Math.min(0.7, 0.12 * airdef);
      let hits = 0;
      for (let i = 0; i < n; i++) if (this.rand() >= p) hits++;
      const target: Partial<Units> = D ? D.units : ((T.g ?? { inf: 0, tank: 0 }) as Partial<Units>);
      const dLoss: Partial<Units> = {};
      let budget = hits * 8 * techMult(A.tech) / techMult(D ? D.tech : T.nt ?? 1);
      // تدمير الوحدات الأغلى أول بشكل عشوائي
      let guard = 0;
      while (budget > 0 && guard++ < 500) {
        const avail = COMBAT_UNITS.filter((k) => (target[k] ?? 0) > 0);
        if (!avail.length) break;
        const k = avail[Math.floor(this.rand() * avail.length)];
        const val = (UNITS[k].atk + UNITS[k].def) / 2;
        target[k] = (target[k] ?? 0) - 1;
        dLoss[k] = (dLoss[k] ?? 0) + 1;
        budget -= val;
      }
      T.gdp *= 1 - 0.01 * hits;
      T.pop *= 1 - 0.002 * hits;
      if (D) D.stability = clamp(D.stability - hits * 0.5, 0, 100);
      const rep: Report = {
        id: this.id(), day: s.day, kind: 'missile', att: A.id, def: D?.id ?? '', terr: T.id, from: m.from, A: n, D: 0, la: 100, ld: 100,
        win: hits > 0, aUnits: { missile: n }, dUnits: {}, aLoss: { missile: n }, dLoss, allies: [], hits, intercepted: n - hits,
      };
      s.reports.push(rep);
      this.news('🚀', `${A.name} قصفت ${this.tname(T.id)} بـ ${n} صاروخ (${hits} أصابت${n - hits ? `، ${n - hits} اعترضها الدفاع الجوي` : ''})`, 'battle', { n: [A.id, D?.id ?? ''], terr: T.id });
    } else {
      const p = Math.min(0.4, 0.08 * airdef);
      const intercepted = this.rand() < p;
      const rep: Report = {
        id: this.id(), day: s.day, kind: 'nuke', att: A.id, def: D?.id ?? '', terr: T.id, from: m.from, A: 1, D: 0, la: 100, ld: 100,
        win: !intercepted, aUnits: { nuke: 1 }, dUnits: {}, aLoss: { nuke: 1 }, dLoss: {}, allies: [], hits: intercepted ? 0 : 1, intercepted: intercepted ? 1 : 0,
      };
      if (intercepted) {
        this.news('📡', `الدفاع الجوي في ${this.tname(T.id)} اعترض قنبلة نووية أطلقتها ${A.name}!`, 'nuke', { n: [A.id, D?.id ?? ''], terr: T.id });
      } else {
        T.pop *= 0.45;
        T.gdp *= 0.4;
        T.nuked = 60;
        if (D) {
          const frac = T.id === D.capital ? 0.5 : 0.3;
          rep.dLoss = this.applyLoss({ ...D.units }, frac, D.units);
          D.stability = clamp(D.stability - 25, 0, 100);
        } else if (T.g) {
          rep.dLoss = this.applyLoss({ ...T.g }, 0.8, T.g as Partial<Units>);
        }
        this.news('☢️', `${A.name} ضربت ${this.tname(T.id)} بقنبلة نووية! العالم في صدمة`, 'nuke', { n: [A.id, D?.id ?? ''], terr: T.id });
      }
      // ردة فعل العالم
      A.stability = clamp(A.stability - 10, 0, 100);
      for (const o of Object.values(s.nations)) {
        if (o.id === A.id || !o.alive) continue;
        const r = this.peek(A.id, o.id);
        if (r?.ally) { delete r.ally; this.news('💔', `${o.name} فسخت تحالفها مع ${A.name} بسبب الهجوم النووي`, 'diplo', { n: [o.id, A.id] }); }
        if (r?.trade) delete r.trade;
        if (o.ai) o.ai.grudge = A.id;
      }
      s.reports.push(rep);
    }
    if (s.reports.length > 30) s.reports.splice(0, s.reports.length - 30);
    if (D && D.alive) this.recompute(D);
    this.recompute(A);
  }

  // ---------------- الفوز ----------------
  checkWin() {
    const s = this.s;
    if (s.phase !== 'playing') return;
    const alive = Object.values(s.nations).filter((n) => n.alive);
    const humans = alive.filter((n) => n.kind === 'player');
    const anyHumans = Object.values(s.nations).some((n) => n.kind === 'player');
    const end = (winners: Nation[], reason: string) => {
      s.phase = 'ended';
      s.winner = { nations: winners.map((w) => w.id), reason, day: s.day };
      this.news('🏆', `انتهت اللعبة! ${winners.map((w) => w.name).join(' و ')} ${winners.length > 1 ? 'فازوا' : 'فازت'} — ${reason}`, 'system');
    };
    const top = () => [...alive].sort((a, b) => b.d.score - a.d.score)[0];
    if (anyHumans && humans.length === 0 && alive.length) return end([top()], 'سقطت كل دول اللاعبين');
    if (s.settings.win === 'domination' || alive.length <= 1) {
      if (alive.length === 1) return end(alive, 'سيطرت على العالم');
      const allAllied = alive.every((a) => alive.every((b) => a.id === b.id || this.allied(a.id, b.id)));
      if (alive.length > 1 && allAllied && s.settings.win === 'domination') return end(alive, 'تحالف واحد يحكم العالم');
    }
    if (s.settings.win === 'percent') {
      const total = this.w.totalArea;
      for (const n of alive) {
        const group = [n, ...this.allies(n.id).map((id) => s.nations[id])];
        const area = group.reduce((x, g) => x + g.d.area, 0);
        if (area / total >= s.settings.percent / 100) {
          return end(group, `سيطرت على ${Math.round((area / total) * 100)}% من مساحة العالم`);
        }
      }
    }
    if (s.settings.win === 'score' && s.day >= s.settings.years * 12 * DAYS_PER_MONTH) {
      return end([top()], `أعلى نقاط بعد ${s.settings.years} سنة`);
    }
  }

  // ---------------- الأوامر ----------------
  command(nid: NationId, c: Command, isHost = false): CmdResult {
    const s = this.s;
    if (c.t === 'speed') {
      if (!isHost) return { ok: false, msg: 'بس صاحب الغرفة يغير السرعة' };
      s.speed = clamp(c.speed, 0.5, 8);
      return { ok: true };
    }
    if (c.t === 'pause') {
      if (!isHost) return { ok: false, msg: 'بس صاحب الغرفة يوقف اللعبة' };
      s.paused = c.paused;
      return { ok: true };
    }
    if (c.t === 'spin') return this.spin(nid, c.wheel);
    if (c.t === 'respin') return this.respin(nid, c.wheel);
    if (c.t === 'autospin') { this.autospin(nid); return { ok: true }; }
    if (c.t === 'ready') return this.ready(nid);
    const n = s.nations[nid];
    if (c.t === 'chat') {
      const text = c.text.trim().slice(0, 300);
      if (!text) return { ok: false };
      const player = Object.values(s.players).find((p) => p.nation === nid);
      s.chat.push({ id: this.id(), day: s.day, from: nid, name: player?.name ?? n?.leader ?? '؟', to: c.to, text });
      if (s.chat.length > 80) s.chat.splice(0, s.chat.length - 80);
      return { ok: true };
    }
    if (!n || !n.alive) return { ok: false, msg: 'دولتك سقطت' };
    if (s.phase !== 'playing') return { ok: false, msg: 'اللعبة مو شغالة' };
    const res = this.cmdNation(n, c);
    if (res.ok) this.recompute(n);
    return res;
  }

  private cmdNation(n: Nation, c: Command): CmdResult {
    const s = this.s;
    switch (c.t) {
      case 'tax':
        n.tax = clamp(Math.round(c.rate * 100) / 100, 0.05, 0.45);
        return { ok: true };
      case 'build': {
        const b = c.b;
        if (!BUILDING_TYPES.includes(b)) return { ok: false };
        if (b === 'mining' && n.res === 'none') return { ok: false, msg: 'ما عندك موارد طبيعية تستخرجها' };
        if (n.b[b] + n.bq.filter((q) => q.type === b).length >= MAX_BUILDING_LEVEL) return { ok: false, msg: 'وصلت لأعلى مستوى' };
        this.recompute(n);
        if (n.d.used >= n.d.slots) return { ok: false, msg: 'ما عندك مساحة للبناء، احتل أراضي جديدة' };
        if (n.bq.length >= 6) return { ok: false, msg: 'طابور البناء ممتلئ' };
        const cost = this.buildCost(n, b);
        if (n.treasury < cost) return { ok: false, msg: 'الخزينة ما تكفي' };
        const days = this.buildDays(n, b);
        n.treasury -= cost;
        n.bq.push({ id: this.id(), kind: 'building', type: b, count: 1, left: days, total: days, cost });
        return { ok: true };
      }
      case 'cancel': {
        const list = c.q === 'q' ? n.q : n.bq;
        const item = list.find((x) => x.id === c.id);
        if (!item) return { ok: false };
        n.treasury += (item.cost ?? 0) * 0.5;
        if (c.q === 'q') n.q = n.q.filter((x) => x.id !== c.id); else n.bq = n.bq.filter((x) => x.id !== c.id);
        return { ok: true, msg: 'انلغى ورجع لك نص المبلغ' };
      }
      case 'recruit': {
        const u = c.u;
        if (!UNITS[u]) return { ok: false };
        const cnt = Math.floor(c.n);
        if (cnt < 1 || cnt > (u === 'inf' ? 200 : u === 'nuke' ? 3 : 80)) return { ok: false, msg: 'عدد غير مسموح' };
        if (n.tech < UNITS[u].tech && u !== 'nuke') return { ok: false, msg: `تحتاج تكنولوجيا مستوى ${UNITS[u].tech}` };
        if (u === 'nuke') {
          if (!n.nukeProg) return { ok: false, msg: 'تحتاج برنامج نووي أول' };
          if (n.tech < 3) return { ok: false, msg: 'تحتاج تكنولوجيا مستوى 3 على الأقل' };
        }
        const cost = this.unitCost(n, u) * cnt;
        if (n.treasury < cost) return { ok: false, msg: 'الخزينة ما تكفي' };
        this.recompute(n);
        if (UNITS[u].man * cnt > n.d.manpower) return { ok: false, msg: 'ما عندك شباب كفاية للتجنيد (القوى البشرية)' };
        const days = this.prodDays(n, u, cnt);
        n.treasury -= cost;
        n.q.push({ id: this.id(), kind: 'unit', type: u, count: cnt, left: days, total: days, cost });
        return { ok: true };
      }
      case 'disband': {
        const u = c.u;
        const cnt = Math.min(Math.floor(c.n), n.units[u] ?? 0);
        if (cnt < 1) return { ok: false, msg: 'ما عندك وحدات تسرحها' };
        n.units[u] -= cnt;
        return { ok: true, msg: `تم تسريح ${cnt} ${UNITS[u].name}` };
      }
      case 'project': {
        if (n.nukeProg) return { ok: false, msg: 'عندك برنامج نووي' };
        if (n.q.some((q) => q.kind === 'project')) return { ok: false, msg: 'البرنامج شغال' };
        if (n.tech < NUKE_PROJECT.tech) return { ok: false, msg: `تحتاج تكنولوجيا مستوى ${NUKE_PROJECT.tech}` };
        if (n.treasury < NUKE_PROJECT.cost) return { ok: false, msg: 'الخزينة ما تكفي' };
        n.treasury -= NUKE_PROJECT.cost;
        n.q.push({ id: this.id(), kind: 'project', type: 'nuke', count: 1, left: NUKE_PROJECT.days, total: NUKE_PROJECT.days, cost: NUKE_PROJECT.cost });
        this.news('☢️', `${n.name} بدأت برنامج نووي!`, 'nuke', { n: [n.id] });
        return { ok: true };
      }
      case 'fortune': return spinFortune(this, n);
      case 'attack': return this.cmdAttack(n, c.to, c.units);
      case 'strike': return this.cmdStrike(n, c.to, c.kind, c.n);
      case 'propose': return this.cmdPropose(n, c.to, c.type);
      case 'respond': {
        const p = s.props.find((x) => x.id === c.id && x.to === n.id);
        if (!p) return { ok: false, msg: 'الاقتراح انتهى' };
        s.props = s.props.filter((x) => x.id !== p.id);
        const from = s.nations[p.from];
        if (!from?.alive) return { ok: false };
        if (c.accept) this.acceptProposal(p);
        else this.news('❌', `${n.name} رفضت ${PROP_NAMES[p.type]}`, 'diplo', { to: [p.from, p.to] });
        return { ok: true };
      }
      case 'breakAlly': {
        const r = this.peek(n.id, c.with);
        if (!r?.ally) return { ok: false };
        delete r.ally;
        r.truce = s.day + 90;
        n.stability = clamp(n.stability - 10, 0, 100);
        this.news('💔', `${n.name} فسخت تحالفها مع ${this.nname(c.with)}`, 'diplo', { n: [n.id, c.with] });
        return { ok: true };
      }
      case 'cancelTrade': {
        const r = this.peek(n.id, c.with);
        if (!r?.trade) return { ok: false };
        delete r.trade;
        this.news('📦', `${n.name} ألغت الاتفاقية التجارية مع ${this.nname(c.with)}`, 'diplo', { n: [n.id, c.with] });
        return { ok: true };
      }
      case 'declare': {
        const b = s.nations[c.on];
        if (!b) return { ok: false };
        const why = this.canHit(n, b);
        if (why) return { ok: false, msg: why };
        this.declareWar(n, b);
        return { ok: true };
      }
      case 'aid': {
        const b = s.nations[c.to];
        if (!b?.alive || b.id === n.id) return { ok: false };
        if (this.atWar(n.id, b.id)) return { ok: false, msg: 'ما تقدر تساعد عدوك' };
        const parts: string[] = [];
        if (c.money && c.money > 0) {
          const m = Math.min(c.money, Math.max(0, n.treasury));
          if (m <= 0) return { ok: false, msg: 'الخزينة فاضية' };
          n.treasury -= m;
          b.treasury += m;
          parts.push(`${Math.round(m)} مليار`);
        }
        if (c.units) {
          for (const k of UNIT_TYPES) {
            const x = Math.min(Math.floor(c.units[k] ?? 0), n.units[k]);
            if (x > 0) { n.units[k] -= x; b.units[k] += x; parts.push(`${x} ${UNITS[k].name}`); }
          }
        }
        if (!parts.length) return { ok: false, msg: 'ما حددت شي' };
        this.recompute(b);
        this.news('🎁', `${n.name} أرسلت مساعدات لـ ${b.name}: ${parts.join('، ')}`, 'diplo', { n: [n.id, b.id] });
        return { ok: true };
      }
      default:
        return { ok: false };
    }
  }

  private cmdAttack(n: Nation, to: TerrId, req: Partial<Units>): CmdResult {
    const s = this.s;
    const T = s.terr[to];
    if (!T) return { ok: false };
    if (T.owner === n.id) return { ok: false, msg: 'هذي أرضك' };
    if (T.owner) {
      const why = this.canHit(n, s.nations[T.owner]);
      if (why) return { ok: false, msg: why };
    }
    const units = emptyUnits();
    for (const k of COMBAT_UNITS) units[k] = clamp(Math.floor(req[k] ?? 0), 0, n.units[k]);
    if (units.inf + units.tank < 1) return { ok: false, msg: 'لازم ترسل قوات برية (مشاة أو دبابات) عشان تحتل' };
    const route = this.route(n, to);
    if (!route) return { ok: false, msg: 'ما تقدر توصل لهذي الدولة (مو مجاورة لك وبعيدة عن مدى أسطولك)' };
    if (route.naval) {
      const need = Math.ceil((units.inf + units.tank) / SHIP_CAPACITY);
      if (units.ship < need) return { ok: false, msg: `الغزو البحري يحتاج ${need} سفن على الأقل لنقل قواتك` };
    } else if (!this.w.get(to).c) units.ship = 0;
    for (const k of COMBAT_UNITS) n.units[k] -= units[k];
    const days = this.travelDays(n, route.from, to, route.naval);
    s.moves.push({ id: this.id(), owner: n.id, from: route.from, to, units, depart: s.day, arrive: s.day + days, kind: 'attack', naval: route.naval });
    if (T.owner) {
      const D = s.nations[T.owner];
      if (!this.atWar(n.id, D.id)) this.declareWar(n, D);
      this.news('⚠️', `قوات ${n.name} متجهة لـ ${this.tname(to)}! توصل بعد ${days} يوم`, 'war', { to: [D.id], terr: to });
    }
    return { ok: true, msg: `الجيش تحرك، يوصل بعد ${days} يوم` };
  }

  private cmdStrike(n: Nation, to: TerrId, kind: 'missile' | 'nuke', cnt: number): CmdResult {
    const s = this.s;
    const T = s.terr[to];
    if (!T || T.owner === n.id) return { ok: false };
    if (T.owner) {
      const why = this.canHit(n, s.nations[T.owner]);
      if (why) return { ok: false, msg: why };
    }
    const k = kind === 'missile' ? 'missile' : 'nuke';
    const num = kind === 'nuke' ? 1 : clamp(Math.floor(cnt), 1, n.units.missile);
    if (n.units[k] < num || num < 1) return { ok: false, msg: kind === 'nuke' ? 'ما عندك قنابل نووية' : 'ما عندك صواريخ' };
    const range = Math.max(missileRange(n.tech), kind === 'nuke' ? 2500 : 0);
    const d = this.strikeRange(n, to);
    if (d > range) return { ok: false, msg: `الهدف بعيد (${Math.round(d)} كم) ومدى صواريخك ${range >= 40000 ? 'عالمي' : range + ' كم'}` };
    n.units[k] -= num;
    const u = emptyUnits();
    u[k] = num;
    const from = this.owned(n.id).sort((a, b) => this.w.dist(a.id, to) - this.w.dist(b.id, to))[0]?.id ?? n.capital;
    s.moves.push({ id: this.id(), owner: n.id, from, to, units: u, depart: s.day, arrive: s.day + (kind === 'nuke' ? 3 : 2), kind });
    if (T.owner && !this.atWar(n.id, T.owner)) this.declareWar(n, s.nations[T.owner]);
    return { ok: true };
  }

  private cmdPropose(n: Nation, to: NationId, type: ProposalType): CmdResult {
    const s = this.s;
    const b = s.nations[to];
    if (!b?.alive || b.id === n.id) return { ok: false };
    const r = this.peek(n.id, to);
    if (type === 'peace' && !r?.war) return { ok: false, msg: 'أنتم مو في حرب' };
    if (type === 'ally' && r?.war) return { ok: false, msg: 'ما تقدر تتحالف مع عدوك، اطلب سلام أول' };
    if (type === 'ally' && r?.ally) return { ok: false, msg: 'أنتم حلفاء أصلاً' };
    if (type === 'trade' && r?.war) return { ok: false, msg: 'ما فيه تجارة وقت الحرب' };
    if (type === 'trade' && r?.trade) return { ok: false, msg: 'عندكم اتفاقية تجارية' };
    if (s.props.some((p) => p.from === n.id && p.to === to && p.type === type)) return { ok: false, msg: 'أرسلت هذا الاقتراح من قبل' };
    // لو الطرف الثاني أرسل نفس الاقتراح، نقبله مباشرة
    const mirror = s.props.find((p) => p.from === to && p.to === n.id && p.type === type);
    if (mirror) {
      s.props = s.props.filter((p) => p.id !== mirror.id);
      this.acceptProposal(mirror);
      return { ok: true };
    }
    const p: Proposal = { id: this.id(), from: n.id, to, type, day: s.day };
    s.props.push(p);
    b.lastProp = s.day;
    this.news('📨', `${n.name} ترسل لك ${PROP_NAMES[type]}`, 'diplo', { to: [to] });
    if ((b.kind === 'bot' || b.aiControl) && b.ai) b.ai.next = Math.min(b.ai.next, s.day + this.randInt(2, 5));
    return { ok: true, msg: 'تم إرسال الاقتراح' };
  }

  acceptProposal(p: Proposal) {
    const a = this.s.nations[p.from];
    const b = this.s.nations[p.to];
    if (!a?.alive || !b?.alive) return;
    const r = this.rel(a.id, b.id);
    if (p.type === 'peace') { if (r.war) this.makePeace(a, b); }
    else if (p.type === 'ally') {
      if (r.war) return;
      r.ally = this.s.day;
      this.news('🤝', `تحالف جديد بين ${a.name} و ${b.name}`, 'diplo', { n: [a.id, b.id] });
    } else if (p.type === 'trade') {
      if (r.war) return;
      r.trade = this.s.day;
      this.news('📦', `اتفاقية تجارية بين ${a.name} و ${b.name}`, 'diplo', { n: [a.id, b.id] });
    }
    this.recompute(a);
    this.recompute(b);
  }
}

export const PROP_NAMES: Record<ProposalType, string> = {
  ally: 'طلب تحالف',
  trade: 'اتفاقية تجارية',
  peace: 'طلب سلام',
};
