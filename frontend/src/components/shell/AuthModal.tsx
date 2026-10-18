import React, { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ArrowRight, Check, Eye, EyeOff, KeyRound, Loader2, ShieldCheck, Sparkles, X } from 'lucide-react';
import { authApi } from '../../api/client';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAuthenticated: () => void;
  required?: boolean;
}

type AuthMode = 'login' | 'register';
type AuthView = 'password' | 'otp' | 'forgot';
type OtpStep = 'identifier' | 'code';
type ForgotStep = 'identifier' | 'reset';

const formatCountdown = (seconds: number) => `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onAuthenticated, required = false }) => {
  const [mode, setMode] = useState<AuthMode>('login');
  const [view, setView] = useState<AuthView>('password');
  const [otpStep, setOtpStep] = useState<OtpStep>('identifier');
  const [forgotStep, setForgotStep] = useState<ForgotStep>('identifier');
  const [identifier, setIdentifier] = useState('');
  const [fullName, setFullName] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [lockSeconds, setLockSeconds] = useState(0);

  useEffect(() => {
    if (!lockSeconds) return undefined;
    const timer = window.setInterval(() => setLockSeconds((value) => Math.max(0, value - 1)), 1000);
    return () => window.clearInterval(timer);
  }, [lockSeconds]);

  useEffect(() => {
    if (isOpen) {
      setError(null);
      setInfo(null);
    }
  }, [isOpen]);

  const resetFeedback = () => {
    setError(null);
    setInfo(null);
  };

  const switchMode = (nextMode: AuthMode) => {
    setMode(nextMode);
    setView('password');
    setOtpStep('identifier');
    setForgotStep('identifier');
    resetFeedback();
  };

  const handlePasswordSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (lockSeconds > 0) return;
    resetFeedback();
    if (mode === 'register' && password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      if (mode === 'login') {
        await authApi.login(identifier, password);
      } else {
        await authApi.register({ identifier, username, password, fullName });
      }
      onAuthenticated();
    } catch (err) {
      const status = (err as { status?: number }).status;
      if (status === 429) setLockSeconds(15 * 60);
      setError(err instanceof Error ? err.message : 'Unable to continue. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSendOtp = async (event: React.FormEvent) => {
    event.preventDefault();
    resetFeedback();
    setLoading(true);
    try {
      await authApi.sendOtp(identifier);
      setOtpStep('code');
      setInfo('Verification code sent. Check your configured OTP delivery.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to send verification code.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (event: React.FormEvent) => {
    event.preventDefault();
    resetFeedback();
    setLoading(true);
    try {
      await authApi.verifyOtp(identifier, otpCode, mode === 'register' ? { fullName, username } : undefined);
      onAuthenticated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to verify code.');
    } finally {
      setLoading(false);
    }
  };

  const handleForgotRequest = async (event: React.FormEvent) => {
    event.preventDefault();
    resetFeedback();
    setLoading(true);
    try {
      const message = await authApi.requestPasswordReset(identifier);
      setInfo(message);
      setForgotStep('reset');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to start password reset.');
    } finally {
      setLoading(false);
    }
  };

  const handleForgotReset = async (event: React.FormEvent) => {
    event.preventDefault();
    resetFeedback();
    if (newPassword.length < 8) {
      setError('New password must contain at least 8 characters.');
      return;
    }
    setLoading(true);
    try {
      const message = await authApi.resetPassword(identifier, otpCode, newPassword);
      setInfo(message);
      setView('password');
      setPassword('');
      setNewPassword('');
      setOtpCode('');
      setForgotStep('identifier');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to reset password.');
    } finally {
      setLoading(false);
    }
  };

  const inputType = showPassword ? 'text' : 'password';
  const close = required ? undefined : onClose;

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[90] flex items-end justify-center bg-[#05050a]/85 p-0 backdrop-blur-xl sm:items-center sm:p-4">
          <motion.button type="button" aria-label="Close authentication" className="absolute inset-0 cursor-default" onClick={close} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
          <motion.div initial={{ y: '100%', opacity: 0.6 }} animate={{ y: 0, opacity: 1 }} exit={{ y: '100%', opacity: 0.6 }} transition={{ type: 'spring', stiffness: 280, damping: 28 }} role="dialog" aria-modal="true" aria-labelledby="auth-title" className="relative z-10 w-full max-w-md overflow-hidden rounded-t-[2rem] border border-white/10 bg-[#11121b] shadow-[0_24px_100px_rgba(0,0,0,.55)] sm:rounded-[2rem]">
            <div className="absolute inset-x-0 top-0 h-40 bg-[radial-gradient(circle_at_15%_0%,rgba(139,92,246,.35),transparent_55%),radial-gradient(circle_at_90%_15%,rgba(245,208,97,.16),transparent_45%)]" />
            <div className="relative p-6 sm:p-7">
              <div className="mx-auto mb-5 h-1 w-12 rounded-full bg-white/20 sm:hidden" />
              <div className="mb-7 flex items-start justify-between">
                <div>
                  <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-violet-300/20 bg-violet-400/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[.18em] text-violet-200"><Sparkles className="h-3 w-3" /> Your next scene</div>
                  <h2 id="auth-title" className="font-display text-2xl font-bold tracking-tight text-white">{view === 'forgot' ? 'Reset your password.' : mode === 'login' ? 'Welcome back.' : 'Make your entrance.'}</h2>
                  <p className="mt-1.5 max-w-[280px] text-xs leading-relaxed text-slate-400">{view === 'forgot' ? 'Recover your account with a secure reset code.' : mode === 'login' ? 'Log in before you clap, create, join, or save.' : 'Create one unique profile for your ideas and daily wins.'}</p>
                </div>
                {!required && <button onClick={onClose} aria-label="Close login" className="tactile-btn rounded-full border border-white/10 p-2 text-slate-400 transition hover:bg-white/10 hover:text-white"><X className="h-4 w-4" /></button>}
              </div>

              {view !== 'forgot' && (
                <div className="mb-5 grid grid-cols-2 rounded-2xl border border-white/10 bg-black/20 p-1">
                  {(['login', 'register'] as AuthMode[]).map((item) => (
                    <button key={item} type="button" onClick={() => switchMode(item)} className={`tactile-btn relative rounded-xl py-2.5 text-xs font-bold transition ${mode === item ? 'text-white' : 'text-slate-500 hover:text-slate-300'}`}>
                      {mode === item && <motion.span layoutId="auth-mode" className="absolute inset-0 rounded-xl bg-white/10" transition={{ type: 'spring', stiffness: 420, damping: 30 }} />}
                      <span className="relative">{item === 'login' ? 'Log in' : 'Register'}</span>
                    </button>
                  ))}
                </div>
              )}

              {view === 'password' && (
                <form onSubmit={handlePasswordSubmit} className="space-y-3.5">
                  {mode === 'register' && <div className="grid grid-cols-2 gap-3"><label className="space-y-1.5 text-xs font-semibold text-slate-300">Name<input value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Aarav Sharma" autoComplete="name" className="auth-input" required /></label><label className="space-y-1.5 text-xs font-semibold text-slate-300">Username<input value={username} onChange={(event) => setUsername(event.target.value.replace(/\s/g, '').slice(0, 64))} placeholder="aarav" autoComplete="username" className="auth-input" required /></label></div>}
                  <label className="block space-y-1.5 text-xs font-semibold text-slate-300">Username, email, or phone<input value={identifier} onChange={(event) => setIdentifier(event.target.value)} placeholder="@aarav or you@example.com" autoComplete="username" className="auth-input" required /></label>
                  <label className="block space-y-1.5 text-xs font-semibold text-slate-300">Password<div className="relative"><input value={password} onChange={(event) => setPassword(event.target.value)} type={inputType} placeholder="At least 8 characters" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} className="auth-input pr-11" required minLength={8} /><button type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword((value) => !value)} className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-2 text-slate-400 hover:text-white">{showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button></div></label>
                  {mode === 'register' && <label className="block space-y-1.5 text-xs font-semibold text-slate-300">Confirm password<input value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} type={inputType} autoComplete="new-password" className="auth-input" required minLength={8} /></label>}
                  {lockSeconds > 0 && <p className="rounded-xl border border-amber-400/20 bg-amber-400/10 px-3 py-2 text-xs text-amber-100">Too many attempts. Try again in <strong>{formatCountdown(lockSeconds)}</strong>.</p>}
                  {error && <p className="rounded-xl border border-rose-400/20 bg-rose-400/10 px-3 py-2 text-xs text-rose-200">{error}</p>}
                  {info && <p className="rounded-xl border border-emerald-400/20 bg-emerald-400/10 px-3 py-2 text-xs text-emerald-100">{info}</p>}
                  <button type="submit" disabled={loading || lockSeconds > 0} className="auth-primary-btn tactile-btn">{loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}<span>{mode === 'login' ? 'Enter SPREEGO' : 'Create my profile'}</span></button>
                  {mode === 'login' && <div className="flex items-center justify-between text-[10px]"><button type="button" onClick={() => { setView('forgot'); resetFeedback(); }} className="tactile-btn text-violet-300 hover:text-white">Forgot password?</button><button type="button" onClick={() => { setView('otp'); setOtpStep('identifier'); resetFeedback(); }} className="tactile-btn text-slate-500 hover:text-white">Use OTP instead</button></div>}
                  <p className="flex items-center justify-center gap-1.5 pt-1 text-[10px] text-slate-500"><ShieldCheck className="h-3 w-3" /> Passwords are encrypted before storage</p>
                </form>
              )}

              {view === 'otp' && (otpStep === 'identifier' ? (
                <form onSubmit={handleSendOtp} className="space-y-3.5"><label className="block space-y-1.5 text-xs font-semibold text-slate-300">Phone or email<input value={identifier} onChange={(event) => setIdentifier(event.target.value)} placeholder="you@example.com or +919876543210" className="auth-input" required /></label>{mode === 'register' && <div className="grid grid-cols-2 gap-3"><label className="space-y-1.5 text-xs font-semibold text-slate-300">Name<input value={fullName} onChange={(event) => setFullName(event.target.value)} className="auth-input" required /></label><label className="space-y-1.5 text-xs font-semibold text-slate-300">Username<input value={username} onChange={(event) => setUsername(event.target.value)} className="auth-input" required /></label></div>}{error && <p className="rounded-xl border border-rose-400/20 bg-rose-400/10 px-3 py-2 text-xs text-rose-200">{error}</p>}<button type="submit" disabled={loading} className="auth-primary-btn tactile-btn">{loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <KeyRound className="h-4 w-4" />}<span>Send verification code</span></button><button type="button" onClick={() => setView('password')} className="tactile-btn w-full text-center text-xs text-slate-500 hover:text-white">Use password instead</button></form>
              ) : (
                <form onSubmit={handleVerifyOtp} className="space-y-4"><div className="rounded-2xl border border-violet-300/15 bg-violet-300/10 p-3.5 text-xs text-violet-100">Code sent for <span className="font-semibold text-white">{identifier}</span>.</div><label className="block space-y-1.5 text-xs font-semibold text-slate-300">Verification code<input value={otpCode} onChange={(event) => setOtpCode(event.target.value.replace(/\D/g, '').slice(0, 10))} placeholder="Enter OTP" inputMode="numeric" autoComplete="one-time-code" className="auth-input text-center text-lg tracking-[.35em]" required /></label>{error && <p className="rounded-xl border border-rose-400/20 bg-rose-400/10 px-3 py-2 text-xs text-rose-200">{error}</p>}<button type="submit" disabled={loading} className="auth-primary-btn tactile-btn">{loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}<span>Enter SPREEGO</span></button><button type="button" onClick={() => setOtpStep('identifier')} className="tactile-btn w-full text-center text-xs text-slate-500 hover:text-white">Use a different contact</button></form>
              ))}

              {view === 'forgot' && (forgotStep === 'identifier' ? (
                <form onSubmit={handleForgotRequest} className="space-y-4"><label className="block space-y-1.5 text-xs font-semibold text-slate-300">Username, email, or phone<input value={identifier} onChange={(event) => setIdentifier(event.target.value)} placeholder="@aarav or you@example.com" className="auth-input" required /></label>{error && <p className="rounded-xl border border-rose-400/20 bg-rose-400/10 px-3 py-2 text-xs text-rose-200">{error}</p>}<button type="submit" disabled={loading} className="auth-primary-btn tactile-btn">{loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}<span>Send reset code</span></button><button type="button" onClick={() => setView('password')} className="tactile-btn w-full text-center text-xs text-slate-500 hover:text-white">Back to login</button></form>
              ) : (
                <form onSubmit={handleForgotReset} className="space-y-4"><div className="rounded-2xl border border-violet-300/15 bg-violet-300/10 p-3.5 text-xs text-violet-100">Enter the reset code printed by your configured delivery service.</div><label className="block space-y-1.5 text-xs font-semibold text-slate-300">Reset code<input value={otpCode} onChange={(event) => setOtpCode(event.target.value.replace(/\D/g, '').slice(0, 10))} className="auth-input text-center tracking-[.35em]" required /></label><label className="block space-y-1.5 text-xs font-semibold text-slate-300">New password<input value={newPassword} onChange={(event) => setNewPassword(event.target.value)} type="password" className="auth-input" minLength={8} required /></label>{error && <p className="rounded-xl border border-rose-400/20 bg-rose-400/10 px-3 py-2 text-xs text-rose-200">{error}</p>}{info && <p className="rounded-xl border border-emerald-400/20 bg-emerald-400/10 px-3 py-2 text-xs text-emerald-100">{info}</p>}<button type="submit" disabled={loading} className="auth-primary-btn tactile-btn">{loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}<span>Set new password</span></button></form>
              ))}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
