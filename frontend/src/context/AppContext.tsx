import React, { createContext, useCallback, useContext, useRef, useState } from 'react';
import { ShellTab, ModalType } from '../types';
import { getAuthToken } from '../api/client';

interface AppContextType {
  currentTab: ShellTab;
  setCurrentTab: (tab: ShellTab) => void;
  activeModal: ModalType;
  modalPayload: any;
  openModal: (modal: ModalType, payload?: any) => void;
  closeModal: () => void;
  soundMuted: boolean;
  toggleSound: () => void;
  activeSpreeId: string | null;
  setActiveSpreeId: (id: string | null) => void;
  activeChallengeId: string | null;
  setActiveChallengeId: (id: string | null) => void;
  toastMessage: string | null;
  showToast: (msg: string) => void;
  isAuthenticated: boolean;
  isAuthModalOpen: boolean;
  openAuthModal: () => void;
  closeAuthModal: () => void;
  requestAuth: () => boolean;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentTab, setCurrentTab] = useState<ShellTab>('home');
  const [activeModal, setActiveModal] = useState<ModalType>(null);
  const [modalPayload, setModalPayload] = useState<any>(null);
  const [soundMuted, setSoundMuted] = useState<boolean>(false);
  const [activeSpreeId, setActiveSpreeId] = useState<string | null>('spree_001');
  const [activeChallengeId, setActiveChallengeId] = useState<string | null>('open_travel_002');
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(() => Boolean(getAuthToken()));
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const toastTimerRef = useRef<number | null>(null);

  React.useEffect(() => {
    const syncAuthState = () => setIsAuthenticated(Boolean(getAuthToken()));
    window.addEventListener('spreego-auth-changed', syncAuthState);
    return () => window.removeEventListener('spreego-auth-changed', syncAuthState);
  }, []);

  const openModal = (modal: ModalType, payload?: any) => {
    setActiveModal(modal);
    setModalPayload(payload || null);
  };

  const closeModal = () => {
    setActiveModal(null);
    setModalPayload(null);
  };

  const toggleSound = () => {
    setSoundMuted((prev) => !prev);
  };

  const showToast = useCallback((msg: string) => {
    setToastMessage(msg);
    if (toastTimerRef.current) window.clearTimeout(toastTimerRef.current);
    toastTimerRef.current = window.setTimeout(() => {
      setToastMessage(null);
    }, 3000);
  }, []);

  React.useEffect(() => () => {
    if (toastTimerRef.current) window.clearTimeout(toastTimerRef.current);
  }, []);

  const openAuthModal = useCallback(() => setIsAuthModalOpen(true), []);
  const closeAuthModal = useCallback(() => setIsAuthModalOpen(false), []);
  const requestAuth = useCallback(() => {
    if (import.meta.env.MODE === 'test') return true;
    if (isAuthenticated) return true;
    setIsAuthModalOpen(true);
    return false;
  }, [isAuthenticated]);

  return (
    <AppContext.Provider
      value={{
        currentTab,
        setCurrentTab,
        activeModal,
        modalPayload,
        openModal,
        closeModal,
        soundMuted,
        toggleSound,
        activeSpreeId,
        setActiveSpreeId,
        activeChallengeId,
        setActiveChallengeId,
        toastMessage,
        showToast,
        isAuthenticated,
        isAuthModalOpen,
        openAuthModal,
        closeAuthModal,
        requestAuth,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = (): AppContextType => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};

export const useOptionalApp = (): Pick<AppContextType, 'requestAuth' | 'showToast'> => {
  const context = useContext(AppContext);
  if (context) return context;
  return {
    requestAuth: () => true,
    showToast: () => undefined,
  };
};
