import { useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, Pin, Plus, Send, Trash2 } from 'lucide-react';
import { api } from '../api';
import { Markdown } from '../Markdown';
import { Empty, Pill } from '../ui';
import { holidayIndex, iso, parseIso, upcomingHolidays, type Holiday } from './holidays';
import { Gate, Note, useLoad } from './shared';
import type { CalEvent, WidgetProps } from './types';

const input = 'bg-premium-950 border border-premium-700 rounded-md px-2 py-1 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-600';
const geoLabel = (g: string, name?: string) => g === 'HI' ? 'the state' : name ?? g;

export function AskWidget({ geo, ctx }: WidgetProps) {
  const [q, setQ] = useState('');
  const n = geoLabel(geo, ctx.geos.find(x => x.geo_id === geo)?.name);
  const sugg = [`Give me a profile of ${n}`, `Which programs fit ${n}?`, `Compare ${n} with the state`];
  return <>
    <form onSubmit={e => { e.preventDefault(); if (q.trim()) ctx.onAsk(q.trim()); }} className="flex gap-2">
      <input value={q} onChange={e => setQ(e.target.value)} placeholder={`Ask about ${n}…`} aria-label="Question" className={`flex-1 min-w-0 ${input} text-sm py-1.5`} />
      <button className="px-2.5 rounded-md bg-cyan-700 hover:bg-cyan-600" aria-label="Ask"><Send className="w-4 h-4" /></button>
    </form>
    <div className="mt-2 flex flex-col gap-1.5">{sugg.map(s => (
      <button key={s} onClick={() => ctx.onAsk(s)} className="px-2 py-1 rounded-md border border-cyan-900 text-xs text-cyan-300 hover:bg-cyan-950 text-left">{s}</button>))}
    </div>
  </>;
}

export function ChatsWidget({ ctx }: WidgetProps) {
  const l = useLoad('chats', () => api.chats(), true);
  return <Gate l={l}>{cs => {
    const shown = [...cs].sort((a, b) => Number(b.pinned) - Number(a.pinned) || b.updated_at.localeCompare(a.updated_at)).slice(0, 10);
    if (!shown.length) return <Empty>No chats yet. Ask a question to start one.</Empty>;
    return <ul className="divide-y divide-premium-800">{shown.map(c => (
      <li key={c.id}><button onClick={() => ctx.onOpenChat(c.id)} className="w-full py-1.5 flex items-center gap-2 text-left text-sm text-slate-200 hover:text-cyan-300">
        {c.pinned && <Pin className="w-3 h-3 text-emerald-400 shrink-0" aria-label="pinned" />}
        <span className="truncate flex-1">{c.title || 'Untitled chat'}</span>
        <span className="text-[10px] text-slate-500 font-mono shrink-0">{c.updated_at.slice(5, 10)}</span></button></li>))}
    </ul>;
  }}</Gate>;
}

export function AnswerWidget({ w }: WidgetProps) {
  const { text, question, created } = w.config;
  if (!text) return <Empty>This pinned answer is empty.</Empty>;
  return <>
    {question && <div className="text-xs text-slate-400 mb-1">Q: <span className="text-slate-300">{question}</span></div>}
    <div className="text-slate-200 max-h-[60vh] overflow-y-auto"><Markdown text={text} /></div>
    <Note>Snapshot{created ? ` from ${created.slice(0, 10)}` : ''}; figures may have been updated since. Ask again for current, cited numbers.</Note>
  </>;
}

const tagPills = (h: Holiday) => h.tags.map(t => <Pill key={t} tone={t === 'State' ? 'emerald' : 'cyan'}>{t}</Pill>);
const day = (s: string) => parseIso(s).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });

export function HolidaysWidget(_: WidgetProps) {
  const hs = useMemo(() => upcomingHolidays(), []);
  if (!hs.length) return <Empty>No holidays in the next 90 days.</Empty>;
  return <ul className="space-y-1.5">{hs.map(h => (
    <li key={h.date + h.name} className="text-sm">
      <div className="flex items-center justify-between gap-2"><span className="text-slate-100">{h.name}</span><span className="flex gap-1 shrink-0">{tagPills(h)}</span></div>
      <div className="text-[11px] text-slate-500">{day(h.date)}{h.observed && <> · observed {day(h.observed)}</>}{h.note && <> · {h.note}</>}</div>
    </li>))}
  </ul>;
}

export function CalendarWidget({ w, setConfig }: WidgetProps) {
  const today = iso(new Date());
  const [month, setMonth] = useState(() => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1); });
  const [sel, setSel] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const events = w.config.events ?? [];
  const evBy = Object.fromEntries(events.map(e => [e.date, e]));
  const hol = useMemo(() => holidayIndex(month.getFullYear()), [month.getFullYear()]);
  const y = month.getFullYear(), m = month.getMonth(), lead = month.getDay(), days = new Date(y, m + 1, 0).getDate();
  const cells = [...Array(lead).fill(null), ...Array.from({ length: days }, (_, i) => iso(new Date(y, m, i + 1)))] as (string | null)[];
  const pick = (d: string) => { setSel(d); setDraft(evBy[d]?.text ?? ''); };
  const save = (text: string) => {
    if (!sel) return;
    const rest = events.filter(e => e.date !== sel);
    setConfig({ events: (text.trim() ? [...rest, { date: sel, text: text.trim().slice(0, 140) }] : rest).sort((a, b) => a.date.localeCompare(b.date)) });
    setSel(null);
  };
  const shift = (k: number) => { setMonth(new Date(y, m + k, 1)); setSel(null); };
  const monthEvents: CalEvent[] = events.filter(e => e.date.startsWith(`${y}-${String(m + 1).padStart(2, '0')}`));
  return <>
    <div className="flex items-center justify-between mb-1">
      <button onClick={() => shift(-1)} aria-label="Previous month" className="p-1 text-slate-400 hover:text-cyan-300"><ChevronLeft className="w-4 h-4" /></button>
      <span className="text-sm text-slate-200">{month.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}</span>
      <button onClick={() => shift(1)} aria-label="Next month" className="p-1 text-slate-400 hover:text-cyan-300"><ChevronRight className="w-4 h-4" /></button>
    </div>
    <div className="grid grid-cols-7 gap-0.5 text-center text-[10px] text-slate-500">{['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((d, i) => <div key={i}>{d}</div>)}</div>
    <div className="grid grid-cols-7 gap-0.5">{cells.map((d, i) => d === null ? <div key={i} /> : (
      <button key={d} onClick={() => pick(d)} title={[...(hol[d] ?? []).map(h => h.name), evBy[d]?.text].filter(Boolean).join(' · ') || 'Add an entry'}
        className={`relative h-7 rounded text-xs ${d === today ? 'bg-cyan-800 text-white' : 'text-slate-300 hover:bg-premium-800'} ${sel === d ? 'ring-1 ring-cyan-400' : ''} ${hol[d] ? 'font-semibold text-emerald-300' : ''}`}>
        {Number(d.slice(8))}
        <span className="absolute bottom-0.5 left-1/2 -translate-x-1/2 flex gap-0.5">
          {hol[d] && <span className="w-1 h-1 rounded-full bg-emerald-400" />}{evBy[d] && <span className="w-1 h-1 rounded-full bg-cyan-300" />}</span>
      </button>))}
    </div>
    {sel && <form onSubmit={e => { e.preventDefault(); save(draft); }} className="mt-2 space-y-1">
      <div className="text-[11px] text-slate-400">{day(sel)}{hol[sel] && <> · {hol[sel].map(h => h.name).join(', ')}</>}</div>
      <div className="flex gap-1">
        <input autoFocus value={draft} onChange={e => setDraft(e.target.value)} maxLength={140} placeholder="Short entry" aria-label="Calendar entry" className={`flex-1 min-w-0 ${input}`} />
        <button className="px-2 rounded border border-cyan-800 text-xs text-cyan-300">Save</button>
        {evBy[sel] && <button type="button" onClick={() => save('')} aria-label="Delete entry" className="px-1.5 text-slate-400 hover:text-red-400"><Trash2 className="w-3.5 h-3.5" /></button>}
        <button type="button" onClick={() => setSel(null)} className="px-1.5 text-xs text-slate-400">Cancel</button>
      </div>
    </form>}
    {monthEvents.length > 0 && <ul className="mt-2 text-xs space-y-0.5">{monthEvents.map(e => (
      <li key={e.date}><button onClick={() => pick(e.date)} className="text-left hover:text-cyan-300"><span className="font-mono text-slate-500 mr-2">{e.date.slice(8)}</span><span className="text-slate-300">{e.text}</span></button></li>))}</ul>}
    <Note><span className="text-emerald-400">●</span> holiday · <span className="text-cyan-300">●</span> your entry. Connecting Google or Outlook calendars is coming later.</Note>
  </>;
}

export function NotesWidget({ w, setConfig }: WidgetProps) {
  const [draft, setDraft] = useState('');
  const todos = w.config.todos ?? [];
  const add = () => { if (!draft.trim()) return; setConfig({ todos: [...todos, { id: Date.now().toString(36), text: draft.trim(), done: false }] }); setDraft(''); };
  return <div className="flex flex-col h-full gap-2">
    <textarea value={w.config.notes ?? ''} onChange={e => setConfig({ notes: e.target.value })} placeholder="Notes…" aria-label="Notes"
      className={`${input} text-sm flex-1 min-h-[4rem] resize-none`} />
    <ul className="space-y-0.5">{todos.map(t => (
      <li key={t.id} className="flex items-center gap-2 text-sm group">
        <input type="checkbox" checked={t.done} onChange={() => setConfig({ todos: todos.map(x => x.id === t.id ? { ...x, done: !x.done } : x) })} aria-label={`Done: ${t.text}`} className="accent-cyan-500" />
        <span className={`flex-1 ${t.done ? 'line-through text-slate-500' : 'text-slate-200'}`}>{t.text}</span>
        <button onClick={() => setConfig({ todos: todos.filter(x => x.id !== t.id) })} aria-label={`Delete ${t.text}`} className="text-slate-600 hover:text-red-400"><Trash2 className="w-3.5 h-3.5" /></button>
      </li>))}
    </ul>
    <form onSubmit={e => { e.preventDefault(); add(); }} className="flex gap-1">
      <input value={draft} onChange={e => setDraft(e.target.value)} placeholder="Add a to-do" aria-label="New to-do" className={`flex-1 min-w-0 ${input}`} />
      <button aria-label="Add to-do" className="px-2 rounded border border-premium-700 text-slate-300 hover:text-cyan-300"><Plus className="w-3.5 h-3.5" /></button>
    </form>
  </div>;
}

export function UsageWidget(_: WidgetProps) {
  const l = useLoad('usage', () => api.usage(), true);
  return <Gate l={l}>{u => {
    const days = u.questions_by_day.slice(-14), max = Math.max(1, ...days.map(d => d.questions));
    const pct = u.llm_budget.limit ? Math.min(100, (u.llm_budget.used_today / u.llm_budget.limit) * 100) : 0;
    const stat = (label: string, v: number | string) => <div><div className="text-[11px] text-slate-400">{label}</div><div className="font-mono text-lg text-cyan-300">{v}</div></div>;
    return <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(12rem, 1fr))' }}>
      <div className="grid grid-cols-2 gap-2 content-start">
        {stat('Questions today', u.questions_today)}{stat('Users', u.totals.users)}{stat('Chats', u.totals.chats)}{stat('Messages', u.totals.messages)}
      </div>
      <div>
        <div className="text-[11px] text-slate-400">LLM budget today</div>
        <div className="font-mono text-sm text-slate-200">{u.llm_budget.used_today.toLocaleString()} / {u.llm_budget.limit.toLocaleString()}</div>
        <div className="mt-1 h-2 rounded bg-premium-800"><div className={`h-2 rounded ${pct > 85 ? 'bg-amber-500' : 'bg-cyan-600'}`} style={{ width: `${pct}%` }} /></div>
        <div className="mt-3 text-[11px] text-slate-400">Questions by day</div>
        <div className="flex items-end gap-0.5 h-12">{days.map(d => (
          <div key={d.day} title={`${d.day}: ${d.questions}`} className="flex-1 bg-cyan-800/80 rounded-sm" style={{ height: `${(d.questions / max) * 100}%` }} />))}</div>
      </div>
      <div>
        <div className="text-[11px] text-slate-400 mb-1">Top users</div>
        {u.by_user.length ? <ul className="text-xs space-y-0.5">{u.by_user.slice(0, 5).map(r => (
          <li key={r.user} className="flex justify-between gap-2"><span className="truncate text-slate-300">{r.user}</span><span className="font-mono text-slate-400">{r.questions}</span></li>))}</ul>
          : <Empty>No questions yet.</Empty>}
      </div>
    </div>;
  }}</Gate>;
}
