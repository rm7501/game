// بطاقة الدولة المختارة على الخريطة
import { AREA_NAMES, UNITS } from '../game/defs';
import { defenseValue } from '../game/battle';
import { cardTargets } from '../game/cards';
import type { Engine } from '../game/engine';
import type { Nation, TerrId } from '../game/types';
import { REGION_NAMES } from '../game/world';
import { Bar, Flag, NationTag, UnitIcon } from './bits';
import { dateStr, fmtArea, fmtMoney, fmtNum, fmtPop } from './format';

interface Props {
  eng: Engine;
  me?: Nation;
  id: TerrId;
  onClose: () => void;
  onAttack: () => void;
  onStrike: (k: 'missile' | 'nuke') => void;
  onDiplo: (nid: string) => void;
  onDefect?: () => void;
}

export function TerritoryCard({ eng, me, id, onClose, onAttack, onStrike, onDiplo, onDefect }: Props) {
  const s = eng.s;
  const t = s.terr[id];
  const m = eng.w.get(id);
  if (!t) return null;
  const owner = t.owner ? s.nations[t.owner] : null;
  const mine = !!me && t.owner === me.id;
  const def = !mine ? { D: defenseValue(eng, id, me ?? null) } : null;
  const battle = s.battles.find((b) => b.terr === id);
  const route = me && !mine ? eng.route(me, id) : null;
  const r = me && owner && !mine ? eng.peek(me.id, owner.id) : undefined;
  const why = me && owner && !mine ? eng.canHit(me, owner) : null;
  const incoming = s.moves.filter((x) => x.to === id && x.kind === 'attack');
  const canDefect = !!me && me.cards.includes('defect') && cardTargets(eng, me, 'defect').terrs.includes(id);
  return (
    <div class="tcard">
      <div class="tcard-head">
        <Flag id={id} size={28} />
        <div class="tcard-title">
          <div class="tcard-name">
            {m.ar} {owner?.capital === id && <span title="عاصمة">★</span>}
          </div>
          {m.par && <div class="small">منطقة من {eng.w.country(m.par).ar} ({eng.w.country(m.par).provs.length} مناطق)</div>}
          <div class="muted small">
            {REGION_NAMES[m.reg]} · {AREA_NAMES[m.cls]} ({fmtArea(m.area)}){!m.c && ' · بدون بحر'}
          </div>
        </div>
        <button class="icon-btn" onClick={onClose} aria-label="إغلاق">✕</button>
      </div>
      <div class="tcard-owner">
        {owner ? (
          <span class="clickable" onClick={() => !mine && onDiplo(owner.id)}>
            <NationTag name={owner.name} color={owner.color} flag={owner.home} leader={owner.leader} />
            {mine && <span class="badge good">أرضك</span>}
            {r?.war && <span class="badge bad">⚔️ حرب</span>}
            {r?.ally && <span class="badge good">🤝 حليف</span>}
            {r?.truce && r.truce > s.day && <span class="badge">🕊️ هدنة لين {dateStr(r.truce)}</span>}
          </span>
        ) : (
          <span class="muted">🏳️ دولة محايدة (تدافع عن نفسها بس)</span>
        )}
      </div>
      <div class="tcard-stats">
        <span>👥 {fmtPop(t.pop)}</span>
        <span>📈 {fmtMoney(t.gdp)}</span>
        {def && <span title="قوة الدفاع التقريبية">🛡️ {fmtNum(def.D)}</span>}
        {t.unrest > 0 && <span title="اضطرابات بعد الاحتلال">😠 {t.unrest} شهر</span>}
        {t.nuked > 0 && <span title="إشعاع نووي">☢️ {t.nuked} شهر</span>}
      </div>
      {!owner && t.g && (
        <div class="tcard-garrison muted small">
          الحامية: <UnitIcon u="inf" size={13} /> {t.g.inf} {UNITS.inf.name} · <UnitIcon u="tank" size={13} /> {t.g.tank} {UNITS.tank.name}
        </div>
      )}
      {battle && (
        <div class="battle-box">
          <div class="row-between small">
            <b>⚔️ معركة جارية · اليوم {battle.days}</b>
            <span class="muted">{s.nations[battle.att]?.name} ضد {battle.def ? s.nations[battle.def]?.name : 'الحامية'}</span>
          </div>
          <div class="bb-row"><span class="dot" style={{ background: s.nations[battle.att]?.color }} /><Bar value={battle.a} max={battle.a0} color="var(--bad)" /><span class="small">{Math.round((battle.a / battle.a0) * 100)}%</span></div>
          <div class="bb-row"><span class="dot" style={{ background: battle.def ? s.nations[battle.def]?.color : '#777' }} /><Bar value={battle.d} max={battle.d0} color="var(--accent)" /><span class="small">{Math.round((battle.d / battle.d0) * 100)}%</span></div>
          <div class="muted small">المهاجم ينسحب تحت {Math.round(battle.aBreak * 100)}%، والمدافع ينهار تحت {Math.round(battle.dBreak * 100)}%</div>
        </div>
      )}
      {incoming.length > 0 && <div class="warn small">⚠️ فيه {incoming.length} جيش متجه لهنا!</div>}
      {me && !mine && (
        <>
          <div class="muted small">
            {route ? (route.naval ? `🚢 تقدر توصل لها بغزو بحري من ${eng.w.name(route.from)}` : `🛤️ مجاورة لأراضيك (${eng.w.name(route.from)})`) : '🚫 بعيدة عن متناولك حالياً'}
          </div>
          {why && <div class="small warn">⛔ {why}</div>}
          <div class="tcard-actions">
            <button class="btn btn-danger" disabled={!route || !!why} onClick={onAttack}>⚔️ هجوم</button>
            {me.units.missile > 0 && <button class="btn" disabled={!!why} onClick={() => onStrike('missile')}>🚀 قصف ({me.units.missile})</button>}
            {me.units.nuke > 0 && <button class="btn btn-danger" disabled={!!why} onClick={() => onStrike('nuke')}>☢️ نووي ({me.units.nuke})</button>}
            {canDefect && <button class="btn btn-gold" title="بطاقة الانشقاق: تنضم لك بدون حرب" onClick={onDefect}>🏳️ انشقاق</button>}
            {owner && <button class="btn" onClick={() => onDiplo(owner.id)}>🤝 دبلوماسية</button>}
          </div>
        </>
      )}
    </div>
  );
}
