import { useEffect, useState } from 'react';
import { LayoutDashboard, LayoutGrid, CalendarDays, Map, GitCompare, ListOrdered, HandHeart, MessageSquare, BookOpen, Star, Users, LogOut } from 'lucide-react';
import { api, hasToken, setToken, SIGNED_OUT, type Geo, type Health, type User } from './api';
import { GeoPicker, Pill, usePersistentState } from './ui';
import { CompareTab, OverviewTab, ProgramsTab, SourcesTab } from './tabs';
import { MapTab } from './MapTab';
import { RankingsTab } from './RankingsTab';
import { Finder } from './Finder';
import { Login } from './Login';
import { ChatTab } from './ChatTab';
import { AdminTab } from './AdminTab';
import { DashboardTab } from './Dashboard';
import { CalendarTab } from './CalendarTab';
import { ThemePicker } from './theme';
import dwaiLogo from './brand/dataworkflows-logo.png';

const TABS = [
  { id: 'dashboard', label: 'Dashboard', short: 'Dashboard', Icon: LayoutGrid },
  { id: 'calendar', label: 'Calendar', short: 'Calendar', Icon: CalendarDays },
  { id: 'overview', label: 'Overview', short: 'Overview', Icon: LayoutDashboard },
  { id: 'map', label: 'Map', short: 'Map', Icon: Map },
  { id: 'compare', label: 'Compare', short: 'Compare', Icon: GitCompare },
  { id: 'rankings', label: 'Rankings', short: 'Rankings', Icon: ListOrdered },
  { id: 'programs', label: 'Programs', short: 'Programs', Icon: HandHeart },
  { id: 'ask', label: 'Chat with the agent', short: 'Chat', Icon: MessageSquare },
  { id: 'sources', label: 'Sources & Methods', short: 'Sources', Icon: BookOpen },
  { id: 'admin', label: 'Accounts & usage', short: 'Accounts', Icon: Users },
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

/** Sign-in gate: nothing but the sign-in page until there is an account. */
export default function App() {
  const [user, setUser] = useState<User | null | undefined>(hasToken() ? undefined : null);
  const [, setTab] = usePersistentState<string>('kyd_tab', 'dashboard');
  useEffect(() => {
    if (hasToken()) api.me().then(setUser).catch(() => setUser(null));
    const out = () => setUser(null);
    window.addEventListener(SIGNED_OUT, out);
    return () => window.removeEventListener(SIGNED_OUT, out);
  }, []);
  if (user === undefined) return <div className="h-screen flex items-center justify-center text-sm text-slate-500">Loading…</div>;
  if (!user) return <Login onSignedIn={u => { setTab('dashboard'); setUser(u); }} />;
  const signOut = () => {
    if (user.email.endsWith('@guest.kyd') && !window.confirm('Signing out ends this guest workspace and its chats. Sign out?')) return;
    setToken(null); setUser(null);
  };
  return <Workspace user={user} onSignOut={signOut} />;
}

function Workspace({ user, onSignOut }: { user: User; onSignOut: () => void }) {
  const [tab, setTab] = usePersistentState<string>('kyd_tab', 'dashboard');
  const [office, setOffice] = usePersistentState<string | null>('kyd_office', null);
  const [geo, setGeo] = usePersistentState<string>('kyd_geo', office ?? 'HD-22');
  const [geos, setGeos] = useState<Geo[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [pending, setPending] = useState<string | null>(null);
  const [openChat, setOpenChat] = useState<string | null>(null);
  const staff = user.role === 'owner' || user.role === 'admin';
  const tabs = TABS.filter(t => t.id !== 'admin' || staff);

  useEffect(() => { api.geographies().then(setGeos).catch(() => setGeos([])); api.health().then(setHealth).catch(() => setHealth(null)); }, []);
  useEffect(() => { if (tab === 'admin' && !staff) setTab('dashboard'); }, [tab, staff]);
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
      <header className="shrink-0 min-h-16 min-[1440px]:h-16 py-2 min-[1440px]:py-0 border-b border-premium-800 flex flex-wrap min-[1440px]:flex-nowrap items-center px-4 lg:px-6 bg-premium-900 shadow-md gap-x-4 gap-y-2">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 max-w-full min-[1440px]:shrink-0">
          <div>
            <h1 className="text-lg font-bold whitespace-nowrap text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-emerald-400">KNOW YOUR DISTRICT</h1>
            <p className="text-xs text-slate-400 hidden min-[1440px]:block">Hawaiʻi legislative district profiles</p>
          </div>
          <div className="flex items-center gap-2 no-print">
            <span className="text-sm text-slate-400">by</span>
            <img src={dwaiLogo} alt="DataWorkflows.ai" width={181} height={36} className="h-9 w-auto" />
          </div>
        </div>

        {/* On Overview the district picker sits in the page header next to the district name; elsewhere it sits here, next to the title. */}
        <div className="flex items-center gap-2 min-w-[1px] shrink-0">{tab !== 'overview' && districtControl}</div>
        <div className="shrink-0"><Finder onPick={setGeo} /></div>

        <nav aria-label="Sections" className="w-full min-[1440px]:w-auto justify-between md:justify-start min-[1440px]:ml-auto flex gap-1 bg-premium-950 p-1 rounded-lg border border-premium-800 overflow-x-auto min-w-0">
          {tabs.map(({ id, label, short, Icon }) => (
            <button key={id} onClick={() => setTab(id)} aria-current={tab === id ? 'page' : undefined} title={label} aria-label={label}
              className={`flex items-center gap-2 px-2.5 py-1.5 rounded-md text-sm font-medium whitespace-nowrap transition ${tab === id ? 'bg-premium-800 text-cyan-400 border border-premium-700' : 'text-slate-400 hover:text-slate-200'}`}>
              <Icon className="w-4 h-4 shrink-0" />
              <span className="hidden md:inline min-[1440px]:hidden min-[1800px]:inline">{short}</span>
            </button>
          ))}
        </nav>
        <div className="flex items-center gap-2 shrink-0 no-print">
          <ThemePicker compact />
          <span className="text-xs text-slate-300 max-w-[10rem] truncate" title={user.email}>{user.name}</span>
          {user.role !== 'user' && <Pill tone={user.role === 'owner' ? 'amber' : 'cyan'}>{user.role}</Pill>}
          <button onClick={onSignOut} title="Sign out" aria-label="Sign out" className="p-1.5 rounded-md text-slate-400 hover:text-cyan-300 hover:bg-premium-800">
            <LogOut className="w-4 h-4" /></button>
        </div>
      </header>

      <main className={`flex-grow p-4 lg:p-6 ${tab === 'ask' ? 'overflow-hidden min-h-0' : 'overflow-y-auto'}`}>
        <div className="print-only text-xs mb-2">
          Know Your District by DataWorkflows.ai · {geos.find(g => g.geo_id === geo)?.name ?? geo} · printed {new Date().toLocaleDateString()} ·
          Sources: ACS 2020–2024 and the agencies listed on the Sources tab · {window.location.href}
        </div>
        {tab === 'dashboard' && <DashboardTab geo={geo} geos={geos} user={user} onAsk={ask}
          onOpen={(t, g) => { if (g) setGeo(g); setTab(t); }} onOpenChat={id => { setOpenChat(id); setTab('ask'); }} />}
        {tab === 'calendar' && <CalendarTab user={user} />}
        {tab === 'overview' && <OverviewTab geo={geo} geos={geos} onAsk={ask} onPick={setGeo} picker={districtControl} />}
        {tab === 'map' && <MapTab geos={geos} geo={geo} office={office} onPick={setGeo} onOpen={g => { setGeo(g); setTab('overview'); }} />}
        {tab === 'compare' && <CompareTab geos={geos} geo={geo} />}
        {tab === 'rankings' && <RankingsTab onOpen={g => { setGeo(g); setTab('overview'); }} />}
        {tab === 'programs' && <ProgramsTab geo={geo} />}
        {tab === 'ask' && <ChatTab geo={geo} pending={pending} clearPending={() => setPending(null)}
          openChat={openChat} clearOpenChat={() => setOpenChat(null)} />}
        {tab === 'sources' && <SourcesTab />}
        {tab === 'admin' && staff && <AdminTab me={user} />}
      </main>

      <footer className="shrink-0 min-h-9 py-1 border-t border-premium-800 bg-premium-900 flex flex-wrap items-center justify-between gap-x-3 gap-y-1 px-4 lg:px-6 text-xs text-slate-500 font-mono">
        <span className="hidden sm:inline">Nonpartisan · population-level only · every figure cited</span>
        <div className="flex gap-3">
          {health ? <>
            <Pill tone={health.demo ? 'amber' : 'emerald'}>Data: {health.demo ? 'Demo' : 'Read-Only'}</Pill>
            <Pill tone={health.llm === 'none' ? 'slate' : 'cyan'}>S2: {health.llm}</Pill>
            <Pill>{health.geographies} geos · {health.programs} programs</Pill>
          </> : <Pill tone="red">API offline</Pill>}
        </div>
      </footer>
    </div>
  );
}
