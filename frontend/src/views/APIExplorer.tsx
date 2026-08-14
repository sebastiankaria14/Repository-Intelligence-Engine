import { useState, useMemo } from 'react';
import { Lock, Unlock, Search, Copy, Check } from 'lucide-react';

import NoRepository from '../components/NoRepository';
import DataShell from '../components/DataShell';
import { useCurrentRepoId, useApi } from '../hooks/useRepository';
import type { APIDiscoveryResponse } from '../types/api';
import { repositoryApi } from '../lib/api';

const methodColors: Record<string, string> = {
  GET: '#10b981',
  POST: '#6366f1',
  PUT: '#f59e0b',
  DELETE: '#f43f5e',
  PATCH: '#a855f7',
};

export default function APIExplorer() {
  const repoId = useCurrentRepoId();
  const { data, loading, error, refetch: _refetch } = useApi<APIDiscoveryResponse>(
    repoId,
    repositoryApi.getApis,
  );

  const [searchTerm, setSearchTerm] = useState('');
  const [methodFilter, setMethodFilter] = useState('ALL');
  const [copiedPath, setCopiedPath] = useState<string | null>(null);

  if (!repoId && !loading && !data) {
    return <NoRepository />;
  }

  const endpoints = data?.endpoints ?? [];

  const filteredEndpoints = useMemo(() => {
    return endpoints.filter((ep) => {
      const matchesSearch =
        !searchTerm ||
        ep.path.toLowerCase().includes(searchTerm.toLowerCase()) ||
        ep.handler.toLowerCase().includes(searchTerm.toLowerCase()) ||
        ep.file_path.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesMethod = methodFilter === 'ALL' || ep.method === methodFilter;
      return matchesSearch && matchesMethod;
    });
  }, [endpoints, searchTerm, methodFilter]);

  const handleCopy = (path: string) => {
    navigator.clipboard.writeText(path).catch(() => {});
    setCopiedPath(path);
    setTimeout(() => setCopiedPath(null), 2000);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="page-header">
        <h2 className="gradient-text">API Explorer</h2>
        <p>Discovered REST, GraphQL, gRPC, and WebSocket endpoints</p>
      </div>

      <DataShell
        loading={loading}
        error={error}
        isEmpty={endpoints.length === 0}
        emptyTitle="No endpoints discovered"
        emptyDescription="No API endpoints have been discovered yet. The analysis pipeline scans for REST, GraphQL, gRPC, and WebSocket routes."
      >
        <>
          {/* Stats */}
          <div className="stats-grid-3 mb-6">
            <div className="stat-card">
              <p className="text-[11px] text-[var(--text-muted)] mb-1 font-medium">Total Discovered Endpoints</p>
              <p className="text-2xl font-bold text-[var(--accent-blue)] font-mono">
                {data?.total ?? endpoints.length}
              </p>
            </div>
            <div className="stat-card">
              <p className="text-[11px] text-[var(--text-muted)] mb-1 font-medium">Auth Protected</p>
              <p className="text-2xl font-bold text-[var(--accent-amber)] font-mono">
                {endpoints.filter((e) => e.auth_required).length}
              </p>
            </div>
            <div className="stat-card">
              <p className="text-[11px] text-[var(--text-muted)] mb-1 font-medium">Detected Frameworks</p>
              <p className="text-base font-semibold text-[var(--accent-cyan)] capitalize">
                {data?.frameworks_detected?.length
                  ? data.frameworks_detected.join(', ')
                  : 'FastAPI / Express'}
              </p>
            </div>
          </div>

          {/* Search & Filter Bar */}
          <div className="flex flex-col sm:flex-row gap-3 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--text-muted)]" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Filter by path, handler, file..."
                className="w-full pl-10 pr-4 py-2 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)] text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] transition-colors"
              />
            </div>
            <select
              value={methodFilter}
              onChange={(e) => setMethodFilter(e.target.value)}
              className="px-4 py-2 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)] text-xs text-[var(--text-primary)]"
            >
              <option value="ALL">All Methods</option>
              <option value="GET">GET</option>
              <option value="POST">POST</option>
              <option value="PUT">PUT</option>
              <option value="DELETE">DELETE</option>
              <option value="PATCH">PATCH</option>
            </select>
          </div>

          {/* Endpoint List */}
          <div className="glass-card divide-y divide-[var(--border-subtle)] overflow-hidden">
            {filteredEndpoints.length === 0 ? (
              <div className="p-8 text-center text-xs text-[var(--text-muted)]">
                {searchTerm || methodFilter !== 'ALL'
                  ? 'No matching endpoints found.'
                  : 'No endpoints discovered yet.'}
              </div>
            ) : (
              filteredEndpoints.map((ep, idx) => {
                const color = methodColors[ep.method] || '#6366f1';
                return (
                  <div
                    key={`${ep.method}-${ep.path}-${idx}`}
                    className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 gap-2.5 hover:bg-[rgba(99,102,241,0.03)] transition-colors"
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <span
                        className="px-2 py-0.5 rounded text-[10px] font-bold font-mono min-w-[52px] text-center flex-shrink-0"
                        style={{
                          color: color,
                          background: `${color}12`,
                          border: `1px solid ${color}25`,
                        }}
                      >
                        {ep.method}
                      </span>
                      <span className="font-mono text-xs text-[var(--text-primary)] font-medium truncate">
                        {ep.path}
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-[10px] text-[var(--text-muted)] flex-shrink-0">
                      {ep.handler && (
                        <span className="font-mono bg-[var(--bg-primary)] px-2 py-0.5 rounded border border-[var(--border-subtle)] text-[var(--text-secondary)]">
                          {ep.handler}()
                        </span>
                      )}

                      <span className="truncate max-w-[160px] hidden lg:inline" title={ep.file_path}>
                        {ep.file_path}:{ep.line_number}
                      </span>

                      {ep.auth_required ? (
                        <div className="flex items-center gap-1 text-[var(--accent-amber)] font-medium" title="Authentication Required">
                          <Lock className="w-3 h-3" />
                          <span>Protected</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1 text-[var(--text-muted)]" title="Public Endpoint">
                          <Unlock className="w-3 h-3" />
                          <span>Public</span>
                        </div>
                      )}

                      <button
                        onClick={() => handleCopy(ep.path)}
                        className="p-1 rounded hover:bg-[var(--bg-primary)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
                        title="Copy endpoint path"
                      >
                        {copiedPath === ep.path ? (
                          <Check className="w-3 h-3 text-[var(--accent-green)]" />
                        ) : (
                          <Copy className="w-3 h-3" />
                        )}
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </>
      </DataShell>
    </div>
  );
}
