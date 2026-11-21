import { useMemo, type ReactNode } from 'react';
import { Eye, Plus, Trash2, X } from 'lucide-react';
import { api, type Geo, type Role } from '../api';
import { GeoPicker } from '../ui';
import { canSee, DEFERRED, META, type Field } from './catalog';
import { useLoad } from './shared';
import type { Chamber, Series, Widget, WidgetType } from './types';

const sel = 'w-full bg-premium-950 border border-premium-700 rounded-md px-2 py-1.5 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-600';
const SERIES: [Series, string][] = [['unemployment', 'Unemployment (county vs state)'], ['crime', 'Crime (Oʻahu estimate)'], ['vital', 'Births and deaths']];

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-start justify-center p-4 overflow-y-auto" onPointerDown={e => e.target === e.currentTarget && onClose()}>
      <div role="dialog" aria-label={title} className="kyd-card rounded-xl w-full max-w-lg mt-12 p-4" onKeyDown={e => e.key === 'Escape' && onClose()}>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wide">{title}</h2>
          <button onClick={onClose} aria-label="Close" className="text-slate-400 hover:text-slate-100"><X className="w-4 h-4" /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return <div className="space-y-1"><div className="text-xs text-slate-400">{label}</div>{children}</div>;
}

export function SettingsPanel({ w, geo, geos, onChange, onRemove, onClose }: {
  w: Widget; geo: string; geos: Geo[]; onChange: (patch: Partial<Widget>) => void; onRemove: () => void; onClose: () => void;
}) {
  const fields = META[w.type].fields;
  const inds = useLoad(fields.includes('indicator') ? 'indicators' : null, () => api.indicators());
  const topics = useMemo(() => {
    const g: Record<string, { indicator: string; label: string }[]> = {};
    for (const i of inds.data ?? []) (g[i.topic || 'Other'] ??= []).push(i);
    return Object.entries(g);
  }, [inds.data]);
  const cfg = (patch: Partial<Widget['config']>) => onChange({ config: { ...w.config, ...patch } });
  const field = (f: Field): ReactNode => {
    switch (f) {
      case 'title':
        return <Row key={f} label="Title"><input value={w.title ?? ''} placeholder={META[w.type].title} onChange={e => onChange({ title: e.target.value || undefined })} className={sel} /></Row>;
      case 'geo': {
        const follow = !w.config.geo;
        return <Row key={f} label="District">
          <label className="flex items-center gap-2 text-sm text-slate-300">
            <input type="checkbox" checked={follow} onChange={e => cfg({ geo: e.target.checked ? undefined : geo })} className="accent-cyan-500" />
            Follow the selected district</label>
          {!follow && <GeoPicker geos={geos} value={w.config.geo ?? geo} onChange={g => cfg({ geo: g })} />}
        </Row>;
      }
      case 'indicator':
        return <Row key={f} label="Indicator">
          {inds.err ? <div className="text-xs text-slate-500">Could not load indicators.</div> :
            <select value={w.config.indicator ?? 'pct_below_fpl'} onChange={e => cfg({ indicator: e.target.value })} className={sel}>
              {!inds.data && <option value={w.config.indicator ?? 'pct_below_fpl'}>{w.config.indicator ?? 'pct_below_fpl'}</option>}
              {topics.map(([t, xs]) => <optgroup key={t} label={t}>{xs.map(i => <option key={i.indicator} value={i.indicator}>{i.label}</option>)}</optgroup>)}
            </select>}
        </Row>;
      case 'chamber':
        return <Row key={f} label="Chamber (used when the district is a county or the state)">
          <div className="flex gap-1">{([['sldl', 'House'], ['sldu', 'Senate']] as [Chamber, string][]).map(([c, l]) => (
            <button key={c} onClick={() => cfg({ chamber: c })} aria-pressed={(w.config.chamber ?? 'sldl') === c}
              className={`px-3 py-1 rounded text-xs border ${(w.config.chamber ?? 'sldl') === c ? 'border-cyan-700 text-cyan-300' : 'border-premium-700 text-slate-400'}`}>{l}</button>))}</div>
        </Row>;
      case 'series':
        return <Row key={f} label="Series">
          <select value={w.config.series ?? 'unemployment'} onChange={e => cfg({ series: e.target.value as Series })} className={sel}>
            {SERIES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
        </Row>;
      default: { const never: never = f; return never; }
    }
  };
  return <Modal title={`${w.title || META[w.type].title}: settings`} onClose={onClose}>
    <div className="space-y-3">{fields.map(field)}</div>
    <div className="mt-4 flex justify-between">
      <button onClick={() => { if (window.confirm('Remove this widget? Its settings and contents are deleted.')) onRemove(); }}
        className="inline-flex items-center gap-1 px-2 py-1 rounded-md border border-red-900 text-xs text-red-400 hover:text-red-300"><Trash2 className="w-3.5 h-3.5" />Remove widget</button>
      <button onClick={onClose} className="px-3 py-1 rounded-md bg-cyan-700 hover:bg-cyan-600 text-sm">Done</button>
    </div>
  </Modal>;
}

export function CatalogPanel({ role, hidden, onAdd, onShow, onClose }: {
  role: Role; hidden: Widget[]; onAdd: (t: WidgetType) => void; onShow: (id: string) => void; onClose: () => void;
}) {
  const types = (Object.keys(META) as WidgetType[]).filter(t => canSee(t, role));
  return <Modal title="Add widget" onClose={onClose}>
    {hidden.length > 0 && <div className="mb-3">
      <div className="text-xs text-slate-400 mb-1">Hidden widgets</div>
      <div className="flex flex-wrap gap-1.5">{hidden.map(w => (
        <button key={w.id} onClick={() => onShow(w.id)} className="inline-flex items-center gap-1 px-2 py-1 rounded border border-premium-700 text-xs text-slate-300 hover:text-cyan-300">
          <Eye className="w-3 h-3" />{w.title || META[w.type].title}</button>))}</div>
    </div>}
    <ul className="divide-y divide-premium-800 max-h-[60vh] overflow-y-auto">
      {types.map(t => (
        <li key={t} className="py-2 flex items-center justify-between gap-3">
          <div><div className="text-sm text-slate-100">{META[t].title}</div><div className="text-xs text-slate-500">{META[t].desc}</div></div>
          {META[t].pinOnly ? <span className="text-[11px] text-slate-500 whitespace-nowrap">pin from Ask</span> :
            <button onClick={() => onAdd(t)} className="shrink-0 inline-flex items-center gap-1 px-2 py-1 rounded border border-cyan-800 text-xs text-cyan-300 hover:bg-cyan-950"><Plus className="w-3 h-3" />Add</button>}
        </li>))}
      {DEFERRED.map(d => (
        <li key={d.title} className="py-2 flex items-center justify-between gap-3 opacity-60" aria-disabled>
          <div><div className="text-sm text-slate-300">{d.title}</div><div className="text-xs text-slate-500">{d.note}</div></div>
          <span className="text-[11px] text-amber-400 whitespace-nowrap">needs data</span>
        </li>))}
    </ul>
  </Modal>;
}
