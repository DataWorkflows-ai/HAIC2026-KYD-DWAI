import type { Role } from '../api';
import type { Widget, WidgetConfig, WidgetType } from './types';

export type Field = 'title' | 'geo' | 'indicator' | 'chamber' | 'series';
type Meta = { title: string; desc: string; size: [number, number]; fields: Field[]; admin?: boolean; pinOnly?: boolean };

export const META: Record<WidgetType, Meta> = {
  snapshot: { title: 'District snapshot', desc: 'Headline figures for the district', size: [8, 4], fields: ['title', 'geo'] },
  kpi: { title: 'Key figure', desc: 'One indicator, compared with the state', size: [4, 4], fields: ['title', 'geo', 'indicator'] },
  rank: { title: 'Rankings', desc: 'Where the district ranks among its chamber', size: [4, 6], fields: ['title', 'geo', 'chamber'] },
  minimap: { title: 'Mini map', desc: 'Choropleth of one indicator by district', size: [6, 8], fields: ['title', 'indicator', 'chamber', 'geo'] },
  snap: { title: 'SNAP: look eligible, not enrolled', desc: 'Range of estimates and similar districts', size: [4, 6], fields: ['title', 'geo'] },
  programs: { title: 'Program matches', desc: 'Top five programs for the district', size: [4, 6], fields: ['title', 'geo'] },
  trends: { title: 'Trends', desc: 'Unemployment, crime (Oʻahu) or births and deaths over time', size: [4, 6], fields: ['title', 'geo', 'series'] },
  crime: { title: 'Crime (Oʻahu estimate)', desc: 'Latest district crime estimates with caveats', size: [6, 5], fields: ['title', 'geo'] },
  schools: { title: 'Schools', desc: 'School meals and test scores vs the state', size: [4, 6], fields: ['title', 'geo'] },
  housing: { title: 'Housing', desc: 'HUD-assisted housing, rent burden, public housing', size: [6, 5], fields: ['title', 'geo'] },
  reps: { title: 'Who represents it', desc: 'Legislators for the district and overlapping districts', size: [4, 5], fields: ['title', 'geo', 'chamber'] },
  ask: { title: 'Ask', desc: 'Quick question to the agent', size: [4, 5], fields: ['title', 'geo'] },
  chats: { title: 'Chats', desc: 'Pinned and recent chats', size: [4, 5], fields: ['title'] },
  answer: { title: 'Pinned answer', desc: 'Pin an answer from the Ask tab', size: [6, 6], fields: ['title'], pinOnly: true },
  holidays: { title: 'Upcoming holidays', desc: 'Federal and Hawaiʻi state holidays, next 90 days', size: [4, 5], fields: ['title'] },
  calendar: { title: 'Calendar', desc: 'Today at a glance and what is coming up; double-click for the Calendar tab', size: [4, 8], fields: ['title'] },
  notes: { title: 'Notes & to-dos', desc: 'Scratch notes and a checklist', size: [4, 6], fields: ['title'] },
  usage: { title: 'Usage', desc: 'Questions, LLM budget and top users (admins)', size: [12, 5], fields: ['title'], admin: true },
};
export const isType = (t: unknown): t is WidgetType => typeof t === 'string' && t in META;
export const canSee = (t: WidgetType, role: Role) => !META[t].admin || role === 'admin' || role === 'owner';

export const DEFERRED = [
  { title: 'Homeless counts', note: 'PIT data not loaded' },
  { title: 'Legislative bills & updates', note: 'Capitol integration not built' },
  { title: 'External calendar sync', note: 'Google / Outlook connection not built' },
];

type Spec = [WidgetType, number, number, number, number, WidgetConfig?];
const build = (specs: Spec[]): Widget[] => specs.map(([type, x, y, w, h, config], i) => ({ id: `${type}-p${i}`, type, x, y, w, h, config: config ?? {} }));

export const PRESETS: { id: string; title: string; specs: Spec[] }[] = [
  { id: 'legislator', title: 'Legislator overview', specs: [
    ['snapshot', 0, 0, 8, 4], ['kpi', 8, 0, 4, 4, { indicator: 'pct_below_fpl' }],
    ['snap', 0, 4, 4, 7], ['programs', 4, 4, 4, 7], ['trends', 8, 4, 4, 7],
    ['reps', 0, 11, 4, 5], ['ask', 4, 11, 4, 5], ['chats', 8, 11, 4, 5],
    ['calendar', 0, 16, 4, 8], ['notes', 4, 16, 8, 8]] },
  { id: 'constituent', title: 'Constituent services', specs: [
    ['snapshot', 0, 0, 12, 3], ['programs', 0, 3, 4, 7], ['snap', 4, 3, 4, 7], ['housing', 8, 3, 4, 7],
    ['schools', 0, 10, 4, 7], ['ask', 4, 10, 4, 4], ['chats', 4, 14, 4, 3], ['calendar', 8, 10, 4, 8], ['notes', 0, 18, 12, 5]] },
  { id: 'budget', title: 'Budget & finance', specs: [
    ['snapshot', 0, 0, 8, 4], ['kpi', 8, 0, 4, 4, { indicator: 'median_hh_income' }],
    ['rank', 0, 4, 4, 7], ['trends', 4, 4, 4, 7], ['housing', 8, 4, 4, 7],
    ['minimap', 0, 11, 8, 8, { indicator: 'median_hh_income' }], ['notes', 8, 11, 4, 8]] },
  { id: 'hhs', title: 'Health & human services', specs: [
    ['snapshot', 0, 0, 8, 4], ['kpi', 8, 0, 4, 4, { indicator: 'pct_uninsured' }],
    ['snap', 0, 4, 4, 7], ['programs', 4, 4, 4, 7], ['schools', 8, 4, 4, 7],
    ['crime', 0, 11, 8, 6], ['holidays', 8, 11, 4, 6]] },
];

export function presetWidgets(id: string, role: Role): Widget[] {
  const p = PRESETS.find(x => x.id === id) ?? PRESETS[0];
  const ws = build(p.specs);
  if (p.id === 'legislator' && canSee('usage', role)) ws.push(...build([['usage', 0, 24, 12, 5]]).map(w => ({ ...w, id: 'usage-p' })));
  return ws;
}
