// نوافذ: الهجوم، القصف، المساعدات، تقرير المعركة
import { useMemo, useState } from 'preact/hooks';
import type { Controller } from '../client/controller';
import { SHIP_CAPACITY, UNITS, missileRange } from '../game/defs';
import { estimate } from '../game/battle';
import type { Engine } from '../game/engine';
import type { Nation, Report, TerrId, Units, UnitType } from '../game/types';
import { COMBAT_UNITS } from '../game/types';
import { sfx } from './audio';
import { Flag, Modal, NationTag, UnitIcon } from './bits';
import { fmtMoney, fmtNum } from './format';
import { toast } from './toast';

function chanceLabel(p: number) {
  if (p >= 0.95) return ['مضمونة تقريباً', 'good'];
  if (p >= 0.7) return ['عالية', 'good'];
  if (p >= 0.4) return ['متوسطة', ''];
  if (p >= 0.1) return ['ضعيفة', 'bad'];
  return ['انتحار!', 'bad'];
}

export function AttackDialog({ ctl, eng, me, to, onClose }: { ctl: Controller; eng: Engine; me: Nation; to: TerrId; onClose: () => void }) {
  const s = eng.s;
  const T = s.terr[to];
  const owner = T.owner ? s.nations[T.owner] : null;
  const route = useMemo(() => eng.route(me, to), [to, me.d.terrs]);
  const coastal = !!eng.w.get(to).c;
  const [u, setU] = useState<Partial<Units>>(() => {
    const init: Partial<Units> = {};
    init.inf = Math.ceil(me.units.inf * 0.6);
    init.tank = Math.ceil(me.units.tank * 0.6);
    init.jet = Math.ceil(me.units.jet * 0.5);
    const land = (init.inf ?? 0) + (init.tank ?? 0);
    init.ship = route?.naval ? Math.min(me.units.ship, Math.max(Math.ceil(land / SHIP_CAPACITY), Math.ceil(me.units.ship * 0.6))) : coastal ? Math.floor(me.units.ship * 0.3) : 0;
    return init;
  });
  const est = useMemo(() => estimate(eng, me, u, to, 40), [to, u.inf, u.tank, u.jet, u.ship, me.tech, me.d.terrs]);
  const p = est.p;
  const [label, tone] = chanceLabel(p);
  const land = (u.inf ?? 0) + (u.tank ?? 0);
  const needShips = route?.naval ? Math.ceil(land / SHIP_CAPACITY) : 0;
  const days = route ? eng.travelDays(me, route.from, to, route.naval) : 0;
  const why = owner ? eng.canHit(me, owner) : null;
  const newWar = owner && !eng.atWar(me.id, owner.id);
  const types: UnitType[] = route?.naval || coastal ? COMBAT_UNITS : ['inf', 'tank', 'jet'];

  const go = async () => {
    if (p < 0.15 && !confirm(`فرصة الفوز ${Math.round(p * 100)}% بس، وبتخسر أغلب جيشك. متأكد؟`)) return;
    const r = await ctl.send({ t: 'attack', to, units: u });
    if (r.ok) {
      sfx.alert();
      toast({ icon: '⚔️', text: r.msg ?? 'الجيش تحرك', kind: 'good' });
      onClose();
    } else toast({ icon: '⚠️', text: r.msg ?? 'ما ينفع', kind: 'bad' });
  };

  return (
    <Modal title={<>⚔️ هجوم على <Flag id={to} size={16} /> {eng.w.name(to)}</>} onClose={onClose}>
      <div class="atk-top">
        <div>المدافع: {owner ? <NationTag name={owner.name} color={owner.color} flag={owner.home} leader={owner.leader} /> : 'دولة محايدة'}</div>
        {route ? (
          <div class="muted small">
            {route.naval ? '🚢 غزو بحري' : '🛤️ هجوم بري'} من {eng.w.name(route.from)} · يوصلون بعد {days} يوم
          </div>
        ) : (
          <div class="bad small">ما تقدر توصل لهنا: مو مجاورة لأراضيك وبعيدة عن مدى أسطولك.</div>
        )}
        {why && <div class="bad small">⛔ {why}</div>}
        {newWar && !why && <div class="warn small">⚠️ الهجوم بيعلن الحرب على {owner!.name}!</div>}
      </div>
      <div class="sliders">
        {types.map((k) => (
          <label class="slider-row" key={k}>
            <UnitIcon u={k} />
            <span class="sl-name">{UNITS[k].name}</span>
            <input type="range" min={0} max={me.units[k]} value={u[k] ?? 0} onInput={(e) => setU({ ...u, [k]: Number((e.target as HTMLInputElement).value) })} disabled={!me.units[k]} />
            <b class="sl-val">{u[k] ?? 0}<span class="muted">/{me.units[k]}</span></b>
          </label>
        ))}
        {route?.naval && <div class={`small ${(u.ship ?? 0) < needShips ? 'bad' : 'muted'}`}>🚢 تحتاج {needShips} سفن لنقل {land} وحدة برية (كل سفينة تنقل {SHIP_CAPACITY})</div>}
        {!coastal && <div class="muted small">الهدف ما له بحر، السفن ما تشارك.</div>}
      </div>
      <div class="vs">
        <div class="vs-side">
          <div class="muted small">قوة هجومك</div>
          <div class="vs-n">{fmtNum(est.A)}</div>
        </div>
        <div class="vs-mid">ضد</div>
        <div class="vs-side">
          <div class="muted small">دفاعهم (تقريباً)</div>
          <div class="vs-n">{fmtNum(est.D)}</div>
        </div>
      </div>
      {est.mods.length > 0 && (
        <div class="mods">
          {est.mods.map((m) => <span class="badge" key={m}>{m}</span>)}
        </div>
      )}
      <div class={`chance ${tone}`}>
        فرصة الفوز: <b>{Math.round(p * 100)}%</b> ({label})
        <div class="chance-bar"><div style={{ width: `${p * 100}%` }} /></div>
        <div class="muted small">
          المعركة تاخذ تقريباً {est.days} يوم، وخسائرك المتوقعة {Math.round(est.aLoss * 100)}% من القوات المرسلة. الأقوى يفوز غالباً، والحظ اليومي بسيط 🎲
        </div>
      </div>
      <div class="modal-foot">
        <button class="btn" onClick={onClose}>إلغاء</button>
        <button class="btn btn-danger btn-big" disabled={!route || !!why || land < 1 || (route.naval && (u.ship ?? 0) < needShips)} onClick={go}>
          ⚔️ هجوم!
        </button>
      </div>
    </Modal>
  );
}

export function StrikeDialog({ ctl, eng, me, to, kind, onClose }: { ctl: Controller; eng: Engine; me: Nation; to: TerrId; kind: 'missile' | 'nuke'; onClose: () => void }) {
  const s = eng.s;
  const T = s.terr[to];
  const owner = T.owner ? s.nations[T.owner] : null;
  const [n, setN] = useState(Math.min(me.units.missile, 3));
  const range = Math.max(missileRange(me.tech), kind === 'nuke' ? 2500 : 0);
  const dist = eng.strikeRange(me, to);
  const inRange = dist <= range;
  const airdef = owner ? owner.b.airdef : 0;
  const intercept = kind === 'nuke' ? Math.min(0.4, 0.08 * airdef) : Math.min(0.7, 0.12 * airdef);
  const why = owner ? eng.canHit(me, owner) : null;
  const go = async () => {
    const r = await ctl.send({ t: 'strike', to, kind, n });
    if (r.ok) {
      kind === 'nuke' ? sfx.nuke() : sfx.alert();
      onClose();
    } else toast({ icon: '⚠️', text: r.msg ?? 'ما ينفع', kind: 'bad' });
  };
  return (
    <Modal title={<>{kind === 'nuke' ? '☢️ ضربة نووية' : '🚀 قصف صاروخي'} على <Flag id={to} size={16} /> {eng.w.name(to)}</>} onClose={onClose}>
      <div class="atk-top">
        <div>الهدف: {owner ? <NationTag name={owner.name} color={owner.color} flag={owner.home} /> : 'دولة محايدة'}</div>
        <div class={`small ${inRange ? 'muted' : 'bad'}`}>المسافة {fmtNum(dist)} كم · مدى صواريخك {range >= 40000 ? 'عالمي 🌍' : fmtNum(range) + ' كم'}</div>
        <div class="muted small">الدفاع الجوي عندهم يعترض {Math.round(intercept * 100)}% {kind === 'nuke' ? 'احتمال' : 'من الصواريخ'}</div>
        {why && <div class="bad small">⛔ {why}</div>}
      </div>
      {kind === 'missile' ? (
        <label class="slider-row">
          <span>🚀</span>
          <span class="sl-name">عدد الصواريخ</span>
          <input type="range" min={1} max={Math.max(1, me.units.missile)} value={n} onInput={(e) => setN(Number((e.target as HTMLInputElement).value))} />
          <b class="sl-val">{n}</b>
        </label>
      ) : (
        <div class="nuke-warn">
          ☢️ القنبلة النووية تقتل أكثر من نص السكان وتدمر الاقتصاد والجيش في الهدف.
          <br />
          <b>العالم كله بيدينك:</b> كل حلفائك بيفسخون التحالف، والتجارة تنقطع، والبوتات بتعاديك، والاستقرار ينزل 10.
        </div>
      )}
      <div class="modal-foot">
        <button class="btn" onClick={onClose}>إلغاء</button>
        <button class="btn btn-danger btn-big" disabled={!inRange || !!why || (kind === 'missile' ? me.units.missile < 1 : me.units.nuke < 1)} onClick={go}>
          {kind === 'nuke' ? '☢️ أطلق القنبلة' : `🚀 أطلق ${n} صاروخ`}
        </button>
      </div>
    </Modal>
  );
}

export function AidDialog({ ctl, eng, me, to, onClose }: { ctl: Controller; eng: Engine; me: Nation; to: string; onClose: () => void }) {
  const o = eng.s.nations[to];
  const [money, setMoney] = useState(0);
  const [u, setU] = useState<Partial<Units>>({});
  const maxMoney = Math.max(0, Math.floor(me.treasury));
  const go = async () => {
    const r = await ctl.send({ t: 'aid', to, money, units: u });
    if (r.ok) {
      sfx.coin();
      toast({ icon: '🎁', text: `أرسلت المساعدات لـ ${o.name}`, kind: 'good' });
      onClose();
    } else toast({ icon: '⚠️', text: r.msg ?? 'ما ينفع', kind: 'bad' });
  };
  return (
    <Modal title={<>🎁 مساعدات لـ <Flag id={o.home} size={16} /> {o.name}</>} onClose={onClose}>
      <label class="slider-row">
        <span>💰</span>
        <span class="sl-name">فلوس</span>
        <input type="range" min={0} max={maxMoney} value={money} onInput={(e) => setMoney(Number((e.target as HTMLInputElement).value))} />
        <b class="sl-val">{fmtMoney(money)}</b>
      </label>
      {(['inf', 'tank', 'jet', 'ship', 'missile'] as UnitType[]).map((k) => (
        <label class="slider-row" key={k}>
          <UnitIcon u={k} />
          <span class="sl-name">{UNITS[k].name}</span>
          <input type="range" min={0} max={me.units[k]} value={u[k] ?? 0} disabled={!me.units[k]} onInput={(e) => setU({ ...u, [k]: Number((e.target as HTMLInputElement).value) })} />
          <b class="sl-val">{u[k] ?? 0}</b>
        </label>
      ))}
      <div class="modal-foot">
        <button class="btn" onClick={onClose}>إلغاء</button>
        <button class="btn btn-primary" onClick={go}>إرسال</button>
      </div>
    </Modal>
  );
}

function UnitsLine({ u }: { u: Partial<Units> }) {
  const parts = (Object.entries(u) as [UnitType, number][]).filter(([, n]) => n > 0);
  if (!parts.length) return <span class="muted">—</span>;
  return (
    <span class="units-line">
      {parts.map(([k, n]) => (
        <span key={k} class="ul-item"><UnitIcon u={k} size={14} /> {n}</span>
      ))}
    </span>
  );
}

export function ReportModal({ eng, rep, myId, onClose }: { eng: Engine; rep: Report; myId?: string; onClose: () => void }) {
  const s = eng.s;
  const A = s.nations[rep.att];
  const D = rep.def ? s.nations[rep.def] : null;
  const iAmAtt = rep.att === myId;
  const iAmDef = rep.def === myId;
  const myWin = (iAmAtt && rep.win) || (iAmDef && !rep.win);
  const title = rep.kind === 'nuke' ? '☢️ ضربة نووية' : rep.kind === 'missile' ? '🚀 قصف صاروخي' : '⚔️ تقرير المعركة';
  return (
    <Modal title={<>{title} · <Flag id={rep.terr} size={14} /> {eng.w.name(rep.terr)}</>} onClose={onClose}>
      {(iAmAtt || iAmDef) && rep.kind === 'battle' && (
        <div class={`report-banner ${myWin ? 'good' : 'bad'}`}>{myWin ? '🏆 انتصار!' : '💀 هزيمة'}</div>
      )}
      {rep.kind === 'battle' ? (
        <div class="report">
          <div class="rep-side">
            <div class="rep-title">المهاجم</div>
            {A && <NationTag name={A.name} color={A.color} flag={A.home} />}
            <div class="muted small">القوات</div>
            <UnitsLine u={rep.aUnits} />
            <div class="rep-pow">قوة البداية {fmtNum(rep.A)} · بقي <b>{rep.la}%</b></div>
            <div class="muted small">الخسائر</div>
            <UnitsLine u={rep.aLoss} />
          </div>
          <div class="rep-vs">{rep.win ? '⬅️ فاز' : 'فاز ➡️'}</div>
          <div class="rep-side">
            <div class="rep-title">المدافع</div>
            {D ? <NationTag name={D.name} color={D.color} flag={D.home} /> : <span>{eng.w.name(rep.terr)} (محايدة)</span>}
            <div class="muted small">القوات</div>
            <UnitsLine u={rep.dUnits} />
            <div class="rep-pow">قوة البداية {fmtNum(rep.D)} · بقي <b>{rep.ld}%</b></div>
            <div class="muted small">الخسائر</div>
            <UnitsLine u={rep.dLoss} />
            {rep.allies.length > 0 && <div class="muted small">بمساعدة: {rep.allies.map((a) => s.nations[a]?.name).join('، ')}</div>}
          </div>
        </div>
      ) : (
        <div class="report-strike">
          <div>{A?.name} ← {eng.w.name(rep.terr)}</div>
          {rep.kind === 'missile' ? (
            <div>
              أصاب {rep.hits} صاروخ{rep.intercepted ? ` واعترض الدفاع الجوي ${rep.intercepted}` : ''}
            </div>
          ) : (
            <div>{rep.hits ? 'القنبلة انفجرت 💥' : 'الدفاع الجوي اعترض القنبلة 📡'}</div>
          )}
          <div class="muted small">الخسائر في الهدف</div>
          <UnitsLine u={rep.dLoss} />
        </div>
      )}
      {rep.kind === 'battle' && (
        <div class="rep-foot">
          {rep.days ? <div>⏱️ المعركة استمرت {rep.days} يوم</div> : null}
          {rep.mods && rep.mods.length > 0 && <div class="mods">{rep.mods.map((m) => <span class="badge" key={m}>{m}</span>)}</div>}
          <div class="muted small">{rep.win ? `${eng.w.name(rep.terr)} صارت تابعة لـ ${A?.name}` : 'المهاجم انسحب بالقوات اللي بقت'}</div>
        </div>
      )}
    </Modal>
  );
}
