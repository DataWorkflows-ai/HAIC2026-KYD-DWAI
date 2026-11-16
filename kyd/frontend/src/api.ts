export type Obs = {
  obs_id: string; geo_id: string; indicator: string; label: string; unit: string;
  value: number | null; moe: number | null; cv: number | null; vintage: string;
  method: string; method_note?: string | null; source_id: string; flags: string[];
};
export type Geo = { geo_id: string; geo_type: string; name: string; counties: string[] };
export type Program = {
  program_id: string; name: string; agency: string; level: string; summary: string;
  official_url: string; populations: string[]; proxy_indicators: string[];
};
export type ProgramMatch = {
  program: Program; score: number; eligible_proxy: Obs | null; uptake_proxy: Obs | null;
  gap_note: string | null; rationale: string[];
};
export type Profile = {
  geography: Geo; observations: Obs[]; comparisons: Record<string, Obs[]>; peers: string[]; data_as_of: string;
};
export type Answer = {
  text: string; route: 'S1' | 'S2' | 'REFUSED'; intent: string | null; geo_ids: string[];
  observations: Obs[]; programs: ProgramMatch[]; escalation_reasons: string[]; trace: any[];
};
export type Member = {
  geo_id: string; name: string | null; title: string; basis: string;
  status: 'official' | 'secondary' | 'verify' | 'pending'; source: string | null; source_url: string | null; note: string | null;
};
export type Counterpart = { geo_id: string; share_of_this: number; share_of_other: number; member: Member | null };
export type Board = { number: number; name: string; share: number };
export type Council = { body: string; number: number | null; name: string | null; share: number };
export type MapDistrict = {
  geo_id: string; name: string; counties: string[]; member: Member | null; counterparts: Counterpart[];
  neighborhoods: string[]; boards: Board[]; council: Council[];
  top_program: string | null; figures: Obs[];
};
export type MapSummary = { roster: { as_of: string; counts: Record<string, number> }; overlap_method: string; local_method: string; districts: MapDistrict[] };
export type VerifySummary = { generated_at: string; git_sha: string | null; pass: number; info: number; warn: number; fail: number };
export type Health = { ok: boolean; mode: string; demo: boolean; llm: string; graph: string; verification: VerifySummary | null; geographies: number; programs: number };
export type VCheck = { id: string; source: string; kind: string; status: 'pass' | 'info' | 'warn' | 'fail'; detail: string; expected: any; actual: any; location: string | null };
export type Verification = {
  summary: VerifySummary; checks: VCheck[];
  capabilities: { capability: string; name: string; program_id: string | null; status: string; datasets: { id: string; status: string; verified_at: string | null }[] }[];
};

export type CrossEstimate = {
  program_id: string; name: string; rule: string; source: { title: string; url: string }; unit: string;
  estimate: number | null; low: number | null; high: number | null; formula: string; input_obs_ids: string[];
  confidence: 'high' | 'medium' | 'low'; assumptions: string[];
};
export type CrossProgram = { geo_id: string; estimates: CrossEstimate[]; note: string };
export type ProgramContext = {
  geo_id: string; county: string;
  school_meals: { title: string; observations: Obs[]; state_pct: number | null; source: string; url: string; note: string };
  facts: { program: string; level: string; agency: string; income_rule: string; limit_1_person: string; limit_4_person: string; enrollment_latest: string; smallest_geography: string; link: string }[];
  hud: { title: string; as_of: string; observations: Obs[]; state_per_1k_hh: number | null; source: string; caveats: string[] };
  medquest: { title: string; sfy: number; statewide: number; source: string; caveats: string[];
    islands: { island: string; recipients: number; share_of_state_percent: number; enrollment_to_need_ratio: number | null }[];
    trend: { sfy: number; recipients: number }[] };
  tanf_island: { title: string; month: string; island?: string; county?: string; tanf_persons?: number; population?: number;
    tanf_per_1000?: number; poverty_rate_percent?: number; source: string; note: string };
  county_snap: { title: string; month: string; source: string; rows: { area: string; households: number; persons: number }[] };
  tanf_underenrollment: { title: string; available: boolean; poverty_population: number | null; caveats: string[];
    groups: { label: string; poverty_count: number | null; district_poverty_share_percent: number | null;
      statewide_tanf_share_percent: number; under_enrollment_pp: number | null; note: string }[] };
};

// Bearer token from the login flow (see backend/app/auth.py). Stored per tab; absent = anonymous viewer.
function authHeader(): Record<string, string> {
  try { const t = sessionStorage.getItem('kyd_token'); return t ? { Authorization: `Bearer ${t}` } : {}; }
  catch { return {}; }
}

async function j<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, { ...init, headers: { ...authHeader(), ...(init?.headers ?? {}) } });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

export const api = {
  health: () => j<Health>('/api/health'),
  geographies: () => j<Geo[]>('/api/geographies'),
  profile: (g: string) => j<Profile>(`/api/districts/${g}`),
  programs: (g: string) => j<ProgramMatch[]>(`/api/districts/${g}/programs`),
  crossProgram: (g: string) => j<CrossProgram>(`/api/districts/${g}/cross-program`),
  programContext: (g: string) => j<ProgramContext>(`/api/districts/${g}/program-context`),
  compare: (a: string, b: string) => j<{ a: string; b: string; rows: { indicator: string; a: Obs; b: Obs; significant: boolean }[] }>(`/api/compare?a=${a}&b=${b}`),
  mapSummary: (t: string) => j<MapSummary>(`/api/map-summary?geo_type=${t}`),
  mapLayer: (ind: string, t: string) => j<{ features: Obs[] }>(`/api/map/${ind}?geo_type=${t}`),
  indicators: () => j<{ indicator: string; label: string; unit: string; topic: string }[]>('/api/indicators'),
  sources: () => j<any[]>('/api/sources'),
  cite: (id: string) => j<any>(`/api/sources/observation/${id}`),
  verification: () => j<Verification>('/api/verification'),
  ask: (question: string, geo_id: string | null) =>
    j<Answer>('/api/agent/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question, geo_id }) }),
};

export function fmt(o: Pick<Obs, 'value' | 'unit'>): string {
  if (o.value === null || o.value === undefined) return '—';
  if (o.unit === 'usd') return '$' + Math.round(o.value).toLocaleString();
  if (o.unit === 'pct') return o.value.toFixed(1) + '%';
  if (o.unit === 'count') return Math.round(o.value).toLocaleString();
  if (o.unit === 'per_1000') return o.value.toFixed(1) + ' per 1,000';
  return String(o.value);
}
