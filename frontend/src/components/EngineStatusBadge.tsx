import { useEffect, useState } from 'react';
import { Cpu, RefreshCw } from 'lucide-react';
import { healthApi } from '../lib/api';

export default function EngineStatusBadge() {
  const [status, setStatus] = useState<'online' | 'starting' | 'offline'>('online');
  const [details, setDetails] = useState<string>('Port 8000 · 100% Offline');
  const [isRestarting, setIsRestarting] = useState(false);
  const isElectron = Boolean(window.electronAPI?.isElectron);

  const checkStatus = async () => {
    if (isElectron && window.electronAPI?.getPipelineStatus) {
      try {
        const res = await window.electronAPI.getPipelineStatus();
        if (res.running) {
          setStatus('online');
          setDetails(`Port ${res.port} · PID ${res.pid || 'N/A'} · 100% Offline`);
        } else {
          setStatus('offline');
          setDetails('Engine stopped');
        }
      } catch {
        setStatus('offline');
        setDetails('Engine offline');
      }
    } else {
      try {
        const res = await healthApi.check();
        if (res.data.status === 'healthy') {
          setStatus('online');
          setDetails('Port 8000 · 100% Offline · Zero API Keys');
        } else {
          setStatus('offline');
          setDetails('Engine status: degraded');
        }
      } catch {
        setStatus('offline');
        setDetails('Engine offline');
      }
    }
  };

  useEffect(() => {
    void checkStatus();
    const interval = setInterval(checkStatus, 6000);

    let unsubStatus: (() => void) | undefined;
    if (isElectron && window.electronAPI?.onPipelineStatus) {
      unsubStatus = window.electronAPI.onPipelineStatus((event) => {
        if (event.status === 'running') {
          setStatus('online');
          setDetails('Port 8000 · 100% Offline');
        } else if (event.status === 'starting') {
          setStatus('starting');
          setDetails('Starting engine...');
        } else if (event.status === 'stopped' || event.status === 'error') {
          setStatus('offline');
          setDetails('Engine stopped');
        }
      });
    }

    return () => {
      clearInterval(interval);
      if (unsubStatus) unsubStatus();
    };
  }, [isElectron]);

  const handleRestart = async () => {
    if (isElectron && window.electronAPI?.restartPipelineEngine) {
      setIsRestarting(true);
      setStatus('starting');
      setDetails('Restarting engine...');
      try {
        await window.electronAPI.restartPipelineEngine();
        await checkStatus();
      } catch (err) {
        console.error('Failed to restart engine:', err);
      } finally {
        setIsRestarting(false);
      }
    }
  };

  return (
    <div
      title={details}
      className="rounded-xl bg-[#1e2330]/70 border border-white/5 p-2.5 space-y-1.5"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Cpu className="w-3.5 h-3.5 text-amber-400" />
          <span className="text-[11px] font-semibold text-gray-200 font-mono">Analysis Engine</span>
        </div>
        <div className="flex items-center gap-1">
          <span
            className={`w-2 h-2 rounded-full ${
              status === 'online'
                ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]'
                : status === 'starting'
                ? 'bg-amber-400 animate-pulse'
                : 'bg-rose-400'
            }`}
          />
          <span
            className={`text-[10px] font-mono font-medium ${
              status === 'online'
                ? 'text-emerald-400'
                : status === 'starting'
                ? 'text-amber-400'
                : 'text-rose-400'
            }`}
          >
            {status === 'online' ? 'Online' : status === 'starting' ? 'Starting' : 'Offline'}
          </span>
        </div>
      </div>

      <div className="text-[10px] text-gray-400 flex items-center justify-between">
        <span className="truncate pr-1">{details}</span>
        {isElectron && (
          <button
            onClick={handleRestart}
            disabled={isRestarting}
            title="Restart Local Python Engine"
            className="p-1 hover:bg-white/10 rounded transition-colors text-gray-400 hover:text-amber-400 disabled:opacity-50 flex-shrink-0"
            style={{ border: 'none' }}
          >
            <RefreshCw className={`w-3 h-3 ${isRestarting ? 'animate-spin text-amber-400' : ''}`} />
          </button>
        )}
      </div>
    </div>
  );
}
