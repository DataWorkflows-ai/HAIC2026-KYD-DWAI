import { useEffect, useState } from 'react';
import { LayoutDashboard, Map, GitCompare, ListOrdered, HandHeart, MessageSquare, BookOpen, MapPinned, Star } from 'lucide-react';
import { api, type Geo, type Health } from './api';
import { GeoPicker, Pill, usePersistentState } from './ui';
import { AskTab, CompareTab, OverviewTab, ProgramsTab, SourcesTab } from './tabs';
import { MapTab } from './MapTab';
import { RankingsTab } from './RankingsTab';
import { Finder } from './Finder';

const TABS = [
  { id: 'overview', label: 'Overview', short: 'Overview', Icon: LayoutDashboard },
  { id: 'map', label: 'Map', short: 'Map', Icon: Map },
  { id: 'compare', label: 'Compare', short: 'Compare', Icon: GitCompare },
  { id: 'rankings', label: 'Rankings', short: 'Rankings', Icon: ListOrdered },
  { id: 'programs', label: 'Programs', short: 'Programs', Icon: HandHeart },
  { id: 'ask', label: 'Ask the Agent', short: 'Ask', Icon: MessageSquare },
  { id: 'sources', label: 'Sources & Methods', short: 'Sources', Icon: BookOpen },
] as const;
const TAB_IDS: string[] = TABS.map(t => t.id);
const GEO_RE = /^(HD|SD)-\d{2}$|^HI$|^CNTY-\d{5}$/;

/** Shareable links: /house-22/map opens House District 22 on the Map tab (also /senate-12, /state;
 *  older #/HD-22/map links still work). */
const toSlug = (geo: string) => geo === 'HI' ? 'state' : geo.startsWith('HD') ? `house-${parseInt(geo.slice(3), 10)}`
  : geo.startsWith('SD') ? `senate-${parseInt(geo.slice(3), 10)}` : geo.toLowerCase();
function fromSlug(s: string | undefined): string | undefined {
  if (!s) return undefined;
  const t = s.toLowerCase(), m = t.match(/^(house|senate|hd|sd)-?(\d{1,2})$/);
  if (m) {
    const g = `${m[1].startsWith('s') ? 'SD' : 'HD'}-${m[2].padStart(2, '0')}`;
    return GEO_RE.test(g) ? g : undefined;
  }
  if (t === 'state' || t === 'hi') return 'HI';
  return GEO_RE.test(s.toUpperCase()) ? s.toUpperCase() : undefined;
}
function readHash(): { geo?: string; tab?: string } {
  const raw = window.location.hash ? window.location.hash.replace(/^#\/?/, '') : window.location.pathname.replace(/^\/+/, '');
  const [g, t] = decodeURIComponent(raw).split('/');
  return { geo: fromSlug(g), tab: t && TAB_IDS.includes(t) ? t : undefined };
}

// A shared link wins over the last-visited district and tab, from the very first render.
{
  const h = readHash();
  try {
    if (h.geo) localStorage.setItem('kyd_geo', JSON.stringify(h.geo));
    if (h.tab) localStorage.setItem('kyd_tab', JSON.stringify(h.tab));
  } catch { /* storage unavailable: the hash effect below still applies it */ }
}

export default function App() {
  const [tab, setTab] = usePersistentState<string>('kyd_tab', 'overview');
  const [office, setOffice] = usePersistentState<string | null>('kyd_office', null);
  const [geo, setGeo] = usePersistentState<string>('kyd_geo', office ?? 'HD-22');
  const [geos, setGeos] = useState<Geo[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [pending, setPending] = useState<string | null>(null);

  useEffect(() => { api.geographies().then(setGeos); api.health().then(setHealth).catch(() => setHealth(null)); }, []);
  // URL hash <-> district and tab, so a link opens the same view
  useEffect(() => {
    const apply = () => { const h = readHash(); if (h.geo) setGeo(h.geo); if (h.tab) setTab(h.tab); };
    apply();
    window.addEventListener('hashchange', apply);
    window.addEventListener('popstate', apply);
    return () => { window.removeEventListener('hashchange', apply); window.removeEventListener('popstate', apply); };
  }, []);
  useEffect(() => {
    const want = `/${toSlug(geo)}/${tab}`;
    if (window.location.pathname !== want || window.location.hash) window.history.replaceState(null, '', want);
  }, [geo, tab]);
  const ask = (q: string) => { setPending(q); setTab('ask'); };
  const districtControl = (
    <div className="flex items-center gap-2">
      <GeoPicker geos={geos} value={geo} onChange={setGeo} />
      {(geo.startsWith('HD') || geo.startsWith('SD')) && (
        <button onClick={() => setOffice(office === geo ? null : geo)} aria-pressed={office === geo}
          title={office === geo ? 'This is your office (click to clear)' : 'Set as my office: the map and agent default to it'}
          className={`p-1.5 rounded-md border ${office === geo ? 'border-amber-600 text-amber-300' : 'border-premium-700 text-slate-500 hover:text-amber-300'}`}>
          <Star className="w-4 h-4" fill={office === geo ? 'currentColor' : 'none'} />
        </button>
      )}
    </div>
  );

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {health?.demo && (
        <div role="status" className="bg-amber-900/70 text-amber-100 text-xs text-center py-1">
          DEMO MODE: figures are synthetic placeholders and are not real Census data.
        </div>
      )}
      <header className="h-16 border-b border-premium-800 flex items-center px-4 lg:px-6 bg-premium-900 shadow-md gap-4">
        <div className="flex items-center gap-3 min-w-max shrink-0">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-cyan-500 to-emerald-500 flex items-center justify-center shadow-lg">
            <MapPinned className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-emerald-400">KNOW YOUR DISTRICT</h1>
            <p className="text-xs text-slate-400 hidden xl:block">Hawaiʻi legislative district profiles</p>
          </div>
        </div>

        {/* On Overview the district picker sits in the page header next to the district name; elsewhere it sits here, next to the title. */}
        <div className="flex items-center gap-2 min-w-[1px] shrink-0">{tab !== 'overview' && districtControl}</div>
        <div className="hidden md:block shrink-0"><Finder onPick={setGeo} /></div>

        <nav aria-label="Sections" className="ml-auto flex gap-1 bg-premium-950 p-1 rounded-lg border border-premium-800 overflow-x-auto min-w-0">
          {TABS.map(({ id, label, short, Icon }) => (
            <button key={id} onClick={() => setTab(id)} aria-current={tab === id ? 'page' : undefined} title={label} aria-label={label}
              className={`flex items-center gap-2 px-2.5 py-1.5 rounded-md text-sm font-medium whitespace-nowrap transition ${tab === id ? 'bg-premium-800 text-cyan-400 border border-premium-700' : 'text-slate-400 hover:text-slate-200'}`}>
              <Icon className="w-4 h-4 shrink-0" />
              <span className="hidden min-[1600px]:inline">{short}</span>
            </button>
          ))}
        </nav>
      </header>

      <main className="flex-grow overflow-y-auto p-4 lg:p-6">
        <div className="print-only text-xs mb-2">
          Know Your District · {geos.find(g => g.geo_id === geo)?.name ?? geo} · printed {new Date().toLocaleDateString()} ·
          Sources: ACS 2020–2024 and the agencies listed on the Sources tab · {window.location.href}
        </div>
        {tab === 'overview' && <OverviewTab geo={geo} geos={geos} onAsk={ask} onPick={setGeo} picker={districtControl} />}
        {tab === 'map' && <MapTab geos={geos} geo={geo} office={office} onPick={setGeo} onOpen={g => { setGeo(g); setTab('overview'); }} />}
        {tab === 'compare' && <CompareTab geos={geos} geo={geo} />}
        {tab === 'rankings' && <RankingsTab onOpen={g => { setGeo(g); setTab('overview'); }} />}
        {tab === 'programs' && <ProgramsTab geo={geo} />}
        {tab === 'ask' && <AskTab geo={geo} pending={pending} clearPending={() => setPending(null)} />}
        {tab === 'sources' && <SourcesTab />}
      </main>

      <footer className="h-9 border-t border-premium-800 bg-premium-900 flex items-center justify-between px-6 text-xs text-slate-500 font-mono">
        <span>Nonpartisan · population-level only · every figure cited</span>
        <div className="flex gap-3">
          {health ? <>
            <Pill tone={health.demo ? 'amber' : 'emerald'}>data: {health.mode}</Pill>
            <Pill tone={health.llm === 'none' ? 'slate' : 'cyan'}>S2: {health.llm}</Pill>
            <Pill>{health.geographies} geos · {health.programs} programs</Pill>
          </> : <Pill tone="red">API offline</Pill>}
        </div>
      </footer>
    </div>
  );
}
