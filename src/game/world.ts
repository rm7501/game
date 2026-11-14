// بيانات خريطة العالم الثابتة + حساب المسافات والجيران
import type { Topology } from 'topojson-specification';
import type { TerrId } from './types';

export interface TerrMeta {
  id: TerrId;
  ar: string;
  en: string;
  reg: string;
  p: 0 | 1; // قابلة للاختيار في عجلة المكان
  area: number;
  cls: number;
  lp: [number, number]; // نقطة الاسم (lon, lat)
  b: [[number, number], [number, number]];
  c: 0 | 1; // ساحلية
  n: TerrId[]; // جيران بريين (مع المضائق)
  s: Record<TerrId, number>; // جيران بحريين قريبين
  a: [number, number][]; // نقاط تمثيلية للمسافات
}

export interface WorldData {
  topo: Topology;
  meta: TerrMeta[];
}

const R = 6371;
const toRad = Math.PI / 180;
export function haversine(a: [number, number], b: [number, number]): number {
  const dLat = (b[1] - a[1]) * toRad;
  const dLon = (b[0] - a[0]) * toRad;
  const s = Math.sin(dLat / 2) ** 2 + Math.cos(a[1] * toRad) * Math.cos(b[1] * toRad) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(s)));
}

export const REGION_NAMES: Record<string, string> = {
  AS: 'آسيا', EU: 'أوروبا', AF: 'أفريقيا', NA: 'أمريكا الشمالية', SA: 'أمريكا الجنوبية', OC: 'أوقيانوسيا',
};

export class World {
  readonly data: WorldData;
  readonly list: TerrMeta[];
  readonly byId: Map<TerrId, TerrMeta>;
  readonly totalArea: number;
  private distCache = new Map<string, number>();

  constructor(data: WorldData) {
    this.data = data;
    this.list = data.meta;
    this.byId = new Map(data.meta.map((m) => [m.id, m]));
    this.totalArea = data.meta.reduce((s, m) => s + m.area, 0);
  }

  get(id: TerrId): TerrMeta {
    const m = this.byId.get(id);
    if (!m) throw new Error('Unknown territory ' + id);
    return m;
  }

  name(id: TerrId): string {
    return this.byId.get(id)?.ar ?? id;
  }

  isLandNeighbor(a: TerrId, b: TerrId): boolean {
    return this.get(a).n.includes(b);
  }

  /** أقل مسافة تقريبية (كم) بين دولتين */
  dist(a: TerrId, b: TerrId): number {
    if (a === b) return 0;
    const k = a < b ? a + b : b + a;
    const c = this.distCache.get(k);
    if (c !== undefined) return c;
    const ma = this.get(a);
    const mb = this.get(b);
    let d: number;
    if (ma.n.includes(b)) d = 0;
    else if (ma.s[b] !== undefined) d = ma.s[b];
    else {
      d = Infinity;
      for (const p of ma.a) for (const q of mb.a) {
        const x = haversine(p, q);
        if (x < d) d = x;
      }
    }
    this.distCache.set(k, d);
    return d;
  }

  /** المسافة بين مركزي الدولتين (لحساب وقت التحرك) */
  centerDist(a: TerrId, b: TerrId): number {
    return haversine(this.get(a).lp, this.get(b).lp);
  }
}
