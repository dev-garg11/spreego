import React, { useState, useEffect } from 'react';
import { UserProfile, SpreeItem } from '../../types';
import { userApi, feedApi } from '../../api/client';
import { StoreCatalog } from './StoreCatalog';
import { AnalyticsDashboard } from './AnalyticsDashboard';
import { useApp } from '../../context/AppContext';
import {
  Settings,
  Share2,
  MapPin,
  ShoppingBag,
  BarChart2,
  Grid,
  Play,
} from 'lucide-react';

export const CreatorProfile: React.FC = () => {
  const { showToast } = useApp();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [viewMode, setViewMode] = useState<'posts' | 'store' | 'analytics'>('posts');
  const [mediaTab, setMediaTab] = useState<'spree' | 'moments' | 'collage' | 'saved'>('spree');
  const [userSprees, setUserSprees] = useState<SpreeItem[]>([]);
  const [isFollowing, setIsFollowing] = useState(false);

  useEffect(() => {
    userApi.getCurrentUser().then((u) => setProfile(u)).catch(() => {});
    feedApi.getExploreItems('all', '').then((items) => setUserSprees(items)).catch(() => {});
  }, []);

  if (!profile) {
    return (
      <div className="py-16 flex justify-center">
        <div className="w-6 h-6 border-2 border-spreego-violet border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="w-full flex-1 flex flex-col space-y-4 pb-16">
      {/* Header & Sub-View Switcher */}
      <div className="flex items-center justify-between py-1 border-b border-white/5">
        <div className="flex items-center space-x-1 bg-spreego-surface p-1 rounded-2xl border border-white/5">
          <button
            onClick={() => setViewMode('posts')}
            className={`px-3 py-1 rounded-xl text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              viewMode === 'posts'
                ? 'bg-spreego-violet text-white shadow-sm shadow-spreego-violet/40'
                : 'text-spreego-text-secondary hover:text-white'
            }`}
          >
            <Grid className="w-3.5 h-3.5" />
            <span>Profile</span>
          </button>
          <button
            onClick={() => setViewMode('store')}
            className={`px-3 py-1 rounded-xl text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              viewMode === 'store'
                ? 'bg-spreego-violet text-white shadow-sm shadow-spreego-violet/40'
                : 'text-spreego-text-secondary hover:text-white'
            }`}
          >
            <ShoppingBag className="w-3.5 h-3.5" />
            <span>Store</span>
          </button>
          <button
            onClick={() => setViewMode('analytics')}
            className={`px-3 py-1 rounded-xl text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              viewMode === 'analytics'
                ? 'bg-spreego-violet text-white shadow-sm shadow-spreego-violet/40'
                : 'text-spreego-text-secondary hover:text-white'
            }`}
          >
            <BarChart2 className="w-3.5 h-3.5" />
            <span>Analytics</span>
          </button>
        </div>

        <button
          onClick={() => showToast('Creator settings')}
          aria-label="Settings"
          className="p-2 rounded-full hover:bg-spreego-elevated text-spreego-text-secondary hover:text-white transition-colors"
        >
          <Settings className="w-4 h-4" />
        </button>
      </div>

      {viewMode === 'store' && <StoreCatalog />}
      {viewMode === 'analytics' && <AnalyticsDashboard />}

      {viewMode === 'posts' && (
        <div className="space-y-4">
          {/* Creator Profile Identity */}
          <div className="flex items-center space-x-4">
            {/* Avatar with Gradient Story Ring */}
            <div className="relative p-0.5 rounded-full bg-gradient-to-tr from-spreego-violet via-pink-500 to-spreego-champagne shadow-lg">
              <img
                src={profile.avatar_url}
                alt={profile.username}
                className="w-20 h-20 rounded-full object-cover border-2 border-[#0B0D13]"
              />
            </div>

            {/* Stats Row */}
            <div className="flex-1 flex justify-around text-center">
              <div>
                <span className="font-mono font-bold text-base text-white block">
                  {profile.post_count}
                </span>
                <span className="text-[10px] text-spreego-text-secondary">Posts</span>
              </div>
              <div>
                <span className="font-mono font-bold text-base text-white block">
                  {(profile.follower_count / 1000).toFixed(1)}K
                </span>
                <span className="text-[10px] text-spreego-text-secondary">Followers</span>
              </div>
              <div>
                <span className="font-mono font-bold text-base text-white block">
                  {profile.following_count}
                </span>
                <span className="text-[10px] text-spreego-text-secondary">Following</span>
              </div>
            </div>
          </div>

          {/* Bio & Details */}
          <div className="space-y-1">
            <div className="flex items-center space-x-1.5">
              <h3 className="font-display font-bold text-base text-white">{profile.display_name}</h3>
              {profile.is_verified && (
                <span className="w-3.5 h-3.5 rounded-full bg-blue-500 flex items-center justify-center text-[9px] text-white font-bold">
                  ✓
                </span>
              )}
            </div>
            <span className="text-xs text-spreego-text-secondary block font-mono">{profile.handle}</span>
            <p className="text-xs text-slate-200 leading-relaxed pt-1">{profile.bio}</p>
            {profile.location && (
              <span className="flex items-center space-x-1 text-[11px] text-spreego-champagne/90 pt-0.5">
                <MapPin className="w-3 h-3" />
                <span>{profile.location}</span>
              </span>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex items-center space-x-2 pt-1">
            <button
              onClick={() => {
                const next = !isFollowing;
                setIsFollowing(next);
                showToast(next ? 'Followed creator!' : 'Unfollowed');
              }}
              className={`flex-1 py-2 rounded-xl text-xs font-bold transition-all shadow-md active:scale-98 ${
                isFollowing
                  ? 'bg-spreego-elevated text-white border border-white/10'
                  : 'bg-spreego-violet hover:brightness-110 text-white shadow-violet-900/30'
              }`}
            >
              {isFollowing ? 'Following' : 'Follow Creator'}
            </button>
            <button
              onClick={() => {
                if (navigator.clipboard) {
                  navigator.clipboard.writeText(window.location.href);
                }
                showToast('Profile link copied!');
              }}
              className="p-2 rounded-xl bg-spreego-elevated border border-white/5 text-white hover:bg-white/10 transition-colors"
            >
              <Share2 className="w-4 h-4" />
            </button>
          </div>

          {/* Story Highlights Row */}
          {profile.story_highlights && profile.story_highlights.length > 0 && (
            <div className="flex items-center space-x-3 overflow-x-auto scrollbar-none py-1">
              {profile.story_highlights.map((h) => (
                <div key={h.id} className="flex flex-col items-center space-y-1 cursor-pointer shrink-0">
                  <div className="w-14 h-14 rounded-full p-0.5 border border-white/20 bg-spreego-surface overflow-hidden">
                    <img src={h.cover_url} alt={h.title} className="w-full h-full rounded-full object-cover" />
                  </div>
                  <span className="text-[10px] text-slate-300 font-medium truncate max-w-[56px] text-center">
                    {h.title}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Media Tabs (Spree, Moments, Collage, Saved) */}
          <div className="flex items-center space-x-1 border-b border-white/5 pt-2">
            {(['spree', 'moments', 'collage', 'saved'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setMediaTab(tab)}
                className={`flex-1 pb-2 text-xs font-semibold capitalize transition-all border-b-2 ${
                  mediaTab === tab
                    ? 'border-spreego-violet text-white'
                    : 'border-transparent text-spreego-text-secondary hover:text-white'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* 3-Column Video/Photo Grid */}
          <div className="grid grid-cols-3 gap-1.5">
            {userSprees.map((spree) => (
              <div
                key={spree.id}
                onClick={() => showToast(`Selected: ${spree.title}`)}
                className="relative aspect-[9/14] bg-spreego-surface rounded-xl overflow-hidden cursor-pointer group border border-white/5 shadow-sm"
              >
                <img
                  src={spree.thumbnail_url || spree.media_url}
                  alt={spree.title}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                <div className="absolute bottom-1.5 left-1.5 right-1.5 flex items-center justify-between text-[9px] font-mono text-white">
                  <span className="flex items-center space-x-0.5">
                    <Play className="w-2.5 h-2.5 fill-white" />
                    <span>{(((spree.views_count || 1200)) / 1000).toFixed(1)}k</span>
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
