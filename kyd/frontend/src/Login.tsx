import { useState } from 'react';
import { LogIn, Sparkles, UserPlus } from 'lucide-react';
import { api, setToken, type Session, type User } from './api';
import dwaiLogo from './brand/dataworkflows-logo.png';

/** Sign in or register. Registration is instant; the owner can change roles or disable accounts later. */
export function Login({ onSignedIn }: { onSignedIn: (u: User) => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const run = async (go: () => Promise<Session>) => {
    setErr(''); setBusy(true);
    try {
      const s = await go();
      setToken(s.token);
      onSignedIn(s.user);
    } catch (x) { setErr(x instanceof Error ? x.message : String(x)); }
    finally { setBusy(false); }
  };
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    run(() => mode === 'login' ? api.login(email, password) : api.register(email, name, password));
  };
  const input = 'w-full bg-premium-950 border border-premium-700 rounded-md px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-600';
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-sm kyd-card rounded-xl p-6 space-y-5">
        <div className="text-center space-y-1">
          <h1 className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-emerald-400">KNOW YOUR DISTRICT</h1>
          <p className="text-xs text-slate-400">Hawaiʻi legislative district profiles</p>
          <div className="flex items-center justify-center gap-2 pt-1">
            <span className="text-xs text-slate-500">by</span>
            <img src={dwaiLogo} alt="DataWorkflows.ai" width={140} height={28} className="h-7 w-auto" />
          </div>
        </div>
        <div className="space-y-1.5">
          <button onClick={() => run(api.guest)} disabled={busy}
            className="w-full py-2.5 rounded-md bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 text-sm font-semibold inline-flex items-center justify-center gap-2">
            <Sparkles className="w-4 h-4" />Try the demo</button>
          <p className="text-[11px] text-slate-500 text-center">No sign-up. You get a private guest workspace with a sample chat and brief. Signing out ends it.</p>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-slate-500"><span className="flex-1 border-t border-premium-800" />or use an account<span className="flex-1 border-t border-premium-800" /></div>
        <div role="tablist" className="grid grid-cols-2 gap-1 bg-premium-950 p-1 rounded-lg border border-premium-800">
          {(['login', 'register'] as const).map(m => (
            <button key={m} role="tab" aria-selected={mode === m} onClick={() => { setMode(m); setErr(''); }}
              className={`py-1.5 rounded-md text-sm ${mode === m ? 'bg-premium-800 text-cyan-400 border border-premium-700' : 'text-slate-400 hover:text-slate-200'}`}>
              {m === 'login' ? 'Sign in' : 'Create account'}
            </button>))}
        </div>
        <form onSubmit={submit} className="space-y-3">
          {mode === 'register' && (
            <label className="block text-xs text-slate-400 space-y-1"><span>Name</span>
              <input className={input} value={name} onChange={e => setName(e.target.value)} required maxLength={80} autoComplete="name" /></label>)}
          <label className="block text-xs text-slate-400 space-y-1"><span>Email</span>
            <input className={input} type="email" value={email} onChange={e => setEmail(e.target.value)} required autoComplete="email" /></label>
          <label className="block text-xs text-slate-400 space-y-1"><span>Password{mode === 'register' && ' (8 characters or more)'}</span>
            <input className={input} type="password" value={password} onChange={e => setPassword(e.target.value)} required
              minLength={mode === 'register' ? 8 : undefined} autoComplete={mode === 'register' ? 'new-password' : 'current-password'} /></label>
          {err && <p role="alert" className="text-xs text-rose-300">{err}</p>}
          <button disabled={busy} className="w-full py-2 rounded-md bg-cyan-700 hover:bg-cyan-600 disabled:opacity-50 text-sm font-medium inline-flex items-center justify-center gap-2">
            {mode === 'login' ? <><LogIn className="w-4 h-4" />Sign in</> : <><UserPlus className="w-4 h-4" />Create account</>}
          </button>
        </form>
        <p className="text-[11px] text-slate-500 text-center">Demo accounts. Nonpartisan, population-level data only. Your questions are logged for audit, with personal details removed.</p>
      </div>
    </div>
  );
}
