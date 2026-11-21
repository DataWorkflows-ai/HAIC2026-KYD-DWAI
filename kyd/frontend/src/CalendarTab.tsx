import { useMemo, useState } from 'react';
import { CalendarDays, Check, ChevronLeft, ChevronRight, CloudOff, Loader2, Plus, Trash2 } from 'lucide-react';
import type { User } from './api';
import { Modal } from './dashboard/panels';
import { hstToday, useCalendar } from './dashboard/calendar';
import { holidayIndex, iso, parseIso } from './dashboard/holidays';
import { newId } from './dashboard/layout';
import type { CalEvent } from './dashboard/types';

const input = 'w-full bg-premium-950 border border-premium-700 rounded-md px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-600';
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

type Draft = { id?: string; date: string; time: string; text: string };

function EntryModal({ draft, onSave, onDelete, onClose }: {
  draft: Draft; onSave: (d: Draft) => void; onDelete?: () => void; onClose: () => void;
}) {
  const [d, setD] = useState(draft);
  return (
    <Modal title={draft.id ? 'Edit entry' : 'New entry'} onClose={onClose}>
      <form onSubmit={e => { e.preventDefault(); if (d.text.trim()) onSave(d); }} className="space-y-3">
        <label className="block text-xs text-slate-400 space-y-1"><span>What</span>
          <input autoFocus className={input} value={d.text} onChange={e => setD({ ...d, text: e.target.value })} maxLength={140} required placeholder="e.g. Town hall, Waipahu" /></label>
        <div className="grid grid-cols-2 gap-2">
          <label className="block text-xs text-slate-400 space-y-1"><span>Date</span>
            <input type="date" className={input} value={d.date} onChange={e => setD({ ...d, date: e.target.value })} required /></label>
          <label className="block text-xs text-slate-400 space-y-1"><span>Time (optional, HST)</span>
            <input type="time" className={input} value={d.time} onChange={e => setD({ ...d, time: e.target.value })} /></label>
        </div>
        <div className="flex items-center justify-between pt-1">
          {onDelete ? <button type="button" onClick={onDelete} className="inline-flex items-center gap-1 px-3 py-1.5 rounded-md text-xs border border-red-900 text-red-400 hover:bg-red-950">
            <Trash2 className="w-3.5 h-3.5" />Delete</button> : <span />}
          <div className="flex gap-2">
            <button type="button" onClick={onClose} className="px-3 py-1.5 rounded-md text-xs border border-premium-700 text-slate-400">Cancel</button>
            <button className="px-4 py-1.5 rounded-md text-xs font-medium bg-cyan-700 hover:bg-cyan-600 text-white">{draft.id ? 'Save' : 'Add entry'}</button>
          </div>
        </div>
      </form>
    </Modal>
  );
}

/** Month view of your entries and Federal / Hawaiʻi holidays. Entries are shared with the dashboard's Calendar widget. */
export function CalendarTab({ user }: { user: User }) {
  const { events, status, save } = useCalendar(user.role);
  const today = hstToday();
  const [cursor, setCursor] = useState(() => { const t = parseIso(today); return new Date(t.getFullYear(), t.getMonth(), 1); });
  const [draft, setDraft] = useState<Draft | null>(null);
  const y = cursor.getFullYear(), m = cursor.getMonth();
  const hol = useMemo(() => ({ ...holidayIndex(y - 1), ...holidayIndex(y), ...holidayIndex(y + 1) }), [y]);
  const byDay = useMemo(() => {
    const o: Record<string, CalEvent[]> = {};
    for (const e of events) (o[e.date] ??= []).push(e);
    return o;
  }, [events]);
  const cells = Array.from({ length: 42 }, (_, i) => new Date(y, m, 1 - cursor.getDay() + i));

  const create = (date: string) => setDraft({ date, time: '', text: '' });
  const edit = (e: CalEvent) => setDraft({ id: e.id, date: e.date, time: e.time ?? '', text: e.text });
  const commit = (d: Draft) => {
    const entry: CalEvent = { id: d.id ?? newId('ev'), date: d.date, text: d.text.trim().slice(0, 140), ...(d.time ? { time: d.time } : {}) };
    save([...events.filter(e => e.id !== entry.id), entry]);
    setDraft(null);
  };
  const remove = (id: string) => { save(events.filter(e => e.id !== id)); setDraft(null); };

  return (
    <div className="flex flex-col h-full min-h-[36rem]">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold text-slate-100 flex items-center gap-2">
            <CalendarDays className="w-5 h-5 text-cyan-400" />{cursor.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}</h1>
          <div className="flex gap-1">
            <button onClick={() => setCursor(new Date(y, m - 1, 1))} aria-label="Previous month" className="p-1.5 rounded-md border border-premium-700 text-slate-400 hover:text-cyan-300"><ChevronLeft className="w-4 h-4" /></button>
            <button onClick={() => { const t = parseIso(today); setCursor(new Date(t.getFullYear(), t.getMonth(), 1)); }} className="px-2.5 rounded-md border border-premium-700 text-xs text-slate-300 hover:text-cyan-300">Today</button>
            <button onClick={() => setCursor(new Date(y, m + 1, 1))} aria-label="Next month" className="p-1.5 rounded-md border border-premium-700 text-slate-400 hover:text-cyan-300"><ChevronRight className="w-4 h-4" /></button>
          </div>
          <span className="text-[11px] text-slate-500 inline-flex items-center gap-1" aria-live="polite">
            {status === 'saving' && <><Loader2 className="w-3 h-3 animate-spin" />Saving…</>}
            {status === 'saved' && <><Check className="w-3 h-3 text-emerald-400" />Saved</>}
            {status === 'error' && <><CloudOff className="w-3 h-3 text-amber-400" />Saved in this browser only</>}
          </span>
        </div>
        <button onClick={() => create(today)} className="inline-flex items-center gap-1 px-4 py-2 rounded-lg text-sm font-semibold text-white bg-gradient-to-r from-cyan-600 to-emerald-600 hover:from-cyan-500 hover:to-emerald-500">
          <Plus className="w-4 h-4" />New entry</button>
      </div>

      <div className="grid grid-cols-7 gap-px">
        {DAYS.map(d => <div key={d} className="text-center text-[11px] font-mono text-slate-500 uppercase tracking-widest py-1.5 bg-premium-900 border border-premium-800 rounded-t">{d}</div>)}
      </div>
      <div className="flex-1 grid grid-cols-7 grid-rows-6 gap-px bg-premium-800 border border-premium-800 rounded-b overflow-hidden">
        {cells.map(c => {
          const key = iso(c), inMonth = c.getMonth() === m, dayEvents = byDay[key] ?? [], hs = hol[key] ?? [];
          const chips = hs.length + dayEvents.length;
          return (
            <div key={key} onDoubleClick={() => create(key)} title="Double-click to add an entry"
              className={`group relative flex flex-col p-1 min-h-[5.5rem] overflow-hidden cursor-pointer ${inMonth ? 'bg-premium-950' : 'bg-premium-900/60'} hover:bg-premium-900`}>
              <div className="flex items-center justify-between shrink-0">
                <span className={`text-xs font-mono w-6 h-6 flex items-center justify-center rounded-full ${key === today ? 'bg-cyan-600 text-white font-bold' : inMonth ? 'text-slate-300' : 'text-slate-600'}`}>{c.getDate()}</span>
                <button onClick={e => { e.stopPropagation(); create(key); }} aria-label={`Add an entry on ${key}`}
                  className="opacity-0 group-hover:opacity-100 focus:opacity-100 text-slate-500 hover:text-cyan-300 px-1"><Plus className="w-3.5 h-3.5" /></button>
              </div>
              <div className="flex-1 min-h-0 space-y-0.5 mt-0.5 overflow-hidden">
                {hs.map(h => <div key={h.name} title={`${h.name}${h.note ? ` · ${h.note}` : ''}`}
                  className="px-1 py-0.5 rounded bg-emerald-950 border border-emerald-900 text-[10px] text-emerald-300 truncate">{h.name}</div>)}
                {dayEvents.slice(0, Math.max(0, 3 - hs.length)).map(e => (
                  <button key={e.id} onClick={ev => { ev.stopPropagation(); edit(e); }} title={`${e.time ? e.time + ' · ' : ''}${e.text} (click to edit)`}
                    className="w-full text-left px-1 py-0.5 rounded bg-cyan-950 border border-cyan-900 hover:border-cyan-600 text-[10px] text-cyan-300 truncate block">
                    {e.time && <span className="font-mono">{e.time} </span>}{e.text}</button>))}
                {chips > 3 && <button onClick={ev => { ev.stopPropagation(); const extra = dayEvents[Math.max(0, 3 - hs.length)]; if (extra) edit(extra); }}
                  className="text-[10px] font-mono text-slate-500 pl-1 hover:text-cyan-300">+{chips - 3} more</button>}
              </div>
            </div>
          );
        })}
      </div>
      <p className="text-[11px] text-slate-500 mt-2">Double-click a day to add an entry · click an entry to edit · <span className="text-emerald-300">teal</span> = Federal and Hawaiʻi state holidays.
        Entries are saved to your account and show on the dashboard's Calendar widget. Google and Outlook sync is coming later.</p>
      {draft && <EntryModal draft={draft} onSave={commit} onClose={() => setDraft(null)} onDelete={draft.id ? () => remove(draft.id!) : undefined} />}
    </div>
  );
}
