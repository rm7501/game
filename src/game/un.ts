// الأمم المتحدة: قرار كل سنتين ونص تقريباً، والدول تصوت (نعم / لا / ممتنع)
import { DAYS_PER_MONTH, TECH_COST, UN_EVERY, UN_RES, UN_VOTE_DAYS, UNITS } from './defs';
import type { Engine } from './engine';
import { dominance, rankOf } from './events';
import type { CmdResult, Nation, UNResId, UNVote, Vote } from './types';
import { COMBAT_UNITS } from './types';

const clamp = (x: number, a: number, b: number) => Math.max(a, Math.min(b, x));

export function scheduleUN(e: Engine, first = false) {
  const s = e.s;
  const months = first ? Math.max(30, s.settings.peaceMonths + 18) : e.randInt(UN_EVERY[0], UN_EVERY[1]);
  s.nextUN = s.day + months * DAYS_PER_MONTH;
}

const alive = (e: Engine) => Object.values(e.s.nations).filter((n) => n.alive);

export function unText(e: Engine, v: { res: UNResId; target?: string }) {
  const t = v.target ? e.s.nations[v.target]?.name : undefined;
  return UN_RES[v.res].desc(t);
}

/** يختار قرار يناسب وضع العالم */
export function openUN(e: Engine, forced?: UNResId) {
  const s = e.s;
  const all = alive(e);
  if (all.length < 3) return;
  const byScore = [...all].sort((a, b) => b.d.score - a.d.score);
  const byPower = [...all].sort((a, b) => b.d.power - a.d.power);
  const dom = dominance(e);
  const powDom = byPower[0].d.power / Math.max(1, byPower[1].d.power);
  const aggressor = [...all].filter((n) => n.d.atWar >= 1).sort((a, b) => b.d.atWar - a.d.atWar || b.d.power - a.d.power)[0];
  let wars = 0;
  for (const a of all) for (const b of all) if (a.id < b.id && e.atWar(a.id, b.id)) wars++;
  const nukes = all.some((n) => n.units.nuke > 0 || n.nukeProg) && !((s.mods.nukeBan ?? 0) > s.day);
  const w: Record<UNResId, number> = {
    sanctions: dom > 1.3 ? 4 : 1.5,
    condemn: aggressor ? 2.5 : 0,
    nukeban: nukes ? 2 : 0,
    peacekeep: wars >= 2 ? 2.5 : wars ? 1 : 0,
    devfund: 1.5,
    science: 1.2,
    disarm: powDom > 1.5 ? 2 : 0.6,
  };
  const ids = Object.keys(w) as UNResId[];
  const res = forced ?? ids[e.weighted(ids.map((k) => w[k]))];
  const target = res === 'sanctions' ? byScore[0].id : res === 'condemn' ? (aggressor ?? byPower[0]).id : undefined;
  const v: UNVote = { id: e.id(), res, target, start: s.day, end: s.day + UN_VOTE_DAYS, votes: {} };
  if (target) v.votes[target] = 'n';
  s.un = v;
  e.news('🏛️', `الأمم المتحدة تصوت على «${UN_RES[res].icon} ${UN_RES[res].name}»: ${unText(e, v)}`, 'system');
}

export function castVote(e: Engine, n: Nation, v: Vote): CmdResult {
  const u = e.s.un;
  if (!u) return { ok: false, msg: 'ما فيه تصويت الحين' };
  if (u.target === n.id) return { ok: false, msg: 'القرار ضدك، صوتك «لا» تلقائياً' };
  if (!['y', 'n', 'a'].includes(v)) return { ok: false };
  u.votes[n.id] = v;
  return { ok: true, msg: v === 'y' ? '🗳️ صوتت بنعم' : v === 'n' ? '🗳️ صوتت بلا' : '🗳️ امتنعت عن التصويت' };
}

/** تصويت البوت حسب مصلحته */
export function aiVote(e: Engine, n: Nation, u: UNVote): Vote {
  const s = e.s;
  const r = e.rand();
  const T = u.target ? s.nations[u.target] : undefined;
  if (T && T.id === n.id) return 'n';
  const friend = !!T && (e.allied(n.id, T.id) || (!!n.team && n.team === T.team));
  switch (u.res) {
    case 'sanctions':
    case 'condemn':
      if (!T) return 'a';
      if (friend) return 'n';
      if (n.ai?.grudge === T.id || e.atWar(n.id, T.id) || s.coalition === T.id) return 'y';
      if (e.trading(n.id, T.id)) return r < 0.25 ? 'y' : r < 0.85 ? 'a' : 'n';
      return r < 0.65 ? 'y' : 'a';
    case 'nukeban':
      if (n.units.nuke > 0 || n.nukeProg) return r < 0.8 ? 'n' : 'a';
      return r < 0.75 ? 'y' : 'a';
    case 'peacekeep': {
      const foes = e.enemies(n.id).map((id) => s.nations[id]);
      if (!foes.length) return r < 0.6 ? 'y' : 'a';
      const foePow = Math.max(...foes.map((f) => f.d.power));
      return n.d.power > foePow * 1.3 ? 'n' : 'y';
    }
    case 'devfund': {
      const k = rankOf(e, n);
      if (k >= 0.5) return 'y';
      if (k < 0.3) return r < 0.7 ? 'n' : 'a';
      return 'a';
    }
    case 'science': {
      const maxT = Math.max(...alive(e).map((x) => x.tech));
      return n.tech >= maxT ? 'n' : r < 0.8 ? 'y' : 'a';
    }
    case 'disarm': {
      const byPow = alive(e).sort((a, b) => b.d.power - a.d.power);
      const i = byPow.findIndex((x) => x.id === n.id);
      return i < Math.max(1, Math.ceil(byPow.length * 0.25)) ? 'n' : r < 0.75 ? 'y' : 'a';
    }
  }
}

/** يومياً: فتح وإغلاق جلسات التصويت */
export function tickUN(e: Engine) {
  const s = e.s;
  if (s.un) {
    if (s.day >= s.un.end) closeUN(e);
    return;
  }
  if (s.nextUN > 0 && s.day >= s.nextUN) {
    openUN(e);
    scheduleUN(e);
  }
}

export function closeUN(e: Engine) {
  const s = e.s;
  const u = s.un;
  if (!u) return;
  s.un = undefined;
  let yes = 0, no = 0, abst = 0;
  for (const n of alive(e)) {
    let v = u.votes[n.id];
    if (!v) v = n.kind === 'bot' || n.aiControl ? aiVote(e, n, u) : 'a';
    u.votes[n.id] = v;
    if (v === 'y') yes++;
    else if (v === 'n') no++;
    else abst++;
  }
  const T = u.target ? s.nations[u.target] : undefined;
  const passed = yes > no && yes >= 2 && (!u.target || !!T?.alive);
  const def = UN_RES[u.res];
  let text = '';
  if (passed) text = applyUN(e, u);
  s.unLast = { id: u.id, res: u.res, target: u.target, yes, no, abst, passed, day: s.day, text };
  e.news('🏛️', `${passed ? '✅ الأمم المتحدة أقرت' : '❌ الأمم المتحدة رفضت'} «${def.name}» (${yes} نعم، ${no} لا، ${abst} ممتنع)${text ? ': ' + text : ''}`, 'system', { n: T ? [T.id] : undefined });
  e.histEvent('🏛️', `${passed ? 'أقرت' : 'رفضت'} الأمم المتحدة «${def.name}»${T ? ' ضد ' + T.name : ''}`);
  for (const n of alive(e)) e.recompute(n);
}

function applyUN(e: Engine, u: UNVote): string {
  const s = e.s;
  const all = alive(e);
  const T = u.target ? s.nations[u.target] : undefined;
  switch (u.res) {
    case 'sanctions':
      if (!T) return '';
      T.fx.sanct = s.day + 24 * DAYS_PER_MONTH;
      return `دخل ${T.name} ينقص 30% لمدة سنتين`;
    case 'condemn': {
      if (!T) return '';
      T.stability = clamp(T.stability - 15, 0, 100);
      const left: string[] = [];
      for (const id of e.allies(T.id)) {
        const X = s.nations[id];
        const r = e.peek(T.id, id);
        if (!r || r.team || X.kind !== 'bot' || e.rand() > 0.4) continue;
        delete r.ally;
        r.truce = s.day + 90;
        left.push(X.name);
      }
      return `استقرار ${T.name} -15${left.length ? `، وتخلى عنها: ${left.join('، ')}` : ''}`;
    }
    case 'nukeban': {
      let count = 0;
      for (const n of all) {
        const k = n.units.nuke;
        const q = n.q.filter((x) => x.kind === 'unit' && x.type === 'nuke');
        const queued = q.reduce((a, x) => a + x.count, 0);
        if (k + queued > 0) {
          n.treasury += (k + queued) * UNITS.nuke.cost * 0.5;
          n.units.nuke = 0;
          n.q = n.q.filter((x) => !(x.kind === 'unit' && x.type === 'nuke'));
          count += k + queued;
        }
      }
      s.mods.nukeBan = s.day + 60 * DAYS_PER_MONTH;
      return count ? `تفككت ${count} قنبلة نووية، وممنوع تصنيعها 5 سنوات` : 'ممنوع تصنيع القنابل النووية 5 سنوات';
    }
    case 'peacekeep': {
      let c = 0;
      for (const a of all) for (const b of all) if (a.id < b.id && e.atWar(a.id, b.id)) { e.makePeace(a, b, 12, true); c++; }
      return c ? `توقفت ${c} حروب بهدنة سنة` : 'ما كان فيه حروب';
    }
    case 'devfund': {
      const ranked = [...all].sort((a, b) => b.d.score - a.d.score);
      const half = Math.ceil(ranked.length / 2);
      let pool = 0;
      for (const n of ranked.slice(0, half)) {
        const x = Math.max(0, n.treasury) * 0.08;
        n.treasury -= x;
        pool += x;
      }
      const poor = ranked.slice(half);
      if (!poor.length) return '';
      for (const n of poor) n.treasury += pool / poor.length;
      return `${Math.round(pool)} مليار انتقلت للدول الأضعف`;
    }
    case 'science': {
      const maxT = Math.max(...all.map((n) => n.tech));
      let c = 0;
      for (const n of all) if (n.tech < maxT) { n.research += (TECH_COST[n.tech + 1] ?? 0) * 0.5; c++; }
      return `${c} دول أخذت دفعة أبحاث`;
    }
    case 'disarm': {
      const big = [...all].sort((a, b) => b.d.power - a.d.power)[0];
      for (const n of all) {
        const f = n.id === big.id ? 0.75 : 0.9;
        for (const k of COMBAT_UNITS) n.units[k] = Math.floor(n.units[k] * f);
      }
      return `كل الجيوش نقصت 10%، وجيش ${big.name} نقص 25%`;
    }
  }
}
