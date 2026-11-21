import type { Layout, Widget, WidgetConfig, WidgetType } from './types';
import { META, isType } from './catalog';

export const COLS = 12, ROW = 56, GAP = 12;
export const STORE = 'kyd_dashboard_v1';

export const newId = (t: string) => `${t}-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
const overlaps = (a: Widget, b: Widget) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
export const bottom = (ws: Widget[]) => Math.max(0, ...ws.filter(w => !w.hidden).map(w => w.y + w.h));

/** Keep `fixed` where it is and push every other visible widget down until nothing overlaps. */
export function resolve(ws: Widget[], fixed?: string): Widget[] {
  const placed: Widget[] = ws.filter(w => w.id === fixed && !w.hidden);
  const rest = ws.filter(w => w.id !== fixed && !w.hidden).sort((a, b) => a.y - b.y || a.x - b.x);
  for (const w0 of rest) {
    const w = { ...w0 };
    for (let hit = placed.find(p => overlaps(p, w)); hit; hit = placed.find(p => overlaps(p, w))) w.y = hit.y + hit.h;
    placed.push(w);
  }
  const byId = Object.fromEntries(placed.map(w => [w.id, w]));
  return ws.map(w => byId[w.id] ?? w);
}

export function clampBox(w: Widget): Widget {
  const ww = Math.max(2, Math.min(COLS, Math.round(w.w))), hh = Math.max(2, Math.round(w.h));
  return { ...w, w: ww, h: hh, x: Math.max(0, Math.min(COLS - ww, Math.round(w.x))), y: Math.max(0, Math.round(w.y)) };
}

export function makeWidget(type: WidgetType, config: WidgetConfig = {}, title?: string, at?: Partial<Pick<Widget, 'x' | 'y' | 'w' | 'h'>>): Widget {
  const [w, h] = META[type].size;
  return { id: newId(type), type, ...(title ? { title } : {}), x: 0, y: 0, w, h, ...at, config };
}

/** Append below everything that is showing. */
export function append(ws: Widget[], w: Widget): Widget[] {
  return [...ws, { ...w, x: 0, y: bottom(ws), hidden: false }];
}

/** Accept only well-formed layouts (server and localStorage are both untrusted input). */
export function sanitize(raw: unknown): Layout | null {
  const l = raw as Partial<Layout> | null;
  if (!l || typeof l !== 'object' || !Array.isArray(l.widgets)) return null;
  const widgets = l.widgets.filter((w): w is Widget => !!w && typeof w === 'object' && typeof w.id === 'string' && isType(w.type)
    && [w.x, w.y, w.w, w.h].every(n => typeof n === 'number' && isFinite(n)))
    .map(w => clampBox({ ...w, config: w.config && typeof w.config === 'object' ? w.config : {} }));
  return { version: 1, updated: typeof l.updated === 'number' ? l.updated : 0, widgets: resolve(widgets) };
}

export function readLocal(): Layout | null {
  try { return sanitize(JSON.parse(localStorage.getItem(STORE) ?? 'null')); } catch { return null; }
}
export function writeLocal(l: Layout) {
  try { localStorage.setItem(STORE, JSON.stringify(l)); } catch { /* storage full or unavailable */ }
}
