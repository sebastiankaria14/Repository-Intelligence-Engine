/**
 * RIE Frontend — Repository Context
 * Tracks the currently selected repository across the application.
 * The active repo id is kept in the URL (?repo=...) so views can read it.
 */

import { createContext, useCallback, type ReactNode } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import type { Repository } from '../types/api';
import type { RepositoryState } from './useRepositoryContext';

export const RepositoryContext = createContext<RepositoryState | undefined>(undefined);

export function RepositoryProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const currentRepoId = searchParams.get('repo');

  const setRepo = useCallback(
    (repo: Repository) => {
      navigate(`/overview?repo=${repo.id}`, { replace: true });
    },
    [navigate],
  );

  const value = { currentRepoId, setRepo };
  return (
    <RepositoryContext.Provider value={value}>{children}</RepositoryContext.Provider>
  );
}
