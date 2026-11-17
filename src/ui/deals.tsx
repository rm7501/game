// واجهة: نافذة الصفقة، العروض الواصلة، سوق السلاح، القروض، سباق الفضاء، والأحداث بقرارات
import { useMemo, useState } from 'preact/hooks';
import type { Controller } from '../client/controller';
import { BRANCH_DEFS, CARDS, UNITS } from '../game/defs';
import { BANK_MONTHS, BANK_RATE, NAP_MONTHS, TRIBUTE, canGive, dealScore, debtOf, loanMax, marketOffers, sideText } from '../game/deals';
import { DECISIONS, SPACE } from '../game/decisions';
import type { Engine } from '../game/engine';
import type { Deal, DealSide, DealTerm, Nation, NationId, TerrId, Units, UnitType } from '../game/types';
import { BRANCH_OF, UNIT_TYPES } from '../game/types';
import { sfx } from './audio';
import { Bar, Flag, Modal, NationTag, UnitIcon } from './bits';
import { fmtMoney, fmtNum } from './format';
import { toast } from './toast';

async function send(ctl: Controller, cmd: Parameters<Controller['send']>[0], good = sfx.good) {
  const r = await ctl.send(cmd);
  if (r.ok) {
    good();
    if (r.msg) toast({ icon: '✅', text: r.msg, kind: 'good' });
  } else toast({ icon: '⚠️', text: r.msg ?? 'ما ينفع', kind: 'bad' });
  return r.ok;
}

// ---------------- نافذة الصفقة ----------------
interface Draft { give: DealSide; get: DealSide; terms: DealTerm[]; vassal?: 'from' | 'to'; base?: { host: 'from' | 'to'; terr: TerrId }; ult: boolean }

function SideEditor({ eng, owner, side, onChange, mine, viewer }: { eng: Engine; owner: Nation; side: DealSide; onChange: (s: DealSide) => void; mine: boolean; viewer: Nation }) {
  const terrs = eng.owned(owner.id).filter((t) => t.id !== owner.capital).sort((a, b) => b.gdp - a.gdp).slice(0, 30);
  const seeCards = mine || (viewer.intel?.[owner.id] ?? 0) > eng.s.day;
  const set = (p: Partial<DealSide>) => onChange({ ...side, ...p });
  return (
    <div class="deal-side">
      <label class="deal-row">💰 فلوس (مليار)
        <input type="number" min={0} value={side.money ?? ''} placeholder="0" onInput={(e) => set({ money: Number((e.target as HTMLInputElement).value) || undefined })} />
      </label>
      {mine && <div class="muted small">عندك {fmtMoney(owner.treasury)}</div>}
      <label class="deal-row">📆 دفعة شهرية
        <input type="number" min={0} value={side.pay?.amt ?? ''} placeholder="0" onInput={(e) => { const a = Number((e.target as HTMLInputElement).value); set({ pay: a > 0 ? { amt: a, months: side.pay?.months ?? 12 } : undefined }); }} />
        <select value={side.pay?.months ?? 12} onChange={(e) => side.pay && set({ pay: { ...side.pay, months: Number((e.target as HTMLSelectElement).value) } })}>
          {[6, 12, 24, 36].map((m) => <option key={m} value={m}>{m} شهر</option>)}
        </select>
      </label>
      <div class="deal-units">
        {UNIT_TYPES.filter((k) => owner.units[k] > 0 || (side.units?.[k] ?? 0) > 0).map((k) => (
          <label key={k} class="deal-unit" title={`عندهم ${owner.units[k]}`}>
            <UnitIcon u={k} size={14} />
            <input type="number" min={0} max={owner.units[k]} value={side.units?.[k] ?? ''} placeholder="0" onInput={(e) => set({ units: { ...side.units, [k]: Math.min(owner.units[k], Number((e.target as HTMLInputElement).value) || 0) } })} />
            <span class="muted small">/{fmtNum(owner.units[k])}</span>
          </label>
        ))}
      </div>
      {terrs.length > 0 && (
        <details class="deal-terrs">
          <summary class="small">🗺️ أراضي ({side.terrs?.length ?? 0})</summary>
          {terrs.map((t) => (
            <label key={t.id} class="dev-check small">
              <input type="checkbox" checked={side.terrs?.includes(t.id) ?? false} onChange={(e) => {
                const on = (e.target as HTMLInputElement).checked;
                const cur = side.terrs ?? [];
                set({ terrs: on ? [...cur, t.id] : cur.filter((x) => x !== t.id) });
              }} /> <Flag id={t.id} size={11} /> {eng.w.name(t.id)} <span class="muted">· {fmtMoney(t.gdp)}</span>
            </label>
          ))}
        </details>
      )}
      {seeCards && owner.cards.length > 0 && (
        <div class="deal-cards">
          {owner.cards.map((c, i) => {
            const on = (side.cards ?? []).filter((x) => x === c).length > owner.cards.slice(0, i).filter((x) => x === c).length;
            return (
              <button key={i} class={`btn btn-xs ${on ? 'btn-gold' : 'btn-ghost'}`} title={CARDS[c].desc} onClick={() => {
                const cur = [...(side.cards ?? [])];
                if (on) cur.splice(cur.indexOf(c), 1); else cur.push(c);
                set({ cards: cur });
              }}>🃏 {CARDS[c].icon} {CARDS[c].name}</button>
            );
          })}
        </div>
      )}
      <label class="deal-row">🧪 نقاط بحث
        <input type="number" min={0} value={side.research ?? ''} placeholder="0" onInput={(e) => set({ research: Number((e.target as HTMLInputElement).value) || undefined })} />
      </label>
    </div>
  );
}

export function DealDialog({ ctl, eng, me, to, base, onClose }: { ctl: Controller; eng: Engine; me: Nation; to: NationId; base?: Deal; onClose: () => void }) {
  const s = eng.s;
  const O = s.nations[to];
  const r = eng.peek(me.id, to);
  const [d, setD] = useState<Draft>(() => base
    ? { give: base.get, get: base.give, terms: base.terms, vassal: base.vassal === 'from' ? 'to' : base.vassal === 'to' ? 'from' : undefined, base: base.base ? { host: base.base.host === 'from' ? 'to' : 'from', terr: base.base.terr } : undefined, ult: false }
    : { give: {}, get: {}, terms: r?.war ? ['peace'] : [], ult: false });
  const preview: Deal = { id: 0, from: me.id, to, day: s.day, give: d.give, get: d.get, terms: d.terms, vassal: d.vassal, base: d.base, ult: d.ult };
  const score = useMemo(() => (O && (O.kind === 'bot' || O.aiControl) ? dealScore(eng, preview, O) : null), [JSON.stringify(d)]);
  if (!O) return null;
  const toggle = (t: DealTerm) => setD({ ...d, terms: d.terms.includes(t) ? d.terms.filter((x) => x !== t) : [...d.terms, t] });
  const myTerrs = eng.owned(me.id).filter((t) => t.id !== me.capital);
  const theirTerrs = eng.owned(O.id).filter((t) => t.id !== O.capital);
  const err = canGive(eng, me, d.give);
  const go = async () => {
    if (await send(ctl, { t: 'deal', to, give: d.give, get: d.get, terms: d.terms, vassal: d.vassal, base: d.base, ult: d.ult, counter: base?.id }, sfx.click)) onClose();
  };
  return (
    <Modal title={<>🤝 صفقة مع <Flag id={O.home} size={16} /> {O.name}</>} onClose={onClose} wide>
      <div class="deal-grid">
        <div>
          <div class="block-title">📤 أنت تعطي</div>
          <SideEditor eng={eng} owner={me} side={d.give} onChange={(g) => setD({ ...d, give: g })} mine viewer={me} />
        </div>
        <div>
          <div class="block-title">📥 تطلب منهم</div>
          <SideEditor eng={eng} owner={O} side={d.get} onChange={(g) => setD({ ...d, get: g })} mine={false} viewer={me} />
        </div>
      </div>
      <div class="deal-terms">
        <div class="block-title">📜 بنود</div>
        <div class="dev-row-actions wrap">
          {r?.war && <button class={`btn btn-xs ${d.terms.includes('peace') ? 'btn-gold' : ''}`} onClick={() => toggle('peace')}>🕊️ سلام</button>}
          {!r?.ally && <button class={`btn btn-xs ${d.terms.includes('ally') ? 'btn-gold' : ''}`} onClick={() => toggle('ally')}>🤝 تحالف</button>}
          {!r?.trade && <button class={`btn btn-xs ${d.terms.includes('trade') ? 'btn-gold' : ''}`} onClick={() => toggle('trade')}>📦 تجارة</button>}
          {!(r?.nap && r.nap > s.day) && <button class={`btn btn-xs ${d.terms.includes('nap') ? 'btn-gold' : ''}`} onClick={() => toggle('nap')}>🛡️ عدم اعتداء ({NAP_MONTHS / 12} سنين)</button>}
          <button class={`btn btn-xs ${d.vassal === 'to' ? 'btn-gold' : ''}`} onClick={() => setD({ ...d, vassal: d.vassal === 'to' ? undefined : 'to' })}>👑 يصيرون تابعين لك</button>
          <button class={`btn btn-xs ${d.vassal === 'from' ? 'btn-gold' : ''}`} onClick={() => setD({ ...d, vassal: d.vassal === 'from' ? undefined : 'from' })}>🙇 تصير تابع لهم</button>
        </div>
        <div class="deal-base">
          <span class="small">🏰 قاعدة عسكرية:</span>
          <select value={d.base ? `${d.base.host}:${d.base.terr}` : ''} onChange={(e) => {
            const v = (e.target as HTMLSelectElement).value;
            if (!v) return setD({ ...d, base: undefined });
            const [host, terr] = v.split(':');
            setD({ ...d, base: { host: host as 'from' | 'to', terr } });
          }}>
            <option value="">بدون</option>
            <optgroup label="قاعدة لك في أرضهم">{theirTerrs.slice(0, 25).map((t) => <option key={t.id} value={`to:${t.id}`}>{eng.w.name(t.id)}</option>)}</optgroup>
            <optgroup label="قاعدة لهم في أرضك">{myTerrs.slice(0, 25).map((t) => <option key={t.id} value={`from:${t.id}`}>{eng.w.name(t.id)}</option>)}</optgroup>
          </select>
        </div>
        <label class="dev-check small"><input type="checkbox" checked={d.ult} onChange={(e) => setD({ ...d, ult: (e.target as HTMLInputElement).checked })} /> 📜 إنذار نهائي: لو رفضوا تبدأ الحرب (وهجومك أقوى 15% لـ 6 شهور)</label>
        {d.vassal && <div class="muted small">👑 الدولة التابعة تدفع {Math.round(TRIBUTE * 100)}% من دخلها كل شهر، وتصير حليفة للمتبوعة.</div>}
      </div>
      {score !== null && (
        <div class={`deal-guess ${score >= 0 ? 'good' : score > -100 ? '' : 'bad'}`}>
          {score >= 0 ? '👍 غالباً يقبلون' : score > -100 ? '🤔 ممكن يردون بعرض ثاني' : '👎 غالباً يرفضون'}
        </div>
      )}
      {err && <div class="bad small">⚠️ {err}</div>}
      <div class="modal-foot">
        <button class="btn" onClick={onClose}>إلغاء</button>
        <button class={`btn ${d.ult ? 'btn-danger' : 'btn-primary'}`} disabled={!!err} onClick={go}>{d.ult ? '📜 أرسل الإنذار' : '📨 أرسل العرض'}</button>
      </div>
    </Modal>
  );
}

/** ملخص صفقة واصلة */
export function DealCard({ ctl, eng, me, d, onCounter }: { ctl: Controller; eng: Engine; me: Nation; d: Deal; onCounter: (d: Deal) => void }) {
  const A = eng.s.nations[d.from];
  if (!A) return null;
  const give = sideText(eng, d.give);
  const get = sideText(eng, d.get);
  const termNames: Record<DealTerm, string> = { peace: '🕊️ سلام', ally: '🤝 تحالف', trade: '📦 تجارة', nap: '🛡️ عدم اعتداء' };
  const extra = [...d.terms.map((t) => termNames[t])];
  if (d.vassal) extra.push(d.vassal === 'to' ? '🙇 تصير تابع لهم' : '👑 يصيرون تابعين لك');
  if (d.base) extra.push(d.base.host === 'to' ? `🏰 يبون قاعدة في ${eng.w.name(d.base.terr)}` : `🏰 يعطونك قاعدة في ${eng.w.name(d.base.terr)}`);
  const why = canGive(eng, me, d.get);
  return (
    <div class={`deal-card ${d.ult ? 'ult' : ''}`}>
      <div class="row-between"><b><NationTag name={A.name} color={A.color} flag={A.home} /> {d.ult ? '📜 إنذار نهائي!' : 'عرض صفقة'}</b><span class="muted small">باقي {Math.max(0, (d.ult ? 30 : 60) - (eng.s.day - d.day))} يوم</span></div>
      {give.length > 0 && <div class="small">📥 تاخذ: {give.join('، ')}</div>}
      {get.length > 0 && <div class="small">📤 تعطي: {get.join('، ')}</div>}
      {extra.length > 0 && <div class="small">📜 {extra.join('، ')}</div>}
      {d.ult && <div class="small bad">لو رفضت أو تجاهلت، تبدأ الحرب!</div>}
      {why && <div class="small warn">⚠️ {why}</div>}
      <div class="dev-row-actions wrap">
        <button class="btn btn-sm btn-primary" disabled={!!why} onClick={() => send(ctl, { t: 'dealRespond', id: d.id, accept: true })}>✅ قبول</button>
        <button class="btn btn-sm" onClick={() => send(ctl, { t: 'dealRespond', id: d.id, accept: false }, sfx.click)}>❌ رفض</button>
        {!d.ult && <button class="btn btn-sm btn-ghost" onClick={() => onCounter(d)}>🔁 عرض مضاد</button>}
      </div>
    </div>
  );
}

// ---------------- سوق السلاح ----------------
export function MarketModal({ ctl, eng, me, onClose }: { ctl: Controller; eng: Engine; me: Nation; onClose: () => void }) {
  const offers = marketOffers(eng, me);
  const [qty, setQty] = useState<Record<string, number>>({});
  const [markup, setMarkup] = useState(me.exp?.markup ?? 1.3);
  return (
    <Modal title="🛒 سوق السلاح" onClose={onClose} wide>
      <p class="muted small">الدول المتخصصة تبيع أسلحتها. السلاح من جيل أعلى من جيلك يساوي وحدات أكثر عندك. الشحنة توصل عاصمتك بعد أيام.</p>
      {offers.length === 0 && <p class="muted">ما فيه عروض الحين (أو كل البائعين أعداء لك).</p>}
      <div class="market">
        {offers.map((o) => {
          const S = eng.s.nations[o.seller];
          const key = o.seller + o.u;
          const n = qty[key] ?? (o.u === 'inf' ? 10 : 3);
          const myGen = me.gen[BRANCH_OF[o.u]];
          const got = Math.max(1, Math.round(n * (1 + 0.18 * (o.gen - 1)) / (1 + 0.18 * (myGen - 1))));
          return (
            <div class="offer" key={key}>
              <div class="row-between">
                <span><Flag id={S.home} size={14} /> <b>{S.name}</b></span>
                <span class="gen-pill">جيل {o.gen}: {BRANCH_DEFS[BRANCH_OF[o.u]].gens[o.gen]}</span>
              </div>
              <div class="row-between small">
                <span><UnitIcon u={o.u} size={16} /> {UNITS[o.u].name}</span>
                <span>{fmtMoney(o.price)} للوحدة</span>
              </div>
              <div class="dev-row-actions">
                {(o.u === 'inf' ? [10, 25, 50] : [1, 3, 5, 10]).map((x) => <button key={x} class={`chip ${n === x ? 'on' : ''}`} onClick={() => setQty({ ...qty, [key]: x })}>{x}</button>)}
                <button class="btn btn-sm btn-primary" disabled={me.treasury < o.price * n} onClick={() => send(ctl, { t: 'buy', seller: o.seller, u: o.u, n }, sfx.coin)}>اشترِ · {fmtMoney(o.price * n)}</button>
              </div>
              {got !== n && <div class="small good">توصلك {got} وحدة (فرق الأجيال)</div>}
            </div>
          );
        })}
      </div>
      {me.spec.length > 0 && (
        <div class="block">
          <div class="block-title">📦 صادراتك ({me.spec.map((b) => BRANCH_DEFS[b].name).join(' و ')})</div>
          <label class="dev-check"><input type="checkbox" checked={me.exp?.open ?? true} onChange={(e) => send(ctl, { t: 'exports', open: (e.target as HTMLInputElement).checked, markup }, sfx.click)} /> أبيع أسلحتي للدول الثانية (تاخذ 60% من السعر)</label>
          <div class="row-between small"><span>هامش الربح</span><b>×{markup.toFixed(2)}</b></div>
          <input type="range" min={80} max={250} value={Math.round(markup * 100)} onInput={(e) => setMarkup(Number((e.target as HTMLInputElement).value) / 100)} onChange={() => send(ctl, { t: 'exports', open: me.exp?.open ?? true, markup }, sfx.click)} />
        </div>
      )}
    </Modal>
  );
}

// ---------------- القروض والدفعات ----------------
export function FinanceBlock({ ctl, eng, me }: { ctl: Controller; eng: Engine; me: Nation }) {
  const max = loanMax(eng, me);
  const pays = eng.s.pays.filter((p) => p.from === me.id || p.to === me.id);
  const debt = debtOf(eng, me);
  return (
    <div class="block">
      <div class="row-between"><span class="block-title">🏦 القروض والدفعات</span>{debt > 0 && <span class="small bad">ديونك {fmtMoney(debt)}</span>}</div>
      <div class="dev-row-actions wrap">
        {[0.25, 0.5, 1].map((f) => {
          const a = Math.round(max * f);
          return <button key={f} class="btn btn-sm" disabled={a < 5} onClick={() => confirm(`تاخذ قرض ${a} مليار وتسدد ${Math.round(a * (1 + BANK_RATE))} على ${BANK_MONTHS} شهر؟`) && send(ctl, { t: 'loan', amount: a }, sfx.coin)}>قرض {fmtMoney(a)}</button>;
        })}
      </div>
      <div class="muted small">البنك الدولي: فائدة {Math.round(BANK_RATE * 100)}% وتسدد على {BANK_MONTHS} شهر. تقدر بعد تسلف دول ثانية من نافذة الصفقة (فلوس الحين مقابل دفعات شهرية).</div>
      {pays.map((p) => (
        <div class="qrow small" key={p.id}>
          <span>{p.from === me.id ? '📤' : '📥'}</span>
          <span class="q-name">{p.from === me.id ? `تدفع لـ ${p.to ? eng.nname(p.to) : 'البنك الدولي'}` : `تاخذ من ${eng.nname(p.from)}`} ({p.why})</span>
          <span>{fmtMoney(p.amt)}/شهر</span>
          <span class="muted">{p.left} شهر</span>
        </div>
      ))}
      {me.lord && <div class="small">👑 أنت تابع لـ {eng.nname(me.lord)}: تدفع {Math.round(TRIBUTE * 100)}% من دخلك (≈ {fmtMoney(me.d.income * TRIBUTE)}/شهر)</div>}
      {Object.values(eng.s.nations).filter((o) => o.alive && o.lord === me.id).map((o) => <div class="small good" key={o.id}>👑 {o.name} تابعة لك وتدفع لك ≈ {fmtMoney(o.d.income * TRIBUTE)}/شهر</div>)}
    </div>
  );
}

export function SpaceBlock({ ctl, me }: { ctl: Controller; me: Nation }) {
  const next = (me.space ?? 0) + 1;
  const def = SPACE[next];
  const q = me.q.find((x) => x.type.startsWith('space:'));
  return (
    <div class="block space">
      <div class="block-title">🚀 سباق الفضاء</div>
      <div class="space-steps">
        {SPACE.slice(1).map((st, i) => <span key={i} class={`space-step ${(me.space ?? 0) > i ? 'done' : ''}`} title={st.desc}>{st.icon} {st.name}</span>)}
      </div>
      {q ? (
        <div class="row-between small"><span>{SPACE[Number(q.type.split(':')[1])].icon} قيد التنفيذ</span><Bar value={q.total - q.left} max={q.total} color="var(--accent)" /><span class="muted">{Math.ceil(q.left)} يوم</span></div>
      ) : def ? (
        <button class="btn btn-sm" disabled={me.tech < def.tech || me.treasury < def.cost} onClick={() => send(ctl, { t: 'space' }, sfx.fanfare)}>
          {me.tech < def.tech ? `🔒 ${def.name} يحتاج تكنولوجيا ${def.tech}` : `${def.icon} ${def.name} · ${fmtMoney(def.cost)} · ${Math.round(def.days / 30)} شهر · +${def.pts} نقطة`}
        </button>
      ) : <div class="good small">🏆 وصلت المريخ!</div>}
      {def && <div class="muted small">{def.desc}</div>}
    </div>
  );
}

// ---------------- الأحداث بقرارات ----------------
export function DecisionModal({ ctl, eng, me, onClose }: { ctl: Controller; eng: Engine; me: Nation; onClose: () => void }) {
  const d = me.decision;
  if (!d) return null;
  const def = DECISIONS[d.ev];
  return (
    <Modal title={`${def.icon} ${def.title}`} onClose={onClose}>
      <div class="decision">
        <div class="decision-icon">{def.icon}</div>
        <p>{def.text}</p>
        <div class="decision-opts">
          {def.opts.map((o, i) => (
            <button key={i} class="decision-opt" onClick={() => send(ctl, { t: 'decide', i }).then((ok) => ok && onClose())}>
              <b>{o.label}</b>
              <span class="muted small">{o.hint}</span>
            </button>
          ))}
        </div>
        <div class="muted small">لو ما قررت خلال {Math.max(0, d.until - eng.s.day)} يوم، الحكومة تختار الأول.</div>
      </div>
    </Modal>
  );
}

export type { Units, UnitType };
