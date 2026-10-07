import { useRef, useCallback } from 'react';
import confetti from 'canvas-confetti';

interface UseHapticClapOptions {
  onClap?: (count: number) => void;
}

export function useHapticClap(options?: UseHapticClapOptions) {
  const lastTapRef = useRef<number>(0);

  const triggerClapBurst = useCallback((originX: number = 0.5, originY: number = 0.5) => {
    // Haptic feedback if supported
    if (typeof navigator !== 'undefined' && 'vibrate' in navigator) {
      try {
        navigator.vibrate([15, 30, 15]);
      } catch {
        // Ignore haptic errors on unsupported environments
      }
    }

    // Kinetic particle burst with Taste-Design calibrated colors
    try {
      confetti({
        particleCount: 28,
        spread: 60,
        startVelocity: 35,
        origin: { x: originX, y: originY },
        colors: ['#7C3AED', '#8B5CF6', '#F5D061', '#FFFFFF'],
        ticks: 120,
        gravity: 1.1,
        scalar: 0.9,
        disableForReducedMotion: true,
      });
    } catch (e) {
      console.warn('[HapticClap] Canvas confetti burst failed:', e);
    }

    if (options?.onClap) {
      options.onClap(1);
    }
  }, [options]);

  const handleDoubleTap = useCallback(
    (e: React.MouseEvent<HTMLElement> | React.TouchEvent<HTMLElement>) => {
      const now = Date.now();
      const DOUBLE_TAP_DELAY = 300; // ms

      if (now - lastTapRef.current < DOUBLE_TAP_DELAY) {
        // Double tap confirmed
        let x = 0.5;
        let y = 0.5;

        if ('clientX' in e && window.innerWidth > 0 && window.innerHeight > 0) {
          x = e.clientX / window.innerWidth;
          y = e.clientY / window.innerHeight;
        } else if ('touches' in e && e.touches.length > 0 && window.innerWidth > 0 && window.innerHeight > 0) {
          x = e.touches[0].clientX / window.innerWidth;
          y = e.touches[0].clientY / window.innerHeight;
        }

        triggerClapBurst(x, y);
        lastTapRef.current = 0;
        return true;
      } else {
        lastTapRef.current = now;
        return false;
      }
    },
    [triggerClapBurst]
  );

  return {
    triggerClapBurst,
    handleDoubleTap,
  };
}
