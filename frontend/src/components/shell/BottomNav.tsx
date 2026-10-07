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
      className="fixed bottom-0 left-0 right-0 z-40 bg-spreego-surface/90 backdrop-blur-xl border-t border-white/10 px-3 py-2 max-w-lg mx-auto"
    >
      <div className="flex items-center justify-around relative">
        {TABS.map((tab) => {
          const isActive = currentTab === tab.id && !tab.isSpecial;
          const Icon = tab.icon;

          if (tab.isSpecial) {
            return (
              <button
                key={tab.id}
                onClick={() => handleTabClick(tab)}
                aria-label="Create Spree"
                className="relative -top-3 flex items-center justify-center w-12 h-12 rounded-full bg-gradient-to-tr from-spreego-violet to-spreego-violet-light text-white shadow-lg shadow-spreego-violet/40 hover:brightness-110 active:scale-90 transition-all duration-150"
              >
                <Icon className="w-6 h-6 stroke-[2.5]" />
              </button>
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
                  className="absolute inset-0 bg-spreego-elevated/80 rounded-xl -z-10 border border-spreego-violet/30"
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
