// رسم خريطة العالم (SVG + D3) مع التكبير والتحريك والجيوش
import { geoPath, geoProjection, type GeoProjection, type GeoPermissibleObjects } from 'd3-geo';
import { select } from 'd3-selection';
import { zoom, zoomIdentity, type ZoomBehavior } from 'd3-zoom';
import { feature, mesh } from 'topojson-client';
import type { Feature, FeatureCollection, Geometry } from 'geojson';
import type { GeometryCollection } from 'topojson-specification';
import type { GameState, Movement, NationId, TerrId } from '../game/types';
import type { World } from '../game/world';

const NS = 'http://www.w3.org/2000/svg';

function millerRaw(l: number, p: number): [number, number] {
  return [l, 1.25 * Math.log(Math.tan(Math.PI / 4 + 0.4 * p))];
}
millerRaw.invert = (x: number, y: number): [number, number] => [x, 2.5 * Math.atan(Math.exp(0.8 * y)) - 0.625 * Math.PI];

function hash(s: string) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h);
}

export function neutralFill(id: string) {
  const h = hash(id);
  return `hsl(${205 + (h % 30)}, ${8 + (h % 7)}%, ${25 + (h % 9)}%)`;
}

function el<K extends keyof SVGElementTagNameMap>(tag: K, attrs: Record<string, string | number> = {}, parent?: Element): SVGElementTagNameMap[K] {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, String(v));
  if (parent) parent.appendChild(e);
  return e;
}

export interface MapOpts {
  onSelect?: (id: TerrId | null) => void;
  onHover?: (id: TerrId | null, x: number, y: number) => void;
  interactive?: boolean;
  minimal?: boolean; // للخرائط الصغيرة (عجلة المكان)
}

const MOVE_ICON: Record<string, string> = { attack: '⚔️', return: '↩️', missile: '🚀', nuke: '☢️' };

export class MapRenderer {
  readonly svg: SVGSVGElement;
  private root: SVGGElement;
  private gLand: SVGGElement;
  private gHl: SVGGElement;
  private gMarkers: SVGGElement;
  private gLabels: SVGGElement;
  private gMoves: SVGGElement;
  private gFx: SVGGElement;
  private borders: SVGPathElement;
  private nborders: SVGPathElement;
  private coast: SVGPathElement;
  private mine: SVGPathElement;
  private selPath: SVGPathElement;
  private proj!: GeoProjection;
  private pathGen!: ReturnType<typeof geoPath>;
  private fc: FeatureCollection<Geometry>;
  private feats = new Map<TerrId, Feature<Geometry>>();
  private paths = new Map<TerrId, SVGPathElement>();
  private markers = new Map<TerrId, SVGCircleElement>();
  private tiny = new Set<TerrId>();
  private widths = new Map<TerrId, number>();
  private tLabels = new Map<TerrId, SVGTextElement>();
  private nLabels = new Map<NationId, SVGTextElement>();
  private moveEls = new Map<number, { line: SVGPathElement; icon: SVGGElement; p0: [number, number]; c: [number, number]; p1: [number, number] }>();
  private zoomer?: ZoomBehavior<SVGSVGElement, unknown>;
  private ro?: ResizeObserver;
  private ownersKey = '';
  private fillKey = '';
  private lastState?: GameState;
  private myId?: NationId;
  private selected: TerrId | null = null;
  private labelRaf = 0;
  W = 800;
  H = 450;
  k = 1;

  constructor(private container: HTMLElement, private world: World, private opts: MapOpts = {}) {
    const topo = world.data.topo;
    const obj = topo.objects.t as GeometryCollection;
    this.fc = feature(topo, obj) as unknown as FeatureCollection<Geometry>;
    for (const f of this.fc.features) this.feats.set(String(f.id), f);

    this.svg = el('svg', { class: 'map-svg' }) as SVGSVGElement;
    container.appendChild(this.svg);
    const defs = el('defs', {}, this.svg);
    const grad = el('radialGradient', { id: 'oceanGrad', cx: '50%', cy: '45%', r: '75%' }, defs);
    el('stop', { offset: '0%', 'stop-color': '#12305a' }, grad);
    el('stop', { offset: '100%', 'stop-color': '#08142b' }, grad);
    el('rect', { class: 'ocean', width: '100%', height: '100%', fill: 'url(#oceanGrad)' }, this.svg);
    this.root = el('g', { class: 'map-root' }, this.svg);
    this.gLand = el('g', { class: 'land' }, this.root);
    this.coast = el('path', { class: 'coast' }, this.root);
    this.borders = el('path', { class: 'borders' }, this.root);
    this.nborders = el('path', { class: 'nborders' }, this.root);
    this.mine = el('path', { class: 'mine-outline' }, this.root);
    this.gHl = el('g', { class: 'hl-layer' }, this.root);
    this.selPath = el('path', { class: 'sel-outline' }, this.root);
    this.gMarkers = el('g', { class: 'markers' }, this.root);
    this.gMoves = el('g', { class: 'moves' }, this.root);
    this.gLabels = el('g', { class: 'labels' }, this.root);
    this.gFx = el('g', { class: 'fx' }, this.root);

    for (const f of this.fc.features) {
      const id = String(f.id);
      const p = el('path', { 'data-id': id, fill: neutralFill(id) }, this.gLand);
      this.paths.set(id, p);
    }

    this.bindEvents(opts.interactive !== false);
    this.layout();
    this.ro = new ResizeObserver(() => {
      const r = this.container.getBoundingClientRect();
      if (Math.abs(r.width - this.W) > 2 || Math.abs(r.height - this.H) > 2) this.layout();
    });
    this.ro.observe(container);
  }

  private bindEvents(interactive: boolean) {
    this.zoomer = zoom<SVGSVGElement, unknown>()
      .scaleExtent([1, 48])
      .filter((ev: Event) => interactive && (!(ev as MouseEvent).button || ev.type === 'wheel'))
      .on('zoom', (ev) => {
        const t = ev.transform;
        this.root.setAttribute('transform', t.toString());
        if (Math.abs(t.k - this.k) > 1e-3) {
          this.k = t.k;
          this.scheduleLabels();
        }
      });
    select(this.svg).call(this.zoomer).on('dblclick.zoom', null);
    if (!interactive) return;
    const onPick = (e: Event) => {
      const t = e.target as Element;
      const id = t.getAttribute('data-id');
      this.opts.onSelect?.(id);
    };
    this.svg.addEventListener('click', onPick);
    if (this.opts.onHover) {
      this.svg.addEventListener('mousemove', (e) => {
        const id = (e.target as Element).getAttribute?.('data-id');
        this.opts.onHover?.(id, e.clientX, e.clientY);
      });
      this.svg.addEventListener('mouseleave', () => this.opts.onHover?.(null, 0, 0));
    }
  }

  layout() {
    const r = this.container.getBoundingClientRect();
    this.W = Math.max(200, r.width);
    this.H = Math.max(150, r.height);
    this.svg.setAttribute('width', String(this.W));
    this.svg.setAttribute('height', String(this.H));
    const pad = this.opts.minimal ? 4 : 10;
    this.proj = geoProjection(millerRaw).fitExtent(
      [[pad, pad], [this.W - pad, this.H - pad]],
      this.fc as unknown as GeoPermissibleObjects,
    );
    this.pathGen = geoPath(this.proj);
    const topo = this.world.data.topo;
    const obj = topo.objects.t as GeometryCollection;
    for (const [id, f] of this.feats) {
      const d = this.pathGen(f as GeoPermissibleObjects) ?? '';
      this.paths.get(id)!.setAttribute('d', d);
      const b = this.pathGen.bounds(f as GeoPermissibleObjects);
      const w = b[1][0] - b[0][0];
      const h = b[1][1] - b[0][1];
      this.widths.set(id, w);
      if (w * h < 30 || w < 4) this.tiny.add(id);
    }
    this.coast.setAttribute('d', this.pathGen(mesh(topo, obj, (a, b) => a === b) as GeoPermissibleObjects) ?? '');
    this.borders.setAttribute('d', this.pathGen(mesh(topo, obj, (a, b) => a !== b) as GeoPermissibleObjects) ?? '');
    // علامات الدول الصغيرة جداً
    this.gMarkers.textContent = '';
    this.markers.clear();
    for (const id of this.tiny) {
      const [x, y] = this.pt(this.world.get(id).lp);
      const c = el('circle', { cx: x, cy: y, r: 3, 'data-id': id, class: 'tiny-marker', fill: this.paths.get(id)!.getAttribute('fill') ?? '#555' }, this.gMarkers);
      this.markers.set(id, c);
    }
    // أسماء الدول
    this.gLabels.textContent = '';
    this.tLabels.clear();
    this.nLabels.clear();
    if (!this.opts.minimal) {
      for (const m of this.world.list) {
        const [x, y] = this.pt(m.lp);
        const t = el('text', { x, y, class: 'tlabel' }, this.gLabels);
        t.textContent = m.ar;
        this.tLabels.set(m.id, t);
      }
    }
    if (this.zoomer) {
      this.zoomer.translateExtent([[-this.W * 0.05, -this.H * 0.1], [this.W * 1.05, this.H * 1.1]]);
    }
    this.ownersKey = '';
    this.fillKey = '';
    this.moveEls.forEach((m) => { m.line.remove(); m.icon.remove(); });
    this.moveEls.clear();
    if (this.lastState) this.update(this.lastState, this.myId);
    if (this.selected) this.select(this.selected);
    this.scheduleLabels();
  }

  pt(lonlat: [number, number]): [number, number] {
    return (this.proj(lonlat) as [number, number]) ?? [0, 0];
  }

  private scheduleLabels() {
    if (this.labelRaf) return;
    this.labelRaf = requestAnimationFrame(() => {
      this.labelRaf = 0;
      this.updateLabels();
    });
  }

  private updateLabels() {
    const k = this.k;
    this.root.style.setProperty('--k', String(k));
    for (const [id, c] of this.markers) {
      const owned = !!this.lastState?.terr[id]?.owner;
      c.setAttribute('r', String((owned ? 5.5 : Math.max(2.6, 4.2 - k * 0.15)) / k));
    }
    const s = this.lastState;
    const fs = 10 / k;
    for (const [id, t] of this.tLabels) {
      const w = (this.widths.get(id) ?? 0) * k;
      const owner = s?.terr[id]?.owner;
      const n = owner ? s?.nations[owner] : undefined;
      const isCapital = n && n.capital === id;
      const show = !isCapital && w > 55 && k > 1.6;
      t.style.display = show ? '' : 'none';
      if (show) t.setAttribute('font-size', String(fs));
    }
    for (const [nid, t] of this.nLabels) {
      const n = s?.nations[nid];
      if (!n) continue;
      const size = Math.min(22, 10 + Math.log2(1 + n.d.terrs) * 2.6) / Math.pow(k, 0.85);
      t.setAttribute('font-size', String(size));
      // الدول الصغيرة جداً: الاسم فوق العلامة عشان ما يغطيها
      t.setAttribute('dy', this.tiny.has(n.capital) ? String(-12 / k) : '0');
    }
    for (const [, m] of this.moveEls) m.icon.setAttribute('transform', m.icon.getAttribute('transform')!.replace(/scale\([^)]*\)/, `scale(${1 / Math.sqrt(k)})`));
  }

  /** تحديث الألوان والحدود حسب حالة اللعبة */
  update(s: GameState, myId?: NationId) {
    this.lastState = s;
    this.myId = myId;
    let ok = '';
    let fk = '';
    for (const id in s.terr) {
      const t = s.terr[id];
      ok += t.owner + ',';
      fk += (t.owner ? s.nations[t.owner]?.color : '') + (t.nuked > 0 ? 'n' : '') + (t.unrest > 0 ? 'u' : '') + ';';
    }
    fk += myId ?? '';
    if (fk !== this.fillKey) {
      this.fillKey = fk;
      for (const [id, p] of this.paths) {
        const t = s.terr[id];
        const n = t?.owner ? s.nations[t.owner] : undefined;
        const fill = n ? n.color : neutralFill(id);
        p.setAttribute('fill', fill);
        p.classList.toggle('owned', !!n);
        p.classList.toggle('nuked', !!t && t.nuked > 0);
        p.classList.toggle('unrest', !!t && t.unrest > 0);
        const mk = this.markers.get(id);
        if (mk) {
          mk.setAttribute('fill', fill);
          mk.classList.toggle('owned', !!n);
        }
      }
      this.scheduleLabels();
    }
    if (ok !== this.ownersKey) {
      this.ownersKey = ok;
      const topo = this.world.data.topo;
      const obj = topo.objects.t as GeometryCollection;
      const own = (g: { id?: string | number }) => s.terr[String(g.id)]?.owner ?? '';
      this.nborders.setAttribute(
        'd',
        this.pathGen(mesh(topo, obj, (a, b) => a !== b && (own(a) !== own(b) || own(a) === '')) as GeoPermissibleObjects) ?? '',
      );
      if (myId) {
        const mineGeoms = obj.geometries.filter((g) => own(g) === myId);
        this.mine.setAttribute('d', mineGeoms.length ? this.pathGen(mesh(topo, { type: 'GeometryCollection', geometries: mineGeoms } as GeometryCollection, (a, b) => a === b || own(a) !== own(b)) as GeoPermissibleObjects) ?? '' : '');
      } else this.mine.setAttribute('d', '');
    }
    // أسماء الدول (اللاعبين والبوتات)
    if (!this.opts.minimal) {
      const alive = new Set<NationId>();
      for (const n of Object.values(s.nations)) {
        if (!n.alive) continue;
        alive.add(n.id);
        let t = this.nLabels.get(n.id);
        if (!t) {
          t = el('text', { class: 'nlabel' }, this.gLabels);
          this.nLabels.set(n.id, t);
        }
        const cap = this.world.byId.get(n.capital);
        if (!cap) continue;
        const [x, y] = this.pt(cap.lp);
        t.setAttribute('x', String(x));
        t.setAttribute('y', String(y));
        const label = `★ ${n.name}`;
        if (t.textContent !== label) t.textContent = label;
        t.classList.toggle('me', n.id === myId);
      }
      for (const [id, t] of this.nLabels) if (!alive.has(id)) { t.remove(); this.nLabels.delete(id); }
      this.scheduleLabels();
    }
    this.syncMoves(s);
  }

  private syncMoves(s: GameState) {
    const seen = new Set<number>();
    for (const m of s.moves) {
      seen.add(m.id);
      if (this.moveEls.has(m.id)) continue;
      const n = s.nations[m.owner];
      const p0 = this.pt(this.world.get(m.from).lp);
      let p1 = this.pt(this.world.get(m.to).lp);
      // عبور خط التاريخ
      if (Math.abs(p1[0] - p0[0]) > this.W * 0.5) p1 = [p1[0] + (p1[0] < p0[0] ? this.W : -this.W) * 0.98, p1[1]];
      const dx = p1[0] - p0[0];
      const dy = p1[1] - p0[1];
      const len = Math.hypot(dx, dy) || 1;
      const bend = Math.min(60, len * 0.25);
      const c: [number, number] = [(p0[0] + p1[0]) / 2 + (dy / len) * bend * -1, (p0[1] + p1[1]) / 2 + (dx / len) * bend];
      const cls = `move move-${m.kind}${m.naval ? ' naval' : ''}${m.owner === this.myId ? ' mine' : ''}`;
      const line = el('path', { d: `M${p0[0]},${p0[1]} Q${c[0]},${c[1]} ${p1[0]},${p1[1]}`, class: cls, stroke: n?.color ?? '#fff' }, this.gMoves);
      const icon = el('g', { class: 'move-icon', transform: `translate(${p0[0]},${p0[1]}) scale(1)` }, this.gMoves);
      el('circle', { r: 9, fill: n?.color ?? '#fff', class: 'move-dot' }, icon);
      const tx = el('text', { class: 'move-emoji', y: 3.5 }, icon);
      tx.textContent = m.naval && m.kind === 'attack' ? '🚢' : MOVE_ICON[m.kind];
      this.moveEls.set(m.id, { line, icon, p0, c, p1 });
    }
    for (const [id, e] of this.moveEls) {
      if (!seen.has(id)) {
        e.line.remove();
        e.icon.remove();
        this.moveEls.delete(id);
      }
    }
  }

  /** تحريك أيقونات الجيوش (كل فريم) */
  animate(moves: Movement[], nowDay: number) {
    const sc = 1 / Math.sqrt(this.k);
    for (const m of moves) {
      const e = this.moveEls.get(m.id);
      if (!e) continue;
      const t = Math.max(0, Math.min(1, (nowDay - m.depart) / Math.max(1, m.arrive - m.depart)));
      const u = 1 - t;
      const x = u * u * e.p0[0] + 2 * u * t * e.c[0] + t * t * e.p1[0];
      const y = u * u * e.p0[1] + 2 * u * t * e.c[1] + t * t * e.p1[1];
      e.icon.setAttribute('transform', `translate(${x.toFixed(1)},${y.toFixed(1)}) scale(${sc})`);
    }
  }

  select(id: TerrId | null) {
    this.selected = id;
    if (!id || !this.feats.has(id)) {
      this.selPath.setAttribute('d', '');
      return;
    }
    this.selPath.setAttribute('d', this.paths.get(id)!.getAttribute('d') ?? '');
  }

  /** تمييز مجموعة دول (أهداف ممكنة / خيارات العجلة) */
  highlight(ids: TerrId[], cls = 'hl') {
    this.gHl.textContent = '';
    for (const id of ids) {
      const p = this.paths.get(id);
      if (!p) continue;
      el('path', { d: p.getAttribute('d') ?? '', class: cls }, this.gHl);
      if (this.tiny.has(id)) {
        const [x, y] = this.pt(this.world.get(id).lp);
        el('circle', { cx: x, cy: y, r: 5 / Math.sqrt(this.k), class: cls + '-dot' }, this.gHl);
      }
    }
  }

  flash(id: TerrId, cls: string) {
    const p = this.paths.get(id);
    if (!p) return;
    const e = el('path', { d: p.getAttribute('d') ?? '', class: cls }, this.gHl);
    if (this.tiny.has(id)) {
      const [x, y] = this.pt(this.world.get(id).lp);
      el('circle', { cx: x, cy: y, r: 6, class: cls + '-dot' }, this.gHl);
    }
    return e;
  }

  explode(id: TerrId, kind: 'battle' | 'missile' | 'nuke' = 'battle') {
    const m = this.world.byId.get(id);
    if (!m) return;
    const [x, y] = this.pt(m.lp);
    const g = el('g', { transform: `translate(${x},${y}) scale(${1 / Math.sqrt(this.k)})`, class: `boom boom-${kind}` }, this.gFx);
    el('circle', { r: kind === 'nuke' ? 40 : 16, class: 'boom-ring' }, g);
    el('circle', { r: kind === 'nuke' ? 22 : 8, class: 'boom-core' }, g);
    const t = el('text', { class: 'boom-emoji', y: 5 }, g);
    t.textContent = kind === 'nuke' ? '☢️' : kind === 'missile' ? '💥' : '💥';
    setTimeout(() => g.remove(), kind === 'nuke' ? 2600 : 1400);
  }

  flyTo(id: TerrId, scale?: number, ms = 900, yBias = 0) {
    const f = this.feats.get(id);
    if (!f || !this.zoomer) return;
    const b = this.pathGen.bounds(f as GeoPermissibleObjects);
    let [[x0, y0], [x1, y1]] = b;
    // الدول اللي عابرة خط التاريخ أو فيها جزر بعيدة: نركز على نقطة الاسم
    if (x1 - x0 > this.W * 0.4) {
      const [cx, cy] = this.pt(this.world.get(id).lp);
      x0 = cx - this.W * 0.1; x1 = cx + this.W * 0.1; y0 = cy - this.H * 0.1; y1 = cy + this.H * 0.1;
    }
    const w = Math.max(x1 - x0, 6);
    const h = Math.max(y1 - y0, 6);
    const k = scale ?? Math.max(1.2, Math.min(18, 0.35 / Math.max(w / this.W, h / this.H)));
    const cx = (x0 + x1) / 2;
    const cy = (y0 + y1) / 2;
    const t = zoomIdentity.translate(this.W / 2 - k * cx, this.H * (0.5 + yBias) - k * cy).scale(k);
    const sel = select(this.svg);
    if (ms > 0) {
      // انتقال بسيط بدون d3-transition
      const from = { x: this.currentT().x, y: this.currentT().y, k: this.currentT().k };
      const start = performance.now();
      const step = (now: number) => {
        const p = Math.min(1, (now - start) / ms);
        const e = p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;
        const kk = from.k + (t.k - from.k) * e;
        const xx = from.x + (t.x - from.x) * e;
        const yy = from.y + (t.y - from.y) * e;
        sel.call(this.zoomer!.transform, zoomIdentity.translate(xx, yy).scale(kk));
        if (p < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    } else sel.call(this.zoomer.transform, t);
  }

  resetView() {
    if (this.zoomer) select(this.svg).call(this.zoomer.transform, zoomIdentity);
  }

  zoomBy(f: number) {
    if (this.zoomer) select(this.svg).call(this.zoomer.scaleBy, f);
  }

  private currentT() {
    const tr = (this.svg as unknown as { __zoom?: { x: number; y: number; k: number } }).__zoom;
    return tr ?? { x: 0, y: 0, k: 1 };
  }

  destroy() {
    this.ro?.disconnect();
    if (this.labelRaf) cancelAnimationFrame(this.labelRaf);
    this.svg.remove();
  }
}
