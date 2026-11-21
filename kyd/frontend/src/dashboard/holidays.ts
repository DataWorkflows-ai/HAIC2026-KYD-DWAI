/** US federal and Hawaiʻi state holidays, computed (no lookup table to go stale). Dates are local 'YYYY-MM-DD'. */
export type HolidayTag = 'Federal' | 'State';
export type Holiday = { date: string; name: string; tags: HolidayTag[]; observed?: string; note?: string };

export const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
export const parseIso = (s: string) => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d); };

/** n-th weekday (0=Sun) of a month; n = -1 for the last one. */
function nth(y: number, m: number, dow: number, n: number): Date {
  if (n < 0) { const d = new Date(y, m + 1, 0); d.setDate(d.getDate() - ((d.getDay() - dow + 7) % 7)); return d; }
  const d = new Date(y, m, 1); d.setDate(1 + ((dow - d.getDay() + 7) % 7) + (n - 1) * 7); return d;
}

/** Western Easter (anonymous Gregorian algorithm). */
function easter(y: number): Date {
  const a = y % 19, b = Math.floor(y / 100), c = y % 100, d = Math.floor(b / 4), e = b % 4, f = Math.floor((b + 8) / 25),
    g = Math.floor((b - f + 1) / 3), h = (19 * a + b - d - g + 15) % 30, i = Math.floor(c / 4), k = c % 4,
    l = (32 + 2 * e + 2 * i - h - k) % 7, m = Math.floor((a + 11 * h + 22 * l) / 451), mo = Math.floor((h + l - 7 * m + 114) / 31);
  return new Date(y, mo - 1, ((h + l - 7 * m + 114) % 31) + 1);
}

/** Fixed-date holidays on a weekend are observed on the nearest weekday. */
function fixed(y: number, m: number, d: number, name: string, tags: HolidayTag[], note?: string): Holiday {
  const dt = new Date(y, m, d), dow = dt.getDay();
  const obs = dow === 6 ? new Date(y, m, d - 1) : dow === 0 ? new Date(y, m, d + 1) : null;
  return { date: iso(dt), name, tags, ...(obs ? { observed: iso(obs) } : {}), ...(note ? { note } : {}) };
}
const on = (d: Date, name: string, tags: HolidayTag[], note?: string): Holiday => ({ date: iso(d), name, tags, ...(note ? { note } : {}) });

const BOTH: HolidayTag[] = ['Federal', 'State'];
export function holidaysFor(y: number): Holiday[] {
  const gf = easter(y); gf.setDate(gf.getDate() - 2);
  const firstMonNov = nth(y, 10, 1, 1);
  const hs: Holiday[] = [
    fixed(y, 0, 1, "New Year's Day", BOTH),
    on(nth(y, 0, 1, 3), 'Martin Luther King Jr. Day', BOTH),
    on(nth(y, 1, 1, 3), "Presidents' Day", BOTH),
    fixed(y, 2, 26, 'Prince Jonah Kūhiō Kalanianaʻole Day', ['State']),
    on(gf, 'Good Friday', ['State']),
    on(nth(y, 4, 1, -1), 'Memorial Day', BOTH),
    fixed(y, 5, 11, 'King Kamehameha I Day', ['State']),
    fixed(y, 5, 19, 'Juneteenth', ['Federal']),
    fixed(y, 6, 4, 'Independence Day', BOTH),
    on(nth(y, 7, 5, 3), 'Statehood Day', ['State']),
    on(nth(y, 8, 1, 1), 'Labor Day', BOTH),
    on(nth(y, 9, 1, 2), 'Columbus Day', ['Federal'], 'Federal only; not a Hawaiʻi state holiday'),
    fixed(y, 10, 11, 'Veterans Day', BOTH),
    on(nth(y, 10, 4, 4), 'Thanksgiving Day', BOTH),
    fixed(y, 11, 25, 'Christmas Day', BOTH),
  ];
  if (y % 2 === 0) hs.push(on(new Date(y, 10, firstMonNov.getDate() + 1), 'General Election Day', ['State']));
  return hs.sort((a, b) => a.date.localeCompare(b.date));
}

/** Holidays from `from` (inclusive) through `days` ahead, matched on the actual or the observed date. */
export function upcomingHolidays(from = new Date(), days = 90): Holiday[] {
  const lo = iso(from), end = new Date(from); end.setDate(end.getDate() + days);
  const hi = iso(end), y = from.getFullYear();
  return [...holidaysFor(y), ...holidaysFor(y + 1)].filter(h => (h.date >= lo && h.date <= hi) || (h.observed && h.observed >= lo && h.observed <= hi));
}

/** date -> holidays falling (or observed) on it, for a calendar month view. */
export function holidayIndex(year: number): Record<string, Holiday[]> {
  const idx: Record<string, Holiday[]> = {};
  for (const h of [...holidaysFor(year - 1), ...holidaysFor(year), ...holidaysFor(year + 1)])
    for (const d of h.observed ? [h.date, h.observed] : [h.date]) (idx[d] ??= []).push(h);
  return idx;
}
