// تبويبات اللوحة الجانبية داخل اللعبة
import { useEffect, useRef, useState } from 'preact/hooks';
import type { Controller } from '../client/controller';
import {
  AREA_NAMES, BUILDINGS, DAYS_PER_MONTH, GOVS, LEADERS, LUCK, MAX_BUILDING_LEVEL, MAX_TECH, NUKE_PROJECT, RESOURCES, TECH_COST, TECH_NAMES,
  TERRAINS, UNITS,
} from '../game/defs';
import { Engine, PROP_NAMES } from '../game/engine';
import { missionProgress, missionText } from '../game/events';
import type { BuildingType, Nation, NationId, UnitType } from '../game/types';
import { BUILDING_TYPES, UNIT_TYPES } from '../game/types';
import { sfx } from './audio';
import { Bar, Flag, NationTag, Stat, UnitIcon } from './bits';
import { dateStr, fmtArea, fmtMoney, fmtNum, fmtPop } from './format';
import { toast } from './toast';
import { IntelBlock, IntelReveal, TeamBadge, TeamStandings } from './plans';
import { hasIntel } from '../game/spies';
import { isController } from '../game/dev';
import { CARDS } from '../game/defs';

export interface PanelProps {
  ctl: Controller;
  eng: Engine;
  me?: Nation;
  onSelect: (t: string) => void;
  onAid?: (to: NationId) => void;
  openTab?: (t: Tab) => void;
  focusNation?: NationId | null;
  onSpy?: (to: NationId) => void;
  onCards?: () => void;
}

export type Tab = 'overview' | 'economy' | 'military' | 'diplo' | 'chat' | 'rank' | 'news';

async function run(ctl: Controller, cmd: Parameters<Controller['send']>[0], okMsg?: string, sound: () => void = sfx.coin) {
  const r = await ctl.send(cmd);
  if (r.ok) {
    sound();
    if (r.msg || okMsg) toast({ icon: '✅', text: r.msg ?? okMsg!, kind: 'good' });
  } else toast({ icon: '⚠️', text: r.msg ?? 'ما ينفع', kind: 'bad' });
  return r.ok;
}

// ---------------- دولتي ----------------
export function OverviewTab({ ctl, eng, me, onSelect, onCards }: PanelProps) {
  if (!me) return <Spectator ctl={ctl} />;
  const d = me.d;
  const net = d.income - d.upkeep;
  const terrs = eng.owned(me.id).sort((a, b) => b.gdp - a.gdp);
  const ranking = Object.values(eng.s.nations).filter((n) => n.alive).sort((a, b) => b.d.score - a.d.score);
  const rank = ranking.findIndex((n) => n.id === me.id) + 1;
  const nextCost = me.tech < MAX_TECH ? TECH_COST[me.tech + 1] : 0;
  const [tax, setTax] = useState(me.tax);
  useEffect(() => setTax(me.tax), [me.tax]);
  return (
    <div class="tab-body">
      <div class="nation-head">
        <Flag id={me.home} size={34} />
        <div>
          <div class="nation-name" style={{ color: me.color }}>{me.name}</div>
          <div class="muted small">
            {me.leader} · {GOVS[me.gov].icon} {GOVS[me.gov].name} · {RESOURCES[me.res].icon} {RESOURCES[me.res].name}
          </div>
        </div>
        <div class="rank-badge" title="ترتيبك">#{rank}</div>
      </div>
      <div class="traits">
        <span class="badge" title={LEADERS[me.trait].desc}>{LEADERS[me.trait].icon} {LEADERS[me.trait].name}</span>
        <span class="badge" title={TERRAINS[me.terrain].desc}>{TERRAINS[me.terrain].icon} {TERRAINS[me.terrain].name}</span>
        {me.underdog && <span class="badge good" title="من الدول الأضعف: الجيش أرخص 15%، والنمو أسرع، والدفاع أقوى 20%">🛡️ دعم المستضعفين</span>}
        {me.gov === 'transitional' && me.govUntil && <span class="badge">🌀 الحكومة الانتقالية تنتهي بعد {Math.max(1, Math.ceil((me.govUntil - eng.s.day) / 30))} شهر</span>}
        <TeamBadge team={me.team} />
        {(me.fx.blitz ?? 0) > eng.s.day && <span class="badge good">⚡ هجوم خاطف ({me.fx.blitz! - eng.s.day} يوم)</span>}
        {(me.fx.shield ?? 0) > eng.s.day && <span class="badge good">🛡️ درع وطني ({me.fx.shield! - eng.s.day} يوم)</span>}
        {(me.fx.sanct ?? 0) > eng.s.day && <span class="badge bad" title="دخلك ناقص 30%">🚫 عقوبات لين {dateStr(me.fx.sanct!)}</span>}
        {(me.fx.supply ?? 0) > eng.s.day && <span class="badge bad">🚧 إمداداتك مقطوعة ({me.fx.supply! - eng.s.day} يوم)</span>}
      </div>
      <button class="block cards-strip clickable" onClick={onCards}>
        <span class="block-title">🃏 بطاقات الخطط ({me.cards.length})</span>
        <span class="cards-mini">{me.cards.length ? me.cards.map((c, i) => <span key={i} title={CARDS[c].name}>{CARDS[c].icon}</span>) : <span class="muted small">ما عندك بطاقات (تاخذ وحدة كل سنة)</span>}</span>
      </button>
      {eng.s.coalition === me.id && <div class="hint bad block">🌍 العالم متحالف ضدك بسبب هيمنتك! هجومهم عليك أقوى 20%، انتبه لحدودك.</div>}
      {eng.s.coalition && eng.s.coalition !== me.id && eng.s.nations[eng.s.coalition] && (
        <div class="hint block">🌍 فيه تحالف دولي ضد {eng.s.nations[eng.s.coalition].name}. لو هاجمتها يكون هجومك أقوى 20%.</div>
      )}
      <div class={`block mission ${me.mission.done ? 'done' : ''}`}>
        <div class="row-between">
          <span class="block-title">🎯 مهمتك السرية</span>
          {me.mission.done ? <b class="good">✅ تحققت</b> : <span class="muted small">{Math.min(missionProgress(eng, me), me.mission.target)}/{me.mission.target}</span>}
        </div>
        <div>{missionText(me)}</div>
        {!me.mission.done && <Bar value={missionProgress(eng, me)} max={me.mission.target} color="var(--gold)" />}
        <div class="muted small">لو حققتها تاخذ نقاط إضافية كبيرة وفلوس ولفة حظ مجانية</div>
      </div>
      <div class="stat-grid">
        <Stat icon="💰" label="الخزينة" value={fmtMoney(me.treasury)} sub={<span class={net >= 0 ? 'good' : 'bad'}>{net >= 0 ? '+' : ''}{fmtMoney(net)} شهرياً</span>} tone={me.treasury < 0 ? 'bad' : undefined} />
        <Stat icon="📈" label="الناتج المحلي" value={fmtMoney(d.gdp)} sub="سنوياً" />
        <Stat icon="🏦" label="الدخل" value={fmtMoney(d.income)} sub={`صيانة الجيش ${fmtMoney(d.upkeep)}`} />
        <Stat icon="👥" label="السكان" value={fmtPop(d.pop)} sub={`قوى بشرية ${fmtNum(Math.max(0, d.manpower))} ألف`} />
        <Stat icon="⚔️" label="القوة العسكرية" value={fmtNum(d.power)} sub={d.atWar ? `في حرب مع ${d.atWar}` : 'ما فيه حروب'} tone={d.atWar ? 'bad' : undefined} />
        <Stat icon="🗺️" label="الأراضي" value={`${d.countries} ${d.countries === 1 ? 'دولة' : 'دول'}`} sub={`${d.terrs > d.countries ? d.terrs + ' مناطق · ' : ''}${fmtArea(d.area)}`} />
        <Stat icon="🏆" label="النقاط" value={fmtNum(d.score)} sub={`المركز ${rank} من ${ranking.length}`} />
        <Stat icon="🎁" label="المفاجأة" value={`${LUCK[me.luck].icon} ${LUCK[me.luck].name}`} />
      </div>
      {net < 0 && (
        <div class="hint bad block">
          ⚠️ مصاريف جيشك أكثر من دخلك! ارفع الضرائب، أو ابنِ مصانع، أو سرّح جزء من الجيش من تبويب «الجيش». لو صارت الخزينة بالسالب كثير بيتسرح الجيش لحاله.
        </div>
      )}
      <div class="block">
        <div class="row-between">
          <span>⚖️ الاستقرار</span>
          <b class={me.stability < 30 ? 'bad' : me.stability > 65 ? 'good' : ''}>{Math.round(me.stability)}%</b>
        </div>
        <Bar value={me.stability} max={100} color={me.stability < 30 ? 'var(--bad)' : me.stability > 65 ? 'var(--good)' : 'var(--gold)'} />
        {me.stability < 25 && <div class="hint bad">⚠️ الاستقرار منخفض جداً! ممكن تصير ثورات وتخسر أراضي. خفف الضرائب أو ابنِ صحة وتعليم.</div>}
      </div>
      <div class="block">
        <div class="row-between">
          <span>🧪 التكنولوجيا: {TECH_NAMES[me.tech]} ({me.tech}/{MAX_TECH})</span>
          <span class="muted small">+{d.research.toFixed(1)} نقطة/شهر</span>
        </div>
        {me.tech < MAX_TECH ? <Bar value={me.research} max={nextCost} color="var(--accent)" /> : <div class="muted small">وصلت لأعلى مستوى 🚀</div>}
      </div>
      <div class="block">
        <div class="row-between">
          <span>🧾 الضرائب</span>
          <b>{Math.round(tax * 100)}%</b>
        </div>
        <input
          type="range" min={5} max={45} step={1} value={Math.round(tax * 100)}
          onInput={(e) => setTax(Number((e.target as HTMLInputElement).value) / 100)}
          onChange={(e) => run(ctl, { t: 'tax', rate: Number((e.target as HTMLInputElement).value) / 100 }, undefined, sfx.click)}
        />
        <div class="muted small">ضرائب أعلى = فلوس أكثر بس الشعب يزعل (الاستقرار ينزل)</div>
      </div>
      <div class="block">
        <div class="block-title">أراضيك ({terrs.length})</div>
        <ul class="terr-list">
          {terrs.map((t) => (
            <li key={t.id} onClick={() => onSelect(t.id)}>
              <Flag id={t.id} size={14} />
              <span class="tl-name">{eng.w.name(t.id)} {t.id === me.capital && '★'}</span>
              <span class="tl-info">{fmtPop(t.pop)} · {fmtMoney(t.gdp)}</span>
              {t.unrest > 0 && <span title="اضطرابات بعد الاحتلال">😠</span>}
              {t.nuked > 0 && <span title="إشعاع نووي">☢️</span>}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function Spectator({ ctl }: { ctl: Controller }) {
  const gm = !!ctl.state.players[ctl.me]?.gm;
  return (
    <div class="tab-body center">
      <div class="big-emoji">{gm ? '🛠️' : '💀'}</div>
      <p>{gm ? 'أنت تدير اللعبة بدون دولة. تحكم بكل شي من زر 🛠️ «لوحة المتحكم» على الخريطة.' : 'دولتك سقطت.. تقدر تتفرج على باقي اللعبة.'}</p>
    </div>
  );
}

// ---------------- الاقتصاد ----------------
export function EconomyTab({ ctl, eng, me }: PanelProps) {
  if (!me) return <Spectator ctl={ctl} />;
  const d = me.d;
  const par = 2 + GOVS[me.gov].parallel;
  return (
    <div class="tab-body">
      <div class="block">
        <div class="row-between">
          <span>🏗️ مساحة البناء</span>
          <b>{d.used} / {d.slots}</b>
        </div>
        <Bar value={d.used} max={d.slots} />
        <div class="muted small">كل ما احتليت أراضي أكبر زادت مساحة البناء. تبني {par} مباني بنفس الوقت.</div>
      </div>
      {me.bq.length > 0 && (
        <div class="block">
          <div class="block-title">قيد البناء</div>
          {me.bq.map((q, i) => (
            <div class="qrow" key={q.id}>
              <span>{BUILDINGS[q.type as BuildingType].icon}</span>
              <span class="q-name">{BUILDINGS[q.type as BuildingType].name}{i >= par && <span class="muted small"> (بالانتظار)</span>}</span>
              <Bar value={q.total - q.left} max={q.total} color="var(--accent)" />
              <span class="muted small">{Math.ceil(q.left)} يوم</span>
              <button class="icon-btn" title="إلغاء (يرجع نص المبلغ)" onClick={() => run(ctl, { t: 'cancel', q: 'bq', id: q.id }, undefined, sfx.click)}>✕</button>
            </div>
          ))}
        </div>
      )}
      <div class="build-grid">
        {BUILDING_TYPES.map((b) => {
          const def = BUILDINGS[b];
          const lvl = me.b[b];
          const queued = me.bq.filter((q) => q.type === b).length;
          const cost = eng.buildCost(me, b);
          const days = eng.buildDays(me, b);
          const disabled = (b === 'mining' && me.res === 'none') || lvl + queued >= MAX_BUILDING_LEVEL;
          const afford = me.treasury >= cost && d.used < d.slots && me.bq.length < 6;
          return (
            <div class={`build-card ${disabled ? 'disabled' : ''}`} key={b}>
              <div class="bc-head">
                <span class="bc-icon">{def.icon}</span>
                <span class="bc-name">{def.name}</span>
                <span class="bc-lvl">مستوى {lvl}{queued ? `+${queued}` : ''}</span>
              </div>
              <div class="bc-desc">{def.desc}</div>
              <button class="btn btn-sm btn-primary" disabled={disabled || !afford} onClick={() => run(ctl, { t: 'build', b }, `بدأ بناء ${def.name}`)}>
                بناء · {fmtMoney(cost)} · {days} يوم
              </button>
            </div>
          );
        })}
      </div>
      {!me.nukeProg && (
        <div class="block special">
          <div class="block-title">☢️ البرنامج النووي</div>
          <div class="muted small">
            يفتح لك صناعة القنابل النووية. يحتاج تكنولوجيا مستوى {NUKE_PROJECT.tech}، ويكلف {NUKE_PROJECT.cost} مليار، ويستغرق سنتين. (لو عندك يورانيوم يكون جاهز من البداية)
          </div>
          <button class="btn btn-sm btn-danger" disabled={me.tech < NUKE_PROJECT.tech || me.treasury < NUKE_PROJECT.cost || me.q.some((q) => q.kind === 'project')} onClick={() => run(ctl, { t: 'project', p: 'nuke' }, 'بدأ البرنامج النووي')}>
            {me.q.some((q) => q.kind === 'project') ? 'البرنامج شغال...' : 'ابدأ البرنامج النووي'}
          </button>
        </div>
      )}
    </div>
  );
}

// ---------------- الجيش ----------------
export function MilitaryTab({ ctl, eng, me, onSelect }: PanelProps) {
  if (!me) return <Spectator ctl={ctl} />;
  const moving = eng.movingUnits(me.id);
  const [qty, setQty] = useState<Record<string, number>>({ inf: 5, tank: 2, jet: 1, ship: 1, missile: 1, nuke: 1 });
  const myMoves = eng.s.moves.filter((m) => m.owner === me.id);
  const myBattles = eng.s.battles.filter((b) => b.att === me.id || b.def === me.id || b.allies.some((a) => a.id === me.id));
  return (
    <div class="tab-body">
      {myBattles.length > 0 && (
        <div class="block special">
          <div class="block-title">⚔️ معارك شغالة</div>
          {myBattles.map((b) => {
            const att = b.att === me.id;
            return (
              <div class="battle-row clickable" key={b.id} onClick={() => onSelect(b.terr)}>
                <span class="br-title">{att ? '⚔️' : '🛡️'} {eng.w.name(b.terr)} <span class="muted small">· يوم {b.days}</span></span>
                <span class="br-bars">
                  <Bar value={b.a} max={b.a0} color="var(--bad)" />
                  <Bar value={b.d} max={b.d0} color="var(--accent)" />
                </span>
              </div>
            );
          })}
        </div>
      )}
      <div class="army-table">
        {UNIT_TYPES.map((u) => (
          <div class="army-row" key={u}>
            <UnitIcon u={u} />
            <span class="ar-name">{UNITS[u].name}</span>
            <b class="ar-n">{fmtNum(me.units[u])}</b>
            {moving[u] > 0 && <span class="muted small">+{moving[u]} بالطريق</span>}
          </div>
        ))}
        <div class="muted small">القوة الكلية {fmtNum(me.d.power)} · القوى البشرية {fmtNum(Math.max(0, me.d.manpower))} ألف</div>
      </div>
      {me.q.length > 0 && (
        <div class="block">
          <div class="block-title">قيد الإنتاج</div>
          {me.q.map((q) => (
            <div class="qrow" key={q.id}>
              {q.kind === 'unit' ? <UnitIcon u={q.type as UnitType} size={16} /> : <span>☢️</span>}
              <span class="q-name">{q.kind === 'unit' ? `${q.count} ${UNITS[q.type as UnitType].name}` : 'البرنامج النووي'}</span>
              <Bar value={q.total - q.left} max={q.total} color="var(--accent)" />
              <span class="muted small">{Math.ceil(q.left)} يوم</span>
              <button class="icon-btn" title="إلغاء (يرجع نص المبلغ)" onClick={() => run(ctl, { t: 'cancel', q: 'q', id: q.id }, undefined, sfx.click)}>✕</button>
            </div>
          ))}
        </div>
      )}
      <div class="block-title">تجنيد وشراء أسلحة</div>
      <div class="recruit-list">
        {UNIT_TYPES.map((u) => {
          const def = UNITS[u];
          const locked = u === 'nuke' ? !me.nukeProg || me.tech < 3 : me.tech < def.tech;
          const n = Math.max(1, qty[u] ?? 1);
          const cost = eng.unitCost(me, u) * n;
          const days = eng.prodDays(me, u, n);
          return (
            <div class={`recruit ${locked ? 'locked' : ''}`} key={u}>
              <div class="rc-head">
                <UnitIcon u={u} size={22} />
                <div>
                  <div class="rc-name">{def.name}</div>
                  <div class="muted small">
                    {def.atk || def.def ? `هجوم ${def.atk} · دفاع ${def.def} · ` : ''}{def.desc}
                  </div>
                </div>
              </div>
              {locked ? (
                <div class="muted small">🔒 {u === 'nuke' ? 'تحتاج برنامج نووي وتكنولوجيا 3' : `تحتاج تكنولوجيا مستوى ${def.tech}`}</div>
              ) : (
                <div class="rc-buy">
                  <div class="qty">
                    {(u === 'nuke' ? [1] : u === 'inf' ? [1, 5, 10, 25] : [1, 3, 5, 10]).map((x) => (
                      <button key={x} class={`chip ${n === x ? 'on' : ''}`} onClick={() => setQty({ ...qty, [u]: x })}>{x}</button>
                    ))}
                  </div>
                  <button class="btn btn-sm btn-primary" disabled={me.treasury < cost} onClick={() => run(ctl, { t: 'recruit', u, n }, `بدأ إنتاج ${n} ${def.name}`)}>
                    {fmtMoney(cost)} · {days} يوم
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
      <details class="block">
        <summary class="block-title clickable">🪖 تسريح وحدات (يوفر صيانة)</summary>
        <div class="disband">
          {(['inf', 'tank', 'jet', 'ship'] as UnitType[]).map((u) => (
            <button key={u} class="btn btn-sm btn-ghost" disabled={me.units[u] < 1} onClick={() => run(ctl, { t: 'disband', u, n: Math.max(1, Math.ceil(me.units[u] * 0.2)) }, undefined, sfx.click)}>
              <UnitIcon u={u} size={14} /> سرّح {Math.max(1, Math.ceil(me.units[u] * 0.2))}
            </button>
          ))}
        </div>
        <div class="muted small">الصيانة الحالية {fmtMoney(me.d.upkeep)} شهرياً</div>
      </details>
      {myMoves.length > 0 && (
        <div class="block">
          <div class="block-title">جيوشك بالطريق</div>
          {myMoves.map((m) => (
            <div class="qrow clickable" key={m.id} onClick={() => onSelect(m.to)}>
              <span>{m.kind === 'return' ? '↩️' : m.kind === 'missile' ? '🚀' : m.kind === 'nuke' ? '☢️' : m.naval ? '🚢' : '⚔️'}</span>
              <span class="q-name">{m.kind === 'return' ? 'راجعين من' : 'متجهين إلى'} {eng.w.name(m.kind === 'return' ? m.from : m.to)}</span>
              <span class="muted small">{Math.max(0, m.arrive - eng.s.day)} يوم</span>
            </div>
          ))}
        </div>
      )}
      <div class="muted small hint">💡 عشان تهاجم: اضغط على أي دولة بالخريطة واختر «هجوم».</div>
    </div>
  );
}

// ---------------- الدبلوماسية ----------------
export function DiplomacyTab({ ctl, eng, me, onAid, focusNation, onSelect, onSpy }: PanelProps) {
  const s = eng.s;
  const nations = Object.values(s.nations).filter((n) => n.alive && n.id !== me?.id).sort((a, b) => b.d.score - a.d.score);
  const incoming = me ? s.props.filter((p) => p.to === me.id) : [];
  const outgoing = me ? s.props.filter((p) => p.from === me.id) : [];
  const focusRef = useRef<HTMLDivElement>(null);
  useEffect(() => focusRef.current?.scrollIntoView({ block: 'center', behavior: 'smooth' }), [focusNation]);
  if (!me) return <Spectator ctl={ctl} />;
  return (
    <div class="tab-body">
      <IntelBlock ctl={ctl} eng={eng} me={me} />
      {incoming.length > 0 && (
        <div class="block special">
          <div class="block-title">📨 طلبات وصلتك</div>
          {incoming.map((p) => (
            <div class="prop-row" key={p.id}>
              <span><Flag id={s.nations[p.from]?.home ?? ''} size={14} /> {s.nations[p.from]?.name} ترسل {PROP_NAMES[p.type]}</span>
              <span class="prop-actions">
                <button class="btn btn-sm btn-primary" onClick={() => run(ctl, { t: 'respond', id: p.id, accept: true }, 'تم القبول', sfx.good)}>قبول</button>
                <button class="btn btn-sm" onClick={() => run(ctl, { t: 'respond', id: p.id, accept: false }, undefined, sfx.click)}>رفض</button>
              </span>
            </div>
          ))}
        </div>
      )}
      {nations.length === 0 && <p class="muted">ما فيه دول ثانية.</p>}
      {nations.map((o) => {
        const r = eng.peek(me.id, o.id);
        const truce = r?.truce && r.truce > s.day;
        const ratio = o.d.power / Math.max(1, me.d.power);
        const peace = s.day < eng.peaceEnd(me, o);
        const pending = (t: string) => outgoing.some((p) => p.to === o.id && p.type === t);
        return (
          <div class={`dip-card ${focusNation === o.id ? 'focus' : ''}`} key={o.id} ref={focusNation === o.id ? focusRef : undefined}>
            <div class="dip-head" onClick={() => onSelect(o.capital)}>
              <Flag id={o.home} size={18} />
              <span class="dot" style={{ background: o.color }} />
              <span class="dip-name">{o.name}</span>
              <span class="muted small">{o.kind === 'bot' ? '🤖' : '👤'} {o.leader}</span>
              <TeamBadge team={o.team} short />
            </div>
            <div class="dip-badges">
              {r?.war && <span class="badge bad">⚔️ حرب</span>}
              {r?.ally && <span class="badge good">{r.team ? '👥 فريقك' : '🤝 حلفاء'}</span>}
              {r?.trade && <span class="badge">📦 تجارة</span>}
              {truce && <span class="badge">🕊️ هدنة لين {dateStr(r!.truce!)}</span>}
              {peace && !r?.war && <span class="badge">🕊️ فترة سلام</span>}
              <span class={`badge ${ratio > 1.3 ? 'bad' : ratio < 0.7 ? 'good' : ''}`} title="قوتهم مقارنة بقوتك">
                قوتهم {ratio >= 10 ? '×' + Math.round(ratio) : ratio >= 1 ? '×' + ratio.toFixed(1) : Math.round(ratio * 100) + '%'}
              </span>
              <span class="badge">{o.d.countries} دول</span>
              {(o.fx.sanct ?? 0) > s.day && <span class="badge bad">🚫 عليها عقوبات</span>}
            </div>
            {(hasIntel(eng, me, o.id) || isController(s, ctl.me)) && <IntelReveal eng={eng} o={o} until={hasIntel(eng, me, o.id) ? me.intel[o.id] : undefined} />}
            <div class="dip-actions">
              {r?.war ? (
                <button class="btn btn-sm" disabled={pending('peace')} onClick={() => run(ctl, { t: 'propose', to: o.id, type: 'peace' }, undefined, sfx.click)}>🕊️ اطلب سلام</button>
              ) : (
                <>
                  {!r?.ally && <button class="btn btn-sm" disabled={pending('ally')} onClick={() => run(ctl, { t: 'propose', to: o.id, type: 'ally' }, undefined, sfx.click)}>🤝 تحالف</button>}
                  {!r?.trade && <button class="btn btn-sm" disabled={pending('trade')} onClick={() => run(ctl, { t: 'propose', to: o.id, type: 'trade' }, undefined, sfx.click)}>📦 تجارة</button>}
                  {r?.ally && !r.team && <button class="btn btn-sm btn-ghost" onClick={() => confirm('أكيد تبي تفسخ التحالف؟ (الاستقرار ينزل 10)') && run(ctl, { t: 'breakAlly', with: o.id }, undefined, sfx.bad)}>💔 فسخ التحالف</button>}
                  {r?.trade && <button class="btn btn-sm btn-ghost" onClick={() => run(ctl, { t: 'cancelTrade', with: o.id }, undefined, sfx.click)}>إلغاء التجارة</button>}
                  {!r?.ally && !truce && !peace && <button class="btn btn-sm btn-danger" onClick={() => confirm(`تعلن الحرب على ${o.name}؟`) && run(ctl, { t: 'declare', on: o.id }, undefined, sfx.alert)}>⚔️ إعلان حرب</button>}
                  <button class="btn btn-sm" onClick={() => onAid?.(o.id)}>🎁 مساعدة</button>
                </>
              )}
              {!(me.team && o.team === me.team) && <button class="btn btn-sm btn-ghost" onClick={() => onSpy?.(o.id)}>🕵️ تجسس</button>}
            </div>
          </div>
        );
      })}
      <div class="muted small hint">💡 التجارة تزيد دخلك ودخلهم. الحلفاء يدافعون عن بعض (15% من جيشهم) وما يقدرون يهاجمون بعض.</div>
    </div>
  );
}

// ---------------- الدردشة ----------------
export function ChatTab({ ctl, eng, me }: PanelProps) {
  const s = eng.s;
  const myId = ctl.myNationId();
  const [to, setTo] = useState<string>('');
  const [text, setText] = useState('');
  const box = useRef<HTMLDivElement>(null);
  const myTeam = me?.team ?? (myId ? s.nations[myId]?.team : undefined);
  const msgs = s.chat.filter((c) => (c.team ? c.team === myTeam : !c.to || c.to === myId || c.from === myId));
  useEffect(() => {
    box.current?.scrollTo({ top: box.current.scrollHeight });
  }, [msgs.length]);
  const others = Object.values(s.nations).filter((n) => n.id !== myId && n.kind === 'player');
  const send = () => {
    if (!text.trim()) return;
    ctl.send({ t: 'chat', text, to: to && to !== 'team' ? to : undefined, team: to === 'team' || undefined });
    setText('');
  };
  return (
    <div class="tab-body chat">
      <div class="chat-msgs" ref={box}>
        {msgs.length === 0 && <div class="muted center">ما فيه رسائل.. قل مرحبا 👋</div>}
        {msgs.map((c) => {
          const n = s.nations[c.from];
          return (
            <div class={`msg ${c.from === myId ? 'mine' : ''} ${c.to || c.team ? 'dm' : ''}`} key={c.id}>
              <span class="msg-from" style={{ color: n?.color }}>
                {n && <Flag id={n.home} size={11} />} {c.name}
                {c.to && <span class="muted"> ← {c.to === myId ? 'لك' : s.nations[c.to]?.name}</span>}
                {c.team && <span class="muted"> ← 👥 الفريق</span>}
              </span>
              <span class="msg-text">{c.text}</span>
            </div>
          );
        })}
      </div>
      <div class="chat-input">
        <select value={to} onChange={(e) => setTo((e.target as HTMLSelectElement).value)}>
          <option value="">📢 للكل</option>
          {myTeam ? <option value="team">👥 لفريقي</option> : null}
          {others.map((o) => (
            <option value={o.id} key={o.id}>🔒 {o.name} ({o.leader})</option>
          ))}
        </select>
        <input
          value={text}
          maxLength={300}
          placeholder={me ? 'اكتب رسالة...' : 'اكتب رسالة (متفرج)...'}
          onInput={(e) => setText((e.target as HTMLInputElement).value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
        />
        <button class="btn btn-primary btn-sm" onClick={send}>إرسال</button>
      </div>
    </div>
  );
}

// ---------------- الترتيب ----------------
export function RankTab({ eng, me, onSelect }: PanelProps) {
  const s = eng.s;
  const all = Object.values(s.nations).sort((a, b) => Number(b.alive) - Number(a.alive) || b.d.score - a.d.score);
  const total = eng.w.totalArea;
  return (
    <div class="tab-body">
      <GoalBox eng={eng} me={me} />
      <TeamStandings eng={eng} me={me} />
      <table class="rank-table">
        <thead>
          <tr><th>#</th><th>الدولة</th><th>النقاط</th><th>الأراضي</th><th>القوة</th></tr>
        </thead>
        <tbody>
          {all.map((n, i) => (
            <tr key={n.id} class={`${n.id === me?.id ? 'me' : ''} ${n.alive ? '' : 'dead'}`} onClick={() => n.alive && onSelect(n.capital)}>
              <td>{n.alive ? i + 1 : '💀'}</td>
              <td>
                <NationTag name={n.name} color={n.color} flag={n.home} />
                <div class="muted small">{n.kind === 'bot' ? '🤖' : '👤'} {n.leader} <TeamBadge team={n.team} short /></div>
              </td>
              <td>{fmtNum(n.d.score)}</td>
              <td>{n.d.countries} <span class="muted small">({Math.round((n.d.area / total) * 100)}%)</span></td>
              <td>{fmtNum(n.d.power)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function GoalBox({ eng, me }: { eng: Engine; me?: Nation }) {
  const s = eng.s;
  const st = s.settings;
  let text = '';
  const teams = st.teams > 0;
  if (st.win === 'score') {
    const left = st.years * 12 * DAYS_PER_MONTH - s.day;
    text = `🏆 ${teams ? 'الفريق صاحب أعلى مجموع نقاط' : 'أعلى نقاط'} بعد ${st.years} سنة · باقي ${Math.max(0, Math.ceil(left / 360))} سنة`;
  } else if (st.win === 'percent') {
    const mine = me ? Math.round((me.d.area / eng.w.totalArea) * 100) : 0;
    text = `🏆 أول ${teams ? 'فريق' : 'من'} يسيطر على ${st.percent}% من مساحة العالم${teams ? '' : ' (مع حلفائه)'} · أنت ${mine}%`;
  } else text = teams ? '🏆 السيطرة على العالم: آخر فريق يبقى يفوز' : '🏆 السيطرة على العالم: آخر دولة (أو تحالف) يبقى يفوز';
  return <div class="goal-box">{text}</div>;
}

// ---------------- الأخبار ----------------
export function NewsTab({ ctl, eng, onSelect }: PanelProps) {
  const myId = ctl.myNationId();
  const items = eng.s.news.filter((n) => !n.to || (myId && n.to.includes(myId))).slice().reverse();
  return (
    <div class="tab-body">
      <ul class="news-list">
        {items.map((n) => (
          <li key={n.id} class={`news-${n.kind} ${n.n?.includes(myId ?? '-') || n.to ? 'mine' : ''} ${n.terr ? 'clickable' : ''}`} onClick={() => n.terr && onSelect(n.terr)}>
            <span class="news-icon">{n.icon}</span>
            <span class="news-text">{n.text}</span>
            <span class="news-date">{dateStr(n.day)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export { AREA_NAMES };
