import { useMemo, useState } from 'react';
import { ExternalLink } from 'lucide-react';
import { api, type RangeEnd } from '../api';
import { Empty, Figure, Pill } from '../ui';
import { RankMap } from '../RankMap';
import { by, chamberOf, Gate, Go, Note, useLoad } from './shared';
import type { WidgetProps } from './types';

const HEADLINE = ['total_pop', 'median_hh_income', 'pct_below_fpl', 'pct_uninsured', 'pct_65plus', 'pct_rent_burden_30'];
export const useProfile = (g: string) => useLoad(`profile:${g}`, () => api.profile(g));
export const usePrograms = (g: string) => useLoad(`programs:${g}`, () => api.programs(g));

export function SnapshotWidget({ geo, ctx }: WidgetProps) {
  const l = useProfile(geo);
  return <Gate l={l}>{p => {
    const me = by(p.observations), st = by(p.comparisons.state);
    const shown = HEADLINE.filter(k => me[k]);
    return <>
      <div className="text-sm text-slate-100 mb-2">{p.geography.name} <span className="text-xs text-slate-500">ACS {p.data_as_of}</span></div>
      {!shown.length && <Empty>No headline figures for this geography.</Empty>}
      <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(8.5rem, 1fr))' }}>
        {shown.map(k => (
          <div key={k} className="rounded-lg bg-black/30 p-2">
            <div className="text-[11px] text-slate-400 mb-0.5 truncate" title={me[k].label}>{me[k].label}</div>
            <Figure o={me[k]} big />
            {st[k] && geo !== 'HI' && <div className="text-[11px] text-slate-500">State <Figure o={st[k]} /></div>}
          </div>))}
      </div>
      <Go onClick={() => ctx.onOpen('overview', geo)}>Open Overview</Go>
    </>;
  }}</Gate>;
}

export function KpiWidget({ w, geo }: WidgetProps) {
  const ind = w.config.indicator || 'pct_below_fpl';
  const l = useProfile(geo);
  return <Gate l={l}>{p => {
    const o = p.observations.find(x => x.indicator === ind), st = p.comparisons.state?.find(x => x.indicator === ind),
      co = p.comparisons.county?.find(x => x.indicator === ind);
    if (!o) return <Empty>{ind} is not published for {p.geography.name}.</Empty>;
    return <>
      <div className="text-xs text-slate-400">{o.label}</div>
      <div className="text-[11px] text-slate-500 mb-1">{p.geography.name}</div>
      <Figure o={o} big />
      <div className="mt-2 space-y-0.5 text-xs text-slate-400">
        {co && <div>County <Figure o={co} /></div>}
        {st && geo !== 'HI' && <div>State <Figure o={st} /></div>}
      </div>
    </>;
  }}</Gate>;
}

export function RankWidget({ w, geo, ctx }: WidgetProps) {
  const ch = chamberOf(geo) ?? w.config.chamber ?? 'sldl';
  const l = useLoad(`rankings:${ch}`, () => api.rankings(ch));
  if (!chamberOf(geo)) return <Empty>Rankings cover House and Senate districts. Pick one in this widget's settings.</Empty>;
  return <Gate l={l}>{d => {
    const row = d.rows.find(r => r.geo_id === geo);
    if (!row) return <Empty>No ranking row for {geo}.</Empty>;
    return <>
      <div className="text-sm text-slate-100 mb-2">{row.name} <span className="text-xs text-slate-500">among {d.rows.length} {ch === 'sldl' ? 'House' : 'Senate'} districts</span></div>
      <table className="w-full text-xs">
        <tbody>{d.columns.map(c => {
          const cell = row.cells[c.indicator];
          return <tr key={c.indicator} className="border-t border-premium-800">
            <td className="py-1 pr-2 text-slate-300">{c.label}{c.kind === 'estimate' && <span className="ml-1"><Pill tone="amber">EST</Pill></span>}</td>
            <td className="py-1 whitespace-nowrap">{cell ? <Figure o={cell.obs} /> : <span className="text-slate-600">—</span>}</td>
            <td className="py-1 text-right whitespace-nowrap text-slate-400 font-mono">{cell?.rank ? `#${cell.rank} of ${c.ranked}` : 'unranked'}</td>
          </tr>;
        })}</tbody>
      </table>
      <Note>Rank 1 is the highest value. Districts whose margins overlap may not truly differ in rank.</Note>
      <Go onClick={() => ctx.onOpen('rankings', geo)}>Open Rankings</Go>
    </>;
  }}</Gate>;
}

export function MinimapWidget({ w, geo, ctx }: WidgetProps) {
  const ch = w.config.chamber ?? chamberOf(geo) ?? 'sldl', ind = w.config.indicator || 'pct_below_fpl';
  const l = useLoad(`layer:${ind}:${ch}`, () => api.mapLayer(ind, ch));
  const [hover, setHover] = useState<string | null>(null);
  const values = useMemo(() => Object.fromEntries((l.data?.features ?? []).map(o => [o.geo_id, o.value])), [l.data]);
  return <Gate l={l}>{d => {
    const first = d.features[0], mine = d.features.find(o => o.geo_id === geo);
    if (!first) return <Empty>No map data for {ind}.</Empty>;
    return <>
      {mine && <div className="text-xs text-slate-400 mb-1">{geo}: <Figure o={mine} /></div>}
      <RankMap chamber={ch} values={values} unit={first.unit} label={first.label} active={hover ?? (mine ? geo : null)}
        onHover={setHover} onPick={g => ctx.onOpen('map', g)} />
      <Note>Click a district to open it on the Map tab.</Note>
    </>;
  }}</Gate>;
}

function End({ e, side }: { e: RangeEnd; side: string }) {
  return (
    <div className="min-w-0 rounded border border-premium-700 p-2">
      <div className="text-[10px] uppercase tracking-wide text-slate-500">{side} · grade {e.grade}</div>
      <div className="text-[11px] text-slate-400 truncate" title={e.basis}>{e.basis}</div>
      <Figure o={e.persons} />
      {e.share && <div className="text-[11px] text-slate-500"><Figure o={e.share} /> of people below 200% FPL</div>}
    </div>
  );
}

export function SnapWidget({ geo, ctx }: WidgetProps) {
  const l = usePrograms(geo);
  const peers = useLoad(`peers:${geo}`, () => api.uptakePeers(geo));
  return <Gate l={l}>{ms => {
    const m = ms.find(x => x.gap_range && /snap/i.test(x.program.program_id)) ?? ms.find(x => x.gap_range);
    const p = peers.data;
    return <>
      {m?.gap_range ? <>
        <div className="text-xs text-amber-300 mb-1">{m.program.name}: people who look eligible but are not enrolled (a range)</div>
        <div className="grid grid-cols-2 gap-2"><End e={m.gap_range.low} side="Low end" /><End e={m.gap_range.high} side="High end" /></div>
        <Note>{m.gap_range.is_not}</Note>
      </> : <Empty>No SNAP gap range for this geography.</Empty>}
      {p?.gap && p.need && <p className="mt-2 text-xs text-slate-300">Below 200% of poverty: <Figure o={p.need} />; not in SNAP households: <Figure o={p.gap} />.</p>}
      {p && <p className="mt-1 text-xs text-slate-400">{p.peers.length
        ? <>{p.peers.length} district{p.peers.length > 1 ? 's' : ''} with similar need reach more people with SNAP (estimate).</>
        : 'No similar-need district reaches noticeably more with SNAP.'}</p>}
      <Go onClick={() => ctx.onOpen('programs', geo)}>Open Programs</Go>
    </>;
  }}</Gate>;
}

export function ProgramsWidget({ geo, ctx }: WidgetProps) {
  const l = usePrograms(geo);
  return <Gate l={l}>{ms => <>
    {!ms.length && <Empty>No program matches.</Empty>}
    <ol className="space-y-1.5">{ms.slice(0, 5).map((m, i) => (
      <li key={m.program.program_id} className="text-sm">
        <span className="text-slate-500 mr-1.5">{i + 1}.</span>
        <a href={m.program.official_url} target="_blank" rel="noreferrer" className="text-slate-100 hover:text-cyan-300 inline-flex items-center gap-1">
          {m.program.name}<ExternalLink className="w-3 h-3 text-slate-500" /></a>
        {m.rationale[0] && <div className="text-[11px] text-slate-500 ml-5">{m.rationale[0]}</div>}
      </li>))}
    </ol>
    <Note>Population-level matches, not individual eligibility.</Note>
    <Go onClick={() => ctx.onOpen('programs', geo)}>Open Programs</Go>
  </>}</Gate>;
}
