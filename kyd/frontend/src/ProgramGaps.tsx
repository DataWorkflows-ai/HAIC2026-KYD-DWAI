import { useEffect, useMemo, useRef, useState } from 'react';
import { ExternalLink } from 'lucide-react';
import { api, fmt, type GapSchoolRow, type Obs, type ProgramGaps } from './api';
import { Card, Empty, ExportButtons, Figure, Pill } from './ui';

const n = (v: number | null | undefined) => v == null ? 'n/a' : Math.round(v).toLocaleString();
const pct = (row: GapSchoolRow) => row.enrollment ? ((100 * row.free_reduced / row.enrollment).toFixed(1) + '%') : 'n/a';
const cepLabel = (s: string) => s.replace(/_/g, ' ');

function bar(enrolled?: Obs | null, eligible?: Obs | null, gap?: Obs | null) {
  const e = enrolled?.value ?? 0, g = gap?.value ?? 0, total = eligible?.value ?? (e + g);
  const w = Math.max(total ?? 0, e + g, 1);
  return (
    <div className="mt-2" aria-label="Eligible versus enrolled bar">
      <div className="h-3 rounded-full overflow-hidden bg-premium-800 flex">
        <div className="bg-emerald-500" style={{ width: `${Math.min(100, 100 * e / w)}%` }} />
        <div className="bg-amber-500" style={{ width: `${Math.min(100, 100 * g / w)}%` }} />
      </div>
      <div className="mt-1 flex gap-3 text-[11px] text-slate-500"><span>enrolled/served</span><span>gap/range</span></div>
    </div>
  );
}

export function ProgramGapsTab({ geo }: { geo: string }) {
  const [d, setD] = useState<ProgramGaps | null>(null);
  const [err, setErr] = useState('');
  useEffect(() => { let live = true; setErr(''); api.programGaps(geo).then(x => live && setD(x)).catch(e => { if (live) setErr(String(e.message ?? e)); }); return () => { live = false; }; }, [geo]);
  if (err) return <Empty>{err}</Empty>;
  if (!d) return <Empty>Loading program gaps...</Empty>;
  const ranked = [...d.rows].filter(r => r.gap?.value || r.range_high?.value)
    .sort((a, b) => ((b.gap?.value ?? b.range_high?.value ?? 0) - (a.gap?.value ?? a.range_high?.value ?? 0))).slice(0, 6);
  return (
    <div className="grid grid-cols-12 gap-4">
      <Card className="col-span-12" title="Program Gaps" right={<Pill tone="amber">informational only</Pill>}>
        <p className="text-sm text-slate-300">{d.disclaimer}</p>
        <p className="mt-1 text-xs text-slate-500">Every figure cites source/year/geography. District values are public aggregate estimates; agency rules decide individual eligibility.</p>
      </Card>
      <Card className="col-span-12 lg:col-span-8" title="Eligible vs enrolled / reached">
        <div className="grid md:grid-cols-2 gap-3">
          {d.rows.map(r => (
            <div key={r.program_id} className="rounded-lg border border-premium-800 p-3">
              <div className="flex items-start justify-between gap-2">
                <div><div className="font-semibold text-slate-100">{r.name}</div><div className="text-xs text-slate-500">{r.geography}</div></div>
                <Pill tone={r.unavailable ? 'slate' : r.basis.includes('District') ? 'cyan' : 'amber'}>{r.basis}</Pill>
              </div>
              {r.unavailable ? <p className="mt-2 text-sm text-slate-400">{r.unavailable}</p> : (
                <>
                  <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                    {r.eligible && <div><span className="text-slate-500">Eligible/proxy</span><br /><Figure o={r.eligible} /></div>}
                    {r.enrolled && <div><span className="text-slate-500">Enrolled/reached</span><br /><Figure o={r.enrolled} /></div>}
                    {r.gap && <div><span className="text-slate-500">Gap</span><br /><Figure o={r.gap} /></div>}
                    {r.reach && <div><span className="text-slate-500">Reach</span><br /><Figure o={r.reach} /></div>}
                    {(r.range_low || r.range_high) && <div className="col-span-2"><span className="text-slate-500">Range</span><br />
                      {r.range_low && <Figure o={r.range_low} />}{r.range_low && r.range_high && <span className="text-slate-500"> to </span>}{r.range_high && <Figure o={r.range_high} />}</div>}
                  </div>
                  {bar(r.enrolled, r.eligible, r.gap ?? r.range_high)}
                </>
              )}
              <ul className="mt-2 text-[11px] text-slate-500 list-disc ml-4">{r.caveats.map(c => <li key={c}>{c}</li>)}</ul>
              <a className="mt-2 inline-flex items-center gap-1 text-xs text-cyan-400 hover:underline" href={r.official_url} target="_blank" rel="noreferrer">
                Official program page <ExternalLink className="w-3 h-3" /></a>
            </div>
          ))}
        </div>
      </Card>
      <Card className="col-span-12 lg:col-span-4" title="Largest visible gaps">
        <ol className="space-y-2">
          {ranked.map(r => <li key={r.program_id} className="text-sm flex justify-between gap-3">
            <span className="text-slate-200">{r.name}</span>
            <span className="font-mono text-amber-300">{n(r.gap?.value ?? r.range_high?.value)} {r.unit}</span>
          </li>)}
        </ol>
        <p className="mt-3 text-xs text-slate-500">Map-ready gap indicators: {d.map_indicators.join(', ')}. Open the Map tab and choose one of these indicators to shade districts.</p>
      </Card>
      <div className="col-span-12"><SchoolDetailsCard data={d} /></div>
      <div className="col-span-12"><CepDetailsCard data={d} /></div>
    </div>
  );
}

export function SchoolDetailsCard({ data }: { data: ProgramGaps }) {
  return <SchoolTable title="Schools in this geography (October eligibility rows)" rows={data.school_meals.rows} totals={data.school_meals.totals}
    name={`kyd_${data.geo_id}_school_meals`} />;
}

export function CepDetailsCard({ data }: { data: ProgramGaps }) {
  const not = data.cep.eligible_not_participating;
  const part = data.cep.participating;
  return (
    <div className="grid lg:grid-cols-2 gap-4">
      <SchoolTable title="CEP-eligible, not participating" rows={not.rows} totals={not.totals} name={`kyd_${data.geo_id}_cep_not_participating`} />
      <SchoolTable title="CEP participating schools" rows={part.rows} totals={part.totals} name={`kyd_${data.geo_id}_cep_participating`} />
    </div>
  );
}

function SchoolTable({ title, rows, totals, name }: { title: string; rows: GapSchoolRow[]; totals: ProgramGaps['school_meals']['totals']; name: string }) {
  const table = useRef<HTMLTableElement>(null);
  const [sort, setSort] = useState<keyof GapSchoolRow>('school_name');
  const [dir, setDir] = useState<1 | -1>(1);
  const shown = useMemo(() => [...rows].sort((a, b) => {
    const av = a[sort], bv = b[sort];
    const cmp = typeof av === 'number' && typeof bv === 'number' ? av - bv : String(av).localeCompare(String(bv));
    return cmp * dir;
  }), [rows, sort, dir]);
  const head = (key: keyof GapSchoolRow, label: string) => (
    <button className="hover:text-cyan-300" onClick={() => { setDir(sort === key ? (dir === 1 ? -1 : 1) : 1); setSort(key); }}>{label}</button>
  );
  return (
    <Card title={title} right={<ExportButtons table={table} name={name} />}>
      <div className="mb-2 flex flex-wrap gap-3 text-xs text-slate-400">
        <span>{totals.schools} schools</span><span>{n(totals.enrollment)} enrollment</span>
        <span>{n(totals.free_reduced)} free/reduced eligible</span><span>{n(totals.uncertified)} not certified</span>
      </div>
      {!rows.length ? <Empty>No school rows for this geography.</Empty> : (
        <div className="max-h-96 overflow-auto">
          <table ref={table} className="w-full text-xs">
            <thead className="sticky top-0 bg-premium-900 text-slate-500 text-left">
              <tr><th className="py-1 pr-3">{head('school_name', 'School')}</th><th className="pr-3">Districts</th><th className="pr-3">{head('complex_area', 'Complex / island')}</th>
                <th className="text-right pr-3">{head('enrollment', 'Enroll')}</th><th className="text-right pr-3">{head('free_reduced', 'F/R')}</th>
                <th className="text-right pr-3">F/R %</th><th className="pr-3">{head('cep_status', 'CEP status')}</th><th>Source/year</th></tr>
            </thead>
            <tbody>
              {shown.map((r, i) => (
                <tr key={`${r.school_name}-${i}`} className="border-t border-premium-800 align-top">
                  <td className="py-1.5 pr-3 text-slate-200">{r.school_name}</td>
                  <td className="pr-3 font-mono text-slate-400">{r.house || '—'} / {r.senate || '—'}</td>
                  <td className="pr-3 text-slate-400">{r.complex_area || r.island_or_district || '—'}</td>
                  <td className="text-right pr-3 font-mono">{n(r.enrollment)}</td>
                  <td className="text-right pr-3 font-mono">{n(r.free_reduced)}</td>
                  <td className="text-right pr-3 font-mono">{pct(r)}</td>
                  <td className="pr-3"><Pill tone={r.cep_status === 'participating' ? 'emerald' : r.cep_status === 'eligible_not_participating' ? 'amber' : 'slate'}>{cepLabel(r.cep_status)}</Pill></td>
                  <td><a className="text-cyan-400 hover:underline" href={r.source_url} target="_blank" rel="noreferrer">{r.source_year}</a></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
