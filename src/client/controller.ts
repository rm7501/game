// وحدة التحكم: تربط الواجهة بالمحرك (محلياً) أو بالسيرفر (أونلاين)
import { MS_PER_DAY } from '../game/defs';
import { Engine } from '../game/engine';
import type { CmdResult, Command, GameState, Nation, NationId, News, Settings } from '../game/types';
import type { World } from '../game/world';

export type Listener = () => void;
export type NetStatus = 'ok' | 'connecting' | 'offline';

export abstract class Controller {
  readonly world: World;
  readonly me: string;
  status: NetStatus = 'ok';
  roomCode?: string;
  protected listeners = new Set<Listener>();
  protected stamp = performance.now();
  onNews?: (n: News) => void;

  constructor(world: World, me: string) {
    this.world = world;
    this.me = me;
  }

  abstract get state(): GameState;
  abstract send(cmd: Command): Promise<CmdResult>;
  abstract isHost(): boolean;
  abstract leave(): void;

  subscribe(fn: Listener): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  protected emit() {
    this.stamp = performance.now();
    for (const l of [...this.listeners]) l();
  }

  myNationId(): NationId | undefined {
    return this.state.players[this.me]?.nation;
  }

  myNation(): Nation | undefined {
    const id = this.myNationId();
    return id ? this.state.nations[id] : undefined;
  }

  /** اليوم الحالي بكسوره (لتحريك الجيوش بنعومة) */
  nowDay(): number {
    const s = this.state;
    if (s.phase !== 'playing' || s.paused) return s.day;
    const el = performance.now() - this.stamp;
    return s.day + Math.min(2, el / (MS_PER_DAY / s.speed));
  }

  // عمليات صاحب الغرفة
  setSettings(_p: Partial<Settings>) {}
  startWheels() {}
  forceStart() {}
  kick(_id: string) {}
}

/** مؤقت يشتغل حتى لو التبويب بالخلفية (عن طريق Worker) */
export function makeTicker(fn: () => void, ms: number): { stop(): void } {
  try {
    const code = `let t=setInterval(()=>postMessage(0),${ms});onmessage=()=>clearInterval(t);`;
    const url = URL.createObjectURL(new Blob([code], { type: 'text/javascript' }));
    const w = new Worker(url);
    w.onmessage = () => fn();
    return {
      stop() {
        w.terminate();
        URL.revokeObjectURL(url);
      },
    };
  } catch {
    const t = setInterval(fn, ms);
    return { stop: () => clearInterval(t) };
  }
}

const SAVE_KEY = 'won-save-v1';

export function loadSave(): GameState | null {
  try {
    const raw = localStorage.getItem(SAVE_KEY);
    if (!raw) return null;
    const s = JSON.parse(raw) as GameState;
    if (s.v !== 2 || s.mode !== 'single' || s.phase === 'ended') return null;
    return s;
  } catch {
    return null;
  }
}

export function clearSave() {
  try {
    localStorage.removeItem(SAVE_KEY);
  } catch {
    /* ignore */
  }
}

/** صاحب اللعبة: يشغل المحرك (لعب فردي أو صاحب غرفة أونلاين) */
export class HostController extends Controller {
  engine: Engine;
  private ticker?: { stop(): void };
  private last = performance.now();
  private lastEmit = 0;
  private lastSave = 0;
  dirty = true;
  /** يُستدعى بعد كل تحديث (للبث للاعبين) */
  afterEmit?: (force: boolean) => void;
  private onHide = () => {
    if (document.hidden && this.state.mode === 'single') {
      if (this.state.phase === 'playing' && !this.state.paused) {
        this.state.paused = true;
        this.dirty = true;
      }
      this.save(true);
    }
  };

  constructor(world: World, me: string, state: GameState) {
    super(world, me);
    this.engine = new Engine(world, state);
    this.engine.onNews = (n) => this.onNews?.(n);
    this.ticker = makeTicker(() => this.loop(), 50);
    document.addEventListener('visibilitychange', this.onHide);
    window.addEventListener('beforeunload', this.onHide);
  }

  get state() {
    return this.engine.s;
  }

  isHost() {
    return true;
  }

  async send(cmd: Command): Promise<CmdResult> {
    return this.apply(this.me, cmd);
  }

  apply(clientId: string, cmd: Command): CmdResult {
    const p = this.state.players[clientId];
    if (!p) return { ok: false, msg: 'لاعب غير معروف' };
    const r = this.engine.command(p.nation, cmd, clientId === this.state.hostId);
    this.dirty = true;
    this.flush(true);
    return r;
  }

  setSettings(p: Partial<Settings>) {
    const s = this.state;
    if (s.phase !== 'lobby') return;
    Object.assign(s.settings, p);
    s.speed = s.settings.speed;
    this.dirty = true;
    this.flush(true);
  }

  startWheels() {
    if (this.state.phase !== 'lobby') return;
    this.engine.startWheels();
    this.dirty = true;
    this.flush(true);
  }

  /** يبدأ اللعبة حتى لو فيه أحد ما خلص عجلاته */
  forceStart() {
    const s = this.state;
    if (s.phase !== 'wheels') return;
    this.engine.readyAll();
    if (!s.countdown) s.countdown = Date.now() + 3000;
    this.dirty = true;
    this.flush(true);
  }

  kick(id: string) {
    if (id === this.me) return;
    if (this.state.phase === 'lobby') delete this.state.players[id];
    this.dirty = true;
    this.flush(true);
  }

  flush(force = false) {
    const now = performance.now();
    if (!this.dirty) return;
    if (!force && now - this.lastEmit < 110) return;
    this.dirty = false;
    this.lastEmit = now;
    this.emit();
    this.afterEmit?.(force);
  }

  private loop() {
    const now = performance.now();
    const dt = Math.min(1000, now - this.last);
    this.last = now;
    const s = this.state;
    if (s.phase === 'wheels') {
      if (!s.countdown && this.engine.allWheelsDone()) {
        s.countdown = Date.now() + 4000;
        this.dirty = true;
      } else if (s.countdown && Date.now() >= s.countdown) {
        s.countdown = undefined;
        this.engine.finishWheels();
        this.dirty = true;
      }
    }
    // وقت الأحداث العالمية نوقف اللعبة ثواني عشان الكل يشوف العجلة
    const hold = !!s.holdUntil && Date.now() < s.holdUntil;
    if (s.holdUntil && !hold) {
      s.holdUntil = undefined;
      this.dirty = true;
    }
    if (s.phase === 'playing' && !s.paused && !hold) {
      const before = s.day;
      this.engine.advance((dt / MS_PER_DAY) * s.speed);
      if (s.day !== before) this.dirty = true;
    }
    this.flush();
    if (s.mode === 'single' && now - this.lastSave > 15000) this.save();
  }

  save(force = false) {
    if (this.state.mode !== 'single') return;
    const now = performance.now();
    if (!force && now - this.lastSave < 5000) return;
    this.lastSave = now;
    try {
      if (this.state.phase === 'ended') clearSave();
      else if (this.state.phase === 'playing') localStorage.setItem(SAVE_KEY, JSON.stringify(this.state));
    } catch {
      /* التخزين ممكن يكون مقفل */
    }
  }

  leave() {
    this.save(true);
    this.ticker?.stop();
    document.removeEventListener('visibilitychange', this.onHide);
    window.removeEventListener('beforeunload', this.onHide);
    this.listeners.clear();
  }
}
