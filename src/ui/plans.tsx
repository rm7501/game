// واجهة: بطاقات الخطط، التصويت في الأمم المتحدة، الجواسيس، الفرق
import { useState } from 'preact/hooks';
import type { Controller } from '../client/controller';
import { CARDS, HAND_MAX, SPY_OPS, TEAMS, UN_RES, agentCost } from '../game/defs';
import type { Engine } from '../game/engine';
import { missionText } from '../game/events';
import { cardTargets } from '../game/cards';
import { busyAgents, maxAgents, spyChance } from '../game/spies';
import { unText } from '../game/un';
import type { CardId, Nation, NationId, SpyOpId, Vote } from '../game/types';
import { COMBAT_UNITS } from '../game/types';
import { sfx } from './audio';
import { Flag, Modal, NationTag, UnitIcon } from './bits';
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

// ---------------- الفرق ----------------
export function TeamBadge({ team, short }: { team?: number; short?: boolean }) {
  if (!team) return null;
  const t = TEAMS[team - 1];
  if (!t) return null;
  return <span class="badge team-badge" style={{ borderColor: t.color, color: t.color }}>{t.icon}{short ? '' : ` ${t.name}`}</span>;
}

export function TeamStandings({ eng, me }: { eng: Engine; me?: Nation }) {
  if (eng.s.settings.teams <= 0) return null;
  const st = eng.teamStats().filter((t) => t.members.length).sort((a, b) => b.score - a.score);
  const total = eng.w.totalArea;
  return (
    <div class="block team-standings">
      <div class="block-title">👥 ترتيب الفرق</div>
      {st.map((t, i) => {
        const def = TEAMS[t.team - 1];
        return (
          <div class={`team-row ${me?.team === t.team ? 'me' : ''}`} key={t.team}>
            <span class="team-rank">{i + 1}</span>
            <span class="team-name" style={{ color: def.color }}>{def.icon} {def.name}</span>
            <span class="team-members">
              {t.members.map((m) => <span key={m.id} class={m.alive ? '' : 'dead'} title={`${m.name} (${m.leader})`}><Flag id={m.home} size={12} /></span>)}
            </span>
            <span class="team-score">{fmtNum(t.score)} <small class="muted">({Math.round((t.area / total) * 100)}%)</small></span>
          </div>
        );
      })}
    </div>
  );
}

// ---------------- بطاقات الخطط ----------------
export function CardsModal({ ctl, eng, me, onClose, onSelect }: { ctl: Controller; eng: Engine; me: Nation; onClose: () => void; onSelect?: (t: string) => void }) {
  const [pick, setPick] = useState<CardId | null>(null);
  const s = eng.s;
  const play = async (card: CardId, target?: NationId, terr?: string) => {
    sfx.click();
    const ok = await send(ctl, { t: 'card', card, target, terr }, sfx.fanfare);
    if (ok) {
      setPick(null);
      if (terr) onSelect?.(terr);
      if (me.cards.length <= 1) onClose();
    }
  };
  const def = pick ? CARDS[pick] : null;
  const targets = pick ? cardTargets(eng, me, pick) : null;
  return (
    <Modal title={`🃏 بطاقات الخطط (${me.cards.length}/${HAND_MAX})`} onClose={onClose} wide>
      {me.cards.length === 0 && (
        <p class="muted center">ما عندك بطاقات الحين. تاخذ بطاقة كل سنة، وبطاقتين لو حققت مهمتك السرية، وأحياناً من عجلة الحظ ومن الانتصارات.</p>
      )}
      {!pick && (
        <div class="cards-hand">
          {me.cards.map((c, i) => {
            const d = CARDS[c];
            return (
              <button key={i} class={`plan-card ${d.target ? 'targeted' : ''}`} onClick={() => (d.target ? (sfx.click(), setPick(c)) : play(c))}>
                <span class="pc-icon">{d.icon}</span>
                <span class="pc-name">{d.name}</span>
                <span class="pc-desc">{d.desc}</span>
                <span class="pc-play">{d.target ? 'اختر الهدف ←' : 'العب البطاقة'}</span>
              </button>
            );
          })}
        </div>
      )}
      {pick && def && targets && (
        <div class="card-target">
          <div class="row-between">
            <b>{def.icon} {def.name}</b>
            <button class="btn btn-sm btn-ghost" onClick={() => setPick(null)}>→ رجوع</button>
          </div>
          <p class="muted small">{def.desc}</p>
          {def.target === 'terr' ? (
            targets.terrs.length ? (
              <ul class="terr-list">
                {targets.terrs.map((id) => {
                  const t = s.terr[id];
                  const o = t.owner ? s.nations[t.owner] : null;
                  return (
                    <li key={id} onClick={() => play(pick, undefined, id)}>
                      <Flag id={id} size={14} />
                      <span class="tl-name">{eng.w.name(id)}</span>
                      <span class="tl-info">{o ? `${o.name} · استقرار ${Math.round(o.stability)}%` : 'محايدة'}</span>
                    </li>
                  );
                })}
              </ul>
            ) : <p class="warn small">ما فيه أرض مناسبة الحين: لازم تكون مجاورة لك، ومحايدة أو تابعة لدولة استقرارها أقل من 55% (أو محتلة حديثاً)، ومو عاصمة.</p>
          ) : targets.nations.length ? (
            <div class="target-list">
              {targets.nations.map((id) => {
                const o = s.nations[id];
                return (
                  <button key={id} class="target-btn" onClick={() => play(pick, id)}>
                    <NationTag name={o.name} color={o.color} flag={o.home} leader={o.leader} />
                    <span class="muted small">قوة {fmtNum(o.d.power)} · استقرار {Math.round(o.stability)}%</span>
                  </button>
                );
              })}
            </div>
          ) : (
            <p class="warn small">{def.target === 'enemy' ? 'هذي البطاقة تحتاج دولة أنت في حرب معها.' : 'ما فيه دولة مناسبة.'}</p>
          )}
        </div>
      )}
      <p class="muted small">💡 أي بطاقة تلعبها يشوفها الكل في الأخبار. أقصى عدد بيدك {HAND_MAX} بطاقات.</p>
    </Modal>
  );
}

// ---------------- الأمم المتحدة ----------------
export function UNModal({ ctl, eng, me, onClose }: { ctl: Controller; eng: Engine; me?: Nation; onClose: () => void }) {
  const s = eng.s;
  const u = s.un;
  if (!u) {
    const r = s.unLast;
    return (
      <Modal title="🏛️ الأمم المتحدة" onClose={onClose}>
        {r ? (
          <div class={`un-result ${r.passed ? 'good' : 'bad'}`}>
            <div class="un-res-name">{UN_RES[r.res].icon} {UN_RES[r.res].name}</div>
            <div class="un-verdict">{r.passed ? '✅ القرار مرّ' : '❌ القرار انرفض'}</div>
            <div class="un-tally"><span class="good">نعم {r.yes}</span> · <span class="bad">لا {r.no}</span> · <span class="muted">ممتنع {r.abst}</span></div>
            {r.text && <p>{r.text}</p>}
          </div>
        ) : <p class="muted">ما فيه تصويت الحين.</p>}
        <div class="modal-foot"><button class="btn" onClick={onClose}>تمام</button></div>
      </Modal>
    );
  }
  const def = UN_RES[u.res];
  const T = u.target ? s.nations[u.target] : undefined;
  const mine = me ? u.votes[me.id] : undefined;
  const votes = Object.entries(u.votes).filter(([id]) => s.nations[id]?.alive);
  const yes = votes.filter(([, v]) => v === 'y').length;
  const no = votes.filter(([, v]) => v === 'n').length;
  const ab = votes.filter(([, v]) => v === 'a').length;
  const total = Object.values(s.nations).filter((n) => n.alive).length;
  const vote = (v: Vote) => send(ctl, { t: 'vote', v }, sfx.click);
  return (
    <Modal title="🏛️ تصويت في الأمم المتحدة" onClose={onClose}>
      <div class="un-box">
        <div class="un-res-icon">{def.icon}</div>
        <div class="un-res-name">{def.name}</div>
        {T && <div class="un-target">ضد <NationTag name={T.name} color={T.color} flag={T.home} leader={T.leader} /></div>}
        <p>{unText(eng, u)}</p>
        <div class="un-tally">
          <span class="good">✅ نعم {yes}</span>
          <span class="bad">❌ لا {no}</span>
          <span class="muted">⚪ ممتنع {ab}</span>
          <span class="muted">⏳ ما صوتوا {total - votes.length}</span>
        </div>
        <div class="muted small">باقي {Math.max(0, u.end - s.day)} يوم على نهاية التصويت. القرار يمر لو «نعم» أكثر من «لا».</div>
        {me && (u.target === me.id ? (
          <div class="hint bad">القرار ضدك! صوتك «لا» تلقائياً. حاول تقنع الدول الثانية بالشات أو بالمساعدات 😉</div>
        ) : (
          <div class="un-vote">
            <button class={`btn ${mine === 'y' ? 'btn-primary' : ''}`} onClick={() => vote('y')}>✅ نعم</button>
            <button class={`btn ${mine === 'n' ? 'btn-danger' : ''}`} onClick={() => vote('n')}>❌ لا</button>
            <button class={`btn ${mine === 'a' ? 'on' : ''}`} onClick={() => vote('a')}>⚪ ممتنع</button>
          </div>
        ))}
        {mine && <div class="muted small center">تقدر تغير صوتك لين ينتهي التصويت</div>}
      </div>
    </Modal>
  );
}

// ---------------- الاستخبارات ----------------
export function IntelBlock({ ctl, eng, me }: { ctl: Controller; eng: Engine; me: Nation }) {
  const s = eng.s;
  const max = maxAgents(me);
  const busy = busyAgents(eng, me);
  const cost = agentCost(me.d.gdp);
  const ops = s.ops.filter((o) => o.owner === me.id);
  return (
    <div class="block intel">
      <div class="row-between">
        <span class="block-title">🕵️ الاستخبارات</span>
        <span class="muted small">جاهزين {me.agents} · بمهمة {busy} · الحد {max}</span>
      </div>
      <div class="agents">
        {Array.from({ length: max }, (_, i) => (
          <span key={i} class={`agent ${i < me.agents ? 'ready' : i < me.agents + busy ? 'busy' : 'empty'}`} title={i < me.agents ? 'جاهز' : i < me.agents + busy ? 'بمهمة' : 'فاضي'}>🕵️</span>
        ))}
        <button class="btn btn-sm" disabled={me.agents + busy >= max || me.treasury < cost} onClick={() => send(ctl, { t: 'agent' }, sfx.coin)}>
          ＋ جند جاسوس · {fmtMoney(cost)}
        </button>
      </div>
      {ops.length > 0 && ops.map((o) => (
        <div class="qrow" key={o.id}>
          <span>{SPY_OPS[o.op].icon}</span>
          <span class="q-name">{SPY_OPS[o.op].name} ← {s.nations[o.target]?.name}</span>
          <span class="muted small">{Math.max(0, o.done - s.day)} يوم</span>
        </div>
      ))}
      <div class="muted small">اضغط «🕵️ تجسس» على أي دولة تحت. ابنِ «جهاز الاستخبارات» من الاقتصاد عشان تزيد الجواسيس ونجاحهم.</div>
    </div>
  );
}

export function SpyDialog({ ctl, eng, me, target, onClose }: { ctl: Controller; eng: Engine; me: Nation; target: NationId; onClose: () => void }) {
  const s = eng.s;
  const T = s.nations[target];
  if (!T) return null;
  const running = s.ops.find((o) => o.owner === me.id && o.target === T.id);
  const go = async (op: SpyOpId) => {
    if (await send(ctl, { t: 'spy', op, target: T.id }, sfx.click)) onClose();
  };
  return (
    <Modal title={<>🕵️ عملية سرية ضد <Flag id={T.home} size={16} /> {T.name}</>} onClose={onClose}>
      <div class="muted small">جواسيسك الجاهزين: {me.agents} · خزينتك {fmtMoney(me.treasury)} · استخباراتهم مستوى {T.b.intel ?? 0}</div>
      {running && <div class="hint">⏳ عندك عملية «{SPY_OPS[running.op].name}» شغالة ضدهم، النتيجة بعد {Math.max(0, running.done - s.day)} يوم.</div>}
      <div class="spy-ops">
        {(Object.keys(SPY_OPS) as SpyOpId[]).map((op) => {
          const d = SPY_OPS[op];
          const p = spyChance(me, T, op);
          return (
            <button key={op} class="spy-op" disabled={!!running || me.agents < 1 || me.treasury < d.cost} onClick={() => go(op)}>
              <span class="so-icon">{d.icon}</span>
              <span class="so-body">
                <b>{d.name}</b>
                <span class="muted small">{d.desc}</span>
              </span>
              <span class="so-meta">
                <b class={p >= 0.6 ? 'good' : p < 0.4 ? 'bad' : ''}>{Math.round(p * 100)}%</b>
                <span class="muted small">{fmtMoney(d.cost)} · {d.days} يوم</span>
              </span>
            </button>
          );
        })}
      </div>
      <p class="muted small">⚠️ لو فشلت العملية ممكن ينمسك الجاسوس، والكل يعرف إنك تتجسس، والبوتات تحقد عليك.</p>
    </Modal>
  );
}

/** الأسرار المكشوفة عن دولة (لو عندك معلومات استخباراتية) */
export function IntelReveal({ eng, o, until }: { eng: Engine; o: Nation; until: number }) {
  return (
    <div class="intel-reveal">
      <div class="small"><b>📂 أسرار مكشوفة</b> <span class="muted">لين {eng.dateStr(until)}</span></div>
      <div class="small">🎯 {missionText(o)} {o.mission.done ? '✅' : ''}</div>
      <div class="small">🃏 {o.cards.length ? o.cards.map((c) => `${CARDS[c].icon} ${CARDS[c].name}`).join('، ') : 'ما عندها بطاقات'}</div>
      <div class="small intel-army">
        {COMBAT_UNITS.map((k) => <span key={k}><UnitIcon u={k} size={12} /> {o.units[k]}</span>)}
        {o.units.missile > 0 && <span>🚀 {o.units.missile}</span>}
        {o.units.nuke > 0 && <span>☢️ {o.units.nuke}</span>}
        <span class="muted">· 💰 {fmtMoney(o.treasury)}</span>
      </div>
    </div>
  );
}
