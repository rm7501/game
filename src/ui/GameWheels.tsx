// العجلات داخل اللعبة: عجلة الحظ الشخصية + عجلة الأحداث العالمية
import { useEffect, useMemo, useRef, useState } from 'preact/hooks';
import type { Controller } from '../client/controller';
import { FORTUNES, FORTUNE_SLICES, WORLD_EVENTS, WORLD_SLICES, type Slice } from '../game/defs';
import type { Engine } from '../game/engine';
import { fortuneWeights } from '../game/events';
import type { FortuneId, Nation, WorldEventId } from '../game/types';
import { sfx } from './audio';
import { Modal } from './bits';
import { toast } from './toast';
import { WheelCanvas, visibleIndex } from './WheelCanvas';

const wheelSize = () => Math.min(330, Math.max(230, Math.min(window.innerWidth - 70, window.innerHeight - 320)));

export function FortuneModal({ ctl, eng, me, onClose }: { ctl: Controller; eng: Engine; me: Nation; onClose: () => void }) {
  // الأوزان حسب ترتيبك: كل ما كنت متأخر كبرت الشرائح الحلوة
  const slices = useMemo<Slice[]>(() => {
    const w = fortuneWeights(eng, me);
    return FORTUNE_SLICES.map((sl) => ({ ...sl, w: w[sl.v as FortuneId] }));
  }, []);
  const [spinning, setSpinning] = useState(false);
  const [target, setTarget] = useState<number | null>(null);
  const [done, setDone] = useState(false);
  const nonce = useRef(me.fortune?.nonce ?? 0);
  const available = eng.s.day >= me.fortuneNext;

  useEffect(() => {
    if (!spinning || target !== null) return;
    const f = me.fortune;
    if (f && f.nonce > nonce.current) setTarget(visibleIndex(slices, f.res));
  });

  const spin = async () => {
    setSpinning(true);
    sfx.click();
    const r = await ctl.send({ t: 'fortune' });
    if (!r.ok) {
      setSpinning(false);
      toast({ icon: '⚠️', text: r.msg ?? 'ما ينفع', kind: 'bad' });
    }
  };

  const onStop = () => {
    setDone(true);
    const f = me.fortune;
    if (f) FORTUNES[f.res].good === -1 ? sfx.bad() : FORTUNES[f.res].good === 1 ? sfx.fanfare() : sfx.reveal();
  };

  const res = done ? me.fortune : undefined;
  return (
    <Modal title="🎰 عجلة الحظ" onClose={onClose}>
      <div class="game-wheel">
        <p class="muted small center">
          تتوفر لك كل {me.trait === 'gambler' ? 'سنة' : 'سنتين'}. كل ما كان ترتيبك متأخر، كبرت فرصتك بالنتايج الحلوة.
        </p>
        <WheelCanvas slices={slices} target={target} spinning={spinning} onStop={onStop} size={wheelSize()} hub="🎰" />
        {res ? (
          <div class={`reveal static ${FORTUNES[res.res].good === -1 ? 'bad' : FORTUNES[res.res].good === 1 ? 'good' : ''}`}>
            <div class="reveal-icon">{FORTUNES[res.res].icon}</div>
            <div class="reveal-title">{FORTUNES[res.res].name}</div>
            <div class="reveal-desc">{res.text}</div>
            <button class="btn btn-gold" onClick={onClose}>تمام</button>
          </div>
        ) : (
          <button class="btn btn-gold btn-big" disabled={spinning || !available} onClick={spin}>
            {spinning ? '... تدور' : available ? '🎰 لف العجلة' : 'مو متاحة الحين'}
          </button>
        )}
      </div>
    </Modal>
  );
}

export function WorldEventModal({ ev, text, onClose }: { ev: WorldEventId; text: string; onClose: () => void }) {
  const [spinning, setSpinning] = useState(false);
  const [done, setDone] = useState(false);
  useEffect(() => {
    sfx.alert();
    const t = setTimeout(() => setSpinning(true), 400);
    return () => clearTimeout(t);
  }, []);
  useEffect(() => {
    if (!done) return;
    const t = setTimeout(onClose, 9000);
    return () => clearTimeout(t);
  }, [done]);
  const def = WORLD_EVENTS[ev];
  return (
    <Modal title="🌍 عجلة الأحداث العالمية" onClose={onClose}>
      <div class="game-wheel">
        <p class="muted small center">حدث يغير العالم كله.. وغالباً يضرب الدول المسيطرة أقوى!</p>
        <WheelCanvas
          slices={WORLD_SLICES}
          target={visibleIndex(WORLD_SLICES, ev)}
          spinning={spinning}
          onStop={() => {
            setDone(true);
            sfx.fanfare();
          }}
          size={wheelSize()}
          hub="🌍"
        />
        {done && (
          <div class="reveal static">
            <div class="reveal-icon">{def.icon}</div>
            <div class="reveal-title">{def.name}</div>
            <div class="reveal-desc">{text}</div>
            <button class="btn btn-gold" onClick={onClose}>تمام</button>
          </div>
        )}
      </div>
    </Modal>
  );
}
