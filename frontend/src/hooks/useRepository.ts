/**
 * RIE Frontend — Data-fetching hooks
 * Connects views to the backend API with loading/error state.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { AxiosResponse } from 'axios';

import type { Repository, ScanJob } from '../types/api';
import { useRepositorySummary } from './useRepositorySummary';

export function useCurrentRepoId(): string | null {
  const [searchParams] = useSearchParams();
  return searchParams.get('repo');
}

export function useRepository(repoId: string | null) {
  const { data: summary, loading, error, refetch } = useRepositorySummary(repoId);

  const repository: Repository | null = summary?.repository ?? null;
  const scanJob: ScanJob | null = summary?.scan_job ?? null;

  return { repository, scanJob, loading, error, refetch };
}

export function useApi<T>(
  repoId: string | null,
  fn: (id: string) => Promise<AxiosResponse<T>>,
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fnRef = useRef(fn);
  fnRef.current = fn;

  const fetch = useCallback(async () => {
    if (!repoId) {
      setData(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fnRef.current(repoId);
      setData(res.data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load data';
      setError(message);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [repoId]);

  useEffect(() => {
    void fetch();
  }, [fetch]);

  return { data, loading, error, refetch: fetch };
}
