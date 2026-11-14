// مكونات صغيرة مشتركة
import type { ComponentChildren } from 'preact';
import type { UnitType } from '../game/types';
import { UNITS } from '../game/defs';

export function Flag({ id, size = 20, class: cls = '' }: { id: string; size?: number; class?: string }) {
  if (!id) return <span class={`flag flag-neutral ${cls}`} style={{ width: size * 1.33, height: size }} />;
  return <img class={`flag ${cls}`} src={`./flags/${id}.svg`} width={Math.round(size * 1.33)} height={size} alt="" loading="lazy" draggable={false} />;
}

export function TankIcon({ size = 18 }: { size?: number }) {
  return (
    <svg class="ico-tank" width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path fill="currentColor" d="M3 15h18a2 2 0 0 1 0 4H3a2 2 0 0 1 0-4zm2-4h11l2 3H4l1-3zm3-3h6v3H8zm6 1h8v1.4h-8z" />
      <circle cx="6" cy="17" r="1" fill="#0b1020" />
      <circle cx="10" cy="17" r="1" fill="#0b1020" />
      <circle cx="14" cy="17" r="1" fill="#0b1020" />
      <circle cx="18" cy="17" r="1" fill="#0b1020" />
    </svg>
  );
}

export function UnitIcon({ u, size = 18 }: { u: UnitType; size?: number }) {
  if (u === 'tank') return <TankIcon size={size} />;
  return <span class="emoji" style={{ fontSize: size * 0.9 }}>{UNITS[u].icon}</span>;
}

export function Bar({ value, max = 1, color }: { value: number; max?: number; color?: string }) {
  const p = Math.max(0, Math.min(1, value / max));
  return (
    <div class="bar">
      <div class="bar-fill" style={{ width: `${p * 100}%`, background: color }} />
    </div>
  );
}

export function Modal({ title, onClose, children, wide }: { title?: ComponentChildren; onClose: () => void; children: ComponentChildren; wide?: boolean }) {
  return (
    <div class="modal-back" onClick={onClose}>
      <div class={`modal ${wide ? 'modal-wide' : ''}`} onClick={(e) => e.stopPropagation()} role="dialog">
        <div class="modal-head">
          <div class="modal-title">{title}</div>
          <button class="icon-btn" onClick={onClose} aria-label="إغلاق">✕</button>
        </div>
        <div class="modal-body">{children}</div>
      </div>
    </div>
  );
}

export function Stat({ icon, label, value, sub, tone }: { icon: ComponentChildren; label: string; value: ComponentChildren; sub?: ComponentChildren; tone?: 'good' | 'bad' }) {
  return (
    <div class="stat">
      <span class="stat-icon">{icon}</span>
      <span class="stat-body">
        <span class="stat-label">{label}</span>
        <span class={`stat-value ${tone ?? ''}`}>{value}</span>
        {sub && <span class="stat-sub">{sub}</span>}
      </span>
    </div>
  );
}

export function NationTag({ name, color, flag, leader }: { name: string; color?: string; flag?: string; leader?: string }) {
  return (
    <span class="ntag">
      {flag !== undefined && <Flag id={flag} size={14} />}
      {color && <span class="dot" style={{ background: color }} />}
      <span class="ntag-name">{name}</span>
      {leader && <span class="ntag-leader">({leader})</span>}
    </span>
  );
}
