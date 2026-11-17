// لوحة المتحكم: منفصلة عن واجهة اللعبة، تطلع بس للي مفعّل وضع المتحكم
import { useMemo, useState } from 'preact/hooks';
import type { Controller } from '../../client/controller';
import {
  AREA_SLICES, BRANCH_DEFS, CARDS, FORTUNE_SLICES, FORTUNES, GOVS, LEADERS, MISSIONS, RESOURCES, STATIC_SLICES, TECH_NAMES, TERRAINS, UN_RES,
  UNITS, WHEELS, WORLD_EVENTS, type Slice,
} from '../../game/defs';
import { activeWheels, isController } from '../../game/dev';
import { Engine } from '../../game/engine';
import { missionText } from '../../game/events';
import type {
  CardId, DevCmd, FortuneId, GovId, LeaderId, MissionId, Nation, NationField, Personality, RelKind, ResId, TerrainId, UNResId, UnitType,
  Vote, WheelId, WorldEventId,
} from '../../game/types';
import { BRANCHES, UNIT_TYPES, WHEEL_ORDER } from '../../game/types';
import { sfx } from '../audio';
import { Flag, UnitIcon } from '../bits';
import { describe } from '../describe';
import { fmtMoney, fmtNum } from '../format';
import { toast } from '../toast';

type DevTab = 'wheels' | 'rig' | 'nations' | 'map' | 'events' | 'rel' | 'time' | 'luck' | 'general';

export function useDev(ctl: Controller) {
  return async (d: DevCmd, quiet = false) => {
    const r = await ctl.send({ t: 'dev', d });
    if (!r.ok) toast({ icon: '⚠️', text: r.msg ?? 'ما ينفع', kind: 'bad' });
    else {
      if (!quiet) sfx.click();
      if (r.msg) toast({ icon: '🛠️', text: r.msg, kind: 'good', ttl: 2500 });
    }
    return r.ok;
  };
}

/** زر المتحكم العائم + اللوحة (للشاشات اللي ما فيها مكان للزر) */
export function DevFab({ ctl, sel }: { ctl: Controller; sel?: string | null }) {
  const [open, setOpen] = useState(false);
  if (!isController(ctl.state, ctl.me)) return null;
  return (
    <>
      <button class={`dev-fab ${open ? 'on' : ''}`} title="لوحة المتحكم" onClick={() => setOpen(!open)}>🛠️</button>
      {open && <DevPanel ctl={ctl} sel={sel} onClose={() => setOpen(false)} withFab />}
    </>
  );
}

/** شارة تبين للاعبين إن فيه متحكم في الغرفة */
export function DevBadge({ ctl }: { ctl: Controller }) {
  const s = ctl.state;
  if (!s.dev || s.mode !== 'online') return null;
  const name = s.players[s.dev.by]?.name ?? 'صاحب الغرفة';
  return <span class="chip-stat dev-badge" title={`${name} يقدر يتحكم بالعجلات والحظ والدول`}>🛠️ <span class="dev-badge-long">فيه متحكم:</span> {name}</span>;
}

export function DevPanel({ ctl, sel, onClose, withFab }: { ctl: Controller; sel?: string | null; onClose: () => void; withFab?: boolean }) {
  const s = ctl.state;
  const playing = s.phase === 'playing' || s.phase === 'ended';
  const tabs: { id: DevTab; label: string }[] = playing
    ? [
        { id: 'nations', label: '🏳️ الدول' },
        { id: 'map', label: '🗺️ الأراضي' },
        { id: 'events', label: '🌍 الأحداث' },
        { id: 'rel', label: '🤝 العلاقات' },
        { id: 'luck', label: '🎲 الحظ' },
        { id: 'time', label: '⏱️ الوقت' },
        { id: 'general', label: '⚙️' },
      ]
    : [
        { id: 'wheels', label: '🎡 العجلات' },
        { id: 'rig', label: '🎯 النتايج والدول' },
        { id: 'luck', label: '🎲 الحظ' },
        { id: 'general', label: '⚙️' },
      ];
  const [tab, setTab] = useState<DevTab>(tabs[0].id);
  const cur = tabs.some((t) => t.id === tab) ? tab : tabs[0].id;
  return (
    <div class={`dev-panel ${withFab ? 'with-fab' : ''}`} role="dialog">
      <div class="dev-head">
        <b>🛠️ لوحة المتحكم</b>
        <button class="icon-btn" onClick={onClose} aria-label="إغلاق">✕</button>
      </div>
      <nav class="dev-tabs">
        {tabs.map((t) => (
          <button key={t.id} class={`dev-tab ${cur === t.id ? 'on' : ''}`} onClick={() => setTab(t.id)}>{t.label}</button>
        ))}
      </nav>
      <div class="dev-body">
        {cur === 'wheels' && <WheelsTab ctl={ctl} />}
        {cur === 'rig' && <RigTab ctl={ctl} />}
        {cur === 'luck' && <LuckTab ctl={ctl} />}
        {cur === 'nations' && <NationsTab ctl={ctl} />}
        {cur === 'map' && <MapTab ctl={ctl} sel={sel} />}
        {cur === 'events' && <EventsTab ctl={ctl} />}
        {cur === 'rel' && <RelTab ctl={ctl} />}
        {cur === 'time' && <TimeTab ctl={ctl} />}
        {cur === 'general' && <GeneralTab ctl={ctl} />}
      </div>
    </div>
  );
}

// ---------------- أدوات ----------------
const MULTS = [0, 0.5, 1, 2, 5, 10];

function wheelSlices(w: WheelId): Slice[] {
  if (w === 'area') return AREA_SLICES;
  return STATIC_SLICES[w] ?? [];
}

function sliceLabel(sl: Slice) {
  return `${sl.icon ?? ''} ${sl.label}`.trim();
}

/** المشاركين في العجلات (قبل ما تتكون الدول) */
function participants(ctl: Controller): { id: string; name: string }[] {
  const s = ctl.state;
  if (s.phase === 'lobby') {
    const ps = Object.values(s.players).filter((p) => !p.gm).map((p) => ({ id: p.nation, name: `👤 ${p.name}` }));
    for (let i = 1; i <= s.settings.bots; i++) ps.push({ id: `B${i}`, name: `🤖 بوت ${i}` });
    return ps;
  }
  return Object.keys(s.wheels).map((id) => {
    const p = Object.values(s.players).find((x) => x.nation === id);
    return { id, name: p ? `👤 ${p.name}` : `🤖 بوت ${id.slice(1)}` };
  });
}

function NationSelect({ ctl, value, onChange, allowNone, label }: { ctl: Controller; value: string; onChange: (v: string) => void; allowNone?: string; label?: string }) {
  const s = ctl.state;
  const list = Object.values(s.nations).filter((n) => n.alive).sort((a, b) => b.d.score - a.d.score);
  return (
    <label class="dev-field">
      {label && <span>{label}</span>}
      <select value={value} onChange={(e) => onChange((e.target as HTMLSelectElement).value)}>
        {allowNone !== undefined && <option value="">{allowNone}</option>}
        {list.map((n) => (
          <option key={n.id} value={n.id}>{n.kind === 'bot' ? '🤖' : '👤'} {n.name} ({n.leader})</option>
        ))}
      </select>
    </label>
  );
}

function useNation(ctl: Controller): [Nation | undefined, string, (v: string) => void] {
  const s = ctl.state;
  const mine = ctl.myNationId();
  const first = (mine && s.nations[mine]?.alive ? mine : Object.values(s.nations).find((n) => n.alive)?.id) ?? '';
  const [id, setId] = useState(first);
  const nid = s.nations[id]?.alive ? id : first;
  return [s.nations[nid], nid, setId];
}

// ---------------- العجلات ----------------
function WheelsTab({ ctl }: { ctl: Controller }) {
  const s = ctl.state;
  const dev = useDev(ctl);
  const off = s.dev?.off ?? {};
  const [open, setOpen] = useState<WheelId | null>(null);
  const respins = Object.values(s.wheels)[0]?.respins ?? 1;
  return (
    <div class="dev-sec">
      <p class="muted small">شغّل أو اقفل أي عجلة. العجلة المقفلة ما تطلع للاعبين وتنلف تلقائياً. وتقدر تغيّر أوزان شرائحها (احتمال كل نتيجة).</p>
      {WHEEL_ORDER.map((w) => {
        const sl = wheelSlices(w);
        const wm = s.dev?.wm?.[w] ?? {};
        return (
          <div class={`dev-wheel ${off[w] ? 'off' : ''}`} key={w}>
            <div class="row-between">
              <span>{WHEELS[w].icon} {WHEELS[w].title.replace('عجلة ', '')}</span>
              <span class="dev-row-actions">
                {sl.length > 0 && <button class="btn btn-xs btn-ghost" onClick={() => setOpen(open === w ? null : w)}>⚖️ الأوزان{Object.keys(wm).length ? ' •' : ''}</button>}
                <button class={`btn btn-xs ${off[w] ? 'btn-danger' : 'btn-primary'}`} onClick={() => dev({ a: 'wheelOff', wheel: w, off: !off[w] })}>
                  {off[w] ? '🔒 مقفلة' : '✅ شغالة'}
                </button>
              </span>
            </div>
            {open === w && <WeightsEditor ctl={ctl} wheel={w} slices={sl} />}
          </div>
        );
      })}
      <div class="dev-box">
        <div class="row-between">
          <span>🔄 إعادات اللف لكل لاعب</span>
          <span class="dev-row-actions">
            {[0, 1, 3, 10, 99].map((n) => (
              <button key={n} class={`btn btn-xs ${respins === n ? 'btn-gold' : ''}`} disabled={s.phase === 'lobby'} onClick={() => dev({ a: 'respins', n })}>{n === 99 ? '∞' : n}</button>
            ))}
          </span>
        </div>
        {s.phase === 'lobby' && <div class="muted small">تقدر تغيرها بعد ما تبدأ العجلات</div>}
      </div>
      {s.phase === 'wheels' && (
        <button class="btn btn-gold" onClick={() => dev({ a: 'finishWheels' })}>⏩ خلّص العجلات للكل وابدأ اللعبة</button>
      )}
    </div>
  );
}

function WeightsEditor({ ctl, wheel, slices }: { ctl: Controller; wheel: string; slices: Slice[] }) {
  const s = ctl.state;
  const dev = useDev(ctl);
  const wm = s.dev?.wm?.[wheel] ?? {};
  const total = slices.reduce((a, sl) => a + sl.w * (wm[String(sl.v)] ?? 1), 0) || 1;
  return (
    <div class="dev-weights">
      {slices.map((sl) => {
        const m = wm[String(sl.v)] ?? 1;
        return (
          <div class="dev-weight" key={String(sl.v)}>
            <span class="dw-name">{sliceLabel(sl)}</span>
            <span class="dw-pct muted small">{Math.round(((sl.w * m) / total) * 100)}%</span>
            <span class="dw-btns">
              {MULTS.map((x) => (
                <button key={x} class={`btn btn-xs ${m === x ? 'btn-gold' : ''}`} onClick={() => dev({ a: 'weight', wheel, v: String(sl.v), m: x }, true)} title={x === 0 ? 'ما تطلع أبداً' : `×${x}`}>
                  {x === 0 ? '🚫' : `×${x}`}
                </button>
              ))}
            </span>
          </div>
        );
      })}
      <button class="btn btn-xs btn-ghost" onClick={() => dev({ a: 'weightsReset', wheel })}>↩️ رجّع الأوزان الأصلية</button>
    </div>
  );
}

// ---------------- النتايج والدول ----------------
function RigTab({ ctl }: { ctl: Controller }) {
  const s = ctl.state;
  const dev = useDev(ctl);
  const list = participants(ctl);
  const [who, setWho] = useState(list[0]?.id ?? '');
  const [q, setQ] = useState('');
  const id = list.some((x) => x.id === who) ? who : list[0]?.id ?? '';
  if (!id) return <p class="muted">ما فيه لاعبين.</p>;
  const rig = s.dev?.rig?.[id] ?? {};
  const ws = s.wheels[id];
  const countries = [...ctl.world.countries.values()].filter((c) => c.p).sort((a, b) => b.area - a.area);
  const takenBy = (c: string) => s.taken[c];
  const shown = countries.filter((c) => !q || c.ar.includes(q) || c.en.toLowerCase().includes(q.toLowerCase())).slice(0, 60);
  const nameOf = (nid: string) => list.find((x) => x.id === nid)?.name ?? nid;
  return (
    <div class="dev-sec">
      <label class="dev-field">
        <span>اللاعب</span>
        <select value={id} onChange={(e) => setWho((e.target as HTMLSelectElement).value)}>
          {list.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </label>
      <p class="muted small">ثبّت نتيجة أي عجلة لهذا اللاعب. لو العجلة انلفت، النتيجة تتغير على طول. العجلة تنلف عادي قدامه وتوقف على اللي اخترته 😉</p>
      <div class="dev-box">
        <div class="block-title">📍 الدولة</div>
        <div class="small">
          {rig.country ? <>🎯 مثبتة: <Flag id={String(rig.country)} size={13} /> {ctl.world.country(String(rig.country)).ar} <button class="btn btn-xs btn-ghost" onClick={() => dev({ a: 'rig', nid: id, wheel: 'country', v: null })}>✕ إلغاء</button></> : '🎲 عشوائية حسب المساحة'}
          {ws?.res.country && <span class="muted"> · الحالية: {ctl.world.country(String(ws.res.country)).ar}</span>}
        </div>
        <input class="dev-search" placeholder="🔎 دوّر على دولة..." value={q} onInput={(e) => setQ((e.target as HTMLInputElement).value)} />
        <ul class="dev-list">
          {shown.map((c) => {
            const t = takenBy(c.id);
            const other = !!t && t !== id;
            const pick = () => {
              if (other && !confirm(`${c.ar} مع ${nameOf(t)}. تبدّلها؟ (هو ياخذ دولة هذا اللاعب أو تنلف له دولة ثانية)`)) return;
              dev({ a: 'rig', nid: id, wheel: 'country', v: c.id });
            };
            return (
              <li key={c.id} class={rig.country === c.id ? 'on' : ''} onClick={pick}>
                <Flag id={c.id} size={13} />
                <span class="tl-name">{c.ar}</span>
                <span class="muted small">{AREA_SLICES[c.cls]?.label}{c.provs.length > 1 ? ` · ${c.provs.length} مناطق` : ''}</span>
                {other && <span class="muted small">🔄 مع {nameOf(t)}</span>}
                {t === id && <span class="small good">✓</span>}
              </li>
            );
          })}
        </ul>
      </div>
      {WHEEL_ORDER.filter((w) => w !== 'country').map((w) => {
        const sl = wheelSlices(w);
        const v = rig[w];
        const curRes = ws?.res[w];
        return (
          <label class="dev-field" key={w}>
            <span>{WHEELS[w].icon} {WHEELS[w].title.replace('عجلة ', '')}{curRes !== undefined && <small class="muted"> (الحالية: {describe(w, curRes, ctl.world).title})</small>}</span>
            <select value={v === undefined ? '' : String(v)} onChange={(e) => {
              const raw = (e.target as HTMLSelectElement).value;
              const val = raw === '' ? null : typeof sl[0]?.v === 'number' ? Number(raw) : raw;
              dev({ a: 'rig', nid: id, wheel: w, v: val });
            }}>
              <option value="">🎲 عشوائي</option>
              {sl.map((x) => <option key={String(x.v)} value={String(x.v)}>{sliceLabel(x)}</option>)}
            </select>
          </label>
        );
      })}
    </div>
  );
}

// ---------------- الحظ ----------------
function LuckTab({ ctl }: { ctl: Controller }) {
  const s = ctl.state;
  const dev = useDev(ctl);
  const noise = s.dev?.noise ?? 0.08;
  const [open, setOpen] = useState(false);
  return (
    <div class="dev-sec">
      <div class="dev-box">
        <div class="block-title">🎰 عجلة الحظ داخل اللعبة (لكل الدول)</div>
        <p class="muted small">غيّر احتمال كل نتيجة. 🚫 = ما تطلع أبداً.</p>
        <button class="btn btn-xs" onClick={() => setOpen(!open)}>{open ? 'إخفاء' : '⚖️ الأوزان'}</button>
        {open && <WeightsEditor ctl={ctl} wheel="fortune" slices={FORTUNE_SLICES} />}
      </div>
      <div class="dev-box">
        <div class="row-between"><span class="block-title">⚔️ حظ المعارك اليومي</span><b>±{Math.round(noise * 100)}%</b></div>
        <input type="range" min={0} max={60} value={Math.round(noise * 100)} onChange={(e) => dev({ a: 'noise', x: Number((e.target as HTMLInputElement).value) / 100 }, true)} />
        <div class="muted small">0% = الأقوى يفوز دايماً · 8% = العادي · 60% = فوضى كاملة</div>
      </div>
      {s.phase !== 'playing' && <p class="muted small">💡 بعد ما تبدأ اللعبة تقدر تختار نتيجة عجلة الحظ لدولة معينة من تبويب «الأحداث»، وتقوّي أي دولة في المعارك من تبويب «الدول».</p>}
    </div>
  );
}

// ---------------- الدول ----------------
function NationsTab({ ctl }: { ctl: Controller }) {
  const s = ctl.state;
  const dev = useDev(ctl);
  const [n, nid, setId] = useNation(ctl);
  const eng = useMemo(() => new Engine(ctl.world, s), [s]);
  const [money, setMoney] = useState('');
  if (!n) return <p class="muted">ما فيه دول.</p>;
  const set = (f: NationField, v: number | string) => dev({ a: 'nation', nid, f, v }, true);
  const god = s.dev?.god?.[nid] ?? 1;
  return (
    <div class="dev-sec">
      <NationSelect ctl={ctl} value={nid} onChange={setId} />
      <div class="dev-stats small">
        <span>💰 {fmtMoney(n.treasury)}</span><span>⚔️ {fmtNum(n.d.power)}</span><span>🗺️ {n.d.terrs}</span><span>🏆 {fmtNum(n.d.score)}</span>
      </div>
      <div class="dev-box">
        <div class="block-title">💰 الخزينة</div>
        <div class="dev-row-actions wrap">
          {[100, 1000, 10000].map((x) => <button key={x} class="btn btn-xs" onClick={() => set('treasury', n.treasury + x)}>+{fmtNum(x)}</button>)}
          <button class="btn btn-xs" onClick={() => set('treasury', n.treasury * 2)}>×2</button>
          <button class="btn btn-xs btn-ghost" onClick={() => set('treasury', 0)}>صفّر</button>
          <input class="dev-num" type="number" placeholder="رقم" value={money} onInput={(e) => setMoney((e.target as HTMLInputElement).value)} />
          <button class="btn btn-xs btn-primary" disabled={money === ''} onClick={() => { set('treasury', Number(money)); setMoney(''); }}>حط</button>
        </div>
      </div>
      <div class="dev-box">
        <div class="block-title">🪖 الجيش</div>
        {UNIT_TYPES.map((u: UnitType) => (
          <div class="dev-unit" key={u}>
            <span><UnitIcon u={u} size={14} /> {UNITS[u].name}</span>
            <span class="dev-row-actions">
              <button class="btn btn-xs btn-ghost" onClick={() => dev({ a: 'units', nid, u, d: -10 }, true)}>-10</button>
              <button class="btn btn-xs btn-ghost" onClick={() => dev({ a: 'units', nid, u, d: -1 }, true)}>-1</button>
              <b class="dev-count">{n.units[u]}</b>
              <button class="btn btn-xs" onClick={() => dev({ a: 'units', nid, u, d: 1 }, true)}>+1</button>
              <button class="btn btn-xs" onClick={() => dev({ a: 'units', nid, u, d: 10 }, true)}>+10</button>
              <button class="btn btn-xs" onClick={() => dev({ a: 'units', nid, u, d: 100 }, true)}>+100</button>
            </span>
          </div>
        ))}
      </div>
      <div class="dev-box">
        <div class="row-between"><span class="block-title">⚖️ الاستقرار</span><b>{Math.round(n.stability)}%</b></div>
        <input type="range" min={0} max={100} value={Math.round(n.stability)} onChange={(e) => set('stability', Number((e.target as HTMLInputElement).value))} />
        <div class="block-title">🧪 التكنولوجيا</div>
        <div class="dev-row-actions wrap">
          {[1, 2, 3, 4, 5, 6].map((t) => <button key={t} class={`btn btn-xs ${n.tech === t ? 'btn-gold' : ''}`} title={TECH_NAMES[t]} onClick={() => set('tech', t)}>{t}</button>)}
        </div>
        <div class="block-title">🔧 أجيال الأسلحة</div>
        {BRANCHES.map((b) => (
          <div class="dev-unit" key={b}>
            <span>{BRANCH_DEFS[b].icon} {BRANCH_DEFS[b].name}</span>
            <span class="dev-row-actions">
              {[1, 2, 3, 4, 5].map((g) => <button key={g} class={`btn btn-xs ${n.gen[b] === g ? 'btn-gold' : ''}`} onClick={() => dev({ a: 'gen', nid, b, v: g }, true)}>{g}</button>)}
            </span>
          </div>
        ))}
        <div class="row-between small"><span>🎖️ الجنرالات: <b>{n.generals.length}</b></span><button class="btn btn-xs" onClick={() => dev({ a: 'addGeneral', nid })}>＋ جنرال</button></div>
        <div class="block-title">💪 قوة المعارك</div>
        <div class="dev-row-actions wrap">
          {[0.25, 0.5, 1, 2, 5, 10].map((m) => <button key={m} class={`btn btn-xs ${god === m ? 'btn-gold' : ''}`} onClick={() => dev({ a: 'god', nid, m }, true)}>×{m}</button>)}
        </div>
        <div class="muted small">يضرب قوة هجومها ودفاعها في كل معركة</div>
      </div>
      <div class="dev-box">
        <Pick label="🏛️ نظام الحكم" value={n.gov} items={Object.entries(GOVS).map(([k, v]) => [k, `${v.icon} ${v.name}`])} onPick={(v) => set('gov', v as GovId)} />
        <Pick label="⛏️ الموارد" value={n.res} items={Object.entries(RESOURCES).map(([k, v]) => [k, `${v.icon} ${v.name}`])} onPick={(v) => set('res', v as ResId)} />
        <Pick label="🧭 القائد" value={n.trait} items={Object.entries(LEADERS).map(([k, v]) => [k, `${v.icon} ${v.name}`])} onPick={(v) => set('trait', v as LeaderId)} />
        <Pick label="🏔️ التضاريس" value={n.terrain} items={Object.entries(TERRAINS).map(([k, v]) => [k, `${v.icon} ${v.name}`])} onPick={(v) => set('terrain', v as TerrainId)} />
        {n.ai && (
          <Pick label="🤖 شخصية البوت" value={n.ai.pers} items={[['aggressive', '😠 عدواني'], ['balanced', '⚖️ متوازن'], ['economic', '💼 اقتصادي'], ['defensive', '🛡️ دفاعي']]} onPick={(v) => dev({ a: 'pers', nid, pers: v as Personality })} />
        )}
      </div>
      <div class="dev-box">
        <div class="block-title">🎯 المهمة السرية</div>
        <div class="small">{missionText(n)} {n.mission.done ? '✅' : ''}</div>
        <Pick label="غيّرها" value={n.mission.id} items={Object.entries(MISSIONS).map(([k, v]) => [k, `${v.icon} ${v.name}`])} onPick={(v) => dev({ a: 'mission', nid, id: v as MissionId })} />
        {!n.mission.done && <button class="btn btn-xs" onClick={() => dev({ a: 'mission', nid, done: true })}>✅ حققها له (تنحسب أول الشهر)</button>}
      </div>
      <div class="dev-box">
        <div class="block-title">🃏 البطاقات ({n.cards.length})</div>
        <div class="dev-row-actions wrap">
          {n.cards.map((c, i) => <button key={i} class="btn btn-xs" title="شيلها" onClick={() => dev({ a: 'card', nid, card: c, remove: true }, true)}>{CARDS[c].icon} {CARDS[c].name} ✕</button>)}
        </div>
        <div class="dev-row-actions wrap">
          {(Object.keys(CARDS) as CardId[]).map((c) => <button key={c} class="btn btn-xs btn-ghost" title={CARDS[c].desc} onClick={() => dev({ a: 'card', nid, card: c })}>＋{CARDS[c].icon}</button>)}
        </div>
        <div class="row-between small"><span>🕵️ الجواسيس: <b>{n.agents}</b></span>
          <span class="dev-row-actions"><button class="btn btn-xs btn-ghost" onClick={() => set('agents', n.agents - 1)}>-1</button><button class="btn btn-xs" onClick={() => set('agents', n.agents + 1)}>+1</button></span>
        </div>
      </div>
      <div class="dev-box">
        <RenameRow name={n.name} onSave={(v) => set('name', v)} />
        <div class="muted small">أسرارها: 🃏 {n.cards.map((c) => CARDS[c].icon).join(' ') || 'ما عندها بطاقات'} · 🗺️ {eng.owned(nid).length} أراضي</div>
        <button class="btn btn-xs btn-danger" onClick={() => confirm(`تسقط ${n.name}؟ كل أراضيها تصير محايدة`) && dev({ a: 'kill', nid })}>💀 أسقط الدولة</button>
      </div>
    </div>
  );
}

function Pick({ label, value, items, onPick }: { label: string; value: string; items: [string, string][]; onPick: (v: string) => void }) {
  return (
    <label class="dev-field">
      <span>{label}</span>
      <select value={value} onChange={(e) => onPick((e.target as HTMLSelectElement).value)}>
        {items.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
      </select>
    </label>
  );
}

function RenameRow({ name, onSave }: { name: string; onSave: (v: string) => void }) {
  const [v, setV] = useState(name);
  return (
    <div class="dev-row-actions">
      <input class="dev-search" value={v} maxLength={24} onInput={(e) => setV((e.target as HTMLInputElement).value)} />
      <button class="btn btn-xs" disabled={!v.trim() || v === name} onClick={() => onSave(v)}>✏️ غيّر الاسم</button>
    </div>
  );
}

// ---------------- الأراضي ----------------
function MapTab({ ctl, sel }: { ctl: Controller; sel?: string | null }) {
  const s = ctl.state;
  const dev = useDev(ctl);
  const [to, setTo] = useState(ctl.myNationId() ?? '');
  const [whole, setWhole] = useState(false);
  const t = sel ? s.terr[sel] : undefined;
  const owner = t?.owner ? s.nations[t.owner] : undefined;
  const meta = sel ? ctl.world.byId.get(sel) : undefined;
  return (
    <div class="dev-sec">
      <p class="muted small">اضغط على أي أرض في الخريطة، وبعدين اختر لمين تصير.</p>
      {t && meta ? (
        <div class="dev-box">
          <div class="row-between">
            <b><Flag id={sel!} size={16} /> {ctl.world.name(sel!)}</b>
            <span class="muted small">{owner ? owner.name : 'محايدة'}</span>
          </div>
          <NationSelect ctl={ctl} value={to} onChange={setTo} allowNone="🏳️ تصير محايدة" label="تصير لـ" />
          {meta.par && (
            <label class="dev-check"><input type="checkbox" checked={whole} onChange={(e) => setWhole((e.target as HTMLInputElement).checked)} /> الدولة كاملة ({ctl.world.country(meta.par).provs.length} مناطق)</label>
          )}
          <button class="btn btn-primary" onClick={() => dev({ a: 'terr', terr: sel!, owner: to, whole })}>🏳️ نفّذ</button>
        </div>
      ) : (
        <div class="dev-box muted">👆 ما اخترت أرض</div>
      )}
    </div>
  );
}

// ---------------- الأحداث ----------------
function EventsTab({ ctl }: { ctl: Controller }) {
  const s = ctl.state;
  const dev = useDev(ctl);
  const [n, nid, setId] = useNation(ctl);
  const [fres, setFres] = useState<string>('');
  const fortuneRig = s.dev?.fortune?.[nid];
  return (
    <div class="dev-sec">
      <div class="dev-box">
        <div class="block-title">🌍 حدث عالمي الحين</div>
        <div class="dev-grid">
          {(Object.keys(WORLD_EVENTS) as WorldEventId[]).map((ev) => (
            <button key={ev} class="btn btn-xs" title={WORLD_EVENTS[ev].desc} onClick={() => dev({ a: 'world', ev })}>{WORLD_EVENTS[ev].icon} {WORLD_EVENTS[ev].name}</button>
          ))}
        </div>
      </div>
      <div class="dev-box">
        <div class="block-title">🏛️ الأمم المتحدة</div>
        <div class="dev-grid">
          {(Object.keys(UN_RES) as UNResId[]).map((r) => (
            <button key={r} class="btn btn-xs" onClick={() => dev({ a: 'un', res: r })}>{UN_RES[r].icon} {UN_RES[r].name}</button>
          ))}
        </div>
        {s.un && (
          <>
            <div class="small">التصويت الحالي: <b>{UN_RES[s.un.res].name}</b> · باقي {Math.max(0, s.un.end - s.day)} يوم</div>
            <ul class="dev-votes">
              {Object.values(s.nations).filter((x) => x.alive).map((x) => (
                <li key={x.id}>
                  <span>{x.name}</span>
                  <span class="dev-row-actions">
                    {(['y', 'n', 'a'] as Vote[]).map((v) => (
                      <button key={v} class={`btn btn-xs ${s.un!.votes[x.id] === v ? 'btn-gold' : 'btn-ghost'}`} onClick={() => dev({ a: 'unVote', nid: x.id, v }, true)}>{v === 'y' ? '✅' : v === 'n' ? '❌' : '⚪'}</button>
                    ))}
                  </span>
                </li>
              ))}
            </ul>
            <button class="btn btn-xs btn-primary" onClick={() => dev({ a: 'unClose' })}>⏹️ أنهِ التصويت الحين</button>
          </>
        )}
      </div>
      <div class="dev-box">
        <div class="block-title">🎰 عجلة الحظ لدولة</div>
        <NationSelect ctl={ctl} value={nid} onChange={setId} />
        <label class="dev-field">
          <span>النتيجة</span>
          <select value={fres} onChange={(e) => setFres((e.target as HTMLSelectElement).value)}>
            <option value="">🎲 عشوائية (بس خلها متاحة الحين)</option>
            {(Object.keys(FORTUNES) as FortuneId[]).map((f) => <option key={f} value={f}>{FORTUNES[f].icon} {FORTUNES[f].name}</option>)}
          </select>
        </label>
        <button class="btn btn-xs btn-primary" onClick={() => dev({ a: 'fortune', nid, res: (fres || null) as FortuneId | null })}>🎰 جهّزها</button>
        {fortuneRig && n && <div class="small">🎯 عجلة {n.name} الجاية: {FORTUNES[fortuneRig].icon} {FORTUNES[fortuneRig].name}</div>}
      </div>
      <div class="dev-box dev-row-actions wrap">
        <button class="btn btn-xs" onClick={() => dev({ a: 'deal' })}>🃏 وزّع بطاقة على الكل</button>
        <button class="btn btn-xs" onClick={() => dev({ a: 'addBot' })}>🤖 أضف بوت جديد</button>
        <button class="btn btn-xs" onClick={() => dev({ a: 'peaceAll' })}>🕊️ أوقف كل الحروب</button>
      </div>
    </div>
  );
}

// ---------------- العلاقات ----------------
function RelTab({ ctl }: { ctl: Controller }) {
  const s = ctl.state;
  const dev = useDev(ctl);
  const alive = Object.values(s.nations).filter((n) => n.alive);
  const [x, setX] = useState(alive[0]?.id ?? '');
  const [y, setY] = useState(alive[1]?.id ?? '');
  const eng = new Engine(ctl.world, s);
  const r = x && y ? eng.peek(x, y) : undefined;
  const acts: [RelKind, string][] = [['war', '⚔️ حرب'], ['peace', '🕊️ سلام'], ['ally', '🤝 تحالف'], ['trade', '📦 تجارة'], ['none', '✖ ولا شي']];
  return (
    <div class="dev-sec">
      <NationSelect ctl={ctl} value={x} onChange={setX} label="الدولة الأولى" />
      <NationSelect ctl={ctl} value={y} onChange={setY} label="الدولة الثانية" />
      <div class="small">الحالية: {r?.war ? '⚔️ حرب' : ''} {r?.ally ? (r.team ? '👥 فريق' : '🤝 حلفاء') : ''} {r?.trade ? '📦 تجارة' : ''} {r?.truce && r.truce > s.day ? '🕊️ هدنة' : ''} {!r?.war && !r?.ally && !r?.trade ? 'ما فيه علاقة' : ''}</div>
      <div class="dev-row-actions wrap">
        {acts.map(([k, l]) => <button key={k} class={`btn btn-xs ${k === 'war' ? 'btn-danger' : ''}`} disabled={!x || !y || x === y} onClick={() => dev({ a: 'rel', x, y, r: k })}>{l}</button>)}
      </div>
    </div>
  );
}

// ---------------- الوقت ----------------
function TimeTab({ ctl }: { ctl: Controller }) {
  const s = ctl.state;
  const dev = useDev(ctl);
  const [winner, setWinner] = useState('');
  return (
    <div class="dev-sec">
      <div class="dev-box">
        <div class="block-title">⏩ السرعة</div>
        <div class="dev-row-actions wrap">
          <button class={`btn btn-xs ${s.paused ? 'btn-gold' : ''}`} onClick={() => ctl.send({ t: 'pause', paused: !s.paused })}>{s.paused ? '▶️ كمّل' : '⏸️ وقف'}</button>
          {[0.5, 1, 2, 4, 8, 16, 32].map((x) => <button key={x} class={`btn btn-xs ${s.speed === x ? 'btn-gold' : ''}`} onClick={() => dev({ a: 'speed', x }, true)}>×{x}</button>)}
        </div>
      </div>
      <div class="dev-box">
        <div class="block-title">⏭️ قدّم الوقت</div>
        <div class="dev-row-actions wrap">
          {[[1, 'شهر'], [6, '6 شهور'], [12, 'سنة'], [60, '5 سنين']].map(([m, l]) => (
            <button key={m} class="btn btn-xs" disabled={s.phase !== 'playing'} onClick={() => dev({ a: 'skip', months: m as number })}>+{l}</button>
          ))}
        </div>
      </div>
      {s.settings.win === 'score' && (
        <div class="dev-box">
          <div class="row-between"><span class="block-title">⌛ مدة اللعبة</span><b>{s.settings.years} سنة</b></div>
          <div class="dev-row-actions wrap">
            {[-5, -1, 1, 5].map((d) => <button key={d} class="btn btn-xs" onClick={() => dev({ a: 'years', d })}>{d > 0 ? '+' : ''}{d}</button>)}
          </div>
        </div>
      )}
      <div class="dev-box">
        <div class="block-title">🏁 أنهِ اللعبة الحين</div>
        <NationSelect ctl={ctl} value={winner} onChange={setWinner} allowNone="🏆 صاحب أعلى نقاط" label="الفايز" />
        <button class="btn btn-xs btn-danger" disabled={s.phase !== 'playing'} onClick={() => confirm('تنهي اللعبة الحين؟') && dev({ a: 'end', winner: winner || undefined })}>🏁 أنهِ اللعبة</button>
      </div>
    </div>
  );
}

// ---------------- عام ----------------
function GeneralTab({ ctl }: { ctl: Controller }) {
  const s = ctl.state;
  const dev = useDev(ctl);
  const me = s.players[ctl.me];
  const on = activeWheels(s).length;
  return (
    <div class="dev-sec">
      <div class="dev-box">
        <b>🛠️ أنت المتحكم في هذي اللعبة</b>
        <div class="muted small">
          {s.mode === 'online' ? 'اللاعبين يشوفون شارة «فيه متحكم». ' : ''}العجلات الشغالة {on} من {WHEEL_ORDER.length}. كل اللي تسويه هنا يتطبق على طول عند الكل.
        </div>
      </div>
      {s.phase === 'lobby' && (
        <div class="dev-box">
          <div class="block-title">دورك</div>
          <div class="dev-row-actions wrap">
            <button class={`btn btn-xs ${!me?.gm ? 'btn-gold' : ''}`} onClick={() => dev({ a: 'gm', on: false })}>🎮 ألعب بدولة وأتحكم</button>
            <button class={`btn btn-xs ${me?.gm ? 'btn-gold' : ''}`} onClick={() => dev({ a: 'gm', on: true })}>👁️ أدير بس (بدون دولة)</button>
          </div>
        </div>
      )}
      <button class="btn btn-danger btn-sm" onClick={() => confirm('تقفل وضع المتحكم؟') && dev({ a: 'enable', on: false })}>🔒 اقفل وضع المتحكم</button>
    </div>
  );
}
