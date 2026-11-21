import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Archive, ArchiveRestore, Bot, Check, Copy, Download, FileText, MessageSquarePlus, PanelLeft, PanelRight, Pencil,
  Pin, PinOff, Printer, Search, Send, ShieldAlert, X, Zap, LayoutDashboard,
} from 'lucide-react';
import { api, type Answer, type ChatMeta, type ChatMsg, type Doc, type Obs } from './api';
import { Markdown } from './Markdown';
import { pinToDashboard } from './pins';
import { suggestions } from './tabs';
import { Pill, usePersistentState } from './ui';

const wide = () => window.matchMedia('(min-width: 1024px)').matches;
const answerOf = (m: ChatMsg): Answer | null => (m.role === 'assistant' && typeof m.content !== 'string' ? m.content : null);
const iconBtn = 'p-1.5 rounded-md text-slate-400 hover:text-cyan-300 hover:bg-premium-800';

function download(name: string, text: string) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], { type: 'text/markdown;charset=utf-8' }));
  a.download = `${name.replace(/[^\w ʻ-]+/g, '').trim().replace(/\s+/g, '_') || 'document'}.md`;
  a.click();
}

function CopyButton({ text, label = 'Copy' }: { text: string; label?: string }) {
  const [done, setDone] = useState(false);
  return <button className={iconBtn} title={label} aria-label={label}
    onClick={() => navigator.clipboard.writeText(text).then(() => { setDone(true); setTimeout(() => setDone(false), 1500); })}>
    {done ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
  </button>;
}

/** Claude-desktop-style workspace: saved chats on the left, the conversation, documents on the right. */
export function ChatTab({ geo, pending, clearPending, openChat, clearOpenChat }: {
  geo: string; pending: string | null; clearPending: () => void; openChat: string | null; clearOpenChat: () => void;
}) {
  const [chatId, setChatId] = usePersistentState<string | null>('kyd_chat', null);
  const [chats, setChats] = useState<ChatMeta[]>([]);
  const [archived, setArchived] = useState(false);
  const [q, setQ] = useState('');
  const [msgs, setMsgs] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [left, setLeft] = useState(wide);
  const [doc, setDoc] = useState<Doc | null>(null);
  const [renaming, setRenaming] = useState<string | null>(null);
  const end = useRef<HTMLDivElement>(null);

  const refresh = () => api.chats(archived, q).then(setChats).catch(() => setChats([]));
  useEffect(() => { const t = setTimeout(refresh, q ? 250 : 0); return () => clearTimeout(t); }, [archived, q]);
  useEffect(() => {
    if (!chatId) return;
    api.chat(chatId).then(c => setMsgs(c.messages)).catch(() => { setChatId(null); setMsgs([]); });
  }, [chatId]);
  useEffect(() => { if (openChat) { setChatId(openChat); setDoc(null); clearOpenChat(); } }, [openChat]);
  useEffect(() => { if (pending) { newChat(); send(pending, null); clearPending(); } }, [pending]);
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }); }, [msgs, busy]);

  const obs = useMemo(() => Object.fromEntries(msgs.flatMap(m => answerOf(m)?.observations ?? []).map(o => [o.obs_id, o])) as Record<string, Obs>, [msgs]);
  const docs = useMemo(() => msgs.map(answerOf).filter((a): a is Answer => !!a?.document).map(a => a.document as Doc), [msgs]);
  const current = chats.find(c => c.id === chatId);

  const newChat = () => { setChatId(null); setMsgs([]); setDoc(null); setErr(''); if (!wide()) setLeft(false); };
  const pick = (id: string) => { setChatId(id); setDoc(null); setErr(''); if (!wide()) setLeft(false); };
  const update = async (id: string, patch: { title?: string; pinned?: boolean; archived?: boolean }) => {
    await api.updateChat(id, patch).catch(e => setErr(e.message));
    if (patch.archived !== undefined && id === chatId) newChat();
    refresh();
  };

  const send = async (text: string, cid: string | null = chatId) => {
    const question = text.trim();
    if (!question || busy) return;
    setErr(''); setInput(''); setBusy(true);
    setMsgs(m => [...m, { id: -Date.now(), role: 'user', content: question, created_at: new Date().toISOString() }]);
    try {
      const a = await api.ask(question, geo, cid ?? 'new');
      setMsgs(m => [...m, { id: Date.now(), role: 'assistant', content: a, created_at: new Date().toISOString() }]);
      if (a.chat_id && a.chat_id !== cid) setChatId(a.chat_id);
      if (a.document) setDoc(a.document);
      refresh();
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  };

  const print = () => {
    document.body.classList.add('print-doc');
    window.print();
    setTimeout(() => document.body.classList.remove('print-doc'), 500);
  };

  const sidebar = (
    <aside className={`chat-side no-print flex flex-col kyd-card rounded-xl p-3 gap-2 w-72 shrink-0
      max-lg:absolute max-lg:inset-y-0 max-lg:left-0 max-lg:z-30 max-lg:shadow-2xl`}>
      <div className="flex items-center gap-2">
        <button onClick={newChat} className="flex-1 inline-flex items-center justify-center gap-2 py-1.5 rounded-md bg-cyan-800 hover:bg-cyan-700 text-sm">
          <MessageSquarePlus className="w-4 h-4" />New chat</button>
        <button className={iconBtn} onClick={() => setLeft(false)} title="Hide chat history" aria-label="Hide chat history"><PanelLeft className="w-4 h-4" /></button>
      </div>
      <label className="relative block">
        <Search className="w-3.5 h-3.5 absolute left-2 top-2.5 text-slate-500" />
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search chats" aria-label="Search chats"
          className="w-full bg-premium-950 border border-premium-700 rounded-md pl-7 pr-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-cyan-600" />
      </label>
      <div className="flex gap-1 text-xs">
        {[false, true].map(a => (
          <button key={String(a)} onClick={() => setArchived(a)} aria-pressed={archived === a}
            className={`px-2 py-1 rounded ${archived === a ? 'bg-premium-800 text-cyan-300' : 'text-slate-500 hover:text-slate-300'}`}>
            {a ? 'Archived' : 'Chats'}</button>))}
      </div>
      <ul className="flex-1 overflow-y-auto -mx-1 space-y-0.5 min-h-0">
        {!chats.length && <li className="px-2 py-3 text-xs text-slate-500">{q ? 'No chats match.' : archived ? 'No archived chats.' : 'No chats yet. Ask a question to start one.'}</li>}
        {chats.map(c => (
          <li key={c.id} className={`group rounded-md px-2 py-1.5 flex items-center gap-1 ${c.id === chatId ? 'bg-premium-800' : 'hover:bg-premium-800/60'}`}>
            {renaming === c.id ? (
              <form className="flex-1" onSubmit={e => { e.preventDefault(); const t = (e.currentTarget.elements.namedItem('t') as HTMLInputElement).value.trim(); if (t) update(c.id, { title: t }); setRenaming(null); }}>
                <input name="t" defaultValue={c.title} autoFocus maxLength={120} onBlur={() => setRenaming(null)} aria-label="Chat title"
                  className="w-full bg-premium-950 border border-cyan-700 rounded px-1.5 py-0.5 text-xs text-slate-100" />
              </form>
            ) : (
              <button onClick={() => pick(c.id)} className="flex-1 min-w-0 text-left text-sm text-slate-300 truncate" title={c.title}>
                {c.pinned && <Pin className="w-3 h-3 inline mr-1 text-amber-300" />}{c.title}</button>
            )}
            <span className="hidden group-hover:flex group-focus-within:flex items-center">
              <button className="p-1 text-slate-500 hover:text-cyan-300" title="Rename" aria-label="Rename" onClick={() => setRenaming(c.id)}><Pencil className="w-3.5 h-3.5" /></button>
              {!c.archived && <button className="p-1 text-slate-500 hover:text-amber-300" title={c.pinned ? 'Unpin' : 'Pin'} aria-label={c.pinned ? 'Unpin' : 'Pin'}
                onClick={() => update(c.id, { pinned: !c.pinned })}>{c.pinned ? <PinOff className="w-3.5 h-3.5" /> : <Pin className="w-3.5 h-3.5" />}</button>}
              <button className="p-1 text-slate-500 hover:text-cyan-300" title={c.archived ? 'Unarchive' : 'Archive'} aria-label={c.archived ? 'Unarchive' : 'Archive'}
                onClick={() => update(c.id, { archived: !c.archived })}>{c.archived ? <ArchiveRestore className="w-3.5 h-3.5" /> : <Archive className="w-3.5 h-3.5" />}</button>
            </span>
          </li>))}
      </ul>
    </aside>
  );

  const docPanel = doc && (
    <aside className="chat-doc flex flex-col kyd-card rounded-xl w-[min(36rem,45%)] shrink-0 max-lg:absolute max-lg:inset-0 max-lg:w-auto max-lg:z-30">
      <div className="no-print flex items-center gap-1 px-3 py-2 border-b border-premium-800">
        <FileText className="w-4 h-4 text-cyan-400 shrink-0" />
        {docs.length > 1 ? (
          <select value={docs.findIndex(d => d.title === doc.title && d.body === doc.body)} onChange={e => setDoc(docs[+e.target.value])}
            aria-label="Documents in this chat" className="flex-1 min-w-0 bg-transparent text-sm text-slate-200 truncate">
            {docs.map((d, i) => <option key={i} value={i} className="bg-premium-900">{d.title}</option>)}
            {!docs.some(d => d.title === doc.title && d.body === doc.body) && <option value={-1} className="bg-premium-900">{doc.title}</option>}
          </select>
        ) : <span className="flex-1 min-w-0 text-sm text-slate-200 truncate" title={doc.title}>{doc.title}</span>}
        <CopyButton text={`# ${doc.title}\n\n${doc.body}`} label="Copy document" />
        <button className={iconBtn} onClick={print} title="Print or save as PDF" aria-label="Print or save as PDF"><Printer className="w-4 h-4" /></button>
        <button className={iconBtn} onClick={() => download(doc.title, `# ${doc.title}\n\n${doc.body}\n`)} title="Download Markdown" aria-label="Download Markdown"><Download className="w-4 h-4" /></button>
        <button className={iconBtn} onClick={() => setDoc(null)} title="Close document" aria-label="Close document"><X className="w-4 h-4" /></button>
      </div>
      <article className="flex-1 overflow-y-auto px-5 py-4">
        <h1 className="text-xl font-semibold text-slate-100 mb-2">{doc.title}</h1>
        <Markdown text={doc.body} obs={obs} />
        <p className="print-only text-[10px] mt-6">Know Your District by DataWorkflows.ai · nonpartisan, population-level data · printed {new Date().toLocaleDateString()}</p>
      </article>
    </aside>
  );

  return (
    <div className="relative h-full flex gap-3 min-h-0">
      {left && sidebar}
      {left && <div className="lg:hidden absolute inset-0 z-20 bg-black/40" onClick={() => setLeft(false)} aria-hidden />}
      <section className="chat-main flex-1 min-w-0 flex flex-col kyd-card rounded-xl">
        <div className="no-print flex items-center gap-1 px-3 py-2 border-b border-premium-800">
          {!left && <button className={iconBtn} onClick={() => setLeft(true)} title="Show chat history" aria-label="Show chat history"><PanelLeft className="w-4 h-4" /></button>}
          <h2 className="flex-1 min-w-0 text-sm font-medium text-slate-200 truncate">{current?.title ?? (chatId ? 'Chat' : 'New chat')}</h2>
          <span className="text-xs text-slate-500 hidden sm:inline">Context: {geo}</span>
          {!doc && docs.length > 0 && <button className={iconBtn} onClick={() => setDoc(docs[docs.length - 1])} title="Show documents" aria-label="Show documents"><PanelRight className="w-4 h-4" /></button>}
        </div>
        <div className="flex-1 overflow-y-auto px-3 sm:px-6 py-4 space-y-4 min-h-0" aria-live="polite">
          {!msgs.length && !busy && (
            <div className="max-w-2xl mx-auto pt-6 space-y-3">
              <p className="text-sm text-slate-400">Ask in plain English. Every number in an answer comes from a tool and is cited. Ask for a memo, brief, letter or talking points and it opens as a document on the right.</p>
              <div className="flex flex-wrap gap-2">
                {[...suggestions(geo).slice(0, 5), `Write a one-page brief on ${geo === 'HI' ? 'the state' : 'this district'} for a constituent meeting`].map(s => (
                  <button key={s} onClick={() => send(s)} className="px-2.5 py-1.5 rounded-md border border-cyan-900 text-xs text-cyan-300 hover:bg-cyan-950 text-left">{s}</button>))}
              </div>
            </div>
          )}
          {msgs.map((m, i) => {
            const a = answerOf(m);
            if (!a) return (
              <div key={m.id} className="flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-br-md bg-premium-700 px-3 py-2 text-sm whitespace-pre-wrap">{m.content as string}</div>
              </div>);
            const question = typeof msgs[i - 1]?.content === 'string' ? msgs[i - 1].content as string : '';
            const asDoc: Doc = a.document ?? { title: question.slice(0, 80) || 'Answer', body: a.text };
            return (
              <div key={m.id} className="max-w-3xl">
                <div className="text-slate-200"><Markdown text={a.text} obs={obs} /></div>
                {a.document && (
                  <button onClick={() => setDoc(a.document!)} className="mt-2 w-full max-w-sm text-left kyd-card rounded-lg px-3 py-2 flex items-center gap-2">
                    <FileText className="w-5 h-5 text-cyan-400 shrink-0" />
                    <span className="min-w-0"><span className="block text-sm text-slate-100 truncate">{a.document.title}</span>
                      <span className="block text-xs text-slate-500">Document · click to open</span></span>
                  </button>)}
                <div className="no-print mt-1 flex flex-wrap gap-1 items-center text-xs text-slate-500">
                  <CopyButton text={a.text} label="Copy answer" />
                  <button className={iconBtn} onClick={() => setDoc(asDoc)} title="Open as document" aria-label="Open as document"><FileText className="w-4 h-4" /></button>
                  <button className={iconBtn} title="Pin to dashboard" aria-label="Pin to dashboard"
                    onClick={() => pinToDashboard({ type: 'answer', title: question.slice(0, 60) || 'Pinned answer', config: { text: a.text, question, created: m.created_at } })}>
                    <LayoutDashboard className="w-4 h-4" /></button>
                  {a.route === 'S1' && <span className="inline-flex items-center gap-1 ml-1"><Zap className="w-3 h-3 text-emerald-400" />System 1</span>}
                  {a.route === 'S2' && <span className="inline-flex items-center gap-1 ml-1"><Bot className="w-3 h-3 text-cyan-400" />System 2</span>}
                  {a.route === 'REFUSED' && <span className="inline-flex items-center gap-1 ml-1"><ShieldAlert className="w-3 h-3 text-amber-400" />Guardrail</span>}
                  {a.escalation_reasons.map(r => <Pill key={r}>{r}</Pill>)}
                </div>
              </div>);
          })}
          {busy && <div className="text-xs text-slate-500 animate-pulse">Thinking…</div>}
          {err && <p role="alert" className="text-xs text-rose-300">{err}</p>}
          <div ref={end} />
        </div>
        <form onSubmit={e => { e.preventDefault(); send(input); }} className="no-print p-3 border-t border-premium-800">
          <div className="flex items-end gap-2 bg-premium-950 border border-premium-700 rounded-xl px-3 py-2 focus-within:ring-2 focus-within:ring-cyan-700">
            <label htmlFor="ask" className="sr-only">Question</label>
            <textarea id="ask" value={input} onChange={e => setInput(e.target.value)} rows={1} maxLength={2000}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(input); } }}
              placeholder="Ask about a district, or ask for a memo…" className="flex-1 resize-none bg-transparent text-sm text-slate-200 focus:outline-none max-h-40" />
            <button disabled={busy || !input.trim()} className="p-2 rounded-lg bg-cyan-700 hover:bg-cyan-600 disabled:opacity-40" aria-label="Send"><Send className="w-4 h-4" /></button>
          </div>
          <p className="text-[11px] text-slate-500 mt-1 px-1">Enter to send, Shift+Enter for a new line. Answers are population-level and nonpartisan.</p>
        </form>
      </section>
      {docPanel}
    </div>
  );
}
