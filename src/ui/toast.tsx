// تنبيهات سريعة تطلع فوق الشاشة
import { useEffect, useState } from 'preact/hooks';

export interface ToastAction {
  label: string;
  run: () => void;
  kind?: 'primary' | 'danger';
}
export interface Toast {
  id: number;
  icon?: string;
  text: string;
  kind?: 'info' | 'good' | 'bad' | 'warn';
  actions?: ToastAction[];
  ttl?: number;
}

let seq = 0;
let toasts: Toast[] = [];
const subs = new Set<() => void>();
const notify = () => subs.forEach((f) => f());

export function toast(t: Omit<Toast, 'id'>) {
  const id = ++seq;
  toasts = [...toasts.slice(-4), { id, ...t }];
  notify();
  const ttl = t.ttl ?? (t.actions?.length ? 12000 : 4500);
  setTimeout(() => dismiss(id), ttl);
  return id;
}

export function dismiss(id: number) {
  toasts = toasts.filter((t) => t.id !== id);
  notify();
}

export function Toasts() {
  const [, set] = useState(0);
  useEffect(() => {
    const f = () => set((x) => x + 1);
    subs.add(f);
    return () => {
      subs.delete(f);
    };
  }, []);
  return (
    <div class="toasts" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} class={`toast toast-${t.kind ?? 'info'}`} onClick={() => !t.actions && dismiss(t.id)}>
          {t.icon && <span class="toast-icon">{t.icon}</span>}
          <span class="toast-text">{t.text}</span>
          {t.actions && (
            <span class="toast-actions">
              {t.actions.map((a) => (
                <button
                  class={`btn btn-sm ${a.kind === 'danger' ? 'btn-danger' : a.kind === 'primary' ? 'btn-primary' : ''}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    a.run();
                    dismiss(t.id);
                  }}
                >
                  {a.label}
                </button>
              ))}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
