import { useState } from 'react';
import {
  X,
  TrendingUp,
  Shield,
  AlertTriangle,
  Zap,
  Layers,
  CheckCircle2,
  FileCode,
  Info,
} from 'lucide-react';

import type {
  ArchitectureResponse,
  SecurityResponse,
  PerformanceResponse,
  TechnicalDebtResponse,
  Repository,
} from '../types/api';

export type OverviewModalTab = 'health' | 'security' | 'debt' | 'performance' | 'architecture';

interface OverviewDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialTab?: OverviewModalTab;
  repository: Repository | null;
  security: SecurityResponse | null;
  performance: PerformanceResponse | null;
  techDebt: TechnicalDebtResponse | null;
  architecture: ArchitectureResponse | null;
}

export default function OverviewDetailModal({
  isOpen,
  onClose,
  initialTab = 'health',
  repository,
  security,
  performance,
  techDebt,
  architecture,
}: OverviewDetailModalProps) {
  const [activeTab, setActiveTab] = useState<OverviewModalTab>(initialTab);
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [perfFilter, setPerfFilter] = useState<string>('all');
  const [visibleDebtCount, setVisibleDebtCount] = useState<number>(40);
  const [visiblePerfCount, setVisiblePerfCount] = useState<number>(40);

  if (!isOpen) return null;

  const healthScore = repository?.health_score != null ? Math.round(repository.health_score) : 25;
  const securityFindings = security?.findings ?? [];
  const perfFindings = performance?.findings ?? [];
  const debtItems = techDebt?.items ?? [];
  const debtScore = techDebt?.debt_score ?? 100;
  const effortHours = techDebt?.total_effort_hours ?? 0;

  // Formula deductions
  const secRisk = security?.risk_score ?? (securityFindings.length > 0 ? 25.0 : 0.0);
  const secDeduction = Math.min(secRisk, 50.0);
  const debtDeduction = Math.min(debtScore, 30.0);
  const perfDeduction = Math.min(perfFindings.length * 2, 20.0);

  const filteredSecurity = securityFindings.filter((f) => {
    if (severityFilter === 'all') return true;
    return f.severity?.toLowerCase() === severityFilter.toLowerCase();
  });

  const filteredPerf = perfFindings.filter((f) => {
    if (perfFilter === 'all') return true;
    return f.type?.toLowerCase() === perfFilter.toLowerCase();
  });

  const getSeverityBadgeClass = (sev: string) => {
    switch (sev?.toLowerCase()) {
      case 'critical':
        return 'bg-rose-500/15 text-rose-400 border border-rose-500/30';
      case 'high':
        return 'bg-amber-500/15 text-amber-400 border border-amber-500/30';
      case 'medium':
        return 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/30';
      case 'low':
      case 'info':
        return 'bg-blue-500/15 text-blue-400 border border-blue-500/30';
      default:
        return 'bg-slate-500/15 text-slate-400 border border-slate-500/30';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
      <div
        className="glass-card w-full max-w-4xl h-[85vh] max-h-[85vh] flex flex-col overflow-hidden shadow-2xl border border-[var(--border-color)] relative"
        style={{ backgroundColor: '#0c111d' }}
      >
        {/* Fixed Header */}
        <div className="flex-shrink-0 flex items-center justify-between px-6 py-4 border-b border-[var(--border-color)] bg-[var(--bg-secondary)] z-20">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[rgba(99,102,241,0.15)] flex items-center justify-center border border-[rgba(99,102,241,0.3)]">
              {activeTab === 'health' && <TrendingUp className="w-4 h-4 text-[var(--accent-blue)]" />}
              {activeTab === 'security' && <Shield className="w-4 h-4 text-[var(--accent-rose)]" />}
              {activeTab === 'debt' && <AlertTriangle className="w-4 h-4 text-[var(--accent-amber)]" />}
              {activeTab === 'performance' && <Zap className="w-4 h-4 text-[var(--accent-amber)]" />}
              {activeTab === 'architecture' && <Layers className="w-4 h-4 text-[var(--accent-cyan)]" />}
            </div>
            <div>
              <h2 className="text-base font-bold text-[var(--text-primary)]">
                {activeTab === 'health' && 'Health Score Breakdown & Diagnostic'}
                {activeTab === 'security' && 'Security Audit & Vulnerabilities'}
                {activeTab === 'debt' && 'Technical Debt & Code Smells'}
                {activeTab === 'performance' && 'Performance Antipatterns & Insights'}
                {activeTab === 'architecture' && 'Architectural Pattern & Layers'}
              </h2>
              <p className="text-xs text-[var(--text-muted)]">
                {repository?.name ? `Repository: ${repository.name}` : 'Codebase Metric Inspection'}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-[var(--border-color)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors border-none"
            style={{ border: 'none' }}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Fixed Tab Navigation */}
        <div className="flex-shrink-0 flex items-center gap-1 px-6 pt-3 border-b border-[var(--border-color)] bg-[var(--bg-primary)] overflow-x-auto z-20">
          <button
            onClick={() => setActiveTab('health')}
            className={`flex-shrink-0 px-3 py-2 text-xs font-semibold rounded-t-lg transition-all border-b-2 flex items-center gap-1.5 ${
              activeTab === 'health'
                ? 'border-[var(--accent-blue)] text-[var(--accent-blue)] bg-[var(--bg-secondary)]'
                : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
            }`}
            style={{ borderTop: 'none', borderLeft: 'none', borderRight: 'none' }}
          >
            <TrendingUp className="w-3.5 h-3.5" />
            Health Score ({healthScore}/100)
          </button>

          <button
            onClick={() => setActiveTab('security')}
            className={`flex-shrink-0 px-3 py-2 text-xs font-semibold rounded-t-lg transition-all border-b-2 flex items-center gap-1.5 ${
              activeTab === 'security'
                ? 'border-[var(--accent-rose)] text-[var(--accent-rose)] bg-[var(--bg-secondary)]'
                : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
            }`}
            style={{ borderTop: 'none', borderLeft: 'none', borderRight: 'none' }}
          >
            <Shield className="w-3.5 h-3.5" />
            Security ({securityFindings.length})
          </button>

          <button
            onClick={() => setActiveTab('debt')}
            className={`flex-shrink-0 px-3 py-2 text-xs font-semibold rounded-t-lg transition-all border-b-2 flex items-center gap-1.5 ${
              activeTab === 'debt'
                ? 'border-[var(--accent-amber)] text-[var(--accent-amber)] bg-[var(--bg-secondary)]'
                : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
            }`}
            style={{ borderTop: 'none', borderLeft: 'none', borderRight: 'none' }}
          >
            <AlertTriangle className="w-3.5 h-3.5" />
            Tech Debt ({debtScore}/100)
          </button>

          <button
            onClick={() => setActiveTab('performance')}
            className={`flex-shrink-0 px-3 py-2 text-xs font-semibold rounded-t-lg transition-all border-b-2 flex items-center gap-1.5 ${
              activeTab === 'performance'
                ? 'border-[var(--accent-amber)] text-[var(--accent-amber)] bg-[var(--bg-secondary)]'
                : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
            }`}
            style={{ borderTop: 'none', borderLeft: 'none', borderRight: 'none' }}
          >
            <Zap className="w-3.5 h-3.5" />
            Performance ({perfFindings.length})
          </button>

          <button
            onClick={() => setActiveTab('architecture')}
            className={`flex-shrink-0 px-3 py-2 text-xs font-semibold rounded-t-lg transition-all border-b-2 flex items-center gap-1.5 ${
              activeTab === 'architecture'
                ? 'border-[var(--accent-cyan)] text-[var(--accent-cyan)] bg-[var(--bg-secondary)]'
                : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
            }`}
            style={{ borderTop: 'none', borderLeft: 'none', borderRight: 'none' }}
          >
            <Layers className="w-3.5 h-3.5" />
            Architecture ({architecture?.pattern || 'Pattern'})
          </button>
        </div>

        {/* Scrollable Content Body — strictly constrained with min-h-0 */}
        <div className="flex-1 min-h-0 overflow-y-auto p-6 space-y-6 relative z-10">
          {/* TAB 1: HEALTH SCORE */}
          {activeTab === 'health' && (
            <div className="space-y-6">
              {/* Score Highlight Banner */}
              <div className="p-5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] flex flex-wrap items-center justify-between gap-4">
                <div>
                  <span className="text-xs uppercase tracking-wider text-[var(--text-muted)] font-semibold block mb-1">
                    Overall Codebase Health Rating
                  </span>
                  <div className="flex items-baseline gap-2">
                    <span
                      className="text-4xl font-extrabold font-mono"
                      style={{
                        color:
                          healthScore >= 75
                            ? 'var(--accent-green)'
                            : healthScore >= 50
                            ? 'var(--accent-amber)'
                            : 'var(--accent-rose)',
                      }}
                    >
                      {healthScore}/100
                    </span>
                    <span className="text-sm text-[var(--text-muted)]">
                      {healthScore >= 75 ? 'Healthy' : healthScore >= 50 ? 'Moderate Risk' : 'Needs Immediate Attention'}
                    </span>
                  </div>
                </div>

                <div className="text-xs text-[var(--text-muted)] max-w-xs text-right">
                  Score synthesized from static security analysis, code debt heuristics, and performance loop audits.
                </div>
              </div>

              {/* Deductions Breakdown */}
              <div>
                <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-3">
                  Mathematical Score Breakdown
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                  <div className="p-4 rounded-xl bg-[var(--bg-primary)] border border-[var(--border-color)]">
                    <span className="text-[11px] text-[var(--text-muted)] block mb-1">Base Score</span>
                    <p className="text-xl font-bold font-mono text-[var(--accent-green)]">+100.0</p>
                    <p className="text-[11px] text-[var(--text-muted)] mt-1">Starting baseline</p>
                  </div>

                  <div className="p-4 rounded-xl bg-[var(--bg-primary)] border border-rose-500/20">
                    <span className="text-[11px] text-rose-400 block mb-1">Security Risk Penalty</span>
                    <p className="text-xl font-bold font-mono text-[var(--accent-rose)]">-{secDeduction.toFixed(1)} pts</p>
                    <p className="text-[11px] text-[var(--text-muted)] mt-1">{securityFindings.length} vulnerabilities</p>
                  </div>

                  <div className="p-4 rounded-xl bg-[var(--bg-primary)] border border-amber-500/20">
                    <span className="text-[11px] text-amber-400 block mb-1">Technical Debt Penalty</span>
                    <p className="text-xl font-bold font-mono text-[var(--accent-amber)]">-{debtDeduction.toFixed(1)} pts</p>
                    <p className="text-[11px] text-[var(--text-muted)] mt-1">Debt score: {debtScore}/100</p>
                  </div>

                  <div className="p-4 rounded-xl bg-[var(--bg-primary)] border border-cyan-500/20">
                    <span className="text-[11px] text-cyan-400 block mb-1">Performance Penalty</span>
                    <p className="text-xl font-bold font-mono text-[var(--accent-cyan)]">-{perfDeduction.toFixed(1)} pts</p>
                    <p className="text-[11px] text-[var(--text-muted)] mt-1">{perfFindings.length} antipatterns</p>
                  </div>
                </div>
              </div>

              {/* Action Plan */}
              <div className="p-5 rounded-xl bg-[var(--bg-primary)] border border-[var(--border-color)] space-y-3">
                <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                  Remediation Recommendations to Recover Points
                </h3>
                <ul className="space-y-2 text-xs text-[var(--text-secondary)]">
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--accent-rose)] font-bold">1.</span>
                    <span>
                      <strong className="text-[var(--text-primary)]">Resolve Security Vulnerabilities:</strong> Fix all {securityFindings.length} hardcoded secret and injection findings to instantly recover up to {secDeduction.toFixed(0)} health points.
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--accent-amber)] font-bold">2.</span>
                    <span>
                      <strong className="text-[var(--text-primary)]">Refactor High-Complexity Files:</strong> Break down god classes and long methods to lower technical debt below 30.
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--accent-cyan)] font-bold">3.</span>
                    <span>
                      <strong className="text-[var(--text-primary)]">Eliminate N+1 Queries:</strong> Add batch loading or pagination across the {perfFindings.length} detected call loops.
                    </span>
                  </li>
                </ul>
              </div>
            </div>
          )}

          {/* TAB 2: SECURITY FINDINGS */}
          {activeTab === 'security' && (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                    Audit Findings ({securityFindings.length} Total)
                  </h3>
                  <p className="text-xs text-[var(--text-muted)]">
                    Risk score: {secRisk}/100 · Static heuristic detection
                  </p>
                </div>

                <div className="flex items-center gap-1">
                  {['all', 'critical', 'high', 'medium', 'low'].map((sev) => (
                    <button
                      key={sev}
                      onClick={() => setSeverityFilter(sev)}
                      className={`px-2.5 py-1 rounded text-xs capitalize transition-colors ${
                        severityFilter === sev
                          ? 'bg-[var(--accent-rose)] text-white'
                          : 'bg-[var(--bg-primary)] text-[var(--text-muted)] hover:text-[var(--text-primary)]'
                      }`}
                      style={{ border: 'none' }}
                    >
                      {sev}
                    </button>
                  ))}
                </div>
              </div>

              {filteredSecurity.length === 0 ? (
                <div className="p-8 text-center glass-card">
                  <CheckCircle2 className="w-8 h-8 text-[var(--accent-green)] mx-auto mb-2" />
                  <p className="text-sm font-medium text-[var(--text-primary)]">No findings in this category</p>
                  <p className="text-xs text-[var(--text-muted)] mt-1">
                    Static analysis found no matching vulnerabilities.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {filteredSecurity.map((f, idx) => (
                    <div
                      key={f.id || idx}
                      className="p-4 rounded-xl bg-[var(--bg-primary)] border border-[var(--border-color)] hover:border-slate-700 transition-colors space-y-2.5"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${getSeverityBadgeClass(f.severity)}`}>
                            {f.severity}
                          </span>
                          <span className="font-semibold text-sm text-[var(--text-primary)]">
                            {f.title}
                          </span>
                        </div>
                        {f.rule_id && (
                          <span className="font-mono text-[10px] text-[var(--text-muted)] bg-[var(--bg-secondary)] px-2 py-0.5 rounded border border-[var(--border-color)]">
                            {f.rule_id}
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-2 text-xs font-mono text-[var(--accent-cyan)]">
                        <FileCode className="w-3.5 h-3.5 flex-shrink-0" />
                        <span>{f.file_path}{f.line_start ? `:${f.line_start}` : ''}</span>
                      </div>

                      {f.description && (
                        <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                          {f.description}
                        </p>
                      )}

                      {f.recommendation && (
                        <div className="p-2.5 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)] text-xs">
                          <span className="font-semibold text-[var(--accent-green)] block mb-0.5">Remediation:</span>
                          <p className="text-[var(--text-muted)]">{f.recommendation}</p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 3: TECHNICAL DEBT */}
          {activeTab === 'debt' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] flex flex-wrap items-center justify-between gap-4">
                <div>
                  <span className="text-xs text-[var(--text-muted)] block">Technical Debt Score</span>
                  <p className="text-2xl font-bold font-mono text-[var(--accent-amber)]">{debtScore}/100</p>
                </div>
                <div>
                  <span className="text-xs text-[var(--text-muted)] block">Estimated Remediation Effort</span>
                  <p className="text-2xl font-bold font-mono text-[var(--accent-cyan)]">{effortHours} Hours</p>
                </div>
                <div>
                  <span className="text-xs text-[var(--text-muted)] block">Maintenance Items</span>
                  <p className="text-2xl font-bold font-mono text-[var(--text-primary)]">{debtItems.length}</p>
                </div>
              </div>

              <div className="space-y-3">
                {debtItems.length === 0 ? (
                  <div className="p-8 text-center glass-card">
                    <CheckCircle2 className="w-8 h-8 text-[var(--accent-green)] mx-auto mb-2" />
                    <p className="text-sm font-medium text-[var(--text-primary)]">Codebase Structure is Clean</p>
                    <p className="text-xs text-[var(--text-muted)] mt-1">
                      No high-severity code smells or cyclomatic complexity bottlenecks detected.
                    </p>
                  </div>
                ) : (
                  <>
                    {debtItems.slice(0, visibleDebtCount).map((item, idx) => (
                      <div
                        key={idx}
                        className="p-4 rounded-xl bg-[var(--bg-primary)] border border-[var(--border-color)] space-y-2"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-bold uppercase tracking-wider text-[var(--accent-amber)]">
                            {item.type?.replace('_', ' ')}
                          </span>
                          {item.effort_hours != null && (
                            <span className="text-[11px] text-[var(--text-muted)] font-mono">
                              ~{item.effort_hours}h effort
                            </span>
                          )}
                        </div>

                        <h4 className="font-semibold text-sm text-[var(--text-primary)]">
                          {item.title}
                        </h4>

                        <div className="flex items-center gap-2 text-xs font-mono text-[var(--accent-cyan)]">
                          <FileCode className="w-3.5 h-3.5 flex-shrink-0" />
                          <span>{item.file_path}</span>
                        </div>

                        <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                          {item.description}
                        </p>
                      </div>
                    ))}

                    {debtItems.length > visibleDebtCount && (
                      <button
                        onClick={() => setVisibleDebtCount((prev) => prev + 50)}
                        className="btn-secondary w-full py-2.5 text-xs font-semibold text-[var(--accent-cyan)]"
                        style={{ border: 'none' }}
                      >
                        Load 50 More Items ({debtItems.length - visibleDebtCount} remaining)
                      </button>
                    )}
                  </>
                )}
              </div>
            </div>
          )}

          {/* TAB 4: PERFORMANCE INSIGHTS */}
          {activeTab === 'performance' && (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                    Performance Findings ({perfFindings.length} Total)
                  </h3>
                  <p className="text-xs text-[var(--text-muted)]">
                    Identified via loop analysis, query inspections, and sync call heuristics
                  </p>
                </div>

                <div className="flex items-center gap-1">
                  {['all', 'n_plus_one', 'heavy_endpoint', 'large_object'].map((pType) => (
                    <button
                      key={pType}
                      onClick={() => setPerfFilter(pType)}
                      className={`px-2.5 py-1 rounded text-xs capitalize transition-colors ${
                        perfFilter === pType
                          ? 'bg-[var(--accent-amber)] text-black font-semibold'
                          : 'bg-[var(--bg-primary)] text-[var(--text-muted)] hover:text-[var(--text-primary)]'
                      }`}
                      style={{ border: 'none' }}
                    >
                      {pType.replace('_', ' ')}
                    </button>
                  ))}
                </div>
              </div>

              {filteredPerf.length === 0 ? (
                <div className="p-8 text-center glass-card">
                  <CheckCircle2 className="w-8 h-8 text-[var(--accent-green)] mx-auto mb-2" />
                  <p className="text-sm font-medium text-[var(--text-primary)]">No matching performance issues</p>
                  <p className="text-xs text-[var(--text-muted)] mt-1">
                    No bottlenecks detected under this filter.
                  </p>
                </div>
              ) : (
                <>
                  <div className="space-y-3">
                    {filteredPerf.slice(0, visiblePerfCount).map((p, idx) => (
                      <div
                        key={idx}
                        className="p-4 rounded-xl bg-[var(--bg-primary)] border border-[var(--border-color)] hover:border-slate-700 transition-colors space-y-2"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-500/15 text-amber-400 border border-amber-500/30">
                            {p.type?.replace('_', ' ')}
                          </span>
                          {p.severity && (
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${getSeverityBadgeClass(p.severity)}`}>
                              {p.severity}
                            </span>
                          )}
                        </div>

                        <h4 className="font-semibold text-sm text-[var(--text-primary)]">
                          {p.title}
                        </h4>

                        <div className="flex items-center gap-2 text-xs font-mono text-[var(--accent-cyan)]">
                          <FileCode className="w-3.5 h-3.5 flex-shrink-0" />
                          <span>{p.file_path}{p.line_number ? `:${p.line_number}` : ''}</span>
                        </div>

                        <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                          {p.description}
                        </p>

                        {p.recommendation && (
                          <div className="p-2.5 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)] text-xs">
                            <span className="font-semibold text-[var(--accent-green)] block mb-0.5">Optimization:</span>
                            <p className="text-[var(--text-muted)]">{p.recommendation}</p>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {filteredPerf.length > visiblePerfCount && (
                    <button
                      onClick={() => setVisiblePerfCount((prev) => prev + 30)}
                      className="btn-secondary w-full py-2.5 text-xs font-semibold text-[var(--accent-cyan)]"
                      style={{ border: 'none' }}
                    >
                      Load More Findings ({filteredPerf.length - visiblePerfCount} remaining)
                    </button>
                  )}
                </>
              )}
            </div>
          )}

          {/* TAB 5: ARCHITECTURE PATTERN */}
          {activeTab === 'architecture' && (
            <div className="space-y-5">
              <div className="p-5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] flex flex-wrap items-center justify-between gap-4">
                <div>
                  <span className="text-xs uppercase tracking-wider text-[var(--text-muted)] font-semibold block mb-1">
                    Classified Architecture Pattern
                  </span>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-extrabold text-[var(--accent-blue)]">
                      {architecture?.pattern || 'Modular Architecture'}
                    </span>
                    <span className="text-xs font-mono font-bold text-[var(--accent-green)]">
                      {Math.round((architecture?.confidence ?? 0.8) * 100)}% Confidence
                    </span>
                  </div>
                </div>

                <div className="text-xs text-[var(--text-muted)] max-w-xs text-right">
                  Pattern inferred through dependency graph topology, file layout, and component couplings.
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-3">
                  Detected Architectural Layers ({architecture?.layers?.length ?? 0})
                </h3>

                <div className="space-y-3">
                  {(architecture?.layers ?? []).map((layer, idx) => (
                    <div
                      key={idx}
                      className="p-4 rounded-xl bg-[var(--bg-primary)] border border-[var(--border-color)] space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <h4 className="font-bold text-sm text-[var(--accent-cyan)]">
                          {layer.name} Layer
                        </h4>
                        <span className="text-xs font-mono text-[var(--text-muted)]">
                          {layer.file_count} files
                        </span>
                      </div>

                      <p className="text-xs text-[var(--text-secondary)]">
                        {layer.description}
                      </p>

                      {layer.components && layer.components.length > 0 && (
                        <div className="pt-1">
                          <span className="text-[11px] text-[var(--text-muted)] block mb-1">Components:</span>
                          <div className="flex flex-wrap gap-1.5">
                            {layer.components.slice(0, 10).map((comp, ci) => (
                              <span
                                key={ci}
                                className="px-2 py-0.5 rounded bg-[var(--bg-secondary)] text-[10px] font-mono text-[var(--text-secondary)] border border-[var(--border-color)]"
                              >
                                {comp}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Fixed Footer */}
        <div className="flex-shrink-0 px-6 py-3 border-t border-[var(--border-color)] bg-[var(--bg-secondary)] flex items-center justify-between z-20">
          <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
            <Info className="w-3.5 h-3.5 text-[var(--accent-blue)]" />
            <span>Click any tab above to inspect other code health metrics.</span>
          </div>

          <button
            onClick={onClose}
            className="btn-secondary text-xs px-4 py-1.5"
            style={{ border: 'none' }}
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
}
