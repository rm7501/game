// الشاشات: القائمة الرئيسية، الإعدادات، الانضمام، اللوبي
import { useEffect, useRef, useState } from 'preact/hooks';
import type { Controller } from '../client/controller';
import { onlineReady } from '../config';
import { DEFAULT_SETTINGS } from '../game/engine';
import type { Difficulty, NeutralStrength, Settings, WinMode } from '../game/types';
import type { World } from '../game/world';
import { sfx } from './audio';
import { Flag } from './bits';
import { HowTo } from './HowTo';
import { MapRenderer } from './map';
import { toast } from './toast';

export function getName(): string {
  try {
    return localStorage.getItem('won-name') ?? '';
  } catch {
    return '';
  }
}
export function saveName(n: string) {
  try {
    localStorage.setItem('won-name', n);
  } catch {
    /* ignore */
  }
}

function BgMap({ world }: { world: World }) {
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!box.current) return;
    const m = new MapRenderer(box.current, world, { interactive: false, minimal: true });
    const ids = world.list.map((x) => x.id);
    const colors = ['#e6194b', '#3cb44b', '#4363d8', '#f58231', '#911eb4', '#42d4f4', '#f032e6', '#ffe119'];
    const fake = { terr: {} as Record<string, { owner: string; unrest: number; nuked: number }>, nations: {} as Record<string, { color: string; alive: boolean; capital: string; name: string; d: { terrs: number } }>, moves: [] };
    for (const id of ids) fake.terr[id] = { owner: '', unrest: 0, nuked: 0 };
    colors.forEach((c, i) => (fake.nations['X' + i] = { color: c, alive: false, capital: '', name: '', d: { terrs: 0 } }));
    const t = setInterval(() => {
      const id = ids[Math.floor(Math.random() * ids.length)];
      fake.terr[id].owner = Math.random() < 0.3 ? '' : 'X' + Math.floor(Math.random() * colors.length);
      m.update(fake as never);
    }, 260);
    return () => {
      clearInterval(t);
      m.destroy();
    };
  }, []);
  return <div class="bg-map" ref={box} />;
}

export function Menu({
  world, onSingle, onCreate, onJoin, onLocal, onContinue, hasSave,
}: {
  world: World;
  onSingle: () => void;
  onCreate: (name: string) => void;
  onJoin: (name: string, code: string) => void;
  onLocal: (name: string, code?: string) => void;
  onContinue?: () => void;
  hasSave: boolean;
}) {
  const [name, setName] = useState(getName());
  const [code, setCode] = useState(new URLSearchParams(location.search).get('room') ?? '');
  const [howto, setHowto] = useState(false);
  const [joinOpen, setJoinOpen] = useState(!!code);
  const ready = onlineReady();
  const needName = () => {
    if (!name.trim()) {
      toast({ icon: '✍️', text: 'اكتب اسمك أول', kind: 'warn' });
      return true;
    }
    saveName(name.trim());
    return false;
  };
  return (
    <div class="screen menu-screen">
      <BgMap world={world} />
      <div class="menu-card">
        <div class="logo">🎡</div>
        <h1 class="title">عجلة الأمم</h1>
        <p class="subtitle">لف العجلة، ابنِ دولتك، واحكم العالم</p>
        <label class="field">
          <span>اسمك</span>
          <input value={name} maxLength={20} placeholder="مثلاً: أبو فهد" onInput={(e) => setName((e.target as HTMLInputElement).value)} />
        </label>
        {hasSave && onContinue && (
          <button class="btn btn-gold btn-big" onClick={() => { sfx.click(); onContinue(); }}>
            ▶️ كمّل لعبتك المحفوظة
          </button>
        )}
        <button class={`btn btn-big ${hasSave ? '' : 'btn-gold'}`} onClick={() => { sfx.click(); if (!needName()) onSingle(); }}>
          🎮 لعب فردي ضد البوتات
        </button>
        <div class="menu-row">
          <button class="btn btn-primary" onClick={() => { sfx.click(); if (needName()) return; ready ? onCreate(name.trim()) : onLocal(name.trim()); }}>
            🌐 إنشاء غرفة
          </button>
          <button class="btn btn-primary" onClick={() => { sfx.click(); setJoinOpen(!joinOpen); }}>
            🔗 دخول غرفة
          </button>
        </div>
        {joinOpen && (
          <div class="join-row">
            <input class="code-input" value={code} maxLength={5} placeholder="الكود" onInput={(e) => setCode((e.target as HTMLInputElement).value.toUpperCase())} />
            <button class="btn btn-gold" onClick={() => {
              if (needName()) return;
              if (code.trim().length < 4) return toast({ icon: '🔢', text: 'اكتب كود الغرفة', kind: 'warn' });
              ready ? onJoin(name.trim(), code.trim()) : onLocal(name.trim(), code.trim());
            }}>دخول</button>
          </div>
        )}
        {!ready && (
          <div class="hint small">
            ⚙️ سيرفر الأونلاين ما تجهز بعد (شوف ملف README). الحين الغرف تشتغل بين تبويبات نفس المتصفح بس للتجربة.
          </div>
        )}
        <button class="btn btn-ghost btn-sm" onClick={() => setHowto(true)}>📖 طريقة اللعب</button>
      </div>
      {howto && <HowTo onClose={() => setHowto(false)} />}
    </div>
  );
}

const WIN_OPTS: { v: WinMode; label: string; desc: string }[] = [
  { v: 'score', label: '🏆 أعلى نقاط', desc: 'بعد مدة محددة' },
  { v: 'percent', label: '🗺️ نسبة من العالم', desc: 'أول من يوصلها' },
  { v: 'domination', label: '👑 السيطرة على العالم', desc: 'آخر من يبقى' },
];

export function SettingsForm({ value, onChange, readOnly, single }: { value: Settings; onChange: (p: Partial<Settings>) => void; readOnly?: boolean; single?: boolean }) {
  const v = value;
  const opt = <T,>(cur: T, items: { v: T; label: string }[], key: keyof Settings) => (
    <div class="seg">
      {items.map((it) => (
        <button key={String(it.v)} class={`seg-btn ${cur === it.v ? 'on' : ''}`} disabled={readOnly} onClick={() => onChange({ [key]: it.v } as Partial<Settings>)}>
          {it.label}
        </button>
      ))}
    </div>
  );
  return (
    <div class="settings">
      <div class="set-row">
        <span class="set-label">🤖 عدد البوتات</span>
        <div class="set-ctl">
          <input type="range" min={single ? 1 : 0} max={30} value={v.bots} disabled={readOnly} onInput={(e) => onChange({ bots: Number((e.target as HTMLInputElement).value) })} />
          <b class="set-val">{v.bots}</b>
        </div>
      </div>
      <div class="set-row">
        <span class="set-label">🧠 صعوبة البوتات</span>
        {opt<Difficulty>(v.difficulty, [{ v: 'easy', label: 'سهل' }, { v: 'normal', label: 'متوسط' }, { v: 'hard', label: 'صعب' }], 'difficulty')}
      </div>
      <div class="set-row col">
        <span class="set-label">🏁 شرط الفوز</span>
        <div class="win-opts">
          {WIN_OPTS.map((w) => (
            <button key={w.v} class={`win-opt ${v.win === w.v ? 'on' : ''}`} disabled={readOnly} onClick={() => onChange({ win: w.v })}>
              <b>{w.label}</b>
              <span class="muted small">{w.desc}</span>
            </button>
          ))}
        </div>
        {v.win === 'score' && (
          <div class="seg">
            {[10, 15, 25, 40, 60].map((y) => (
              <button key={y} class={`seg-btn ${v.years === y ? 'on' : ''}`} disabled={readOnly} onClick={() => onChange({ years: y })}>
                {y} سنة <small class="muted">≈{Math.round((y * 72) / 60)}د</small>
              </button>
            ))}
          </div>
        )}
        {v.win === 'percent' && (
          <div class="seg">
            {[25, 35, 50, 65].map((p) => (
              <button key={p} class={`seg-btn ${v.percent === p ? 'on' : ''}`} disabled={readOnly} onClick={() => onChange({ percent: p })}>
                {p}%
              </button>
            ))}
          </div>
        )}
      </div>
      <div class="set-row">
        <span class="set-label">🏳️ قوة الدول المحايدة</span>
        {opt<NeutralStrength>(v.neutral, [{ v: 'weak', label: 'ضعيفة' }, { v: 'normal', label: 'عادية' }, { v: 'strong', label: 'قوية' }], 'neutral')}
      </div>
      <div class="set-row">
        <span class="set-label">🕊️ فترة السلام بالبداية</span>
        {opt<number>(v.peaceMonths, [{ v: 0, label: 'بدون' }, { v: 6, label: '6 شهور' }, { v: 12, label: 'سنة' }, { v: 24, label: 'سنتين' }], 'peaceMonths')}
      </div>
    </div>
  );
}

export function SingleSetup({ onStart, onBack }: { onStart: (s: Settings) => void; onBack: () => void }) {
  const [st, setSt] = useState<Settings>(() => {
    try {
      const raw = localStorage.getItem('won-sp-settings');
      if (raw) return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
    } catch {
      /* ignore */
    }
    return { ...DEFAULT_SETTINGS };
  });
  return (
    <div class="screen center">
      <div class="card setup-card">
        <div class="card-title big">🎮 لعب فردي</div>
        <SettingsForm value={st} single onChange={(p) => setSt({ ...st, ...p })} />
        <div class="modal-foot">
          <button class="btn" onClick={onBack}>رجوع</button>
          <button class="btn btn-gold btn-big" onClick={() => {
            try { localStorage.setItem('won-sp-settings', JSON.stringify(st)); } catch { /* ignore */ }
            sfx.click();
            onStart(st);
          }}>🎡 ابدأ ولف العجلات</button>
        </div>
      </div>
    </div>
  );
}

export function Lobby({ ctl, onLeave }: { ctl: Controller; onLeave: () => void }) {
  const s = ctl.state;
  const host = ctl.isHost();
  const players = Object.values(s.players).sort((a, b) => a.joinedAt - b.joinedAt);
  const link = `${location.origin}${location.pathname}?room=${ctl.roomCode}`;
  const [msg, setMsg] = useState('');
  const chatBox = useRef<HTMLDivElement>(null);
  useEffect(() => chatBox.current?.scrollTo({ top: chatBox.current.scrollHeight }), [s.chat.length]);
  const share = async () => {
    try {
      if (navigator.share) await navigator.share({ title: 'عجلة الأمم', text: `تعال العب معي! كود الغرفة: ${ctl.roomCode}`, url: link });
      else {
        await navigator.clipboard.writeText(link);
        toast({ icon: '🔗', text: 'نسخت الرابط، أرسله لأصحابك', kind: 'good' });
      }
    } catch {
      /* ignore */
    }
  };
  const sendMsg = () => {
    if (!msg.trim()) return;
    ctl.send({ t: 'chat', text: msg });
    setMsg('');
  };
  return (
    <div class="screen lobby">
      <div class="lobby-grid">
        <div class="card">
          <div class="card-title big">🌐 غرفة اللعب</div>
          <div class="room-code" onClick={share} title="اضغط للمشاركة">
            <span class="muted small">كود الغرفة</span>
            <b>{ctl.roomCode}</b>
          </div>
          <div class={`conn ${ctl.status}`}>
            {!onlineReady()
              ? '🧪 وضع تجربة محلي (بين تبويبات نفس المتصفح)'
              : ctl.status === 'ok'
                ? '🟢 متصل بالسيرفر'
                : ctl.status === 'connecting'
                  ? '🔄 يتصل بالسيرفر... (لو طوّل: ممكن مشروع Supabase متوقف، شغّله من لوحة Supabase)'
                  : '📴 انقطع الاتصال بالسيرفر'}
          </div>
          <div class="menu-row">
            <button class="btn btn-primary" onClick={share}>📤 شارك الرابط</button>
            <button class="btn" onClick={() => { navigator.clipboard?.writeText(ctl.roomCode ?? ''); toast({ icon: '📋', text: 'نسخت الكود', kind: 'good' }); }}>📋 نسخ الكود</button>
          </div>
          <div class="card-title">اللاعبين ({players.length})</div>
          <ul class="plist big">
            {players.map((p) => (
              <li key={p.id}>
                <span class={`online-dot ${p.online ? 'on' : ''}`} />
                <span class="pname">{p.name}{p.id === ctl.me && ' (أنت)'}</span>
                {p.id === s.hostId && <span title="صاحب الغرفة">👑</span>}
                {host && p.id !== ctl.me && <button class="icon-btn" title="طرد" onClick={() => ctl.kick(p.id)}>✕</button>}
              </li>
            ))}
            {s.settings.bots > 0 && (
              <li class="muted">
                <span>🤖</span> + {s.settings.bots} بوت
              </li>
            )}
          </ul>
          <div class="lobby-chat">
            <div class="chat-msgs small" ref={chatBox}>
              {s.chat.map((c) => (
                <div key={c.id} class="msg"><b>{c.name}:</b> {c.text}</div>
              ))}
            </div>
            <div class="chat-input">
              <input value={msg} placeholder="اكتب رسالة..." maxLength={300} onInput={(e) => setMsg((e.target as HTMLInputElement).value)} onKeyDown={(e) => e.key === 'Enter' && sendMsg()} />
              <button class="btn btn-sm" onClick={sendMsg}>إرسال</button>
            </div>
          </div>
        </div>
        <div class="card">
          <div class="card-title big">⚙️ الإعدادات {!host && <span class="muted small">(صاحب الغرفة يحددها)</span>}</div>
          <SettingsForm value={s.settings} readOnly={!host} onChange={(p) => ctl.setSettings(p)} />
          <div class="modal-foot">
            <button class="btn" onClick={onLeave}>🚪 خروج</button>
            {host ? (
              <button class="btn btn-gold btn-big" onClick={() => { sfx.click(); ctl.startWheels(); }}>🎡 ابدأ اللعبة</button>
            ) : (
              <div class="muted">⏳ بانتظار صاحب الغرفة يبدأ...</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export function Connecting({ ctl, onBack }: { ctl: Controller & { error?: string }; onBack: () => void }) {
  return (
    <div class="screen center">
      <div class="card center">
        {ctl.error ? (
          <>
            <div class="big-emoji">😕</div>
            <p>{ctl.error}</p>
          </>
        ) : (
          <>
            <div class="spinner" />
            <p>جاري الدخول للغرفة {ctl.roomCode}...</p>
          </>
        )}
        <button class="btn" onClick={onBack}>رجوع</button>
      </div>
    </div>
  );
}

export { Flag };
