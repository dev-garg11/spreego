import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { SpreeItem, FeedSubTab } from '../../types';
import { feedApi } from '../../api/client';
import { ReelCard } from './ReelCard';
import { ChevronUp, ChevronDown, MousePointerClick } from 'lucide-react';

interface ReelFeedProps {
  subTab: FeedSubTab;
  onExploreSponsored?: () => void;
}

export const ReelFeed: React.FC<ReelFeedProps> = ({ subTab, onExploreSponsored }) => {
  const [sprees, setSprees] = useState<SpreeItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [direction, setDirection] = useState<number>(1);
  const [loading, setLoading] = useState(true);
  const [showScrollHint, setShowScrollHint] = useState(true);

  const containerRef = useRef<HTMLDivElement>(null);
  const isScrollingRef = useRef(false);
  const touchStartY = useRef<number | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    feedApi.getFeed(subTab).then((items) => {
      if (mounted) {
        setSprees(items);
        setCurrentIndex(0);
        setDirection(1);
        setShowScrollHint(true);
        setLoading(false);
      }
    });
    return () => {
      mounted = false;
    };
  }, [subTab]);

  const handleNext = useCallback(() => {
    if (currentIndex < sprees.length - 1) {
      setDirection(1);
      setCurrentIndex((prev) => prev + 1);
      setShowScrollHint(false);
    }
  }, [currentIndex, sprees.length]);

  const handlePrev = useCallback(() => {
    if (currentIndex > 0) {
      setDirection(-1);
      setCurrentIndex((prev) => prev - 1);
      setShowScrollHint(false);
    }
  }, [currentIndex]);

  const goToReel = useCallback((index: number) => {
    if (index === currentIndex) return;
    setDirection(index > currentIndex ? 1 : -1);
    setCurrentIndex(index);
    setShowScrollHint(false);
  }, [currentIndex]);

  // Wheel scroll handler with cooldown debounce
  const handleWheel = useCallback((e: React.WheelEvent) => {
    if (isScrollingRef.current) return;
    if (Math.abs(e.deltaY) < 20) return;

    isScrollingRef.current = true;
    if (e.deltaY > 0) {
      handleNext();
    } else {
      handlePrev();
    }

    setTimeout(() => {
      isScrollingRef.current = false;
    }, 380);
  }, [handleNext, handlePrev]);

  // Touch swipe gesture handlers
  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartY.current = e.touches[0].clientY;
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (touchStartY.current === null) return;
    const deltaY = touchStartY.current - e.changedTouches[0].clientY;
    touchStartY.current = null;

    if (Math.abs(deltaY) < 40) return;

    if (deltaY > 0) {
      handleNext();
    } else {
      handlePrev();
    }
  };

  // Keyboard navigation (ArrowDown / ArrowUp / PageDown / PageUp)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (['ArrowDown', 'PageDown', 'j', 'J'].includes(e.key)) {
        e.preventDefault();
        handleNext();
      } else if (['ArrowUp', 'PageUp', 'k', 'K'].includes(e.key)) {
        e.preventDefault();
        handlePrev();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleNext, handlePrev]);

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center space-y-3 min-h-[70vh]">
        <div className="w-8 h-8 rounded-full border-2 border-spreego-violet border-t-transparent animate-spin" />
        <span className="text-xs text-spreego-text-secondary">Loading Sprees...</span>
      </div>
    );
  }

  if (sprees.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center min-h-[70vh] space-y-2">
        <p className="text-sm font-semibold text-white">No sprees available in this feed</p>
        <p className="text-xs text-spreego-text-secondary">Check back later or switch sub-tabs</p>
      </div>
    );
  }

  const currentSpree = sprees[currentIndex];

  const variants = {
    enter: (dir: number) => ({
      y: dir > 0 ? 120 : -120,
      opacity: 0,
      scale: 0.98,
    }),
    center: {
      y: 0,
      opacity: 1,
      scale: 1,
    },
    exit: (dir: number) => ({
      y: dir > 0 ? -120 : 120,
      opacity: 0,
      scale: 0.98,
    }),
  };

  return (
    <div
      ref={containerRef}
      onWheel={handleWheel}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      tabIndex={0}
      aria-label="Reels feed viewer"
      className="relative w-full flex-1 flex flex-col items-center justify-center outline-none select-none overflow-hidden"
    >
      {/* Kinetic Animated Active Reel */}
      <AnimatePresence mode="popLayout" custom={direction}>
        <motion.div
          key={currentSpree.id}
          custom={direction}
          variants={variants}
          initial="enter"
          animate="center"
          exit="exit"
          transition={{
            y: { type: 'spring', stiffness: 280, damping: 28 },
            opacity: { duration: 0.2 },
            scale: { duration: 0.2 },
          }}
          className="w-full h-full flex items-center justify-center"
        >
          <ReelCard
            spree={currentSpree}
            isActive={true}
            onExploreSponsored={onExploreSponsored}
          />
        </motion.div>
      </AnimatePresence>

      {/* Vertical Segmented Progress Pill Indicator (Right Rail) */}
      <div className="absolute right-3 top-1/2 -translate-y-1/2 z-30 flex flex-col items-center space-y-3 pointer-events-auto">
        {/* Navigation Step Buttons */}
        <button
          onClick={handlePrev}
          disabled={currentIndex === 0}
          aria-label="Previous reel"
          className="p-2 rounded-full bg-black/50 backdrop-blur-md border border-white/10 text-white disabled:opacity-20 hover:bg-spreego-violet/80 hover:border-spreego-violet transition-all active:scale-90"
        >
          <ChevronUp className="w-4 h-4" />
        </button>

        {/* Segmented Dots Indicator */}
        <div className="flex flex-col items-center space-y-1.5 py-2 px-1 rounded-full bg-black/40 backdrop-blur-md border border-white/5">
          {sprees.map((s, idx) => (
            <button
              key={s.id}
              onClick={() => goToReel(idx)}
              aria-label={`Go to reel ${idx + 1}`}
              className={`rounded-full transition-all duration-300 ${
                idx === currentIndex
                  ? 'w-1.5 h-4 bg-spreego-violet shadow-sm shadow-spreego-violet'
                  : 'w-1.5 h-1.5 bg-white/20 hover:bg-white/50'
              }`}
            />
          ))}
        </div>

        <button
          onClick={handleNext}
          disabled={currentIndex === sprees.length - 1}
          aria-label="Next reel"
          className="p-2 rounded-full bg-black/50 backdrop-blur-md border border-white/10 text-white disabled:opacity-20 hover:bg-spreego-violet/80 hover:border-spreego-violet transition-all active:scale-90"
        >
          <ChevronDown className="w-4 h-4" />
        </button>
      </div>

      {/* Subtle First-Time Scroll Hint (Bouncing Pill) */}
      {currentIndex === 0 && showScrollHint && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: [0, -6, 0] }}
          transition={{
            y: { repeat: Infinity, duration: 1.8, ease: 'easeInOut' },
            opacity: { duration: 0.3 },
          }}
          onClick={handleNext}
          className="absolute bottom-6 z-30 cursor-pointer flex items-center space-x-1.5 px-3 py-1.5 rounded-full bg-black/60 backdrop-blur-md border border-white/15 text-white/80 hover:text-white text-[11px] font-medium shadow-lg hover:border-spreego-violet/50 transition-colors"
        >
          <MousePointerClick className="w-3.5 h-3.5 text-spreego-violet" />
          <span>Scroll or Swipe for next reel</span>
          <ChevronDown className="w-3.5 h-3.5" />
        </motion.div>
      )}
    </div>
  );
};
