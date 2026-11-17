// واجهة الجيش: الأجيال والتخصص، الجنرالات، الجيوش المتمركزة، نقل القوات
import { useMemo, useState } from 'preact/hooks';
import type { Controller } from '../client/controller';
import {
  BRANCH_DEFS, GENERALS, MAX_GEN, MAX_GENERALS, MAX_SPECS, SPECS, SPEC_PROJECT, UNITS, generalCost, stars,
} from '../game/defs';
import { armies, deployDays, generalAt, stackPower, stationable, upgradeCost } from '../game/army';
import type { Engine } from '../game/engine';
import type { Branch, Nation, Stack, TerrId, Units, UnitType } from '../game/types';
import { BRANCHES } from '../game/types';
import { sfx } from './audio';
import { Bar, Flag, Modal, UnitIcon } from './bits';
import { fmtMoney, fmtNum } from './format';
import { toast } from './toast';

const LAND_AIR_SEA: UnitType[] = ['inf', 'tank', 'jet', 'ship'];

async function send(ctl: Controller, cmd: Parameters<Controller['send']>[0], good = sfx.coin) {
  const r = await ctl.send(cmd);
  if (r.ok) {
    good();
    if (r.msg) toast({ icon: '✅', text: r.msg, kind: 'good' });
  } else toast({ icon: '⚠️', text: r.msg ?? 'ما ينفع', kind: 'bad' });
  return r.ok;
}

export const Stars = ({ xp }: { xp: number }) => {
  const n = stars(xp);
  return n ? <span class="xp-stars" title={`خبرة ${Math.round(xp)}/100: قوة +${n * 5}%`}>{'⭐'.repeat(n)}</span> : null;
};

/** ملخص جيش متمركز */
export function StackLine({ st }: { st?: Stack }) {
  if (!st) return <span class="muted small">ما فيه جيش</span>;
  return (
    <span class="stack-line">
      {LAND_AIR_SEA.filter((k) => st.u[k] > 0).map((k) => (
        <span key={k}><UnitIcon u={k} size={13} /> {fmtNum(st.u[k])}</span>
      ))}
      <Stars xp={st.xp} />
    </span>
  );
}

// ---------------- الأفرع والأجيال والتخصص ----------------
export function BranchesBlock({ ctl, eng, me }: { ctl: Controller; eng: Engine; me: Nation }) {
  const [pick, setPick] = useState(false);
  const busy = (b: Branch) => me.q.find((q) => q.kind === 'project' && q.type === 'gen:' + b);
  const specBusy = me.q.find((q) => q.kind === 'project' && q.type.startsWith('spec:'));
  return (
    <div class="block branches">
      <div class="row-between">
        <span class="block-title">🔧 تطوير الأسلحة (الأجيال)</span>
        <span class="small">{me.spec.length ? me.spec.map((b) => <span class="badge good" key={b}>{BRANCH_DEFS[b].icon} تخصص {BRANCH_DEFS[b].name}</span>) : <span class="badge">{SPECS.balanced.icon} متوازن</span>}</span>
      </div>
      {BRANCHES.map((b) => {
        const def = BRANCH_DEFS[b];
        const g = me.gen[b];
        const q = busy(b);
        const { cost, days } = upgradeCost(me, b);
        const needTech = me.tech < g + 1;
        return (
          <div class={`branch ${me.spec.includes(b) ? 'spec' : ''}`} key={b}>
            <div class="row-between">
              <span><b>{def.icon} {def.name}</b> <span class="muted small">({def.units})</span></span>
              <span class="gen-pill" title={`قوة ${def.units} ×${(1 + 0.18 * (g - 1)).toFixed(2)}`}>جيل {g}: {def.gens[g]}</span>
            </div>
            <div class="gen-dots">{Array.from({ length: MAX_GEN }, (_, i) => <span key={i} class={i < g ? 'on' : ''} />)}</div>
            {q ? (
              <div class="row-between small"><span>🔧 يتطور للجيل {g + 1}...</span><Bar value={q.total - q.left} max={q.total} color="var(--accent)" /><span class="muted">{Math.ceil(q.left)} يوم</span></div>
            ) : g >= MAX_GEN ? (
              <div class="muted small">🏆 أعلى جيل</div>
            ) : (
              <button class="btn btn-sm" disabled={needTech || me.treasury < cost} onClick={() => send(ctl, { t: 'upgrade', b })}>
                {needTech ? `🔒 يحتاج تكنولوجيا ${g + 1}` : `طوّر للجيل ${g + 1} (${def.gens[g + 1]}) · ${fmtMoney(cost)} · ${days} يوم`}
              </button>
            )}
          </div>
        );
      })}
      {me.spec.length < MAX_SPECS && (
        specBusy ? (
          <div class="small">🏭 مجمع {BRANCH_DEFS[specBusy.type.split(':')[1] as Branch].name} قيد البناء · {Math.ceil(specBusy.left)} يوم</div>
        ) : pick ? (
          <div class="spec-pick">
            {BRANCHES.filter((b) => !me.spec.includes(b)).map((b) => (
              <button key={b} class="btn btn-sm" disabled={me.treasury < SPEC_PROJECT.cost} onClick={() => send(ctl, { t: 'specialize', b }).then((ok) => ok && setPick(false))}>
                {BRANCH_DEFS[b].icon} {BRANCH_DEFS[b].name}
              </button>
            ))}
            <button class="btn btn-sm btn-ghost" onClick={() => setPick(false)}>إلغاء</button>
          </div>
        ) : (
          <button class="btn btn-sm btn-ghost" onClick={() => setPick(true)}>🏭 ابنِ مجمع صناعات لتخصص جديد · {fmtMoney(SPEC_PROJECT.cost)} · سنة</button>
        )
      )}
      <div class="muted small">💡 التخصص: أسلحته أقوى 10% وأرخص 20%، وتطويره أرخص وأسرع، وتقدر تبيعها للدول الثانية.</div>
    </div>
  );
}

// ---------------- الجنرالات ----------------
export function GeneralsBlock({ ctl, eng, me, onSelect }: { ctl: Controller; eng: Engine; me: Nation; onSelect: (t: string) => void }) {
  const cost = generalCost(me.generals.length, me.d.gdp);
  const spots = [...stationable(eng, me)];
  return (
    <div class="block generals">
      <div class="row-between">
        <span class="block-title">🎖️ الجنرالات ({me.generals.length}/{MAX_GENERALS})</span>
        <button class="btn btn-sm" disabled={me.generals.length >= MAX_GENERALS || me.treasury < cost} onClick={() => send(ctl, { t: 'general', act: 'hire' }, sfx.fanfare)}>＋ عيّن جنرال · {fmtMoney(cost)}</button>
      </div>
      {me.generals.length === 0 && <div class="muted small">ما عندك جنرالات. الجنرال يقوّي الجيش اللي معه ويترقى مع الانتصارات.</div>}
      {me.generals.map((g) => (
        <div class="general" key={g.id}>
          <span class="gen-icon" title={GENERALS[g.kind].desc}>{GENERALS[g.kind].icon}</span>
          <span class="gen-body">
            <b>{g.name}</b> <span class="muted small">{GENERALS[g.kind].name} · {'★'.repeat(g.lvl)}{'☆'.repeat(5 - g.lvl)}</span>
            <span class="muted small">{GENERALS[g.kind].desc}</span>
          </span>
          {g.at ? (
            <select value={g.at} onChange={(e) => send(ctl, { t: 'general', act: 'station', id: g.id, at: (e.target as HTMLSelectElement).value }, sfx.click)}>
              {spots.map((t) => <option key={t} value={t}>{eng.w.name(t)}</option>)}
            </select>
          ) : <span class="muted small">🚚 مع جيش بالطريق</span>}
          {g.at && <button class="icon-btn" title="شوف مكانه" onClick={() => onSelect(g.at)}>📍</button>}
          <button class="icon-btn" title="تقاعد" onClick={() => confirm(`تقاعد ${g.name}؟`) && send(ctl, { t: 'general', act: 'fire', id: g.id }, sfx.click)}>✕</button>
        </div>
      ))}
    </div>
  );
}

// ---------------- الجيوش المتمركزة ----------------
export function ArmiesBlock({ eng, me, onSelect, onMove }: { eng: Engine; me: Nation; onSelect: (t: string) => void; onMove: (from: TerrId) => void }) {
  const list = armies(eng, me);
  return (
    <div class="block">
      <div class="block-title">🗺️ جيوشك المتمركزة</div>
      {list.length === 0 && <div class="muted small">ما عندك جيوش متمركزة.</div>}
      <ul class="army-list">
        {list.map((a) => (
          <li key={a.t}>
            <span class="al-name clickable" onClick={() => onSelect(a.t)}>
              <Flag id={a.t} size={13} /> {eng.w.name(a.t)} {a.t === me.capital && '★'} {a.gen && <span title={a.gen.name}>{GENERALS[a.gen.kind].icon}</span>}
            </span>
            <StackLine st={me.place[a.t]} />
            <span class="muted small">⚔️ {fmtNum(a.power)}</span>
            <button class="btn btn-xs" onClick={() => onMove(a.t)}>🚚</button>
          </li>
        ))}
      </ul>
      <div class="muted small">💡 كل أرض يدافع عنها الجيش اللي فيها (وربع جيوش الأراضي المجاورة). انقل قواتك للحدود الخطرة، وهاجم من الأرض اللي فيها جيشك.</div>
    </div>
  );
}

// ---------------- نافذة نقل القوات ----------------
export function MoveDialog({ ctl, eng, me, from, onClose }: { ctl: Controller; eng: Engine; me: Nation; from: TerrId; onClose: () => void }) {
  const st = me.place[from];
  const spots = useMemo(() => [...stationable(eng, me)].filter((t) => t !== from).sort((a, b) => eng.w.centerDist(from, a) - eng.w.centerDist(from, b)), [from, me.d.terrs]);
  const threat = (t: TerrId) => eng.w.get(t).n.some((x) => {
    const o = eng.s.terr[x]?.owner;
    return o && o !== me.id && eng.atWar(me.id, o);
  });
  const [to, setTo] = useState<TerrId>(() => spots.find(threat) ?? spots[0] ?? '');
  const [u, setU] = useState<Partial<Units>>(() => {
    const o: Partial<Units> = {};
    for (const k of LAND_AIR_SEA) o[k] = Math.floor((st?.u[k] ?? 0) * 0.5);
    return o;
  });
  const [withGen, setWithGen] = useState(false);
  if (!st) return null;
  const gen = generalAt(me, from);
  const coastal = !!to && !!eng.w.get(to).c;
  const days = to ? deployDays(eng, me, from, to, withGen ? gen : undefined) : 0;
  const go = async () => {
    const units = { ...u };
    if (!coastal) units.ship = 0;
    if (await send(ctl, { t: 'move', from, to, units, gen: withGen && !!gen }, sfx.click)) onClose();
  };
  return (
    <Modal title={<>🚚 نقل قوات من <Flag id={from} size={16} /> {eng.w.name(from)}</>} onClose={onClose}>
      <label class="dev-field">
        <span>إلى</span>
        <select value={to} onChange={(e) => setTo((e.target as HTMLSelectElement).value)}>
          {spots.map((t) => {
            const p = me.place[t] ? stackPower(me, me.place[t].u) : 0;
            return <option key={t} value={t}>{threat(t) ? '⚠️ ' : ''}{eng.w.name(t)} · ⚔️ {fmtNum(p)}</option>;
          })}
        </select>
      </label>
      <div class="move-units">
        {LAND_AIR_SEA.map((k) => {
          const max = st.u[k];
          if (!max) return null;
          const disabled = k === 'ship' && !coastal;
          return (
            <div class="mu-row" key={k}>
              <span><UnitIcon u={k} size={15} /> {UNITS[k].name}</span>
              <input type="range" min={0} max={max} value={disabled ? 0 : u[k] ?? 0} disabled={disabled} onInput={(e) => setU({ ...u, [k]: Number((e.target as HTMLInputElement).value) })} />
              <b>{disabled ? 0 : u[k] ?? 0}/{max}</b>
            </div>
          );
        })}
      </div>
      <div class="row-between small">
        <button class="btn btn-xs btn-ghost" onClick={() => { const o: Partial<Units> = {}; for (const k of LAND_AIR_SEA) o[k] = st.u[k]; setU(o); }}>الكل</button>
        <button class="btn btn-xs btn-ghost" onClick={() => { const o: Partial<Units> = {}; for (const k of LAND_AIR_SEA) o[k] = Math.floor(st.u[k] / 2); setU(o); }}>النص</button>
      </div>
      {gen && <label class="dev-check"><input type="checkbox" checked={withGen} onChange={(e) => setWithGen((e.target as HTMLInputElement).checked)} /> {GENERALS[gen.kind].icon} {gen.name} يروح معهم</label>}
      <div class="modal-foot">
        <span class="muted">⏱️ يوصلون بعد {days} يوم</span>
        <button class="btn btn-primary" disabled={!to} onClick={go}>🚚 انقل</button>
      </div>
    </Modal>
  );
}
