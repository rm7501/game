// محاكاة بدون واجهة: بوتات فقط، للتأكد من التوازن وعدم وجود أخطاء
import { readFileSync } from 'node:fs';
import { Engine, newState, DEFAULT_SETTINGS } from '../src/game/engine';
import { World } from '../src/game/world';

const world = new World(JSON.parse(readFileSync('public/data/world.json', 'utf8')));
const years = Number(process.argv[2] ?? 25);
const bots = Number(process.argv[3] ?? 12);
const seed = Number(process.argv[4] ?? 42);
const teams = Number(process.argv[5] ?? 0);
const st = newState('single', { ...DEFAULT_SETTINGS, bots, years, win: 'score', teams }, 'host', seed);
const e = new Engine(world, st);
const counts: Record<string, number> = {};
const bump = (k: string) => (counts[k] = (counts[k] ?? 0) + 1);
e.onNews = (n) => {
  if (n.text.includes('لعبت بطاقة')) bump('بطاقات ملعوبة');
  if (n.text.includes('القبض على جاسوس')) bump('جواسيس انمسكوا');
  if (n.icon === '🕵️' && n.to && n.text.startsWith('🕵️') === false && !n.text.includes('القبض')) bump('عمليات تجسس');
  if (n.text.includes('الأمم المتحدة أقرت')) bump('قرارات أممية ✅');
  if (n.text.includes('الأمم المتحدة رفضت')) bump('قرارات أممية ❌');
  if (n.text.includes('انشقت')) bump('انشقاق');
  if (n.text.includes('انقلاب في')) bump('انقلاب');
  if (n.text.startsWith('صفقة بين')) bump('صفقات');
  if (n.text.includes('رضخت لإنذار')) bump('إنذار مقبول');
  if (n.text.includes('رفضت إنذار')) bump('إنذار مرفوض');
  if (n.icon === '🛒') bump('شراء سلاح');
  if (n.text.includes('صارت دولة تابعة')) bump('تبعية');
  if (n.text.includes('عدم اعتداء')) bump('عدم اعتداء');
  if (n.text.includes('🚀 ') && n.text.includes('نجحت في')) bump('فضاء');
  if (n.icon === '🪦') bump('جنرال سقط');
  if (n.icon === '🎖️') bump('ترقية جنرال');
};
e.addPlayer('me', 'تجربة');
e.startWheels();
e.autospin('P1');
e.finishWheels();
const me = st.nations['P1'];
me.kind = 'bot'; me.ai = { pers: 'balanced', next: 5 }; // نخلي اللاعب بوت للتجربة
const t0 = Date.now();
const leaders: string[] = [];
const fmt = (x: number) => (x >= 1000 ? (x / 1000).toFixed(1) + 'T' : x.toFixed(0));
for (let y = 0; y < years && st.phase === 'playing'; y++) {
  for (let d = 0; d < 360 && st.phase === 'playing'; d++) e.dayTick();
  {
    const alive0 = Object.values(st.nations).filter((n) => n.alive);
    const wars = Object.values(st.rel).filter((r) => r.war).length;
    const sc = alive0.map((n) => n.d.score).sort((a, b) => b - a);
    const lead = alive0.sort((a, b) => b.d.score - a.d.score)[0];
    console.log(`سنة ${2027 + y}: محايدة ${Object.values(st.terr).filter((t) => t.owner === '').length} | دول ${alive0.length} | حروب ${wars} | معارك جارية ${st.battles.length} | أكبر دولة ${Math.max(...alive0.map((n) => n.d.terrs))} | المتصدر ${lead.name} ×${(sc[0] / Math.max(1, sc[1])).toFixed(2)} | حدث ${st.world?.ev ?? '-'} | تحالف ضد ${st.coalition ? st.nations[st.coalition].name : '-'} | مهمات ${Object.values(st.nations).filter((n) => n.mission.done).length}`);
    leaders.push(lead.name);
    if (y % 5 === 4) console.log(`   المتصدر: أراضي ${lead.d.terrs} استقرار ${lead.stability.toFixed(0)} دخل ${lead.d.income.toFixed(0)} صيانة ${lead.d.upkeep.toFixed(0)} قوة ${lead.d.power.toFixed(0)} | الثاني قوة ${alive0[1]?.d.power.toFixed(0)}`);
  }
  if (y % 8 === 7) {
    const alive = Object.values(st.nations).filter((n) => n.alive).sort((a, b) => b.d.score - a.d.score);
    const neutral = Object.values(st.terr).filter((t) => t.owner === '').length;
    console.log(`\n== سنة ${2026 + y + 1} | دول حية ${alive.length} | محايدة ${neutral} | حركات ${st.moves.length}`);
    for (const n of alive.slice(0, 8)) {
      console.log(`${n.name.padEnd(14)} ${n.ai?.pers?.padEnd(10)} أراضي:${String(n.d.terrs).padStart(3)} ناتج:${fmt(n.d.gdp).padStart(6)} دخل:${n.d.income.toFixed(1).padStart(6)} صيانة:${n.d.upkeep.toFixed(1).padStart(5)} خزينة:${fmt(n.treasury).padStart(6)} قوة:${n.d.power.toFixed(0).padStart(6)} تك:${n.tech} استقرار:${n.stability.toFixed(0)} نقاط:${n.d.score} حروب:${n.d.atWar}`);
    }
  }
}
const bad = Object.values(st.nations).filter((n) => !Number.isFinite(n.treasury) || !Number.isFinite(n.d.score) || Object.values(n.units).some((u) => u < 0 || !Number.isFinite(u)));
console.log('\nأخطاء أرقام:', bad.map((n) => n.name));
console.log('مرحلة:', st.phase, st.winner ? JSON.stringify(st.winner) : '');
console.log("معارك:", Object.values(st.nations).reduce((a, n) => a + n.st.won + n.st.lost, 0), "حروب حالية:", Object.values(st.rel).filter((r) => r.war).length, "تحالفات:", Object.values(st.rel).filter((r) => r.ally).length, "تجارة:", Object.values(st.rel).filter((r) => r.trade).length, 'أخبار:', st.news.length, 'وقت:', Date.now() - t0, 'ms');
console.log('المتصدرين عبر السنين:', [...new Set(leaders)].join(' ← '), '| تغير المتصدر', leaders.filter((l, i) => i && l !== leaders[i - 1]).length, 'مرات');
console.log('حجم الحالة JSON:', Math.round(JSON.stringify(st).length / 1024), 'KB', '| بدون السجل:', Math.round(JSON.stringify({ ...st, hist: undefined }).length / 1024), 'KB', '| إطارات السجل:', st.hist?.f.length, 'أحداث:', st.hist?.ev.length);
console.log('إحصائيات:', JSON.stringify(counts));
if (teams) console.log('الفرق:', JSON.stringify(e.teamStats().map((t) => ({ t: t.team, score: t.score, alive: t.alive, n: t.members.map((m) => m.name) }))));
console.log('آخر قرار أممي:', JSON.stringify(st.unLast));
console.log('الجيوش:', Object.values(st.nations).filter((n) => n.alive).map((n) => `${n.name}: أجيال ${n.gen.land}/${n.gen.air}/${n.gen.sea}/${n.gen.rocket} تخصص ${n.spec.join('+') || '-'} جنرالات ${n.generals.length} مواقع ${Object.keys(n.place).length}/${n.d.terrs} نجوم ${Math.max(0, ...Object.values(n.place).map((x) => Math.floor(x.xp / 20)))}`).join('\n  '));
console.log('بطاقات بالأيدي:', Object.values(st.nations).filter((n) => n.alive).map((n) => n.cards.length).join(','), '| جواسيس:', Object.values(st.nations).filter((n) => n.alive).map((n) => n.agents + '/' + (1 + n.b.intel)).join(','));
console.log(st.news.slice(-12).map((n) => n.icon + ' ' + n.text).join('\n'));
