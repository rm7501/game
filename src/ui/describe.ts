// وصف نتائج العجلات بالعربي
import {
  AREA_SLICES, ECON_NAMES, ECON_VALUES, GOVS, LEADERS, LUCK, MIL_NAMES, MIL_TIERS, MISSIONS, POP_VALUES, RESOURCES, TECH_NAMES,
  TERRAINS, UNITS,
} from '../game/defs';
import type { GovId, LeaderId, LuckId, MissionId, ResId, TerrainId, UnitType, WheelId } from '../game/types';
import { REGION_NAMES, type World } from '../game/world';
import { fmtArea, fmtMoney } from './format';

export interface ResultInfo {
  icon: string;
  title: string;
  desc: string;
  tone?: 'good' | 'bad';
  flag?: string;
}

const TIER_TONE = (i: number) => (i >= 4 ? 'good' : i <= 1 ? 'bad' : undefined);

export function unitsSummary(u: Partial<Record<UnitType, number>>): string {
  return (Object.entries(u) as [UnitType, number][])
    .filter(([, n]) => n > 0)
    .map(([k, n]) => `${n} ${UNITS[k].name}`)
    .join('، ');
}

export function describe(w: WheelId, v: number | string, world: World): ResultInfo {
  switch (w) {
    case 'area': {
      const s = AREA_SLICES[v as number];
      return { icon: s.icon, title: `دولة ${s.label}`, desc: s.sub ?? '', tone: (v as number) >= 4 ? 'good' : (v as number) === 0 ? 'bad' : undefined };
    }
    case 'country': {
      const m = world.country(v as string);
      const regions = m.provs.length > 1 ? ` · ${m.provs.length} مناطق` : '';
      return { icon: '📍', title: m.ar, desc: `${REGION_NAMES[m.reg] ?? ''} · ${fmtArea(m.area)}${regions}`, flag: m.id };
    }
    case 'pop':
      return { icon: '👥', title: `${POP_VALUES[v as number]} مليون نسمة`, desc: 'عدد الشعب يحدد التجنيد والنمو', tone: TIER_TONE(v as number) };
    case 'econ':
      return { icon: '📈', title: `اقتصاد ${ECON_NAMES[v as number]}`, desc: `الناتج المحلي ${fmtMoney(ECON_VALUES[v as number])} سنوياً`, tone: TIER_TONE(v as number) };
    case 'mil':
      return { icon: '⚔️', title: `جيش ${MIL_NAMES[v as number]}`, desc: unitsSummary(MIL_TIERS[v as number]), tone: TIER_TONE(v as number) };
    case 'res': {
      const r = RESOURCES[v as ResId];
      return { icon: r.icon, title: r.name, desc: r.desc, tone: v === 'none' ? 'bad' : v === 'oil' || v === 'uranium' ? 'good' : undefined };
    }
    case 'gov': {
      const g = GOVS[v as GovId];
      return { icon: g.icon, title: g.name, desc: g.desc };
    }
    case 'tech':
      return { icon: '🧪', title: `تكنولوجيا ${TECH_NAMES[v as number]}`, desc: `مستوى ${v} من 6${(v as number) >= 2 ? ' · تقدر تصنع طائرات وصواريخ' : ' · الطائرات والصواريخ تحتاج مستوى 2'}`, tone: (v as number) >= 4 ? 'good' : (v as number) === 1 ? 'bad' : undefined };
    case 'leader': {
      const l = LEADERS[v as LeaderId];
      return { icon: l.icon, title: l.name, desc: l.desc, tone: 'good' };
    }
    case 'terrain': {
      const t = TERRAINS[v as TerrainId];
      return { icon: t.icon, title: t.name, desc: t.desc };
    }
    case 'mission': {
      const m = MISSIONS[v as MissionId];
      return { icon: m.icon, title: `مهمة: ${m.name}`, desc: 'هدفك السري يطلع لك أول ما تبدأ اللعبة (محد يعرفه غيرك)' };
    }
    case 'luck': {
      const l = LUCK[v as LuckId];
      return { icon: l.icon, title: l.name, desc: l.desc, tone: l.good ? 'good' : 'bad' };
    }
  }
}
