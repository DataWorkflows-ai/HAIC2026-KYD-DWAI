import { useEffect, useState } from 'react';
import { LayoutDashboard, Map, GitCompare, HandHeart, MessageSquare, BookOpen, MapPinned } from 'lucide-react';
import { api, type Geo, type Health } from './api';
import { GeoPicker, Pill, usePersistentState } from './ui';
import { AskTab, CompareTab, MapTab, OverviewTab, ProgramsTab, SourcesTab } from './tabs';

const TABS = [
  { id: 'overview', label: 'Overview', Icon: LayoutDashboard },
  { id: 'map', label: 'Map', Icon: Map },
  { id: 'compare', label: 'Compare', Icon: GitCompare },
  { id: 'programs', label: 'Programs', Icon: HandHeart },
  { id: 'ask', label: 'Ask the Agent', Icon: MessageSquare },
  { id: 'sources', label: 'Sources & Methods', Icon: BookOpen },
] as const;

export default function App() {
  const [tab, setTab] = usePersistentState<string>('kyd_tab', 'overview');
  const [geo, setGeo] = usePersistentState<string>('kyd_geo', 'HD-22');
  const [geos, setGeos] = useState<Geo[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [pending, setPending] = useState<string | null>(null);

  useEffect(() => { api.geographies().then(setGeos); api.health().then(setHealth).catch(() => setHealth(null)); }, []);
  const ask = (q: string) => { setPending(q); setTab('ask'); };

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {health?.demo && (
        <div role="status" className="bg-amber-900/70 text-amber-100 text-xs text-center py-1">
          DEMO MODE: figures are synthetic placeholders and are not real Census data.
        </div>
      )}
      <header className="h-16 border-b border-premium-800 flex items-center justify-between px-6 bg-premium-900 shadow-md gap-4">
        <div className="flex items-center gap-3 min-w-max">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-cyan-500 to-emerald-500 flex items-center justify-center shadow-lg">
            <MapPinned className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-emerald-400">KNOW YOUR DISTRICT</h1>
            <p className="text-xs text-slate-400">Hawaiʻi legislative district profiles</p>
          </div>
        </div>

        <nav aria-label="Sections" className="flex gap-1 bg-premium-950 p-1 rounded-lg border border-premium-800 overflow-x-auto">
          {TABS.map(({ id, label, Icon }) => (
            <button key={id} onClick={() => setTab(id)} aria-current={tab === id ? 'page' : undefined}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium whitespace-nowrap transition ${tab === id ? 'bg-premium-800 text-cyan-400 border border-premium-700' : 'text-slate-400 hover:text-slate-200'}`}>
              <Icon className="w-4 h-4" />{label}
            </button>
          ))}
        </nav>

        <GeoPicker geos={geos} value={geo} onChange={setGeo} />
      </header>

      <main className="flex-grow overflow-y-auto p-6">
        {tab === 'overview' && <OverviewTab geo={geo} geos={geos} onAsk={ask} onPick={setGeo} />}
        {tab === 'map' && <MapTab geos={geos} geo={geo} onPick={g => { setGeo(g); setTab('overview'); }} />}
        {tab === 'compare' && <CompareTab geos={geos} geo={geo} />}
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
