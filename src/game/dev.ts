// وضع المتحكم: صاحب اللعبة يقدر يتحكم بكل شي (العجلات، الحظ، الدول، الأحداث، الوقت)
// منفصل عن اللعبة: لو مو مفعّل ما يأثر على شي
import {
  CARDS, DAYS_PER_MONTH, FORTUNES, GOVS, HAND_MAX, LEADERS, MAX_TECH, MISSIONS, RESOURCES, TERRAINS, UNITS, WORLD_EVENTS,
} from './defs';
import type { Engine } from './engine';
import { assignMission, fireWorldEvent, scheduleWorld } from './events';
import { dealCards } from './cards';
import { closeUN, openUN } from './un';
import { UN_RES } from './defs';
import type {
  CmdResult, DevCmd, DevState, GameState, GovId, LeaderId, MissionId, Nation, ResId, TerrainId, WheelId,
} from './types';
import { UNIT_TYPES, WHEEL_ORDER } from './types';

const clamp = (x: number, a: number, b: number) => Math.max(a, Math.min(b, x));

export function newDev(by: string): DevState {
  return { by, off: {}, wm: {}, rig: {}, fortune: {}, god: {} };
}

/** العجلات المقفلة (المساحة والمكان ما ينقفلون مع بعض: لازم وحدة منهم على الأقل تبين الدولة) */
export function wheelIsOff(s: GameState, w: WheelId): boolean {
  return !!s.dev?.off?.[w];
}

export function weightMult(s: GameState, wheel: string, v: number | string): number {
  const m = s.dev?.wm?.[wheel]?.[String(v)];
  return m === undefined ? 1 : m;
}

export const activeWheels = (s: GameState): WheelId[] => WHEEL_ORDER.filter((w) => !wheelIsOff(s, w));

/** هل هذا الجهاز هو المتحكم؟ */
export const isController = (s: GameState, clientId: string) => !!s.dev && s.dev.by === clientId;

/** تنفيذ أمر من المتحكم (يتحقق إنه المتحكم فعلاً) */
export function devCommand(e: Engine, clientId: string, d: DevCmd): CmdResult {
  const s = e.s;
  if (d.a === 'enable') {
    const owner = s.owner ?? s.hostId;
    if (d.on) {
      if (s.dev) return s.dev.by === clientId ? { ok: true } : { ok: false, msg: 'فيه متحكم ثاني في هذي اللعبة' };
      if (clientId !== owner && clientId !== s.hostId) return { ok: false, msg: 'بس اللي سوى اللعبة يقدر يفعّل وضع المتحكم' };
      s.dev = newDev(clientId);
      s.settings.dev = true;
      e.news('🛠️', `${s.players[clientId]?.name ?? 'صاحب اللعبة'} فعّل وضع المتحكم`, 'system');
      return { ok: true, msg: '🛠️ وضع المتحكم شغال' };
    }
    if (!s.dev || s.dev.by !== clientId) return { ok: false };
    if (s.players[clientId]?.gm && s.phase !== 'lobby') return { ok: false, msg: 'أنت تدير اللعبة بدون دولة، ما تقدر تقفله الحين' };
    s.dev = undefined;
    s.settings.dev = false;
    if (s.players[clientId]) delete s.players[clientId].gm;
    e.news('🛠️', 'وضع المتحكم انقفل', 'system');
    return { ok: true, msg: 'انقفل وضع المتحكم' };
  }
  if (!s.dev || s.dev.by !== clientId) return { ok: false, msg: 'أنت مو المتحكم في هذي اللعبة' };
  const dev = s.dev;
  const N = (id: string): Nation | undefined => s.nations[id];
  const done = (msg?: string): CmdResult => ({ ok: true, msg });
  switch (d.a) {
    // ---------- قبل اللعبة ----------
    case 'gm': {
      if (s.phase !== 'lobby') return { ok: false, msg: 'تختار هذا قبل ما تبدأ اللعبة' };
      const p = s.players[clientId];
      if (!p) return { ok: false };
      if (d.on) p.gm = true; else delete p.gm;
      return done(d.on ? '👁️ بتدير اللعبة بدون دولة' : '🎮 بتلعب بدولة وتتحكم');
    }
    case 'wheelOff': {
      if (!WHEEL_ORDER.includes(d.wheel)) return { ok: false };
      if (d.off && ((d.wheel === 'area' && dev.off.country) || (d.wheel === 'country' && dev.off.area))) {
        // نسمح، بس الدولة تنختار تلقائياً
      }
      if (d.off) dev.off[d.wheel] = true; else delete dev.off[d.wheel];
      if (d.off && s.phase === 'wheels') for (const nid of Object.keys(s.wheels)) if (!s.wheels[nid].ready) e.fillOff(nid);
      return done();
    }
    case 'weight': {
      const m = clamp(Number(d.m) || 0, 0, 20);
      (dev.wm[d.wheel] ??= {})[d.v] = m;
      if (m === 1) delete dev.wm[d.wheel][d.v];
      return done();
    }
    case 'weightsReset':
      if (d.wheel) delete dev.wm[d.wheel]; else dev.wm = {};
      return done('رجعت الأوزان الأصلية');
    case 'rig': {
      const r = (dev.rig[d.nid] ??= {});
      if (d.v === null || d.v === undefined) {
        delete r[d.wheel];
        return done();
      }
      if (s.nations[d.nid]) return { ok: false, msg: 'هذي الدولة بدأت تلعب: عدّلها من تبويب «الدول» و«الأراضي»' };
      const ws = s.wheels[d.nid];
      if (d.wheel === 'country') {
        const c = String(d.v);
        const cm = e.w.countries.get(c);
        if (!cm?.p) return { ok: false, msg: 'دولة غير معروفة' };
        // ما ينفع دولتين ياخذون نفس الدولة
        for (const [oid, or] of Object.entries(dev.rig)) if (oid !== d.nid && or.country === c) delete or.country;
        const prevRig = r.country;
        r.country = c; // نحجزها قبل ما نعيد لف دولة اللي كانت معه
        const other = s.taken[c];
        if (other && other !== d.nid) {
          // مأخوذة من لاعب أو بوت لسا ما بدأ: نبدّل
          if (s.nations[other]) {
            if (prevRig === undefined) delete r.country; else r.country = prevRig;
            return { ok: false, msg: 'هذي الدولة صارت لدولة في اللعب' };
          }
          const ows = s.wheels[other];
          const mine = ws?.res.country as string | undefined;
          delete s.taken[c];
          if (ows) {
            if (mine && s.taken[mine] === d.nid) {
              ows.res.country = mine;
              ows.res.area = e.w.country(mine).cls;
              s.taken[mine] = other;
              if (ws) delete ws.res.country;
            } else {
              delete ows.res.country;
              ows.done = false;
              if (other.startsWith('B')) { ows.ready = true; e.autospin(other); } else ows.ready = false;
            }
          }
        } else if (!other && s.phase !== 'lobby' && !e.countryFree(cm)) {
          if (prevRig === undefined) delete r.country; else r.country = prevRig;
          return { ok: false, msg: 'هذي الدولة مو متاحة' };
        }
        if (ws && (ws.res.country !== undefined || ws.res.area !== undefined)) {
          const old = ws.res.country as string | undefined;
          if (old && s.taken[old] === d.nid) delete s.taken[old];
          if (ws.res.country !== undefined || ws.res.area !== undefined) {
            ws.res.area = cm.cls;
            ws.res.country = c;
            s.taken[c] = d.nid;
            ws.done = e.nextWheel(d.nid) === null;
          }
        }
        return done(`📍 ${cm.ar} صارت لهذا اللاعب`);
      }
      r[d.wheel] = d.v;
      // لو العجلة انلفت، نغير نتيجتها مباشرة
      if (ws && ws.res[d.wheel] !== undefined) {
        if (d.wheel === 'area') {
          ws.res.area = Number(d.v);
          const old = ws.res.country as string | undefined;
          if (old && e.w.countries.get(old)?.cls !== Number(d.v)) {
            if (s.taken[old] === d.nid) delete s.taken[old];
            delete ws.res.country;
            ws.done = false;
            ws.ready = false;
            if (d.nid.startsWith('B')) e.autospin(d.nid);
          }
        } else ws.res[d.wheel] = d.v;
      }
      return done('🎯 تثبتت النتيجة');
    }
    case 'respins': {
      const n = clamp(Math.round(d.n), 0, 99);
      for (const [nid, ws] of Object.entries(s.wheels)) if (!d.nid || d.nid === nid) ws.respins = n;
      return done(`🔄 إعادات اللف صارت ${n}`);
    }
    case 'finishWheels': {
      if (s.phase !== 'wheels') return { ok: false };
      e.readyAll();
      if (!s.countdown) s.countdown = Date.now() + 3000;
      return done('⏩ بدأنا اللعبة');
    }
    // ---------- الدول ----------
    case 'nation': {
      const n = N(d.nid);
      if (!n) return { ok: false };
      const num = Number(d.v);
      switch (d.f) {
        case 'treasury': n.treasury = clamp(num, -1e6, 1e8); break;
        case 'stability': n.stability = clamp(num, 0, 100); break;
        case 'tech': n.tech = clamp(Math.round(num), 1, MAX_TECH); n.research = 0; break;
        case 'research': n.research = clamp(num, 0, 1e6); break;
        case 'agents': n.agents = clamp(Math.round(num), 0, 50); break;
        case 'bonus': n.bonus = clamp(Math.round(num), -1e6, 1e7); break;
        case 'tax': n.tax = clamp(num, 0.05, 0.45); break;
        case 'gov': if (!GOVS[d.v as GovId]) return { ok: false }; n.gov = d.v as GovId; n.govUntil = undefined; break;
        case 'res': if (!RESOURCES[d.v as ResId]) return { ok: false }; n.res = d.v as ResId; break;
        case 'trait': if (!LEADERS[d.v as LeaderId]) return { ok: false }; n.trait = d.v as LeaderId; break;
        case 'terrain': if (!TERRAINS[d.v as TerrainId]) return { ok: false }; n.terrain = d.v as TerrainId; break;
        case 'name': { const t = String(d.v).trim().slice(0, 24); if (!t) return { ok: false }; n.name = t; break; }
      }
      e.recompute(n);
      return done();
    }
    case 'units': {
      const n = N(d.nid);
      if (!n || !UNITS[d.u]) return { ok: false };
      n.units[d.u] = clamp(Math.round(n.units[d.u] + d.d), 0, 100000);
      e.recompute(n);
      return done();
    }
    case 'card': {
      const n = N(d.nid);
      if (!n || !CARDS[d.card]) return { ok: false };
      if (d.remove) {
        const i = n.cards.indexOf(d.card);
        if (i >= 0) n.cards.splice(i, 1);
        return done();
      }
      if (n.cards.length >= HAND_MAX) return { ok: false, msg: `يده مليانة (${HAND_MAX} بطاقات)` };
      n.cards.push(d.card);
      return done(`🃏 أعطيته ${CARDS[d.card].name}`);
    }
    case 'mission': {
      const n = N(d.nid);
      if (!n) return { ok: false };
      if (d.id && MISSIONS[d.id as MissionId]) assignMission(e, n, d.id as MissionId);
      if (d.done) n.mission.target = 0;
      return done();
    }
    case 'pers': {
      const n = N(d.nid);
      if (!n?.ai) return { ok: false, msg: 'هذي مو دولة بوت' };
      n.ai.pers = d.pers;
      return done();
    }
    case 'god':
      if (d.m === 1) delete dev.god[d.nid]; else dev.god[d.nid] = clamp(d.m, 0.1, 20);
      return done();
    case 'noise':
      dev.noise = clamp(d.x, 0, 0.6);
      return done();
    case 'kill': {
      const n = N(d.nid);
      if (!n?.alive) return { ok: false };
      for (const t of e.owned(n.id)) e.revolt(t, n);
      e.eliminate(n, null);
      return done(`💀 ${n.name} سقطت`);
    }
    case 'addBot': {
      if (s.phase !== 'playing') return { ok: false, msg: 'تضيف بوتات وقت اللعب (أو زيد العدد من الإعدادات قبل البداية)' };
      const b = e.spawnBot();
      return b ? done(`🤖 دخل بوت جديد: ${b.name}`) : { ok: false, msg: 'ما فيه دول فاضية' };
    }
    // ---------- الخريطة ----------
    case 'terr': {
      const T = s.terr[d.terr];
      if (!T) return { ok: false };
      if (d.owner && !N(d.owner)) return { ok: false };
      const ids = d.whole ? e.w.country(d.terr).provs : [d.terr];
      for (const id of ids) if (s.terr[id]) e.transferTerr(s.terr[id], d.owner);
      return done(d.owner ? `🏳️ صارت لـ ${N(d.owner)!.name}` : '🏳️ صارت محايدة');
    }
    // ---------- الأحداث ----------
    case 'world':
      if (!WORLD_EVENTS[d.ev] || s.phase !== 'playing') return { ok: false };
      fireWorldEvent(e, d.ev);
      scheduleWorld(e);
      return done();
    case 'un':
      if (!UN_RES[d.res] || s.phase !== 'playing') return { ok: false };
      if (s.un) closeUN(e);
      openUN(e, d.res);
      return s.un ? done('🏛️ بدأ التصويت') : { ok: false, msg: 'لازم 3 دول على الأقل' };
    case 'unClose':
      if (!s.un) return { ok: false, msg: 'ما فيه تصويت' };
      closeUN(e);
      return done();
    case 'unVote':
      if (!s.un || !N(d.nid)) return { ok: false };
      s.un.votes[d.nid] = d.v;
      return done();
    case 'fortune': {
      const n = N(d.nid);
      if (!n) return { ok: false };
      if (d.res && FORTUNES[d.res]) dev.fortune[n.id] = d.res; else delete dev.fortune[n.id];
      n.fortuneNext = Math.min(n.fortuneNext, s.day);
      return done(d.res ? `🎰 عجلة الحظ الجاية لـ ${n.name}: ${FORTUNES[d.res].name}` : '🎰 عجلة الحظ متاحة');
    }
    case 'deal':
      dealCards(e);
      return done('🃏 الكل أخذ بطاقة');
    case 'rel': {
      const a = N(d.x), b = N(d.y);
      if (!a?.alive || !b?.alive || a.id === b.id) return { ok: false };
      const r = e.rel(a.id, b.id);
      if (r.team && d.r !== 'ally') return { ok: false, msg: 'هذولا في نفس الفريق' };
      if (d.r === 'war') { delete r.truce; e.declareWar(a, b); }
      else if (d.r === 'peace') { if (r.war) e.makePeace(a, b); else r.truce = s.day + 24 * DAYS_PER_MONTH; }
      else if (d.r === 'ally') { if (r.war) e.makePeace(a, b, 0, true); r.ally = Math.max(1, s.day); e.news('🤝', `تحالف جديد بين ${a.name} و ${b.name}`, 'diplo', { n: [a.id, b.id] }); }
      else if (d.r === 'trade') { if (r.war) e.makePeace(a, b, 0, true); r.trade = Math.max(1, s.day); }
      else { delete r.war; delete r.ally; delete r.trade; delete r.truce; }
      e.recompute(a);
      e.recompute(b);
      return done();
    }
    case 'peaceAll': {
      const all = Object.values(s.nations).filter((n) => n.alive);
      for (const a of all) for (const b of all) if (a.id < b.id && e.atWar(a.id, b.id)) e.makePeace(a, b, 12, true);
      e.news('🕊️', 'المتحكم أوقف كل الحروب (هدنة سنة)', 'system');
      return done();
    }
    // ---------- الوقت ----------
    case 'speed':
      s.speed = clamp(d.x, 0.25, 32);
      return done();
    case 'skip': {
      if (s.phase !== 'playing') return { ok: false };
      const days = clamp(Math.round(d.months), 1, 60) * DAYS_PER_MONTH;
      for (let i = 0; i < days && s.phase === 'playing'; i++) e.dayTick();
      return done(`⏩ قدّمنا ${Math.round(days / DAYS_PER_MONTH)} شهر`);
    }
    case 'years':
      s.settings.years = clamp(s.settings.years + Math.round(d.d), 1, 200);
      return done(`مدة اللعبة صارت ${s.settings.years} سنة`);
    case 'end': {
      if (s.phase !== 'playing') return { ok: false };
      const alive = Object.values(s.nations).filter((n) => n.alive).sort((a, b) => b.d.score - a.d.score);
      const w = d.winner ? N(d.winner) : alive[0];
      if (!w) return { ok: false };
      const team = s.settings.teams > 0 && w.team ? Object.values(s.nations).filter((n) => n.team === w.team) : [w];
      e.endGame(team, 'قرار المتحكم');
      return done();
    }
  }
  return { ok: false };
}

/** أسماء الحقول للواجهة */
export const DEV_UNIT_TYPES = UNIT_TYPES;
