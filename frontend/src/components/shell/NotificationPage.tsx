import React, { useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { notificationApi } from '../../api/client';
import { NotificationItem } from '../../types';
import { useApp } from '../../context/AppContext';
import {
  Bell,
  CheckCheck,
  ChevronRight,
  Flame,
  Gift,
  Heart,
  MessageCircle,
  Sparkles,
  Trophy,
  Zap,
} from 'lucide-react';

type NotificationFilter = 'all' | 'drops' | 'missions' | 'activity';

const filters: Array<{ id: NotificationFilter; label: string; caption: string }> = [
  { id: 'all', label: 'All', caption: 'Everything in one place' },
  { id: 'drops', label: 'Drops', caption: 'Fresh rewards & alerts' },
  { id: 'missions', label: 'Missions', caption: 'Challenges and opens' },
  { id: 'activity', label: 'Activity', caption: 'Claps and comments' },
];

const getNotificationIcon = (type: NotificationItem['type']) => {
  switch (type) {
    case 'DROP':
      return <Gift className="h-5 w-5 text-spreego-champagne" />;
    case 'BUZZER':
      return <Flame className="h-5 w-5 fill-amber-400 text-amber-400" />;
    case 'MISSION':
      return <Trophy className="h-5 w-5 text-emerald-400" />;
    case 'CLAP':
      return <Heart className="h-5 w-5 fill-rose-400 text-rose-400" />;
    case 'COMMENT':
      return <MessageCircle className="h-5 w-5 text-sky-400" />;
    case 'OPEN':
      return <Zap className="h-5 w-5 text-purple-300" />;
    default:
      return <Bell className="h-5 w-5 text-spreego-violet-light" />;
  }
};
const filterNotifications = (items: NotificationItem[], filter: NotificationFilter) => {
  if (filter === 'drops') return items.filter((item) => item.type === 'DROP' || item.type === 'BUZZER');
  if (filter === 'missions') return items.filter((item) => item.type === 'MISSION' || item.type === 'OPEN');
  if (filter === 'activity') return items.filter((item) => item.type === 'CLAP' || item.type === 'COMMENT');
  return items;
};

export const NotificationPage: React.FC = () => {
  const { showToast } = useApp();
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [activeFilter, setActiveFilter] = useState<NotificationFilter>('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    notificationApi
      .getNotifications()
      .then((data) => {
        if (mounted) setNotifications(data);
      })
      .catch(() => {
        if (mounted) showToast('Notifications are taking a moment to load');
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const unreadCount = notifications.filter((item) => !item.is_read).length;
  const filteredNotifications = useMemo(
    () => filterNotifications(notifications, activeFilter),
    [activeFilter, notifications],
  );

  const handleMarkAllRead = async () => {
    try {
      await notificationApi.markAllAsRead();
      setNotifications((items) => items.map((item) => ({ ...item, is_read: true })));
      showToast('You are all caught up ✨');
    } catch {
      showToast('Could not mark notifications as read');
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.42, ease: 'easeOut' }}
      className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-4 pb-8"
    >
      <section className="relative overflow-hidden rounded-[2rem] border border-white/10 bg-gradient-to-br from-spreego-violet/25 via-spreego-surface to-spreego-elevated p-5 shadow-[0_20px_60px_rgba(64,35,120,.2)]">
        <motion.div
          aria-hidden="true"
          className="absolute -right-12 -top-16 h-40 w-40 rounded-full bg-spreego-violet/25 blur-3xl"
          animate={{ scale: [1, 1.18, 1], opacity: [0.4, 0.7, 0.4] }}
          transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
        />
        <div className="relative flex items-start justify-between gap-4">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-white/10 bg-black/20 px-3 py-1.5 text-[10px] font-bold uppercase tracking-[.18em] text-spreego-champagne">
              <Sparkles className="h-3.5 w-3.5" />
              Your pulse
            </div>
            <h1 className="font-display text-2xl font-bold tracking-tight text-white">Stay in the loop.</h1>
            <p className="mt-1 max-w-sm text-xs leading-relaxed text-slate-300">
              Drops, missions and people who are making your orbit more interesting.
            </p>
          </div>
          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl border border-white/15 bg-black/20 text-spreego-violet-light shadow-lg shadow-spreego-violet/20">
            <Bell className="h-7 w-7" />
            {unreadCount > 0 && (
              <span className="absolute right-5 top-5 flex h-5 min-w-5 items-center justify-center rounded-full border-2 border-spreego-surface bg-spreego-champagne px-1 text-[9px] font-black text-black">
                {unreadCount}
              </span>
            )}
          </div>
        </div>
        <div className="relative mt-5 flex items-center justify-between rounded-2xl border border-white/10 bg-black/15 px-3 py-2.5">
          <div>
            <p className="text-[9px] font-bold uppercase tracking-[.16em] text-spreego-text-secondary">Inbox status</p>
            <p className="mt-0.5 text-xs font-semibold text-white">
              {unreadCount > 0 ? `${unreadCount} new updates waiting` : 'You are all caught up'}
            </p>
          </div>
          <button
            type="button"
            onClick={handleMarkAllRead}
            disabled={unreadCount === 0}
            className="tactile-btn inline-flex items-center gap-1.5 rounded-xl border border-emerald-300/20 bg-emerald-400/10 px-3 py-2 text-[10px] font-bold text-emerald-200 transition hover:bg-emerald-400/20 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <CheckCheck className="h-3.5 w-3.5" />
            Mark read
          </button>
        </div>
      </section>

      <section className="rounded-[1.75rem] border border-white/10 bg-spreego-surface/65 p-2 shadow-xl shadow-black/10 backdrop-blur-xl">
        <div className="grid grid-cols-4 gap-1">
          {filters.map((filter) => {
            const active = activeFilter === filter.id;
            return (
              <button
                type="button"
                key={filter.id}
                onClick={() => setActiveFilter(filter.id)}
                className={`tactile-btn rounded-2xl px-2 py-2.5 text-center transition-all ${
                  active
                    ? 'bg-gradient-to-br from-spreego-violet to-spreego-violet-light text-white shadow-lg shadow-spreego-violet/25'
                    : 'text-spreego-text-secondary hover:bg-white/5 hover:text-white'
                }`}
              >
                <span className="block text-[11px] font-bold">{filter.label}</span>
                <span className="mt-0.5 block truncate text-[8px] opacity-70">{filter.caption}</span>
              </button>
            );
          })}
        </div>
      </section>

      <section className="space-y-2">
        <div className="flex items-center justify-between px-1">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[.18em] text-spreego-text-secondary">Latest updates</p>
            <h2 className="mt-1 font-display text-lg font-bold text-white">{filters.find((item) => item.id === activeFilter)?.label}</h2>
          </div>
          <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[10px] font-semibold text-spreego-text-secondary">
            {filteredNotifications.length} updates
          </span>
        </div>

        <div className="space-y-2">
          {loading ? (
            <div className="space-y-2">
              {[0, 1, 2].map((item) => (
                <div key={item} className="flex animate-pulse items-center gap-3 rounded-2xl border border-white/5 bg-spreego-surface/70 p-4">
                  <div className="h-11 w-11 rounded-2xl bg-white/10" />
                  <div className="flex-1 space-y-2">
                    <div className="h-2.5 w-2/5 rounded-full bg-white/10" />
                    <div className="h-2 w-4/5 rounded-full bg-white/5" />
                  </div>
                </div>
              ))}
            </div>
          ) : filteredNotifications.length === 0 ? (
            <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} className="rounded-3xl border border-dashed border-white/10 bg-spreego-surface/50 px-6 py-14 text-center">
              <Sparkles className="mx-auto h-8 w-8 text-spreego-champagne opacity-70" />
              <p className="mt-3 text-sm font-bold text-white">Nothing new here</p>
              <p className="mt-1 text-xs text-spreego-text-secondary">Switch filters or keep exploring your orbit.</p>
            </motion.div>
          ) : (
            <AnimatePresence mode="popLayout">
              {filteredNotifications.map((notification, index) => (
                <motion.button
                  type="button"
                  layout
                  key={notification.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.98 }}
                  transition={{ delay: index * 0.045, duration: 0.28 }}
                  onClick={() => showToast(notification.action_url ? 'Opening update…' : 'Notification opened')}
                  className={`tactile-btn group flex w-full items-start gap-3 rounded-2xl border p-3 text-left transition-all hover:-translate-y-0.5 ${
                    notification.is_read
                      ? 'border-white/5 bg-spreego-surface/60 hover:border-white/15 hover:bg-spreego-elevated'
                      : 'border-spreego-violet/30 bg-gradient-to-r from-spreego-violet/15 via-spreego-surface to-spreego-surface hover:border-spreego-violet/60'
                  }`}
                >
                  <div className="relative flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-2xl border border-white/10 bg-spreego-elevated">
                    {notification.actor_avatar ? (
                      <img src={notification.actor_avatar} alt={notification.actor_name || 'Notification'} className="h-full w-full object-cover" />
                    ) : (
                      getNotificationIcon(notification.type)
                    )}
                    {!notification.is_read && <span className="absolute right-0.5 top-0.5 h-2.5 w-2.5 rounded-full bg-spreego-champagne ring-2 ring-spreego-elevated" />}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="truncate text-xs font-bold text-white">{notification.title}</h3>
                      <span className="shrink-0 text-[9px] font-medium text-spreego-text-secondary">{notification.created_at}</span>
                    </div>
                    <p className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-slate-300">{notification.message}</p>
                    {notification.reward_badge && (
                      <span className="mt-2 inline-flex rounded-lg border border-spreego-champagne/25 bg-spreego-champagne/10 px-2 py-1 text-[9px] font-bold text-spreego-champagne">
                        {notification.reward_badge}
                      </span>
                    )}
                  </div>
                  <ChevronRight className="mt-3 h-4 w-4 shrink-0 text-spreego-text-tertiary transition-transform group-hover:translate-x-1 group-hover:text-white" />
                </motion.button>
              ))}
            </AnimatePresence>
          )}
        </div>
      </section>
    </motion.div>
  );
};
