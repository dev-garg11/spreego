import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { UserProfile, SpreeItem, StoryHighlightItem } from '../../types';
import { userApi, feedApi } from '../../api/client';
import { mockStoryCollections, mockMomentsBook, mockCollageThreads } from '../../api/mockData';
import { StoreCatalog } from './StoreCatalog';
import { AnalyticsDashboard } from './AnalyticsDashboard';
import { StoryViewerModal } from './StoryViewerModal';
import { useApp } from '../../context/AppContext';
import {
  Settings,
  Share2,
  MapPin,
  ShoppingBag,
  BarChart2,
  Grid,
  Play,
  Sparkles,
  BookOpen,
  Layers,
  Bookmark,
  ShieldCheck,
  Edit3,
  Users,
  X,
  ChevronRight,
} from 'lucide-react';

export const CreatorProfile: React.FC = () => {
  const { showToast } = useApp();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [viewMode, setViewMode] = useState<'posts' | 'store' | 'analytics'>('posts');
  const [mediaTab, setMediaTab] = useState<'spree' | 'moments' | 'collage' | 'saved'>('spree');
  const [userSprees, setUserSprees] = useState<SpreeItem[]>([]);
  const [isFollowing, setIsFollowing] = useState(false);
  const [selectedHighlight, setSelectedHighlight] = useState<StoryHighlightItem | null>(null);
  const [isEditProfileOpen, setIsEditProfileOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // Edit profile form state
  const [editName, setEditName] = useState('');
  const [editBio, setEditBio] = useState('');
  const [editLocation, setEditLocation] = useState('');

  // Moments flipbook active page
  const [activeMomentPage, setActiveMomentPage] = useState(0);

  useEffect(() => {
    userApi.getCurrentUser().then((u) => {
      setProfile(u);
      setEditName(u.display_name);
      setEditBio(u.bio || '');
      setEditLocation(u.location || 'Bangalore, India');
    }).catch(() => {});
    feedApi.getExploreItems('all', '').then((items) => setUserSprees(items)).catch(() => {});
  }, []);

  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault();
    if (profile) {
      setProfile({
        ...profile,
        display_name: editName,
        bio: editBio,
        location: editLocation,
      });
      setIsEditProfileOpen(false);
      showToast('Profile updated successfully! ✨');
    }
  };

  if (!profile) {
    return (
      <div className="py-16 flex justify-center">
        <div className="w-6 h-6 border-2 border-spreego-violet border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const storyHighlights = profile.story_highlights || mockStoryCollections;

  return (
    <div className="w-full flex-1 flex flex-col space-y-4 pb-20">
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

        <div className="flex items-center space-x-1">
          <button
            onClick={() => setIsEditProfileOpen(true)}
            aria-label="Edit Profile"
            className="p-2 rounded-full hover:bg-spreego-elevated text-spreego-text-secondary hover:text-white transition-colors"
          >
            <Edit3 className="w-4 h-4" />
          </button>
          <button
            onClick={() => setIsSettingsOpen(true)}
            aria-label="Settings"
            className="p-2 rounded-full hover:bg-spreego-elevated text-spreego-text-secondary hover:text-white transition-colors"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>

      {viewMode === 'store' && <StoreCatalog />}
      {viewMode === 'analytics' && <AnalyticsDashboard />}

      {viewMode === 'posts' && (
        <div className="space-y-4">
          {/* Creator Profile Identity */}
          <div className="flex items-center space-x-4">
            {/* Avatar with Gradient Story Ring (clickable to open 1st highlight) */}
            <div
              onClick={() => setSelectedHighlight(storyHighlights[0])}
              className="relative p-0.5 rounded-full bg-gradient-to-tr from-spreego-violet via-pink-500 to-spreego-champagne shadow-lg cursor-pointer hover:scale-105 transition-transform"
              title="Click to view story"
            >
              <img
                src={profile.avatar_url}
                alt={profile.username}
                className="w-20 h-20 rounded-full object-cover border-2 border-[#0B0D13]"
              />
              <span className="absolute bottom-0 right-0 p-1 rounded-full bg-spreego-violet text-white border-2 border-[#0B0D13]">
                <Sparkles className="w-2.5 h-2.5 text-spreego-champagne" />
              </span>
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

          {/* Trust Score & Spreemates Badges */}
          <div className="flex items-center space-x-2">
            <div className="px-2.5 py-1 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center space-x-1.5 text-emerald-400 text-[10px] font-mono font-bold">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>98.4% Trust Score • High</span>
            </div>
            <div className="px-2.5 py-1 rounded-xl bg-spreego-champagne/10 border border-spreego-champagne/30 flex items-center space-x-1.5 text-spreego-champagne text-[10px] font-mono font-bold">
              <Users className="w-3.5 h-3.5" />
              <span>1,420 Spreemates</span>
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

          {/* Story Highlights Row (Clickable to open full Story Viewer) */}
          {storyHighlights && storyHighlights.length > 0 && (
            <div className="flex items-center space-x-3 overflow-x-auto scrollbar-none py-1">
              {storyHighlights.map((h) => (
                <div
                  key={h.id}
                  onClick={() => setSelectedHighlight(h)}
                  className="flex flex-col items-center space-y-1 cursor-pointer shrink-0 group"
                >
                  <div className="w-14 h-14 rounded-full p-0.5 border border-white/20 bg-spreego-surface overflow-hidden group-hover:border-spreego-violet transition-colors group-hover:scale-105 transform">
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
                className={`flex-1 pb-2 text-xs font-semibold capitalize transition-all border-b-2 flex items-center justify-center space-x-1 ${
                  mediaTab === tab
                    ? 'border-spreego-violet text-white'
                    : 'border-transparent text-spreego-text-secondary hover:text-white'
                }`}
              >
                {tab === 'spree' && <Play className="w-3 h-3" />}
                {tab === 'moments' && <BookOpen className="w-3 h-3" />}
                {tab === 'collage' && <Layers className="w-3 h-3" />}
                {tab === 'saved' && <Bookmark className="w-3 h-3" />}
                <span>{tab}</span>
              </button>
            ))}
          </div>

          {/* TAB 1: SPREE REEL GRID */}
          {mediaTab === 'spree' && (
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
          )}

          {/* TAB 2: MOMENTS FLIP-BOOK */}
          {mediaTab === 'moments' && (
            <div className="p-4 rounded-3xl bg-spreego-surface border border-white/5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center space-x-1.5">
                  <BookOpen className="w-4 h-4 text-spreego-champagne" />
                  <span>Moments &amp; Memories Book</span>
                </span>
                <span className="text-[10px] text-spreego-text-secondary">Kept beyond 24h</span>
              </div>

              {/* Turning Page Card with 3D Flip feel */}
              <motion.div
                key={activeMomentPage}
                initial={{ rotateY: 90, opacity: 0 }}
                animate={{ rotateY: 0, opacity: 1 }}
                exit={{ rotateY: -90, opacity: 0 }}
                transition={{ duration: 0.4 }}
                className="relative rounded-2xl overflow-hidden bg-black border border-white/10 shadow-xl"
              >
                <div className="relative h-64 w-full">
                  <img
                    src={mockMomentsBook[activeMomentPage].image_url}
                    alt={mockMomentsBook[activeMomentPage].book_title}
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent" />
                  <div className="absolute top-3 left-3 bg-black/60 px-2.5 py-1 rounded-full text-[10px] font-mono text-spreego-champagne border border-white/10">
                    {mockMomentsBook[activeMomentPage].date}
                  </div>
                  <div className="absolute bottom-3 left-3 right-3">
                    <p className="text-xs text-white leading-relaxed font-medium">
                      {mockMomentsBook[activeMomentPage].text}
                    </p>
                  </div>
                </div>
              </motion.div>

              {/* Book Page Controls */}
              <div className="flex items-center justify-between pt-1">
                <button
                  disabled={activeMomentPage === 0}
                  onClick={() => setActiveMomentPage((p) => Math.max(0, p - 1))}
                  className="px-3 py-1.5 rounded-xl bg-spreego-elevated disabled:opacity-40 text-xs text-white font-semibold"
                >
                  ← Turn Back
                </button>
                <span className="text-xs font-mono text-spreego-text-secondary">
                  Page {activeMomentPage + 1} of {mockMomentsBook.length}
                </span>
                <button
                  disabled={activeMomentPage === mockMomentsBook.length - 1}
                  onClick={() => setActiveMomentPage((p) => Math.min(mockMomentsBook.length - 1, p + 1))}
                  className="px-3 py-1.5 rounded-xl bg-spreego-violet disabled:opacity-40 text-xs text-white font-semibold"
                >
                  Turn Page →
                </button>
              </div>
            </div>
          )}

          {/* TAB 3: COLLAGE THREADS */}
          {mediaTab === 'collage' && (
            <div className="grid grid-cols-2 gap-2.5">
              {mockCollageThreads.map((thread) => (
                <div
                  key={thread.id}
                  onClick={() => showToast(`Viewing Collage Canvas: ${thread.title}`)}
                  className="group relative rounded-2xl overflow-hidden bg-spreego-surface border border-white/10 cursor-pointer hover:border-spreego-violet/50 transition-all active:scale-[0.98]"
                >
                  <div className="relative h-40 w-full">
                    <img
                      src={thread.cover_url}
                      alt={thread.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/20 to-transparent" />
                    <span className="absolute top-2 right-2 px-1.5 py-0.5 rounded-full bg-black/70 text-[9px] font-mono text-spreego-champagne border border-white/10">
                      {thread.layers_count} layers
                    </span>
                    <div className="absolute bottom-2 left-2 right-2">
                      <h4 className="text-xs font-bold text-white line-clamp-1">{thread.title}</h4>
                      <span className="text-[9px] text-slate-300 block truncate">{thread.creator_name}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* TAB 4: SAVED SPREES */}
          {mediaTab === 'saved' && (
            <div className="grid grid-cols-3 gap-1.5">
              {userSprees.slice(0, 3).map((spree) => (
                <div
                  key={spree.id}
                  onClick={() => showToast(`Saved item: ${spree.title}`)}
                  className="relative aspect-[9/14] bg-spreego-surface rounded-xl overflow-hidden cursor-pointer group border border-white/5 shadow-sm"
                >
                  <img
                    src={spree.thumbnail_url || spree.media_url}
                    alt={spree.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  />
                  <div className="absolute top-2 right-2 p-1 rounded-full bg-black/60 text-spreego-champagne">
                    <Bookmark className="w-3 h-3 fill-spreego-champagne" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Story Viewer Modal */}
      <StoryViewerModal
        isOpen={Boolean(selectedHighlight)}
        highlight={selectedHighlight}
        onClose={() => setSelectedHighlight(null)}
        creatorName={profile.display_name}
        creatorAvatar={profile.avatar_url}
      />

      {/* Edit Profile Bottom Sheet */}
      <AnimatePresence>
        {isEditProfileOpen && (
          <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/75 backdrop-blur-md">
            <div className="absolute inset-0" onClick={() => setIsEditProfileOpen(false)} />
            <motion.div
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ type: 'spring', stiffness: 300, damping: 28 }}
              className="relative z-10 w-full max-w-lg bg-spreego-surface rounded-t-3xl border-t border-white/10 p-5 flex flex-col space-y-4 max-h-[85vh] overflow-y-auto"
            >
              <div className="w-12 h-1 bg-white/20 rounded-full mx-auto" />
              <div className="flex items-center justify-between">
                <h3 className="font-display font-bold text-base text-white">Edit Profile</h3>
                <button
                  onClick={() => setIsEditProfileOpen(false)}
                  className="p-1 rounded-full text-spreego-text-secondary hover:text-white"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleSaveProfile} className="space-y-3">
                <div>
                  <label className="text-xs font-semibold text-spreego-text-secondary block mb-1">
                    Display Name
                  </label>
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    required
                    className="w-full px-3 py-2 rounded-xl bg-spreego-elevated border border-white/10 text-xs text-white focus:outline-none focus:border-spreego-violet"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-spreego-text-secondary block mb-1">
                    Bio Description
                  </label>
                  <textarea
                    value={editBio}
                    onChange={(e) => setEditBio(e.target.value)}
                    rows={3}
                    className="w-full px-3 py-2 rounded-xl bg-spreego-elevated border border-white/10 text-xs text-white focus:outline-none focus:border-spreego-violet resize-none"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-spreego-text-secondary block mb-1">
                    Location
                  </label>
                  <input
                    type="text"
                    value={editLocation}
                    onChange={(e) => setEditLocation(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-spreego-elevated border border-white/10 text-xs text-white focus:outline-none focus:border-spreego-violet"
                  />
                </div>

                <button
                  type="submit"
                  className="w-full py-3 rounded-xl bg-spreego-violet text-white font-bold text-xs shadow-md shadow-violet-900/30 active:scale-98 transition-all"
                >
                  Save Profile Changes
                </button>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Settings Bottom Sheet */}
      <AnimatePresence>
        {isSettingsOpen && (
          <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/75 backdrop-blur-md">
            <div className="absolute inset-0" onClick={() => setIsSettingsOpen(false)} />
            <motion.div
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ type: 'spring', stiffness: 300, damping: 28 }}
              className="relative z-10 w-full max-w-lg bg-spreego-surface rounded-t-3xl border-t border-white/10 p-5 flex flex-col space-y-4"
            >
              <div className="w-12 h-1 bg-white/20 rounded-full mx-auto" />
              <div className="flex items-center justify-between">
                <h3 className="font-display font-bold text-base text-white">Creator Settings</h3>
                <button
                  onClick={() => setIsSettingsOpen(false)}
                  className="p-1 rounded-full text-spreego-text-secondary hover:text-white"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-2 divide-y divide-white/5">
                <div
                  onClick={() => {
                    setIsSettingsOpen(false);
                    setViewMode('analytics');
                  }}
                  className="py-2.5 flex items-center justify-between cursor-pointer hover:text-white text-xs text-slate-200"
                >
                  <span>💳 Creator Wallet &amp; Payout Settings</span>
                  <ChevronRight className="w-4 h-4 text-spreego-text-secondary" />
                </div>
                <div
                  onClick={() => {
                    showToast('Privacy & Security: End-to-end encrypted session active');
                  }}
                  className="py-2.5 flex items-center justify-between cursor-pointer hover:text-white text-xs text-slate-200"
                >
                  <span>🔒 Privacy &amp; Data Telemetry Permissions</span>
                  <ChevronRight className="w-4 h-4 text-spreego-text-secondary" />
                </div>
                <div
                  onClick={() => {
                    showToast('Notification preferences saved');
                  }}
                  className="py-2.5 flex items-center justify-between cursor-pointer hover:text-white text-xs text-slate-200"
                >
                  <span>🔔 In-App Push &amp; Sound Alerts</span>
                  <ChevronRight className="w-4 h-4 text-spreego-text-secondary" />
                </div>
              </div>

              <button
                onClick={() => setIsSettingsOpen(false)}
                className="w-full py-2.5 rounded-xl bg-spreego-elevated text-white font-semibold text-xs border border-white/10"
              >
                Close Settings
              </button>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};
