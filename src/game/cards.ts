// بطاقات الخطط: تاخذها كل سنة ومن المهمات والمعارك وعجلة الحظ، وتلعبها وقت ما تبي
import { CARDS, CARD_EVERY, GOVS, GOV_SLICES, HAND_MAX, DAYS_PER_MONTH } from './defs';
import type { Engine } from './engine';
import { rankOf } from './events';
import type { CardId, CmdResult, GovId, Nation, NationId, TerrId } from './types';
import { COMBAT_UNITS } from './types';

const clamp = (x: number, a: number, b: number) => Math.max(a, Math.min(b, x));

/** تسحب بطاقة عشوائية (الدول المتأخرة تاخذ البطاقات القوية أكثر) */
export function drawCard(e: Engine, n: Nation, why?: string): CardId | null {
  if (!n.alive || n.cards.length >= HAND_MAX) return null;
  const ids = Object.keys(CARDS) as CardId[];
  const r = rankOf(e, n);
  const ws = ids.map((id) => CARDS[id].w * (id === 'coup' || id === 'defect' || id === 'ceasefire' ? 0.6 + 0.9 * r : 1));
  const c = ids[e.weighted(ws)];
  n.cards.push(c);
  e.news('🃏', `بطاقة جديدة: ${CARDS[c].icon} ${CARDS[c].name}${why ? ` (${why})` : ''}`, 'event', { to: [n.id] });
  return c;
}

/** توزيع البطاقات السنوي */
export function dealCards(e: Engine) {
  const s = e.s;
  for (const n of Object.values(s.nations)) if (n.alive) drawCard(e, n, 'بطاقة السنة');
  s.nextCards = s.day + CARD_EVERY;
}

/** الأهداف المسموحة للبطاقة */
export function cardTargets(e: Engine, n: Nation, card: CardId): { nations: NationId[]; terrs: TerrId[] } {
  const s = e.s;
  const def = CARDS[card];
  const others = Object.values(s.nations).filter((o) => o.alive && o.id !== n.id && !(n.team && o.team === n.team));
  if (def.target === 'enemy') return { nations: others.filter((o) => e.atWar(n.id, o.id)).map((o) => o.id), terrs: [] };
  if (def.target === 'any') return { nations: others.filter((o) => !e.allied(n.id, o.id)).map((o) => o.id), terrs: [] };
  if (def.target === 'terr') {
    const out = new Set<TerrId>();
    const busy = new Set(s.battles.map((b) => b.terr));
    for (const t of e.owned(n.id)) {
      for (const x of e.w.get(t.id).n) {
        const T = s.terr[x];
        if (!T || T.owner === n.id || busy.has(x)) continue;
        if (T.owner) {
          const D = s.nations[T.owner];
          if (!D?.alive || x === D.capital || e.canHit(n, D)) continue;
          if (D.stability >= 55 && T.unrest <= 0) continue;
        }
        out.add(x);
      }
    }
    return { nations: [], terrs: [...out] };
  }
  return { nations: [], terrs: [] };
}

export function playCard(e: Engine, n: Nation, card: CardId, target?: NationId, terr?: TerrId): CmdResult {
  const s = e.s;
  const i = n.cards.indexOf(card);
  if (i < 0 || !CARDS[card]) return { ok: false, msg: 'ما عندك هذي البطاقة' };
  const def = CARDS[card];
  let T: Nation | undefined;
  if (def.target === 'enemy' || def.target === 'any') {
    T = target ? s.nations[target] : undefined;
    if (!T || !cardTargets(e, n, card).nations.includes(T.id)) {
      return { ok: false, msg: def.target === 'enemy' ? 'اختر دولة أنت في حرب معها' : 'اختر دولة (مو حليفة ولا من فريقك)' };
    }
  }
  if (def.target === 'terr' && (!terr || !cardTargets(e, n, card).terrs.includes(terr))) {
    return { ok: false, msg: 'اختر أرض مجاورة: محايدة أو لدولة غير مستقرة (مو عاصمة)' };
  }
  let text = '';
  switch (card) {
    case 'boom':
      for (const t of e.owned(n.id)) t.gdp *= 1.1;
      text = 'الناتج المحلي +10%';
      break;
    case 'mobilize': {
      const inf = Math.max(10, Math.round(n.units.inf * 0.2));
      const tank = Math.max(3, Math.round(n.units.tank * 0.1));
      n.units.inf += inf;
      n.units.tank += tank;
      n.stability = clamp(n.stability - 5, 0, 100);
      text = `+${inf} مشاة و +${tank} دبابات`;
      break;
    }
    case 'shield':
      n.fx.shield = s.day + 2 * DAYS_PER_MONTH;
      text = 'دفاعك أقوى 30% لمدة شهرين';
      break;
    case 'blitz':
      n.fx.blitz = s.day + DAYS_PER_MONTH;
      text = 'لمدة شهر: هجومك أقوى 25% وجيوشك أسرع';
      break;
    case 'reluck':
      n.fortuneNext = s.day;
      text = 'عجلة الحظ جاهزة!';
      break;
    case 'supply': {
      let delayed = 0;
      for (const m of s.moves) if (m.owner === T!.id && m.kind === 'attack') { m.arrive += 15; delayed++; }
      for (const b of s.battles) if (b.att === T!.id) b.a *= 0.8;
      T!.fx.supply = s.day + 2 * DAYS_PER_MONTH;
      text = `${delayed ? delayed + ' جيوش تأخرت، و' : ''}إمدادات ${T!.name} انقطعت`;
      break;
    }
    case 'ceasefire':
      e.makePeace(n, T!, 12, true);
      text = `سلام فوري مع ${T!.name} (هدنة سنة)`;
      break;
    case 'double': {
      n.intel[T!.id] = s.day + 360;
      let stolen = '';
      if (T!.cards.length && n.cards.length - 1 < HAND_MAX) {
        const k = Math.floor(e.rand() * T!.cards.length);
        const c = T!.cards.splice(k, 1)[0];
        n.cards.push(c);
        stolen = ` وسرقت بطاقة «${CARDS[c].icon} ${CARDS[c].name}»`;
        e.news('🎭', `عميل مزدوج سرق بطاقة «${CARDS[c].name}» من يدك!`, 'event', { to: [T!.id] });
      }
      text = `أسرار ${T!.name} مكشوفة لك لمدة سنة${stolen}`;
      break;
    }
    case 'defect': {
      const t = s.terr[terr!];
      const D = t.owner ? s.nations[t.owner] : null;
      t.owner = n.id;
      t.unrest = 6;
      delete t.g; delete t.gmax; delete t.nt;
      if (D) {
        D.stability = clamp(D.stability - 6, 0, 100);
        if (D.ai && D.kind === 'bot' && e.rand() < 0.6) D.ai.grudge = n.id;
        e.recompute(D);
      }
      text = `${e.tname(t.id)} انشقت${D ? ` عن ${D.name}` : ''} وانضمت لك!`;
      e.news('🏳️', `${e.tname(t.id)} انشقت${D ? ` عن ${D.name}` : ''} وانضمت لـ ${n.name}`, 'battle', { n: [n.id, D?.id ?? ''], terr: t.id });
      break;
    }
    case 'coup': {
      const opts = GOV_SLICES.filter((x) => x.v !== T!.gov);
      const g = opts[e.weighted(opts.map((x) => x.w))].v as GovId;
      T!.gov = g;
      T!.govUntil = g === 'transitional' ? s.day + 48 * DAYS_PER_MONTH : undefined;
      T!.stability = clamp(T!.stability - 25, 0, 100);
      for (const k of COMBAT_UNITS) T!.units[k] = Math.floor(T!.units[k] * 0.9);
      text = `انقلاب في ${T!.name}! صار نظامها ${GOVS[g].name}`;
      e.news('🗡️', `انقلاب في ${T!.name}! النظام صار ${GOVS[g].icon} ${GOVS[g].name}، والاستقرار انهار`, 'event', { n: [T!.id] });
      if (T!.ai && T!.kind === 'bot' && e.rand() < 0.4) T!.ai.grudge = n.id;
      break;
    }
  }
  n.cards.splice(n.cards.indexOf(card), 1);
  e.news('🃏', `${n.name} لعبت بطاقة «${def.icon} ${def.name}»${T ? ` ضد ${T.name}` : ''}!`, 'event', { n: [n.id, ...(T ? [T.id] : [])] });
  e.recompute(n);
  if (T) e.recompute(T);
  return { ok: true, msg: `${def.icon} ${text}` };
}

/** البوتات تلعب بطاقاتها لما يكون الوقت مناسب */
export function aiCards(e: Engine, n: Nation, atWar: NationId[], danger: boolean) {
  if (!n.cards.length || e.rand() > 0.45) return;
  const s = e.s;
  const has = (c: CardId) => n.cards.includes(c);
  const play = (c: CardId, target?: NationId, terr?: TerrId) => playCard(e, n, c, target, terr).ok;
  if (has('boom') && play('boom')) return;
  if (has('reluck') && play('reluck')) return;
  if (has('mobilize') && (danger || atWar.length) && play('mobilize')) return;
  const attacked = s.battles.some((b) => b.def === n.id) || s.moves.some((m) => m.kind === 'attack' && s.terr[m.to]?.owner === n.id);
  if (has('shield') && attacked && play('shield')) return;
  if (atWar.length) {
    const enemies = atWar.map((id) => s.nations[id]).sort((a, b) => b.d.power - a.d.power);
    const big = enemies[0];
    if (has('ceasefire') && big.d.power > n.d.power * 1.3 && play('ceasefire', big.id)) return;
    if (has('supply') && attacked) {
      const att = enemies.find((x) => s.moves.some((m) => m.owner === x.id && s.terr[m.to]?.owner === n.id) || s.battles.some((b) => b.att === x.id && b.def === n.id));
      if (att && play('supply', att.id)) return;
    }
    if (has('blitz') && e.rand() < 0.5 && play('blitz')) return;
  }
  if (has('defect')) {
    const t = cardTargets(e, n, 'defect').terrs.sort((a, b) => s.terr[b].gdp - s.terr[a].gdp)[0];
    if (t && play('defect', undefined, t)) return;
  }
  const others = Object.values(s.nations).filter((o) => o.alive && o.id !== n.id && !(n.team && o.team === n.team) && !e.allied(n.id, o.id));
  const leader = others.sort((a, b) => b.d.score - a.d.score)[0];
  const foe = (n.ai?.grudge && s.nations[n.ai.grudge]?.alive ? s.nations[n.ai.grudge] : null) ?? (leader && leader.d.score > n.d.score ? leader : null);
  if (foe) {
    if (has('coup') && e.rand() < 0.5 && play('coup', foe.id)) return;
    if (has('double') && play('double', foe.id)) return;
  }
  // اليد مليانة: نلعب أي بطاقة ما تحتاج هدف عشان ما تضيع البطاقات الجاية
  if (n.cards.length >= HAND_MAX - 1) {
    for (const c of ['mobilize', 'blitz', 'shield'] as CardId[]) if (has(c) && play(c)) return;
    if (foe && has('coup') && play('coup', foe.id)) return;
  }
}
