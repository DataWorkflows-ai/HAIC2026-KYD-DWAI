/**
 * District map built on the ArcGIS Maps SDK for JavaScript, loaded from Esri's CDN.
 *
 * Layers, top to bottom:
 *  1. Official 2022 district lines: FeatureLayer served live by the Hawaiʻi Statewide GIS Program
 *     (geodata.hawaii.gov AdminBnd/MapServer 33 = House, 34 = Senate). Outline only.
 *  2. Data layer: GeoJSONLayer built from the bundled /geo/{sldl,sldu}.geojson (from the same
 *     source, simplified), joined in the browser to the indicator being mapped. Drives the choropleth,
 *     hover highlight and hit-testing.
 *  3. Basemap: Esri World Imagery tiles, which need no key, or OpenStreetMap. With an ArcGIS
 *     API key (VITE_ARCGIS_API_KEY) the vector basemaps are used instead.
 *
 * Interaction: hover (mouse) highlights a district and shows a summary card. Click or tap pins
 * it in the side panel. "Open profile" jumps to the Overview tab.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { ExternalLink, Layers, MapPin, Star } from 'lucide-react';
import { api, fmt, type Geo, type MapDistrict, type MapSummary, type Member } from './api';
import { Card, Pill } from './ui';

const SDK = 'https://js.arcgis.com/4.33/';
const STATE_GIS = 'https://geodata.hawaii.gov/arcgis/rest/services/AdminBnd/MapServer';
const LAYER_ID: Record<Chamber, number> = { sldl: 33, sldu: 34 };
const IMAGERY = 'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer';
const API_KEY = (import.meta as any).env?.VITE_ARCGIS_API_KEY as string | undefined;
const RAMP = ['#1e3a8a', '#2563eb', '#a855f7', '#ec4899', '#f97316'];
const ISLANDS: [string, number[]][] = [
  ['Kauaʻi', [-160.3, 21.85, -159.25, 22.25]], ['Oʻahu', [-158.3, 21.25, -157.6, 21.72]],
  ['Maui Nui', [-157.35, 20.5, -155.95, 21.25]], ['Hawaiʻi', [-156.1, 18.9, -154.75, 20.3]], ['State', [-160.3, 18.9, -154.75, 22.25]],
];
type Chamber = 'sldl' | 'sldu';

let sdkPromise: Promise<any> | null = null;
function loadSdk(): Promise<any> {
  if ((window as any).$arcgis) return Promise.resolve((window as any).$arcgis);
  if (sdkPromise) return sdkPromise;
  sdkPromise = new Promise((resolve, reject) => {
    const css = document.createElement('link');
    css.rel = 'stylesheet';
    css.href = SDK + 'esri/themes/dark/main.css';
    document.head.appendChild(css);
    const s = document.createElement('script');
    s.src = SDK;
    s.onload = () => resolve((window as any).$arcgis);
    s.onerror = () => { sdkPromise = null; reject(new Error('ArcGIS SDK failed to load')); };
    document.head.appendChild(s);
  });
  return sdkPromise;
}

const memberName = (m: Member | null) => m?.name ?? 'Not yet confirmed';
const pct = (x: number) => `${Math.round(x * 100)}%`;

/** Neighborhoods, Oʻahu neighborhood boards and county council districts inside a legislative district. */
function LocalAreas({ d, compact }: { d: MapDistrict; compact: boolean }) {
  const shown = compact ? d.neighborhoods.slice(0, 8) : d.neighborhoods;
  const more = d.neighborhoods.length - shown.length;
  const council = d.council.filter(c => c.share >= (compact ? 0.15 : 0.05));
  const boards = d.boards.filter(b => b.share >= (compact ? 0.15 : 0.05));
  return (
    <>
      {d.neighborhoods.length > 0 && (
        <div>
          <div className="text-[11px] uppercase tracking-wide text-slate-500">Neighborhoods</div>
          <div className="text-slate-200 text-xs leading-snug">
            {shown.join(' · ')}{more > 0 && <span className="text-slate-500"> + {more} more</span>}
          </div>
        </div>
      )}
      {council.length > 0 && (
        <div className="text-xs">
          <span className="text-slate-500">{council[0].body.replace(' (residency area)', '')}: </span>
          {council.map((c, i) => (
            <span key={`${c.body}${c.number}`} className="text-slate-200">
              {i > 0 && ', '}{c.number == null || (c.name && c.body.includes('residency')) ? c.name : `District ${c.number}`}
              {council.length > 1 && <span className="text-slate-500"> ({pct(c.share)})</span>}
            </span>))}
        </div>
      )}
      {boards.length > 0 && (
        <div className="text-xs">
          <span className="text-slate-500">Neighborhood board{boards.length > 1 ? 's' : ''}: </span>
          {boards.map((b, i) => (
            <span key={b.number} className="text-slate-200">
              {i > 0 && ', '}No. {b.number} {b.name}{boards.length > 1 && <span className="text-slate-500"> ({pct(b.share)})</span>}
            </span>))}
        </div>
      )}
    </>
  );
}
const isTouch = () => typeof window !== 'undefined' && window.matchMedia?.('(hover: none)').matches;

function StatusBadge({ m }: { m: Member | null }) {
  if (!m || m.status === 'official') return null;
  const label = { secondary: 'unconfirmed', verify: 'verify', pending: 'pending' }[m.status];
  return <span title={m.note ?? ''} className="ml-1 text-[10px] px-1 rounded border border-amber-700 text-amber-300">{label}</span>;
}

/** Hover card and side-panel body: one district's people, overlaps and key figures. */
function DistrictCard({ d, chamber, compact = false }: { d: MapDistrict; chamber: Chamber; compact?: boolean }) {
  const otherTitle = chamber === 'sldl' ? 'Senator' : 'Representative';
  const major = d.counterparts.filter(c => c.share_of_this >= 0.05);
  const minor = d.counterparts.filter(c => c.share_of_this < 0.05);
  return (
    <div className="space-y-2 text-sm">
      <div>
        <div className="font-semibold text-slate-100">{d.name}</div>
        <div className="text-xs text-slate-400">{d.counties.join(', ')}</div>
      </div>
      <LocalAreas d={d} compact={compact} />
      <div>
        <div className="text-[11px] uppercase tracking-wide text-slate-500">{d.member?.title ?? (chamber === 'sldl' ? 'Representative' : 'Senator')}</div>
        <div className="text-slate-100">{memberName(d.member)}<StatusBadge m={d.member} /></div>
      </div>
      <div>
        <div className="text-[11px] uppercase tracking-wide text-slate-500">{otherTitle}{major.length > 1 ? 's' : ''} covering this district</div>
        <ul>
          {major.map(c => (
            <li key={c.geo_id} className="flex justify-between gap-3">
              <span className="text-slate-200">{memberName(c.member)}<StatusBadge m={c.member} /></span>
              <span className="text-xs text-slate-500 font-mono whitespace-nowrap">{c.geo_id} · {Math.round(c.share_of_this * 100)}%</span>
            </li>
          ))}
        </ul>
        {minor.length > 0 && <div className="text-xs text-slate-500">+ edges of {minor.map(c => c.geo_id).join(', ')} (&lt;5%)</div>}
      </div>
      {!compact && (
        <div className="grid grid-cols-2 gap-x-3 gap-y-1 pt-1 border-t border-premium-700">
          {d.figures.map(o => (
            <div key={o.obs_id} className="text-xs">
              <div className="text-slate-500 truncate">{o.label}</div>
              <div className={`font-mono ${o.flags.includes('suppressed_cv') ? 'text-slate-500 italic' : 'text-cyan-300'}`}>
                {fmt(o)}{o.moe !== null && <span className="text-slate-500"> ±{fmt({ value: o.moe, unit: o.unit })}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
      {compact && d.figures.slice(0, 3).map(o => (
        <div key={o.obs_id} className="flex justify-between text-xs"><span className="text-slate-400">{o.label}</span><span className="font-mono text-cyan-300">{fmt(o)}</span></div>
      ))}
      {d.top_program && <div className="text-xs text-slate-400">Top program match: <span className="text-slate-200">{d.top_program}</span></div>}
    </div>
  );
}

export function MapTab({ geos, geo, office, onPick, onOpen }: {
  geos: Geo[]; geo: string; office: string | null; onPick: (g: string) => void; onOpen: (g: string) => void;
}) {
  const defaultChamber: Chamber = (office ?? geo).startsWith('SD') ? 'sldu' : 'sldl';
  const [chamber, setChamber] = useState<Chamber>(defaultChamber);
  const [indicator, setIndicator] = useState('pct_below_fpl');
  const [indicators, setIndicators] = useState<{ indicator: string; label: string; unit: string }[]>([]);
  const [summary, setSummary] = useState<Record<Chamber, MapSummary | null>>({ sldl: null, sldu: null });
  const [values, setValues] = useState<Record<string, number | null>>({});
  const [hover, setHover] = useState<{ id: string; x: number; y: number } | null>(null);
  const [selected, setSelected] = useState<string | null>(geo.startsWith(defaultChamber === 'sldl' ? 'HD' : 'SD') ? geo : null);
  const [basemap, setBasemap] = useState<'imagery' | 'streets'>('imagery');
  const [showOfficial, setShowOfficial] = useState(true);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [error, setError] = useState('');
  const [layersVersion, setLayersVersion] = useState(0);

  const el = useRef<HTMLDivElement>(null);
  const tooltipHost = useRef<HTMLDivElement>(null);
  const ctx = useRef<any>({});            // ArcGIS objects: view, modules, layers, highlight handles

  // data
  useEffect(() => { api.indicators().then(xs => setIndicators(xs.filter(i => (i.unit !== 'count' || i.indicator === 'total_pop') && i.topic !== 'employment_trend'))); }, []);
  useEffect(() => {
    (['sldl', 'sldu'] as Chamber[]).forEach(c => api.mapSummary(c).then(s => setSummary(p => ({ ...p, [c]: s }))));
  }, []);
  useEffect(() => {
    api.mapLayer(indicator, chamber).then(d => setValues(Object.fromEntries(d.features.map(f => [f.geo_id, f.value]))));
  }, [indicator, chamber]);
  const byId = useMemo(() => Object.fromEntries((summary[chamber]?.districts ?? []).map(d => [d.geo_id, d])), [summary, chamber]);
  const unit = indicators.find(i => i.indicator === indicator)?.unit ?? 'pct';
  const breaks = useMemo(() => {
    const v = Object.values(values).filter((x): x is number => x !== null).sort((a, b) => a - b);
    return v.length ? [0.2, 0.4, 0.6, 0.8].map(q => v[Math.floor(q * (v.length - 1))]) : [];
  }, [values]);

  // map: init once
  useEffect(() => {
    let destroyed = false;
    (async () => {
      try {
        const $a = await loadSdk();
        const [EsriMap, MapView, GeoJSONLayer, FeatureLayer, TileLayer, Basemap, esriConfig, Extent] = await $a.import([
          '@arcgis/core/Map.js', '@arcgis/core/views/MapView.js', '@arcgis/core/layers/GeoJSONLayer.js',
          '@arcgis/core/layers/FeatureLayer.js', '@arcgis/core/layers/TileLayer.js', '@arcgis/core/Basemap.js',
          '@arcgis/core/config.js', '@arcgis/core/geometry/Extent.js']);
        if (destroyed || !el.current) return;
        if (API_KEY) esriConfig.apiKey = API_KEY;
        const basemaps = {
          imagery: API_KEY ? 'arcgis/imagery' : new Basemap({ baseLayers: [new TileLayer({ url: IMAGERY })], title: 'World Imagery' }),
          streets: API_KEY ? 'arcgis/navigation' : 'osm',
        };
        const map = new EsriMap({ basemap: basemaps.imagery });
        const view = new MapView({
          container: el.current, map, center: [-157.5, 20.6], zoom: 7, constraints: { minZoom: 6 },
          popupEnabled: false, ui: { components: ['zoom', 'attribution'] },
        });
        try { view.highlightOptions = { color: '#22d3ee', fillOpacity: 0.25, haloOpacity: 1 }; } catch { /* newer SDKs use view.highlights */ }
        ctx.current = { $a, view, map, GeoJSONLayer, FeatureLayer, Extent, basemaps, layers: {} };
        await view.when();
        if (!destroyed) setStatus('ready');
      } catch (e: any) {
        if (!destroyed) { setStatus('error'); setError(String(e?.message ?? e)); }
      }
    })();
    return () => { destroyed = true; ctx.current.view?.destroy(); ctx.current = {}; };
  }, []);

  // basemap
  useEffect(() => { const c = ctx.current; if (status === 'ready') c.map.basemap = c.basemaps[basemap]; }, [basemap, status]);

  // data + official layers whenever chamber / indicator values change
  useEffect(() => {
    const c = ctx.current;
    if (status !== 'ready' || !Object.keys(values).length) return;
    let cancelled = false;
    (async () => {
      const gj = await (await fetch(`/geo/${chamber}.geojson`)).json();
      gj.features.forEach((f: any) => { f.properties.value = values[f.properties.geo_id] ?? null; });
      const url = URL.createObjectURL(new Blob([JSON.stringify(gj)], { type: 'application/json' }));
      const sym = (color: string) => ({ type: 'simple-fill', color: color + 'b3', outline: { color: [0, 0, 0, 0], width: 0 } });
      const edges = [-Infinity, ...breaks, Infinity];
      const data = new c.GeoJSONLayer({
        url, title: 'District data', outFields: ['*'],
        renderer: {
          type: 'class-breaks', field: 'value',
          defaultSymbol: { type: 'simple-fill', color: [100, 116, 139, 0.4], outline: { color: [255, 255, 255, 0.5], width: 0.6 } },
          classBreakInfos: RAMP.map((col, i) => ({ minValue: edges[i], maxValue: edges[i + 1], symbol: sym(col) })),
        },
      });
      const official = new c.FeatureLayer({
        url: `${STATE_GIS}/${LAYER_ID[chamber]}`, title: 'Official 2022 boundaries (Hawaiʻi Statewide GIS Program)',
        visible: showOfficial, popupEnabled: false,
        renderer: { type: 'simple', symbol: { type: 'simple-fill', color: [0, 0, 0, 0], outline: { color: [255, 255, 255, 0.95], width: 1.1 } } },
      });
      if (cancelled) return;
      c.hoverHL?.remove(); c.selHL?.remove(); c.hoverHL = c.selHL = null; c.dataView = null; c.graphics = null;
      c.map.removeMany(Object.values(c.layers));
      c.map.addMany([data, official]);
      c.layers = { data, official };
      c.dataView = await c.view.whenLayerView(data);
      // Index graphics by geo_id for highlighting
      const q = await data.queryFeatures({ where: '1=1', outFields: ['geo_id'], returnGeometry: true });
      c.graphics = Object.fromEntries(q.features.map((g: any) => [g.attributes.geo_id, g]));
      setLayersVersion(v => v + 1);
      URL.revokeObjectURL(url);
    })().catch(e => console.warn('map layer error', e));
    return () => { cancelled = true; };
  }, [status, chamber, values, breaks]);

  useEffect(() => { const l = ctx.current.layers?.official; if (l) l.visible = showOfficial; }, [showOfficial]);

  // hover + click
  useEffect(() => {
    const c = ctx.current;
    if (status !== 'ready') return;
    let seq = 0;
    const hit = async (e: any) => {
      const my = ++seq;
      if (!c.layers?.data || c.view?.destroyed) return;
      let r: any;
      try { r = await c.view.hitTest(e, { include: [c.layers.data] }); } catch { return; }
      if (my !== seq) return;
      const g = r.results.find((x: any) => x.graphic?.attributes?.geo_id)?.graphic;
      return g?.attributes?.geo_id as string | undefined;
    };
    const move = c.view.on('pointer-move', async (e: any) => {
      if (isTouch()) return;
      const id = await hit(e);
      c.hoverHL?.remove(); c.hoverHL = null;
      if (id && c.graphics?.[id] && c.dataView) { c.hoverHL = c.dataView.highlight(c.graphics[id]); setHover({ id, x: e.x, y: e.y }); el.current!.style.cursor = 'pointer'; }
      else { setHover(null); el.current!.style.cursor = ''; }
    });
    const leave = c.view.on('pointer-leave', () => { c.hoverHL?.remove(); c.hoverHL = null; setHover(null); });
    const click = c.view.on('click', async (e: any) => { const id = await hit(e); if (id) { setSelected(id); onPick(id); } });
    const dbl = c.view.on('double-click', async (e: any) => { const id = await hit(e); if (id) { e.stopPropagation(); onOpen(id); } });
    return () => { move.remove(); leave.remove(); click.remove(); dbl.remove(); };
  }, [status]);

  // selection + office outline
  useEffect(() => {
    const c = ctx.current;
    if (!c.dataView || !c.graphics) return;
    c.selHL?.remove();
    const ids = [selected, office].filter((x): x is string => !!x && !!c.graphics[x]);
    c.selHL = ids.length ? c.dataView.highlight(ids.map(i => c.graphics[i])) : null;
  }, [selected, office, layersVersion]);

  // chamber switch keeps the selection meaningful: jump to the biggest counterpart
  const switchChamber = (next: Chamber) => {
    if (next === chamber) return;
    const cur = selected ? byId[selected] : undefined;
    const nextSel = cur?.counterparts[0]?.geo_id ?? null;
    setChamber(next); setSelected(nextSel); setHover(null);
  };

  const zoomExtent = ([xmin, ymin, xmax, ymax]: number[]) =>
    ctx.current.view?.goTo(new ctx.current.Extent({ xmin, ymin, xmax, ymax, spatialReference: { wkid: 4326 } }))
      .catch((e: any) => console.warn('goTo', e));
  const zoomTo = (id: string) => { const g = ctx.current.graphics?.[id]; if (g) ctx.current.view.goTo(g.geometry.extent.expand(1.6)); };
  const sel = selected ? byId[selected] : null;
  const hov = hover ? byId[hover.id] : null;
  const roster = summary[chamber]?.roster;

  return (
    <div className="grid grid-cols-12 gap-4 h-[calc(100vh-11rem)] min-h-[520px]">
      <div className="col-span-12 lg:col-span-8 xl:col-span-9 relative rounded-xl overflow-hidden border border-premium-800">
        <div ref={el} className="absolute inset-0" role="application" aria-label={`Map of Hawaiʻi ${chamber === 'sldl' ? 'House' : 'Senate'} districts`} />

        {/* controls */}
        <div className="absolute top-3 left-14 right-3 flex flex-wrap gap-2 items-start pointer-events-none">
          <div className="pointer-events-auto flex bg-premium-900/90 border border-premium-700 rounded-lg p-0.5" role="group" aria-label="Chamber">
            {(['sldl', 'sldu'] as Chamber[]).map(c => (
              <button key={c} onClick={() => switchChamber(c)} aria-pressed={chamber === c}
                className={`px-3 py-1 rounded-md text-xs font-medium ${chamber === c ? 'bg-cyan-700 text-white' : 'text-slate-300 hover:text-white'}`}>
                {c === 'sldl' ? 'House (51)' : 'Senate (25)'}
              </button>
            ))}
          </div>
          <select value={indicator} onChange={e => setIndicator(e.target.value)} aria-label="Indicator to map"
            className="pointer-events-auto bg-premium-900/90 border border-premium-700 rounded-lg px-2 py-1 text-xs text-slate-200 max-w-[16rem]">
            {indicators.map(i => <option key={i.indicator} value={i.indicator}>{i.label}</option>)}
          </select>
          <div className="pointer-events-auto flex items-center gap-1 bg-premium-900/90 border border-premium-700 rounded-lg px-2 py-1 text-xs">
            <Layers className="w-3.5 h-3.5 text-slate-400" />
            <select value={basemap} onChange={e => setBasemap(e.target.value as any)} aria-label="Basemap" className="bg-transparent text-slate-200">
              <option value="imagery">Satellite</option><option value="streets">Streets</option>
            </select>
            <label className="ml-2 flex items-center gap-1 text-slate-300">
              <input type="checkbox" checked={showOfficial} onChange={e => setShowOfficial(e.target.checked)} /> Official lines
            </label>
          </div>
        </div>

        {/* island quick zoom */}
        <div className="absolute top-14 left-14 flex flex-wrap gap-1" role="group" aria-label="Zoom to island">
          {ISLANDS.map(([n, ext]) => (
            <button key={n} onClick={() => zoomExtent(ext)} className="px-2 py-0.5 rounded-md text-[11px] bg-premium-900/90 border border-premium-700 text-slate-300 hover:text-white">{n}</button>
          ))}
        </div>

        {/* legend */}
        <div className="absolute bottom-8 left-3 bg-premium-900/90 border border-premium-700 rounded-lg px-3 py-2 text-xs">
          <div className="text-slate-300 mb-1">{indicators.find(i => i.indicator === indicator)?.label}</div>
          <div className="flex items-center gap-1">
            {RAMP.map((c, i) => <span key={c} className="w-7 h-3 rounded-sm" style={{ background: c }} title={i === 0 ? `< ${fmt({ value: breaks[0], unit })}` : `≥ ${fmt({ value: breaks[i - 1], unit })}`} />)}
          </div>
          <div className="flex justify-between text-slate-500 font-mono mt-0.5">
            <span>{breaks.length ? fmt({ value: breaks[0], unit }) : ''}</span><span>{breaks.length ? fmt({ value: breaks[3], unit }) : ''}</span>
          </div>
          <div className="text-slate-500 mt-1">Quintiles across {chamber === 'sldl' ? 'House' : 'Senate'} districts · ACS 2020–2024</div>
        </div>

        {/* hover card (desktop) */}
        {hov && hover && (
          <div ref={tooltipHost} className="absolute z-10 w-72 p-3 rounded-lg bg-premium-900/95 border border-cyan-800 shadow-2xl pointer-events-none"
            style={{ left: Math.min(hover.x + 16, (el.current?.clientWidth ?? 800) - 300), top: Math.max(8, Math.min(hover.y + 16, (el.current?.clientHeight ?? 600) - 440)) }}>
            <DistrictCard d={hov} chamber={chamber} compact />
            <div className="text-[10px] text-slate-500 mt-2">Click to pin · double-click to open profile</div>
          </div>
        )}

        {status === 'loading' && <div className="absolute inset-0 flex items-center justify-center text-sm text-slate-400">Loading ArcGIS map…</div>}
        {status === 'error' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-sm text-slate-300 gap-2 p-6 text-center">
            <div>The map could not load ({error}).</div>
            <div className="text-xs text-slate-500">Check that js.arcgis.com and geodata.hawaii.gov are reachable from this network.</div>
          </div>
        )}
      </div>

      {/* side panel */}
      <div className="col-span-12 lg:col-span-4 xl:col-span-3 space-y-4 overflow-y-auto">
        <Card title={sel ? 'Selected district' : 'Districts'} right={sel && (
          <div className="flex gap-1">
            <button onClick={() => zoomTo(sel.geo_id)} className="text-xs px-2 py-0.5 rounded border border-premium-700 hover:text-cyan-300" aria-label="Zoom to district"><MapPin className="w-3 h-3" /></button>
            <button onClick={() => onOpen(sel.geo_id)} className="text-xs px-2 py-0.5 rounded border border-cyan-800 text-cyan-300 hover:bg-cyan-950">Open profile</button>
          </div>)}>
          {sel ? <DistrictCard d={sel} chamber={chamber} /> : (
            <p className="text-sm text-slate-400">{isTouch() ? 'Tap' : 'Hover over'} a district to see who represents it. {isTouch() ? '' : 'Click to pin it here.'}</p>
          )}
          {office && office === sel?.geo_id && <div className="mt-2 text-xs text-amber-300 flex items-center gap-1"><Star className="w-3 h-3" /> Your office</div>}
        </Card>
        <Card title="About this map">
          <ul className="text-xs text-slate-400 space-y-1.5 list-disc ml-4">
            <li>Boundaries: 2022 reapportionment plan, from the Hawaiʻi Statewide GIS Program ArcGIS service (white lines).</li>
            <li>House and Senate districts do not nest. Overlap shares are by land area until population weights are added.</li>
            <li>District numbers are State Legislature districts. County council and Oʻahu neighborhood board numbers are different and are listed separately.</li>
            {summary[chamber]?.local_method && <li>{summary[chamber]!.local_method}</li>}
            <li>Legislators as of {roster?.as_of ?? '—'}, taken from Office of Elections final reports and the Legislature roster.
              {roster && (roster.counts.secondary || roster.counts.pending || roster.counts.verify) ? (
                <> {roster.counts.secondary ?? 0} seats are still to be confirmed against official records, {roster.counts.pending ?? 0} are pending and {roster.counts.verify ?? 0} need review.</>) : null}
            </li>
            <li>Party affiliation is intentionally not shown.</li>
          </ul>
          <a className="mt-2 inline-flex items-center gap-1 text-xs text-cyan-400 hover:underline" href={`${STATE_GIS}/${LAYER_ID[chamber]}`} target="_blank" rel="noreferrer">
            Boundary service <ExternalLink className="w-3 h-3" /></a>
        </Card>
        <Card title="All districts">
          <ul className="text-xs max-h-64 overflow-y-auto divide-y divide-premium-800">
            {(summary[chamber]?.districts ?? []).map(d => (
              <li key={d.geo_id}>
                <button onClick={() => { setSelected(d.geo_id); zoomTo(d.geo_id); onPick(d.geo_id); }}
                  className={`w-full text-left py-1.5 flex justify-between gap-2 hover:text-cyan-300 ${d.geo_id === selected ? 'text-cyan-300' : 'text-slate-300'}`}>
                  <span>{d.geo_id}{d.geo_id === office && <Star className="inline w-3 h-3 ml-1 text-amber-300" />}</span>
                  <span className="truncate">{memberName(d.member)}</span>
                </button>
              </li>
            ))}
          </ul>
        </Card>
        <Pill>Esri ArcGIS Maps SDK · Hawaiʻi Statewide GIS</Pill>
      </div>
    </div>
  );
}
