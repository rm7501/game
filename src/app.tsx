// التطبيق: يتنقل بين الشاشات حسب حالة اللعبة
import { useEffect, useRef, useState } from 'preact/hooks';
import { clearSave, HostController, loadSave, type Controller } from './client/controller';
import { onlineReady } from './config';
import { DEFAULT_SETTINGS, newState } from './game/engine';
import type { Settings } from './game/types';
import { World, type WorldData } from './game/world';
import { OnlineController } from './net/online';
import { LocalTransport, SupabaseTransport } from './net/transport';
import { GameScreen } from './ui/GameScreen';
import { Connecting, getName, Lobby, Menu, SingleSetup } from './ui/screens';
import { toast, Toasts } from './ui/toast';
import { WheelsScreen } from './ui/WheelsScreen';

type Screen = { t: 'loading' } | { t: 'busy'; msg: string } | { t: 'error'; msg: string } | { t: 'menu' } | { t: 'setup'; dev?: boolean } | { t: 'ctl'; ctl: Controller };

function clientId(): string {
  try {
    let id = sessionStorage.getItem('won-cid');
    if (!id) {
      id = 'c' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4);
      sessionStorage.setItem('won-cid', id);
    }
    return id;
  } catch {
    return 'c' + Math.random().toString(36).slice(2, 10);
  }
}

function setRoomInUrl(code?: string) {
  const u = new URL(location.href);
  if (code) u.searchParams.set('room', code);
  else u.searchParams.delete('room');
  history.replaceState(null, '', u.toString());
}

export function App() {
  const [world, setWorld] = useState<World | null>(null);
  const [screen, setScreen] = useState<Screen>({ t: 'loading' });
  const [, force] = useState(0);
  const [hasSave, setHasSave] = useState(() => !!loadSave());

  useEffect(() => {
    fetch('./data/world.json')
      .then((r) => r.json())
      .then((d: WorldData) => {
        setWorld(new World(d));
        setScreen({ t: 'menu' });
        // رابط غرفة + اسم محفوظ = ندخل مباشرة (مثلاً بعد تحديث الصفحة)
        const code = new URLSearchParams(location.search).get('room');
        const name = getName();
        if (code && name) autoJoin.current = { code, name };
      })
      .catch(() => setScreen({ t: 'error', msg: 'ما قدرنا نحمّل خريطة العالم. تأكد من الاتصال وحدّث الصفحة.' }));
  }, []);

  const autoJoin = useRef<{ code: string; name: string } | null>(null);
  useEffect(() => {
    if (world && autoJoin.current) {
      const { code, name } = autoJoin.current;
      autoJoin.current = null;
      void goOnline(name, code, !onlineReady());
    }
  }, [world]);

  useEffect(() => {
    if (screen.t !== 'ctl') return;
    if (import.meta.env.DEV) (window as unknown as { __ctl?: Controller }).__ctl = screen.ctl;
    let raf = 0;
    const unsub = screen.ctl.subscribe(() => {
      if (!raf) raf = requestAnimationFrame(() => {
        raf = 0;
        force((x) => x + 1);
      });
    });
    return () => {
      unsub();
      cancelAnimationFrame(raf);
    };
  }, [screen]);

  if (screen.t === 'busy') {
    return (
      <div class="screen center">
        <div class="card center">
          <div class="spinner" />
          <p>{screen.msg}</p>
        </div>
      </div>
    );
  }

  if (screen.t === 'loading' || !world) {
    return (
      <div class="screen center">
        {screen.t === 'error' ? <div class="card">{screen.msg}</div> : <div class="spinner" />}
      </div>
    );
  }

  const exit = () => {
    if (screen.t === 'ctl') screen.ctl.leave();
    setRoomInUrl();
    setHasSave(!!loadSave());
    setScreen({ t: 'menu' });
  };

  const startSingle = (settings: Settings, gm = false) => {
    clearSave();
    const me = clientId();
    const st = newState('single', settings, me);
    const ctl = new HostController(world, me, st);
    ctl.engine.addPlayer(me, getName() || 'أنت');
    if (gm && st.dev) st.players[me].gm = true; // المتحكم يدير بس ويتفرج على البوتات
    ctl.startWheels();
    setScreen({ t: 'ctl', ctl });
  };

  const continueSingle = () => {
    const st = loadSave();
    if (!st) return;
    const me = Object.keys(st.players)[0];
    st.paused = true;
    const ctl = new HostController(world, me, st);
    setScreen({ t: 'ctl', ctl });
  };

  async function goOnline(name: string, code: string | undefined, local: boolean, dev = false) {
    if (!world) return;
    const me = clientId();
    const tr = local ? new LocalTransport() : new SupabaseTransport();
    setScreen({ t: 'busy', msg: code ? `جاري الدخول للغرفة ${code.toUpperCase()}...` : 'جاري تجهيز الغرفة...' });
    try {
      let saved: Partial<Settings> = {};
      try {
        saved = JSON.parse(localStorage.getItem('won-sp-settings') ?? '{}') as Partial<Settings>;
      } catch {
        /* ignore */
      }
      const ctl = code
        ? await OnlineController.join(world, me, name, code, tr)
        : await OnlineController.create(world, me, name, { ...DEFAULT_SETTINGS, ...saved, bots: Math.min(saved.bots ?? 4, 8), dev }, tr);
      setRoomInUrl(ctl.roomCode);
      setScreen({ t: 'ctl', ctl });
    } catch (e) {
      console.error(e);
      toast({ icon: '⚠️', text: 'صار خطأ بالاتصال بالسيرفر', kind: 'bad' });
      setScreen({ t: 'menu' });
    }
  }

  let body;
  if (screen.t === 'menu') {
    body = (
      <Menu
        world={world}
        hasSave={hasSave}
        onContinue={continueSingle}
        onSingle={() => setScreen({ t: 'setup' })}
        onSingleDev={() => setScreen({ t: 'setup', dev: true })}
        onCreate={(name, dev) => goOnline(name, undefined, false, dev)}
        onJoin={(name, code) => goOnline(name, code, false)}
        onLocal={(name, code, dev) => goOnline(name, code, true, dev)}
      />
    );
  } else if (screen.t === 'setup') {
    body = <SingleSetup dev={screen.dev} onStart={startSingle} onBack={() => setScreen({ t: 'menu' })} />;
  } else if (screen.t === 'ctl') {
    const ctl = screen.ctl;
    const s = ctl.state;
    const nid = ctl.myNationId();
    if (ctl instanceof OnlineController && !ctl.ready) body = <Connecting ctl={ctl} onBack={exit} />;
    else if (s.phase === 'lobby') body = <Lobby ctl={ctl} onLeave={exit} />;
    else if (s.phase === 'wheels' || (nid && s.wheels[nid] && !s.nations[nid])) body = <WheelsScreen ctl={ctl} />;
    else body = <GameScreen ctl={ctl} onExit={exit} />;
  }
  return (
    <>
      {body}
      <Toasts />
      {!onlineReady() && screen.t === 'ctl' && screen.ctl.state.mode === 'online' && <div class="local-badge">🧪 وضع تجربة محلي</div>}
    </>
  );
}
