import React, { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ArrowRight, Check, Loader2, ShieldCheck, Sparkles, X } from 'lucide-react';
import { authApi } from '../../api/client';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAuthenticated: () => void;
}

type AuthMode = 'login' | 'register';
type AuthStep = 'identifier' | 'otp';

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onAuthenticated }) => {
  const [mode, setMode] = useState<AuthMode>('login');
  const [step, setStep] = useState<AuthStep>('identifier');
  const [identifier, setIdentifier] = useState('');
  const [fullName, setFullName] = useState('');
  const [username, setUsername] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) setError(null);
  }, [isOpen]);

  const switchMode = (nextMode: AuthMode) => {
    setMode(nextMode);
    setStep('identifier');
    setOtpCode('');
    setError(null);
  };

  const handleSendOtp = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!identifier.trim()) return;
    if (mode === 'register' && (!fullName.trim() || username.trim().length < 3)) {
      setError('Name and a username with at least 3 characters are required.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await authApi.sendOtp(identifier.trim());
      setStep('otp');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to send OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!otpCode.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await authApi.verifyOtp(identifier.trim(), otpCode.trim(), mode === 'register' ? { fullName, username } : undefined);
      setStep('identifier');
      setOtpCode('');
      onAuthenticated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to verify OTP');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[90] flex items-end justify-center bg-[#05050a]/80 p-0 backdrop-blur-xl sm:items-center sm:p-4">
          <motion.button type="button" aria-label="Close authentication" className="absolute inset-0 cursor-default" onClick={onClose} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
          <motion.div initial={{ y: '100%', opacity: 0.6 }} animate={{ y: 0, opacity: 1 }} exit={{ y: '100%', opacity: 0.6 }} transition={{ type: 'spring', stiffness: 280, damping: 28 }} role="dialog" aria-modal="true" aria-labelledby="auth-title" className="relative z-10 w-full max-w-md overflow-hidden rounded-t-[2rem] border border-white/10 bg-[#11121b] shadow-[0_24px_100px_rgba(0,0,0,.55)] sm:rounded-[2rem]">
            <div className="absolute inset-x-0 top-0 h-40 bg-[radial-gradient(circle_at_15%_0%,rgba(139,92,246,.35),transparent_55%),radial-gradient(circle_at_90%_15%,rgba(245,208,97,.16),transparent_45%)]" />
            <div className="relative p-6 sm:p-7">
              <div className="mx-auto mb-5 h-1 w-12 rounded-full bg-white/20 sm:hidden" />
              <div className="mb-7 flex items-start justify-between">
                <div>
                  <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-violet-300/20 bg-violet-400/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[.18em] text-violet-200"><Sparkles className="h-3 w-3" /> Your next scene</div>
                  <h2 id="auth-title" className="font-display text-2xl font-bold tracking-tight text-white">{mode === 'login' ? 'Welcome back.' : 'Make your entrance.'}</h2>
                  <p className="mt-1.5 max-w-[270px] text-xs leading-relaxed text-slate-400">{mode === 'login' ? 'Pick up where your feed left off.' : 'Create a profile for your ideas, drops, and daily wins.'}</p>
                </div>
                <button onClick={onClose} aria-label="Close login" className="rounded-full border border-white/10 p-2 text-slate-400 transition hover:bg-white/10 hover:text-white"><X className="h-4 w-4" /></button>
              </div>

              <div className="mb-6 grid grid-cols-2 rounded-2xl border border-white/10 bg-black/20 p-1">
                {(['login', 'register'] as AuthMode[]).map((item) => (
                  <button key={item} type="button" onClick={() => switchMode(item)} className={`relative rounded-xl py-2.5 text-xs font-bold transition ${mode === item ? 'text-white' : 'text-slate-500 hover:text-slate-300'}`}>
                    {mode === item && <motion.span layoutId="auth-mode" className="absolute inset-0 rounded-xl bg-white/10" transition={{ type: 'spring', stiffness: 420, damping: 30 }} />}
                    <span className="relative">{item === 'login' ? 'Log in' : 'Register'}</span>
                  </button>
                ))}
              </div>

              {step === 'identifier' ? (
                <form onSubmit={handleSendOtp} className="space-y-3.5">
                  {mode === 'register' && <div className="grid grid-cols-2 gap-3">
                    <label className="space-y-1.5 text-xs font-semibold text-slate-300">Name<input value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Aarav Sharma" autoComplete="name" className="auth-input" required /></label>
                    <label className="space-y-1.5 text-xs font-semibold text-slate-300">Username<input value={username} onChange={(event) => setUsername(event.target.value.replace(/\s/g, '').slice(0, 64))} placeholder="aarav" autoComplete="username" className="auth-input" required /></label>
                  </div>}
                  <label className="block space-y-1.5 text-xs font-semibold text-slate-300" htmlFor="auth-identifier">Phone or email<input id="auth-identifier" value={identifier} onChange={(event) => setIdentifier(event.target.value)} placeholder="you@example.com or +919876543210" autoComplete="email tel" className="auth-input" required /></label>
                  {error && <p className="rounded-xl border border-rose-400/20 bg-rose-400/10 px-3 py-2 text-xs text-rose-200">{error}</p>}
                  <button type="submit" disabled={loading} className="auth-primary-btn">{loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}<span>Send verification code</span></button>
                  <p className="flex items-center justify-center gap-1.5 pt-1 text-[10px] text-slate-500"><ShieldCheck className="h-3 w-3" /> Secure OTP sign in</p>
                </form>
              ) : (
                <form onSubmit={handleVerifyOtp} className="space-y-4">
                  <div className="rounded-2xl border border-violet-300/15 bg-violet-300/10 p-3.5 text-xs text-violet-100">Code sent for <span className="font-semibold text-white">{identifier}</span>. Check your configured OTP delivery or backend log.</div>
                  <label className="block space-y-1.5 text-xs font-semibold text-slate-300" htmlFor="auth-otp">Verification code<input id="auth-otp" value={otpCode} onChange={(event) => setOtpCode(event.target.value.replace(/\D/g, '').slice(0, 10))} placeholder="Enter OTP" inputMode="numeric" autoComplete="one-time-code" className="auth-input text-center text-lg tracking-[.35em]" required /></label>
                  {error && <p className="rounded-xl border border-rose-400/20 bg-rose-400/10 px-3 py-2 text-xs text-rose-200">{error}</p>}
                  <button type="submit" disabled={loading} className="auth-primary-btn">{loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}<span>{mode === 'login' ? 'Enter SPREEGO' : 'Create my profile'}</span></button>
                  <button type="button" onClick={() => setStep('identifier')} className="w-full text-center text-xs text-slate-500 transition hover:text-white">Use a different contact</button>
                </form>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
