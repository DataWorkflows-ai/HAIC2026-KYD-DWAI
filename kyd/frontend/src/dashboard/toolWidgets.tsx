import { useMemo, useState } from 'react';
import { Pin, Plus, Send, Trash2 } from 'lucide-react';
import { api } from '../api';
import { Markdown } from '../Markdown';
import { Empty, Pill } from '../ui';
import { hstToday, upcoming } from './calendar';
import { parseIso, upcomingHolidays, type Holiday } from './holidays';
import { Gate, Note, useLoad } from './shared';
import type { WidgetProps } from './types';

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

/** Styled like a desk-calendar icon: month band, weekday, big date. Double-click (or the link) opens the Calendar tab. */
export function CalendarWidget({ ctx }: WidgetProps) {
  const today = hstToday(), now = parseIso(today);
  const items = upcoming(ctx.calendar, 30);
  const entries = items.filter(i => i.kind === 'entry').length, holidays = items.length - entries;
  const open = () => ctx.onOpen('calendar');
  return <div className="flex flex-col h-full select-none cursor-pointer" onDoubleClick={open} title="Double-click to open the Calendar tab">
    <div className="shrink-0 rounded-lg overflow-hidden border border-premium-700 shadow-lg">
      <div className="bg-gradient-to-r from-cyan-600 to-emerald-600 text-white text-center font-bold uppercase tracking-widest py-1.5 text-sm">
        {now.toLocaleDateString('en-US', { month: 'long' })}</div>
      <div className="bg-premium-950 flex flex-col items-center justify-center py-3 gap-1">
        <div className="text-slate-400 text-sm font-semibold tracking-wide">{now.toLocaleDateString('en-US', { weekday: 'long' })}</div>
        <div className="text-cyan-400 font-bold" style={{ fontSize: '3.5rem', lineHeight: 1 }}>{now.getDate()}</div>
        <div className="text-slate-500 text-xs font-mono">{now.getFullYear()} · HST</div>
      </div>
      <div className="bg-premium-900 border-t border-premium-800 px-3 py-1 flex items-center justify-between text-[11px] font-mono text-slate-500">
        <span>{entries} {entries === 1 ? 'entry' : 'entries'} · {holidays} {holidays === 1 ? 'holiday' : 'holidays'}</span><span>next 30 days</span>
      </div>
    </div>
    <div className="flex-1 min-h-0 overflow-y-auto mt-2">
      <div className="px-1 pb-0.5 text-[10px] font-mono text-slate-500 uppercase tracking-widest border-b border-premium-800">Coming up</div>
      {!items.length && <p className="text-xs text-slate-500 px-1 py-2">Nothing in the next 30 days. Double-click to add an entry.</p>}
      {items.slice(0, 12).map((it, i) => (
        <div key={i} className={`px-2 py-1 border-b border-premium-800 border-l-2 ${it.date === today ? 'border-l-cyan-500' : it.kind === 'holiday' ? 'border-l-emerald-600' : 'border-l-premium-700'}`}>
          <p className={`text-xs truncate ${it.kind === 'holiday' ? 'text-emerald-300' : 'text-slate-200'}`} title={it.text}>{it.text}</p>
          <p className={`text-[11px] font-mono ${it.date === today ? 'text-cyan-400' : 'text-slate-500'}`}>
            {it.date === today ? 'Today' : day(it.date)}{it.time ? ` · ${it.time}` : ''}{it.kind === 'holiday' ? ' · holiday' : ''}</p>
        </div>))}
    </div>
    <button onClick={open} className="shrink-0 mt-1 self-end text-xs text-cyan-400 hover:text-cyan-300 font-mono">Open calendar →</button>
  </div>;
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
