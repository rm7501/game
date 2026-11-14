// عجلة المكان: ضوء يتنقل بين الدول المرشحة على الخريطة لين يوقف على دولتك
import { useEffect, useRef } from 'preact/hooks';
import type { TerrId } from '../game/types';
import type { World } from '../game/world';
import { sfx } from './audio';
import { MapRenderer } from './map';

interface Props {
  world: World;
  candidates: TerrId[];
  result: TerrId | null;
  spinning: boolean;
  onStop: () => void;
  focus?: TerrId | null;
}

export function CountryRoulette({ world, candidates, result, spinning, onStop, focus }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<MapRenderer | null>(null);
  const st = useRef({ running: false, timer: 0, start: 0, result: null as TerrId | null, cb: onStop, cands: candidates, flash: null as SVGElement | null });
  st.current.result = result;
  st.current.cb = onStop;
  st.current.cands = candidates;

  useEffect(() => {
    if (!box.current) return;
    const m = new MapRenderer(box.current, world, { interactive: false, minimal: true });
    map.current = m;
    return () => {
      clearTimeout(st.current.timer);
      m.destroy();
      map.current = null;
    };
  }, []);

  useEffect(() => {
    if (!st.current.running) map.current?.highlight(candidates, 'cand');
  }, [candidates.join(',')]);

  useEffect(() => {
    if (focus && map.current && !st.current.running) {
      map.current.highlight([focus], 'roul-final');
      map.current.flyTo(focus, undefined, 0, -0.22);
    }
  }, [focus]);

  useEffect(() => {
    const s = st.current;
    if (!spinning || s.running || !map.current) return;
    s.running = true;
    s.start = performance.now();
    map.current.resetView();
    map.current.highlight(s.cands, 'cand');
    let delay = 55;
    let prev = '';
    const step = () => {
      const m = map.current;
      if (!m) return;
      const el = performance.now() - s.start;
      const pool = s.cands.length ? s.cands : [s.result ?? ''];
      let pick = pool[Math.floor(Math.random() * pool.length)];
      if (pool.length > 1) while (pick === prev) pick = pool[Math.floor(Math.random() * pool.length)];
      const finishing = s.result && el > 2600 && delay > 330;
      if (finishing) pick = s.result!;
      prev = pick;
      s.flash?.remove();
      s.flash = m.flash(pick, finishing ? 'roul-final' : 'roul') ?? null;
      sfx.tick();
      if (finishing) {
        s.running = false;
        setTimeout(() => {
          map.current?.flyTo(pick, undefined, 1100, -0.22);
          setTimeout(() => s.cb(), 1150);
        }, 250);
        return;
      }
      if (el > 1200) delay = Math.min(420, delay * 1.13);
      s.timer = window.setTimeout(step, delay);
    };
    step();
  }, [spinning]);

  return <div class="roulette" ref={box} />;
}
