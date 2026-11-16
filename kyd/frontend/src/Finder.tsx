/**
 * Header search: district number or name, legislator, place, neighborhood or ZIP code.
 * Places and ZIPs often span districts, so each result lists every district it touches with its area share.
 * No street addresses: the app stays at the population level.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { Search } from 'lucide-react';

type Entry = { label: string; kind: string; targets: [string, number][]; keys: string[] };
const fold = (s: string) => s.normalize('NFD').replace(/[̀-ͯʻ‘’']/g, '').toLowerCase().trim();
const KIND: Record<string, string> = { district: 'District', legislator: 'Legislator', place: 'Place', neighborhood: 'Neighborhood', zip: 'ZIP' };

export function Finder({ onPick }: { onPick: (geo: string) => void }) {
  const [index, setIndex] = useState<(Entry & { hay: string })[]>([]);
  const [q, setQ] = useState('');
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    fetch('/api/finder-index').then(r => r.json())
      .then((xs: Entry[]) => setIndex(xs.map(x => ({ ...x, hay: fold([x.label, ...x.keys].join(' | ')) }))))
      .catch(() => setIndex([]));
  }, []);
  useEffect(() => {
    const close = (e: MouseEvent) => { if (box.current && !box.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, []);
  const results = useMemo(() => {
    let t = fold(q);
    if (t.length < 2 && !/^\d+$/.test(t)) return [];
    const num = t.match(/^(?:(hd|house|sd|senate)\s*-?\s*)?(\d{1,2})$/);
    if (num) {                                   // "44", "hd 44", "senate 12"
      const n = num[2].padStart(2, '0'), want = num[1]?.startsWith('s') ? ['SD'] : num[1] ? ['HD'] : ['HD', 'SD'];
      return index.filter(e => e.kind === 'district' && want.some(c => e.targets[0][0] === `${c}-${n}`));
    }
    t = t.replace(/\s+/g, ' ');
    const starts = index.filter(e => e.hay.startsWith(t) || e.hay.includes(' ' + t) || e.hay.includes('| ' + t));
    const rest = index.filter(e => !starts.includes(e) && e.hay.includes(t));
    return [...starts, ...rest].slice(0, 10);
  }, [q, index]);
  const pick = (g: string) => { onPick(g); setOpen(false); setQ(''); };

  return (
    <div ref={box} className="relative no-print">
      <label className="flex items-center gap-1.5 bg-premium-950 border border-premium-700 rounded-md px-2 py-1.5 focus-within:ring-2 focus-within:ring-cyan-600">
        <Search className="w-4 h-4 text-slate-500 shrink-0" />
        <span className="sr-only">Find a district, legislator, place or ZIP</span>
        <input value={q} onChange={e => { setQ(e.target.value); setOpen(true); }} onFocus={() => setOpen(true)}
          onKeyDown={e => { if (e.key === 'Escape') setOpen(false); if (e.key === 'Enter' && results[0]) pick(results[0].targets[0][0]); }}
          placeholder="Find district, legislator, place, ZIP" title="Find a district, legislator, place, neighborhood or ZIP" className="bg-transparent text-sm text-slate-200 w-40 xl:w-52 focus:outline-none" />
      </label>
      {open && results.length > 0 && (
        <ul role="listbox" className="absolute z-50 mt-1 w-[26rem] max-w-[calc(100vw-2rem)] max-h-[70vh] overflow-y-auto rounded-lg border border-premium-700 bg-premium-900 shadow-2xl divide-y divide-premium-800">
          {results.map(r => (
            <li key={r.kind + r.label} className="px-3 py-2">
              <div className="flex items-center justify-between gap-2">
                <button onClick={() => pick(r.targets[0][0])} className="text-left text-sm text-slate-100 hover:text-cyan-300">{r.label}</button>
                <span className="text-[10px] uppercase tracking-wide text-slate-500">{KIND[r.kind] ?? r.kind}</span>
              </div>
              {(r.kind === 'place' || r.kind === 'neighborhood' || r.kind === 'zip') && (
                <div className="mt-1 flex flex-wrap gap-1">
                  {r.targets.map(([g, s]) => (
                    <button key={g} onClick={() => pick(g)} className="text-[11px] font-mono px-1.5 py-0.5 rounded border border-premium-700 text-slate-300 hover:text-cyan-300">
                      {g}{s < 0.995 ? ` · ${Math.round(s * 100)}%` : ''}</button>))}
                </div>
              )}
            </li>
          ))}
          <li className="px-3 py-1.5 text-[10px] text-slate-500">Shares are by land area. Street addresses are not searchable.</li>
        </ul>
      )}
    </div>
  );
}
