// شاشة اللعب الرئيسية: الخريطة + المعلومات + التبويبات
import { useEffect, useRef, useState } from 'preact/hooks';
import type { Controller } from '../client/controller';
import { DAYS_PER_MONTH, TECH_NAMES } from '../game/defs';
import { Engine, PROP_NAMES } from '../game/engine';
import type { News, Report, TerrId } from '../game/types';
import { isMuted, setMuted, sfx } from './audio';
import { Flag, Modal } from './bits';
import { AidDialog, AttackDialog, ReportModal, StrikeDialog } from './dialogs';
import { EndScreen } from './EndScreen';
import { dateStr, fmtMoneyShort, fmtNum, fmtPop } from './format';
import { FortuneModal, WorldEventModal } from './GameWheels';
import { HowTo } from './HowTo';
import { MapRenderer } from './map';
import { ChatTab, DiplomacyTab, EconomyTab, MilitaryTab, NewsTab, OverviewTab, RankTab, type Tab } from './panels';
import { TerritoryCard } from './TerritoryCard';
import { toast } from './toast';
import { CardsModal, SpyDialog, UNModal } from './plans';
import { UN_RES } from '../game/defs';

type Dialog =
  | { t: 'attack'; to: TerrId }
  | { t: 'strike'; to: TerrId; kind: 'missile' | 'nuke' }
  | { t: 'aid'; to: string }
  | { t: 'report'; id: number }
  | { t: 'dead' }
  | { t: 'howto' }
  | { t: 'fortune' }
  | { t: 'world' }
  | { t: 'cards' }
  | { t: 'un' }
  | { t: 'spy'; to: string }
  | null;

const maxId = (arr: { id: number }[]) => arr.reduce((m, x) => Math.max(m, x.id), 0);

const TABS: { id: Tab; icon: string; label: string; online?: boolean }[] = [
  { id: 'overview', icon: '🏛️', label: 'دولتي' },
  { id: 'economy', icon: '🏗️', label: 'الاقتصاد' },
  { id: 'military', icon: '⚔️', label: 'الجيش' },
  { id: 'diplo', icon: '🤝', label: 'العلاقات' },
  { id: 'chat', icon: '💬', label: 'الشات', online: true },
  { id: 'rank', icon: '🏆', label: 'الترتيب' },
  { id: 'news', icon: '📰', label: 'الأخبار' },
];

export function GameScreen({ ctl, onExit }: { ctl: Controller; onExit: () => void }) {
  const s = ctl.state;
  const eng = new Engine(ctl.world, s);
  const myId = ctl.myNationId();
  const meAny = myId ? s.nations[myId] : undefined;
  const me = meAny?.alive ? meAny : undefined;
  const wide = typeof window !== 'undefined' && window.innerWidth > 900;
  const [tab, setTab] = useState<Tab>('overview');
  const [panelOpen, setPanelOpen] = useState(wide);
  const [sel, setSel] = useState<TerrId | null>(null);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [focusNation, setFocusNation] = useState<string | null>(null);
  const [menu, setMenu] = useState(false);
  const [muted, setMutedS] = useState(isMuted());
  const [hover, setHover] = useState<{ id: string; x: number; y: number } | null>(null);
  const [unread, setUnread] = useState(0);
  const mapBox = useRef<HTMLDivElement>(null);
  const map = useRef<MapRenderer | null>(null);
  const seen = useRef({ news: maxId(s.news), reps: maxId(s.reports), props: maxId(s.props), chat: maxId(s.chat), dead: !meAny || !meAny.alive, propToast: 0, world: s.world?.id ?? 0, fortune: false, un: s.un?.id ?? 0, unLast: s.unLast?.id ?? 0 });

  useEffect(() => {
    const m = new MapRenderer(mapBox.current!, ctl.world, {
      onSelect: (id) => {
        setSel(id);
        if (id) sfx.click();
      },
      onHover: (id, x, y) => setHover(id ? { id, x, y } : null),
    });
    map.current = m;
    m.update(ctl.state, ctl.myNationId());
    const mine = ctl.myNation();
    if (mine) setTimeout(() => m.flyTo(mine.capital, undefined, 1200), 350);
    let raf = 0;
    const frame = () => {
      m.animate(ctl.state.moves, ctl.nowDay());
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);
    return () => {
      cancelAnimationFrame(raf);
      m.destroy();
      map.current = null;
    };
  }, []);

  useEffect(() => {
    map.current?.update(s, myId);
  });
  useEffect(() => {
    const m = map.current;
    if (!m) return;
    m.select(sel);
    // لو اخترت أرضك نوضح الدول اللي تقدر تهاجمها منها
    const mine = ctl.myNation();
    if (sel && mine?.alive && ctl.state.terr[sel]?.owner === mine.id) {
      const v = new Engine(ctl.world, ctl.state);
      const ids = ctl.world.get(sel).n.filter((x) => ctl.state.terr[x] && ctl.state.terr[x].owner !== mine.id && v.route(mine, x));
      m.highlight(ids, 'cand');
    } else m.highlight([], 'cand');
  }, [sel]);

  // نصيحة بالبداية
  useEffect(() => {
    if (!ctl.myNation()?.alive || ctl.state.day > 60) return;
    const t = setTimeout(() => {
      toast({ icon: '💡', text: 'اضغط على دولتك عشان تشوف الدول اللي تقدر تهاجمها، وطوّر اقتصادك وجيشك من التبويبات', kind: 'info', ttl: 9000 });
    }, 2200);
    return () => clearTimeout(t);
  }, []);

  // التنبيهات
  useEffect(() => {
    const st = seen.current;
    const myNid = ctl.myNationId();
    for (const p of s.props) {
      if (p.id <= st.props) continue;
      if (p.to === myNid) {
        const from = s.nations[p.from];
        sfx.notify();
        // اقتراح واحد بس كل شوي، والباقي في تبويب العلاقات
        if (Date.now() - st.propToast < 9000) continue;
        st.propToast = Date.now();
        toast({
          icon: '📨',
          text: `${from?.name} (${from?.leader}) ترسل لك ${PROP_NAMES[p.type]}`,
          kind: 'info',
          ttl: 20000,
          actions: [
            { label: 'قبول', kind: 'primary', run: () => ctl.send({ t: 'respond', id: p.id, accept: true }).then(() => sfx.good()) },
            { label: 'رفض', run: () => ctl.send({ t: 'respond', id: p.id, accept: false }) },
          ],
        });
      }
    }
    for (const n of s.news) {
      if (n.id <= st.news) continue;
      notifyNews(n, myNid);
    }
    for (const r of s.reports) {
      if (r.id <= st.reps) continue;
      notifyReport(r, myNid);
    }
    for (const c of s.chat) {
      if (c.id <= st.chat || c.from === myNid) continue;
      if (tab !== 'chat' || !panelOpen) {
        setUnread((x) => x + 1);
        if (c.to === myNid) toast({ icon: '💬', text: `${c.name}: ${c.text}`, kind: 'info' });
      }
    }
    st.news = maxId(s.news);
    st.reps = maxId(s.reports);
    st.props = Math.max(st.props, maxId(s.props));
    st.chat = maxId(s.chat);
    if (s.world && s.world.id > st.world) {
      st.world = s.world.id;
      setDialog({ t: 'world' });
    }
    if (s.un && s.un.id > st.un) {
      st.un = s.un.id;
      sfx.notify();
      if (!dialog && ctl.myNation()?.alive) setDialog({ t: 'un' });
      else toast({ icon: '🏛️', text: `تصويت في الأمم المتحدة: ${UN_RES[s.un.res].name}`, kind: 'info', ttl: 9000, actions: [{ label: 'صوّت', kind: 'primary', run: () => setDialog({ t: 'un' }) }] });
    }
    if (s.unLast && s.unLast.id > st.unLast) {
      st.unLast = s.unLast.id;
      const r = s.unLast;
      const againstMe = !!myNid && r.target === myNid;
      if (r.passed && againstMe) sfx.bad();
      toast({
        icon: r.passed ? '✅' : '❌',
        text: `الأمم المتحدة ${r.passed ? 'أقرت' : 'رفضت'} «${UN_RES[r.res].name}» (${r.yes} نعم، ${r.no} لا)${r.text ? ': ' + r.text : ''}`,
        kind: r.passed ? (againstMe ? 'bad' : 'good') : 'info', ttl: 9000,
      });
    }
    const mineN = ctl.myNation();
    if (mineN?.alive && s.day >= mineN.fortuneNext && !st.fortune) {
      st.fortune = true;
      toast({ icon: '🎰', text: 'عجلة الحظ صارت متاحة لك!', kind: 'good', actions: [{ label: 'لف', kind: 'primary', run: () => setDialog({ t: 'fortune' }) }] });
    } else if (mineN && s.day < mineN.fortuneNext) st.fortune = false;
    if (!st.dead && meAny && !meAny.alive) {
      st.dead = true;
      sfx.bad();
      setDialog({ t: 'dead' });
    }
  });

  useEffect(() => {
    if (tab === 'chat' && panelOpen) setUnread(0);
  }, [tab, panelOpen]);

  function notifyNews(n: News, myNid?: string) {
    const mineNews = !!myNid && ((n.to?.includes(myNid) ?? false) || (n.n?.includes(myNid) ?? false));
    if (n.kind === 'nuke' && n.icon === '☢️' && n.terr) {
      sfx.nuke();
      toast({ icon: '☢️', text: n.text, kind: 'bad', ttl: 7000 });
      return;
    }
    if (n.kind === 'battle' && mineNews && (n.icon === '⚔️' || n.icon === '🛡️' || n.icon === '🏴')) {
      // بداية معركة ضدك: تنبيه. الباقي يطلع مع تقرير المعركة
      if (n.icon === '⚔️' && n.n?.[0] !== myNid) {
        sfx.alert();
        toast({ icon: '⚔️', text: n.text, kind: 'warn', ttl: 7000, actions: n.terr ? [{ label: 'شوف', run: () => focus(n.terr!) }] : undefined });
      }
      return;
    }
    if (n.icon === '⚠️' && mineNews) {
      sfx.alert();
      toast({ icon: '⚠️', text: n.text, kind: 'warn', ttl: 8000, actions: n.terr ? [{ label: 'شوف', run: () => focus(n.terr!) }] : undefined });
      return;
    }
    if (n.kind === 'diplo' && n.text.includes('ترسل لك')) return; // يطلع مع الاقتراح
    if (n.icon === '🃏' && n.n?.[0] === myNid) return; // بطاقتك: يطلع لك تأكيد اللعب
    if (mineNews) {
      if (n.kind === 'battle' && n.icon === '🏴') return; // يطلع مع تقرير المعركة
      toast({ icon: n.icon, text: n.text, kind: n.kind === 'war' ? 'warn' : 'info' });
      if (n.kind === 'war') sfx.alert();
      else sfx.notify();
    } else if (n.icon === '💀' || n.kind === 'system' || n.kind === 'join') {
      toast({ icon: n.icon, text: n.text, kind: 'info' });
    }
  }

  function notifyReport(r: Report, myNid?: string) {
    map.current?.explode(r.terr, r.kind);
    const involved = r.att === myNid || r.def === myNid;
    if (!involved) return;
    sfx.boom();
    const iWon = (r.att === myNid && r.win) || (r.def === myNid && !r.win);
    const place = ctl.world.name(r.terr);
    let text: string;
    if (r.kind === 'battle') {
      if (r.att === myNid) text = r.win ? `انتصرت واحتليت ${place}! 🎉` : `هجومك على ${place} فشل`;
      else text = r.win ? `خسرت ${place} 😢` : `صديت الهجوم على ${place} 💪`;
    } else if (r.kind === 'missile') text = r.att === myNid ? `صواريخك ضربت ${place} (${r.hits} إصابة)` : `صواريخ ضربت ${place}!`;
    else text = r.att === myNid ? `قنبلتك النووية ${r.hits ? 'ضربت' : 'انعترضت فوق'} ${place}` : `ضربة نووية على ${place}!`;
    setTimeout(() => (iWon ? sfx.good() : sfx.bad()), 450);
    toast({ icon: r.kind === 'battle' ? (iWon ? '🏆' : '💥') : r.kind === 'nuke' ? '☢️' : '🚀', text, kind: iWon ? 'good' : 'bad', ttl: 7000, actions: [{ label: 'التفاصيل', run: () => setDialog({ t: 'report', id: r.id }) }] });
  }

  const focus = (id: TerrId) => {
    setSel(id);
    map.current?.flyTo(id);
    if (!wide) setPanelOpen(false);
  };

  const openTab = (t: Tab) => {
    if (tab === t && panelOpen && !wide) setPanelOpen(false);
    else {
      setTab(t);
      setPanelOpen(true);
    }
  };

  const panelProps = {
    ctl, eng, me, onSelect: focus,
    onAid: (to: string) => setDialog({ t: 'aid', to }),
    onSpy: (to: string) => setDialog({ t: 'spy', to }),
    onCards: () => setDialog({ t: 'cards' }),
    openTab, focusNation,
  };

  const isHost = ctl.isHost();
  const peaceEnd = me ? Math.max(0, ...Object.values(s.nations).filter((n) => n.alive && n.id !== me.id).map((n) => eng.peaceEnd(me, n))) : 0;
  const inPeace = me && s.day < s.settings.peaceMonths * DAYS_PER_MONTH;
  const net = me ? me.d.income - me.d.upkeep : 0;
  const rep = dialog?.t === 'report' ? s.reports.find((r) => r.id === dialog.id) : undefined;
  const hoverT = hover ? s.terr[hover.id] : undefined;
  const hoverOwner = hoverT?.owner ? s.nations[hoverT.owner] : undefined;
  const tabs = TABS.filter((t) => !t.online || s.mode === 'online');
  const lastNews = s.news.filter((n) => !n.to).slice(-1)[0];

  return (
    <div class={`game ${panelOpen ? 'panel-open' : ''}`}>
      <header class="hud">
        <div class="hud-nation" onClick={() => openTab('overview')}>
          {meAny ? <Flag id={meAny.home} size={22} /> : <span>👁️</span>}
          <div class="hud-nname">
            <b style={{ color: meAny?.color }}>{meAny?.name ?? 'متفرج'}</b>
            <span class="muted small">{dateStr(s.day)}</span>
          </div>
        </div>
        {me && (
          <div class="hud-stats">
            {s.day >= me.fortuneNext ? (
              <button class="chip-stat fortune-ready" title="عجلة الحظ متاحة!" onClick={() => setDialog({ t: 'fortune' })}>🎰 لف الحظ</button>
            ) : (
              <span class="chip-stat muted" title="عجلة الحظ">🎰 {Math.max(1, Math.ceil((me.fortuneNext - s.day) / 30))} شهر</span>
            )}
            {s.un && (
              <button class={`chip-stat un-chip ${s.un.votes[me.id] ? '' : 'pulse'}`} title="تصويت في الأمم المتحدة" onClick={() => setDialog({ t: 'un' })}>🏛️ <span class="un-long">تصويت</span></button>
            )}
            <button class={`chip-stat cards-chip ${me.cards.length ? '' : 'muted'}`} title="بطاقات الخطط" onClick={() => setDialog({ t: 'cards' })}>🃏 {me.cards.length}</button>
            <span class="chip-stat" title="الخزينة (والدخل الصافي الشهري)">💰 {fmtMoneyShort(me.treasury)} <small class={net >= 0 ? 'good' : 'bad'}>{net >= 0 ? '+' : ''}{fmtMoneyShort(net)}</small></span>
            <span class="chip-stat" title="السكان">👥 {fmtPop(me.d.pop)}</span>
            <span class="chip-stat" title="القوة العسكرية">⚔️ {fmtNum(me.d.power)}</span>
            <span class="chip-stat" title="التكنولوجيا">🧪 {me.tech} <small>{TECH_NAMES[me.tech]}</small></span>
            <span class={`chip-stat ${me.stability < 30 ? 'bad' : ''}`} title="الاستقرار">⚖️ {Math.round(me.stability)}%</span>
            <span class="chip-stat" title="الدول (والمناطق)">🗺️ {me.d.countries}{me.d.terrs > me.d.countries ? <small> ({me.d.terrs})</small> : null}</span>
          </div>
        )}
        <div class="hud-time">
          <span class="chip-stat date-chip">{dateStr(s.day)}</span>
          {inPeace && <span class="chip-stat peace" title="فترة السلام: ما أحد يقدر يهاجم دولة لاعب أو بوت">🕊️ <span class="peace-long">سلام لين</span> {dateStr(peaceEnd)}</span>}
          {ctl.status !== 'ok' && <span class="chip-stat bad">{ctl.status === 'connecting' ? '🔄 يتصل...' : '📴 مفصول'}</span>}
          {isHost ? (
            <span class="speed">
              <button class={`icon-btn ${s.paused ? 'on' : ''}`} title={s.paused ? 'كمل' : 'إيقاف مؤقت'} onClick={() => ctl.send({ t: 'pause', paused: !s.paused })}>
                {s.paused ? '▶️' : '⏸️'}
              </button>
              {[1, 2, 4].map((x) => (
                <button key={x} class={`icon-btn ${s.speed === x && !s.paused ? 'on' : ''}`} onClick={async () => { await ctl.send({ t: 'speed', speed: x }); if (ctl.state.paused) await ctl.send({ t: 'pause', paused: false }); }}>
                  ×{x}
                </button>
              ))}
            </span>
          ) : (
            <span class="chip-stat">{s.paused ? '⏸️ متوقفة' : `▶️ ×${s.speed}`}</span>
          )}
          <button class="icon-btn" onClick={() => setMenu(true)} aria-label="القائمة">☰</button>
        </div>
      </header>

      <div class="map-wrap">
        <div class="map-box" ref={mapBox} />
        <div class="map-ctrls">
          <button class="icon-btn" onClick={() => map.current?.zoomBy(1.6)} aria-label="تكبير">＋</button>
          <button class="icon-btn" onClick={() => map.current?.zoomBy(1 / 1.6)} aria-label="تصغير">－</button>
          {me && <button class="icon-btn" title="دولتي" onClick={() => focus(me.capital)}>🎯</button>}
          <button class="icon-btn" title="العالم" onClick={() => map.current?.resetView()}>🌍</button>
        </div>
        {hover && hoverT && wide && (
          <div class="map-tip" style={{ left: hover.x + 14, top: hover.y + 14 }}>
            <Flag id={hover.id} size={12} /> {ctl.world.name(hover.id)}
            <span class="muted"> · {hoverOwner ? hoverOwner.name : 'محايدة'}</span>
          </div>
        )}
        {lastNews && (
          <div class="ticker" onClick={() => openTab('news')}>
            <span>{lastNews.icon}</span> {lastNews.text}
          </div>
        )}
        {s.paused && s.phase === 'playing' && (
          <div class="paused-banner">
            ⏸️ اللعبة متوقفة
            {isHost && <button class="btn btn-sm btn-gold" onClick={() => ctl.send({ t: 'pause', paused: false })}>كمل ▶️</button>}
          </div>
        )}
        {sel && (
          <TerritoryCard
            eng={eng} me={me} id={sel}
            onClose={() => setSel(null)}
            onAttack={() => setDialog({ t: 'attack', to: sel })}
            onStrike={(kind) => setDialog({ t: 'strike', to: sel, kind })}
            onDiplo={(nid) => {
              setFocusNation(nid);
              setTab('diplo');
              setPanelOpen(true);
            }}
            onDefect={() => ctl.send({ t: 'card', card: 'defect', terr: sel }).then((r) => {
              if (r.ok) { sfx.fanfare(); toast({ icon: '🏳️', text: r.msg ?? 'انضمت لك!', kind: 'good' }); }
              else toast({ icon: '⚠️', text: r.msg ?? 'ما ينفع', kind: 'bad' });
            })}
          />
        )}
      </div>

      <aside class="panel">
        <nav class="tabs">
          {tabs.map((t) => (
            <button key={t.id} class={`tab ${tab === t.id && panelOpen ? 'on' : ''}`} onClick={() => openTab(t.id)}>
              <span class="tab-icon">{t.icon}</span>
              <span class="tab-label">{t.label}</span>
              {t.id === 'diplo' && me && s.props.some((p) => p.to === me.id) && <span class="tab-dot" />}
              {t.id === 'chat' && unread > 0 && <span class="tab-dot">{unread}</span>}
            </button>
          ))}
          {wide && (
            <button class="tab collapse" onClick={() => setPanelOpen(!panelOpen)} title="إخفاء اللوحة">
              {panelOpen ? '⇥' : '⇤'}
            </button>
          )}
        </nav>
        {panelOpen && (
          <div class="panel-content">
            {!wide && (
              <div class="sheet-handle" onClick={() => setPanelOpen(false)}>
                <span />
              </div>
            )}
            {tab === 'overview' && <OverviewTab {...panelProps} />}
            {tab === 'economy' && <EconomyTab {...panelProps} />}
            {tab === 'military' && <MilitaryTab {...panelProps} />}
            {tab === 'diplo' && <DiplomacyTab {...panelProps} />}
            {tab === 'chat' && <ChatTab {...panelProps} />}
            {tab === 'rank' && <RankTab {...panelProps} />}
            {tab === 'news' && <NewsTab {...panelProps} />}
          </div>
        )}
      </aside>

      {dialog?.t === 'attack' && me && <AttackDialog ctl={ctl} eng={eng} me={me} to={dialog.to} onClose={() => setDialog(null)} />}
      {dialog?.t === 'strike' && me && <StrikeDialog ctl={ctl} eng={eng} me={me} to={dialog.to} kind={dialog.kind} onClose={() => setDialog(null)} />}
      {dialog?.t === 'aid' && me && <AidDialog ctl={ctl} eng={eng} me={me} to={dialog.to} onClose={() => setDialog(null)} />}
      {rep && <ReportModal eng={eng} rep={rep} myId={myId} onClose={() => setDialog(null)} />}
      {dialog?.t === 'howto' && <HowTo onClose={() => setDialog(null)} />}
      {dialog?.t === 'fortune' && me && <FortuneModal ctl={ctl} eng={eng} me={me} onClose={() => setDialog(null)} />}
      {dialog?.t === 'world' && s.world && <WorldEventModal key={s.world.id} ev={s.world.ev} text={s.world.text} onClose={() => setDialog(null)} />}
      {dialog?.t === 'cards' && me && <CardsModal ctl={ctl} eng={eng} me={me} onClose={() => setDialog(null)} onSelect={focus} />}
      {dialog?.t === 'un' && <UNModal ctl={ctl} eng={eng} me={me} onClose={() => setDialog(null)} />}
      {dialog?.t === 'spy' && me && <SpyDialog ctl={ctl} eng={eng} me={me} target={dialog.to} onClose={() => setDialog(null)} />}
      {dialog?.t === 'dead' && (
        <Modal title="💀 دولتك سقطت" onClose={() => setDialog(null)}>
          <p>للأسف تم احتلال كل أراضيك. تقدر تكمل تتفرج على اللعبة وتشوف مين بيفوز.</p>
          <div class="modal-foot">
            <button class="btn" onClick={() => setDialog(null)}>أتفرج 👁️</button>
            <button class="btn btn-primary" onClick={onExit}>القائمة الرئيسية</button>
          </div>
        </Modal>
      )}
      {menu && (
        <Modal title="القائمة" onClose={() => setMenu(false)}>
          <div class="menu-list">
            <button class="btn" onClick={() => { setMuted(!muted); setMutedS(!muted); }}>{muted ? '🔇 الصوت مقفل' : '🔊 الصوت شغال'}</button>
            <button class="btn" onClick={() => { setMenu(false); setDialog({ t: 'howto' }); }}>📖 طريقة اللعب</button>
            {s.mode === 'online' && ctl.roomCode && (
              <button class="btn" onClick={() => { navigator.clipboard?.writeText(`${location.origin}${location.pathname}?room=${ctl.roomCode}`); toast({ icon: '🔗', text: 'نسخت رابط الغرفة', kind: 'good' }); }}>
                🔗 نسخ رابط الغرفة ({ctl.roomCode})
              </button>
            )}
            <button class="btn btn-danger" onClick={() => { setMenu(false); onExit(); }}>
              {s.mode === 'single' ? '💾 حفظ وخروج' : '🚪 مغادرة الغرفة'}
            </button>
          </div>
        </Modal>
      )}
      {s.phase === 'ended' && <EndScreen ctl={ctl} eng={eng} onExit={onExit} />}
    </div>
  );
}
