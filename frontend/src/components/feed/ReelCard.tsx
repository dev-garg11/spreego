import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { SpreeItem } from '../../types';
import { feedApi, userApi } from '../../api/client';
import { triggerClapConfetti } from './ParticleBurst';
import { VinylDisc } from './VinylDisc';
import { CommentDrawer } from './CommentDrawer';
import { useApp } from '../../context/AppContext';
import {
  Heart,
  MessageCircle,
  Share2,
  Bookmark,
  Volume2,
  VolumeX,
  Play,
  Check,
  Plus,
  Sparkles,
  Flame,
} from 'lucide-react';

interface ReelCardProps {
  spree: SpreeItem;
  isActive: boolean;
  onExploreSponsored?: () => void;
}

export const ReelCard: React.FC<ReelCardProps> = ({ spree, isActive, onExploreSponsored }) => {
  const { soundMuted, showToast, requestAuth } = useApp();
  const [isPlaying, setIsPlaying] = useState(true);
  const [isMuted, setIsMuted] = useState(false);
  const [claps, setClaps] = useState(spree.claps_count ?? 12400);
  const [hasClapped, setHasClapped] = useState(false);
  const [hasSaved, setHasSaved] = useState(false);
  const [hasBuzzed, setHasBuzzed] = useState(false);
  const [isCommentOpen, setIsCommentOpen] = useState(false);
  const [isFollowing, setIsFollowing] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);
  const [showHeartPop, setShowHeartPop] = useState(false);
  const [videoError, setVideoError] = useState(false);
  const [progress, setProgress] = useState(0);
  const lastTapRef = useRef<number>(0);
  const clapInFlightRef = useRef(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  const handleTogglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
        setIsPlaying(false);
      } else {
        videoRef.current.play().catch(() => {});
        setIsPlaying(true);
      }
    } else {
      setIsPlaying(!isPlaying);
    }
  };

  const handleDoubleTap = (e: React.MouseEvent) => {
    const now = Date.now();
    const delta = now - lastTapRef.current;
    if (delta < 300) {
      // Double tap detected
      setShowHeartPop(true);
      setTimeout(() => setShowHeartPop(false), 900);
      handleClap(e.clientX, e.clientY);
    }
    lastTapRef.current = now;
  };

  const handleClap = async (clientX?: number, clientY?: number) => {
    if (!requestAuth()) {
      showToast('Log in first to clap on a Spree 🔐');
      return;
    }
    if (hasClapped || clapInFlightRef.current) return;
    clapInFlightRef.current = true;
    triggerClapConfetti(clientX, clientY);
    setClaps((prev) => prev + 1);
    setHasClapped(true);
    try {
      const response = await feedApi.clapSpree(spree.id);
      if (typeof response.newCount === 'number') setClaps(response.newCount);
      showToast('Clapped! You just added good energy ✨');
    } catch (error) {
      setClaps((prev) => Math.max(0, prev - 1));
      setHasClapped(false);
      showToast(error instanceof Error ? error.message : 'Unable to clap this spree');
    } finally {
      clapInFlightRef.current = false;
    }
  };

  const handleSave = async () => {
    if (!requestAuth()) {
      showToast('Log in first to save a Spree 🔐');
      return;
    }
    const nextSaved = !hasSaved;
    setHasSaved(nextSaved);
    try {
      if (nextSaved) {
        await feedApi.saveSpree(spree.id);
      } else {
        await feedApi.unsaveSpree(spree.id);
      }
      showToast(nextSaved ? 'Saved to your collection 🔖' : 'Removed from your collection');
    } catch (error) {
      setHasSaved(!nextSaved);
      showToast(error instanceof Error ? error.message : 'Unable to update saved state');
    }
  };

  const handleFollow = async () => {
    if (!requestAuth()) {
      showToast('Log in first to follow creators 🔐');
      return;
    }
    const nextState = !isFollowing;
    setIsFollowing(nextState);
    if (!spree.creator?.id) return;
    try {
      if (nextState) {
        await userApi.followUser(spree.creator.id);
      } else {
        await userApi.unfollowUser(spree.creator.id);
      }
      showToast(nextState ? `Following ${creatorHandle}` : `Unfollowed ${creatorHandle}`);
    } catch (error) {
      setIsFollowing(!nextState);
      showToast(error instanceof Error ? error.message : 'Unable to update follow state');
    }
  };

  const handleShare = async () => {
    try {
      const res = await feedApi.shareSpree(spree.id, 'web');
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(res.shareUrl);
        setCopiedLink(true);
        setTimeout(() => setCopiedLink(false), 2200);
        showToast('Share link copied — send the vibe 🚀');
      }
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Unable to share this spree');
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current && videoRef.current.duration) {
      setProgress((videoRef.current.currentTime / videoRef.current.duration) * 100);
    }
  };

  const creatorAvatar = spree.creator?.avatar_url || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150';
  const creatorUsername = spree.creator?.username || 'creator';
  const creatorHandle = spree.creator?.handle || `@${creatorUsername}`;

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    if (isActive) {
      try {
        const playback = video.play();
        if (playback && typeof playback.then === 'function') {
          playback.then(() => setIsPlaying(true)).catch(() => setIsPlaying(false));
        } else {
          setIsPlaying(true);
        }
      } catch {
        setIsPlaying(false);
      }
    } else {
      video.pause();
      setIsPlaying(false);
    }
  }, [isActive]);

  return (
    <motion.div
      onClick={handleDoubleTap}
      initial={{ opacity: 0, scale: 0.985 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.45, ease: 'easeOut' }}
      className="relative flex h-[calc(100dvh-5.5rem)] w-full snap-start select-none items-center justify-center overflow-hidden rounded-[1.75rem] border border-white/10 bg-black shadow-2xl shadow-black/50"
    >
      {/* Copied Link Toast */}
      {copiedLink && (
        <div className="absolute top-4 z-40 px-3.5 py-1.5 rounded-full bg-black/80 backdrop-blur-md border border-spreego-champagne/40 text-spreego-champagne text-xs font-semibold flex items-center space-x-1.5 shadow-xl animate-bounce">
          <Sparkles className="w-3.5 h-3.5 text-spreego-champagne" />
          <span>Link copied to clipboard!</span>
        </div>
      )}

      {/* Double-Tap Heart Pop Animation */}
      <AnimatePresence>
        {showHeartPop && (
          <motion.div
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: [0, 1.4, 1.1], opacity: [0, 1, 0] }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.75, ease: 'easeOut' }}
            className="absolute pointer-events-none z-40 flex items-center justify-center"
          >
            <Heart className="w-24 h-24 fill-rose-500 text-rose-500 drop-shadow-[0_0_24px_rgba(244,63,94,0.8)]" />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Media Player */}
      {!videoError && (spree.media_url.endsWith('.mp4') || spree.type === 'VIDEO_SHORT') ? (
        <video
          ref={videoRef}
          src={spree.media_url}
          poster={spree.thumbnail_url}
          autoPlay={isActive}
          loop
          muted={soundMuted || isMuted}
          playsInline
          onTimeUpdate={handleTimeUpdate}
          onError={() => setVideoError(true)}
          className="w-full h-full object-cover"
        />
      ) : (
        <img
          src={spree.thumbnail_url || spree.media_url}
          alt={spree.title}
          className="w-full h-full object-cover"
        />
      )}

      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,rgba(4,5,10,.52),transparent_24%,transparent_55%,rgba(4,5,10,.92))]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_80%_30%,rgba(124,58,237,.16),transparent_32%)]" />

      {isActive && (
        <motion.div
          aria-hidden="true"
          initial={{ x: '-140%', opacity: 0 }}
          animate={{ x: ['-140%', '180%'], opacity: [0, 0.24, 0] }}
          transition={{ duration: 4.8, repeat: Infinity, repeatDelay: 3.5, ease: 'easeInOut' }}
          className="pointer-events-none absolute inset-y-0 -left-1/2 z-10 w-1/3 -skew-x-[18deg] bg-gradient-to-r from-transparent via-white/30 to-transparent blur-2xl"
        />
      )}

      {/* Video Progress Scrubber Bar */}
      <div className="absolute bottom-0 left-0 right-0 z-20 h-1 bg-white/20">
        <div
          className="h-full bg-gradient-to-r from-spreego-violet-light to-spreego-champagne transition-all duration-100"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Play/Pause Overlay Indicator */}
      {!isPlaying && (
        <div
          onClick={handleTogglePlay}
          className="absolute inset-0 flex items-center justify-center bg-black/30 backdrop-blur-[2px] cursor-pointer"
        >
          <div className="w-16 h-16 rounded-full bg-black/60 border border-white/20 flex items-center justify-center text-white shadow-xl">
            <Play className="w-8 h-8 fill-white translate-x-0.5" />
          </div>
        </div>
      )}

      {/* Sound Toggle (Top Left) */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          setIsMuted(!isMuted);
        }}
        aria-label="Sound toggle"
        className="absolute top-4 left-4 z-20 p-2.5 rounded-full bg-black/50 backdrop-blur-md border border-white/10 text-white hover:bg-black/70 transition-all active:scale-95"
      >
        {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
      </button>

      <div className="pointer-events-none absolute left-16 top-4 z-10 flex items-center gap-2 rounded-full border border-white/10 bg-black/25 px-2.5 py-1.5 text-[9px] font-bold uppercase tracking-[.18em] text-white/80 backdrop-blur-xl">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-spreego-champagne shadow-[0_0_8px_rgba(245,208,97,.9)]" />
        {spree.sponsored ? 'Featured drop' : 'Live in your orbit'}
      </div>

      {/* Right Rail Actions */}
      <div
        onClick={(e) => e.stopPropagation()}
        className="absolute right-3 bottom-24 z-20 flex flex-col items-center space-y-4"
      >
        {/* Creator Avatar with Follow Button */}
        <div className="relative">
          <img
            src={creatorAvatar}
            alt={creatorUsername}
            className="w-11 h-11 rounded-full object-cover border-2 border-white/80 shadow-md"
          />
          <button
            onClick={handleFollow}
            aria-label={isFollowing ? 'Unfollow creator' : 'Follow creator'}
            className={`absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-4 h-4 rounded-full flex items-center justify-center text-white transition-transform ${
              isFollowing ? 'bg-emerald-500 scale-90' : 'bg-spreego-violet hover:scale-110'
            }`}
          >
            {isFollowing ? <Check className="w-2.5 h-2.5" /> : <Plus className="w-2.5 h-2.5" />}
          </button>
        </div>

        {/* Buzzer Booster Button (24-hr Reach Multiplier) */}
        <button
          onClick={() => {
            setHasBuzzed(true);
            triggerClapConfetti();
            showToast('Buzzer boost activated — 2× reach is live 🔥');
          }}
          aria-label="Buzzer Boost"
          className="flex flex-col items-center group active:scale-90 transition-transform"
        >
          <div
            className={`w-10 h-10 rounded-full flex items-center justify-center backdrop-blur-md border transition-all ${
              hasBuzzed
                ? 'bg-amber-500/30 border-amber-400 text-amber-300 shadow-lg shadow-amber-500/40 animate-pulse'
                : 'bg-black/40 border-white/10 text-white group-hover:bg-black/60'
            }`}
          >
            <Flame className={`w-5 h-5 ${hasBuzzed ? 'fill-amber-400 text-amber-400' : 'text-amber-400'}`} />
          </div>
          <span className="text-[9px] font-mono font-bold text-amber-400 mt-0.5 drop-shadow">
            {hasBuzzed ? '2x LIVE' : 'BOOST'}
          </span>
        </button>

        {/* Clap Reaction Button */}
        <button
          onClick={(e) => handleClap(e.clientX, e.clientY)}
          aria-label="Clap"
          className="flex flex-col items-center group active:scale-90 transition-transform"
        >
          <div
            className={`w-10 h-10 rounded-full flex items-center justify-center backdrop-blur-md border transition-all ${
              hasClapped
                ? 'bg-rose-500/20 border-rose-500/60 text-rose-400'
                : 'bg-black/40 border-white/10 text-white group-hover:bg-black/60'
            }`}
          >
            <Heart className={`w-5 h-5 ${hasClapped ? 'fill-rose-500 text-rose-500' : ''}`} />
          </div>
          <span className="text-[10px] font-mono font-medium text-white mt-1 drop-shadow">
            {claps.toLocaleString()}
          </span>
        </button>

        {/* Comments Drawer Trigger */}
        <button
          onClick={() => {
            if (!requestAuth()) {
              showToast('Log in first to join the conversation 🔐');
              return;
            }
            setIsCommentOpen(true);
          }}
          aria-label="Comments"
          className="flex flex-col items-center group active:scale-90 transition-transform"
        >
          <div className="w-10 h-10 rounded-full bg-black/40 backdrop-blur-md border border-white/10 flex items-center justify-center text-white group-hover:bg-black/60 transition-all">
            <MessageCircle className="w-5 h-5" />
          </div>
          <span className="text-[10px] font-mono font-medium text-white mt-1 drop-shadow">
            {spree.comments_count ?? 24}
          </span>
        </button>

        {/* Share Button */}
        <button
          onClick={handleShare}
          aria-label="Share"
          className="flex flex-col items-center group active:scale-90 transition-transform"
        >
          <div className="w-10 h-10 rounded-full bg-black/40 backdrop-blur-md border border-white/10 flex items-center justify-center text-white group-hover:bg-black/60 transition-all">
            <Share2 className="w-5 h-5" />
          </div>
          <span className="text-[10px] font-mono font-medium text-white mt-1 drop-shadow">
            {spree.shares_count ?? 12}
          </span>
        </button>

        {/* Bookmark Button */}
        <button
          onClick={handleSave}
          aria-label="Save"
          className="flex flex-col items-center group active:scale-90 transition-transform"
        >
          <div
            className={`w-10 h-10 rounded-full flex items-center justify-center backdrop-blur-md border transition-all ${
              hasSaved
                ? 'bg-spreego-champagne/20 border-spreego-champagne/60 text-spreego-champagne'
                : 'bg-black/40 border-white/10 text-white group-hover:bg-black/60'
            }`}
          >
            <Bookmark className={`w-5 h-5 ${hasSaved ? 'fill-spreego-champagne text-spreego-champagne' : ''}`} />
          </div>
          <span className="text-[10px] font-mono font-medium text-white mt-1 drop-shadow">
            {spree.saves_count ?? 45}
          </span>
        </button>

        {/* Vinyl Disc Animation */}
        <VinylDisc
          isPlaying={isPlaying}
          coverUrl={creatorAvatar}
          onClick={handleTogglePlay}
        />
      </div>

      {/* Bottom Creator Info Overlay */}
      <div
        onClick={(e) => e.stopPropagation()}
        className="absolute left-4 right-16 bottom-5 z-20 flex flex-col space-y-2 pointer-events-auto"
      >
        {/* Creator Handle & Verified Badge */}
        <div className="flex items-center space-x-1.5">
          <span className="font-display font-bold text-sm text-white drop-shadow-md">
            {creatorHandle}
          </span>
          {spree.creator?.is_verified && (
            <span className="w-3.5 h-3.5 rounded-full bg-blue-500 flex items-center justify-center text-[9px] text-white font-bold">
              ✓
            </span>
          )}
        </div>

        {/* Caption */}
        <p className="text-xs text-slate-100 line-clamp-2 leading-snug drop-shadow-md">
          {spree.caption || spree.title}
        </p>

        {/* Audio Track Tag */}
        {spree.audio_title && (
          <div className="flex items-center space-x-1.5 text-[11px] text-spreego-champagne/90">
            <span className="text-[10px]">🎵</span>
            <span className="truncate">{spree.audio_title} • {spree.audio_artist}</span>
          </div>
        )}

        {/* Sponsored Campaign Badge Pill (e.g. SkyWings) */}
        {spree.sponsored && (
          <div className="mt-1 flex items-center justify-between bg-[#12151E]/90 backdrop-blur-md border border-white/10 p-2 rounded-xl shadow-lg">
            <div className="flex items-center space-x-2 truncate">
              {spree.sponsored.logo_url && (
                <img
                  src={spree.sponsored.logo_url}
                  alt={spree.sponsored.brand_name}
                  className="w-5 h-5 rounded-md object-cover"
                />
              )}
              <div className="truncate">
                <span className="text-[10px] uppercase font-bold tracking-wider text-spreego-champagne">
                  Sponsored by {spree.sponsored.brand_name}
                </span>
                <p className="text-[9px] text-spreego-text-secondary truncate">{spree.sponsored.tagline}</p>
              </div>
            </div>
            <button
              onClick={onExploreSponsored}
              className="text-[10px] font-semibold px-2.5 py-1 rounded-full bg-gradient-to-r from-spreego-violet to-spreego-violet-light text-white shrink-0 hover:brightness-110 active:scale-95 transition-all"
            >
              {spree.sponsored.cta_text || 'Explore'}
            </button>
          </div>
        )}
      </div>

      {/* Comments Drawer Modal */}
      <CommentDrawer
        isOpen={isCommentOpen}
        onClose={() => setIsCommentOpen(false)}
        spreeId={spree.id}
      />
    </motion.div>
  );
};
