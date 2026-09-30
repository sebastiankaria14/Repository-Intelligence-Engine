/**
 * RIE Frontend — API Client
 * Axios-based HTTP client for the FastAPI backend.
 */

import axios, { type AxiosInstance } from 'axios';

import type {
  APIDiscoveryResponse,
  ArchitectureResponse,
  ChatMessage,
  ChatRequest,
  ChatResponse,
  DatabaseResponse,
  DependencyResponse,
  GitInsightsResponse,
  GraphResponse,
  HealthResponse,
  PerformanceResponse,
  Repository,
  RepositoryCreateRequest,
  RepositoryListResponse,
  RepositorySummary,
  ScanJob,
  SecurityResponse,
  TechnicalDebtResponse,
} from '../types/api';

const isDev = import.meta.env.DEV;
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== 'undefined'
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : 'http://localhost:8000');

const api: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': import.meta.env.VITE_API_KEY || 'rie_dev_api_key',
  },
  timeout: 20000,
});

api.interceptors.request.use(
  (config) => {
    if (isDev) {
      console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    }
    return config;
  },
  (error) => Promise.reject(error),
);

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (!originalRequest) return Promise.reject(error);

    const shouldRetry =
      (error.response?.status === 429 || error.response?.status === 502 || error.response?.status === 503) &&
      !originalRequest._retry;

    if (shouldRetry) {
      originalRequest._retry = true;
      const delay = Math.min(1000 * 2 ** (originalRequest._retryCount ?? 0), 8000);
      originalRequest._retryCount = (originalRequest._retryCount ?? 0) + 1;
      await new Promise((resolve) => setTimeout(resolve, delay));
      return api(originalRequest);
    }

    return Promise.reject(error);
  },
);

// ── Repository API ─────────────────────────────────────────

export const repositoryApi = {
  create: (payload: RepositoryCreateRequest) =>
    api.post<Repository>('/repositories', payload),

  list: (skip = 0, limit = 20) =>
    api.get<{ repositories: Repository[]; total: number }>('/repositories', {
      params: { skip, limit },
    }),

  get: (id: string) =>
    api.get<Repository>(`/repositories/${id}`),

  getStatus: (id: string) =>
    api.get<ScanJob>(`/repositories/${id}/status`),

  getArchitecture: (id: string) =>
    api.get<ArchitectureResponse>(`/repositories/${id}/architecture`),

  getApis: (id: string) =>
    api.get<APIDiscoveryResponse>(`/repositories/${id}/apis`),

  getDatabase: (id: string) =>
    api.get<DatabaseResponse>(`/repositories/${id}/database`),

  getDependencies: (id: string) =>
    api.get<DependencyResponse>(`/repositories/${id}/dependencies`),

  getGitInsights: (id: string) =>
    api.get<GitInsightsResponse>(`/repositories/${id}/git-insights`),

  getSecurity: (id: string) =>
    api.get<SecurityResponse>(`/repositories/${id}/security`),

  getPerformance: (id: string) =>
    api.get<PerformanceResponse>(`/repositories/${id}/performance`),

  getTechnicalDebt: (id: string) =>
    api.get<TechnicalDebtResponse>(`/repositories/${id}/technical-debt`),

  getGraph: (id: string, nodeType?: string, limit = 200) =>
    api.get<GraphResponse>(`/repositories/${id}/graph`, {
      params: { node_type: nodeType, limit },
    }),

  getSummary: async (id: string): Promise<RepositorySummary> => {
    const results = await Promise.allSettled([
      repositoryApi.get(id),
      repositoryApi.getStatus(id),
      repositoryApi.getArchitecture(id),
      repositoryApi.getSecurity(id),
      repositoryApi.getPerformance(id),
      repositoryApi.getTechnicalDebt(id),
      repositoryApi.getApis(id),
      repositoryApi.getDatabase(id),
      repositoryApi.getDependencies(id),
    ]);

    const [
      repoRes,
      scanRes,
      archRes,
      _secRes,
      _perfRes,
      debtRes,
      apiRes,
      dbRes,
      depRes,
    ] = results;

    const repository = repoRes.status === 'fulfilled' ? repoRes.value.data : null;
    const scan_job = scanRes.status === 'fulfilled' ? scanRes.value.data : null;
    const architecture = archRes.status === 'fulfilled' ? archRes.value.data : null;

    const statistics =
      repoRes.status === 'fulfilled'
        ? {
            endpoints: apiRes.status === 'fulfilled' ? apiRes.value.data.total : 0,
            tables: dbRes.status === 'fulfilled' ? dbRes.value.data.tables.length : 0,
            packages: depRes.status === 'fulfilled' ? depRes.value.data.total : 0,
            findings: 0,
            debt_items: debtRes.status === 'fulfilled' ? debtRes.value.data.items.length : 0,
            total_effort_hours: debtRes.status === 'fulfilled' ? debtRes.value.data.total_effort_hours : 0,
            risk_score: 0,
          }
        : null;

    if (!repository) {
      throw new Error('Failed to load repository');
    }

    return { repository, scan_job, architecture, statistics };
  },

  chat: (id: string, payload: { message: string; history: ChatMessage[] }) =>
    api.post<ChatResponse>(`/repositories/${id}/chat`, payload as ChatRequest),
};

// ── Health API ──────────────────────────────────────────────

export const healthApi = {
  check: () =>
    axios.get<HealthResponse>(`${API_BASE_URL}/health`),
};

export type { ChatMessage } from '../types/api';

export {
  type APIDiscoveryResponse,
  type ArchitectureResponse,
  type ChatResponse,
  type DatabaseResponse,
  type DependencyResponse,
  type GitInsightsResponse,
  type GraphResponse,
  type HealthResponse,
  type PerformanceResponse,
  type Repository,
  type RepositoryListResponse,
  type ScanJob,
  type SecurityResponse,
  type TechnicalDebtResponse,
};

export default api;
