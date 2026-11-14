// عجلة الحظ (Canvas) مع أنيميشن ودوران حقيقي وأصوات
import { useEffect, useRef } from 'preact/hooks';
import type { Slice } from '../game/defs';
import { sfx } from './audio';

const COLORS = ['#e63946', '#f4a261', '#2a9d8f', '#457b9d', '#8e44ad', '#d4a017', '#06a77d', '#ef476f', '#118ab2', '#c86b00', '#7209b7', '#3a86ff'];
const TAU = Math.PI * 2;

interface Props {
  slices: Slice[];
  target: number | null; // رقم الشريحة الفائزة
  spinning: boolean;
  onStop: () => void;
  size?: number;
  hub?: string;
}

export function WheelCanvas({ slices, target, spinning, onStop, size = 340, hub = '🎡' }: Props) {
  const cv = useRef<HTMLCanvasElement>(null);
  const pointer = useRef<HTMLDivElement>(null);
  const st = useRef({
    rot: Math.random() * TAU,
    phase: 'idle' as 'idle' | 'free' | 'ease',
    v: 0,
    from: 0,
    to: 0,
    t0: 0,
    dur: 0,
    lastIdx: -1,
    lastTick: 0,
    raf: 0,
    stopCb: onStop,
  });
  st.current.stopCb = onStop;
  const visible = slices.filter((s) => s.w > 0);
  const total = visible.reduce((a, s) => a + s.w, 0) || 1;
  // بداية ونهاية كل شريحة (زاوية مع عقارب الساعة من الأعلى)
  const spans = (() => {
    let a = 0;
    return visible.map((s) => {
      const w = (s.w / total) * TAU;
      const r = [a, a + w] as [number, number];
      a += w;
      return r;
    });
  })();
  const geo = useRef({ spans, visible });
  geo.current = { spans, visible };

  const draw = () => {
    const c = cv.current;
    if (!c) return;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    if (c.width !== size * dpr) {
      c.width = size * dpr;
      c.height = size * dpr;
    }
    const ctx = c.getContext('2d')!;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, size, size);
    const R = size / 2 - 8;
    const cx = size / 2;
    const cy = size / 2;
    const { spans, visible } = geo.current;
    const rot = st.current.rot;
    // الإطار
    ctx.beginPath();
    ctx.arc(cx, cy, R + 6, 0, TAU);
    const rim = ctx.createLinearGradient(0, 0, size, size);
    rim.addColorStop(0, '#f5d76e');
    rim.addColorStop(0.5, '#a9791c');
    rim.addColorStop(1, '#f5d76e');
    ctx.fillStyle = rim;
    ctx.fill();
    for (let i = 0; i < visible.length; i++) {
      const [a0, a1] = spans[i];
      // الزاوية على الشاشة: من الأعلى مع عقارب الساعة
      const s0 = a0 + rot - Math.PI / 2;
      const s1 = a1 + rot - Math.PI / 2;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, R, s0, s1);
      ctx.closePath();
      ctx.fillStyle = visible[i].color ?? COLORS[i % COLORS.length];
      ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,0.55)';
      ctx.lineWidth = 1.5;
      ctx.stroke();
      // النص
      const mid = (s0 + s1) / 2;
      const span = a1 - a0;
      // النص على النص الأيسر من العجلة نقلبه عشان ما يطلع مقلوب
      const flip = Math.cos(mid) < 0;
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(flip ? mid + Math.PI : mid);
      const dir = flip ? -1 : 1;
      const big = span > 0.5;
      ctx.font = `${Math.round(size * (big ? 0.07 : 0.058))}px "Noto Color Emoji", "Apple Color Emoji", "Segoe UI Emoji", sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(visible[i].icon, dir * R * 0.84, 0);
      const fs = Math.max(9, Math.min(size * 0.05, (span * R * 0.55) / 1.1));
      ctx.font = `700 ${fs}px Cairo, Tahoma, sans-serif`;
      ctx.direction = 'rtl';
      ctx.textAlign = flip ? 'left' : 'right';
      ctx.lineWidth = 3;
      ctx.strokeStyle = 'rgba(0,0,0,0.45)';
      ctx.fillStyle = '#fff';
      const label = visible[i].label;
      ctx.strokeText(label, dir * R * 0.72, 1);
      ctx.fillText(label, dir * R * 0.72, 1);
      ctx.restore();
    }
    // المحور
    ctx.beginPath();
    ctx.arc(cx, cy, R * 0.17, 0, TAU);
    const hubG = ctx.createRadialGradient(cx - 6, cy - 6, 2, cx, cy, R * 0.17);
    hubG.addColorStop(0, '#fff6d5');
    hubG.addColorStop(1, '#c8962a');
    ctx.fillStyle = hubG;
    ctx.fill();
    ctx.strokeStyle = '#7a5410';
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.font = `${Math.round(R * 0.16)}px "Noto Color Emoji", "Apple Color Emoji", "Segoe UI Emoji", sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(hub, cx, cy + 1);
  };

  const idxAt = (rot: number) => {
    const a = (((-rot) % TAU) + TAU) % TAU;
    const { spans } = geo.current;
    for (let i = 0; i < spans.length; i++) if (a >= spans[i][0] && a < spans[i][1]) return i;
    return spans.length - 1;
  };

  const tickCheck = (now: number) => {
    const i = idxAt(st.current.rot);
    if (i !== st.current.lastIdx) {
      st.current.lastIdx = i;
      if (now - st.current.lastTick > 35) {
        st.current.lastTick = now;
        sfx.tick();
        const p = pointer.current;
        if (p) {
          p.classList.remove('flick');
          void p.offsetWidth;
          p.classList.add('flick');
        }
      }
    }
  };

  const frame = (now: number) => {
    const s = st.current;
    if (s.phase === 'free') {
      s.rot += s.v / 60;
    } else if (s.phase === 'ease') {
      const p = Math.min(1, (now - s.t0) / s.dur);
      const e = 1 - Math.pow(1 - p, 3);
      s.rot = s.from + (s.to - s.from) * e;
      if (p >= 1) {
        s.phase = 'idle';
        draw();
        s.raf = 0;
        s.stopCb();
        return;
      }
    }
    tickCheck(now);
    draw();
    s.raf = requestAnimationFrame(frame);
  };

  const easeTo = (idx: number) => {
    const s = st.current;
    const { spans, visible } = geo.current;
    // الشريحة المطلوبة بين الشرائح الظاهرة
    const vi = Math.max(0, Math.min(visible.length - 1, idx));
    const [a0, a1] = spans[vi];
    const off = (a1 - a0) * (0.18 + Math.random() * 0.64);
    const want = -(a0 + off);
    let delta = (((want - s.rot) % TAU) + TAU) % TAU;
    delta += TAU * (s.phase === 'free' ? 3 : 4);
    s.from = s.rot;
    s.to = s.rot + delta;
    s.t0 = performance.now();
    const v0 = s.phase === 'free' ? s.v : 12;
    s.dur = Math.max(2600, Math.min(5200, ((3 * delta) / v0) * 1000));
    s.phase = 'ease';
    if (!s.raf) s.raf = requestAnimationFrame(frame);
  };

  // الرسم الأول وعند تغير الشرائح
  useEffect(() => {
    if (st.current.phase === 'idle') draw();
  }, [slices, size]);

  useEffect(() => {
    const s = st.current;
    if (spinning && s.phase === 'idle') {
      if (target !== null) {
        s.phase = 'free';
        s.v = 12;
        easeTo(target);
      } else {
        s.phase = 'free';
        s.v = 12;
        if (!s.raf) s.raf = requestAnimationFrame(frame);
      }
    } else if (spinning && s.phase === 'free' && target !== null) {
      easeTo(target);
    }
  }, [spinning, target]);

  useEffect(() => () => cancelAnimationFrame(st.current.raf), []);

  return (
    <div class="wheel" style={{ width: size, height: size }}>
      <canvas ref={cv} style={{ width: size, height: size }} />
      <div ref={pointer} class="wheel-pointer" />
    </div>
  );
}

/** يحسب رقم الشريحة الظاهرة اللي قيمتها v */
export function visibleIndex(slices: Slice[], v: number | string | undefined): number | null {
  if (v === undefined) return null;
  const vis = slices.filter((s) => s.w > 0);
  const i = vis.findIndex((s) => s.v === v);
  return i < 0 ? 0 : i;
}
