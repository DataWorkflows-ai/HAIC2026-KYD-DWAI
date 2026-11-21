import { useCallback, useEffect, useLayoutEffect, useRef, useState, type CSSProperties, type PointerEvent as RPointerEvent, type ReactNode } from 'react';
import { Check, ChevronDown, CloudOff, GripVertical, LayoutGrid, Loader2, Plus, RotateCcw, Settings, X } from 'lucide-react';
import { api, type Geo, type User } from './api';
import { Empty } from './ui';
import { PINNED, takePins } from './pins';
import { canSee, isType, META, PRESETS, presetWidgets } from './dashboard/catalog';
import { append, bottom, clampBox, COLS, GAP, makeWidget, readLocal, resolve, ROW, sanitize, writeLocal } from './dashboard/layout';
import { CatalogPanel, Modal, SettingsPanel } from './dashboard/panels';
import { renderWidget } from './dashboard/registry';
import type { Ctx, Layout, Widget, WidgetConfig, WidgetType } from './dashboard/types';

type Props = { geo: string; geos: Geo[]; user: User; onAsk: (q: string) => void; onOpen: (tab: string, geo?: string) => void; onOpenChat: (chatId: string) => void };
type Status = 'idle' | 'saving' | 'saved' | 'error';
const btn = 'inline-flex items-center gap-1 px-2.5 py-1 rounded-md border text-xs';
const px = (n: number, unit: number) => n * unit + (n - 1) * GAP;

function useNarrow() {
  const q = '(max-width: 767px)';
  const [n, setN] = useState(() => window.matchMedia(q).matches);
  useEffect(() => {
    const m = window.matchMedia(q), f = () => setN(m.matches);
    m.addEventListener('change', f);
    return () => m.removeEventListener('change', f);
  }, []);
  return n;
}

function Frame({ w, edit, canDrag, active, style, onDrag, onResize, onHide, onSettings, children }: {
  w: Widget; edit: boolean; canDrag: boolean; active: boolean; style: CSSProperties;
  onDrag: (e: RPointerEvent) => void; onResize: (e: RPointerEvent) => void; onHide: () => void; onSettings: () => void; children: ReactNode;
}) {
  const title = w.title || META[w.type].title;
  return (
    <section style={style} className={`kyd-card rounded-xl flex flex-col overflow-hidden relative ${active ? 'ring-2 ring-cyan-400 shadow-2xl z-20' : ''}`} aria-label={title}>
      <header onPointerDown={canDrag ? onDrag : undefined}
        className={`flex items-center justify-between gap-2 px-3 py-2 border-b border-premium-800 shrink-0 select-none ${canDrag ? 'cursor-move touch-none bg-cyan-950/30' : ''}`}>
        <h2 className="text-xs font-semibold text-slate-300 uppercase tracking-wide truncate flex items-center gap-1">
          {canDrag && <GripVertical className="w-3.5 h-3.5 text-cyan-500 shrink-0" />}{title}</h2>
        {edit && <div className="flex gap-1 shrink-0" onPointerDown={e => e.stopPropagation()}>
          <button onClick={onSettings} aria-label={`Settings for ${title}`} className="p-0.5 text-slate-400 hover:text-cyan-300"><Settings className="w-3.5 h-3.5" /></button>
          <button onClick={onHide} aria-label={`Hide ${title}`} className="p-0.5 text-slate-400 hover:text-red-400"><X className="w-3.5 h-3.5" /></button>
        </div>}
      </header>
      <div className="flex-1 min-h-0 overflow-auto p-3">{children}</div>
      {canDrag && <div onPointerDown={onResize} aria-hidden className="absolute bottom-0 right-0 w-[18px] h-[18px] cursor-se-resize touch-none flex items-end justify-end z-30">
        <svg width="12" height="12" viewBox="0 0 12 12"><path d="M12 0 L12 12 L0 12 Z" fill="rgba(0,188,255,0.7)" /></svg></div>}
    </section>
  );
}

export function DashboardTab({ geo, geos, user, onAsk, onOpen, onOpenChat }: Props) {
  const role = user.role;
  const fresh = (id = 'legislator'): Layout => ({ version: 1, updated: 0, widgets: presetWidgets(id, role) });
  const [layout, setLayout] = useState<Layout>(() => readLocal() ?? fresh());
  const ref = useRef(layout);
  const [loaded, setLoaded] = useState(false);
  const [status, setStatus] = useState<Status>('idle');
  const [edit, setEdit] = useState(false);
  const [drag, setDrag] = useState<Widget | null>(null);
  const [settings, setSettings] = useState<string | null>(null);
  const [catalog, setCatalog] = useState(false);
  const [presets, setPresets] = useState(false);
  const [width, setWidth] = useState(0);
  const narrow = useNarrow();
  const box = useRef<HTMLDivElement>(null);
  const timer = useRef<number | undefined>(undefined);
  const pending = useRef<Layout | null>(null);

  const flush = useCallback(() => {
    const l = pending.current;
    window.clearTimeout(timer.current); pending.current = null;
    if (l) api.saveDashboard(l).then(() => setStatus('saved'), () => setStatus('error'));
  }, []);
  const schedule = useCallback((l: Layout) => {
    pending.current = l; setStatus('saving');
    window.clearTimeout(timer.current); timer.current = window.setTimeout(flush, 800);
  }, [flush]);
  const commit = useCallback((f: (ws: Widget[]) => Widget[]) => {
    const l: Layout = { version: 1, updated: Date.now(), widgets: f(ref.current.widgets) };
    ref.current = l; setLayout(l); writeLocal(l); schedule(l);
  }, [schedule]);
  useEffect(() => flush, [flush]);

  // Newer of server and this browser wins; the default preset (updated 0) never overwrites a saved layout.
  useEffect(() => {
    let live = true;
    api.dashboard().then(r => {
      if (!live) return;
      const s = sanitize(r.layout), cur = ref.current;
      if (s && s.updated > cur.updated) { ref.current = s; setLayout(s); writeLocal(s); }
      else if (cur.updated > 0 && (!s || cur.updated > s.updated)) schedule(cur);
    }).catch(() => live && setStatus('error')).finally(() => live && setLoaded(true));
    return () => { live = false; };
  }, []);

  // Drain pins only after the server layout is in, so a newer server copy cannot drop them.
  useEffect(() => {
    if (!loaded) return;
    const drain = () => {
      const ps = takePins().filter(p => isType(p.type));
      if (ps.length) commit(ws => ps.reduce((acc, p) => append(acc, makeWidget(p.type as WidgetType, p.config as WidgetConfig, p.title)), ws));
    };
    drain();
    window.addEventListener(PINNED, drain);
    return () => window.removeEventListener(PINNED, drain);
  }, [loaded, commit]);

  useLayoutEffect(() => {
    const el = box.current;
    if (!el) return;
    setWidth(el.clientWidth);
    const ro = new ResizeObserver(() => setWidth(el.clientWidth));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const colW = Math.max(10, (width - GAP * (COLS - 1)) / COLS);
  const visible = layout.widgets.filter(w => !w.hidden && canSee(w.type, role));
  const shown = drag ? resolve(visible.map(w => w.id === drag.id ? drag : w), drag.id) : visible;
  const hidden = layout.widgets.filter(w => w.hidden && canSee(w.type, role));

  const start = (e: RPointerEvent, w: Widget, mode: 'move' | 'resize') => {
    if (!edit || narrow || e.button !== 0) return;
    e.preventDefault(); e.stopPropagation();
    const sx = e.clientX, sy = e.clientY;
    let next = w;
    const move = (ev: PointerEvent) => {
      const dx = Math.round((ev.clientX - sx) / (colW + GAP)), dy = Math.round((ev.clientY - sy) / (ROW + GAP));
      next = clampBox(mode === 'move' ? { ...w, x: w.x + dx, y: w.y + dy } : { ...w, w: Math.min(COLS - w.x, w.w + dx), h: w.h + dy });
      setDrag(next);
    };
    const up = () => {
      window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up); window.removeEventListener('pointercancel', up);
      setDrag(null);
      if (next.x !== w.x || next.y !== w.y || next.w !== w.w || next.h !== w.h) commit(ws => resolve(ws.map(x => x.id === next.id ? next : x), next.id));
    };
    window.addEventListener('pointermove', move); window.addEventListener('pointerup', up); window.addEventListener('pointercancel', up);
  };

  const patch = (id: string, p: Partial<Widget>) => commit(ws => ws.map(x => x.id === id ? { ...x, ...p } : x));
  const show = (id: string) => commit(ws => resolve(ws.map(x => x.id === id ? { ...x, hidden: false, x: 0, y: bottom(ws) } : x), id));
  const add = (t: WidgetType) => { commit(ws => append(ws, makeWidget(t))); setCatalog(false); };
  const applyPreset = (id: string, title: string) => {
    setPresets(false);
    if (window.confirm(`Replace your dashboard with the "${title}" preset? Your current widgets, notes and calendar entries will be removed.`)) commit(() => fresh(id).widgets);
  };
  const reset = () => { if (window.confirm('Reset the dashboard to the default layout? Your current widgets, notes and calendar entries will be removed.')) commit(() => fresh().widgets); };

  const ctx: Ctx = { geos, user, onAsk, onOpen, onOpenChat };
  const first = (user.name || user.email.split('@')[0]).split(/\s+/)[0];
  const geoName = geos.find(g => g.geo_id === geo)?.name ?? geo;
  const editing = settings ? layout.widgets.find(w => w.id === settings) : undefined;

  const frame = (w: Widget, style: CSSProperties) => (
    <Frame key={w.id} w={w} edit={edit} canDrag={edit && !narrow} active={drag?.id === w.id} style={style}
      onDrag={e => start(e, w, 'move')} onResize={e => start(e, w, 'resize')}
      onHide={() => patch(w.id, { hidden: true })} onSettings={() => setSettings(w.id)}>
      {renderWidget({ w, geo: w.config.geo || geo, ctx, setConfig: c => commit(ws => ws.map(x => x.id === w.id ? { ...x, config: { ...x.config, ...c } } : x)) })}
    </Frame>
  );
  const rows = Math.max(1, bottom(shown));
  const guides = `repeating-linear-gradient(to right, rgba(0,188,255,0.05) 0 ${colW}px, transparent ${colW}px ${colW + GAP}px)`;

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-3 mb-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Dashboard</h1>
          <p className="text-sm text-slate-400">Aloha, {first}. Widgets follow <span className="text-cyan-300">{geoName}</span> unless set to a district of their own.</p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] text-slate-500 inline-flex items-center gap-1 mr-1" aria-live="polite">
            {status === 'saving' && <><Loader2 className="w-3 h-3 animate-spin" />Saving…</>}
            {status === 'saved' && <><Check className="w-3 h-3 text-emerald-400" />Saved</>}
            {status === 'error' && <><CloudOff className="w-3 h-3 text-amber-400" />Saved in this browser only</>}
          </span>
          <button onClick={() => setEdit(e => !e)} aria-pressed={edit}
            className={`${btn} ${edit ? 'border-cyan-600 text-cyan-300 bg-cyan-950' : 'border-premium-700 text-slate-300 hover:text-cyan-300'}`}>
            <LayoutGrid className="w-3.5 h-3.5" />{edit ? 'Done' : 'Edit layout'}</button>
          <button onClick={() => setCatalog(true)} className={`${btn} border-premium-700 text-slate-300 hover:text-cyan-300`}><Plus className="w-3.5 h-3.5" />Add widget</button>
          <div className="relative">
            <button onClick={() => setPresets(p => !p)} aria-expanded={presets} className={`${btn} border-premium-700 text-slate-300 hover:text-cyan-300`}>Presets<ChevronDown className="w-3.5 h-3.5" /></button>
            {presets && <>
              <div className="fixed inset-0 z-40" onClick={() => setPresets(false)} />
              <ul className="absolute right-0 mt-1 z-50 w-56 rounded-lg bg-premium-900 border border-premium-700 shadow-xl py-1">
                {PRESETS.map(p => <li key={p.id}><button onClick={() => applyPreset(p.id, p.title)} className="w-full text-left px-3 py-1.5 text-sm text-slate-200 hover:bg-premium-800 hover:text-cyan-300">
                  {p.title}{p.id === 'legislator' && <span className="ml-1 text-[10px] text-slate-500">default</span>}</button></li>)}
              </ul>
            </>}
          </div>
          <button onClick={reset} className={`${btn} border-premium-700 text-slate-400 hover:text-red-400`}><RotateCcw className="w-3.5 h-3.5" />Reset</button>
        </div>
      </div>
      {edit && <p className="mb-2 text-xs text-slate-500">{narrow ? 'Use the gear to configure a widget and × to hide it. Drag and resize on a wider screen.'
        : 'Drag a widget by its title bar, resize from the bottom-right corner, use the gear to configure and × to hide.'}</p>}

      <div ref={box}>
        {!visible.length ? (
          <div className="kyd-card rounded-xl p-6 space-y-3">
            <Empty>All widgets are hidden.</Empty>
            <div className="flex gap-2">
              <button onClick={() => setCatalog(true)} className={`${btn} border-cyan-800 text-cyan-300`}><Plus className="w-3.5 h-3.5" />Add widget</button>
              <button onClick={reset} className={`${btn} border-premium-700 text-slate-300`}><RotateCcw className="w-3.5 h-3.5" />Reset to default</button>
            </div>
          </div>
        ) : narrow ? (
          <div className="flex flex-col" style={{ gap: GAP }}>
            {[...shown].sort((a, b) => a.y - b.y || a.x - b.x).map(w => frame(w, { height: px(w.h, ROW) }))}
          </div>
        ) : width > 0 && (
          <div className="relative rounded-xl" style={{ height: px(rows, ROW), ...(edit ? { backgroundImage: guides } : {}) }}>
            {shown.map(w => frame(w, { position: 'absolute', left: w.x * (colW + GAP), top: w.y * (ROW + GAP), width: px(w.w, colW), height: px(w.h, ROW),
              transition: drag ? 'left 80ms, top 80ms' : undefined }))}
          </div>
        )}
      </div>

      {catalog && <CatalogPanel role={role} hidden={hidden} onAdd={add} onShow={id => { show(id); setCatalog(false); }} onClose={() => setCatalog(false)} />}
      {editing && <SettingsPanel w={editing} geo={geo} geos={geos} onChange={p => patch(editing.id, p)} onClose={() => setSettings(null)}
        onRemove={() => { commit(ws => ws.filter(x => x.id !== editing.id)); setSettings(null); }} />}
      {settings && !editing && <Modal title="Settings" onClose={() => setSettings(null)}><Empty>This widget was removed.</Empty></Modal>}
    </div>
  );
}
