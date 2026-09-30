import { NavLink, useLocation, useSearchParams } from 'react-router-dom';
import {
  LayoutDashboard,
  Boxes,
  Globe,
  Database,
  GitBranch,
  Network,
  MessageSquare,
  Zap,
} from 'lucide-react';
import EngineStatusBadge from './EngineStatusBadge';

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
    <aside className="w-[var(--sidebar-width)] h-[calc(100vh-var(--header-height))] flex flex-col border-r border-white/[0.08] bg-[#12151b] flex-shrink-0 z-20">
      {/* Navigation */}
      <nav className="flex-1 px-4 py-6 overflow-y-auto space-y-6">
        <div>
          <p className="px-3 text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-3">Navigation</p>
          <div className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <NavLink
                  key={item.path}
                  to={to(item.path)}
                  className={`sidebar-link ${isActive ? 'active' : ''}`}
                >
                  <Icon className={`w-4 h-4 flex-shrink-0 transition-colors ${isActive ? 'text-amber-400' : 'text-gray-400'}`} />
                  <span className="font-medium">{item.label}</span>
                </NavLink>
              );
            })}
          </div>
        </div>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-white/[0.08] space-y-2">
        <EngineStatusBadge />
        <div className="rounded-xl bg-[#1e2330]/50 border border-white/5 p-2 text-center">
          <p className="text-[10px] font-medium text-gray-400 tracking-wider uppercase">v0.1.0 · 100% Offline</p>
        </div>
      </div>
    </aside>
  );
}
