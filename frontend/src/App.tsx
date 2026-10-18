import React, { useState } from 'react';
import { ConsentProvider } from './context/ConsentContext';
import { AppProvider, useApp } from './context/AppContext';
import { TopNav } from './components/shell/TopNav';
import { BottomNav } from './components/shell/BottomNav';
import { ConsentGuardModal } from './components/shell/ConsentGuardModal';
import { FeedSubTab } from './types';
import { ReelFeed } from './components/feed/ReelFeed';
import { SpreeExplore } from './components/spree/SpreeExplore';
import { UploadSheetModal } from './components/upload/UploadSheetModal';
import { OpensOverview } from './components/opens/OpensOverview';
import { CreatorProfile } from './components/creator/CreatorProfile';
import { NotificationPage } from './components/shell/NotificationPage';
import { AuthModal } from './components/shell/AuthModal';
import { useConsent } from './context/ConsentContext';
import { getAuthToken } from './api/client';
import { Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const MainAppContent: React.FC = () => {
  const { currentTab, toastMessage, activeModal, closeModal, setCurrentTab, isAuthenticated, isAuthModalOpen, openAuthModal, closeAuthModal } = useApp();
  const { hasAccepted, isLoading: consentLoading } = useConsent();
  const [activeSubTab, setActiveSubTab] = useState<FeedSubTab>('for_you');

  React.useEffect(() => {
    if (import.meta.env.MODE !== 'test' && !consentLoading && hasAccepted && !isAuthenticated) openAuthModal();
  }, [consentLoading, hasAccepted, isAuthenticated, openAuthModal]);

  React.useEffect(() => {
    if (import.meta.env.MODE !== 'test' && !getAuthToken() && currentTab === 'profile') setCurrentTab('home');
  }, [currentTab, setCurrentTab]);

  return (
    <div className="spreego-noise relative min-h-[100dvh] max-w-lg mx-auto overflow-x-hidden bg-spreego-canvas text-spreego-text-primary selection:bg-spreego-violet selection:text-white">
      <motion.div aria-hidden="true" className="pointer-events-none fixed -left-28 top-24 z-0 h-64 w-64 rounded-full bg-violet-600/10 blur-3xl" animate={{ x: [0, 25, 0], y: [0, 30, 0], opacity: [0.45, 0.7, 0.45] }} transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut' }} />
      <motion.div aria-hidden="true" className="pointer-events-none fixed -right-28 bottom-32 z-0 h-72 w-72 rounded-full bg-amber-300/5 blur-3xl" animate={{ x: [0, -20, 0], y: [0, -24, 0], opacity: [0.35, 0.6, 0.35] }} transition={{ duration: 15, repeat: Infinity, ease: 'easeInOut' }} />
      {/* Top Bar */}
      <TopNav activeSubTab={activeSubTab} onSubTabChange={setActiveSubTab} />

      {/* Screen Router Container */}
      <main className={`relative z-10 flex-1 flex flex-col ${currentTab === 'home' ? 'pt-14 pb-20 px-0' : 'pt-14 pb-20 px-3'}`}>
        <AnimatePresence initial={false}>
          <motion.div
            key={currentTab}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.28, ease: 'easeOut' }}
            className="flex min-h-0 flex-1 flex-col"
          >
            {currentTab === 'home' && (
              <ReelFeed
                subTab={activeSubTab}
                onExploreSponsored={() => setCurrentTab('opens')}
              />
            )}

            {currentTab === 'spree' && <SpreeExplore />}

            {currentTab === 'opens' && <OpensOverview />}

            {currentTab === 'profile' && <CreatorProfile />}

            {currentTab === 'notifications' && <NotificationPage />}
          </motion.div>
        </AnimatePresence>
      </main>

      {/* Creation Modal Bottom Sheet */}
      <UploadSheetModal isOpen={activeModal === 'upload'} onClose={closeModal} />

      {/* Persistent Bottom Dock Navigation */}
      <BottomNav />

      <AuthModal
        isOpen={isAuthModalOpen}
        required={hasAccepted && !isAuthenticated}
        onClose={isAuthenticated ? closeAuthModal : () => undefined}
        onAuthenticated={closeAuthModal}
      />

      {/* R3 Terms & Consent Guard Modal */}
      <ConsentGuardModal />

      {/* Tactile Toast Notification */}
      <AnimatePresence>
        {toastMessage && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            role="status"
            className="fixed bottom-24 left-4 right-4 z-50 mx-auto flex max-w-md items-center gap-3 overflow-hidden rounded-2xl border border-spreego-violet/30 bg-[#151321]/95 px-4 py-3 text-xs text-white shadow-[0_16px_50px_rgba(0,0,0,.4)] backdrop-blur-xl"
          >
            <motion.div
              initial={{ rotate: -20, scale: 0.7 }}
              animate={{ rotate: 0, scale: 1 }}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-spreego-violet to-spreego-violet-light shadow-lg shadow-spreego-violet/30"
            >
              <Sparkles className="h-4 w-4 text-white" />
            </motion.div>
            <div className="min-w-0 flex-1">
              <p className="text-[9px] font-bold uppercase tracking-[.18em] text-spreego-champagne">SPREEGO update</p>
              <span className="block truncate text-[11px] font-medium text-slate-100">{toastMessage}</span>
            </div>
            <motion.div
              initial={{ scaleX: 1 }}
              animate={{ scaleX: 0 }}
              transition={{ duration: 3, ease: 'linear' }}
              className="absolute bottom-0 left-0 h-0.5 w-full origin-left bg-gradient-to-r from-spreego-violet-light to-spreego-champagne"
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <ConsentProvider>
      <AppProvider>
        <MainAppContent />
      </AppProvider>
    </ConsentProvider>
  );
};

export default App;
