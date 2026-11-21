import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, Eye, EyeOff, KeyRound, LogIn, Mail, Sparkles, UserPlus } from 'lucide-react';
import { api, setToken, type Session, type User } from './api';
import dwaiLogo from './brand/dataworkflows-logo.png';
import { ThemePicker } from './theme';

const input = 'w-full bg-premium-950 border border-premium-700 rounded-md px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-600';

function PasswordInput({ id, value, onChange, autoComplete, minLength }: {
  id?: string; value: string; onChange: (v: string) => void; autoComplete: string; minLength?: number;
}) {
  const [shown, setShown] = useState(false);
  return (
    <div className="relative">
      <input id={id} className={`${input} pr-10`} type={shown ? 'text' : 'password'} value={value} onChange={e => onChange(e.target.value)}
        required minLength={minLength} autoComplete={autoComplete} />
      <button type="button" onClick={() => setShown(s => !s)} aria-label={shown ? 'Hide password' : 'Show password'} aria-pressed={shown}
        className="absolute inset-y-0 right-0 px-3 text-slate-400 hover:text-slate-200 focus:outline-none focus-visible:text-cyan-400">
        {shown ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
      </button>
    </div>
  );
}

type GoogleId = {
  initialize: (o: { client_id: string; callback: (r: { credential: string }) => void }) => void;
  renderButton: (el: HTMLElement, o: Record<string, unknown>) => void;
};
declare global { interface Window { google?: { accounts: { id: GoogleId } } } }

function loadGoogle(): Promise<GoogleId> {
  if (window.google) return Promise.resolve(window.google.accounts.id);
  return new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = 'https://accounts.google.com/gsi/client';
    s.async = true;
    s.onload = () => window.google ? resolve(window.google.accounts.id) : reject(new Error('Google sign-in did not load'));
    s.onerror = () => reject(new Error('Google sign-in did not load'));
    document.head.appendChild(s);
  });
}

function GoogleButton({ clientId, onCredential }: { clientId: string; onCredential: (credential: string) => void }) {
  const box = useRef<HTMLDivElement>(null);
  const cb = useRef(onCredential);
  cb.current = onCredential;
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let live = true;
    loadGoogle().then(g => {
      if (!live || !box.current) return;
      g.initialize({ client_id: clientId, callback: r => cb.current(r.credential) });
      g.renderButton(box.current, { theme: 'filled_black', size: 'large', text: 'continue_with', shape: 'rectangular', width: box.current.offsetWidth || 320 });
    }).catch(() => live && setFailed(true));
    return () => { live = false; };
  }, [clientId]);
  if (failed) return <p className="text-[11px] text-slate-500 text-center">Google sign-in is unavailable right now.</p>;
  return <div ref={box} className="w-full flex justify-center min-h-[40px]" />;
}

/** Sign in or register (email or Google), or reset a forgotten password with an emailed code. The owner can
 *  change roles or disable accounts later. */
export function Login({ onSignedIn }: { onSignedIn: (u: User) => void }) {
  const [mode, setMode] = useState<'login' | 'register' | 'forgot'>('login');
  const [codeSent, setCodeSent] = useState(false);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [err, setErr] = useState('');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [opts, setOpts] = useState<{ google_client_id: string | null; email_reset: boolean } | null>(null);
  useEffect(() => { api.authOptions().then(setOpts).catch(() => setOpts(null)); }, []);

  const go = (m: typeof mode) => { setMode(m); setErr(''); setNote(''); setCodeSent(false); setCode(''); setPassword(''); };
  const run = async (call: () => Promise<Session>) => {
    setErr(''); setBusy(true);
    try {
      const s = await call();
      setToken(s.token);
      onSignedIn(s.user);
    } catch (x) { setErr(x instanceof Error ? x.message : String(x)); }
    finally { setBusy(false); }
  };
  const sendCode = async () => {
    setErr(''); setNote(''); setBusy(true);
    try {
      setNote((await api.forgot(email)).detail);
      setCodeSent(true);
    } catch (x) { setErr(x instanceof Error ? x.message : String(x)); }
    finally { setBusy(false); }
  };
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (mode === 'forgot') {
      if (codeSent) run(() => api.reset(email, code, password));
      else sendCode();
      return;
    }
    run(() => mode === 'login' ? api.login(email, password) : api.register(email, name, password));
  };

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

        {mode === 'forgot' ? (
          <form onSubmit={submit} className="space-y-3">
            <button type="button" onClick={() => go('login')} className="text-xs text-slate-400 hover:text-slate-200 inline-flex items-center gap-1">
              <ArrowLeft className="w-3.5 h-3.5" />Back to sign in</button>
            <div>
              <h2 className="text-sm font-semibold text-slate-200">Reset your password</h2>
              <p className="text-[11px] text-slate-500">{codeSent ? 'Enter the 6-digit code from the email and choose a new password.' : 'We will email you a 6-digit code.'}</p>
            </div>
            {opts && !opts.email_reset ? (
              <p className="text-xs text-amber-300">Password reset by email isn't set up yet. Contact DataWorkflows.ai to reset your password.</p>
            ) : <>
              <label className="block text-xs text-slate-400 space-y-1"><span>Email</span>
                <input className={input} type="email" value={email} onChange={e => setEmail(e.target.value)} required autoComplete="email" disabled={codeSent} /></label>
              {codeSent && <>
                <label className="block text-xs text-slate-400 space-y-1"><span>6-digit code</span>
                  <input className={`${input} tracking-[0.4em] font-mono`} value={code} onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    required inputMode="numeric" pattern="\d{6}" autoComplete="one-time-code" placeholder="000000" /></label>
                <label className="block text-xs text-slate-400 space-y-1"><span>New password (8 characters or more)</span>
                  <PasswordInput value={password} onChange={setPassword} autoComplete="new-password" minLength={8} /></label>
              </>}
              {note && <p className="text-xs text-emerald-300">{note}</p>}
              {err && <p role="alert" className="text-xs text-rose-300">{err}</p>}
              <button disabled={busy} className="w-full py-2 rounded-md bg-cyan-700 hover:bg-cyan-600 disabled:opacity-50 text-sm font-medium inline-flex items-center justify-center gap-2">
                {codeSent ? <><KeyRound className="w-4 h-4" />Set new password and sign in</> : <><Mail className="w-4 h-4" />Email me a code</>}
              </button>
              {codeSent && <button type="button" disabled={busy} onClick={sendCode} className="w-full text-[11px] text-slate-400 hover:text-slate-200">
                Didn't get it? Send a new code (check spam first)</button>}
            </>}
          </form>
        ) : <>
          <div className="space-y-1.5">
            <button onClick={() => run(api.guest)} disabled={busy}
              className="w-full py-2.5 rounded-md bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 text-sm font-semibold inline-flex items-center justify-center gap-2">
              <Sparkles className="w-4 h-4" />Try the demo</button>
            <p className="text-[11px] text-slate-500 text-center">No sign-up. You get a private guest workspace with a sample chat and brief. Signing out ends it.</p>
          </div>
          <div className="flex items-center gap-2 text-[11px] text-slate-500"><span className="flex-1 border-t border-premium-800" />or use an account<span className="flex-1 border-t border-premium-800" /></div>
          {opts?.google_client_id && <GoogleButton clientId={opts.google_client_id} onCredential={cred => run(() => api.google(cred))} />}
          <div role="tablist" className="grid grid-cols-2 gap-1 bg-premium-950 p-1 rounded-lg border border-premium-800">
            {(['login', 'register'] as const).map(m => (
              <button key={m} role="tab" aria-selected={mode === m} onClick={() => go(m)}
                className={`py-1.5 rounded-md text-sm ${mode === m ? 'bg-premium-800 text-cyan-400 border border-premium-700' : 'text-slate-400 hover:text-slate-200'}`}>
                {m === 'login' ? 'Sign in' : 'Create account'}
              </button>))}
          </div>
          <form onSubmit={submit} className="space-y-3">
            {mode === 'register' && (
              <label className="block text-xs text-slate-400 space-y-1"><span>Name</span>
                <input className={input} value={name} onChange={e => setName(e.target.value)} required maxLength={80} autoComplete="name" /></label>)}
            <label className="block text-xs text-slate-400 space-y-1"><span>Email</span>
              <input className={input} type="email" value={email} onChange={e => setEmail(e.target.value)} required autoComplete="email" />
              {mode === 'login' && <span className="block text-[11px] text-slate-500">Your username is the email you registered with. Forgot which one? Contact DataWorkflows.ai.</span>}
            </label>
            <div className="text-xs text-slate-400 space-y-1">
              <div className="flex justify-between">
                <label htmlFor="kyd-password">Password{mode === 'register' && ' (8 characters or more)'}</label>
                {mode === 'login' && <button type="button" onClick={() => go('forgot')} className="text-cyan-400 hover:text-cyan-300">Forgot password?</button>}
              </div>
              <PasswordInput id="kyd-password" value={password} onChange={setPassword} minLength={mode === 'register' ? 8 : undefined}
                autoComplete={mode === 'register' ? 'new-password' : 'current-password'} />
            </div>
            {err && <p role="alert" className="text-xs text-rose-300">{err}</p>}
            <button disabled={busy} className="w-full py-2 rounded-md bg-cyan-700 hover:bg-cyan-600 disabled:opacity-50 text-sm font-medium inline-flex items-center justify-center gap-2">
              {mode === 'login' ? <><LogIn className="w-4 h-4" />Sign in</> : <><UserPlus className="w-4 h-4" />Create account</>}
            </button>
          </form>
        </>}
        <p className="text-[11px] text-slate-500 text-center">Demo accounts. Nonpartisan, population-level data only. Your questions are logged for audit, with personal details removed.</p>
        <div className="flex justify-center"><ThemePicker /></div>
      </div>
    </div>
  );
}
