// طبقة الاتصال: Supabase Realtime (أونلاين) أو BroadcastChannel (تجربة محلية بين التبويبات)
import { config } from '../config';
import type { NetMsg } from './protocol';

export type TStatus = 'ok' | 'connecting' | 'offline';

export interface Transport {
  onMessage: (m: NetMsg) => void;
  onPeers: (ids: string[]) => void;
  onStatus: (s: TStatus) => void;
  join(room: string, me: { id: string; name: string }): Promise<void>;
  send(m: NetMsg): void;
  leave(): void;
}

const noop = () => {};

/** للتجربة بين تبويبات نفس المتصفح بدون سيرفر */
export class LocalTransport implements Transport {
  onMessage: (m: NetMsg) => void = noop;
  onPeers: (ids: string[]) => void = noop;
  onStatus: (s: TStatus) => void = noop;
  private bc?: BroadcastChannel;
  private seen = new Map<string, number>();
  private hb?: ReturnType<typeof setInterval>;
  private me = '';
  private lastPeers = '';

  async join(room: string, me: { id: string; name: string }) {
    this.me = me.id;
    this.bc = new BroadcastChannel('won-room-' + room);
    this.bc.onmessage = (e) => {
      const m = e.data as NetMsg & { __ping?: string; __bye?: string };
      if (m.__ping) {
        this.seen.set(m.__ping, Date.now());
        this.sync();
        return;
      }
      if (m.__bye) {
        this.seen.delete(m.__bye);
        this.sync();
        return;
      }
      this.onMessage(m);
    };
    const beat = () => {
      this.bc?.postMessage({ __ping: me.id });
      this.seen.set(me.id, Date.now());
      this.sync();
    };
    beat();
    this.hb = setInterval(beat, 1000);
    this.onStatus('ok');
  }

  private sync() {
    const now = Date.now();
    const ids = [...this.seen].filter(([, t]) => now - t < 4000).map(([id]) => id).sort();
    const key = ids.join(',');
    if (key !== this.lastPeers) {
      this.lastPeers = key;
      this.onPeers(ids);
    }
  }

  send(m: NetMsg) {
    this.bc?.postMessage(m);
  }

  leave() {
    clearInterval(this.hb);
    try {
      this.bc?.postMessage({ __bye: this.me });
      this.bc?.close();
    } catch {
      /* ignore */
    }
  }
}

/** Supabase Realtime: بث + حضور (Presence) على قناة الغرفة */
export class SupabaseTransport implements Transport {
  onMessage: (m: NetMsg) => void = noop;
  onPeers: (ids: string[]) => void = noop;
  onStatus: (s: TStatus) => void = noop;
  private ch?: import('@supabase/supabase-js').RealtimeChannel;
  private client?: import('@supabase/supabase-js').SupabaseClient;
  private joined = false;

  async join(room: string, me: { id: string; name: string }) {
    this.onStatus('connecting');
    const { createClient } = await import('@supabase/supabase-js');
    const sb = createClient(config.supabaseUrl, config.supabaseKey, {
      auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
      realtime: { params: { eventsPerSecond: 40 }, heartbeatIntervalMs: 15000 },
    });
    this.client = sb;
    const ch = sb.channel(`won-${room}`, {
      config: { broadcast: { self: false, ack: false }, presence: { key: me.id } },
    });
    this.ch = ch;
    ch.on('broadcast', { event: 'm' }, ({ payload }) => this.onMessage(payload as NetMsg));
    ch.on('presence', { event: 'sync' }, () => this.onPeers(Object.keys(ch.presenceState()).sort()));
    await new Promise<void>((resolve) => {
      let done = false;
      ch.subscribe(async (status) => {
        if (status === 'SUBSCRIBED') {
          this.joined = true;
          this.onStatus('ok');
          try {
            await ch.track({ name: me.name, at: Date.now() });
          } catch {
            /* ignore */
          }
          if (!done) {
            done = true;
            resolve();
          }
        } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
          this.joined = false;
          this.onStatus('connecting');
        } else if (status === 'CLOSED') {
          this.joined = false;
          this.onStatus('offline');
        }
      });
      setTimeout(() => {
        if (!done) {
          done = true;
          resolve();
        }
      }, 12000);
    });
  }

  send(m: NetMsg) {
    // ما نرسل وقت الانقطاع (المكتبة تحول للـ REST وهذا يستهلك طلبات بدون فايدة)
    if (!this.joined) return;
    void this.ch?.send({ type: 'broadcast', event: 'm', payload: m });
  }

  leave() {
    this.joined = false;
    try {
      void this.ch?.unsubscribe();
      if (this.client) void this.client.removeAllChannels();
    } catch {
      /* ignore */
    }
  }
}
