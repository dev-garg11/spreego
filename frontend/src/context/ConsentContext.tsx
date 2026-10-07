import React, { createContext, useContext, useState, useEffect } from 'react';

const STORAGE_KEY = 'spreego_consent_accepted';
const CURRENT_VERSION = 'v1.0';

interface ConsentContextType {
  hasAccepted: boolean;
  isLoading: boolean;
  acceptConsent: () => void;
  declineConsent: () => void;
  resetConsent: () => void;
}

const ConsentContext = createContext<ConsentContextType | undefined>(undefined);

export const ConsentProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [hasAccepted, setHasAccepted] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        setHasAccepted(true);
      }
    } catch (e) {
      console.warn('[ConsentGuard] Could not read localStorage:', e);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const acceptConsent = () => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        accepted: true,
        version: CURRENT_VERSION,
        timestamp: new Date().toISOString(),
      }));
    } catch (e) {
      console.warn('[ConsentGuard] Could not write to localStorage:', e);
    }
    setHasAccepted(true);
  };

  const declineConsent = () => {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (e) {
      console.warn('[ConsentGuard] Could not remove localStorage key:', e);
    }
    setHasAccepted(false);
  };

  const resetConsent = () => {
    declineConsent();
  };

  return (
    <ConsentContext.Provider value={{ hasAccepted, isLoading, acceptConsent, declineConsent, resetConsent }}>
      {children}
    </ConsentContext.Provider>
  );
};

export const useConsent = (): ConsentContextType => {
  const context = useContext(ConsentContext);
  if (!context) {
    throw new Error('useConsent must be used within a ConsentProvider');
  }
  return context;
};
