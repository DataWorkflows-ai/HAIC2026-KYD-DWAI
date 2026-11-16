import { useEffect, useState } from 'react';
import { ExternalLink } from 'lucide-react';
import { api, type CrossProgram, type ProgramContext } from './api';
import { Card, Empty, Pill } from './ui';

const n = (v: number | null | undefined) => (v === null || v === undefined ? 'n/a' : Math.round(v).toLocaleString());
const tone = { high: 'emerald', medium: 'cyan', low: 'amber' } as const;

/** "Likely eligible for other programs": one published rule applied to district counts, per row. */
export function CrossProgramCard({ geo }: { geo: string }) {
  const [d, setD] = useState<CrossProgram | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  useEffect(() => { setD(null); api.crossProgram(geo).then(setD).catch(() => setD({ geo_id: geo, estimates: [], note: '' })); }, [geo]);
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
  useEffect(() => { setC(null); api.programContext(geo).then(setC).catch(() => setC(null)); }, [geo]);
  if (!c) return null;
  const mq = c.medquest, t = c.tanf_island, s = c.county_snap, u = c.tanf_underenrollment;
  const maxTrend = Math.max(...mq.trend.map(x => x.recipients));
  return (
    <>
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
