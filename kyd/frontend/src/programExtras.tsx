import { useEffect, useState } from 'react';
import { ExternalLink } from 'lucide-react';
import { api, type BRow, type CrossProgram, type Obs, type ProgramContext, type Unemployment, type UptakePeers } from './api';
import { Card, Empty, Figure, Pill } from './ui';

const n = (v: number | null | undefined) => (v === null || v === undefined ? 'n/a' : Math.round(v).toLocaleString());
const tone = { high: 'emerald', medium: 'cyan', low: 'amber' } as const;

/** "Likely eligible for other programs": one published rule applied to district counts, per row. */
export function CrossProgramCard({ geo }: { geo: string }) {
  const [d, setD] = useState<CrossProgram | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  useEffect(() => { let live = true; setD(null); api.crossProgram(geo).then(x => live && setD(x)).catch(() => live && setD({ geo_id: geo, estimates: [], note: '' })); return () => { live = false; }; }, [geo]);
  if (!d) return <Card title="Likely eligible for other programs"><Empty>Loading…</Empty></Card>;
  return (
    <Card title="Likely eligible for other programs" right={<Pill>from SNAP + income counts</Pill>} className="col-span-full">
      <p className="text-xs text-slate-400 mb-3">Each row applies one published eligibility rule to this district's Census counts.
        SNAP households automatically meet the income test for several programs; income limits are applied to the poverty ladder.</p>
      {!d.estimates.length && <Empty>No estimates for this geography.</Empty>}
      <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
        {d.estimates.map(e => (
          <div key={e.program_id} className="rounded-lg border border-premium-700 p-3">
            <div className="flex items-start justify-between gap-2">
              <div className="text-sm text-slate-100">{e.name}</div>
              <Pill tone={tone[e.confidence]}>{e.confidence}</Pill>
            </div>
            <div className="mt-1 font-mono text-2xl text-cyan-300">~{n(e.estimate)}</div>
            <div className="text-xs text-slate-400">{e.unit}
              {e.low !== null && e.high !== null && e.low !== e.high && <> · range {n(e.low)}–{n(e.high)}</>}
              {e.low !== null && e.high === null && <> · at least</>}</div>
            <p className="mt-2 text-xs text-slate-300">{e.rule}</p>
            <button onClick={() => setOpen(open === e.program_id ? null : e.program_id)}
              className="mt-2 block text-xs text-cyan-400 hover:underline" aria-expanded={open === e.program_id}>
              {open === e.program_id ? 'Hide method' : 'Show method'}</button>
            {open === e.program_id && (
              <div className="mt-2 text-xs text-slate-400 space-y-1">
                <div><span className="text-slate-300">Formula:</span> {e.formula}</div>
                <ul className="list-disc ml-4">{e.assumptions.map(a => <li key={a}>{a}</li>)}</ul>
                <div className="font-mono text-slate-500 break-all">{e.input_obs_ids.map(i => `obs:${i}`).join(' · ')}</div>
              </div>
            )}
            <a href={e.source.url} target="_blank" rel="noreferrer" className="mt-2 flex items-center gap-1 text-xs text-cyan-400 hover:underline">
              {e.source.title} <ExternalLink className="w-3 h-3" /></a>
          </div>
        ))}
      </div>
      {d.note && <p className="mt-3 text-xs text-slate-500">{d.note}</p>}
    </Card>
  );
}

/** Figures DHS publishes by island or county, not by district: shown as context for this district's island. */
export function ProgramContextCards({ geo }: { geo: string }) {
  const [c, setC] = useState<ProgramContext | null>(null);
  useEffect(() => { let live = true; setC(null); api.programContext(geo).then(x => live && setC(x)).catch(() => live && setC(null)); return () => { live = false; }; }, [geo]);
  if (!c) return null;
  const mq = c.medquest, t = c.tanf_island, s = c.county_snap, u = c.tanf_underenrollment;
  const maxTrend = Math.max(...mq.trend.map(x => x.recipients));
  return (
    <>
      {c.crime && c.crime.district.length > 0 && <CrimeCard k={c.crime} />}
      {c.employment.district.length > 0 && <EmploymentCard e={c.employment} county={c.county} />}
      <UnemploymentBreakdown geo={geo} county={c.county} />
      {c.school_meals.observations.length > 0 && (
        <Card title={<span className="normal-case">{c.school_meals.title}</span>} right={<Pill>schools in district</Pill>}>
          <div className="space-y-2">
            {c.school_meals.observations.map(o => (
              <div key={o.indicator} className="flex items-baseline justify-between gap-2">
                <span className="text-xs text-slate-400">{o.label}</span><Figure o={o} />
              </div>
            ))}
          </div>
          {c.school_meals.state_pct !== null && <p className="mt-2 text-xs text-slate-400">State: {c.school_meals.state_pct}% of public-school students.</p>}
          <p className="mt-1 text-xs text-slate-500">{c.school_meals.note}</p>
          <a href={c.school_meals.url} target="_blank" rel="noreferrer" className="mt-1 flex items-center gap-1 text-xs text-cyan-400 hover:underline">
            {c.school_meals.source} <ExternalLink className="w-3 h-3" /></a>
        </Card>
      )}
      {c.test_scores && c.test_scores.observations.length > 0 && (
        <Card title={<span className="normal-case">{c.test_scores.title}</span>} right={<Pill>schools in district</Pill>}>
          <div className="space-y-2">
            {c.test_scores.observations.map(o => (
              <div key={o.indicator} className="flex items-baseline justify-between gap-2">
                <span className="text-xs text-slate-400">{o.label}</span>
                <span className="flex items-baseline gap-2"><Figure o={o} />
                  {c.test_scores.state[o.indicator] != null && <span className="text-xs text-slate-500">State {c.test_scores.state[o.indicator]}%</span>}</span>
              </div>
            ))}
          </div>
          <p className="mt-2 text-xs text-slate-500">{c.test_scores.note}</p>
          <a href={c.test_scores.url} target="_blank" rel="noreferrer" className="mt-1 flex items-center gap-1 text-xs text-cyan-400 hover:underline">
            {c.test_scores.source} <ExternalLink className="w-3 h-3" /></a>
        </Card>
      )}
      {c.vital && c.vital.observations.length > 0 && <VitalCard v={c.vital} />}
      {c.hpha && (
        <Card title={<span className="normal-case">HPHA public housing in this district</span>} right={<Pill>{c.hpha.properties.length} properties · {c.hpha.units.toLocaleString()} units</Pill>}>
          {c.hpha.properties.length === 0 ? <p className="text-sm text-slate-400">No HPHA public housing property is located in this district.</p> : (
            <ul className="text-sm divide-y divide-premium-800 max-h-64 overflow-y-auto">
              {c.hpha.properties.map(p => (
                <li key={p.name + p.address} className="py-1.5 flex justify-between gap-3">
                  <span><span className="text-slate-100">{p.name}</span>
                    <span className="block text-xs text-slate-500">{p.address}, {p.city} · {p.funding}{p.elderly ? ', elderly' : ''}</span></span>
                  <span className="font-mono text-cyan-300 whitespace-nowrap">{p.units} units</span>
                </li>))}
            </ul>)}
          {c.hpha.state_units > 0 && <p className="mt-2 text-xs text-slate-400">{c.hpha.state_units} of these units are state-funded and do not appear in HUD's figures.</p>}
          <ul className="mt-1 text-xs text-slate-500 list-disc ml-4 space-y-0.5">{c.hpha.caveats.map(t => <li key={t}>{t}</li>)}</ul>
          <a href={c.hpha.url} target="_blank" rel="noreferrer" className="mt-1 flex items-center gap-1 text-xs text-cyan-400 hover:underline">{c.hpha.source} <ExternalLink className="w-3 h-3" /></a>
        </Card>
      )}
      {c.hud.observations.length > 0 && (
        <Card title={<span className="normal-case">{c.hud.title}</span>} right={<Pill>as of {c.hud.as_of}</Pill>} className="col-span-full">
          <div className="grid sm:grid-cols-3 lg:grid-cols-7 gap-3">
            {c.hud.observations.map(o => (
              <div key={o.indicator}>
                <div className="text-xs text-slate-400 min-h-[2rem]">{o.label}</div>
                <Figure o={o} />
              </div>
            ))}
          </div>
          {c.hud.state_per_1k_hh !== null && <p className="mt-2 text-xs text-slate-400">State: {c.hud.state_per_1k_hh.toFixed(1)} subsidized units per 1,000 households.</p>}
          <p className="mt-1 text-xs text-slate-500">{c.hud.source}. {c.hud.caveats.join(' ')}</p>
        </Card>
      )}
      <h3 className="col-span-full mt-2 text-xs font-semibold text-slate-400 uppercase tracking-wide">Island & statewide context · {c.county} County</h3>
      <Card title={<span className="normal-case">{mq.title}</span>} right={<Pill>SFY {mq.sfy}</Pill>}>
        <table className="w-full text-sm">
          <tbody>
            {mq.islands.map(i => (
              <tr key={i.island} className="border-b border-premium-800">
                <td className="py-1 text-slate-300">{i.island}</td>
                <td className="py-1 text-right font-mono text-cyan-300">{n(i.recipients)}</td>
                <td className="py-1 text-right text-xs text-slate-500">{i.share_of_state_percent}% of state</td>
              </tr>
            ))}
            <tr><td className="py-1 text-slate-400">Statewide</td><td className="py-1 text-right font-mono text-slate-200">{n(mq.statewide)}</td><td /></tr>
          </tbody>
        </table>
        <div className="mt-3 flex items-end gap-1 h-12" aria-label="Statewide Med-QUEST enrollment, SFY 2015 to 2025">
          {mq.trend.map(x => (
            <div key={x.sfy} title={`SFY ${x.sfy}: ${n(x.recipients)}`} className="flex-1 bg-cyan-800/70 rounded-sm"
              style={{ height: `${(x.recipients / maxTrend) * 100}%` }} />
          ))}
        </div>
        <div className="flex justify-between text-[10px] text-slate-500 font-mono"><span>{mq.trend[0]?.sfy}</span><span>{mq.trend[mq.trend.length - 1]?.sfy}</span></div>
        <p className="mt-2 text-xs text-slate-500">{mq.source} {mq.caveats.join(' ')}</p>
      </Card>
      <Card title={<span className="normal-case">{t.title}</span>} right={<Pill>{t.month}</Pill>}>
        {t.tanf_persons !== undefined ? (
          <div className="space-y-1 text-sm">
            <div className="text-slate-300">{t.county}</div>
            <div><span className="font-mono text-2xl text-cyan-300">{n(t.tanf_persons)}</span> <span className="text-xs text-slate-400">people on TANF</span></div>
            <div className="text-xs text-slate-400">{t.tanf_per_1000} per 1,000 residents · county poverty rate {t.poverty_rate_percent}%</div>
          </div>
        ) : <Empty>No TANF figure for this county.</Empty>}
        <p className="mt-2 text-xs text-slate-500">{t.source}. {t.note}</p>
      </Card>
      <Card title={<span className="normal-case">{s.title}</span>} right={<Pill>{s.month}</Pill>}>
        <table className="w-full text-sm">
          <thead><tr className="text-xs text-slate-500"><th className="text-left font-normal">Area</th><th className="text-right font-normal">Households</th><th className="text-right font-normal">People</th></tr></thead>
          <tbody>{s.rows.map(r => (
            <tr key={r.area} className="border-b border-premium-800">
              <td className="py-1 text-slate-300">{r.area}</td>
              <td className="py-1 text-right font-mono text-cyan-300">{n(r.households)}</td>
              <td className="py-1 text-right font-mono text-slate-300">{n(r.persons)}</td>
            </tr>))}</tbody>
        </table>
        <p className="mt-2 text-xs text-slate-500">{s.source}</p>
      </Card>
      {c.facts.length > 0 && <ProgramFacts facts={c.facts} />}
      {u.available && (
        <Card title={<span className="normal-case">{u.title}</span>} className="md:col-span-2 xl:col-span-3">
          <p className="text-xs text-slate-400 mb-2">Share of this district's people below poverty in each group, compared with that group's share of TANF
            recipients statewide. A positive gap means the group is a larger part of local need than of statewide TANF enrollment.</p>
          <table className="w-full text-sm">
            <thead><tr className="text-xs text-slate-500"><th className="text-left font-normal">Group</th><th className="text-right font-normal">Below poverty</th>
              <th className="text-right font-normal">District share</th><th className="text-right font-normal">Statewide TANF share</th><th className="text-right font-normal">Gap (pts)</th></tr></thead>
            <tbody>{u.groups.map(g => (
              <tr key={g.label} className="border-b border-premium-800" title={g.note}>
                <td className="py-1 text-slate-300">{g.label}</td>
                <td className="py-1 text-right font-mono">{n(g.poverty_count)}</td>
                <td className="py-1 text-right font-mono">{g.district_poverty_share_percent ?? 'n/a'}%</td>
                <td className="py-1 text-right font-mono">{g.statewide_tanf_share_percent}%</td>
                <td className={`py-1 text-right font-mono ${(g.under_enrollment_pp ?? 0) > 0 ? 'text-amber-300' : 'text-slate-400'}`}>
                  {g.under_enrollment_pp === null ? 'n/a' : (g.under_enrollment_pp > 0 ? '+' : '') + g.under_enrollment_pp}</td>
              </tr>))}</tbody>
          </table>
          <p className="mt-2 text-xs text-slate-500">{u.caveats.join(' ')}</p>
        </Card>
      )}
    </>
  );
}

/** Statewide income limits and latest enrollment for each program, with the source for each row. */
function ProgramFacts({ facts }: { facts: ProgramContext['facts'] }) {
  const [open, setOpen] = useState(false);
  const shown = open ? facts : facts.slice(0, 6);
  return (
    <Card title="Program facts (statewide)" right={<Pill>{facts.length} programs</Pill>} className="col-span-full">
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead><tr className="text-slate-500 text-left">
            <th className="font-normal py-1 pr-3">Program</th><th className="font-normal pr-3">Income rule</th>
            <th className="font-normal pr-3">Limit, 1 person</th><th className="font-normal pr-3">Limit, 4 people</th>
            <th className="font-normal pr-3">Latest enrollment</th><th className="font-normal">Source</th></tr></thead>
          <tbody>{shown.map(f => (
            <tr key={f.program} className="border-b border-premium-800 align-top">
              <td className="py-1 pr-3 text-slate-200">{f.program}<div className="text-slate-500">{f.agency}</div></td>
              <td className="pr-3 text-slate-300">{f.income_rule}</td>
              <td className="pr-3 font-mono text-slate-300">{f.limit_1_person}</td>
              <td className="pr-3 font-mono text-slate-300">{f.limit_4_person}</td>
              <td className="pr-3 text-cyan-300">{f.enrollment_latest}</td>
              <td>{f.link && <a href={f.link} target="_blank" rel="noreferrer" className="text-cyan-400 hover:underline inline-flex items-center gap-1">link <ExternalLink className="w-3 h-3" /></a>}</td>
            </tr>))}</tbody>
        </table>
      </div>
      {facts.length > 6 && <button onClick={() => setOpen(!open)} className="mt-2 text-xs text-cyan-400 hover:underline">{open ? 'Show fewer' : `Show all ${facts.length}`}</button>}
      <p className="mt-2 text-xs text-slate-500">Compiled by the team's research agents from each agency's published charts and reports; every row links to its source. Statewide figures, not district enrollment.</p>
    </Card>
  );
}

/** Current unemployment: district (DBEDT tract estimates rolled up), county and state LAUS, ACS for comparison, 2014–2025 trend. */
function EmploymentCard({ e, county }: { e: ProgramContext['employment']; county: string }) {
  const rate = (xs: Obs[]) => xs.find(o => o.indicator === 'laus_unemp_rate');
  const d = rate(e.district), c = rate(e.county), s = rate(e.state);
  const acs = e.district.find(o => o.indicator === 'unemployment_rate');
  const lf = e.district.find(o => o.indicator === 'laus_labor_force');
  const max = Math.max(...e.trend.flatMap(t => [t.county ?? 0, t.state ?? 0]), 1);
  return (
    <Card title="Unemployment" right={<Pill>2025 annual avg</Pill>} className="md:col-span-2">
      <div className="grid grid-cols-3 gap-3 text-sm">
        <div><div className="text-xs text-slate-400">This district</div>{d && <Figure o={d} big />}
          {lf && <div className="text-xs text-slate-500">labor force <Figure o={lf} /></div>}</div>
        <div><div className="text-xs text-slate-400">{county} County</div>{c && <Figure o={c} big />}</div>
        <div><div className="text-xs text-slate-400">State</div>{s && <Figure o={s} big />}</div>
      </div>
      {acs && <div className="mt-2 text-xs text-slate-400">ACS 2020–2024 five-year rate for comparison: <Figure o={acs} /></div>}
      <div className="mt-3 text-xs text-slate-400">County (cyan) and state (gray), 2014–2025</div>
      <div className="flex items-end gap-1 h-16 mt-1" aria-label="Unemployment rate trend 2014 to 2025">
        {e.trend.map(t => (
          <div key={t.year} className="flex-1 h-full flex items-end gap-px" title={`${t.year}: county ${t.county ?? 'n/a'}%, state ${t.state ?? 'n/a'}%`}>
            <div className="flex-1 bg-cyan-700/80 rounded-sm" style={{ height: `${((t.county ?? 0) / max) * 100}%` }} />
            <div className="flex-1 bg-slate-600 rounded-sm" style={{ height: `${((t.state ?? 0) / max) * 100}%` }} />
          </div>
        ))}
      </div>
      <div className="flex justify-between text-[10px] text-slate-500 font-mono"><span>{e.trend[0]?.year}</span><span>2020 peak {e.trend.find(t => t.year === 2020)?.state ?? ''}%</span><span>{e.trend[e.trend.length - 1]?.year}</span></div>
      <ul className="mt-2 text-xs text-slate-500 list-disc ml-4">{e.notes.map(n => <li key={n}>{n}</li>)}</ul>
      <div className="text-xs text-slate-500">{e.source}</div>
    </Card>
  );
}

/** Who is unemployed: district vs county vs state by sex, age, race/ethnicity, education (ACS 2020–2024). */
function UnemploymentBreakdown({ geo, county }: { geo: string; county: string }) {
  const [u, setU] = useState<Unemployment | null>(null);
  const [dim, setDim] = useState('sex');
  useEffect(() => { let live = true; setU(null); api.unemployment(geo).then(x => live && setU(x)).catch(() => live && setU(null)); return () => { live = false; }; }, [geo]);
  if (!u) return null;
  const cell = (r?: BRow) => {
    if (!r || r.value === null) return <span className="text-slate-600">n/a</span>;
    const weak = r.flags.includes('suppressed_cv');
    return <span className={`font-mono ${weak ? 'text-slate-500 italic' : 'text-cyan-300'}`} title={weak ? 'High uncertainty (CV ≥ 30%)' : `${r.source_table} · obs:${r.obs_id}`}>
      {r.value.toFixed(1)}%<span className="text-[10px] text-slate-500"> ±{r.moe?.toFixed(1)}</span>{weak && ' ⚠'}</span>;
  };
  const key = (r: BRow) => `${r.group}|${r.sex}`;
  const byKey = (xs?: BRow[]) => Object.fromEntries((xs ?? []).map(r => [key(r), r]));
  const ct = byKey(u.county[dim]), st = byKey(u.state[dim]);
  const overall = (x: Record<string, BRow[]>) => x.overall?.[0];
  return (
    <Card title={<span className="normal-case">Who is unemployed (ACS 2020–2024)</span>} right={<Pill>90% margins</Pill>}>
      <div className="flex flex-wrap gap-1 mb-2">
        {Object.entries(u.dimensions).filter(([d]) => d !== 'overall').map(([d, t]) => (
          <button key={d} onClick={() => setDim(d)} aria-pressed={dim === d}
            className={`px-2 py-0.5 rounded text-xs border ${dim === d ? 'border-cyan-700 text-cyan-300' : 'border-premium-700 text-slate-400'}`}>{t.replace('By ', '')}</button>))}
      </div>
      <table className="w-full text-xs">
        <thead><tr className="text-slate-500"><th className="text-left font-normal">Group</th><th className="text-right font-normal">District</th>
          <th className="text-right font-normal">{county} Co.</th><th className="text-right font-normal">State</th></tr></thead>
        <tbody>
          <tr className="border-b border-premium-800"><td className="py-1 text-slate-300">All workers 16+</td>
            <td className="text-right whitespace-nowrap pl-2">{cell(overall(u.rows))}</td><td className="text-right whitespace-nowrap pl-2">{cell(overall(u.county))}</td><td className="text-right whitespace-nowrap pl-2">{cell(overall(u.state))}</td></tr>
          {(u.rows[dim] ?? []).map(r => (
            <tr key={key(r)} className="border-b border-premium-800">
              <td className="py-1 text-slate-300">{r.label}</td><td className="text-right whitespace-nowrap pl-2">{cell(r)}</td>
              <td className="text-right whitespace-nowrap pl-2">{cell(ct[key(r)])}</td><td className="text-right whitespace-nowrap pl-2">{cell(st[key(r)])}</td></tr>))}
        </tbody>
      </table>
      <ul className="mt-2 text-[11px] text-slate-500 list-disc ml-4">{u.notes.map(n => <li key={n}>{n}</li>)}</ul>
    </Card>
  );
}

/** Oʻahu crime by district, ESTIMATE from HPD beat counts × traced beat→district shares. */
function CrimeCard({ k }: { k: NonNullable<ProgramContext['crime']> }) {
  const get = (xs: Obs[], id: string) => xs.find(o => o.indicator === id);
  const max = Math.max(...k.trend.map(t => t.district ?? 0), 1);
  return (
    <Card title={<span className="normal-case">{k.title}</span>} right={<Pill tone="amber">ESTIMATE</Pill>} className="md:col-span-2">
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {k.district.map(o => (
          <div key={o.indicator}><div className="text-xs text-slate-400 min-h-[2rem]">{o.label.replace(` (ESTIMATE, Oʻahu)`, '').replace(', 2025', '')}</div><Figure o={o} /></div>
        ))}
      </div>
      {k.oahu_median_per_1k !== null && <p className="mt-2 text-xs text-slate-400">Median Oʻahu district: {k.oahu_median_per_1k.toFixed(1)} offenses per 1,000 residents.
        {' '}City &amp; County official 2025 (HPD Table 1): {get(k.honolulu_official, 'crime_total_est') && <Figure o={get(k.honolulu_official, 'crime_total_est')!} />} index offenses.</p>}
      <div className="mt-3 text-xs text-slate-400">District index offenses, {k.trend[0]?.year}–{k.trend[k.trend.length - 1]?.year} (estimate)</div>
      <div className="flex items-end gap-1 h-14 mt-1" aria-label="Estimated index offenses by year">
        {k.trend.map(t => <div key={t.year} title={`${t.year}: ${t.district ?? 'n/a'}`} className="flex-1 h-full flex items-end">
          <div className="w-full bg-amber-700/70 rounded-sm" style={{ height: `${((t.district ?? 0) / max) * 100}%` }} /></div>)}
      </div>
      <div className="flex justify-between text-[10px] text-slate-500 font-mono"><span>{k.trend[0]?.year}</span><span>{k.trend[k.trend.length - 1]?.year}</span></div>
      <ul className="mt-2 text-[11px] text-slate-500 list-disc ml-4">{k.caveats.map(c => <li key={c}>{c}</li>)}</ul>
      <div className="text-[11px] text-slate-500">Source: {k.credit}.</div>
    </Card>
  );
}

/** Districts with similar need that reach more of it with SNAP (estimate). */
export function UptakePeersCard({ geo, onPick }: { geo: string; onPick?: (g: string) => void }) {
  const [d, setD] = useState<UptakePeers | null>(null);
  useEffect(() => { let live = true; setD(null); api.uptakePeers(geo).then(x => live && setD(x)).catch(() => live && setD(null)); return () => { live = false; }; }, [geo]);
  if (!d || !d.need || !d.gap) return null;
  return (
    <Card title={<span className="normal-case">SNAP uptake: similar districts that reach more</span>} right={<Pill tone="amber">ESTIMATE</Pill>} className="col-span-full">
      <p className="text-sm text-slate-300">
        In {d.name}, <Figure o={d.need} /> of residents are below 200% of poverty, and about <Figure o={d.gap} /> of them are not in SNAP households.
      </p>
      {d.peers.length === 0 ? (
        <p className="mt-2 text-sm text-slate-400">No district with similar need reaches noticeably more of it, so this district is already at or near the top of its peer group.</p>
      ) : (
        <table className="mt-3 w-full text-sm">
          <thead className="text-xs text-slate-500 text-left"><tr><th className="py-1">Peer district</th><th>Below 200% of poverty</th><th>Not in SNAP</th><th>More people reached at the peer's rate</th></tr></thead>
          <tbody>
            {d.peers.map(p => (
              <tr key={p.geo_id} className="border-t border-premium-800">
                <td className="py-1.5">{onPick ? <button onClick={() => onPick(p.geo_id)} className="text-slate-100 hover:text-cyan-300 hover:underline">{p.name}</button> : p.name}</td>
                <td><Figure o={p.need} /></td><td><Figure o={p.gap} /></td>
                <td><Figure o={p.more_reached} /></td>
              </tr>))}
          </tbody>
        </table>
      )}
      <p className="mt-2 text-xs text-slate-500">{d.note} Differences can reflect household makeup and survey error as well as outreach, so treat these as leads to ask about, not proof.</p>
    </Card>
  );
}

/** Births and deaths by district (ESTIMATE): 2020–2024 averages, crude rates vs state, and the 2000–2024 series. */
function VitalCard({ v }: { v: ProgramContext['vital'] }) {
  const pts = v.trend.filter(t => t.births !== null && t.deaths !== null) as { year: number; births: number; deaths: number }[];
  const max = Math.max(1, ...pts.flatMap(t => [t.births, t.deaths]));
  const W = 300, H = 90, x = (i: number) => (i / Math.max(1, pts.length - 1)) * W, y = (n: number) => H - (n / max) * (H - 6);
  const line = (k: 'births' | 'deaths') => pts.map((t, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(t[k]).toFixed(1)}`).join('');
  const rate = (k: string) => v.state[k];
  return (
    <Card title={<span className="normal-case">{v.title}</span>} right={<Pill tone="amber">ESTIMATE</Pill>}>
      <div className="space-y-2">
        {v.observations.map(o => (
          <div key={o.indicator} className="flex items-baseline justify-between gap-2">
            <span className="text-xs text-slate-400">{o.label.replace(/\s*\(ESTIMATE[^)]*\)/, '')}</span>
            <span className="flex items-baseline gap-2 whitespace-nowrap"><Figure o={o} />
              {rate(o.indicator) != null && o.unit === 'per_1000' && <span className="text-xs text-slate-500">State {rate(o.indicator)}</span>}</span>
          </div>))}
      </div>
      {pts.length > 1 && (
        <div className="mt-3">
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-24" role="img" aria-label="Births and deaths per year, 2000 to 2024">
            <path d={line('births')} fill="none" stroke="#00bcff" strokeWidth={2} />
            <path d={line('deaths')} fill="none" stroke="#f97316" strokeWidth={2} />
          </svg>
          <div className="flex justify-between text-[10px] text-slate-500 font-mono"><span>{pts[0].year}</span>
            <span><span className="text-cyan-400">— births</span> · <span className="text-orange-400">— deaths</span></span><span>{pts[pts.length - 1].year}</span></div>
        </div>
      )}
      <ul className="mt-2 text-xs text-slate-500 list-disc ml-4 space-y-0.5">{v.caveats.map(t => <li key={t}>{t}</li>)}</ul>
      <a href={v.url} target="_blank" rel="noreferrer" className="mt-1 flex items-center gap-1 text-xs text-cyan-400 hover:underline">{v.source} <ExternalLink className="w-3 h-3" /></a>
    </Card>
  );
}
