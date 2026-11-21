import { useEffect, useState } from 'react';
import { api, type Usage, type User } from './api';
import { Card, Empty, Pill } from './ui';

const when = (ts: string | null) => ts ? new Date(ts).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : '—';

/** Accounts and usage. Admins see usage and the account list; only the owner changes roles or disables accounts. */
export function AdminTab({ me }: { me: User }) {
  const [users, setUsers] = useState<User[]>([]);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [err, setErr] = useState('');
  const load = () => {
    api.users().then(setUsers).catch(e => setErr(e.message));
    api.usage().then(setUsage).catch(e => setErr(e.message));
  };
  useEffect(load, []);
  const change = (u: User, patch: { role?: 'admin' | 'user'; disabled?: boolean }) =>
    api.updateUser(u.id, patch).then(load).catch(e => setErr(e.message));
  const owner = me.role === 'owner';
  const max = Math.max(1, ...(usage?.questions_by_day.map(d => d.questions) ?? []));

  return (
    <div className="grid gap-4 xl:grid-cols-3">
      {err && <p role="alert" className="xl:col-span-3 text-sm text-rose-300">{err}</p>}
      <Card title="Usage, last 7 days" className="xl:col-span-1">
        {!usage ? <Empty>Loading…</Empty> : <div className="space-y-4 text-sm">
          <div className="grid grid-cols-2 gap-3">
            {([['Questions today', usage.questions_today], ['AI calls today', `${usage.llm_budget.used_today} / ${usage.llm_budget.limit}`],
              ['Accounts', usage.totals.users], ['Saved chats', usage.totals.chats]] as const).map(([k, v]) => (
              <div key={k}><div className="text-xs text-slate-500">{k}</div><div className="text-xl font-mono text-cyan-300">{v}</div></div>))}
          </div>
          <div>
            <div className="text-xs text-slate-500 mb-1">Questions by day</div>
            {!usage.questions_by_day.length ? <Empty>No questions yet.</Empty> :
              <div className="flex items-end gap-1 h-24">{usage.questions_by_day.map(d => (
                <div key={d.day} className="flex-1 flex flex-col items-center gap-1" title={`${d.day}: ${d.questions}`}>
                  <div className="w-full bg-cyan-700 rounded-t" style={{ height: `${(d.questions / max) * 72}px` }} />
                  <span className="text-[10px] text-slate-500">{d.day.slice(5)}</span>
                </div>))}</div>}
          </div>
          <div>
            <div className="text-xs text-slate-500 mb-1">Answered by</div>
            <div className="flex gap-2">{Object.entries(usage.routes).map(([r, n]) => <Pill key={r}>{r}: {n}</Pill>)}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500 mb-1">Most active</div>
            <ul className="text-xs space-y-0.5">{usage.by_user.map(u => <li key={u.user} className="flex justify-between"><span className="truncate">{u.user}</span><span className="font-mono">{u.questions}</span></li>)}</ul>
          </div>
        </div>}
      </Card>

      <Card title={`Accounts (${users.length})`} className="xl:col-span-2">
        {!owner && <p className="text-xs text-slate-500 mb-2">Only the owner can change roles or disable accounts.</p>}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-xs text-slate-500 text-left"><tr>
              <th className="py-1 pr-3">Name</th><th className="pr-3">Email</th><th className="pr-3">Role</th><th className="pr-3">Last sign-in</th><th>Status</th></tr></thead>
            <tbody>{users.map(u => (
              <tr key={u.id} className="border-t border-premium-800">
                <td className="py-1.5 pr-3 text-slate-200">{u.name}</td>
                <td className="pr-3 text-slate-400">{u.email}</td>
                <td className="pr-3">{owner && u.role !== 'owner'
                  ? <select value={u.role} onChange={e => change(u, { role: e.target.value as 'admin' | 'user' })} aria-label={`Role for ${u.email}`}
                      className="bg-premium-950 border border-premium-700 rounded px-1.5 py-0.5 text-xs">
                      <option value="user">user</option><option value="admin">admin</option></select>
                  : <Pill tone={u.role === 'owner' ? 'amber' : u.role === 'admin' ? 'cyan' : 'slate'}>{u.role}</Pill>}</td>
                <td className="pr-3 text-xs text-slate-500 whitespace-nowrap">{when(u.last_login)}</td>
                <td>{owner && u.role !== 'owner'
                  ? <button onClick={() => change(u, { disabled: !u.disabled })}
                      className={`text-xs px-2 py-0.5 rounded border ${u.disabled ? 'border-rose-800 text-rose-300' : 'border-emerald-800 text-emerald-300'}`}>
                      {u.disabled ? 'Disabled · enable' : 'Active · disable'}</button>
                  : <span className="text-xs text-slate-500">{u.disabled ? 'Disabled' : 'Active'}</span>}</td>
              </tr>))}</tbody>
          </table>
        </div>
      </Card>

      <Card title="Recent activity" className="xl:col-span-3">
        {!usage?.recent.length ? <Empty>No activity yet.</Empty> :
          <ul className="text-xs divide-y divide-premium-800">{usage.recent.map((r, i) => (
            <li key={i} className="py-1 flex gap-3"><span className="text-slate-500 font-mono whitespace-nowrap">{when(r.ts)}</span>
              <span className="text-slate-300 truncate">{r.user}</span><span className="text-slate-400">{r.action}</span>
              {r.route && <span className="text-slate-500">{r.route}</span>}</li>))}</ul>}
        <p className="text-[11px] text-slate-500 mt-2">From the append-only audit log. Question text is not shown here.</p>
      </Card>
    </div>
  );
}
