import type { ReactNode } from 'react';
import { Loader2, AlertCircle, Inbox } from 'lucide-react';

interface DataShellProps {
  loading: boolean;
  error: string | null;
  isEmpty: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  children: ReactNode;
}

export default function DataShell({
  loading,
  error,
  isEmpty,
  emptyTitle = 'No data available',
  emptyDescription = 'Analysis for this section has not been completed yet.',
  children,
}: DataShellProps) {
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <div className="relative">
          <div className="w-12 h-12 rounded-2xl bg-[rgba(99,102,241,0.08)] flex items-center justify-center border border-[var(--border-color)]">
            <Loader2 className="w-5 h-5 animate-spin text-[var(--accent-blue)]" />
          </div>
        </div>
        <div className="text-center">
          <p className="text-sm font-medium text-[var(--text-secondary)]">Loading analysis</p>
          <p className="text-xs text-[var(--text-muted)] mt-1">Fetching data from the knowledge graph…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card p-5 flex items-start gap-4">
        <div className="w-9 h-9 rounded-xl bg-[rgba(244,63,94,0.1)] flex items-center justify-center border border-[rgba(244,63,94,0.2)] flex-shrink-0">
          <AlertCircle className="w-4 h-4 text-[var(--accent-rose)]" />
        </div>
        <div>
          <p className="font-semibold text-sm text-[var(--accent-rose)]">
            Failed to load data
          </p>
          <p className="text-xs text-[var(--text-muted)] mt-1 leading-relaxed">{error}</p>
        </div>
      </div>
    );
  }

  if (isEmpty) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="w-14 h-14 rounded-2xl bg-[rgba(99,102,241,0.06)] flex items-center justify-center border border-[var(--border-color)] mb-4">
          <Inbox className="w-6 h-6 text-[var(--text-muted)]" />
        </div>
        <p className="text-base font-semibold gradient-text mb-1">
          {emptyTitle}
        </p>
        <p className="text-xs text-[var(--text-muted)] max-w-sm leading-relaxed">
          {emptyDescription}
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
