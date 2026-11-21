import { useCallback, useEffect, useRef, useState } from 'react';
import { api, type Role } from '../api';
import { presetWidgets } from './catalog';
import { readLocal, sanitize, sortEvents, writeLocal } from './layout';
import type { CalEvent, Layout } from './types';
import { holidaysFor, iso, parseIso, type Holiday } from './holidays';

export const HST = 'Pacific/Honolulu';
/** Today's date in Hawaiʻi as YYYY-MM-DD, whatever the device's time zone. */
export const hstToday = () => new Date().toLocaleDateString('en-CA', { timeZone: HST });

export type Upcoming = { date: string; time?: string; text: string; kind: 'entry' | 'holiday'; id?: string };

/** Entries and holidays from today for `days` days, in date order. */
export function upcoming(events: CalEvent[], days = 30): Upcoming[] {
  const from = hstToday(), end = parseIso(from);
  end.setDate(end.getDate() + days);
  const to = iso(end), y = Number(from.slice(0, 4));
  const hol: Holiday[] = [...holidaysFor(y), ...holidaysFor(y + 1)];
  const items: Upcoming[] = [
    ...events.filter(e => e.date >= from && e.date <= to).map(e => ({ date: e.date, time: e.time, text: e.text, kind: 'entry' as const, id: e.id })),
    ...hol.filter(h => h.date >= from && h.date <= to).map(h => ({ date: h.date, text: h.name, kind: 'holiday' as const })),
  ];
  return items.sort((a, b) => a.date.localeCompare(b.date) || (a.time ?? '').localeCompare(b.time ?? ''));
}

/** The Calendar tab's copy of the saved layout: newer of server and this browser wins, as on the dashboard. Writes keep
 *  the widgets as they are; with no saved layout yet, the default dashboard is saved alongside the entries. */
export function useCalendar(role: Role) {
  const base = (): Layout => readLocal() ?? { version: 1, updated: 0, widgets: presetWidgets('legislator', role), calendar: [] };
  const ref = useRef<Layout>(base());
  const [events, setEvents] = useState<CalEvent[]>(ref.current.calendar);
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  useEffect(() => {
    let live = true;
    api.dashboard().then(r => {
      const s = sanitize(r.layout);
      if (live && s && s.updated > ref.current.updated) { ref.current = s; writeLocal(s); setEvents(s.calendar); }
    }).catch(() => live && setStatus('error'));
    return () => { live = false; };
  }, []);
  const save = useCallback((next: CalEvent[]) => {
    const l: Layout = { ...ref.current, updated: Date.now(), calendar: sortEvents(next) };
    ref.current = l; writeLocal(l); setEvents(l.calendar); setStatus('saving');
    api.saveDashboard(l).then(() => setStatus('saved'), () => setStatus('error'));
  }, []);
  return { events, status, save };
}
