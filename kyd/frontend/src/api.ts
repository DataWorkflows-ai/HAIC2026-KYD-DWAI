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
export type Health = { ok: boolean; mode: string; demo: boolean; llm: string; geographies: number; programs: number };

async function j<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init);
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

export const api = {
  health: () => j<Health>('/api/health'),
  geographies: () => j<Geo[]>('/api/geographies'),
  profile: (g: string) => j<Profile>(`/api/districts/${g}`),
  programs: (g: string) => j<ProgramMatch[]>(`/api/districts/${g}/programs`),
  compare: (a: string, b: string) => j<{ a: string; b: string; rows: { indicator: string; a: Obs; b: Obs; significant: boolean }[] }>(`/api/compare?a=${a}&b=${b}`),
  mapLayer: (ind: string, t: string) => j<{ features: Obs[] }>(`/api/map/${ind}?geo_type=${t}`),
  indicators: () => j<{ indicator: string; label: string; unit: string; topic: string }[]>('/api/indicators'),
  sources: () => j<any[]>('/api/sources'),
  cite: (id: string) => j<any>(`/api/sources/observation/${id}`),
  ask: (question: string, geo_id: string | null) =>
    j<Answer>('/api/agent/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question, geo_id }) }),
};

export function fmt(o: Pick<Obs, 'value' | 'unit'>): string {
  if (o.value === null || o.value === undefined) return '—';
  if (o.unit === 'usd') return '$' + Math.round(o.value).toLocaleString();
  if (o.unit === 'pct') return o.value.toFixed(1) + '%';
  if (o.unit === 'count') return Math.round(o.value).toLocaleString();
  return String(o.value);
}
