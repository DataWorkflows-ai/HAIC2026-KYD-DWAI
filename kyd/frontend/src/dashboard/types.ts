import type { Geo, User } from '../api';

export type WidgetType = 'snapshot' | 'kpi' | 'rank' | 'minimap' | 'snap' | 'programs' | 'trends' | 'crime' | 'schools' | 'housing'
  | 'reps' | 'ask' | 'chats' | 'answer' | 'holidays' | 'calendar' | 'notes' | 'usage';
export type Chamber = 'sldl' | 'sldu';
export type Series = 'unemployment' | 'crime' | 'vital';
export type CalEvent = { id: string; date: string; text: string; time?: string };
export type Todo = { id: string; text: string; done: boolean };

/** Every field is optional; an empty geo means "follow the district selected in the app". */
export type WidgetConfig = {
  geo?: string; indicator?: string; chamber?: Chamber; series?: Series;
  text?: string; question?: string; created?: string;        // answer pins
  events?: { date: string; text: string }[];                 // calendar entries saved before they moved to Layout.calendar
  notes?: string; todos?: Todo[];
};
export type Widget = { id: string; type: WidgetType; title?: string; x: number; y: number; w: number; h: number; hidden?: boolean; config: WidgetConfig };
/** `calendar` is shared by the Calendar widget and the Calendar tab. */
export type Layout = { version: 1; updated: number; widgets: Widget[]; calendar: CalEvent[] };

export type Ctx = {
  geos: Geo[]; user: User; calendar: CalEvent[];
  onAsk: (q: string) => void; onOpen: (tab: string, geo?: string) => void; onOpenChat: (id: string) => void;
};
export type WidgetProps = { w: Widget; geo: string; ctx: Ctx; setConfig: (patch: Partial<WidgetConfig>) => void };
