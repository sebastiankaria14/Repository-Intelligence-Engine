import React, { useState, useRef, useEffect } from 'react';
import { X, Loader2, AlertCircle, CheckCircle2, FolderOpen } from 'lucide-react';

interface RepositoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (url: string) => Promise<void>;
}

export const RepositoryModal: React.FC<RepositoryModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
}) => {
  const [url, setUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isValid, setIsValid] = useState<boolean | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Focus input on modal open
  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
    }
  }, [isOpen]);

  const handleSelectLocalFolder = async () => {
    if (window.electronAPI) {
      try {
        const folderPath = await window.electronAPI.selectFolder();
        if (folderPath) {
          setUrl(folderPath);
          setIsValid(true);
          setError(null);
        }
      } catch (err) {
        setError('Failed to open local folder dialog');
      }
    }
  };

  // Validate URL format or local directory path
  const validateUrl = async (value: string) => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);

    const trimmed = value.trim();
    if (!trimmed) {
      setIsValid(null);
      setError(null);
      return;
    }

    // Check if it is a local filesystem path
    const isLocalPath = /^[a-zA-Z]:[\\/]|^[\\/]|\.\/|\.\.\//.test(trimmed);
    const githubRegex = /^(https?:\/\/)?(github\.com\/)?[\w-]+\/[\w.-]+\/?$/i;

    if (!isLocalPath && !githubRegex.test(trimmed)) {
      setIsValid(false);
      setError('Please enter a local directory path or GitHub repository URL');
      return;
    }

    setIsValid(null);
    setError(null);

    timeoutRef.current = setTimeout(() => {
      setIsValid(true);
      setError(null);
    }, 400);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setUrl(value);
    validateUrl(value);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!isValid || !url.trim()) {
      setError('Please enter a valid repository URL');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await onSubmit(url);
      setUrl('');
      setIsValid(null);
      onClose();
    } catch (err: unknown) {
      let msg = err instanceof Error ? err.message : 'Failed to add repository';
      if (msg === 'Network Error' || (err as { code?: string })?.code === 'ERR_NETWORK') {
        msg = 'Cannot reach local analysis engine on port 8000. Please wait for the engine to initialize or click restart in the top bar.';
      }
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/75 backdrop-blur-md transition-opacity animate-fade-in"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed left-1/2 top-1/2 z-50 w-full max-w-2xl lg:max-w-[720px] -translate-x-1/2 -translate-y-1/2 p-6">
        <div
          className="glass-card p-10 lg:p-12 space-y-8 rounded-3xl bg-[#171b24]/98 border border-white/15 shadow-2xl backdrop-blur-2xl animate-fade-in-up"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-start justify-between pb-5 border-b border-white/10">
            <div>
              <h2 className="text-2xl font-bold tracking-tight text-gray-100 font-[Plus_Jakarta_Sans]">
                Open Code Repository
              </h2>
              <p className="text-sm text-gray-400 mt-2 leading-relaxed">
                Select a local repository folder from your computer or enter a repository path/URL for instant offline analysis.
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-2.5 hover:bg-white/10 rounded-xl transition-all text-gray-400 hover:text-gray-100 cursor-pointer -mr-2 -mt-1"
              aria-label="Close"
            >
              <X size={22} />
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-7">
            {/* Desktop Local Folder Action */}
            <div>
              <button
                type="button"
                onClick={handleSelectLocalFolder}
                className="btn-secondary w-full py-4 px-6 rounded-2xl flex items-center justify-center gap-3 text-base font-semibold cursor-pointer shadow-md shadow-black/20"
              >
                <FolderOpen size={20} className="text-amber-400" />
                <span>Browse Local Repository Folder</span>
              </button>
            </div>

            <div className="flex items-center gap-4 my-4">
              <div className="flex-1 h-px bg-white/10" />
              <span className="text-xs text-gray-400 font-medium uppercase tracking-widest">Or enter path manually</span>
              <div className="flex-1 h-px bg-white/10" />
            </div>

            {/* Input Field */}
            <div className="space-y-2.5">
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-300">
                Repository Path or URL
              </label>
              <div className="relative">
                <input
                  ref={inputRef}
                  type="text"
                  value={url}
                  onChange={handleInputChange}
                  onKeyDown={handleKeyDown}
                  placeholder="e.g. C:\projects\my-app or https://github.com/owner/repo"
                  className="w-full px-5 py-4 h-14 rounded-2xl text-base bg-[#0d0f12] border border-white/15 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20 transition-all shadow-inner font-mono"
                  disabled={isLoading}
                />

                {/* Status Icon */}
                {url && (
                  <div className="absolute right-5 top-1/2 -translate-y-1/2">
                    {isLoading ? (
                      <Loader2
                        size={20}
                        className="animate-spin text-amber-500"
                      />
                    ) : isValid ? (
                      <CheckCircle2 size={20} className="text-emerald-400" />
                    ) : (
                      <AlertCircle size={20} className="text-rose-400" />
                    )}
                  </div>
                )}
              </div>

              {/* Validation Message */}
              {error && (
                <div className="flex items-center gap-2 pt-1 text-sm text-rose-400 font-medium">
                  <AlertCircle size={16} />
                  <span>{error}</span>
                </div>
              )}
              {!error && isValid === null && url && (
                <p className="text-sm pt-1 text-gray-400 font-medium">
                  Validating repository connection...
                </p>
              )}
            </div>

            {/* Help Text */}
            <div className="p-5 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-200/90 leading-relaxed flex items-center gap-3.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400 flex-shrink-0 animate-ping" />
              <p>
                <strong>Local Folders & Public repositories</strong> are analyzed completely on-device with zero external API dependencies.
              </p>
            </div>

            {/* Actions */}
            <div className="flex gap-4 justify-end pt-3">
              <button
                type="button"
                onClick={onClose}
                className="btn-secondary px-8 py-3.5 rounded-2xl text-sm font-semibold cursor-pointer"
                disabled={isLoading}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn-primary px-9 py-3.5 rounded-2xl text-sm font-semibold flex items-center gap-2 shadow-lg shadow-amber-500/25 cursor-pointer"
                disabled={!isValid || isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Analyzing Codebase...
                  </>
                ) : (
                  '+ Analyze Repository'
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
};
