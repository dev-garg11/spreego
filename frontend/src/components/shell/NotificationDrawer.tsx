import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { notificationApi } from '../../api/client';
import { NotificationItem } from '../../types';
import {
  X,
  Bell,
  Sparkles,
  Zap,
  Trophy,
  Heart,
  MessageCircle,
  Gift,
  CheckCheck,
  Flame,
} from 'lucide-react';

interface NotificationDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onActionClick?: (actionUrl?: string) => void;
}

export const NotificationDrawer: React.FC<NotificationDrawerProps> = ({
  isOpen,
  onClose,
  onActionClick,
}) => {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [activeTab, setActiveTab] = useState<'all' | 'drops' | 'missions' | 'activity'>('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isOpen) {
      setLoading(true);
      notificationApi.getNotifications().then((data) => {
        setNotifications(data);
        setLoading(false);
      }).catch(() => {
        setLoading(false);
      });
    }
  }, [isOpen]);

  const handleMarkAllRead = async () => {
    await notificationApi.markAllAsRead();
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
  };

  const filteredNotifs = notifications.filter((n) => {
    if (activeTab === 'drops') return n.type === 'DROP' || n.type === 'BUZZER';
    if (activeTab === 'missions') return n.type === 'MISSION' || n.type === 'OPEN';
    if (activeTab === 'activity') return n.type === 'CLAP' || n.type === 'COMMENT';
    return true;
  });

  const getIcon = (type: NotificationItem['type']) => {
    switch (type) {
      case 'DROP':
        return <Gift className="w-4 h-4 text-spreego-champagne" />;
      case 'BUZZER':
        return <Flame className="w-4 h-4 text-amber-400 fill-amber-400" />;
      case 'MISSION':
        return <Trophy className="w-4 h-4 text-emerald-400" />;
      case 'CLAP':
        return <Heart className="w-4 h-4 text-rose-400 fill-rose-400" />;
      case 'COMMENT':
        return <MessageCircle className="w-4 h-4 text-blue-400" />;
      case 'OPEN':
        return <Zap className="w-4 h-4 text-purple-400" />;
      default:
        return <Bell className="w-4 h-4 text-spreego-violet-light" />;
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/70 backdrop-blur-sm">
          {/* Backdrop Dismiss */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0"
            onClick={onClose}
          />

          {/* Drawer Container */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', stiffness: 320, damping: 30 }}
            className="relative z-10 w-full max-w-sm h-full bg-spreego-canvas border-l border-white/10 flex flex-col shadow-2xl overflow-hidden"
          >
            {/* Header */}
            <div className="p-4 border-b border-white/10 flex items-center justify-between bg-spreego-surface/80 backdrop-blur-md">
              <div className="flex items-center space-x-2">
                <div className="p-1.5 rounded-xl bg-spreego-violet/20 text-spreego-violet-light border border-spreego-violet/30">
                  <Bell className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-display font-bold text-sm text-white">Notifications</h3>
                  <span className="text-[10px] text-spreego-text-secondary">Updates, Drops & Missions</span>
                </div>
              </div>

              <div className="flex items-center space-x-1">
                <button
                  onClick={handleMarkAllRead}
                  title="Mark all as read"
                  className="p-1.5 rounded-xl hover:bg-white/5 text-spreego-text-secondary hover:text-white transition-colors"
                >
                  <CheckCheck className="w-4 h-4 text-emerald-400" />
                </button>
                <button
                  onClick={onClose}
                  aria-label="Close notifications"
                  className="p-1.5 rounded-xl hover:bg-white/5 text-spreego-text-secondary hover:text-white transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Segmented Filter Pills */}
            <div className="flex items-center space-x-1 p-2 bg-spreego-surface/40 border-b border-white/5">
              {(['all', 'drops', 'missions', 'activity'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`flex-1 py-1 text-[11px] font-semibold rounded-xl capitalize transition-all ${
                    activeTab === tab
                      ? 'bg-spreego-violet text-white shadow-sm shadow-spreego-violet/40'
                      : 'text-spreego-text-secondary hover:text-white'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>

            {/* Notifications List */}
            <div className="flex-1 overflow-y-auto divide-y divide-white/5 p-2 space-y-1">
              {loading ? (
                <div className="py-16 flex flex-col items-center justify-center space-y-2">
                  <div className="w-6 h-6 border-2 border-spreego-violet border-t-transparent rounded-full animate-spin" />
                  <span className="text-xs text-spreego-text-secondary">Loading updates...</span>
                </div>
              ) : filteredNotifs.length === 0 ? (
                <div className="py-16 text-center space-y-1">
                  <Sparkles className="w-6 h-6 text-spreego-champagne mx-auto mb-2 opacity-60" />
                  <p className="text-xs font-semibold text-white">All caught up!</p>
                  <p className="text-[10px] text-spreego-text-secondary">No notifications in this category</p>
                </div>
              ) : (
                filteredNotifs.map((notif) => (
                  <motion.div
                    key={notif.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    onClick={() => onActionClick?.(notif.action_url)}
                    className={`p-3 rounded-2xl cursor-pointer transition-all flex space-x-3 items-start ${
                      notif.is_read
                        ? 'bg-spreego-surface/40 hover:bg-spreego-surface/80 opacity-80'
                        : 'bg-gradient-to-r from-spreego-violet/15 to-spreego-surface border border-spreego-violet/30 hover:brightness-110 shadow-sm'
                    }`}
                  >
                    {/* Icon or Avatar */}
                    <div className="relative shrink-0 mt-0.5">
                      {notif.actor_avatar ? (
                        <img
                          src={notif.actor_avatar}
                          alt={notif.actor_name || 'Actor'}
                          className="w-9 h-9 rounded-full object-cover border border-white/20"
                        />
                      ) : (
                        <div className="w-9 h-9 rounded-full bg-spreego-elevated border border-white/10 flex items-center justify-center">
                          {getIcon(notif.type)}
                        </div>
                      )}
                      {!notif.is_read && (
                        <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-spreego-violet ring-2 ring-black" />
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0 space-y-0.5">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-bold text-white truncate">{notif.title}</h4>
                        <span className="text-[9px] font-mono text-spreego-text-secondary shrink-0 ml-1">
                          {notif.created_at}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-300 leading-snug line-clamp-2">
                        {notif.message}
                      </p>
                      {notif.reward_badge && (
                        <span className="inline-block mt-1 text-[9px] font-bold font-mono px-2 py-0.5 rounded-md bg-spreego-champagne/20 text-spreego-champagne border border-spreego-champagne/30">
                          {notif.reward_badge}
                        </span>
                      )}
                    </div>
                  </motion.div>
                ))
              )}
            </div>

            {/* Footer Quick Action */}
            <div className="p-3 border-t border-white/10 bg-spreego-surface/60 flex items-center justify-between text-[11px] text-spreego-text-secondary">
              <span>🔔 Notification Settings</span>
              <button
                onClick={onClose}
                className="px-3 py-1 rounded-xl bg-spreego-violet text-white text-xs font-semibold"
              >
                Done
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

