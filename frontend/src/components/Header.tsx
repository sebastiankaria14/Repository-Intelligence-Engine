import { useState, useCallback } from 'react';
import { Search, Bell, Settings, Shield } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useModal } from '../contexts/ModalContext';

export default function Header() {
  const [searchQuery, setSearchQuery] = useState('');
  const { openRepositoryModal } = useModal();
  const navigate = useNavigate();
  const location = useLocation();

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
    <header className="h-[var(--header-height)] border-b border-white/[0.08] bg-[#12151b] flex items-center justify-between flex-shrink-0 sticky top-0 z-40 w-full select-none">
      {/* Logo Section — unified seamless header */}
      <div className="flex items-center gap-3.5 px-6 pl-8 h-full flex-shrink-0">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-amber-500 to-amber-700 flex items-center justify-center shadow-md shadow-amber-500/20 flex-shrink-0">
          <Shield className="w-5 h-5 text-white" />
        </div>
        <div className="flex flex-col justify-center">
          <h1 className="text-base font-extrabold tracking-tight text-gray-100 font-[Plus_Jakarta_Sans] leading-none">
            RIE
          </h1>
          <p className="text-[9px] text-amber-400/90 font-semibold tracking-[0.14em] uppercase mt-1 leading-none">
            Intelligence Engine
          </p>
        </div>
      </div>

      {/* Search Bar — with guaranteed spacing between icon and placeholder */}
      <div className="flex items-center flex-1 max-w-xl mx-8">
        <div className="relative w-full">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none z-10" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Ask AI assistant about this repository..."
            style={{ paddingLeft: '48px' }}
            className="w-full h-10 pr-4 rounded-xl bg-[#1e2330]/80 border border-white/10 text-sm text-gray-100 placeholder-gray-400 focus:outline-none focus:border-amber-500/60 focus:ring-2 focus:ring-amber-500/15 transition-all shadow-inner"
          />
        </div>
      </div>

      {/* Actions — shifted inward from extreme corner */}
      <div className="flex items-center gap-3.5 pr-10 lg:pr-14 flex-shrink-0">
        <button
          onClick={openRepositoryModal}
          className="btn-primary h-10 px-5 text-sm font-semibold rounded-xl flex items-center gap-2 shadow-md shadow-amber-500/20"
        >
          <span className="text-base font-bold leading-none">+</span> Add Repository
        </button>

        <div className="h-5 w-px bg-white/10 mx-1" />

        <button
          title="Notifications"
          className="p-2.5 rounded-xl bg-white/5 hover:bg-white/10 transition-all text-gray-400 hover:text-gray-100 flex items-center justify-center cursor-pointer"
        >
          <Bell className="w-4 h-4" />
        </button>

        <button
          title="Settings"
          className="p-2.5 rounded-xl bg-white/5 hover:bg-white/10 transition-all text-gray-400 hover:text-gray-100 flex items-center justify-center cursor-pointer"
        >
          <Settings className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}
