import type { Geo, User } from '../api';

export type WidgetType = 'snapshot' | 'kpi' | 'rank' | 'minimap' | 'snap' | 'programs' | 'trends' | 'crime' | 'schools' | 'housing'
  | 'reps' | 'ask' | 'chats' | 'answer' | 'holidays' | 'calendar' | 'notes' | 'usage';
export type Chamber = 'sldl' | 'sldu';
export type Series = 'unemployment' | 'crime' | 'vital';
export type CalEvent = { date: string; text: string };
export type Todo = { id: string; text: string; done: boolean };

/** Every field is optional; an empty geo means "follow the district selected in the app". */
export type WidgetConfig = {
  geo?: string; indicator?: string; chamber?: Chamber; series?: Series;
  text?: string; question?: string; created?: string;        // answer pins
  events?: CalEvent[]; notes?: string; todos?: Todo[];
};
export type Widget = { id: string; type: WidgetType; title?: string; x: number; y: number; w: number; h: number; hidden?: boolean; config: WidgetConfig };
export type Layout = { version: 1; updated: number; widgets: Widget[] };

export type Ctx = {
  geos: Geo[]; user: User; onAsk: (q: string) => void; onOpen: (tab: string, geo?: string) => void; onOpenChat: (id: string) => void;
};
export type WidgetProps = { w: Widget; geo: string; ctx: Ctx; setConfig: (patch: Partial<WidgetConfig>) => void };
