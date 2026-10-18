import React from 'react';
import { motion } from 'framer-motion';
import { Bell, Search, Zap, Volume2, VolumeX, ArrowLeft } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { FeedSubTab } from '../../types';
import { authApi } from '../../api/client';

interface TopNavProps {
  activeSubTab?: FeedSubTab;
  onSubTabChange?: (tab: FeedSubTab) => void;
  showBack?: boolean;
  onBack?: () => void;
  customTitle?: string;
}

export const TopNav: React.FC<TopNavProps> = ({
  activeSubTab = 'for_you',
  onSubTabChange,
  showBack = false,
  onBack,
  customTitle,
}) => {
  const { currentTab, soundMuted, toggleSound, setCurrentTab, showToast, isAuthenticated, openAuthModal } = useApp();

  const handleNotificationClick = () => setCurrentTab('notifications');

  const handleSearchClick = () => {
    setCurrentTab('spree');
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-40 mx-auto max-w-lg border-b border-white/[0.07] bg-spreego-canvas/70 px-4 py-2.5 shadow-[0_8px_30px_rgba(0,0,0,.12)] backdrop-blur-2xl">
      <div className="flex items-center justify-between">
        {/* Left: Brand Monogram or Back Arrow */}
        <div className="flex items-center space-x-2">
          {showBack || currentTab === 'notifications' ? (
            <button
              onClick={onBack || (() => setCurrentTab('home'))}
              aria-label="Back"
              className="p-1.5 rounded-full hover:bg-spreego-elevated active:scale-95 text-spreego-text-primary transition-all"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
          ) : (
            <div className="flex items-center space-x-1.5 select-none">
              <motion.div whileHover={{ rotate: 8, scale: 1.06 }} className="relative flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-tr from-spreego-violet to-spreego-violet-light shadow-lg shadow-spreego-violet/35">
                <Zap className="w-4 h-4 text-white fill-white" />
                <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-spreego-champagne shadow-[0_0_10px_rgba(245,208,97,.9)]" />
              </motion.div>
              <span className="font-display font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-100 to-spreego-violet-light bg-clip-text text-transparent">
                SPREEGO
              </span>
            </div>
          )}
        </div>

        {/* Center: Contextual Title or Feed Sub-Tabs */}
        <div className="flex items-center justify-center flex-1 mx-2">
          {customTitle ? (
            <h1 className="font-display font-semibold text-sm text-spreego-text-primary truncate">
              {customTitle}
            </h1>
          ) : currentTab === 'home' ? (
            <div className="flex items-center space-x-1 bg-spreego-surface/80 p-0.5 rounded-full border border-white/5">
              {(['for_you', 'following'] as FeedSubTab[]).map((tab) => {
                const isActive = activeSubTab === tab;
                const labels: Record<FeedSubTab, string> = {
                  for_you: 'For You',
                  following: 'Following',
                  clubs: 'Clubs',
                };
                return (
                  <button
                    key={tab}
                    onClick={() => onSubTabChange?.(tab)}
                    className={`relative rounded-full px-3 py-1.5 text-[11px] font-semibold transition-colors ${
                      isActive
                        ? 'text-white'
                        : 'text-spreego-text-secondary hover:text-spreego-text-primary'
                    }`}
                  >
                    {isActive && (
                      <motion.div
                        layoutId="activeSubTabPill"
                        className="absolute inset-0 -z-10 rounded-full bg-gradient-to-r from-spreego-violet to-spreego-violet-light shadow-sm shadow-spreego-violet/40"
                        transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                      />
                    )}
                    {labels[tab]}
                  </button>
                );
              })}
            </div>
          ) : (
            <span className="font-display font-semibold text-sm text-spreego-text-primary">
              {currentTab === 'notifications' ? 'Notification Center' : currentTab}
            </span>
          )}
        </div>

        {/* Right: Actions (Sound, Search, Notification) */}
        <div className="flex items-center space-x-1.5">
          <motion.button
            onClick={async () => {
              if (isAuthenticated) {
                try {
                  await authApi.logout();
                } catch {
                  // Tokens are cleared by authApi.logout even if the server is unavailable.
                }
              } else {
                openAuthModal();
              }
            }}
            aria-label={isAuthenticated ? 'Log out' : 'Log in'}
            whileTap={{ scale: 0.94 }}
            className={`rounded-full border px-2.5 py-1.5 text-[10px] font-bold transition ${isAuthenticated ? 'border-emerald-300/20 bg-emerald-400/10 text-emerald-200' : 'border-white/10 bg-white/5 text-spreego-text-secondary hover:bg-white/10 hover:text-white'}`}
          >
            {isAuthenticated ? 'Log out' : 'Log in'}
          </motion.button>
          {currentTab === 'home' && (
            <motion.button
              onClick={() => {
                toggleSound();
                showToast(soundMuted ? 'Audio is back on 🔊' : 'Audio muted for a calmer scroll');
              }}
              aria-label={soundMuted ? 'Unmute Audio' : 'Mute Audio'}
              whileTap={{ scale: 0.88, rotate: -8 }}
              className="p-2 rounded-full hover:bg-spreego-elevated active:scale-90 text-spreego-text-secondary hover:text-spreego-text-primary transition-all"
            >
              {soundMuted ? (
                <VolumeX className="w-4 h-4 text-spreego-rose" />
              ) : (
                <Volume2 className="w-4 h-4 text-spreego-text-primary" />
              )}
            </motion.button>
          )}

          <motion.button
            onClick={handleSearchClick}
            aria-label="Search"
            whileHover={{ y: -2, rotate: -4 }}
            whileTap={{ scale: 0.88 }}
            className="p-2 rounded-full hover:bg-spreego-elevated active:scale-90 text-spreego-text-secondary hover:text-spreego-text-primary transition-all"
          >
            <Search className="w-4 h-4" />
          </motion.button>

          <motion.button
            onClick={handleNotificationClick}
            aria-label="Notifications"
            whileHover={{ y: -2, rotate: 5 }}
            whileTap={{ scale: 0.88 }}
            className="relative p-2 rounded-full hover:bg-spreego-elevated active:scale-90 text-spreego-text-secondary hover:text-spreego-text-primary transition-all"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-spreego-violet animate-pulse" />
          </motion.button>
        </div>
      </div>

    </header>
  );
};
