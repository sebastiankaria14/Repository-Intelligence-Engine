/**
 * RIE Frontend — WebSocket Client
 * Real-time scan progress updates.
 */

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8001';

export interface ScanProgress {
  repo_id: string;
  scan_job_id: string;
  status: string;
  phase: string;
  progress: number;
  message: string;
  timestamp: string;
}

export type ScanProgressCallback = (progress: ScanProgress) => void;

export class ScanWebSocket {
  private ws: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private callbacks: ScanProgressCallback[] = [];
  private repoId: string;

  constructor(repoId: string) {
    this.repoId = repoId;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    const url = `${WS_BASE_URL}/ws/scan/${this.repoId}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log(`[WS] Connected to scan progress for ${this.repoId}`);
    };

    this.ws.onmessage = (event) => {
      try {
        const data: ScanProgress = JSON.parse(event.data);
        this.callbacks.forEach((cb) => cb(data));
      } catch (err) {
        console.error('[WS] Failed to parse message:', err);
      }
    };

    this.ws.onclose = () => {
      console.log('[WS] Connection closed');
      // Auto-reconnect after 3 seconds
      this.reconnectTimer = setTimeout(() => this.connect(), 3000);
    };

    this.ws.onerror = (err) => {
      console.error('[WS] Error:', err);
    };
  }

  onProgress(callback: ScanProgressCallback): () => void {
    this.callbacks.push(callback);
    return () => {
      this.callbacks = this.callbacks.filter((cb) => cb !== callback);
    };
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
