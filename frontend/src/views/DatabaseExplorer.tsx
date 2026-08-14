import { Database, Table, Key, ArrowRight } from 'lucide-react';

import NoRepository from '../components/NoRepository';
import DataShell from '../components/DataShell';
import { useCurrentRepoId, useApi } from '../hooks/useRepository';
import type { DatabaseResponse } from '../types/api';
import { repositoryApi } from '../lib/api';

export default function DatabaseExplorer() {
  const repoId = useCurrentRepoId();
  const { data, loading, error, refetch: _refetch } = useApi<DatabaseResponse>(
    repoId,
    repositoryApi.getDatabase,
  );

  if (!repoId && !loading && !data) {
    return <NoRepository />;
  }

  const tables = data?.tables ?? [];

  const foreignKeyCount = tables.reduce(
    (sum: number, t: any) => sum + (t.foreign_keys?.length ?? 0),
    0,
  );

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="page-header">
        <h2 className="gradient-text">Database Explorer</h2>
        <p>Discovered tables, relationships, and migration history</p>
      </div>

      <DataShell
        loading={loading}
        error={error}
        isEmpty={tables.length === 0}
        emptyTitle="No database schema discovered"
        emptyDescription="No ORM models, migrations, or raw DDL were detected in this repository."
      >
        <>
          {/* Stats */}
          <div className="stats-grid-3 mb-6">
            <div className="stat-card">
              <div className="flex items-center gap-2 mb-2">
                <Table className="w-3.5 h-3.5 text-[var(--accent-blue)]" />
                <span className="text-[11px] text-[var(--text-muted)] font-medium">Tables</span>
              </div>
              <p className="text-2xl font-bold text-[var(--accent-blue)]">
                {tables.length}
              </p>
            </div>
            <div className="stat-card">
              <div className="flex items-center gap-2 mb-2">
                <Key className="w-3.5 h-3.5 text-[var(--accent-purple)]" />
                <span className="text-[11px] text-[var(--text-muted)] font-medium">Foreign Keys</span>
              </div>
              <p className="text-2xl font-bold text-[var(--accent-purple)]">
                {foreignKeyCount}
              </p>
            </div>
            <div className="stat-card">
              <div className="flex items-center gap-2 mb-2">
                <Database className="w-3.5 h-3.5 text-[var(--accent-green)]" />
                <span className="text-[11px] text-[var(--text-muted)] font-medium">Migrations</span>
              </div>
              <p className="text-xl font-semibold text-[var(--accent-green)]">
                {data?.migrations?.length ?? 0}
              </p>
            </div>
          </div>

          {/* Table Cards */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {tables.map((table) => (
              <div key={table.name} className="glass-card p-5 flex flex-col">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-7 h-7 rounded-lg bg-[rgba(6,182,212,0.1)] flex items-center justify-center border border-[rgba(6,182,212,0.2)] flex-shrink-0">
                    <Table className="w-3.5 h-3.5 text-[var(--accent-cyan)]" />
                  </div>
                  <h3 className="font-semibold font-mono text-sm text-[var(--accent-cyan)] truncate">
                    {table.name}
                  </h3>
                  {table.orm_model && (
                    <span className="text-[10px] text-[var(--text-muted)] flex-shrink-0">
                      ({table.orm_model})
                    </span>
                  )}
                </div>

                <div className="space-y-0.5 mb-4 max-h-40 overflow-y-auto pr-1">
                  {table.columns.map((col) => (
                    <p
                      key={col.name}
                      className="text-[11px] font-mono text-[var(--text-secondary)] pl-2.5 border-l-2 border-[var(--border-subtle)] py-0.5"
                    >
                      {col.name}:{' '}
                      <span className="text-[var(--text-muted)]">{col.type}</span>
                      <span className="text-[var(--text-muted)] opacity-60">
                        {col.nullable ? ' (nullable)' : ' (not null)'}
                      </span>
                    </p>
                  ))}
                </div>

                {table.foreign_keys.length > 0 && (
                  <div className="border-t border-[var(--border-subtle)] pt-3 mb-3">
                    <p className="text-[10px] text-[var(--text-muted)] mb-1.5 font-medium uppercase tracking-wider">
                      Foreign Keys
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {table.foreign_keys.map((fk, i) => (
                        <span
                          key={i}
                          className="inline-flex items-center gap-1 text-[10px] text-[var(--accent-purple)] bg-[rgba(168,85,247,0.06)] px-2 py-0.5 rounded border border-[rgba(168,85,247,0.15)]"
                        >
                          <ArrowRight className="w-2.5 h-2.5" />
                          {fk.column} → {fk.referenced_table}.{fk.referenced_column}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {table.indexes.length > 0 && (
                  <div className="border-t border-[var(--border-subtle)] pt-3 mt-auto">
                    <p className="text-[10px] text-[var(--text-muted)] mb-1.5 font-medium uppercase tracking-wider">Indexes</p>
                    <div className="flex flex-wrap gap-1">
                      {table.indexes.map((idx, i) => (
                        <span
                          key={i}
                          className="text-[10px] text-[var(--accent-cyan)] bg-[rgba(6,182,212,0.06)] px-2 py-0.5 rounded border border-[rgba(6,182,212,0.12)]"
                        >
                          {idx}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Relationships */}
          {data?.relationships && data.relationships.length > 0 && (
            <div className="glass-card p-5 mt-4">
              <h3 className="text-sm font-semibold mb-3 text-[var(--text-primary)]">Relationships</h3>
              <div className="space-y-1.5">
                {data.relationships.map((rel, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 text-xs text-[var(--text-secondary)]"
                  >
                    <span className="font-mono text-[var(--accent-cyan)]">{rel.from_table}</span>
                    <ArrowRight className="w-3 h-3 text-[var(--accent-purple)]" />
                    <span className="font-mono text-[var(--accent-cyan)]">{rel.to_table}</span>
                    <span className="text-[10px] text-[var(--text-muted)] bg-[var(--bg-primary)] px-1.5 py-0.5 rounded">
                      {rel.type}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      </DataShell>
    </div>
  );
}
