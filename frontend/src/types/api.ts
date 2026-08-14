/**
 * RIE Frontend — API Response Types
 * Mirrors the Pydantic schemas in backend/app/models/schemas.py.
 */

import type { AxiosResponse } from 'axios';

export interface ApiResponse<T> extends AxiosResponse<T> {}

// ── Repository ─────────────────────────────────────────────

export interface Repository {
  id: string;
  github_url: string;
  name: string;
  default_branch?: string;
  languages?: string[];
  frameworks?: string[];
  package_managers?: string[];
  is_monorepo?: boolean;
  total_files?: number;
  total_lines?: number;
  health_score?: number | null;
  created_at?: string;
  updated_at?: string;
}

export interface RepositoryListResponse {
  repositories: Repository[];
  total: number;
}

export interface RepositoryCreateRequest {
  github_url: string;
  project_name?: string;
}

// ── Scan Job ───────────────────────────────────────────────

export type ScanStatus =
  | 'pending'
  | 'cloning'
  | 'parsing'
  | 'analyzing'
  | 'building_graph'
  | 'embedding'
  | 'indexing'
  | 'completed'
  | 'failed';

export interface ScanJob {
  id: string;
  repository_id: string;
  status: ScanStatus;
  current_phase: string | null;
  progress: number;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  results_summary: Record<string, unknown>;
  created_at: string;
}

// ── Health ─────────────────────────────────────────────────

export interface ServiceHealth {
  name: string;
  status: 'healthy' | 'unhealthy' | 'unavailable';
  latency_ms: number | null;
  details: string | null;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded';
  version: string;
  services: ServiceHealth[];
}

// ── Architecture ───────────────────────────────────────────

export interface ArchitectureLayer {
  name: string;
  description: string;
  components: string[];
  file_count: number;
}

export interface ArchitectureDiagram {
  nodes: Array<Record<string, unknown>>;
  edges: Array<Record<string, unknown>>;
}

export interface ArchitectureResponse {
  repository_id: string;
  pattern: string;
  confidence: number;
  layers: ArchitectureLayer[];
  diagram: ArchitectureDiagram;
}

// ── API Discovery ──────────────────────────────────────────

export interface APIEndpoint {
  method: string;
  path: string;
  handler: string;
  file_path: string;
  line_number: number;
  parameters: Array<Record<string, string>>;
  auth_required: boolean;
  middleware: string[];
  description: string | null;
}

export interface APIDiscoveryResponse {
  repository_id: string;
  endpoints: APIEndpoint[];
  total: number;
  frameworks_detected: string[];
}

// ── Database Intelligence ──────────────────────────────────

export interface DatabaseColumn {
  name: string;
  type: string;
  nullable: boolean;
  default_value: string | null;
}

export interface DatabaseForeignKey {
  column: string;
  referenced_table: string;
  referenced_column: string;
}

export interface DatabaseTable {
  name: string;
  columns: DatabaseColumn[];
  foreign_keys: DatabaseForeignKey[];
  indexes: string[];
  source_file: string;
  orm_model: string | null;
}

export interface Relationship {
  from_table: string;
  to_table: string;
  type: string;
}

export interface Migration {
  id: string;
  name: string;
  applied_at: string;
}

export interface ERDiagram {
  nodes: Array<Record<string, unknown>>;
  edges: Array<Record<string, unknown>>;
}

export interface DatabaseResponse {
  repository_id: string;
  tables: DatabaseTable[];
  relationships: Relationship[];
  migrations: Migration[];
  er_diagram: ERDiagram;
}

// ── Dependencies ───────────────────────────────────────────

export type DependencyType = 'runtime' | 'dev' | 'peer';

export interface DependencyNode {
  name: string;
  version: string | null;
  type: DependencyType;
  source: string;
}

export interface DependencyGraph {
  nodes: Array<Record<string, unknown>>;
  edges: Array<Record<string, unknown>>;
}

export interface DependencyResponse {
  repository_id: string;
  packages: DependencyNode[];
  service_graph: DependencyGraph;
  circular_dependencies: string[][];
  total: number;
}

// ── Git Intelligence ───────────────────────────────────────

export interface ContributorStats {
  name: string;
  email: string;
  commits: number;
  lines_added: number;
  lines_deleted: number;
  first_commit: string;
  last_commit: string;
  owned_files: string[];
}

export interface HotspotFile {
  file: string;
  changes: number;
  authors: number;
}

export interface ChangeCoupling {
  file_a: string;
  file_b: string;
  coupling_strength: number;
}

export interface GitInsightsResponse {
  repository_id: string;
  total_commits: number;
  total_contributors: number;
  contributors: ContributorStats[];
  hotspot_files: HotspotFile[];
  change_coupling: ChangeCoupling[];
  commit_frequency: Record<string, number>;
}

// ── Security ───────────────────────────────────────────────

export type FindingSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';

export interface SecurityFinding {
  id: string;
  severity: FindingSeverity;
  title: string;
  description: string;
  file_path: string;
  line_start: number;
  line_end: number | null;
  rule_id: string;
  tool: string;
  recommendation: string | null;
  affected_services: string[];
}

export interface SecurityResponse {
  repository_id: string;
  findings: SecurityFinding[];
  summary: Record<string, number>;
  risk_score: number;
}

// ── Performance ────────────────────────────────────────────

export type PerformanceFindingType = 'n_plus_one' | 'large_object' | 'circular_dep' | 'heavy_endpoint';

export interface PerformanceFinding {
  type: PerformanceFindingType;
  severity: FindingSeverity;
  title: string;
  description: string;
  file_path: string;
  line_number: number | null;
  recommendation: string;
}

export interface PerformanceResponse {
  repository_id: string;
  findings: PerformanceFinding[];
  summary: Record<string, number>;
}

// ── Technical Debt ─────────────────────────────────────────

export type DebtType = 'dead_code' | 'duplication' | 'god_class' | 'long_method' | 'legacy';
export type DebtRisk = 'low' | 'medium' | 'high' | 'critical';

export interface DebtItem {
  type: DebtType;
  severity: FindingSeverity;
  title: string;
  description: string;
  file_path: string;
  effort_hours: number;
  priority: number;
  risk: DebtRisk;
}

export interface TechnicalDebtResponse {
  repository_id: string;
  items: DebtItem[];
  total_effort_hours: number;
  debt_score: number;
  summary: Record<string, number>;
}

// ── Knowledge Graph ────────────────────────────────────────

export interface GraphNode {
  id: string;
  label: string;
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  properties: Record<string, unknown>;
}

export interface GraphResponse {
  repository_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  total_nodes: number;
  total_edges: number;
}

// ── AI Chat ────────────────────────────────────────────────

export type ChatRole = 'user' | 'assistant';

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface Citation {
  type: string;
  reference: string;
  snippet: string | null;
  relevance_score: number;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  model_used: string;
  reasoning_type: string;
}

export interface ChatRequest {
  message: string;
  history: ChatMessage[];
  model?: string;
}

// ── Repository Summary (aggregated for dashboard) ──────────

export interface RepositorySummary {
  repository: Repository;
  scan_job: ScanJob | null;
  architecture: ArchitectureResponse | null;
  statistics: {
    endpoints: number;
    tables: number;
    packages: number;
    findings: number;
    debt_items: number;
    total_effort_hours: number;
    risk_score: number;
  } | null;
}
