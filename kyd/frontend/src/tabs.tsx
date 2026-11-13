import { useEffect, useMemo, useRef, useState } from 'react';
import { Send, ExternalLink, Bot, Zap, ShieldAlert } from 'lucide-react';
import { api, fmt, type Answer, type Geo, type Obs, type Profile, type ProgramMatch } from './api';
import { Card, Empty, Figure, GeoPicker, Pill } from './ui';

const HEADLINE = ['total_pop', 'median_hh_income', 'pct_below_fpl', 'pct_65plus', 'pct_rent_burden_30', 'pct_uninsured'];
const by = (xs: Obs[] | undefined) => Object.fromEntries((xs ?? []).map(o => [o.indicator, o]));

// ── Overview ────────────────────────────────────────────────────────────────
export function OverviewTab({ geo, geos, onAsk, onPick }: { geo: string; geos: Geo[]; onAsk: (q: string) => void; onPick: (g: string) => void }) {
  const [p, setP] = useState<Profile | null>(null);
  const [progs, setProgs] = useState<ProgramMatch[]>([]);
  useEffect(() => { setP(null); api.profile(geo).then(setP); api.programs(geo).then(setProgs); }, [geo]);
  if (!p) return <Empty>Loading…</Empty>;
  const me = by(p.observations), st = by(p.comparisons.state), co = by(p.comparisons.county);
  const name = (g: string) => geos.find(x => x.geo_id === g)?.name ?? g;
  return (
    <div className="grid grid-cols-12 gap-4">
      <Card className="col-span-12" title={<span className="normal-case text-lg text-slate-100">{p.geography.name}</span>}
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

// ── Map (placeholder tile grid until ArcGIS boundaries load) ─────────────────
export function MapTab({ geos, geo, onPick }: { geos: Geo[]; geo: string; onPick: (g: string) => void }) {
  const [inds, setInds] = useState<{ indicator: string; label: string }[]>([]);
  const [ind, setInd] = useState('pct_below_fpl');
  const [chamber, setChamber] = useState<'sldl' | 'sldu'>('sldl');
  const [feats, setFeats] = useState<Obs[]>([]);
  useEffect(() => { api.indicators().then(setInds); }, []);
  useEffect(() => { api.mapLayer(ind, chamber).then(d => setFeats(d.features)); }, [ind, chamber]);
  const vals = feats.map(f => f.value ?? 0).sort((a, b) => a - b);
  const q = (v: number) => Math.min(4, Math.floor((vals.filter(x => x <= v).length / Math.max(1, vals.length)) * 5));
  const shades = ['bg-cyan-950', 'bg-cyan-900', 'bg-cyan-800', 'bg-cyan-700', 'bg-cyan-500'];
  const name = (g: string) => geos.find(x => x.geo_id === g)?.name ?? g;
  return (
    <Card title="District map" right={
      <div className="flex gap-2">
        <select value={chamber} onChange={e => setChamber(e.target.value as any)} className="bg-premium-950 border border-premium-700 rounded px-2 py-1 text-xs">
          <option value="sldl">House (51)</option><option value="sldu">Senate (25)</option>
        </select>
        <select value={ind} onChange={e => setInd(e.target.value)} className="bg-premium-950 border border-premium-700 rounded px-2 py-1 text-xs">
          {inds.map(i => <option key={i.indicator} value={i.indicator}>{i.label}</option>)}
        </select>
      </div>}>
      <p className="text-xs text-amber-300 mb-3">Placeholder tile grid. The ArcGIS adapter with 2022 reapportionment boundaries replaces this view (MapLibre as fallback).</p>
      <div className="grid grid-cols-6 md:grid-cols-9 lg:grid-cols-13 gap-1.5" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(72px, 1fr))' }}>
        {feats.map(f => (
          <button key={f.geo_id} onClick={() => onPick(f.geo_id)} title={`${name(f.geo_id)}: ${fmt(f)}`}
            className={`${shades[q(f.value ?? 0)]} ${f.geo_id === geo ? 'ring-2 ring-amber-400' : ''} ${f.flags.includes('suppressed_cv') ? 'opacity-50' : ''} rounded-md p-2 text-left hover:ring-2 hover:ring-cyan-300`}>
            <div className="text-[10px] text-slate-300">{f.geo_id}</div>
            <div className="text-xs font-mono text-white">{fmt(f)}</div>
          </button>
        ))}
      </div>
      <div className="flex items-center gap-1 mt-3 text-xs text-slate-500">Low{shades.map(s => <span key={s} className={`w-6 h-3 rounded ${s}`} />)}High · Faded tiles are low-reliability estimates</div>
    </Card>
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
    <Card title="Compare" right={<div className="flex gap-3"><GeoPicker geos={geos} value={a} onChange={setA} label="A" /><GeoPicker geos={geos} value={b} onChange={setB} label="B" /></div>}>
      <table className="w-full text-sm">
        <thead className="text-xs text-slate-500 text-left"><tr><th className="py-1">Indicator</th><th>A</th><th>B</th><th>Difference</th></tr></thead>
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
export function SourcesTab() {
  const [src, setSrc] = useState<any[]>([]);
  useEffect(() => { api.sources().then(setSrc); }, []);
  return (
    <div className="grid lg:grid-cols-2 gap-4">
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
