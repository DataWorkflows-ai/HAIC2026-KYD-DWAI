import { useEffect, useRef, useState, type ReactNode } from 'react';
import { ExternalLink, GripVertical } from 'lucide-react';
import { api, fmt, type Geo, type Obs, type Profile, type ProgramGaps, type ProgramMatch, type Verification } from './api';
import { Card, Empty, ExportButtons, Figure, GeoPicker, Pill, usePersistentState } from './ui';
import { CrossProgramCard, GapRangeBlock, ProgramContextCards, UptakePeersCard } from './programExtras';
import { SchoolDetailsCard } from './ProgramGaps';

const HEADLINE = ['total_pop', 'median_hh_income', 'pct_below_fpl', 'pct_65plus', 'pct_rent_burden_30', 'pct_uninsured'];
const by = (xs: Obs[] | undefined) => Object.fromEntries((xs ?? []).map(o => [o.indicator, o]));

// ── Overview ────────────────────────────────────────────────────────────────
// Starting set for the All indicators table; everything else is one click away under "Add indicator".
const DEFAULT_ROWS = ['total_pop', 'median_hh_income', 'pct_below_fpl', 'pct_child_poverty', 'pct_65plus_poverty', 'pct_snap_hh',
  'pct_ssi_hh', 'pct_cash_assist_hh', 'pct_rent_burden_30', 'pct_uninsured', 'pct_disability', 'unemployment_rate', 'pct_pop_lidac',
  'pct_65plus', 'pct_limited_english'];
type Layout = { rows: string[] };
export function OverviewTab({ geo, geos, onAsk, onPick, picker }: { geo: string; geos: Geo[]; onAsk: (q: string) => void; onPick: (g: string) => void; picker?: ReactNode }) {
  const indTable = useRef<HTMLTableElement>(null);
  const [layout, setLayout] = usePersistentState<Layout>('kyd_indicator_rows', { rows: DEFAULT_ROWS });
  const [editing, setEditing] = useState(false);
  const [dragKey, setDragKey] = useState<string | null>(null);
  const moveRow = (shownKeys: string[], key: string, to: number) => {
    const r = shownKeys.filter(k => k !== key);
    r.splice(Math.max(0, Math.min(to, r.length)), 0, key);
    setLayout({ rows: [...r, ...layout.rows.filter(k => !shownKeys.includes(k))] });   // keep rows this geography lacks
  };
  const [p, setP] = useState<Profile | null>(null);
  const [progs, setProgs] = useState<ProgramMatch[]>([]);
  const [gaps, setGaps] = useState<ProgramGaps | null>(null);
  useEffect(() => {
    let live = true;   // ignore a slow reply for a district the user has already left
    setP(null);
    api.profile(geo).then(x => live && setP(x)); api.programs(geo).then(x => live && setProgs(x));
    api.programGaps(geo).then(x => live && setGaps(x)).catch(() => live && setGaps(null));
    return () => { live = false; };
  }, [geo]);
  if (!p) return <Empty>Loading…</Empty>;
  const me = by(p.observations), st = by(p.comparisons.state), co = by(p.comparisons.county);
  const name = (g: string) => geos.find(x => x.geo_id === g)?.name ?? g;
  return (
    <div className="grid grid-cols-12 gap-4">
      <Card className="col-span-12" title={<span className="normal-case flex flex-wrap items-center gap-4"><span className="text-lg text-slate-100">{p.geography.name}</span>{picker}</span>}
        right={<span className="text-xs text-slate-500">ACS {p.data_as_of} · {p.geography.counties.map(name).join(', ')}</span>}>
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
          {HEADLINE.filter(k => me[k]).map(k => (
            <div key={k} className="rounded-lg bg-premium-950/60 p-3">
              <div className="text-xs text-slate-400 mb-1">{me[k].label}</div>
              <Figure o={me[k]} big />
              <div className="mt-1 text-xs text-slate-500 space-x-2">
                {co[k] && <span>County {fmt(co[k])}</span>}{st[k] && <span>State {fmt(st[k])}</span>}
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card className="col-span-12 lg:col-span-7" title="Indicators" right={
        <div className="flex items-center gap-1.5">
          <button onClick={() => setEditing(e => !e)} aria-pressed={editing}
            className={`no-print text-xs px-2 py-1 rounded border ${editing ? 'border-cyan-700 text-cyan-300' : 'border-premium-700 text-slate-300 hover:text-cyan-300'}`}>
            {editing ? 'Done' : 'Customize'}</button>
          <ExportButtons table={indTable} name={`kyd_${p.geography.geo_id}_indicators`} />
        </div>}>
        {editing && (
          <div className="no-print mb-2 flex flex-wrap items-center gap-2 text-xs">
            <select value="" onChange={e => e.target.value && setLayout({ rows: [...layout.rows, e.target.value] })} aria-label="Add indicator"
              className="bg-premium-950 border border-premium-700 rounded-md px-2 py-1 text-slate-200">
              <option value="">+ Add indicator…</option>
              {p.observations.filter(o => !layout.rows.includes(o.indicator)).map(o => <option key={o.indicator} value={o.indicator}>{o.label}</option>)}
            </select>
            <button onClick={() => setLayout({ rows: p.observations.map(o => o.indicator) })} className="px-2 py-1 rounded border border-premium-700 text-slate-300 hover:text-cyan-300">Show all</button>
            <button onClick={() => setLayout({ rows: DEFAULT_ROWS })} className="px-2 py-1 rounded border border-premium-700 text-slate-300 hover:text-cyan-300">Reset</button>
            <span className="text-slate-500">Drag ⋮⋮ to reorder, × to hide. Saved in this browser.</span>
          </div>
        )}
        <table ref={indTable} className="w-full text-sm">
          <thead className="text-xs text-slate-500 text-left"><tr><th className="no-print w-6" /><th className="py-1">Indicator</th><th>District</th><th>County</th><th>State</th>{editing && <th className="no-print" />}</tr></thead>
          <tbody>
            {layout.rows.map(k => me[k]).filter(Boolean).map((o, i, shown) => (
              <tr key={o.obs_id}
                onDragOver={e => { if (!dragKey) return; e.preventDefault(); if (dragKey !== o.indicator) moveRow(shown.map(x => x.indicator), dragKey, i); }}
                onDrop={e => { e.preventDefault(); setDragKey(null); }}
                className={`border-t border-premium-800 ${dragKey === o.indicator ? 'opacity-50 bg-cyan-950/40' : ''}`}>
                <td className="no-print w-6 align-middle">
                  <button draggable aria-label={`Reorder ${o.label}: drag, or focus and use the arrow keys`} title="Drag to reorder"
                    onDragStart={e => { setDragKey(o.indicator); e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/plain', o.indicator); }}
                    onDragEnd={() => setDragKey(null)}
                    onKeyDown={e => {
                      if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown') return;
                      e.preventDefault();
                      moveRow(shown.map(x => x.indicator), o.indicator, i + (e.key === 'ArrowUp' ? -1 : 1));
                      const k = o.indicator;
                      setTimeout(() => (document.querySelector(`[data-grip="${k}"]`) as HTMLElement | null)?.focus(), 0);
                    }}
                    data-grip={o.indicator}
                    className="cursor-grab active:cursor-grabbing text-slate-600 hover:text-cyan-300 px-1 py-1"><GripVertical className="w-4 h-4" /></button>
                </td>
                <td className="py-1.5 text-slate-300">{o.label}</td>
                <td><Figure o={o} /></td>
                <td className="text-slate-400 font-mono text-xs">{co[o.indicator] ? fmt(co[o.indicator]) : '—'}</td>
                <td className="text-slate-400 font-mono text-xs">{st[o.indicator] ? fmt(st[o.indicator]) : '—'}</td>
                {editing && (
                  <td className="no-print whitespace-nowrap text-right">
                    <button onClick={() => setLayout({ rows: layout.rows.filter(x => x !== o.indicator) })} aria-label={`Hide ${o.label}`}
                      className="px-1.5 text-slate-400 hover:text-red-400">×</button>
                  </td>
                )}
              </tr>
            ))}
            {!layout.rows.some(k => me[k]) && <tr><td colSpan={5} className="py-3 text-xs text-slate-500">No indicators shown. Click Customize to add some.</td></tr>}
          </tbody>
        </table>
      </Card>

      <div className="col-span-12 lg:col-span-5 space-y-4">
        <Card title="Top program matches">
          <ol className="space-y-2">
            {progs.slice(0, 5).map((m, i) => (
              <li key={m.program.program_id} className="text-sm">
                <span className="text-slate-500 mr-2">{i + 1}.</span>
                <a href={m.program.official_url} target="_blank" rel="noreferrer" className="text-slate-100 hover:text-cyan-300">{m.program.name}</a>
                <div className="text-xs text-slate-500 ml-5">{m.rationale[0]}</div>
              </li>
            ))}
          </ol>
        </Card>
        <Card title="Peer districts" right={<span className="text-xs text-slate-500">nearest by profile</span>}>
          <div className="flex flex-wrap gap-2">
            {p.peers.map(g => <button key={g} onClick={() => onPick(g)} className="px-2 py-1 rounded-md bg-premium-800 border border-premium-700 text-xs hover:text-cyan-300">{name(g)}</button>)}
            {!p.peers.length && <Empty>Not applicable</Empty>}
          </div>
        </Card>
        <Card title="Ask about this district" className="no-print">
          <div className="flex flex-wrap gap-2">
            {suggestions(geo).slice(1, 7).map(q => (
              <button key={q} onClick={() => onAsk(q)} className="px-2 py-1 rounded-md border border-cyan-900 text-xs text-cyan-300 hover:bg-cyan-950">{q}</button>
            ))}
          </div>
        </Card>
      </div>
      <div className="col-span-12 lg:col-span-7"><UptakePeersCard geo={geo} onPick={onPick} /></div>
      {gaps && <div className="col-span-12 lg:col-span-5"><SchoolDetailsCard data={gaps} /></div>}
    </div>
  );
}

// ── Compare ─────────────────────────────────────────────────────────────────
export function CompareTab({ geos, geo }: { geos: Geo[]; geo: string }) {
  const cmpTable = useRef<HTMLTableElement>(null);
  const [a, setA] = useState(geo);
  const [b, setB] = useState('HI');
  const [rows, setRows] = useState<{ indicator: string; a: Obs; b: Obs; significant: boolean }[]>([]);
  useEffect(() => setA(geo), [geo]);
  useEffect(() => { let live = true; api.compare(a, b).then(d => live && setRows(d.rows)); return () => { live = false; }; }, [a, b]);
  return (
    <Card title="Compare" right={<ExportButtons table={cmpTable} name={`kyd_compare_${a}_${b}`} />}>
      <table ref={cmpTable} className="w-full text-sm">
        <thead className="text-xs text-slate-500 text-left align-bottom">
          <tr>
            <th className="py-1 w-[34%]">Indicator</th>
            <th className="py-1 pr-3"><GeoPicker geos={geos} value={a} onChange={setA} label="A" /></th>
            <th className="py-1 pr-3"><GeoPicker geos={geos} value={b} onChange={setB} label="B" /></th>
            <th className="py-1">Difference</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.indicator} className="border-t border-premium-800">
              <td className="py-1.5">{r.a.label}</td><td><Figure o={r.a} /></td><td><Figure o={r.b} /></td>
              <td>{r.significant ? <Pill tone="cyan">significant</Pill> : <Pill>not significant</Pill>}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-xs text-slate-500 mt-3">Significance is tested at 90% confidence using published margins of error.</p>
    </Card>
  );
}

// ── Programs ────────────────────────────────────────────────────────────────
export function ProgramsTab({ geo }: { geo: string }) {
  const [ms, setMs] = useState<ProgramMatch[]>([]);
  useEffect(() => { let live = true; api.programs(geo).then(x => live && setMs(x)); return () => { live = false; }; }, [geo]);
  return (
    <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
      {ms.map((m, i) => (
        <Card key={m.program.program_id} title={<span className="normal-case">{i + 1}. {m.program.name}</span>} right={<Pill tone="cyan">score {m.score.toFixed(2)}</Pill>}>
          <p className="text-sm text-slate-300">{m.program.summary}</p>
          <div className="text-xs text-slate-500 mt-1">{m.program.agency} · {m.program.level}</div>
          <ul className="mt-2 text-xs text-slate-400 list-disc ml-4">{m.rationale.map(r => <li key={r}>{r}</li>)}</ul>
          {m.gap_range ? <GapRangeBlock r={m.gap_range} /> : m.gap_note && <p className="mt-2 text-xs text-amber-300">{m.gap_note}</p>}
          <a href={m.program.official_url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1 text-xs text-cyan-400 hover:underline">
            Official program page <ExternalLink className="w-3 h-3" /></a>
        </Card>
      ))}
      <CrossProgramCard geo={geo} />
      <UptakePeersCard geo={geo} />
      <ProgramContextCards geo={geo} />
      <p className="col-span-full text-xs text-slate-500">Rankings compare district need indicators with the state. Eligibility information is informational only. The administering agency makes all determinations.</p>
    </div>
  );
}

// ── Suggested questions (Overview and Chat) ─────────────────────────────────
/** Starter questions for the selected district; each maps to a tool the agent answers without guessing. */
export function suggestions(geo: string): string[] {
  const n = geo === 'HI' ? 'the state' : geo.startsWith('HD') ? `House District ${parseInt(geo.slice(3), 10)}`
    : geo.startsWith('SD') ? `Senate District ${parseInt(geo.slice(3), 10)}` : 'this district';
  const other = geo.startsWith('SD') ? (geo === 'SD-12' ? 'Senate District 13' : 'Senate District 12')
    : (geo === 'HD-22' ? 'House District 23' : 'House District 22');
  return [
    `Give me a profile of ${n}`,
    `Which programs fit ${n}?`,
    `Who in ${n} may be eligible for other programs?`,
    `Unemployment by age and race in ${n}`,
    `Compare ${n} with the state`,
    ...(geo === 'HI' ? [] : [`Which districts with similar need reach more people with SNAP than ${n}?`,
                            `How do test scores in ${n} compare with the state?`,
                            `Compare ${n} with ${other}`]),
  ];
}

// ── Sources & methods ───────────────────────────────────────────────────────
const STATUS_STYLE: Record<string, string> = {
  pass: 'text-emerald-300 border-emerald-800', info: 'text-sky-300 border-sky-800',
  warn: 'text-amber-300 border-amber-800', fail: 'text-rose-300 border-rose-800',
};
const Badge = ({ s }: { s: string }) => <span className={`text-[10px] px-1.5 rounded border uppercase ${STATUS_STYLE[s] ?? ''}`}>{s}</span>;

function VerificationCard() {
  const [v, setV] = useState<Verification | null>(null);
  const [err, setErr] = useState('');
  const [open, setOpen] = useState(false);
  useEffect(() => { api.verification().then(setV).catch(e => setErr(String(e.message ?? e))); }, []);
  if (err) return <Card title="Data verification"><p className="text-sm text-slate-400">No verification report yet.</p></Card>;
  if (!v) return <Card title="Data verification"><p className="text-sm text-slate-500">Loading…</p></Card>;
  const flagged = v.checks.filter(c => c.status === 'fail' || c.status === 'warn');
  return (
    <Card title="Data verification" right={<span className="text-xs text-slate-500">{v.summary.generated_at.slice(0, 10)}</span>}>
      <div className="flex gap-2 text-xs mb-3">
        {(['pass', 'info', 'warn', 'fail'] as const).map(k => <span key={k} className="flex items-center gap-1"><Badge s={k} />{v.summary[k]}</span>)}
      </div>
      <p className="text-xs text-slate-400 mb-2">Every program source is re-read and checked on each build: hand-typed DHS Databook figures against the PDF,
        the BESSD CSV against its workbook, Census variables against their published totals and Data Profiles, and independent
        sources against each other. A changed report format fails the build instead of producing wrong numbers.</p>
      <ul className="text-sm divide-y divide-premium-800">
        {v.capabilities.map(c => (
          <li key={c.capability} className="py-1.5 flex justify-between gap-2">
            <span className="text-slate-200">{c.name}</span><Badge s={c.status} />
          </li>))}
      </ul>
      {flagged.length > 0 && (
        <div className="mt-3">
          <button onClick={() => setOpen(o => !o)} className="text-xs text-cyan-400 hover:underline">
            {open ? 'Hide' : 'Show'} {flagged.length} item{flagged.length > 1 ? 's' : ''} to review</button>
          {open && <ul className="mt-2 space-y-1.5">{flagged.map(c => (
            <li key={c.id} className="text-xs"><Badge s={c.status} /> <span className="text-slate-300">{c.detail}</span>
              {(c.expected !== null || c.actual !== null) && <span className="text-slate-500 font-mono"> · source {JSON.stringify(c.expected)} · ours {JSON.stringify(c.actual)}</span>}</li>))}
          </ul>}
        </div>
      )}
    </Card>
  );
}

type LibRow = { group: string; name: string; publisher: string; provides: string; vintage: string; url: string; accessed: string; used_in: string };
function SourceLibrary() {
  const [rows, setRows] = useState<LibRow[]>([]);
  const [q, setQ] = useState('');
  useEffect(() => { api.get<LibRow[]>('/api/source-library').then(setRows).catch(() => setRows([])); }, []);
  const shown = rows.filter(r => !q || Object.values(r).join(' ').toLowerCase().includes(q.toLowerCase()));
  const csv = () => {
    const cols = ['group', 'name', 'publisher', 'provides', 'vintage', 'url', 'accessed', 'used_in'] as const;
    const esc = (v: string) => `"${v.replace(/"/g, '""')}"`;
    const body = [cols.join(','), ...rows.map(r => cols.map(c => esc(r[c] ?? '')).join(','))].join('\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([body], { type: 'text/csv' })); a.download = 'kyd_sources.csv'; a.click();
  };
  return (
    <Card title={`Source library (${rows.length})`} right={
      <div className="flex items-center gap-2">
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="Filter sources" aria-label="Filter sources"
          className="bg-premium-950 border border-premium-700 rounded-md px-2 py-1 text-xs text-slate-200 w-44" />
        <button onClick={csv} className="text-xs px-2 py-1 rounded border border-premium-700 text-slate-300 hover:text-cyan-300">Download CSV</button>
      </div>}>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-xs text-slate-500 text-left">
            <tr><th className="py-1 pr-3">Source</th><th className="pr-3">What it provides</th><th className="pr-3">Vintage</th><th className="pr-3">Used in</th><th>Accessed</th></tr>
          </thead>
          <tbody>
            {shown.map(r => (
              <tr key={r.name} className="border-t border-premium-800 align-top">
                <td className="py-1.5 pr-3 min-w-[16rem]">
                  <a href={r.url} target="_blank" rel="noreferrer" className="text-cyan-300 hover:underline inline-flex items-start gap-1">{r.name} <ExternalLink className="w-3 h-3 mt-1 shrink-0" /></a>
                  <div className="text-xs text-slate-500">{r.publisher} · {r.group}</div>
                </td>
                <td className="pr-3 text-xs text-slate-300">{r.provides}</td>
                <td className="pr-3 text-xs text-slate-400 whitespace-nowrap">{r.vintage}</td>
                <td className="pr-3 text-xs text-slate-400">{r.used_in}</td>
                <td className="text-xs text-slate-500 whitespace-nowrap">{r.accessed}</td>
              </tr>))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-500 mt-2">Each source's name, publisher and description are kept here, so the trail survives if a link moves. The same list is in SOURCES.md in the code repository.</p>
    </Card>
  );
}

export function SourcesTab() {
  const [src, setSrc] = useState<any[]>([]);
  useEffect(() => { api.sources().then(setSrc); }, []);
  return (
    <div className="grid lg:grid-cols-2 gap-4">
      <div className="lg:col-span-2"><VerificationCard /></div>
      <div className="lg:col-span-2"><SourceLibrary /></div>
      <Card title="Methods">
        <ul className="text-sm text-slate-300 space-y-2 list-disc ml-4">
          <li>Figures come from a precomputed fact table. The AI never generates numbers. It retrieves them through tools and cites each one.</li>
          <li>ACS margins of error are shown at 90% confidence. Estimates with a coefficient of variation above 30% are greyed out and caveated.</li>
          <li>Figures not published at the district level are apportioned with 2020 block population weights and labelled “apportioned”.</li>
          <li>Comparisons use the Census Bureau significance test.</li>
          <li>Program matching is population-level and informational. It never determines individual eligibility.</li>
          <li>Questions about individuals and partisan questions are refused.</li>
        </ul>
      </Card>
    </div>
  );
}
