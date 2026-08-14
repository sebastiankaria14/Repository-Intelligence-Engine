import { useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import NoRepository from '../components/NoRepository';
import DataShell from '../components/DataShell';
import { useCurrentRepoId, useApi } from '../hooks/useRepository';
import type { ArchitectureResponse } from '../types/api';
import { repositoryApi } from '../lib/api';

const LAYER_COLORS = [
  'rgba(99, 102, 241, 0.15)',
  'rgba(6, 182, 212, 0.15)',
  'rgba(168, 85, 247, 0.15)',
  'rgba(16, 185, 129, 0.15)',
  'rgba(245, 158, 11, 0.15)',
];

const LAYER_BORDER_COLORS = [
  'rgba(99, 102, 241, 0.35)',
  'rgba(6, 182, 212, 0.35)',
  'rgba(168, 85, 247, 0.35)',
  'rgba(16, 185, 129, 0.35)',
  'rgba(245, 158, 11, 0.35)',
];

export default function Architecture() {
  const repoId = useCurrentRepoId();
  const { data: arch, loading, error, refetch: _refetch } = useApi<ArchitectureResponse>(
    repoId,
    repositoryApi.getArchitecture,
  );

  const nodes: Node[] = useMemo(() => {
    if (!arch) return [];
    const diagramNodes = arch.diagram?.nodes ?? [];
    if (diagramNodes.length === 0) return [];

    return diagramNodes.map((n: any, i: number) => ({
      id: n.id ?? n.data?.id ?? String(i),
      position: n.position ?? { x: Math.random() * 400, y: Math.random() * 300 },
      data: {
        label: n.data?.label ?? n.label ?? n.id ?? `Node ${i}`,
      },
      style: {
        background: n.style?.background ?? 'rgba(99, 102, 241, 0.15)',
        border: n.style?.border ?? '1px solid rgba(99, 102, 241, 0.4)',
        borderRadius: '12px',
        padding: '16px',
        color: '#f1f5f9',
        width: 240,
        textAlign: 'center' as const,
        whiteSpace: 'pre-line' as const,
      },
    }));
  }, [arch]);

  const edges: Edge[] = useMemo(() => {
    if (!arch) return [];
    const diagramEdges = arch.diagram?.edges ?? [];
    return diagramEdges.map((e: any, i: number) => ({
      id: e.id ?? `edge-${i}`,
      source: e.source ?? e.data?.source ?? String(i),
      target: e.target ?? e.data?.target ?? String(i + 1),
      type: e.type ?? 'smoothstep',
      animated: e.animated ?? false,
      label: e.label ?? e.data?.label,
      style: { stroke: e.color ?? '#6366f1' },
    }));
  }, [arch]);

  const [rfNodes, , onNodesChange] = useNodesState(nodes);
  const [rfEdges, , onEdgesChange] = useEdgesState(edges);

  const hasDiagram =
    arch &&
    arch.diagram &&
    (arch.diagram.nodes.length > 0 || arch.diagram.edges.length > 0);

  if (!repoId && !loading && !arch) {
    return <NoRepository />;
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="page-header">
        <h2 className="gradient-text">Architecture View</h2>
        <p>Discovered architecture pattern and layer diagram</p>
      </div>

      <DataShell loading={loading} error={error} isEmpty={!arch || (!arch.pattern && !hasDiagram)}>
        {arch && arch.pattern && arch.pattern !== 'pending_analysis' && (
          <div className="stats-grid-3 mb-6">
            <div className="stat-card">
              <p className="text-[11px] text-[var(--text-muted)] mb-1 font-medium">Detected Pattern</p>
              <p className="text-lg font-semibold text-[var(--accent-blue)] capitalize">
                {arch.pattern}
              </p>
            </div>
            <div className="stat-card">
              <p className="text-[11px] text-[var(--text-muted)] mb-1 font-medium">Confidence</p>
              <p className="text-lg font-semibold text-[var(--accent-green)]">
                {Math.round(arch.confidence * 100)}%
              </p>
            </div>
            <div className="stat-card">
              <p className="text-[11px] text-[var(--text-muted)] mb-1 font-medium">Layers</p>
              <p className="text-lg font-semibold text-[var(--accent-purple)]">
                {arch.layers.length}
              </p>
            </div>
          </div>
        )}

        {arch && arch.layers.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-6 stagger-children">
            {arch.layers.map((layer, i) => (
              <div key={layer.name} className="glass-card metric-card p-4">
                <div
                  className="w-2.5 h-2.5 rounded-full mb-2.5"
                  style={{
                    background: LAYER_BORDER_COLORS[i % LAYER_BORDER_COLORS.length],
                    boxShadow: `0 0 8px ${LAYER_COLORS[i % LAYER_COLORS.length]}`,
                  }}
                />
                <h3 className="font-semibold text-sm mb-1 text-[var(--text-primary)]">{layer.name}</h3>
                <p className="text-xs text-[var(--text-muted)] mb-3 leading-relaxed">
                  {layer.description || `${layer.file_count} files`}
                </p>
                <div className="flex flex-wrap gap-1">
                  {layer.components.slice(0, 5).map((c) => (
                    <span
                      key={c}
                      className="text-[10px] px-2 py-0.5 rounded-md bg-[var(--bg-primary)] text-[var(--text-secondary)] border border-[var(--border-subtle)]"
                    >
                      {c}
                    </span>
                  ))}
                  {layer.components.length > 5 && (
                    <span className="text-[10px] text-[var(--text-muted)] px-1">
                      +{layer.components.length - 5}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {hasDiagram && (
          <div className="glass-card overflow-hidden" style={{ height: '600px' }}>
            <ReactFlow
              nodes={rfNodes}
              edges={rfEdges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              fitView
              proOptions={{ hideAttribution: true }}
            >
              <Background color="rgba(99,102,241,0.08)" gap={20} />
              <Controls
                style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                }}
              />
              <MiniMap
                style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                }}
                nodeColor="#6366f1"
              />
            </ReactFlow>
          </div>
        )}
      </DataShell>
    </div>
  );
}
