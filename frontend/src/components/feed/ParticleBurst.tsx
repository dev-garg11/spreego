import confetti from 'canvas-confetti';

export const triggerClapConfetti = (x?: number, y?: number) => {
  const originX = x ? x / window.innerWidth : 0.85;
  const originY = y ? y / window.innerHeight : 0.6;

  confetti({
    particleCount: 28,
    spread: 60,
    origin: { x: originX, y: originY },
    colors: ['#7C3AED', '#8B5CF6', '#F5D061', '#FFFFFF'],
    ticks: 120,
    gravity: 1.2,
    scalar: 0.9,
    disableForReducedMotion: true,
  });

  if (typeof navigator !== 'undefined' && 'vibrate' in navigator) {
    try {
      navigator.vibrate([15, 30, 15]);
    } catch {
      // Ignore vibration errors
    }
  }
};

