/**
 * RIE Frontend — useRepositoryContext hook
 */

import { useContext } from 'react';

import { RepositoryContext } from './RepositoryContext';
import type { Repository } from '../types/api';

export interface RepositoryState {
  currentRepoId: string | null;
  setRepo: (repo: Repository) => void;
}

export const useRepositoryContext = (): RepositoryState => {
  const ctx = useContext(RepositoryContext);
  if (!ctx) {
    throw new Error(
      'useRepositoryContext must be used within a RepositoryProvider',
    );
  }
  return ctx;
};
