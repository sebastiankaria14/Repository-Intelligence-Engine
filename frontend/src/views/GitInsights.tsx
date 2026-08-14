import { GitCommit, Users, Flame, TrendingUp } from 'lucide-react';
import {
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  AreaChart,
  Area,
} from 'recharts';

import NoRepository from '../components/NoRepository';
import DataShell from '../components/DataShell';
import { useCurrentRepoId, useApi } from '../hooks/useRepository';
import type { GitInsightsResponse } from '../types/api';
import { repositoryApi } from '../lib/api';

export default function GitInsights() {
  const repoId = useCurrentRepoId();
  const { data, loading, error, refetch: _refetch } = useApi<GitInsightsResponse>(
    repoId,
    repositoryApi.getGitInsights,
  );

  if (!repoId && !loading && !data) {
    return <NoRepository />;
  }

  const contributors = data?.contributors ?? [];
  const hotspotFiles = data?.hotspot_files ?? [];
  const commitFrequency = data?.commit_frequency ?? {};

  const commitChartData = Object.entries(commitFrequency)
    .map(([date, count]: [string, number]) => ({ month: date.slice(0, 7), commits: count }))
    .slice(-8);

  const maxChanges = hotspotFiles.length
    ? Math.max(...hotspotFiles.map((h: any) => h.changes))
    : 1;
  const avgPerWeek = data && data.total_commits ? Math.round(data.total_commits / 52) : 0;

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold gradient-text">Git Insights</h2>
        <p className="text-[var(--text-muted)] text-sm mt-1">
          Commit history, contributors, hotspots, and change coupling
        </p>
      </div>

      <DataShell
        loading={loading}
        error={error}
        isEmpty={
          !data || (data.total_commits === 0 && contributors.length === 0)
        }
        emptyTitle="No Git history found"
        emptyDescription="No commit history was available for analysis. Ensure the repository was cloned successfully."
      >
        <>
          {/* Stats */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="glass-card metric-card p-4">
              <div className="flex items-center gap-2 mb-2">
                <GitCommit className="w-4 h-4 text-[var(--accent-blue)]" />
                <span className="text-xs text-[var(--text-muted)]">
                  Total Commits
                </span>
              </div>
              <p className="text-2xl font-bold text-[var(--accent-blue)]">
                {data?.total_commits ?? 0}
              </p>
            </div>
            <div className="glass-card metric-card p-4">
              <div className="flex items-center gap-2 mb-2">
                <Users className="w-4 h-4 text-[var(--accent-purple)]" />
                <span className="text-xs text-[var(--text-muted)]">
                  Contributors
                </span>
              </div>
              <p className="text-2xl font-bold text-[var(--accent-purple)]">
                {data?.total_contributors ?? 0}
              </p>
            </div>
            <div className="glass-card metric-card p-4">
              <div className="flex items-center gap-2 mb-2">
                <Flame className="w-4 h-4 text-[var(--accent-rose)]" />
                <span className="text-xs text-[var(--text-muted)]">
                  Hotspot Files
                </span>
              </div>
              <p className="text-2xl font-bold text-[var(--accent-rose)]">
                {hotspotFiles.length}
              </p>
            </div>
            <div className="glass-card metric-card p-4">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-4 h-4 text-[var(--accent-green)]" />
                <span className="text-xs text-[var(--text-muted)]">Avg/Week</span>
              </div>
              <p className="text-2xl font-bold text-[var(--accent-green)]">
                {avgPerWeek}
              </p>
            </div>
          </div>

          {/* Commit Frequency Chart */}
          {commitChartData.length > 0 && (
            <div className="glass-card p-6">
              <h3 className="text-lg font-semibold mb-4">Commit Frequency</h3>
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={commitChartData}>
                  <defs>
                    <linearGradient
                      id="commitGradient"
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,102,241,0.1)" />
                  <XAxis dataKey="month" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--bg-secondary)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '8px',
                      color: 'var(--text-primary)',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="commits"
                    stroke="#6366f1"
                    fill="url(#commitGradient)"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Hotspot Files */}
            <div className="glass-card p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Flame className="w-5 h-5 text-[var(--accent-rose)]" />
                Hotspot Files
              </h3>
              <div className="space-y-3">
                {hotspotFiles.map((f, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-mono truncate text-[var(--text-primary)]">
                        {f.file}
                      </p>
                      <div className="flex gap-3 mt-1">
                        <span className="text-xs text-[var(--text-muted)]">
                          {f.changes} changes
                        </span>
                        <span className="text-xs text-[var(--text-muted)]">
                          {f.authors} authors
                        </span>
                      </div>
                    </div>
                    <div
                      className="h-2 rounded-full"
                      style={{
                        width: `${Math.min((f.changes / maxChanges) * 100, 100)}%`,
                        maxWidth: '100px',
                        background: 'var(--gradient-danger)',
                      }}
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* Top Contributors */}
            <div className="glass-card p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Users className="w-5 h-5 text-[var(--accent-purple)]" />
                Top Contributors
              </h3>
              <div className="space-y-4">
                {contributors.map((c, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <div
                      className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold"
                      style={{
                        background: `var(--gradient-${['primary', 'accent', 'success'][i % 3]})`,
                      }}
                    >
                      {c.name.charAt(0)}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">{c.name}</p>
                      <p className="text-xs text-[var(--text-muted)]">
                        {c.commits} commits · +
                        {(c.lines_added / 1000).toFixed(1)}k / -
                        {(c.lines_deleted / 1000).toFixed(1)}k
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      </DataShell>
    </div>
  );
}
