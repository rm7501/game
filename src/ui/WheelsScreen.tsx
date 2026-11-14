// شاشة عجلات الحظ: كل لاعب يلف عجلاته ويبني دولته
import { useEffect, useRef, useState } from 'preact/hooks';
import type { Controller } from '../client/controller';
import { WHEELS, type Slice } from '../game/defs';
import { Engine } from '../game/engine';
import { WHEEL_ORDER, type TerrId, type WheelId } from '../game/types';
import { sfx } from './audio';
import { Flag } from './bits';
import { CountryRoulette } from './CountryRoulette';
import { describe } from './describe';
import { toast } from './toast';
import { WheelCanvas, visibleIndex } from './WheelCanvas';

function useNow(active: boolean) {
  const [, set] = useState(0);
  useEffect(() => {
    if (!active) return;
    const t = setInterval(() => set((x) => x + 1), 250);
    return () => clearInterval(t);
  }, [active]);
}

export function WheelsScreen({ ctl }: { ctl: Controller }) {
  const s = ctl.state;
  const world = ctl.world;
  const nid = ctl.myNationId() ?? '';
  const ws = s.wheels[nid];
  const next = ws ? WHEEL_ORDER.find((w) => ws.res[w] === undefined) ?? null : null;
  const [active, setActive] = useState<WheelId | null>(null);
  const [frozen, setFrozen] = useState<Slice[] | null>(null);
  const [cands, setCands] = useState<TerrId[]>([]);
  const [spinning, setSpinning] = useState(false);
  const [target, setTarget] = useState<number | string | null>(null);
  const [reveal, setReveal] = useState<WheelId | null>(null);
  const nonceRef = useRef(ws?.last?.nonce ?? 0);
  const [size, setSize] = useState(() => Math.min(380, Math.max(240, Math.min(window.innerWidth - 40, window.innerHeight - 330))));
  useNow(!!s.countdown);

  useEffect(() => {
    const f = () => setSize(Math.min(380, Math.max(240, Math.min(window.innerWidth - 40, window.innerHeight - 330))));
    window.addEventListener('resize', f);
    return () => window.removeEventListener('resize', f);
  }, []);

  // نراقب وصول النتيجة من المحرك
  useEffect(() => {
    if (!ws || !active) return;
    const n = ws.last?.nonce ?? 0;
    if (n > nonceRef.current && ws.last?.wheel === active && ws.res[active] !== undefined) {
      nonceRef.current = n;
      setTarget(ws.res[active] as number | string);
    }
  });

  // لو صار تلقائي (اللف السريع) نحدث الرقم بدون أنيميشن
  useEffect(() => {
    if (!active && ws?.last) nonceRef.current = Math.max(nonceRef.current, ws.last.nonce);
  });

  if (!ws) {
    return (
      <div class="screen center">
        <div class="card">⏳ جاري التحميل...</div>
      </div>
    );
  }

  const eng = new Engine(world, s);
  const startSpin = (wheel: WheelId, respin = false) => {
    if (spinning || active) return;
    sfx.click();
    setReveal(null);
    setTarget(null);
    if (wheel === 'country') {
      const c = eng.countryCandidates(nid);
      const cur = ws.res.country as string | undefined;
      setCands(respin && cur ? [...c, cur] : c);
      setFrozen(null);
    } else {
      setFrozen(eng.slicesFor(nid, wheel));
    }
    setActive(wheel);
    setSpinning(true);
    ctl.send(respin ? { t: 'respin', wheel } : { t: 'spin', wheel }).then((r) => {
      if (!r.ok) {
        toast({ icon: '⚠️', text: r.msg ?? 'ما قدرنا نلف العجلة', kind: 'bad' });
        setSpinning(false);
        setActive(null);
      }
    });
  };

  const onStop = () => {
    const w = active!;
    setSpinning(false);
    setActive(null);
    setTarget(null);
    setReveal(w);
    const v = ws.res[w];
    if (v !== undefined) {
      const info = describe(w, v, world);
      if (info.tone === 'bad') sfx.bad();
      else if (info.tone === 'good') sfx.fanfare();
      else sfx.reveal();
    }
  };

  const shown: WheelId = active ?? reveal ?? next ?? 'luck';
  const slices = frozen ?? (shown === 'country' ? [] : eng.slicesFor(nid, shown));
  const revealInfo = reveal && ws.res[reveal] !== undefined ? describe(reveal, ws.res[reveal]!, world) : null;
  const doneCount = WHEEL_ORDER.filter((w) => ws.res[w] !== undefined).length;
  const others = Object.entries(s.wheels).filter(([id]) => id !== nid);
  const countdown = s.countdown ? Math.max(0, Math.ceil((s.countdown - Date.now()) / 1000)) : null;
  const playerName = (id: string) => Object.values(s.players).find((p) => p.nation === id)?.name;

  return (
    <div class="screen wheels-screen">
      <header class="wheels-head">
        <div class="wheels-title">
          <span class="logo-mini">🎡</span> عجلات الحظ <span class="muted">· جهّز دولتك</span>
        </div>
        <div class="wheel-dots">
          {WHEEL_ORDER.map((w) => (
            <span
              key={w}
              class={`wdot ${ws.res[w] !== undefined ? 'done' : ''} ${w === shown ? 'cur' : ''}`}
              title={WHEELS[w].title}
            >
              {WHEELS[w].icon}
            </span>
          ))}
        </div>
      </header>

      <div class="wheels-body">
        <section class="wheel-stage">
          <h2 class="wheel-name">
            {WHEELS[shown].icon} {WHEELS[shown].title}
          </h2>
          <p class="muted wheel-hint">{WHEELS[shown].hint}</p>
          <div class="wheel-box" style={{ minHeight: shown === 'country' ? undefined : size }}>
            {shown === 'country' ? (
              <CountryRoulette
                world={world}
                candidates={active === 'country' ? cands : eng.countryCandidates(nid)}
                result={active === 'country' ? (target as string | null) : null}
                spinning={spinning && active === 'country'}
                onStop={onStop}
                focus={active ? null : (ws.res.country as string | undefined) ?? null}
              />
            ) : (
              <WheelCanvas
                key={shown}
                slices={slices}
                target={target !== null ? visibleIndex(slices, target) : null}
                spinning={spinning}
                onStop={onStop}
                size={size}
                hub={WHEELS[shown].icon}
              />
            )}
            {revealInfo && !spinning && (
              <div class={`reveal ${revealInfo.tone ?? ''}`}>
                <div class="reveal-icon">{revealInfo.flag ? <Flag id={revealInfo.flag} size={44} /> : revealInfo.icon}</div>
                <div class="reveal-title">{revealInfo.title}</div>
                <div class="reveal-desc">{revealInfo.desc}</div>
                {next ? (
                  <button class="btn btn-gold" onClick={() => startSpin(next)}>
                    لف {WHEELS[next].title} {WHEELS[next].icon}
                  </button>
                ) : (
                  <button class="btn" onClick={() => setReveal(null)}>
                    تمام 👌
                  </button>
                )}
              </div>
            )}
          </div>
          <div class="wheel-actions">
            {next && !revealInfo && (
              <button class="btn btn-gold btn-big" disabled={spinning} onClick={() => startSpin(next)}>
                {spinning ? '... تدور' : `🎰 لف ${WHEELS[next].title}`}
              </button>
            )}
            {next && doneCount < 8 && (
              <button
                class="btn btn-ghost btn-sm"
                disabled={spinning}
                onClick={() => {
                  setReveal(null);
                  ctl.send({ t: 'autospin' });
                }}
              >
                ⚡ لف الباقي تلقائياً
              </button>
            )}
            {!next && <div class="ready-msg">✅ دولتك جاهزة! {s.phase === 'wheels' ? 'بانتظار باقي اللاعبين...' : ''}</div>}
          </div>
        </section>

        <aside class="wheel-side">
          <div class="card result-card">
            <div class="card-title">
              بطاقة دولتك
              <span class="respins" title="تقدر تعيد لف أي عجلة">🔄 {ws.respins}</span>
            </div>
            <ul class="results">
              {WHEEL_ORDER.map((w) => {
                const v = ws.res[w];
                const info = v !== undefined ? describe(w, v, world) : null;
                const hidden = (active === w && spinning) || (w === shown && spinning);
                const canRespin = !!info && ws.respins > 0 && !spinning && !active && !(w === 'luck' && v === 'respin') && !(s.phase === 'playing' && ws.done);
                return (
                  <li key={w} class={`res-row ${info?.tone ?? ''}`}>
                    <span class="res-icon">{WHEELS[w].icon}</span>
                    <span class="res-main">
                      <span class="res-name">{WHEELS[w].title.replace('عجلة ', '')}</span>
                      <span class="res-val">
                        {info && !hidden ? (
                          <>
                            {info.flag && <Flag id={info.flag} size={13} />} {info.title}
                          </>
                        ) : (
                          <span class="muted">؟</span>
                        )}
                      </span>
                    </span>
                    {canRespin && (
                      <button class="icon-btn respin" title="إعادة اللف" onClick={() => startSpin(w, true)}>
                        🔄
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>

          {others.length > 0 && (
            <div class="card">
              <div class="card-title">اللاعبين</div>
              <ul class="plist">
                {others.map(([id, w]) => {
                  const n = WHEEL_ORDER.filter((x) => w.res[x] !== undefined).length;
                  const name = playerName(id) ?? `🤖 بوت ${id.slice(1)}`;
                  return (
                    <li key={id}>
                      {w.res.country ? <Flag id={w.res.country as string} size={14} /> : <span class="flag flag-neutral" />}
                      <span class="pname">{name}</span>
                      <span class="pprog">{w.done ? '✅' : `${n}/9`}</span>
                    </li>
                  );
                })}
              </ul>
              {ctl.isHost() && s.mode === 'online' && s.phase === 'wheels' && !s.countdown && (
                <button class="btn btn-sm" onClick={() => ctl.forceStart()}>
                  ⏩ ابدأ الحين (نلف عن المتأخرين)
                </button>
              )}
            </div>
          )}
        </aside>
      </div>

      {countdown !== null && (
        <div class="countdown">
          <div>تبدأ اللعبة خلال</div>
          <div class="countdown-n">{countdown}</div>
        </div>
      )}
    </div>
  );
}
