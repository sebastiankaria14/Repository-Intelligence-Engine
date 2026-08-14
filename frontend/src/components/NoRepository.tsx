import { PlusCircle, GitBranch } from 'lucide-react';
import { useRepositoryContext } from '../contexts/useRepositoryContext';
import { repositoryApi } from '../lib/api';

export default function NoRepository() {
  const { setRepo } = useRepositoryContext();

  const handleAnalyze = async () => {
    const url = prompt('Enter a GitHub repository URL:');
    if (!url) return;
    try {
      const { data } = await repositoryApi.create({ github_url: url });
      setRepo(data);
    } catch (err) {
      console.error('Failed to add repository:', err);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center py-24 text-center animate-fade-in">
      <div
        className="w-14 h-14 rounded-2xl flex items-center justify-center mb-5"
        style={{
          background: 'var(--gradient-primary)',
          boxShadow: '0 0 40px rgba(99,102,241,0.25)',
        }}
      >
        <GitBranch className="w-7 h-7 text-white" />
      </div>
      <h3 className="text-lg font-semibold gradient-text mb-2">
        No repository selected
      </h3>
      <p className="text-xs text-[var(--text-muted)] mb-6 max-w-md leading-relaxed">
        Add a GitHub repository to begin analysis. The Overview, Architecture,
        API, Database, Dependencies, Git Insights, Graph Explorer, and AI Chat
        views will be populated with real data from the knowledge graph.
      </p>
      <button onClick={handleAnalyze} className="btn-primary">
        <PlusCircle className="w-4 h-4" />
        Add Repository
      </button>
    </div>
  );
}
