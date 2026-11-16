import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Send, ExternalLink, Bot, Zap, ShieldAlert } from 'lucide-react';
import { api, fmt, type Answer, type Geo, type Obs, type Profile, type ProgramMatch, type Verification } from './api';
import { Card, Empty, Figure, GeoPicker, Pill } from './ui';
import { CrossProgramCard, ProgramContextCards } from './programExtras';

const HEADLINE = ['total_pop', 'median_hh_income', 'pct_below_fpl', 'pct_65plus', 'pct_rent_burden_30', 'pct_uninsured'];
const by = (xs: Obs[] | undefined) => Object.fromEntries((xs ?? []).map(o => [o.indicator, o]));

// ── Overview ────────────────────────────────────────────────────────────────
export function OverviewTab({ geo, geos, onAsk, onPick, picker }: { geo: string; geos: Geo[]; onAsk: (q: string) => void; onPick: (g: string) => void; picker?: ReactNode }) {
  const [p, setP] = useState<Profile | null>(null);
  const [progs, setProgs] = useState<ProgramMatch[]>([]);
  useEffect(() => { setP(null); api.profile(geo).then(setP); api.programs(geo).then(setProgs); }, [geo]);
  if (!p) return <Empty>Loading…</Empty>;
  const me = by(p.observations), st = by(p.comparisons.state), co = by(p.comparisons.county);
  const name = (g: string) => geos.find(x => x.geo_id === g)?.name ?? g;
  return (
    <div className="grid grid-cols-12 gap-4">
      <Card className="col-span-12" title={<span className="normal-case flex flex-wrap items-center gap-4"><span className="text-lg text-slate-100">{p.geography.name}</span>{picker}</span>}
        right={<span className="text-xs text-slate-500">ACS {p.data_as_of} · {p.geography.counties.map(name).join(', ')}</span>}>
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
          {HEADLINE.filter(k => me[k]).map(k => (
            <div key={k} className="rounded-lg bg-black/30 p-3">
              <div className="text-xs text-slate-400 mb-1">{me[k].label}</div>
              <Figure o={me[k]} big />
              <div className="mt-1 text-xs text-slate-500 space-x-2">
                {co[k] && <span>County {fmt(co[k])}</span>}{st[k] && <span>State {fmt(st[k])}</span>}
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card className="col-span-12 lg:col-span-7" title="All indicators">
        <table className="w-full text-sm">
          <thead className="text-xs text-slate-500 text-left"><tr><th className="py-1">Indicator</th><th>District</th><th>County</th><th>State</th></tr></thead>
          <tbody>
            {p.observations.map(o => (
              <tr key={o.obs_id} className="border-t border-premium-800">
                <td className="py-1.5 text-slate-300">{o.label}</td>
                <td><Figure o={o} /></td>
                <td className="text-slate-400 font-mono text-xs">{co[o.indicator] ? fmt(co[o.indicator]) : '—'}</td>
                <td className="text-slate-400 font-mono text-xs">{st[o.indicator] ? fmt(st[o.indicator]) : '—'}</td>
              </tr>
            ))}
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
        <Card title="Ask about this district">
          <div className="flex flex-wrap gap-2">
            {['Which programs fit this district?', `Compare this district with ${p.peers[0] ?? 'HI'}`, 'Give me a profile of this district'].map(q => (
              <button key={q} onClick={() => onAsk(q)} className="px-2 py-1 rounded-md border border-cyan-900 text-xs text-cyan-300 hover:bg-cyan-950">{q}</button>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

// ── Compare ─────────────────────────────────────────────────────────────────
export function CompareTab({ geos, geo }: { geos: Geo[]; geo: string }) {
  const [a, setA] = useState(geo);
  const [b, setB] = useState('HI');
  const [rows, setRows] = useState<{ indicator: string; a: Obs; b: Obs; significant: boolean }[]>([]);
  useEffect(() => setA(geo), [geo]);
  useEffect(() => { api.compare(a, b).then(d => setRows(d.rows)); }, [a, b]);
  return (
    <Card title="Compare">
      <table className="w-full text-sm">
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
  useEffect(() => { api.programs(geo).then(setMs); }, [geo]);
  return (
    <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
      {ms.map((m, i) => (
        <Card key={m.program.program_id} title={<span className="normal-case">{i + 1}. {m.program.name}</span>} right={<Pill tone="cyan">score {m.score.toFixed(2)}</Pill>}>
          <p className="text-sm text-slate-300">{m.program.summary}</p>
          <div className="text-xs text-slate-500 mt-1">{m.program.agency} · {m.program.level}</div>
          <ul className="mt-2 text-xs text-slate-400 list-disc ml-4">{m.rationale.map(r => <li key={r}>{r}</li>)}</ul>
          {m.gap_note && <p className="mt-2 text-xs text-amber-300">{m.gap_note}</p>}
          <a href={m.program.official_url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1 text-xs text-cyan-400 hover:underline">
            Official program page <ExternalLink className="w-3 h-3" /></a>
        </Card>
      ))}
      <CrossProgramCard geo={geo} />
      <ProgramContextCards geo={geo} />
      <p className="col-span-full text-xs text-slate-500">Rankings compare district need indicators with the state. Eligibility information is informational only. The administering agency makes all determinations.</p>
    </div>
  );
}

// ── Ask (agent) ─────────────────────────────────────────────────────────────
type Msg = { role: 'user' | 'agent'; text: string; a?: Answer };
export function AskTab({ geo, pending, clearPending }: { geo: string; pending: string | null; clearPending: () => void }) {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  const send = async (q: string) => {
    if (!q.trim()) return;
    setMsgs(m => [...m, { role: 'user', text: q }]); setInput(''); setBusy(true);
    try { const a = await api.ask(q, geo); setMsgs(m => [...m, { role: 'agent', text: a.text, a }]); }
    catch (e) { setMsgs(m => [...m, { role: 'agent', text: 'Error: ' + e }]); }
    finally { setBusy(false); }
  };
  useEffect(() => { if (pending) { send(pending); clearPending(); } }, [pending]);
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }); }, [msgs]);
  const obsMap = useMemo(() => Object.fromEntries(msgs.flatMap(m => m.a?.observations ?? []).map(o => [o.obs_id, o])), [msgs]);

  const render = (t: string) => t.split(/(\[obs:[^\]]+\])/g).map((part, i) => {
    const m = part.match(/^\[obs:([^\]]+)\]$/);
    if (!m) return <span key={i}>{part}</span>;
    const o = obsMap[m[1]];
    return <sup key={i} className="text-cyan-500 ml-0.5" title={o ? `${o.label}: ${fmt(o)} · ACS ${o.vintage}` : m[1]}>[{o ? o.indicator : 'src'}]</sup>;
  });

  return (
    <Card className="flex flex-col h-full" title="Ask the agent" right={<span className="text-xs text-slate-500">Context: {geo}</span>}>
      <div className="flex-1 overflow-y-auto space-y-3 pr-1 min-h-[50vh]" aria-live="polite">
        {!msgs.length && <Empty>Try “Which programs fit House District 22?” or “Compare SD 9 vs SD 14”.</Empty>}
        {msgs.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'text-right' : ''}>
            <div className={`inline-block max-w-[85%] text-left whitespace-pre-wrap rounded-lg px-3 py-2 text-sm ${m.role === 'user' ? 'bg-premium-700' : 'bg-premium-800 border border-premium-700'}`}>
              {m.role === 'agent' ? render(m.text) : m.text}
            </div>
            {m.a && (
              <div className="mt-1 flex gap-2 items-center text-xs text-slate-500">
                {m.a.route === 'S1' && <span className="inline-flex items-center gap-1"><Zap className="w-3 h-3 text-emerald-400" />System 1</span>}
                {m.a.route === 'S2' && <span className="inline-flex items-center gap-1"><Bot className="w-3 h-3 text-cyan-400" />System 2</span>}
                {m.a.route === 'REFUSED' && <span className="inline-flex items-center gap-1"><ShieldAlert className="w-3 h-3 text-amber-400" />Guardrail</span>}
                {m.a.escalation_reasons.map(r => <Pill key={r}>{r}</Pill>)}
              </div>
            )}
          </div>
        ))}
        {busy && <div className="text-xs text-slate-500 animate-pulse">Thinking…</div>}
        <div ref={end} />
      </div>
      <form onSubmit={e => { e.preventDefault(); send(input); }} className="mt-3 flex gap-2">
        <label htmlFor="ask" className="sr-only">Question</label>
        <input id="ask" value={input} onChange={e => setInput(e.target.value)} placeholder="Ask about a district…"
          className="flex-1 bg-premium-950 border border-premium-700 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-600" />
        <button disabled={busy} className="px-3 rounded-md bg-cyan-700 hover:bg-cyan-600 disabled:opacity-50" aria-label="Send"><Send className="w-4 h-4" /></button>
      </form>
    </Card>
  );
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

export function SourcesTab() {
  const [src, setSrc] = useState<any[]>([]);
  useEffect(() => { api.sources().then(setSrc); }, []);
  return (
    <div className="grid lg:grid-cols-2 gap-4">
      <div className="lg:col-span-2"><VerificationCard /></div>
      <Card title="Data sources">
        <ul className="space-y-2 text-sm">{src.map(s => (
          <li key={s.source_id}><div className="text-slate-100">{s.title}</div>
            <div className="text-xs text-slate-500">{s.publisher} · released {s.release_date ?? '—'} · <span className="font-mono">{s.source_id}</span></div></li>))}
        </ul>
      </Card>
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
