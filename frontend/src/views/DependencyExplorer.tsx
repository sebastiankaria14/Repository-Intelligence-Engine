import { useState, useMemo, useEffect, useCallback } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  type Node,
  type Edge,
  type NodeProps,
  ReactFlowProvider,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  Package,
  AlertTriangle,
  Network,
  List,
  Search,
  X,
  Radio,
  ArrowRight,
  ShieldAlert,
  Layers,
} from 'lucide-react';

import NoRepository from '../components/NoRepository';
import DataShell from '../components/DataShell';
import { useCurrentRepoId, useApi } from '../hooks/useRepository';
import type { DependencyResponse, DependencyNode as PackageItem } from '../types/api';
import { repositoryApi } from '../lib/api';

const typeColors: Record<string, string> = {
  runtime: 'var(--accent-green)',
  dev: 'var(--accent-cyan)',
  peer: 'var(--accent-purple)',
};

// ── Custom Dependency / Module Node ──────────────────────────

function DependencyNodeComponent({ data, selected }: NodeProps) {
  const nodeData = data as any;
  const name = nodeData.name || nodeData.label || 'Unknown Module';
  const incoming = nodeData.incoming_count ?? 0;
  const outgoing = nodeData.outgoing_count ?? 0;
  const isCircular = Boolean(nodeData.is_circular);

  // Severity color based on blast radius
  const badgeColor =
    incoming >= 5 ? '#f43f5e' : incoming >= 2 ? '#f59e0b' : '#06b6d4';

  return (
    <div
      className={`relative min-w-[240px] max-w-[300px] rounded-xl border bg-[#0d131f]/95 p-3.5 shadow-2xl backdrop-blur-md transition-all duration-200 ${
        selected
          ? 'border-[var(--accent-cyan)] ring-2 ring-[var(--accent-cyan)]/40 shadow-[0_0_24px_rgba(6,182,212,0.35)]'
          : isCircular
          ? 'border-rose-500/60 shadow-[0_0_16px_rgba(244,63,94,0.2)]'
          : 'border-[rgba(255,255,255,0.08)] hover:border-[rgba(6,182,212,0.4)]'
      }`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!w-2.5 !h-2.5 !bg-[var(--accent-cyan)] !border-2 !border-[#0d131f] !-left-1.5"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!w-2.5 !h-2.5 !bg-[var(--accent-purple)] !border-2 !border-[#0d131f] !-right-1.5"
      />
      <Handle
        type="target"
        position={Position.Top}
        className="!w-2.5 !h-2.5 !bg-[var(--accent-cyan)] !border-2 !border-[#0d131f] !-top-1.5"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-2.5 !h-2.5 !bg-[var(--accent-purple)] !border-2 !border-[#0d131f] !-bottom-1.5"
      />

      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <div
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md border"
            style={{
              background: isCircular ? 'rgba(244,63,94,0.15)' : 'rgba(6,182,212,0.15)',
              borderColor: isCircular ? 'rgba(244,63,94,0.3)' : 'rgba(6,182,212,0.3)',
            }}
          >
            {isCircular ? (
              <AlertTriangle className="h-3.5 w-3.5 text-rose-400" />
            ) : (
              <Layers className="h-3.5 w-3.5 text-[var(--accent-cyan)]" />
            )}
          </div>
          <span className="font-mono text-xs font-semibold text-[var(--text-primary)] truncate">
            {name}
          </span>
        </div>

        {isCircular && (
          <span className="shrink-0 rounded bg-rose-500/20 px-1.5 py-0.5 font-mono text-[9px] font-bold text-rose-300 border border-rose-500/30">
            CIRCULAR
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-[rgba(255,255,255,0.06)] text-[10px] font-mono">
        <div className="flex flex-col">
          <span className="text-[var(--text-muted)] text-[9px] uppercase tracking-wider">Dependents</span>
          <span className="font-bold text-sm" style={{ color: badgeColor }}>
            {incoming}
          </span>
        </div>
        <div className="flex flex-col">
          <span className="text-[var(--text-muted)] text-[9px] uppercase tracking-wider">Calls</span>
          <span className="font-bold text-sm text-[var(--accent-purple)]">
            {outgoing}
          </span>
        </div>
      </div>
    </div>
  );
}

const nodeTypes = {
  dependencyNode: DependencyNodeComponent,
};

// ── Service Graph Canvas ─────────────────────────────────────

function ServiceGraphCanvas({
  rawNodes,
  rawEdges,
  circularDeps,
  onSelectNode,
}: {
  rawNodes: Array<Record<string, unknown>>;
  rawEdges: Array<Record<string, unknown>>;
  circularDeps: string[][];
  onSelectNode: (nodeId: string) => void;
}) {
  const [searchTerm, setSearchTerm] = useState('');

  const initialNodes: Node[] = useMemo(() => {
    return rawNodes.map((n, idx) => {
      const id = String(n.id || `node-${idx}`);
      const pos = (n.position as { x: number; y: number }) || {
        x: (idx % 3) * 360 + 50,
        y: Math.floor(idx / 3) * 280 + 50,
      };
      return {
        id,
        type: 'dependencyNode',
        position: pos,
        data: (n.data as Record<string, unknown>) || { name: id, label: id },
      };
    });
  }, [rawNodes]);

  const initialEdges: Edge[] = useMemo(() => {
    return rawEdges.map((e, idx) => {
      const isCycle = Boolean((e.data as any)?.is_circular);
      return {
        id: String(e.id || `edge-${idx}`),
        source: String(e.source),
        target: String(e.target),
        label: String(e.label || ''),
        animated: isCycle,
        style: {
          stroke: isCycle ? '#f43f5e' : '#06b6d4',
          strokeWidth: isCycle ? 2.5 : 1.5,
        },
        labelStyle: { fill: '#67e8f9', fontSize: 10, fontFamily: 'monospace' },
        labelBgStyle: { fill: '#0d131f', fillOpacity: 0.8 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isCycle ? '#f43f5e' : '#06b6d4',
          width: 12,
          height: 12,
        },
      };
    });
  }, [rawEdges]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
  }, [initialNodes, setNodes]);

  useEffect(() => {
    setEdges(initialEdges);
  }, [initialEdges, setEdges]);

  const filteredNodes = useMemo(() => {
    if (!searchTerm.trim()) return nodes;
    const term = searchTerm.toLowerCase();
    return nodes.map((node) => ({
      ...node,
      style: {
        ...node.style,
        opacity: node.id.toLowerCase().includes(term) ? 1 : 0.2,
      },
    }));
  }, [nodes, searchTerm]);

  const onNodeClick = useCallback(
    (_: any, node: Node) => {
      onSelectNode(node.id);
    },
    [onSelectNode]
  );

  return (
    <div className="relative w-full h-[620px] rounded-xl border border-[var(--border-subtle)] bg-[#070b13] overflow-hidden shadow-inner">
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--text-muted)]" />
          <input
            type="text"
            placeholder="Search module or service..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="h-8 pl-8 pr-3 text-xs rounded-lg bg-[#0d131f]/90 border border-[rgba(255,255,255,0.1)] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-cyan)] w-56 backdrop-blur-md"
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-white"
              style={{ border: 'none' }}
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
        {circularDeps.length > 0 && (
          <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono font-medium rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-300 backdrop-blur-md">
            <AlertTriangle className="w-3.5 h-3.5" />
            {circularDeps.length} Cycle{circularDeps.length > 1 ? 's' : ''} Detected
          </span>
        )}
      </div>

      <ReactFlow
        nodes={filteredNodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        fitView
        fitViewOptions={{ padding: 0.25 }}
        minZoom={0.2}
        maxZoom={2}
      >
        <Background color="#1e293b" gap={20} size={1} />
        <Controls className="!bg-[#0d131f] !border-[rgba(255,255,255,0.1)] !rounded-lg !overflow-hidden [&>button]:!bg-[#0d131f] [&>button]:!border-none [&>button]:!text-[var(--text-secondary)] hover:[&>button]:!text-white" />
        <MiniMap
          nodeColor="#06b6d4"
          maskColor="rgba(7, 11, 19, 0.75)"
          className="!bg-[#0d131f] !border-[rgba(255,255,255,0.1)] !rounded-lg"
        />
      </ReactFlow>
    </div>
  );
}

// ── Blast-Radius Inspection Drawer ───────────────────────────

function BlastRadiusDrawer({
  nodeId,
  rawEdges,
  circularDeps,
  onClose,
}: {
  nodeId: string;
  rawEdges: Array<Record<string, unknown>>;
  circularDeps: string[][];
  onClose: () => void;
}) {
  // Compute Direct Dependents (who imports nodeId: edge.target === nodeId)
  const directDependents = useMemo(() => {
    return rawEdges
      .filter((e) => String(e.target) === nodeId)
      .map((e) => String(e.source));
  }, [rawEdges, nodeId]);

  // Compute Outgoing Dependencies (who nodeId calls: edge.source === nodeId)
  const outgoingDependencies = useMemo(() => {
    return rawEdges
      .filter((e) => String(e.source) === nodeId)
      .map((e) => String(e.target));
  }, [rawEdges, nodeId]);

  // Check if nodeId is part of any circular dependency
  const involvedCycles = useMemo(() => {
    return circularDeps.filter((cycle) => cycle.includes(nodeId));
  }, [circularDeps, nodeId]);

  // Calculate Impact Score
  const impactSeverity =
    directDependents.length >= 5
      ? 'Critical'
      : directDependents.length >= 2
      ? 'Moderate'
      : 'Low';

  const severityColor =
    impactSeverity === 'Critical'
      ? 'text-rose-400 bg-rose-500/10 border-rose-500/30'
      : impactSeverity === 'Moderate'
      ? 'text-amber-400 bg-amber-500/10 border-amber-500/30'
      : 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30';

  return (
    <div className="glass-card p-5 border border-[rgba(6,182,212,0.3)] shadow-2xl animate-fade-in">
      <div className="flex items-center justify-between pb-3 border-b border-[var(--border-subtle)] mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[rgba(6,182,212,0.15)] flex items-center justify-center border border-[rgba(6,182,212,0.3)]">
            <Radio className="w-4 h-4 text-[var(--accent-cyan)]" />
          </div>
          <div>
            <h3 className="text-sm font-semibold font-mono text-[var(--text-primary)]">
              {nodeId}
            </h3>
            <p className="text-[11px] text-[var(--text-muted)]">Blast-Radius & Impact Analysis</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${severityColor}`}>
            {impactSeverity} Blast Impact
          </span>
          <button
            onClick={onClose}
            className="p-1.5 text-[var(--text-muted)] hover:text-white rounded-lg hover:bg-[rgba(255,255,255,0.05)] transition-colors"
            style={{ border: 'none' }}
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {involvedCycles.length > 0 && (
        <div className="mb-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs">
          <div className="flex items-center gap-2 text-rose-400 font-semibold mb-1">
            <ShieldAlert className="w-4 h-4" />
            <span>Participates in Circular Dependency</span>
          </div>
          {involvedCycles.map((c, i) => (
            <div key={i} className="font-mono text-[11px] text-rose-300">
              {c.join(' → ')} → {c[0]}
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <h4 className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-2 flex items-center gap-1.5">
            <Radio className="w-3.5 h-3.5 text-rose-400" />
            Direct Dependents / Inward Impact ({directDependents.length})
          </h4>
          {directDependents.length === 0 ? (
            <p className="text-xs text-[var(--text-muted)] italic">
              No inward dependencies detected. Breaking changes here have low ripple effects.
            </p>
          ) : (
            <div className="space-y-1.5 max-h-48 overflow-y-auto font-mono text-xs">
              {directDependents.map((dep) => (
                <div
                  key={dep}
                  className="flex items-center justify-between p-2 rounded bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)]"
                >
                  <span className="text-[var(--text-primary)]">{dep}</span>
                  <span className="text-[10px] text-rose-400 bg-rose-500/10 px-1.5 py-0.5 rounded border border-rose-500/20">
                    impacted
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div>
          <h4 className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-2 flex items-center gap-1.5">
            <ArrowRight className="w-3.5 h-3.5 text-[var(--accent-purple)]" />
            Outgoing Calls / Dependencies ({outgoingDependencies.length})
          </h4>
          {outgoingDependencies.length === 0 ? (
            <p className="text-xs text-[var(--text-muted)] italic">
              Leaf module (calls no internal subsystems).
            </p>
          ) : (
            <div className="space-y-1.5 max-h-48 overflow-y-auto font-mono text-xs">
              {outgoingDependencies.map((dep) => (
                <div
                  key={dep}
                  className="flex items-center justify-between p-2 rounded bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)]"
                >
                  <span className="text-[var(--accent-cyan)]">{dep}</span>
                  <span className="text-[10px] text-[var(--text-muted)]">imported</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main Dependency Explorer View ────────────────────────────

export default function DependencyExplorer() {
  const repoId = useCurrentRepoId();
  const { data, loading, error, refetch: _refetch } = useApi<DependencyResponse>(
    repoId,
    repositoryApi.getDependencies
  );

  const [viewMode, setViewMode] = useState<'graph' | 'table'>('graph');
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  if (!repoId && !loading && !data) {
    return <NoRepository />;
  }

  const dependencies: PackageItem[] = data?.packages ?? [];
  const circularDeps = data?.circular_dependencies ?? [];
  const serviceNodes = data?.service_graph?.nodes ?? [];
  const serviceEdges = data?.service_graph?.edges ?? [];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="page-header !mb-0">
          <h2 className="gradient-text">Dependency Intelligence</h2>
          <p>Service graph, blast-radius analysis, and manifest package inspection</p>
        </div>

        {/* View Mode Switcher */}
        <div className="flex items-center gap-1 p-1 rounded-xl bg-[rgba(255,255,255,0.03)] border border-[var(--border-subtle)] self-start">
          <button
            onClick={() => setViewMode('graph')}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
              viewMode === 'graph'
                ? 'bg-[var(--accent-cyan)] text-black font-semibold shadow-md'
                : 'text-[var(--text-muted)] hover:text-white'
            }`}
            style={{ border: 'none' }}
          >
            <Network className="w-3.5 h-3.5" />
            Service Graph
          </button>
          <button
            onClick={() => setViewMode('table')}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
              viewMode === 'table'
                ? 'bg-[var(--accent-cyan)] text-black font-semibold shadow-md'
                : 'text-[var(--text-muted)] hover:text-white'
            }`}
            style={{ border: 'none' }}
          >
            <List className="w-3.5 h-3.5" />
            Manifest Table
          </button>
        </div>
      </div>

      <DataShell
        loading={loading}
        error={error}
        isEmpty={dependencies.length === 0 && circularDeps.length === 0 && serviceNodes.length === 0}
        emptyTitle="No dependencies discovered"
        emptyDescription="No package manifests (package.json, requirements.txt, pom.xml, etc.) or internal modules were detected."
      >
        <div className="space-y-6">
          {/* Stats */}
          <div className="stats-grid-3">
            <div className="stat-card">
              <div className="flex items-center gap-2 mb-2">
                <Package className="w-3.5 h-3.5 text-[var(--accent-blue)]" />
                <span className="text-[11px] text-[var(--text-muted)] font-medium">Packages</span>
              </div>
              <p className="text-2xl font-bold text-[var(--accent-blue)]">
                {data?.total ?? dependencies.length}
              </p>
            </div>
            <div className="stat-card">
              <div className="flex items-center gap-2 mb-2">
                <Network className="w-3.5 h-3.5 text-[var(--accent-cyan)]" />
                <span className="text-[11px] text-[var(--text-muted)] font-medium">
                  Service Modules
                </span>
              </div>
              <p className="text-2xl font-bold text-[var(--accent-cyan)]">
                {serviceNodes.length}
              </p>
            </div>
            <div className="stat-card">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
                <span className="text-[11px] text-[var(--text-muted)] font-medium">
                  Circular Deps
                </span>
              </div>
              <p className={`text-2xl font-bold ${circularDeps.length > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                {circularDeps.length}
              </p>
            </div>
          </div>

          {/* Blast Radius Drawer */}
          {selectedNodeId && (
            <BlastRadiusDrawer
              nodeId={selectedNodeId}
              rawEdges={serviceEdges}
              circularDeps={circularDeps}
              onClose={() => setSelectedNodeId(null)}
            />
          )}

          {/* View Mode Body */}
          {viewMode === 'graph' ? (
            serviceNodes.length > 0 ? (
              <ReactFlowProvider>
                <ServiceGraphCanvas
                  rawNodes={serviceNodes}
                  rawEdges={serviceEdges}
                  circularDeps={circularDeps}
                  onSelectNode={(id) => setSelectedNodeId(id)}
                />
              </ReactFlowProvider>
            ) : (
              <div className="glass-card p-8 text-center text-xs text-[var(--text-muted)]">
                Internal module dependencies will appear once multi-module source files are analyzed.
              </div>
            )
          ) : (
            <div className="glass-card table-container overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[var(--border-color)]">
                    <th className="text-left p-3.5 text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider">
                      Package
                    </th>
                    <th className="text-left p-3.5 text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider">
                      Version
                    </th>
                    <th className="text-left p-3.5 text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider">
                      Type
                    </th>
                    <th className="text-left p-3.5 text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider">
                      Source
                    </th>
                  </tr>
                </thead>
                <tbody className="row-striped">
                  {dependencies.map((dep) => (
                    <tr
                      key={`${dep.source}-${dep.name}`}
                      className="border-b border-[var(--border-subtle)] hover:bg-[rgba(99,102,241,0.04)] transition-colors"
                    >
                      <td className="p-3.5">
                        <span className="font-mono text-xs text-[var(--accent-cyan)] font-medium">
                          {dep.name}
                        </span>
                      </td>
                      <td className="p-3.5 text-xs text-[var(--text-secondary)]">
                        {dep.version ?? '—'}
                      </td>
                      <td className="p-3.5">
                        <span
                          className="badge"
                          style={{
                            color: typeColors[dep.type] || 'var(--text-secondary)',
                            background: `${typeColors[dep.type] || '#64748b'}12`,
                            border: `1px solid ${typeColors[dep.type] || '#64748b'}20`,
                          }}
                        >
                          {dep.type}
                        </span>
                      </td>
                      <td className="p-3.5 text-xs font-mono text-[var(--text-muted)]">
                        {dep.source}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Circular Dependencies Card */}
          {circularDeps.length > 0 && (
            <div className="glass-card p-5">
              <h3 className="text-sm font-semibold mb-3 flex items-center gap-2 text-rose-400">
                <AlertTriangle className="w-4 h-4" />
                Detected Cycles ({circularDeps.length})
              </h3>
              <div className="space-y-2">
                {circularDeps.map((cycle, i) => (
                  <div
                    key={i}
                    className="text-xs font-mono text-rose-300 bg-rose-500/10 px-3 py-2 rounded-lg border border-rose-500/20"
                  >
                    {cycle.join(' → ')} → {cycle[0]}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </DataShell>
    </div>
  );
}
