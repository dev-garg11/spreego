import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Bell, Search, Zap, Volume2, VolumeX, ArrowLeft } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { FeedSubTab } from '../../types';
import { NotificationDrawer } from './NotificationDrawer';

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
  const { currentTab, soundMuted, toggleSound, showToast, setCurrentTab } = useApp();
  const [isNotificationOpen, setIsNotificationOpen] = useState(false);

  const handleNotificationClick = () => {
    setIsNotificationOpen(true);
  };

  const handleSearchClick = () => {
    setCurrentTab('spree');
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-40 bg-spreego-canvas/80 backdrop-blur-md border-b border-white/5 px-4 py-2.5 max-w-lg mx-auto">
      <div className="flex items-center justify-between">
        {/* Left: Brand Monogram or Back Arrow */}
        <div className="flex items-center space-x-2">
          {showBack ? (
            <button
              onClick={onBack}
              aria-label="Back"
              className="p-1.5 rounded-full hover:bg-spreego-elevated active:scale-95 text-spreego-text-primary transition-all"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
          ) : (
            <div className="flex items-center space-x-1.5 select-none">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-spreego-violet to-spreego-violet-light flex items-center justify-center shadow-sm shadow-spreego-violet/30">
                <Zap className="w-4 h-4 text-white fill-white" />
              </div>
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
              {(['for_you', 'following', 'clubs'] as FeedSubTab[]).map((tab) => {
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
                    className={`relative px-3 py-1 text-xs rounded-full font-medium transition-colors ${
                      isActive
                        ? 'text-white'
                        : 'text-spreego-text-secondary hover:text-spreego-text-primary'
                    }`}
                  >
                    {isActive && (
                      <motion.div
                        layoutId="activeSubTabPill"
                        className="absolute inset-0 bg-spreego-violet rounded-full -z-10 shadow-sm shadow-spreego-violet/40"
                        transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                      />
                    )}
                    {labels[tab]}
                  </button>
                );
              })}
            </div>
          ) : (
            <span className="font-display font-semibold text-sm text-spreego-text-primary capitalize">
              {currentTab}
            </span>
          )}
        </div>

        {/* Right: Actions (Sound, Search, Notification) */}
        <div className="flex items-center space-x-1.5">
          {currentTab === 'home' && (
            <button
              onClick={toggleSound}
              aria-label={soundMuted ? 'Unmute Audio' : 'Mute Audio'}
              className="p-2 rounded-full hover:bg-spreego-elevated active:scale-90 text-spreego-text-secondary hover:text-spreego-text-primary transition-all"
            >
              {soundMuted ? (
                <VolumeX className="w-4 h-4 text-spreego-rose" />
              ) : (
                <Volume2 className="w-4 h-4 text-spreego-text-primary" />
              )}
            </button>
          )}

          <button
            onClick={handleSearchClick}
            aria-label="Search"
            className="p-2 rounded-full hover:bg-spreego-elevated active:scale-90 text-spreego-text-secondary hover:text-spreego-text-primary transition-all"
          >
            <Search className="w-4 h-4" />
          </button>

          <button
            onClick={handleNotificationClick}
            aria-label="Notifications"
            className="relative p-2 rounded-full hover:bg-spreego-elevated active:scale-90 text-spreego-text-secondary hover:text-spreego-text-primary transition-all"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-spreego-violet animate-pulse" />
          </button>
        </div>
      </div>

      {/* Full Notification Center Drawer */}
      <NotificationDrawer
        isOpen={isNotificationOpen}
        onClose={() => setIsNotificationOpen(false)}
        onActionClick={() => setIsNotificationOpen(false)}
      />
    </header>
  );
};
