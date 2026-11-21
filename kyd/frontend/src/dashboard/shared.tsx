import { useEffect, useState, type ReactNode } from 'react';
import { ArrowRight } from 'lucide-react';
import type { Obs } from '../api';
import { Empty } from '../ui';
import type { Chamber } from './types';

// Several widgets read the same district endpoints; share one request per key for the session.
const cache = new Map<string, Promise<unknown>>();
export function cached<T>(key: string, fn: () => Promise<T>): Promise<T> {
  let p = cache.get(key) as Promise<T> | undefined;
  if (!p) { p = fn(); cache.set(key, p); p.catch(() => cache.delete(key)); }
  return p;
}

export type Load<T> = { data: T | null; err: string | null };
/** Loads `fn` whenever `key` changes; a null key means "nothing to load". Set `fresh` to skip the shared cache. */
export function useLoad<T>(key: string | null, fn: () => Promise<T>, fresh = false): Load<T> {
  const [s, setS] = useState<Load<T>>({ data: null, err: null });
  useEffect(() => {
    if (!key) { setS({ data: null, err: null }); return; }
    let live = true;
    setS({ data: null, err: null });
    (fresh ? fn() : cached(key, fn)).then(d => live && setS({ data: d, err: null }), e => live && setS({ data: null, err: e instanceof Error ? e.message : String(e) }));
    return () => { live = false; };
  }, [key]);
  return s;
}

/** Loading / error placeholder, or the children once data is in. */
export function Gate<T>({ l, children }: { l: Load<T>; children: (d: T) => ReactNode }) {
  if (l.err) return <Empty>Could not load: {l.err}</Empty>;
  if (!l.data) return <Empty>Loading…</Empty>;
  return <>{children(l.data)}</>;
}

export const by = (xs: Obs[] | undefined) => Object.fromEntries((xs ?? []).map(o => [o.indicator, o])) as Record<string, Obs>;
export const chamberOf = (g: string): Chamber | null => g.startsWith('HD') ? 'sldl' : g.startsWith('SD') ? 'sldu' : null;
export const Note = ({ children }: { children: ReactNode }) => <p className="mt-2 text-[11px] text-slate-500">{children}</p>;

export function Go({ onClick, children }: { onClick: () => void; children: ReactNode }) {
  return <button onClick={onClick} className="mt-2 inline-flex items-center gap-1 text-xs text-cyan-400 hover:underline">{children}<ArrowRight className="w-3 h-3" /></button>;
}

/** Tiny multi-series line chart; null points break the line. */
export function Spark({ xs, series, label }: { xs: (string | number)[]; series: { name: string; color: string; ys: (number | null)[] }[]; label: string }) {
  const W = 300, H = 80, vals = series.flatMap(s => s.ys).filter((v): v is number => v !== null);
  if (xs.length < 2 || !vals.length) return <Empty>No trend data.</Empty>;
  const lo = Math.min(0, ...vals), hi = Math.max(...vals, lo + 1);
  const px = (i: number) => (i / (xs.length - 1)) * W, py = (v: number) => H - 4 - ((v - lo) / (hi - lo)) * (H - 8);
  const d = (ys: (number | null)[]) => ys.map((v, i) => v === null ? '' : `${i && ys[i - 1] !== null ? 'L' : 'M'}${px(i).toFixed(1)},${py(v).toFixed(1)}`).join('');
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-20" role="img" aria-label={label} preserveAspectRatio="none">
        {series.map(s => <path key={s.name} d={d(s.ys)} fill="none" stroke={s.color} strokeWidth={2} vectorEffect="non-scaling-stroke" />)}
      </svg>
      <div className="flex justify-between text-[10px] text-slate-500 font-mono"><span>{xs[0]}</span>
        <span>{series.map(s => <span key={s.name} className="ml-2" style={{ color: s.color }}>— {s.name}</span>)}</span><span>{xs[xs.length - 1]}</span></div>
    </div>
  );
}
