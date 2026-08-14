import {
  FileCode,
  GitCommit,
  Users,
  TrendingUp,
  AlertTriangle,
  Shield,
  Clock,
  CheckCircle,
  Download,
  Zap,
  Layers,
} from 'lucide-react';

import NoRepository from '../components/NoRepository';
import { useCurrentRepoId, useRepository, useApi } from '../hooks/useRepository';
import type { ArchitectureResponse, SecurityResponse, PerformanceResponse, TechnicalDebtResponse } from '../types/api';
import { repositoryApi } from '../lib/api';

const scanPhaseLabels: Record<string, string> = {
  queued: 'Queued',
  clone: 'Cloning',
  parse: 'Parsing AST',
  graph: 'Building Graph',
  analysis: 'Running Analysis',
  embed: 'Generating Embeddings',
  index: 'Indexing Codebase',
  done: 'Completed',
};

export default function Overview() {
  const repoId = useCurrentRepoId();
  const { repository, scanJob, loading: repoLoading, error: repoError, refetch } = useRepository(repoId);

  const { data: architecture } = useApi<ArchitectureResponse>(
    repoId,
    repositoryApi.getArchitecture,
  );
  const { data: security } = useApi<SecurityResponse>(
    repoId,
    repositoryApi.getSecurity,
  );
  const { data: performance } = useApi<PerformanceResponse>(
    repoId,
    repositoryApi.getPerformance,
  );
  const { data: techDebt } = useApi<TechnicalDebtResponse>(
    repoId,
    repositoryApi.getTechnicalDebt,
  );

  if (!repoId && !repoLoading && !repository) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="page-header">
          <h2 className="gradient-text">Repository Overview</h2>
          <p>Comprehensive intelligence & health snapshot of your codebase</p>
        </div>
        <NoRepository />
      </div>
    );
  }

  if (repoError && !repository) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="page-header">
          <h2 className="gradient-text">Repository Overview</h2>
          <p>Comprehensive intelligence & health snapshot of your codebase</p>
        </div>
        <div className="glass-card p-5 border-l-4 border-[var(--accent-rose)]">
          <p className="text-[var(--accent-rose)] font-semibold text-sm mb-1">Failed to load repository</p>
          <p className="text-xs text-[var(--text-muted)]">{repoError}</p>
          <button onClick={refetch} className="btn-secondary text-xs mt-3">Retry</button>
        </div>
      </div>
    );
  }

  const repo = repository;

  const securityCount = security?.findings?.length ?? 0;
  const perfCount = performance?.findings?.length ?? 0;
  const debtScore = techDebt?.debt_score ?? null;

  const stats = repo
    ? [
        {
          label: 'Total Files',
          value: (repo.total_files ?? 0).toLocaleString(),
          icon: FileCode,
          color: 'var(--accent-blue)',
        },
        {
          label: 'Total Lines',
          value: (repo.total_lines ?? 0).toLocaleString(),
          icon: GitCommit,
          color: 'var(--accent-cyan)',
        },
        {
          label: 'Languages',
          value: `${repo.languages?.length ?? 0}`,
          icon: Users,
          color: 'var(--accent-purple)',
        },
        {
          label: 'Health Score',
          value:
            repo.health_score != null
              ? `${Math.round(repo.health_score)}/100`
              : 'Pending',
          icon: TrendingUp,
          color:
            repo.health_score != null && repo.health_score >= 60
              ? 'var(--accent-green)'
              : 'var(--accent-amber)',
        },
        {
          label: 'Security Findings',
          value: `${securityCount}`,
          icon: Shield,
          color: securityCount > 0 ? 'var(--accent-rose)' : 'var(--accent-green)',
        },
        {
          label: 'Tech Debt Score',
          value: debtScore != null ? `${debtScore}` : '—',
          icon: AlertTriangle,
          color: debtScore && debtScore > 30 ? 'var(--accent-amber)' : 'var(--accent-cyan)',
        },
      ]
    : [];

  const scanProgress = scanJob ? Math.round(scanJob.progress) : 0;
  const scanStatus = scanJob?.status ?? 'pending';

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="page-header">
          <h2 className="gradient-text">
            {repo ? repo.name : 'Repository Overview'}
          </h2>
          <p>{repo?.github_url ? repo.github_url : 'Comprehensive health snapshot of your codebase'}</p>
        </div>
        {repo && (
          <button
            onClick={() => {
              const url = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'}/api/repositories/${repo.id}/graph`;
              window.open(url, '_blank');
            }}
            className="btn-secondary text-xs flex items-center gap-2 flex-shrink-0"
          >
            <Download className="w-3.5 h-3.5" />
            Export Graph
          </button>
        )}
      </div>

      {repoLoading && !repo && (
        <div className="flex items-center gap-3 p-5 glass-card text-[var(--text-muted)]">
          <div className="w-4 h-4 border-2 border-[var(--accent-blue)] border-t-transparent rounded-full animate-spin" />
          <span className="text-sm">Loading repository metrics…</span>
        </div>
      )}

      {/* Metadata Pills */}
      {repo && (
        <div className="flex flex-wrap items-center gap-1.5">
          {repo.default_branch && (
            <span className="px-2.5 py-1 rounded-full bg-[rgba(99,102,241,0.1)] text-[10px] font-mono text-[var(--accent-blue)] border border-[var(--border-color)]">
              branch: {repo.default_branch}
            </span>
          )}
          {(repo.languages ?? []).map((lang) => (
            <span
              key={lang}
              className="px-2.5 py-1 rounded-full bg-[rgba(6,182,212,0.08)] text-[10px] text-[var(--accent-cyan)] border border-[rgba(6,182,212,0.15)]"
            >
              {lang}
            </span>
          ))}
          {(repo.frameworks ?? []).map((fw) => (
            <span
              key={fw}
              className="px-2.5 py-1 rounded-full bg-[rgba(168,85,247,0.08)] text-[10px] text-[var(--accent-purple)] border border-[rgba(168,85,247,0.15)]"
            >
              {fw}
            </span>
          ))}
          {repo.is_monorepo && (
            <span className="px-2.5 py-1 rounded-full bg-[rgba(245,158,11,0.08)] text-[10px] text-[var(--accent-amber)] border border-[rgba(245,158,11,0.15)]">
              Monorepo
            </span>
          )}
        </div>
      )}

      {/* Scan Job Status Banner */}
      {scanJob && (
        <div className="glass-card p-5 relative overflow-hidden">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2.5">
              {scanStatus === 'completed' ? (
                <div className="w-7 h-7 rounded-lg bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20">
                  <CheckCircle className="w-3.5 h-3.5 text-[var(--accent-green)]" />
                </div>
              ) : scanStatus === 'failed' ? (
                <div className="w-7 h-7 rounded-lg bg-rose-500/10 flex items-center justify-center border border-rose-500/20">
                  <AlertTriangle className="w-3.5 h-3.5 text-[var(--accent-rose)]" />
                </div>
              ) : (
                <div className="w-7 h-7 rounded-lg bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20">
                  <Clock className="w-3.5 h-3.5 text-[var(--accent-blue)] animate-spin" />
                </div>
              )}
              <div>
                <span className="text-sm font-semibold capitalize text-[var(--text-primary)]">
                  Scan: {scanStatus.replace('_', ' ')}
                </span>
                <span className="text-xs text-[var(--text-muted)] ml-2">
                  ({scanJob.current_phase ? scanPhaseLabels[scanJob.current_phase] ?? scanJob.current_phase : 'Queue'})
                </span>
              </div>
            </div>
            <span className="text-xs font-mono text-[var(--accent-cyan)] font-bold">
              {scanProgress}%
            </span>
          </div>

          <div className="progress-bar">
            <div
              className="progress-bar-fill"
              style={{ width: `${scanProgress}%` }}
            />
          </div>

          <p className="text-xs text-[var(--text-muted)] mt-2.5 leading-relaxed">
            {scanJob.error_message ? (
              <span className="text-[var(--accent-rose)]">{scanJob.error_message}</span>
            ) : scanStatus === 'completed' ? (
              'Pipeline execution completed successfully. Grounded knowledge graph & vector search are ready.'
            ) : (
              'Processing codebase AST, dependencies, graph relationships, vector embeddings, and search indices...'
            )}
          </p>
        </div>
      )}

      {/* Metrics Row */}
      {stats.length > 0 && (
        <div className="stats-grid stagger-children">
          {stats.map((s, i) => {
            const Icon = s.icon;
            return (
              <div key={i} className="stat-card metric-card">
                <div className="flex items-center gap-2 mb-3">
                  <Icon className="w-3.5 h-3.5 flex-shrink-0" style={{ color: s.color }} />
                  <span className="text-[11px] text-[var(--text-muted)] font-medium">{s.label}</span>
                </div>
                <p className="text-2xl font-bold font-mono tracking-tight" style={{ color: s.color }}>
                  {s.value}
                </p>
              </div>
            );
          })}
        </div>
      )}

      {/* Architecture & Performance Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {architecture && architecture.pattern && (
          <div className="glass-card p-5">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 rounded-lg bg-[rgba(99,102,241,0.1)] flex items-center justify-center border border-[rgba(99,102,241,0.2)]">
                <Layers className="w-3.5 h-3.5 text-[var(--accent-blue)]" />
              </div>
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">Architecture Pattern</h3>
            </div>
            <div className="flex items-baseline justify-between mb-2">
              <p className="text-xl font-bold text-[var(--accent-blue)]">
                {architecture.pattern}
              </p>
              <span className="text-xs text-[var(--accent-green)] font-mono font-semibold">
                {Math.round(architecture.confidence * 100)}% Confidence
              </span>
            </div>
            <p className="text-xs text-[var(--text-muted)] leading-relaxed">
              Detected {architecture.layers?.length ?? 0} active architectural layers with component mappings.
            </p>
          </div>
        )}

        {performance && (
          <div className="glass-card p-5">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 rounded-lg bg-[rgba(245,158,11,0.1)] flex items-center justify-center border border-[rgba(245,158,11,0.2)]">
                <Zap className="w-3.5 h-3.5 text-[var(--accent-amber)]" />
              </div>
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">Performance Insights</h3>
            </div>
            <div className="flex items-baseline justify-between mb-2">
              <p className="text-xl font-bold text-[var(--accent-amber)]">
                {perfCount} Findings
              </p>
              <span className="text-xs text-[var(--text-muted)]">
                N+1 queries, heavy calls & missing pagination
              </span>
            </div>
            <p className="text-xs text-[var(--text-muted)] leading-relaxed">
              Analyzed call expressions, loop conditions, and query patterns across source files.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
