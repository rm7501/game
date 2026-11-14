// شاشة نهاية اللعبة
import { useEffect } from 'preact/hooks';
import type { Controller } from '../client/controller';
import type { Engine } from '../game/engine';
import { sfx } from './audio';
import { Flag, NationTag } from './bits';
import { dateStr, fmtNum } from './format';

export function EndScreen({ ctl, eng, onExit }: { ctl: Controller; eng: Engine; onExit: () => void }) {
  const s = eng.s;
  const w = s.winner;
  const myId = ctl.myNationId();
  const won = !!myId && !!w?.nations.includes(myId);
  const ranking = Object.values(s.nations).sort((a, b) => Number(b.alive) - Number(a.alive) || b.d.score - a.d.score);
  useEffect(() => {
    if (won) sfx.fanfare();
    else sfx.bad();
  }, []);
  return (
    <div class="end-back">
      <div class="end-card">
        <div class="end-emoji">{won ? '🏆' : myId ? '🎖️' : '🏁'}</div>
        <h2>{won ? 'مبروك! فزت 🎉' : 'انتهت اللعبة'}</h2>
        {w && (
          <p class="end-winner">
            {w.nations.map((id) => {
              const n = s.nations[id];
              return n ? <span key={id} class="end-w"><Flag id={n.home} size={20} /> <b style={{ color: n.color }}>{n.name}</b> ({n.leader})</span> : null;
            })}
            <br />
            <span class="muted">{w.reason} · {dateStr(w.day)}</span>
          </p>
        )}
        <table class="rank-table">
          <thead>
            <tr><th>#</th><th>الدولة</th><th>النقاط</th><th>الأراضي</th><th>معارك</th></tr>
          </thead>
          <tbody>
            {ranking.slice(0, 12).map((n, i) => (
              <tr key={n.id} class={`${n.id === myId ? 'me' : ''} ${n.alive ? '' : 'dead'}`}>
                <td>{n.alive ? i + 1 : '💀'}</td>
                <td><NationTag name={n.name} color={n.color} flag={n.home} /> <span class="muted small">{n.leader}</span></td>
                <td>{fmtNum(n.d.score)}</td>
                <td>{n.d.terrs}</td>
                <td>{n.st.won}✓ {n.st.lost}✗</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div class="modal-foot">
          <button class="btn btn-gold btn-big" onClick={onExit}>🏠 القائمة الرئيسية</button>
        </div>
      </div>
    </div>
  );
}
