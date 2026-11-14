// التحكم في اللعب الأونلاين: صاحب الغرفة يشغل المحرك ويبث الحالة، والباقين يرسلون أوامر
// لو صاحب الغرفة طلع، أقدم لاعب متصل يصير هو صاحب الغرفة ويكمل اللعبة
import { Controller, HostController } from '../client/controller';
import { DEFAULT_SETTINGS, newState } from '../game/engine';
import type { CmdResult, Command, GameState, Settings } from '../game/types';
import type { World } from '../game/world';
import { pack, unpack, type NetMsg } from './protocol';
import type { Transport } from './transport';

const CODE_CHARS = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789';
export function genCode(): string {
  let s = '';
  for (let i = 0; i < 5; i++) s += CODE_CHARS[Math.floor(Math.random() * CODE_CHARS.length)];
  return s;
}

const SAVE_PREFIX = 'won-host-';

export class OnlineController extends Controller {
  private t: Transport;
  private role: 'host' | 'client' = 'client';
  host?: HostController;
  private remote: GameState;
  private ep = 0;
  private sn = 0;
  private peers: string[] = [];
  private pending = new Map<number, (r: CmdResult) => void>();
  private cseq = 0;
  private lastHostMsg = Date.now();
  private joinedAt = Date.now();
  private timers: ReturnType<typeof setInterval>[] = [];
  private packing = false;
  private packAgain = false;
  private lastCast = 0;
  private castTimer?: ReturnType<typeof setTimeout>;
  private offlineSince = new Map<string, number>();
  private lastSave = 0;
  name: string;
  ready = false;
  error?: string;

  private constructor(world: World, me: string, name: string, t: Transport, room: string) {
    super(world, me);
    this.name = name;
    this.t = t;
    this.roomCode = room;
    this.remote = newState('online', DEFAULT_SETTINGS, '');
    this.status = 'connecting';
  }

  static async create(world: World, me: string, name: string, settings: Settings, t: Transport): Promise<OnlineController> {
    const room = genCode();
    const c = new OnlineController(world, me, name, t, room);
    const st = newState('online', settings, me);
    st.epoch = 1;
    c.becomeHost(st, true);
    c.host!.engine.addPlayer(me, name);
    await c.connect();
    c.broadcast(true);
    return c;
  }

  static async join(world: World, me: string, name: string, room: string, t: Transport): Promise<OnlineController> {
    const c = new OnlineController(world, me, name, t, room.toUpperCase());
    await c.connect();
    c.hello();
    return c;
  }

  get state(): GameState {
    return this.role === 'host' && this.host ? this.host.state : this.remote;
  }

  isHost() {
    return this.role === 'host';
  }

  nowDay() {
    return this.role === 'host' && this.host ? this.host.nowDay() : super.nowDay();
  }

  private async connect() {
    this.t.onMessage = (m) => this.handle(m);
    this.t.onPeers = (ids) => this.onPeers(ids);
    this.t.onStatus = (s) => {
      this.status = s;
      if (s === 'ok' && this.role === 'client') this.hello();
      this.emit();
    };
    await this.t.join(this.roomCode!, { id: this.me, name: this.name });
    this.timers.push(setInterval(() => this.watchdog(), 1000));
  }

  private hello() {
    this.t.send({ t: 'hello', from: this.me, name: this.name });
  }

  private watchdog() {
    const now = Date.now();
    if (this.role === 'client') {
      if (!this.ready) {
        if (now - this.joinedAt > 2500 && (now - this.joinedAt) % 2000 < 1000) this.hello();
        // لو كنت أنا صاحب الغرفة وسويت تحديث للصفحة
        if (now - this.joinedAt > 5000) {
          const saved = this.loadSaved();
          if (saved) {
            this.becomeHost(saved, false);
            return;
          }
        }
        if (now - this.joinedAt > 15000 && !this.error) {
          this.error = 'ما لقينا الغرفة. تأكد من الكود أو إن صاحب الغرفة داخل.';
          this.emit();
        }
        return;
      }
      const s = this.remote;
      const hostHere = this.peers.includes(s.hostId);
      if (hostHere && now - this.lastHostMsg < 8000) return;
      if (now - this.lastHostMsg > 9000 && s.phase !== 'ended') {
        // نختار صاحب الغرفة الجديد: أقدم لاعب متصل
        const cands = Object.values(s.players)
          .filter((p) => p.id !== s.hostId && this.peers.includes(p.id))
          .sort((a, b) => a.joinedAt - b.joinedAt);
        if (cands[0]?.id === this.me) this.becomeHost(structuredClone(s), false);
      }
    } else if (this.host) {
      // تحديث دوري حتى لو ما تغير شي
      if (now - this.lastCast > 4000) this.broadcast(true);
      // اللاعبين اللي فصلوا
      for (const [id, since] of this.offlineSince) {
        if (now - since > 7000) {
          this.offlineSince.delete(id);
          const p = this.host.state.players[id];
          if (p && p.online && !this.peers.includes(id)) {
            this.host.engine.setOnline(id, false);
            if (this.host.state.phase === 'lobby') this.host.engine.removePlayer(id);
            else this.host.engine.news('📴', `${p.name} فصل، والبوت يلعب عنه لين يرجع`, 'system');
            this.host.dirty = true;
            this.host.flush(true);
          }
        }
      }
      if (now - this.lastSave > 5000) this.saveHost();
    }
  }

  private onPeers(ids: string[]) {
    this.peers = ids;
    if (this.role === 'host' && this.host) {
      const st = this.host.state;
      for (const p of Object.values(st.players)) {
        if (p.id === this.me) continue;
        const here = ids.includes(p.id);
        if (here) {
          this.offlineSince.delete(p.id);
          if (!p.online) {
            this.host.engine.setOnline(p.id, true);
            if (st.phase !== 'lobby') this.host.engine.news('🔌', `${p.name} رجع للعبة`, 'system');
            this.host.dirty = true;
            this.host.flush(true);
          }
        } else if (p.online && !this.offlineSince.has(p.id)) {
          this.offlineSince.set(p.id, Date.now());
        }
      }
    }
    this.emit();
  }

  private handle(m: NetMsg) {
    switch (m.t) {
      case 'hello': {
        if (this.role !== 'host' || !this.host) return;
        const st = this.host.state;
        const eng = this.host.engine;
        if (!st.players[m.from]) {
          // لو نفس الاسم لاعب فاصل، نرجعه لدولته
          const old = Object.values(st.players).find((p) => !p.online && p.name === m.name);
          if (old) {
            delete st.players[old.id];
            old.id = m.from;
            st.players[m.from] = old;
            eng.setOnline(m.from, true);
          } else {
            eng.addPlayer(m.from, m.name);
            if (st.phase === 'lobby') eng.news('👋', `${m.name} دخل الغرفة`, 'join');
          }
        } else {
          eng.setOnline(m.from, true);
        }
        this.offlineSince.delete(m.from);
        this.host.dirty = true;
        this.host.flush(true);
        this.broadcast(true);
        return;
      }
      case 'cmd': {
        if (this.role !== 'host' || !this.host) return;
        const r = this.host.apply(m.from, m.cmd);
        this.t.send({ t: 'ack', to: m.from, seq: m.seq, ok: r.ok, msg: r.msg });
        return;
      }
      case 'ack': {
        if (m.to !== this.me) return;
        const f = this.pending.get(m.seq);
        if (f) {
          this.pending.delete(m.seq);
          f({ ok: m.ok, msg: m.msg });
        }
        return;
      }
      case 'snap': {
        if (m.from === this.me) return;
        if (m.ep < this.ep || (m.ep === this.ep && m.sn <= this.sn)) return;
        this.ep = m.ep;
        this.sn = m.sn;
        this.lastHostMsg = Date.now();
        const myEp = m.ep;
        const mySn = m.sn;
        unpack<GameState>(m.z).then((st) => {
          if (myEp !== this.ep || mySn !== this.sn) return;
          if (this.role === 'host') this.demote();
          this.remote = st;
          if (!this.ready) {
            this.ready = true;
            this.error = undefined;
          }
          this.status = 'ok';
          this.emit();
        }).catch(() => {});
        return;
      }
      case 'bye': {
        if (this.role === 'host' && this.host) {
          const p = this.host.state.players[m.from];
          if (!p) return;
          this.offlineSince.set(m.from, Date.now() - 6000);
        }
        return;
      }
    }
  }

  private becomeHost(st: GameState, fresh: boolean) {
    const oldHost = st.hostId;
    if (!fresh) {
      st.epoch = Math.max(this.ep, st.epoch ?? 0) + 1;
    }
    st.hostId = this.me;
    this.ep = st.epoch ?? 1;
    this.sn = 0;
    this.role = 'host';
    this.ready = true;
    this.error = undefined;
    this.host = new HostController(this.world, this.me, st);
    this.host.onNews = (n) => this.onNews?.(n);
    this.host.subscribe(() => this.emit());
    this.host.afterEmit = (force) => this.broadcast(force);
    if (!fresh) {
      const eng = this.host.engine;
      if (st.players[this.me]) eng.setOnline(this.me, true);
      if (oldHost && oldHost !== this.me && st.players[oldHost]) eng.setOnline(oldHost, false);
      eng.news('👑', `${this.name} صار صاحب الغرفة`, 'system');
      if (st.countdown) st.countdown = Date.now() + 3000;
      this.host.dirty = true;
    }
    this.host.flush(true);
    this.emit();
  }

  private demote() {
    this.host?.leave();
    this.host = undefined;
    this.role = 'client';
  }

  /** بث الحالة للاعبين (مضغوطة) */
  broadcast(force = false) {
    if (this.role !== 'host' || !this.host) return;
    const now = Date.now();
    if (!force && now - this.lastCast < 700) {
      if (!this.castTimer) this.castTimer = setTimeout(() => { this.castTimer = undefined; this.broadcast(true); }, 700 - (now - this.lastCast));
      return;
    }
    if (this.packing) {
      this.packAgain = true;
      return;
    }
    this.packing = true;
    this.lastCast = now;
    const ep = this.ep;
    pack(this.host.state)
      .then((z) => {
        this.t.send({ t: 'snap', from: this.me, ep, sn: ++this.sn, z });
      })
      .finally(() => {
        this.packing = false;
        if (this.packAgain) {
          this.packAgain = false;
          setTimeout(() => this.broadcast(true), 120);
        }
      });
  }

  async send(cmd: Command): Promise<CmdResult> {
    if (this.role === 'host' && this.host) return this.host.apply(this.me, cmd);
    const seq = ++this.cseq;
    return new Promise((res) => {
      this.pending.set(seq, res);
      this.t.send({ t: 'cmd', from: this.me, seq, cmd });
      setTimeout(() => {
        if (this.pending.has(seq)) {
          this.pending.delete(seq);
          res({ ok: false, msg: 'ما وصل رد من صاحب الغرفة، حاول مرة ثانية' });
        }
      }, 7000);
    });
  }

  setSettings(p: Partial<Settings>) {
    this.host?.setSettings(p);
  }
  startWheels() {
    this.host?.startWheels();
  }
  forceStart() {
    this.host?.forceStart();
  }
  kick(id: string) {
    this.host?.kick(id);
  }

  private saveHost() {
    if (!this.host) return;
    this.lastSave = Date.now();
    try {
      localStorage.setItem(SAVE_PREFIX + this.roomCode, JSON.stringify({ at: Date.now(), state: this.host.state }));
    } catch {
      /* ignore */
    }
  }

  private loadSaved(): GameState | null {
    try {
      const raw = localStorage.getItem(SAVE_PREFIX + this.roomCode);
      if (!raw) return null;
      const { at, state } = JSON.parse(raw) as { at: number; state: GameState };
      if (Date.now() - at > 60 * 60 * 1000 || state.hostId !== this.me || state.phase === 'ended') return null;
      return state;
    } catch {
      return null;
    }
  }

  leave() {
    try {
      this.t.send({ t: 'bye', from: this.me });
      if (this.role === 'host') localStorage.removeItem(SAVE_PREFIX + this.roomCode);
    } catch {
      /* ignore */
    }
    this.timers.forEach(clearInterval);
    clearTimeout(this.castTimer);
    this.host?.leave();
    this.t.leave();
    this.listeners.clear();
  }
}
