import { useEffect, useState } from 'react';
import { Monitor, Moon, Sun } from 'lucide-react';

/** Dark, light, or follow the device. Saved per browser; applied before the first render (main.tsx). */
export type Theme = 'dark' | 'light' | 'system';
const KEY = 'kyd_theme';
const LIGHT = '(prefers-color-scheme: light)';
const CHANGED = 'kyd-theme';

export function getTheme(): Theme {
  try { const t = localStorage.getItem(KEY); return t === 'light' || t === 'system' ? t : 'dark'; } catch { return 'dark'; }
}

function apply(t: Theme) {
  const light = t === 'light' || (t === 'system' && window.matchMedia(LIGHT).matches);
  document.documentElement.classList.toggle('light', light);
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', light ? '#f3f7fb' : '#081a30');
}

export function setTheme(t: Theme) {
  try { localStorage.setItem(KEY, t); } catch { /* storage unavailable: applies for this visit */ }
  apply(t);
  window.dispatchEvent(new Event(CHANGED));
}

export function initTheme() {
  apply(getTheme());
  window.matchMedia(LIGHT).addEventListener('change', () => { if (getTheme() === 'system') apply('system'); });
}

const OPTIONS = [
  { id: 'dark', label: 'Dark', Icon: Moon },
  { id: 'light', label: 'Light', Icon: Sun },
  { id: 'system', label: 'System', Icon: Monitor },
] as const;

export function ThemePicker({ compact = false }: { compact?: boolean }) {
  const [t, setT] = useState<Theme>(getTheme);
  useEffect(() => {
    const f = () => setT(getTheme());
    window.addEventListener(CHANGED, f);
    return () => window.removeEventListener(CHANGED, f);
  }, []);
  return (
    <div role="radiogroup" aria-label="Color theme" className="inline-flex gap-0.5 p-0.5 rounded-md bg-premium-950 border border-premium-800">
      {OPTIONS.map(({ id, label, Icon }) => (
        <button key={id} role="radio" aria-checked={t === id} onClick={() => setTheme(id)} title={`${label} theme`} aria-label={`${label} theme`}
          className={`inline-flex items-center gap-1 px-1.5 py-1 rounded text-[11px] ${t === id ? 'bg-premium-800 text-cyan-400' : 'text-slate-400 hover:text-slate-200'}`}>
          <Icon className="w-3.5 h-3.5" />{!compact && label}
        </button>))}
    </div>
  );
}
