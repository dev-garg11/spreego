import { useEffect, useRef, useCallback } from 'react';
import { feedApi } from '../api/client';

export function useTelemetry(spreeId: string | null) {
  const startTimeRef = useRef<number>(Date.now());
  const currentSpreeIdRef = useRef<string | null>(spreeId);
  const lastSentAtRef = useRef(0);

  // Sync ref
  useEffect(() => {
    currentSpreeIdRef.current = spreeId;
    startTimeRef.current = Date.now();
    lastSentAtRef.current = 0;
  }, [spreeId]);

  const sendTelemetryBeacon = useCallback((isCompleted: boolean = false) => {
    if (!currentSpreeIdRef.current) return;
    const now = Date.now();
    if (now - lastSentAtRef.current < 1000) return;
    lastSentAtRef.current = now;
    const durationSeconds = Math.max(0.1, (now - startTimeRef.current) / 1000);
    // Send telemetry to backend without doing client-side ranking calculations
    feedApi.sendViewTelemetry({
      spree_id: currentSpreeIdRef.current,
      watch_duration: Math.round(durationSeconds * 10) / 10,
      completed: isCompleted,
      device_info: typeof navigator !== 'undefined' ? navigator.userAgent : 'Web Browser',
    }, { keepalive: true });
  }, []);

  const recordSkip = useCallback((id: string) => {
    if (!id) return;
    feedApi.sendViewTelemetry({
      spree_id: id,
      watch_duration: 0.5,
      completed: false,
      device_info: 'Skip Event',
    });
  }, []);

  useEffect(() => {
    const handleBeforeUnload = () => {
      sendTelemetryBeacon(false);
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'hidden') sendTelemetryBeacon(false);
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      sendTelemetryBeacon(false);
    };
  }, [sendTelemetryBeacon]);

  return {
    recordWatchDuration: (seconds: number, completed = false) => {
      if (!currentSpreeIdRef.current) return;
      feedApi.sendViewTelemetry({
        spree_id: currentSpreeIdRef.current,
        watch_duration: seconds,
        completed,
      });
    },
    recordSkip,
    sendTelemetryBeacon,
  };
}
