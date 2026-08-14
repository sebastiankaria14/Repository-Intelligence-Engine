import { NavLink, useLocation, useSearchParams } from 'react-router-dom';
import {
  LayoutDashboard,
  Boxes,
  Globe,
  Database,
  GitBranch,
  Network,
  Shield,
  MessageSquare,
  Zap,
} from 'lucide-react';

const navItems = [
  { path: '/overview', label: 'Overview', icon: LayoutDashboard },
  { path: '/architecture', label: 'Architecture', icon: Boxes },
  { path: '/apis', label: 'API Explorer', icon: Globe },
  { path: '/database', label: 'Database', icon: Database },
  { path: '/dependencies', label: 'Dependencies', icon: Network },
  { path: '/git', label: 'Git Insights', icon: GitBranch },
  { path: '/graph', label: 'Graph Explorer', icon: Zap },
  { path: '/chat', label: 'AI Chat', icon: MessageSquare },
];

export default function Sidebar() {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const repoId = searchParams.get('repo');

  const to = (path: string) => (repoId ? `${path}?repo=${repoId}` : path);

  return (
    <aside className="w-60 h-screen flex flex-col border-r border-[var(--border-color)] bg-[var(--bg-secondary)] flex-shrink-0">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-[var(--border-color)]">
        <div className="flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center shadow-lg"
            style={{ background: 'var(--gradient-primary)' }}
          >
            <Shield className="w-[18px] h-[18px] text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold gradient-text leading-tight">RIE</h1>
            <p className="text-[10px] text-[var(--text-muted)] tracking-wide uppercase">Intelligence Engine</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 overflow-y-auto">
        <p className="section-label px-3 mb-2">Navigation</p>
        <div className="space-y-0.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <NavLink
                key={item.path}
                to={to(item.path)}
                className={`sidebar-link ${isActive ? 'active' : ''}`}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </div>
      </nav>

      {/* Footer */}
      <div className="px-3 py-3 border-t border-[var(--border-color)]">
        <div className="rounded-lg bg-[var(--bg-primary)] border border-[var(--border-subtle)] p-2.5 text-center">
          <p className="text-[10px] text-[var(--text-muted)] tracking-wide">v0.1.0 · Phase 1</p>
        </div>
      </div>
    </aside>
  );
}
