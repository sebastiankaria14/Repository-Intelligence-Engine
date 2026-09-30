import React, { createContext, useState, useCallback } from 'react';

interface ModalContextType {
  isRepositoryModalOpen: boolean;
  openRepositoryModal: () => void;
  closeRepositoryModal: () => void;
}

export const ModalContext = createContext<ModalContextType | undefined>(undefined);

export const ModalProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [isRepositoryModalOpen, setIsRepositoryModalOpen] = useState(false);

  const openRepositoryModal = useCallback(() => {
    setIsRepositoryModalOpen(true);
  }, []);

  const closeRepositoryModal = useCallback(() => {
    setIsRepositoryModalOpen(false);
  }, []);

  return (
    <ModalContext.Provider
      value={{
        isRepositoryModalOpen,
        openRepositoryModal,
        closeRepositoryModal,
      }}
    >
      {children}
    </ModalContext.Provider>
  );
};

export const useModal = (): ModalContextType => {
  const context = React.useContext(ModalContext);
  if (!context) {
    return {
      isRepositoryModalOpen: false,
      openRepositoryModal: () => {},
      closeRepositoryModal: () => {},
    };
  }
  return context;
};
