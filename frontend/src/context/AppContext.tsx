import React, { createContext, useContext, useState } from 'react';
import { ShellTab, ModalType } from '../types';

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

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 3000);
  };

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
