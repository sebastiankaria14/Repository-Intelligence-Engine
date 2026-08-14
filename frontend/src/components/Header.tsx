import { useState, useCallback } from 'react';
import { Search, Bell, Plus, Settings, X } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useRepositoryContext } from '../contexts/useRepositoryContext';
import { repositoryApi } from '../lib/api';

export default function Header() {
  const [showAddRepo, setShowAddRepo] = useState(false);
  const [repoUrl, setRepoUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const { setRepo } = useRepositoryContext();
  const navigate = useNavigate();
  const location = useLocation();

  const handleAddRepo = async () => {
    if (!repoUrl.trim()) return;
    setLoading(true);
    try {
      const { data } = await repositoryApi.create({ github_url: repoUrl.trim() });
      setRepo(data);
      setRepoUrl('');
      setShowAddRepo(false);
    } catch (err) {
      console.error('Failed to add repository:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = useCallback(() => {
    if (!searchQuery.trim()) return;
    const repoId = new URLSearchParams(location.search).get('repo');
    if (repoId) {
      navigate(`/chat?repo=${repoId}`);
    } else {
      navigate('/chat');
    }
  }, [searchQuery, navigate, location.search]);

  return (
    <header className="h-14 border-b border-[var(--border-color)] bg-[var(--bg-secondary)] flex items-center justify-between px-6 flex-shrink-0 relative">
      {/* Subtle bottom glow */}
      <div
        className="absolute bottom-0 left-0 right-0 h-px"
        style={{ background: 'linear-gradient(90deg, transparent, rgba(99,102,241,0.15) 50%, transparent)' }}
      />

      {/* Search */}
      <div className="flex items-center gap-3 flex-1 max-w-md">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--text-muted)]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Ask AI about this repo..."
            className="w-full pl-9 pr-4 py-1.5 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] transition-colors focus:border-[var(--accent-blue)]"
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        {showAddRepo ? (
          <div className="flex items-center gap-2 animate-fade-in">
            <input
              type="text"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAddRepo()}
              placeholder="https://github.com/user/repo"
              className="px-3 py-1.5 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] w-72 transition-colors"
              autoFocus
            />
            <button
              onClick={handleAddRepo}
              disabled={loading}
              className="btn-primary text-xs py-1.5 px-4"
            >
              {loading ? 'Analyzing...' : 'Analyze'}
            </button>
            <button
              onClick={() => setShowAddRepo(false)}
              className="p-1.5 rounded-lg hover:bg-[var(--bg-primary)] transition-colors text-[var(--text-muted)] hover:text-[var(--text-primary)]"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <button
            onClick={() => setShowAddRepo(true)}
            className="btn-primary text-xs py-1.5"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Repository
          </button>
        )}

        <button className="p-1.5 rounded-lg hover:bg-[var(--bg-primary)] transition-colors">
          <Bell className="w-3.5 h-3.5 text-[var(--text-muted)]" />
        </button>

        <button className="p-1.5 rounded-lg hover:bg-[var(--bg-primary)] transition-colors">
          <Settings className="w-3.5 h-3.5 text-[var(--text-muted)]" />
        </button>
      </div>
    </header>
  );
}
