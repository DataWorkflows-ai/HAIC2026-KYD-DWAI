/**
 * Small SVG choropleth for the Rankings tab (KLEAR-style map over a ranked table).
 * The column the table is sorted by colors the map; hovering or clicking a district in either one highlights it in both.
 * Uses the bundled, simplified 2022 district shapes (/geo/{sldl,sldu}.geojson) and needs no map service.
 */
import { useEffect, useMemo, useState } from 'react';
import { fmt } from './api';

const RAMP = ['#1e3a8a', '#2563eb', '#a855f7', '#ec4899', '#f97316'];
const VIEWS: Record<string, [number, number, number, number]> = {      // lon/lat boxes
  State: [-160.3, 18.85, -154.75, 22.3], 'Oʻahu': [-158.3, 21.24, -157.62, 21.73],
  'Maui Nui': [-157.35, 20.5, -155.95, 21.25], 'Hawaiʻi': [-156.1, 18.9, -154.75, 20.3], 'Kauaʻi': [-160.3, 21.8, -159.25, 22.27],
};
const K = Math.cos((20.8 * Math.PI) / 180);                           // equirectangular, corrected at Hawaiʻi's latitude
type Feature = { id: string; rings: number[][][] };

export function RankMap({ chamber, values, unit, label, active, onHover, onPick }: {
  chamber: 'sldl' | 'sldu'; values: Record<string, number | null>; unit: string; label: string;
  active: string | null; onHover: (g: string | null) => void; onPick: (g: string) => void;
}) {
  const [features, setFeatures] = useState<Feature[]>([]);
  const [view, setView] = useState('State');
  useEffect(() => {
    fetch(`/geo/${chamber}.geojson`).then(r => r.json()).then(gj => setFeatures(gj.features.map((f: any) => ({
      id: f.properties.geo_id,
      rings: f.geometry.type === 'Polygon' ? f.geometry.coordinates : f.geometry.coordinates.flat(),
    }))));
  }, [chamber]);
  const breaks = useMemo(() => {
    const v = Object.values(values).filter((x): x is number => x !== null).sort((a, b) => a - b);
    return v.length ? [0.2, 0.4, 0.6, 0.8].map(q => v[Math.floor(q * (v.length - 1))]) : [];
  }, [values]);
  const color = (v: number | null | undefined) => v === null || v === undefined ? '#475569' : RAMP[breaks.filter(b => v >= b).length];
  const [x0, y0, x1, y1] = VIEWS[view];
  const W = 1000, H = Math.round(((y1 - y0) / ((x1 - x0) * K)) * W);
  const path = (rings: number[][][]) => rings.map(r => 'M' + r.map(([lon, lat]) =>
    `${(((lon - x0) * K) / ((x1 - x0) * K)) * W},${((y1 - lat) / (y1 - y0)) * H}`).join('L') + 'Z').join('');
  const legend = breaks.length ? [`< ${fmt({ value: breaks[0], unit })}`, ...[0, 1, 2].map(i => `${fmt({ value: breaks[i], unit })}–${fmt({ value: breaks[i + 1], unit })}`), `≥ ${fmt({ value: breaks[3], unit })}`] : [];
  const hv = active ? values[active] : undefined;

  return (
    <div className="mb-4">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
        <div className="text-sm text-slate-300">Map of <span className="text-cyan-300">{label}</span>
          {active && <span className="ml-2 text-xs text-slate-400">{active}: <span className="font-mono text-cyan-300">{hv === null || hv === undefined ? 'no data' : fmt({ value: hv, unit })}</span></span>}</div>
        <div className="no-print flex gap-1">{Object.keys(VIEWS).map(v => (
          <button key={v} onClick={() => setView(v)} aria-pressed={view === v}
            className={`px-2 py-0.5 rounded text-[11px] border ${view === v ? 'border-cyan-700 text-cyan-300' : 'border-premium-700 text-slate-400 hover:text-slate-200'}`}>{v}</button>))}
        </div>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-h-[42vh] rounded-lg bg-[#06132a]" role="img" aria-label={`Map of ${label} by district`}
        onMouseLeave={() => onHover(null)}>
        {features.map(f => (
          <path key={f.id} d={path(f.rings)} fill={color(values[f.id])} fillOpacity={0.85}
            stroke={f.id === active ? '#22d3ee' : '#e2e8f0'} strokeWidth={f.id === active ? 3 : 0.6} vectorEffect="non-scaling-stroke"
            className="cursor-pointer" onMouseEnter={() => onHover(f.id)} onClick={() => onPick(f.id)}>
            <title>{`${f.id}: ${values[f.id] === null || values[f.id] === undefined ? 'no data' : fmt({ value: values[f.id] as number, unit })}`}</title>
          </path>))}
        {active && features.filter(f => f.id === active).map(f => (
          <path key="hl" d={path(f.rings)} fill="none" stroke="#22d3ee" strokeWidth={3} vectorEffect="non-scaling-stroke" pointerEvents="none" />))}
      </svg>
      <div className="mt-1 grid grid-cols-5 gap-1 max-w-xl">
        {RAMP.map((c, i) => (
          <div key={c}><div className="h-2.5 rounded-sm" style={{ background: c }} />
            <div className="text-[10px] text-slate-400 font-mono text-center leading-tight mt-0.5">{legend[i] ?? ''}</div></div>))}
      </div>
    </div>
  );
}
