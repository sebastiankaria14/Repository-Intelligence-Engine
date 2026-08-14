/**
 * RIE Frontend — Repository Summary Hook
 * Unified data fetching with caching, polling, and error recovery.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { repositoryApi } from '../lib/api';
import type { RepositorySummary } from '../types/api';

const POLL_INTERVAL_MS = 3000;
const CACHE_TTL_MS = 30_000;

interface CachedEntry {
  data: RepositorySummary;
  timestamp: number;
}

const summaryCache = new Map<string, CachedEntry>();

export function useRepositorySummary(repoId: string | null) {
  const [data, setData] = useState<RepositorySummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  const fetchSummary = useCallback(async () => {
    if (!repoId) {
      setData(null);
      setLoading(false);
      return;
    }

    const cached = summaryCache.get(repoId);
    if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
      setData(cached.data);
      setLoading(false);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await repositoryApi.getSummary(repoId);
      if (mountedRef.current) {
        setData(result);
        setError(null);
        summaryCache.set(repoId, { data: result, timestamp: Date.now() });
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load repository data';
      if (mountedRef.current) {
        setError(message);
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [repoId]);

  useEffect(() => {
    mountedRef.current = true;
    void fetchSummary();

    if (repoId) {
      pollRef.current = setInterval(() => {
        const cached = summaryCache.get(repoId);
        if (cached) {
          const scanStatus = cached.data.scan_job?.status;
          if (scanStatus && ['completed', 'failed'].includes(scanStatus)) {
            if (pollRef.current) clearInterval(pollRef.current);
            return;
          }
        }
        void fetchSummary();
      }, POLL_INTERVAL_MS);
    }

    return () => {
      mountedRef.current = false;
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [repoId, fetchSummary]);

  const refetch = useCallback(() => {
    if (repoId) {
      summaryCache.delete(repoId);
    }
    void fetchSummary();
  }, [repoId, fetchSummary]);

  return { data, loading, error, refetch };
}
