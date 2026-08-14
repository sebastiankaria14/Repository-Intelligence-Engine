import { Package, AlertTriangle } from 'lucide-react';

import NoRepository from '../components/NoRepository';
import DataShell from '../components/DataShell';
import { useCurrentRepoId, useApi } from '../hooks/useRepository';
import type { DependencyResponse } from '../types/api';
import { repositoryApi } from '../lib/api';

const typeColors: Record<string, string> = {
  runtime: 'var(--accent-green)',
  dev: 'var(--accent-cyan)',
  peer: 'var(--accent-purple)',
};

export default function DependencyExplorer() {
  const repoId = useCurrentRepoId();
  const { data, loading, error, refetch: _refetch } = useApi<DependencyResponse>(
    repoId,
    repositoryApi.getDependencies,
  );

  if (!repoId && !loading && !data) {
    return <NoRepository />;
  }

  const dependencies = data?.packages ?? [];
  const circularDeps = data?.circular_dependencies ?? [];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="page-header">
        <h2 className="gradient-text">Dependency Explorer</h2>
        <p>Runtime dependencies, service graph, and impact analysis</p>
      </div>

      <DataShell
        loading={loading}
        error={error}
        isEmpty={dependencies.length === 0 && circularDeps.length === 0}
        emptyTitle="No dependencies discovered"
        emptyDescription="No package manifests (package.json, requirements.txt, pom.xml, etc.) were found."
      >
        <>
          {/* Stats */}
          <div className="stats-grid-2 mb-6">
            <div className="stat-card">
              <div className="flex items-center gap-2 mb-2">
                <Package className="w-3.5 h-3.5 text-[var(--accent-blue)]" />
                <span className="text-[11px] text-[var(--text-muted)] font-medium">
                  Total Packages
                </span>
              </div>
              <p className="text-2xl font-bold text-[var(--accent-blue)]">
                {data?.total ?? dependencies.length}
              </p>
            </div>
            <div className="stat-card">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-3.5 h-3.5 text-[var(--accent-amber)]" />
                <span className="text-[11px] text-[var(--text-muted)] font-medium">
                  Circular Deps
                </span>
              </div>
              <p className="text-2xl font-bold text-[var(--accent-amber)]">
                {circularDeps.length}
              </p>
            </div>
          </div>

          {/* Circular Dependencies */}
          {circularDeps.length > 0 && (
            <div className="glass-card p-5 mb-4">
              <h3 className="text-sm font-semibold mb-3 flex items-center gap-2 text-[var(--text-primary)]">
                <div className="w-6 h-6 rounded-md bg-[rgba(244,63,94,0.1)] flex items-center justify-center border border-[rgba(244,63,94,0.2)]">
                  <AlertTriangle className="w-3 h-3 text-[var(--accent-rose)]" />
                </div>
                Circular Dependencies
              </h3>
              <div className="space-y-2">
                {circularDeps.map((cycle, i) => (
                  <div
                    key={i}
                    className="text-xs font-mono text-[var(--accent-rose)] bg-[rgba(244,63,94,0.04)] px-3 py-2 rounded-lg border border-[rgba(244,63,94,0.1)]"
                  >
                    {cycle.join(' → ')} → {cycle[0]}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Dependency Table */}
          <div className="glass-card table-container overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[var(--border-color)]">
                  <th className="text-left p-3.5 text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider">
                    Package
                  </th>
                  <th className="text-left p-3.5 text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider">
                    Version
                  </th>
                  <th className="text-left p-3.5 text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider">
                    Type
                  </th>
                  <th className="text-left p-3.5 text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider">
                    Source
                  </th>
                </tr>
              </thead>
              <tbody className="row-striped">
                {dependencies.map((dep) => (
                  <tr
                    key={`${dep.source}-${dep.name}`}
                    className="border-b border-[var(--border-subtle)] hover:bg-[rgba(99,102,241,0.04)] transition-colors"
                  >
                    <td className="p-3.5">
                      <span className="font-mono text-xs text-[var(--accent-cyan)] font-medium">
                        {dep.name}
                      </span>
                    </td>
                    <td className="p-3.5 text-xs text-[var(--text-secondary)]">
                      {dep.version ?? '—'}
                    </td>
                    <td className="p-3.5">
                      <span
                        className="badge"
                        style={{
                          color: typeColors[dep.type] || 'var(--text-secondary)',
                          background: `${typeColors[dep.type] || '#64748b'}12`,
                          border: `1px solid ${typeColors[dep.type] || '#64748b'}20`,
                        }}
                      >
                        {dep.type}
                      </span>
                    </td>
                    <td className="p-3.5 text-xs font-mono text-[var(--text-muted)]">
                      {dep.source}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      </DataShell>
    </div>
  );
}
