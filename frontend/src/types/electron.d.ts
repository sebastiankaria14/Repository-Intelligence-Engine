export interface PipelineEngineStatus {
  running: boolean;
  managed: boolean;
  pid: number | null;
  port: number;
  health: any | null;
}

export interface PipelineLogMessage {
  type: 'stdout' | 'stderr';
  message: string;
  time: number;
}

export interface PipelineStatusEvent {
  status: 'starting' | 'running' | 'stopped' | 'error';
  details: Record<string, any>;
  timestamp: number;
}

export interface ElectronAPI {
  isElectron: boolean;
  // Dialogs & Filesystem
  selectFolder: () => Promise<string | null>;

  // App Info & Shell
  getAppInfo: () => Promise<{
    version: string;
    name: string;
    platform: string;
    userDataPath: string;
  }>;

  // Window Controls
  minimizeWindow: () => void;
  maximizeWindow: () => void;
  closeWindow: () => void;

  // Local Analysis Engine IPC Management
  getPipelineStatus: () => Promise<PipelineEngineStatus>;
  startPipelineEngine: () => Promise<{ success: boolean; message?: string; managed?: boolean; pid?: number; error?: string }>;
  stopPipelineEngine: () => Promise<{ success: boolean; message?: string; error?: string }>;
  restartPipelineEngine: () => Promise<{ success: boolean; message?: string; managed?: boolean; pid?: number; error?: string }>;
  checkPipelineHealth: () => Promise<{ ok: boolean; data?: any; error?: string; status?: number }>;

  // Stream Listeners
  onPipelineLog: (callback: (log: PipelineLogMessage) => void) => () => void;
  onPipelineStatus: (callback: (status: PipelineStatusEvent) => void) => () => void;
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI;
  }
}
