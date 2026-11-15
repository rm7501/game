// سجل اللعبة: لقطة كل 3 شهور (أصحاب الأراضي + أرقام الدول) عشان الإعادة والرسوم بالنهاية
import type { Engine } from './engine';
import type { GameState, History } from './types';

export const HIST_EVERY = 90; // يوم

export function recordHistory(e: Engine) {
  const s = e.s;
  const h: History = (s.hist ??= { n: [], f: [], ev: [] });
  for (const id of Object.keys(s.nations)) if (!h.n.includes(id)) h.n.push(id);
  const idx = new Map(h.n.map((id, i) => [id, i + 1]));
  let o = '';
  for (const m of e.w.list) {
    const owner = s.terr[m.id]?.owner;
    o += String.fromCharCode(48 + (owner ? idx.get(owner) ?? 0 : 0));
  }
  const v = h.n.map((id) => {
    const n = s.nations[id];
    return n?.alive ? [Math.round(n.d.score), Math.round(n.d.power), Math.round(n.d.gdp), n.d.terrs] : [];
  });
  const last = h.f[h.f.length - 1];
  if (last && last.d === s.day) h.f[h.f.length - 1] = { d: s.day, o, v };
  else h.f.push({ d: s.day, o, v });
}

export function addHistEvent(s: GameState, icon: string, text: string) {
  const h: History = (s.hist ??= { n: [], f: [], ev: [] });
  h.ev.push({ d: s.day, icon, text });
  if (h.ev.length > 120) h.ev.splice(0, h.ev.length - 120);
}

/** صاحب الأرض في إطار معين */
export function frameOwner(h: History, frame: number, terrIndex: number): string {
  const f = h.f[frame];
  if (!f) return '';
  const k = f.o.charCodeAt(terrIndex) - 48;
  return k > 0 ? h.n[k - 1] ?? '' : '';
}
