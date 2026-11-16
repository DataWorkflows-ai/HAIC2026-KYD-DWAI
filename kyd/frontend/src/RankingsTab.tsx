import { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowDown, ArrowUp } from 'lucide-react';
import { api, fmt, type Rankings } from './api';
import { Card, Empty, ExportButtons, Figure, Pill } from './ui';

/** All districts of a chamber ranked on comparable measures. Every cell is a cited figure. */
export function RankingsTab({ onOpen }: { onOpen: (geo: string) => void }) {
  const [chamber, setChamber] = useState<'sldl' | 'sldu'>('sldl');
  const [data, setData] = useState<Rankings | null>(null);
  const [sort, setSort] = useState<{ key: string; desc: boolean }>({ key: 'pct_below_fpl', desc: true });
  useEffect(() => { setData(null); api.rankings(chamber).then(setData); }, [chamber]);
  const tbl = useRef<HTMLTableElement>(null);

  const rows = useMemo(() => {
    if (!data) return [];
    const val = (r: Rankings['rows'][number]) => sort.key === 'name' ? r.geo_id : r.cells[sort.key]?.obs.value ?? null;
    return [...data.rows].sort((a, b) => {
      const x = val(a), y = val(b);
      if (x === null && y === null) return 0;
      if (x === null) return 1;           // missing values always last
      if (y === null) return -1;
      const c = typeof x === 'string' ? x.localeCompare(y as string) : (x as number) - (y as number);
      return sort.desc ? -c : c;
    });
  }, [data, sort]);

  if (!data) return <Empty>Loading…</Empty>;
  const head = (key: string, label: string, extra?: JSX.Element) => (
    <th className="text-left font-normal px-2 py-2 align-bottom">
      <button onClick={() => setSort(s => ({ key, desc: s.key === key ? !s.desc : key !== 'name' }))}
        className={`inline-flex items-center gap-1 hover:text-cyan-300 ${sort.key === key ? 'text-cyan-300' : ''}`} aria-sort={sort.key === key ? (sort.desc ? 'descending' : 'ascending') : 'none'}>
        {label}{sort.key === key && (sort.desc ? <ArrowDown className="w-3 h-3" /> : <ArrowUp className="w-3 h-3" />)}
      </button>{extra && <div className="mt-1">{extra}</div>}
    </th>
  );
  return (
    <Card title="District rankings" right={
      <div className="flex gap-1 items-center"><ExportButtons table={tbl} name={`kyd_rankings_${chamber === 'sldl' ? 'house' : 'senate'}`} />{(['sldl', 'sldu'] as const).map(c => (
        <button key={c} onClick={() => setChamber(c)} aria-pressed={chamber === c}
          className={`px-2 py-0.5 rounded text-xs border ${chamber === c ? 'border-cyan-700 text-cyan-300' : 'border-premium-700 text-slate-400'}`}>
          {c === 'sldl' ? 'House (51)' : 'Senate (25)'}</button>))}</div>}>
      <div className="overflow-x-auto">
        <table ref={tbl} className="w-full text-sm">
          <thead className="text-xs text-slate-400 border-b border-premium-700">
            <tr>
              {head('name', 'District')}
              {data.columns.map(c => head(c.indicator, c.label, <span className="space-x-1">
                {c.kind === 'estimate' ? <Pill tone="amber">ESTIMATE</Pill> : <Pill>ACS ±MOE</Pill>}
                {c.ranked < data.rows.length && <span className="text-[10px] text-slate-500">{c.ranked} ranked</span>}
                {data.state[c.indicator] && <span className="text-[10px] text-slate-500">state {fmt(data.state[c.indicator]!)}</span>}</span>))}
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.geo_id} className="border-b border-premium-800 hover:bg-white/5">
                <td className="px-2 py-1.5 whitespace-nowrap">
                  <button onClick={() => onOpen(r.geo_id)} className="text-slate-100 hover:text-cyan-300 hover:underline">{r.name}</button>
                  <div className="text-[10px] text-slate-500">{r.counties.join(', ')}</div></td>
                {data.columns.map(c => {
                  const cell = r.cells[c.indicator];
                  return <td key={c.indicator} className="px-2 py-1.5 whitespace-nowrap">
                    {cell ? <><Figure o={cell.obs} />{cell.rank && <span className="ml-1 text-[10px] text-slate-500">#{cell.rank}</span>}</>
                      : <span className="text-slate-600 text-xs">—</span>}</td>;
                })}
              </tr>))}
          </tbody>
        </table>
      </div>
      <ul className="mt-3 text-xs text-slate-500 list-disc ml-4">{data.notes.map(n => <li key={n}>{n}</li>)}</ul>
    </Card>
  );
}
