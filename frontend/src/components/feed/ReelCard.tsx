import React, { useState, useRef } from 'react';
import { SpreeItem } from '../../types';
import { feedApi, userApi } from '../../api/client';
import { triggerClapConfetti } from './ParticleBurst';
import { VinylDisc } from './VinylDisc';
import { CommentDrawer } from './CommentDrawer';
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
} from 'lucide-react';

interface ReelCardProps {
  spree: SpreeItem;
  isActive: boolean;
  onExploreSponsored?: () => void;
}

export const ReelCard: React.FC<ReelCardProps> = ({ spree, isActive, onExploreSponsored }) => {
  const [isPlaying, setIsPlaying] = useState(true);
  const [isMuted, setIsMuted] = useState(false);
  const [claps, setClaps] = useState(spree.claps_count);
  const [hasClapped, setHasClapped] = useState(false);
  const [hasSaved, setHasSaved] = useState(false);
  const [isCommentOpen, setIsCommentOpen] = useState(false);
  const [isFollowing, setIsFollowing] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);
  const lastTapRef = useRef<number>(0);
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
      handleClap(e.clientX, e.clientY);
    }
    lastTapRef.current = now;
  };

  const handleClap = async (clientX?: number, clientY?: number) => {
    triggerClapConfetti(clientX, clientY);
    setClaps((prev) => prev + 1);
    setHasClapped(true);
    await feedApi.clapSpree(spree.id);
  };

  const handleSave = async () => {
    setHasSaved(!hasSaved);
    await feedApi.saveSpree(spree.id);
  };

  const handleFollow = async () => {
    const nextState = !isFollowing;
    setIsFollowing(nextState);
    if (nextState) {
      await userApi.followUser(spree.creator.id);
    }
  };

  const handleShare = async () => {
    const res = await feedApi.shareSpree(spree.id, 'web');
    if (navigator.clipboard) {
      navigator.clipboard.writeText(res.shareUrl);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2200);
    }
  };

  return (
    <div
      onClick={handleDoubleTap}
      className="relative w-full h-[calc(100dvh-5.5rem)] rounded-3xl overflow-hidden bg-black select-none snap-start flex items-center justify-center border border-white/5 shadow-2xl"
    >
      {/* Copied Link Toast */}
      {copiedLink && (
        <div className="absolute top-4 z-40 px-3.5 py-1.5 rounded-full bg-black/80 backdrop-blur-md border border-spreego-champagne/40 text-spreego-champagne text-xs font-semibold flex items-center space-x-1.5 shadow-xl animate-bounce">
          <Sparkles className="w-3.5 h-3.5 text-spreego-champagne" />
          <span>Link copied to clipboard!</span>
        </div>
      )}
      {/* Media Player */}
      {spree.media_url.endsWith('.mp4') || spree.type === 'VIDEO_SHORT' ? (
        <video
          ref={videoRef}
          src={spree.media_url}
          poster={spree.thumbnail_url}
          autoPlay={isActive}
          loop
          muted={isMuted}
          playsInline
          className="w-full h-full object-cover"
        />
      ) : (
        <img
          src={spree.thumbnail_url || spree.media_url}
          alt={spree.title}
          className="w-full h-full object-cover"
        />
      )}

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

      {/* Right Rail Actions */}
      <div
        onClick={(e) => e.stopPropagation()}
        className="absolute right-3 bottom-24 z-20 flex flex-col items-center space-y-4"
      >
        {/* Creator Avatar with Follow Button */}
        <div className="relative">
          <img
            src={spree.creator.avatar_url}
            alt={spree.creator.username}
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
          onClick={() => setIsCommentOpen(true)}
          aria-label="Comments"
          className="flex flex-col items-center group active:scale-90 transition-transform"
        >
          <div className="w-10 h-10 rounded-full bg-black/40 backdrop-blur-md border border-white/10 flex items-center justify-center text-white group-hover:bg-black/60 transition-all">
            <MessageCircle className="w-5 h-5" />
          </div>
          <span className="text-[10px] font-mono font-medium text-white mt-1 drop-shadow">
            {spree.comments_count}
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
            {spree.shares_count}
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
            {spree.saves_count}
          </span>
        </button>

        {/* Vinyl Disc Animation */}
        <VinylDisc
          isPlaying={isPlaying}
          coverUrl={spree.creator.avatar_url}
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
            {spree.creator.handle}
          </span>
          {spree.creator.is_verified && (
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
    </div>
  );
};
