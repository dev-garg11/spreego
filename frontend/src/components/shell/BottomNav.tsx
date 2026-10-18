import React from 'react';
import { motion } from 'framer-motion';
import { Home, Compass, Plus, Trophy, User } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { ShellTab } from '../../types';

interface TabItem {
  id: ShellTab;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  isSpecial?: boolean;
}

const TABS: TabItem[] = [
  { id: 'home', label: 'Home', icon: Home },
  { id: 'spree', label: 'Spree', icon: Compass },
  { id: 'upload', label: 'Create', icon: Plus, isSpecial: true },
  { id: 'opens', label: 'Opens', icon: Trophy },
  { id: 'profile', label: 'Profile', icon: User },
];

export const BottomNav: React.FC = () => {
  const { currentTab, setCurrentTab, openModal } = useApp();

  const handleTabClick = (tab: TabItem) => {
    if (tab.isSpecial) {
      // Trigger upload creation modal bottom sheet
      openModal('upload');
    } else {
      setCurrentTab(tab.id);
    }
  };

  return (
    <nav
      aria-label="Bottom Navigation"
      className="fixed bottom-3 left-1/2 z-40 w-[calc(100%-1.25rem)] max-w-lg -translate-x-1/2 rounded-2xl border border-white/10 bg-spreego-surface/80 px-2 py-2 shadow-[0_16px_50px_rgba(0,0,0,.35)] backdrop-blur-2xl"
    >
      <div className="flex items-center justify-around relative">
        {TABS.map((tab) => {
          const isActive = currentTab === tab.id && !tab.isSpecial;
          const Icon = tab.icon;

          if (tab.isSpecial) {
            return (
              <motion.button
                key={tab.id}
                onClick={() => handleTabClick(tab)}
                aria-label="Create Spree"
                whileHover={{ y: -3, rotate: 6 }}
                whileTap={{ scale: 0.88, rotate: -6 }}
                className="relative -top-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-tr from-spreego-violet to-spreego-violet-light text-white shadow-lg shadow-spreego-violet/40 transition-all duration-150 hover:brightness-110"
              >
                <Icon className="w-6 h-6 stroke-[2.5]" />
              </motion.button>
            );
          }

          return (
            <button
              key={tab.id}
              onClick={() => handleTabClick(tab)}
              aria-label={tab.label}
              className={`relative flex flex-col items-center justify-center py-1 px-3 min-w-[56px] min-h-[44px] rounded-xl transition-all duration-150 active:scale-95 ${
                isActive
                  ? 'text-spreego-text-primary'
                  : 'text-spreego-text-secondary hover:text-spreego-text-primary'
              }`}
            >
              {isActive && (
                <motion.div
                  layoutId="activeBottomTabPill"
                  className="absolute inset-0 -z-10 rounded-xl border border-spreego-violet/30 bg-spreego-elevated/80"
                  transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                />
              )}
              <div className="relative">
                <Icon
                  className={`w-5 h-5 transition-transform duration-150 ${
                    isActive ? 'text-spreego-violet scale-110' : ''
                  }`}
                />
              </div>
              <span
                className={`text-[11px] font-medium tracking-tight mt-1 transition-colors ${
                  isActive ? 'text-white font-semibold' : 'text-spreego-text-secondary'
                }`}
              >
                {tab.label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};
