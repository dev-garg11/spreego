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
import { Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const MainAppContent: React.FC = () => {
  const { currentTab, toastMessage, activeModal, closeModal, setCurrentTab } = useApp();
  const [activeSubTab, setActiveSubTab] = useState<FeedSubTab>('for_you');

  return (
    <div className="relative min-h-[100dvh] max-w-lg mx-auto bg-spreego-canvas text-spreego-text-primary flex flex-col overflow-x-hidden selection:bg-spreego-violet selection:text-white">
      {/* Top Bar */}
      <TopNav activeSubTab={activeSubTab} onSubTabChange={setActiveSubTab} />

      {/* Screen Router Container */}
      <main className={`flex-1 flex flex-col ${currentTab === 'home' ? 'pt-14 pb-20 px-0' : 'pt-14 pb-20 px-3'}`}>
        {currentTab === 'home' && (
          <ReelFeed
            subTab={activeSubTab}
            onExploreSponsored={() => setCurrentTab('opens')}
          />
        )}

        {currentTab === 'spree' && <SpreeExplore />}

        {currentTab === 'opens' && <OpensOverview />}

        {currentTab === 'profile' && <CreatorProfile />}
      </main>

      {/* Creation Modal Bottom Sheet */}
      <UploadSheetModal isOpen={activeModal === 'upload'} onClose={closeModal} />

      {/* Persistent Bottom Dock Navigation */}
      <BottomNav />

      {/* R3 Terms & Consent Guard Modal */}
      <ConsentGuardModal />

      {/* Tactile Toast Notification */}
      <AnimatePresence>
        {toastMessage && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="fixed bottom-20 left-4 right-4 z-50 max-w-md mx-auto bg-spreego-elevated/95 backdrop-blur-md border border-white/10 text-white text-xs px-4 py-3 rounded-2xl shadow-xl flex items-center space-x-2"
          >
            <Sparkles className="w-4 h-4 text-spreego-violet-light flex-shrink-0" />
            <span className="truncate">{toastMessage}</span>
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
