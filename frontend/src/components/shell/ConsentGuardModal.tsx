import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldCheck, HeartHandshake, Eye, Lock, CheckCircle2, AlertTriangle, ArrowRight } from 'lucide-react';
import { useConsent } from '../../context/ConsentContext';

export const ConsentGuardModal: React.FC = () => {
  const { hasAccepted, isLoading, acceptConsent, declineConsent } = useConsent();
  const [agreedGuidelines, setAgreedGuidelines] = useState(true);
  const [agreedPrivacy, setAgreedPrivacy] = useState(true);
  const [agreedTelemetry, setAgreedTelemetry] = useState(true);
  const [declineWarning, setDeclineWarning] = useState(false);

  if (isLoading || hasAccepted) {
    return null;
  }

  const allChecked = agreedGuidelines && agreedPrivacy && agreedTelemetry;

  const handleAcceptAll = () => {
    if (allChecked) {
      acceptConsent();
    }
  };

  const handleDecline = () => {
    setDeclineWarning(true);
    declineConsent();
  };

  return (
    <AnimatePresence>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="consent-title"
        className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-spreego-canvas/90 backdrop-blur-xl overflow-y-auto"
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.94, y: 16 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.94, y: 16 }}
          transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          className="w-full max-w-md bg-spreego-surface rounded-3xl border border-white/10 p-6 shadow-2xl shadow-black/80 flex flex-col space-y-5"
        >
          {/* Header Monogram */}
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-spreego-violet to-spreego-violet-light flex items-center justify-center shadow-lg shadow-spreego-violet/30">
              <ShieldCheck className="w-7 h-7 text-white" />
            </div>
            <div>
              <h2 id="consent-title" className="font-display font-bold text-xl text-spreego-text-primary tracking-tight">
                Welcome to SPREEGO
              </h2>
              <p className="text-xs text-spreego-text-secondary mt-0.5">
                Review &amp; accept terms before entering the feed
              </p>
            </div>
          </div>

          <p className="text-xs text-spreego-text-secondary leading-relaxed">
            SPREEGO is built on authentic creator expression, privacy-first infrastructure, and transparent discovery. Please confirm your consent below.
          </p>

          {/* 3 Pillars / Sections */}
          <div className="space-y-3">
            {/* Section 1: Community Guidelines */}
            <div
              onClick={() => setAgreedGuidelines(!agreedGuidelines)}
              className={`p-3.5 rounded-2xl border transition-all cursor-pointer flex items-start space-x-3 ${
                agreedGuidelines
                  ? 'bg-spreego-elevated/70 border-spreego-violet/40'
                  : 'bg-spreego-elevated/30 border-white/5 opacity-75'
              }`}
            >
              <div className="mt-0.5 text-spreego-violet">
                <HeartHandshake className="w-5 h-5" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h4 className="font-display font-semibold text-xs text-spreego-text-primary">
                    Community Guidelines
                  </h4>
                  <CheckCircle2
                    className={`w-4 h-4 transition-colors ${
                      agreedGuidelines ? 'text-spreego-violet fill-spreego-violet/20' : 'text-slate-600'
                    }`}
                  />
                </div>
                <p className="text-[11px] text-spreego-text-secondary mt-0.5 leading-snug">
                  Zero harassment, intellectual property respect, authentic challenge submissions, and safe creator commerce.
                </p>
              </div>
            </div>

            {/* Section 2: Privacy Policy */}
            <div
              onClick={() => setAgreedPrivacy(!agreedPrivacy)}
              className={`p-3.5 rounded-2xl border transition-all cursor-pointer flex items-start space-x-3 ${
                agreedPrivacy
                  ? 'bg-spreego-elevated/70 border-spreego-violet/40'
                  : 'bg-spreego-elevated/30 border-white/5 opacity-75'
              }`}
            >
              <div className="mt-0.5 text-spreego-champagne">
                <Lock className="w-5 h-5" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h4 className="font-display font-semibold text-xs text-spreego-text-primary">
                    Privacy Policy
                  </h4>
                  <CheckCircle2
                    className={`w-4 h-4 transition-colors ${
                      agreedPrivacy ? 'text-spreego-champagne fill-spreego-champagne/20' : 'text-slate-600'
                    }`}
                  />
                </div>
                <p className="text-[11px] text-spreego-text-secondary mt-0.5 leading-snug">
                  Encrypted session credentials, zero third-party data broker sales, and verified direct creator payouts.
                </p>
              </div>
            </div>

            {/* Section 3: Interaction Telemetry */}
            <div
              onClick={() => setAgreedTelemetry(!agreedTelemetry)}
              className={`p-3.5 rounded-2xl border transition-all cursor-pointer flex items-start space-x-3 ${
                agreedTelemetry
                  ? 'bg-spreego-elevated/70 border-spreego-violet/40'
                  : 'bg-spreego-elevated/30 border-white/5 opacity-75'
              }`}
            >
              <div className="mt-0.5 text-spreego-violet-light">
                <Eye className="w-5 h-5" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h4 className="font-display font-semibold text-xs text-spreego-text-primary">
                    Interaction Telemetry
                  </h4>
                  <CheckCircle2
                    className={`w-4 h-4 transition-colors ${
                      agreedTelemetry ? 'text-spreego-violet fill-spreego-violet/20' : 'text-slate-600'
                    }`}
                  />
                </div>
                <p className="text-[11px] text-spreego-text-secondary mt-0.5 leading-snug">
                  Watch durations and video skips stream to our backend recommendation engine to tune your discovery feed.
                </p>
              </div>
            </div>
          </div>

          {declineWarning && (
            <div className="flex items-center space-x-2 p-2.5 rounded-xl bg-spreego-rose/10 border border-spreego-rose/20 text-spreego-rose text-xs">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>Consent is required to unlock full interactive feeds and uploads.</span>
            </div>
          )}

          {/* Action CTAs */}
          <div className="space-y-2 pt-1">
            <button
              onClick={handleAcceptAll}
              disabled={!allChecked}
              className={`w-full py-3.5 px-4 rounded-2xl font-display font-semibold text-sm flex items-center justify-center space-x-2 shadow-lg transition-all tactile-btn ${
                allChecked
                  ? 'bg-spreego-violet hover:bg-spreego-violet-dark text-white shadow-spreego-violet/30 active:scale-[0.98]'
                  : 'bg-spreego-elevated text-slate-500 cursor-not-allowed border border-white/5'
              }`}
            >
              <span>Accept &amp; Enter SPREEGO</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            <button
              onClick={handleDecline}
              className="w-full py-2.5 px-4 rounded-2xl text-xs font-medium text-spreego-text-secondary hover:text-spreego-text-primary hover:bg-white/5 transition-all tactile-btn"
            >
              Decline &amp; Limit Features
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
