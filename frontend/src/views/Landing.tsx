import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, GitBranch, Shield, Zap, Brain, Search, Database, Network, Sparkles, FolderOpen } from 'lucide-react';
import { repositoryApi } from '../lib/api';

const features = [
  { icon: GitBranch, title: 'Architecture Discovery', desc: 'Auto-detect patterns: MVC, hexagonal, microservices', color: 'var(--accent-blue)' },
  { icon: Shield, title: 'Security Intelligence', desc: 'Pattern-based secret, SQLi & dangerous import detection', color: 'var(--accent-rose)' },
  { icon: Zap, title: 'Performance Analysis', desc: 'N+1 queries, circular deps, heavy endpoints', color: 'var(--accent-amber)' },
  { icon: Brain, title: 'AI-Powered Chat', desc: 'Ask questions grounded in your knowledge graph', color: 'var(--accent-purple)' },
  { icon: Search, title: 'API Discovery', desc: 'REST/GraphQL endpoints with lifecycle mapping', color: 'var(--accent-cyan)' },
  { icon: Database, title: 'Database Intelligence', desc: 'ER diagrams, migration history, ORM analysis', color: 'var(--accent-green)' },
  { icon: Network, title: 'Dependency Graph', desc: '"What breaks if Redis goes down?"', color: 'var(--accent-blue)' },
  { icon: GitBranch, title: 'Git Intelligence', desc: 'Ownership, hotspots, change coupling', color: 'var(--accent-purple)' },
];

const sampleRepos = [
  { label: 'FastAPI', url: 'https://github.com/fastapi/fastapi' },
  { label: 'Flask', url: 'https://github.com/pallets/flask' },
  { label: 'Express', url: 'https://github.com/expressjs/express' },
];

export default function Landing() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleSelectLocalFolder = async () => {
    if (window.electronAPI) {
      try {
        const folder = await window.electronAPI.selectFolder();
        if (folder) {
          setUrl(folder);
          void handleAnalyze(folder);
        }
      } catch (err) {
        setError('Failed to select local directory');
      }
    }
  };

  const handleAnalyze = async (targetUrl = url) => {
    const finalUrl = targetUrl.trim();
    if (!finalUrl) return;
    setLoading(true);
    setError(null);
    try {
      const { data } = await repositoryApi.create({ github_url: finalUrl });
      navigate(`/overview?repo=${data.id}`);
    } catch (err: unknown) {
      let msg = err instanceof Error ? err.message : 'Failed to trigger repository scan';
      if (msg === 'Network Error' || (err as { code?: string })?.code === 'ERR_NETWORK') {
        msg = 'Cannot reach local analysis engine on port 8000. Please wait for the engine to initialize or click restart in the top bar.';
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center p-8 relative overflow-hidden"
      style={{ background: 'var(--bg-primary)' }}
    >
      {/* Background Orbs */}
      <div
        className="bg-orb"
        style={{
          width: '500px',
          height: '500px',
          background: 'rgba(99, 102, 241, 0.08)',
          top: '-10%',
          left: '-5%',
          animationDelay: '0s',
        }}
      />
      <div
        className="bg-orb"
        style={{
          width: '400px',
          height: '400px',
          background: 'rgba(6, 182, 212, 0.06)',
          bottom: '-5%',
          right: '-5%',
          animationDelay: '3s',
        }}
      />
      <div
        className="bg-orb"
        style={{
          width: '300px',
          height: '300px',
          background: 'rgba(168, 85, 247, 0.05)',
          top: '50%',
          right: '20%',
          animationDelay: '5s',
        }}
      />

      {/* Hero */}
      <div className="text-center max-w-3xl mx-auto mb-14 animate-fade-in relative z-10">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-[var(--border-color)] bg-[var(--bg-glass)] mb-8">
          <Zap className="w-3.5 h-3.5 text-[var(--accent-cyan)]" />
          <span className="text-xs text-[var(--text-secondary)] font-medium">AI-Powered Software Intelligence</span>
        </div>

        <h1 className="text-5xl lg:text-6xl font-bold mb-5 leading-tight tracking-tight">
          <span className="gradient-text">Repository</span>{' '}
          <span className="text-[var(--text-primary)]">Intelligence</span>
          <br />
          <span className="gradient-text-accent">Engine</span>
        </h1>

        <p className="text-base text-[var(--text-secondary)] mb-10 leading-relaxed max-w-xl mx-auto">
          An MRI for your codebase. Understand architecture, APIs, dependencies,
          security, performance, and technical debt — powered by knowledge graphs and AI.
        </p>

        {/* Input & Desktop Action */}
        <div className="flex flex-col gap-3 max-w-xl mx-auto">
          {/* Desktop Browse Action */}
          <button
            type="button"
            onClick={handleSelectLocalFolder}
            className="btn-secondary w-full py-3.5 px-6 rounded-xl flex items-center justify-center gap-2.5 text-sm font-semibold shadow-lg shadow-black/30 cursor-pointer"
          >
            <FolderOpen className="w-4 h-4 text-amber-400" />
            <span>Select Local Repository Folder</span>
          </button>

          <div className="flex items-center gap-3 my-1">
            <div className="flex-1 h-px bg-white/10" />
            <span className="text-[11px] text-[var(--text-muted)] uppercase tracking-wider font-semibold">Or analyze by URL or Path</span>
            <div className="flex-1 h-px bg-white/10" />
          </div>

          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <GitBranch className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
                placeholder="e.g. C:\projects\repo or https://github.com/user/repo"
                className="w-full pl-11 pr-4 py-3.5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-primary)] placeholder-[var(--text-muted)] text-sm transition-colors"
              />
            </div>
            <button
              onClick={() => handleAnalyze()}
              disabled={loading}
              className="btn-primary py-3.5 px-7 text-sm rounded-xl"
            >
              {loading ? 'Analyzing...' : 'Analyze'}
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          {error && <p className="text-xs text-[var(--accent-rose)] text-left pl-2">{error}</p>}

          {/* Quick Demo buttons - strictly borderless */}
          <div className="flex items-center gap-2 text-xs text-[var(--text-muted)] pt-1 justify-center">
            <Sparkles className="w-3 h-3 text-[var(--accent-amber)]" />
            <span>Try:</span>
            {sampleRepos.map((sample) => (
              <button
                key={sample.url}
                onClick={() => {
                  setUrl(sample.url);
                  void handleAnalyze(sample.url);
                }}
                className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-[var(--accent-cyan)] transition-all text-xs font-medium cursor-pointer"
              >
                {sample.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Feature Grid */}
      <div
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 max-w-5xl mx-auto relative z-10 stagger-children"
        style={{ animationDelay: '0.15s' }}
      >
        {features.map((f, i) => {
          const Icon = f.icon;
          return (
            <div key={i} className="glass-card metric-card p-5">
              <div
                className="w-9 h-9 rounded-lg flex items-center justify-center mb-3"
                style={{ background: `${f.color}12`, border: `1px solid ${f.color}25` }}
              >
                <Icon className="w-4 h-4" style={{ color: f.color }} />
              </div>
              <h3 className="font-semibold text-sm mb-1 text-[var(--text-primary)]">{f.title}</h3>
              <p className="text-xs text-[var(--text-muted)] leading-relaxed">{f.desc}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
