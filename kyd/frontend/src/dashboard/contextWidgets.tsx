import { ExternalLink } from 'lucide-react';
import { api, type Member, type ProgramContext } from '../api';
import { Empty, Figure, Pill } from '../ui';
import { useProfile } from './districtWidgets';
import { chamberOf, Gate, Go, Note, Spark, useLoad } from './shared';
import type { Series, WidgetProps } from './types';

const useContext = (g: string) => useLoad(`context:${g}`, () => api.programContext(g));
const OAHU_ONLY = 'Not available for this county. Crime estimates cover Oʻahu districts only.';

function TrendBody({ c, series }: { c: ProgramContext; series: Series }) {
  switch (series) {
    case 'unemployment': {
      const e = c.employment, rate = (xs: typeof e.district) => xs.find(o => o.indicator === 'laus_unemp_rate');
      const d = rate(e.district), co = rate(e.county), st = rate(e.state);
      return <>
        <div className="text-xs text-slate-400 mb-1">Unemployment rate</div>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-400 mb-2">
          {d && <span>District <Figure o={d} /></span>}{co && <span>{c.county} Co. <Figure o={co} /></span>}{st && <span>State <Figure o={st} /></span>}
        </div>
        <Spark xs={e.trend.map(t => t.year)} label="Unemployment rate trend, county and state"
          series={[{ name: 'county', color: '#00bcff', ys: e.trend.map(t => t.county) }, { name: 'state', color: '#94a3b8', ys: e.trend.map(t => t.state) }]} />
        <Note>{e.source}</Note>
      </>;
    }
    case 'crime':
      if (!c.crime) return <Empty>{OAHU_ONLY}</Empty>;
      return <>
        <div className="flex items-center gap-2 text-xs text-slate-400 mb-1">Index offenses in the district <Pill tone="amber">Oʻahu estimate</Pill></div>
        <Spark xs={c.crime.trend.map(t => t.year)} label="Estimated index offenses by year"
          series={[{ name: 'district', color: '#f97316', ys: c.crime.trend.map(t => t.district) }]} />
        <Note>Source: {c.crime.credit}.</Note>
      </>;
    case 'vital':
      return <>
        <div className="flex items-center gap-2 text-xs text-slate-400 mb-1">Births and deaths per year <Pill tone="amber">ESTIMATE</Pill></div>
        <Spark xs={c.vital.trend.map(t => t.year)} label="Births and deaths per year"
          series={[{ name: 'births', color: '#00bcff', ys: c.vital.trend.map(t => t.births) }, { name: 'deaths', color: '#f97316', ys: c.vital.trend.map(t => t.deaths) }]} />
        <Note>{c.vital.source}</Note>
      </>;
    default: { const never: never = series; return never; }
  }
}

export function TrendsWidget({ w, geo }: WidgetProps) {
  const l = useContext(geo);
  return <Gate l={l}>{c => <TrendBody c={c} series={w.config.series ?? 'unemployment'} />}</Gate>;
}

export function CrimeWidget({ geo }: WidgetProps) {
  const l = useContext(geo);
  return <Gate l={l}>{c => {
    const k = c.crime;
    if (!k || !k.district.length) return <Empty>{OAHU_ONLY}</Empty>;
    return <>
      <div className="flex items-center gap-2 mb-2 text-xs text-slate-400">{k.title} <Pill tone="amber">Oʻahu estimate</Pill></div>
      <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(8rem, 1fr))' }}>
        {k.district.map(o => <div key={o.indicator}><div className="text-[11px] text-slate-400">{o.label.replace(' (ESTIMATE, Oʻahu)', '')}</div><Figure o={o} /></div>)}
      </div>
      <ul className="mt-2 text-[11px] text-slate-500 list-disc ml-4 space-y-0.5">{k.caveats.map(t => <li key={t}>{t}</li>)}</ul>
      <Note>Source: {k.credit}.</Note>
    </>;
  }}</Gate>;
}

export function SchoolsWidget({ geo }: WidgetProps) {
  const l = useContext(geo);
  return <Gate l={l}>{c => {
    const m = c.school_meals, t = c.test_scores;
    return <>
      <div className="text-xs font-semibold text-slate-300 mb-1">{m.title}</div>
      {m.observations.length ? m.observations.map(o => (
        <div key={o.indicator} className="flex items-baseline justify-between gap-2 text-xs"><span className="text-slate-400">{o.label}</span><Figure o={o} /></div>))
        : <Empty>No school meals figures for this geography.</Empty>}
      {m.state_pct !== null && <div className="text-[11px] text-slate-500">State: {m.state_pct}% of public-school students</div>}
      <div className="text-xs font-semibold text-slate-300 mt-3 mb-1">{t?.title ?? 'Test scores'}</div>
      {t?.observations.length ? t.observations.map(o => (
        <div key={o.indicator} className="flex items-baseline justify-between gap-2 text-xs"><span className="text-slate-400">{o.label}</span>
          <span className="whitespace-nowrap"><Figure o={o} />{t.state[o.indicator] != null && <span className="ml-2 text-slate-500">State {t.state[o.indicator]}%</span>}</span></div>))
        : <Empty>No test score figures for this geography.</Empty>}
      <Note>District-level rollups of the schools in the district. By-school and by-grade results: not yet loaded.</Note>
    </>;
  }}</Gate>;
}

export function HousingWidget({ geo }: WidgetProps) {
  const l = useContext(geo), p = useProfile(geo);
  const rb = p.data?.observations.find(o => o.indicator === 'pct_rent_burden_30'), rbs = p.data?.comparisons.state?.find(o => o.indicator === 'pct_rent_burden_30');
  return <Gate l={l}>{c => <>
    {rb && <div className="text-xs text-slate-400 mb-2">{rb.label}: <Figure o={rb} />{rbs && geo !== 'HI' && <span className="ml-2">State <Figure o={rbs} /></span>}</div>}
    <div className="text-xs font-semibold text-slate-300 mb-1">{c.hud.title} <span className="font-normal text-slate-500">as of {c.hud.as_of}</span></div>
    {c.hud.observations.length ? <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(8rem, 1fr))' }}>
      {c.hud.observations.map(o => <div key={o.indicator}><div className="text-[11px] text-slate-400">{o.label}</div><Figure o={o} /></div>)}
    </div> : <Empty>No HUD-assisted housing figures for this geography.</Empty>}
    {c.hud.state_per_1k_hh !== null && <div className="text-[11px] text-slate-500 mt-1">State: {c.hud.state_per_1k_hh.toFixed(1)} subsidized units per 1,000 households</div>}
    <div className="mt-2 text-xs text-slate-400">HPHA public housing: <span className="font-mono text-cyan-300">{c.hpha.units.toLocaleString()}</span> units in {c.hpha.properties.length} properties
      <a href={c.hpha.url} target="_blank" rel="noreferrer" className="ml-1 inline-flex text-cyan-400"><ExternalLink className="w-3 h-3" /></a></div>
    <Note>{c.hud.source}.</Note>
  </>}</Gate>;
}

const who = (m: Member | null) => m?.name ? `${m.title} ${m.name}` : 'Not on file';
export function RepsWidget({ w, geo, ctx }: WidgetProps) {
  const ch = chamberOf(geo) ?? w.config.chamber ?? 'sldl';
  const l = useLoad(`summary:${ch}`, () => api.mapSummary(ch));
  if (!chamberOf(geo)) return <Empty>Pick a House or Senate district in this widget's settings.</Empty>;
  return <Gate l={l}>{s => {
    const d = s.districts.find(x => x.geo_id === geo);
    if (!d) return <Empty>No roster entry for {geo}.</Empty>;
    return <>
      <div className="text-xs text-slate-400">{d.name}</div>
      <div className="text-sm text-slate-100">{who(d.member)}{d.member && d.member.status !== 'official' && <span className="ml-2"><Pill tone="amber">{d.member.status}</Pill></span>}</div>
      {d.counterparts.length > 0 && <>
        <div className="mt-2 text-[11px] uppercase tracking-wide text-slate-500">Overlapping {ch === 'sldl' ? 'Senate' : 'House'} districts</div>
        <ul className="text-xs space-y-0.5">{d.counterparts.map(c => (
          <li key={c.geo_id} className="flex justify-between gap-2"><button onClick={() => ctx.onOpen('overview', c.geo_id)} className="text-slate-300 hover:text-cyan-300 text-left">{c.geo_id} · {who(c.member)}</button>
            <span className="text-slate-500 font-mono">{Math.round(c.share_of_this * 100)}%</span></li>))}</ul>
        <Note>Share of this district's population inside each overlapping district.</Note>
      </>}
      <Note>Roster as of {s.roster.as_of}.</Note>
      <Go onClick={() => ctx.onOpen('map', geo)}>Open Map</Go>
    </>;
  }}</Gate>;
}
