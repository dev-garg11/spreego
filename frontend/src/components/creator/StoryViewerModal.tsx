import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { StoryHighlightItem } from '../../types';
import {
  X,
  Heart,
  Share2,
  Send,
  MapPin,
  Clock,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { triggerClapConfetti } from '../feed/ParticleBurst';

interface StoryViewerModalProps {
  highlight: StoryHighlightItem | null;
  isOpen: boolean;
  onClose: () => void;
  creatorName?: string;
  creatorAvatar?: string;
}

export const StoryViewerModal: React.FC<StoryViewerModalProps> = ({
  highlight,
  isOpen,
  onClose,
  creatorName = 'Travel With Me',
  creatorAvatar = 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150',
}) => {
  const [currentStoryIdx, setCurrentStoryIdx] = useState(0);
  const [progress, setProgress] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [hasLiked, setHasLiked] = useState(false);
  const [replyText, setReplyText] = useState('');
  const [replySent, setReplySent] = useState(false);

  const stories = highlight?.stories || [];
  const currentStory = stories[currentStoryIdx] || null;

  // Auto-progress timer (5 seconds per story)
  useEffect(() => {
    if (!isOpen || !highlight || isPaused || stories.length === 0) return;

    setProgress(0);
    const interval = 50; // Update every 50ms
    const step = 100 / (5000 / interval);

    const timer = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          if (currentStoryIdx < stories.length - 1) {
            setCurrentStoryIdx((i) => i + 1);
            return 0;
          } else {
            clearInterval(timer);
            onClose();
            return 100;
          }
        }
        return prev + step;
      });
    }, interval);

    return () => clearInterval(timer);
  }, [isOpen, highlight, currentStoryIdx, isPaused, stories.length, onClose]);

  // Reset index when opening a new highlight
  useEffect(() => {
    if (isOpen) {
      setCurrentStoryIdx(0);
      setProgress(0);
      setHasLiked(false);
      setReplySent(false);
    }
  }, [isOpen, highlight]);

  const handleNext = () => {
    if (currentStoryIdx < stories.length - 1) {
      setCurrentStoryIdx((i) => i + 1);
      setProgress(0);
    } else {
      onClose();
    }
  };

  const handlePrev = () => {
    if (currentStoryIdx > 0) {
      setCurrentStoryIdx((i) => i - 1);
      setProgress(0);
    }
  };

  const handleReaction = (e: React.MouseEvent) => {
    triggerClapConfetti(e.clientX, e.clientY);
    setHasLiked(true);
  };

  const handleSendReply = (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyText.trim()) return;
    setReplySent(true);
    setReplyText('');
    setTimeout(() => setReplySent(false), 2000);
  };

  if (!isOpen || !highlight || stories.length === 0) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/95 backdrop-blur-md select-none">
        {/* Story Modal Container */}
        <motion.div
          initial={{ scale: 0.92, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.92, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 350, damping: 28 }}
          className="relative w-full max-w-md h-full max-h-[92dvh] bg-neutral-900 rounded-3xl overflow-hidden border border-white/10 flex flex-col shadow-2xl"
          onMouseDown={() => setIsPaused(true)}
          onMouseUp={() => setIsPaused(false)}
          onTouchStart={() => setIsPaused(true)}
          onTouchEnd={() => setIsPaused(false)}
        >
          {/* Progress Bars Row */}
          <div className="absolute top-3 left-3 right-3 z-30 flex items-center space-x-1.5">
            {stories.map((s, idx) => (
              <div
                key={s.id}
                className="flex-1 h-1 bg-white/30 rounded-full overflow-hidden"
              >
                <div
                  className="h-full bg-white transition-all duration-75"
                  style={{
                    width:
                      idx < currentStoryIdx
                        ? '100%'
                        : idx === currentStoryIdx
                        ? `${progress}%`
                        : '0%',
                  }}
                />
              </div>
            ))}
          </div>

          {/* Header Info */}
          <div className="absolute top-6 left-3 right-3 z-30 flex items-center justify-between pointer-events-auto">
            <div className="flex items-center space-x-2.5 bg-black/40 backdrop-blur-md px-3 py-1.5 rounded-full border border-white/10">
              <img
                src={creatorAvatar}
                alt={creatorName}
                className="w-7 h-7 rounded-full object-cover border border-white/30"
              />
              <div className="flex flex-col">
                <div className="flex items-center space-x-1">
                  <span className="text-xs font-bold text-white">{creatorName}</span>
                  <span className="text-[9px] text-spreego-champagne font-mono font-semibold">
                    • {highlight.title}
                  </span>
                </div>
                {currentStory?.location && (
                  <span className="text-[9px] text-slate-300 flex items-center space-x-0.5">
                    <MapPin className="w-2.5 h-2.5 text-rose-400" />
                    <span>{currentStory.location}</span>
                  </span>
                )}
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <span className="text-[10px] font-mono text-white/70 bg-black/40 px-2 py-1 rounded-full backdrop-blur-md flex items-center space-x-1">
                <Clock className="w-3 h-3 text-spreego-champagne" />
                <span>{currentStory?.timestamp || 'Just now'}</span>
              </span>
              <button
                onClick={onClose}
                aria-label="Close story"
                className="p-2 rounded-full bg-black/50 text-white hover:bg-black/70 backdrop-blur-md transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Main Media Content */}
          <div className="relative flex-1 w-full h-full bg-black flex items-center justify-center overflow-hidden">
            {currentStory && (
              <motion.img
                key={currentStory.id}
                initial={{ opacity: 0.5, scale: 1.05 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
                src={currentStory.media_url}
                alt={currentStory.caption || 'Story media'}
                className="w-full h-full object-cover"
              />
            )}

            {/* Gradient Overlays */}
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/40 pointer-events-none" />

            {/* Tap Navigation Zones (Left 30% / Right 70%) */}
            <div
              onClick={handlePrev}
              className="absolute left-0 top-16 bottom-20 w-1/3 z-20 cursor-pointer"
              title="Previous story"
            />
            <div
              onClick={handleNext}
              className="absolute right-0 top-16 bottom-20 w-2/3 z-20 cursor-pointer"
              title="Next story"
            />

            {/* Subtle Navigation Arrows */}
            {currentStoryIdx > 0 && (
              <button
                onClick={handlePrev}
                className="absolute left-2 top-1/2 -translate-y-1/2 z-25 p-2 rounded-full bg-black/40 text-white hover:bg-black/60 backdrop-blur-md"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
            )}
            <button
              onClick={handleNext}
              className="absolute right-2 top-1/2 -translate-y-1/2 z-25 p-2 rounded-full bg-black/40 text-white hover:bg-black/60 backdrop-blur-md"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>

          {/* Caption & Bottom Controls */}
          <div className="absolute bottom-3 left-3 right-3 z-30 flex flex-col space-y-2 pointer-events-auto">
            {currentStory?.caption && (
              <div className="bg-black/60 backdrop-blur-md px-3.5 py-2 rounded-2xl border border-white/10">
                <p className="text-xs text-white leading-relaxed font-medium">
                  {currentStory.caption}
                </p>
              </div>
            )}

            {/* Story Reply Form & Reaction Bar */}
            <form onSubmit={handleSendReply} className="flex items-center space-x-2">
              <div className="relative flex-1">
                <input
                  type="text"
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  placeholder={replySent ? '✨ Reply sent to creator!' : 'Send a reply...'}
                  disabled={replySent}
                  className="w-full px-3.5 py-2 rounded-full bg-black/60 backdrop-blur-md border border-white/20 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-spreego-violet transition-colors"
                />
                {replyText.trim() && (
                  <button
                    type="submit"
                    className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1.5 rounded-full bg-spreego-violet text-white"
                  >
                    <Send className="w-3 h-3" />
                  </button>
                )}
              </div>

              <button
                type="button"
                onClick={handleReaction}
                className={`p-2.5 rounded-full backdrop-blur-md border transition-transform active:scale-90 ${
                  hasLiked
                    ? 'bg-rose-500/30 border-rose-500 text-rose-400'
                    : 'bg-black/60 border-white/20 text-white hover:bg-black/80'
                }`}
              >
                <Heart className={`w-4 h-4 ${hasLiked ? 'fill-rose-500 text-rose-500' : ''}`} />
              </button>

              <button
                type="button"
                onClick={() => {
                  if (navigator.clipboard) {
                    navigator.clipboard.writeText(window.location.href);
                  }
                }}
                className="p-2.5 rounded-full bg-black/60 border border-white/20 text-white hover:bg-black/80 backdrop-blur-md"
              >
                <Share2 className="w-4 h-4" />
              </button>
            </form>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
