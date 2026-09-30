import { GraphMotif } from './GraphMotif';
import { useModal } from '../contexts/ModalContext';

export default function NoRepository() {
  const { openRepositoryModal } = useModal();

  return (
    <div className="flex flex-col items-center justify-center min-h-[68vh] px-6 py-16 animate-fade-in text-center max-w-3xl mx-auto">
      {/* Network Diagram */}
      <div className="mb-8 relative group">
        <div className="absolute inset-0 bg-amber-500/10 rounded-full blur-3xl transition-all group-hover:bg-amber-500/20" />
        <div className="relative text-amber-500/70 hover:text-amber-500 transition-all duration-300 transform group-hover:scale-105">
          <GraphMotif size={240} />
        </div>
      </div>

      {/* Headline */}
      <h2 className="text-3xl sm:text-4xl font-extrabold mb-4 tracking-tight text-gray-100 font-[Plus_Jakarta_Sans]">
        No Repository Selected
      </h2>

      {/* Subtext */}
      <p className="text-base sm:text-lg text-gray-400 max-w-xl mx-auto mb-8 leading-relaxed">
        Add a GitHub repository or open a local folder to analyze its architecture, discover APIs, map database dependencies, and query the codebase knowledge graph.
      </p>

      {/* CTA Button */}
      <button
        onClick={openRepositoryModal}
        className="btn-primary px-8 py-3.5 text-base font-semibold rounded-xl flex items-center gap-3 shadow-xl shadow-amber-500/20 hover:scale-[1.02] transition-all"
      >
        <span className="text-xl font-bold">+</span> Add Repository
      </button>

      {/* Footer hint */}
      <p className="mt-10 text-xs text-gray-500 font-medium tracking-wide">
        Supports public repositories &amp; authenticated private repositories
      </p>
    </div>
  );
}

