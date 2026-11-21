import React, { useEffect, useRef, useState, type ReactNode } from 'react';
import { Info, AlertTriangle, Printer, Download, LayoutDashboard } from 'lucide-react';
import { api, fmt, type Obs, type Geo } from './api';
import { pinToDashboard } from './pins';

export function usePersistentState<T>(key: string, def: T): [T, (v: T) => void] {
  const [v, setV] = useState<T>(() => {
    try { const s = localStorage.getItem(key); if (s !== null) return JSON.parse(s); } catch { /* ignore */ }
    return def;
  });
  return [v, (nv: T) => { setV(nv); try { localStorage.setItem(key, JSON.stringify(nv)); } catch { /* ignore */ } }];
}

export function Card({ title, right, children, className = '' }: { title?: ReactNode; right?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`kyd-card rounded-xl p-4 ${className}`}>
      {title && (
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wide">{title}</h2>
          {right}
        </div>
      )}
      {children}
    </section>
  );
}

/** Every number in the UI renders through <Figure>. Clicking it shows the citation ("show the math", §9.6). */
export function Figure({ o, big = false }: { o: Obs; big?: boolean }) {
  const [open, setOpen] = useState(false);
  const [cite, setCite] = useState<any>(null);
  const [pinned, setPinned] = useState(false);
  const weak = o.flags.includes('suppressed_cv');
  const warn = weak || o.flags.includes('high_moe');
  const [at, setAt] = useState<{ left: number; top: number } | null>(null);
  const pop = useRef<HTMLDivElement>(null);
  useEffect(() => { if (open && !cite) api.cite(o.obs_id).then(setCite).catch(() => setCite({ error: true })); }, [open]);
  // Fixed position, so a scrolling container (dashboard widget) cannot clip it; it closes when anything scrolls.
  useEffect(() => {
    if (!open) return;
    const close = (e: Event) => { if (!pop.current?.contains(e.target as Node)) setOpen(false); };
    window.addEventListener('scroll', close, true);
    return () => window.removeEventListener('scroll', close, true);
  }, [open]);
  const toggle = (e: React.MouseEvent<HTMLButtonElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    setAt({ left: Math.max(8, Math.min(r.left, window.innerWidth - 336)), top: r.bottom + 4 });
    setOpen(!open);
  };
  return (
    <span className="relative inline-block">
      <button onClick={toggle} aria-expanded={open}
        className={`font-mono ${big ? 'text-2xl font-bold' : 'text-sm'} ${weak ? 'text-slate-500 italic' : 'text-cyan-300'} hover:underline decoration-dotted`}
        title={weak ? 'Low reliability (CV > 30%)' : 'Show source and math'}>
        {fmt(o)}{warn && <AlertTriangle className="inline w-3 h-3 ml-1 text-amber-400" aria-label="uncertain estimate" />}
      </button>
      {o.moe !== null && <span className="ml-1 text-xs text-slate-500 font-mono">±{fmt({ value: o.moe, unit: o.unit })}</span>}
      {open && (
        <div role="dialog" ref={pop} style={at ?? undefined} className="fixed z-50 w-80 max-h-[60vh] overflow-y-auto p-3 rounded-lg bg-premium-900 border border-premium-700 shadow-xl text-xs text-slate-300 space-y-1">
          <div className="font-semibold text-slate-100">{o.label}</div>
          <div>Value <b>{fmt(o)}</b>{o.moe !== null && <> ± {fmt({ value: o.moe, unit: o.unit })} (90% MOE)</>}</div>
          {o.cv !== null && <div>Coefficient of variation: {(o.cv * 100).toFixed(1)}%{weak && ' (above the 30% reliability threshold)'}</div>}
          <div>Method: {o.method}{o.method_note ? ` · ${o.method_note}` : ''}</div>
          <div>Vintage: {o.source_id.startsWith('acs') ? 'ACS ' : ''}{o.vintage}</div>
          {cite?.source && <div>Source: {cite.source.publisher}, {cite.source.title}{cite.source.url && <> · <a className="text-cyan-400 underline" href={cite.source.url} target="_blank" rel="noreferrer">link</a></>}</div>}
          <div className="text-slate-500 font-mono">obs:{o.obs_id} · {o.flags.join(', ') || 'no flags'}</div>
          <button onClick={() => { pinToDashboard({ type: 'kpi', title: o.label, config: { indicator: o.indicator, geo: o.geo_id } }); setPinned(true); }}
            className="no-print mt-1 inline-flex items-center gap-1 text-cyan-400 hover:underline">
            <LayoutDashboard className="w-3 h-3" />{pinned ? 'Pinned to your dashboard' : 'Pin to dashboard'}</button>
        </div>
      )}
    </span>
  );
}

export function GeoPicker({ geos, value, onChange, label = 'District' }: { geos: Geo[]; value: string | null; onChange: (g: string) => void; label?: string }) {
  const groups: [string, string][] = [['sldl', 'House'], ['sldu', 'Senate'], ['county', 'County'], ['state', 'State']];
  return (
    <label className="flex items-center gap-2 text-xs text-slate-400">
      <span className="sr-only sm:not-sr-only">{label}</span>
      <select value={value ?? ''} onChange={e => onChange(e.target.value)}
        className="bg-premium-950 border border-premium-700 rounded-md px-2 py-1.5 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-600">
        {groups.map(([t, l]) => (
          <optgroup key={t} label={l}>
            {geos.filter(g => g.geo_type === t).map(g => <option key={g.geo_id} value={g.geo_id}>{g.name}</option>)}
          </optgroup>
        ))}
      </select>
    </label>
  );
}

export function Pill({ children, tone = 'slate' }: { children: ReactNode; tone?: 'slate' | 'cyan' | 'amber' | 'red' | 'emerald' }) {
  const t = { slate: 'border-premium-700 text-slate-400', cyan: 'border-cyan-800 text-cyan-300', amber: 'border-amber-800 text-amber-300',
    red: 'border-red-800 text-red-300', emerald: 'border-emerald-800 text-emerald-300' }[tone];
  return <span className={`px-2 py-0.5 rounded-full border text-xs font-mono ${t}`}>{children}</span>;
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="flex items-center gap-2 text-sm text-slate-500"><Info className="w-4 h-4" />{children}</div>;
}

/** Print and CSV export for the table inside a card. CSV is built from the table on screen (no server call). */
export function ExportButtons({ table, name }: { table: React.RefObject<HTMLTableElement | null>; name: string }) {
  const csv = () => {
    const t = table.current;
    if (!t) return;
    const esc = (v: string) => `"${v.replace(/\s+/g, ' ').trim().replace(/"/g, '""')}"`;
    const lines = Array.from(t.querySelectorAll('tr')).map(tr =>
      Array.from(tr.querySelectorAll('th,td')).filter(c => !c.classList.contains('no-print')).map(c => {
        const sel = c.querySelector('select') as HTMLSelectElement | null;
        return esc(sel ? sel.options[sel.selectedIndex]?.text ?? '' : (c as HTMLElement).innerText);
      }).join(','));
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8' }));
    a.download = `${name}.csv`;
    a.click();
  };
  const btn = 'text-xs px-2 py-1 rounded border border-premium-700 text-slate-300 hover:text-cyan-300 inline-flex items-center gap-1';
  return (
    <div className="no-print flex gap-1.5">
      <button onClick={() => window.print()} className={btn} title="Print or save as PDF"><Printer className="w-3.5 h-3.5" />Print</button>
      <button onClick={csv} className={btn} title="Download this table as CSV"><Download className="w-3.5 h-3.5" />CSV</button>
    </div>
  );
}
