// أصوات بسيطة مولدة بالكود (بدون ملفات)
let ctx: AudioContext | null = null;
let muted = false;
try {
  muted = localStorage.getItem('won-muted') === '1';
} catch {
  /* ignore */
}

function ac(): AudioContext | null {
  if (muted) return null;
  try {
    if (!ctx) ctx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
    if (ctx.state === 'suspended') void ctx.resume();
    return ctx;
  } catch {
    return null;
  }
}

export function isMuted() {
  return muted;
}

export function setMuted(m: boolean) {
  muted = m;
  try {
    localStorage.setItem('won-muted', m ? '1' : '0');
  } catch {
    /* ignore */
  }
}

function tone(freq: number, dur: number, type: OscillatorType = 'sine', vol = 0.15, when = 0, slide?: number) {
  const c = ac();
  if (!c) return;
  const t0 = c.currentTime + when;
  const o = c.createOscillator();
  const g = c.createGain();
  o.type = type;
  o.frequency.setValueAtTime(freq, t0);
  if (slide) o.frequency.exponentialRampToValueAtTime(slide, t0 + dur);
  g.gain.setValueAtTime(0.0001, t0);
  g.gain.exponentialRampToValueAtTime(vol, t0 + 0.01);
  g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
  o.connect(g).connect(c.destination);
  o.start(t0);
  o.stop(t0 + dur + 0.02);
}

function noise(dur: number, vol = 0.3, freq = 800, when = 0) {
  const c = ac();
  if (!c) return;
  const t0 = c.currentTime + when;
  const len = Math.floor(c.sampleRate * dur);
  const buf = c.createBuffer(1, len, c.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / len) ** 2;
  const src = c.createBufferSource();
  src.buffer = buf;
  const f = c.createBiquadFilter();
  f.type = 'lowpass';
  f.frequency.setValueAtTime(freq, t0);
  f.frequency.exponentialRampToValueAtTime(60, t0 + dur);
  const g = c.createGain();
  g.gain.setValueAtTime(vol, t0);
  src.connect(f).connect(g).connect(c.destination);
  src.start(t0);
}

export const sfx = {
  tick: () => tone(1400, 0.03, 'square', 0.04),
  click: () => tone(700, 0.05, 'triangle', 0.08),
  reveal: () => {
    tone(523, 0.12, 'triangle', 0.12);
    tone(659, 0.12, 'triangle', 0.12, 0.1);
    tone(784, 0.25, 'triangle', 0.14, 0.2);
  },
  good: () => {
    tone(660, 0.1, 'sine', 0.12);
    tone(990, 0.2, 'sine', 0.12, 0.08);
  },
  bad: () => {
    tone(300, 0.25, 'sawtooth', 0.08, 0, 150);
  },
  boom: () => {
    noise(0.7, 0.35, 900);
    tone(90, 0.5, 'sine', 0.25, 0, 40);
  },
  nuke: () => {
    noise(2.2, 0.5, 1500);
    tone(60, 2, 'sine', 0.3, 0, 25);
  },
  alert: () => {
    tone(880, 0.15, 'square', 0.07);
    tone(660, 0.2, 'square', 0.07, 0.17);
  },
  coin: () => {
    tone(988, 0.07, 'square', 0.05);
    tone(1319, 0.15, 'square', 0.05, 0.07);
  },
  notify: () => tone(880, 0.12, 'sine', 0.08),
  fanfare: () => {
    [523, 659, 784, 1047].forEach((f, i) => tone(f, 0.25, 'triangle', 0.13, i * 0.14));
    tone(1047, 0.8, 'triangle', 0.15, 0.6);
  },
};
