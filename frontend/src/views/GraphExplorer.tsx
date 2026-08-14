import { useEffect, useMemo, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import { Maximize } from 'lucide-react';

import NoRepository from '../components/NoRepository';
import DataShell from '../components/DataShell';
import { useCurrentRepoId, useApi } from '../hooks/useRepository';
import type { GraphResponse } from '../types/api';
import { repositoryApi } from '../lib/api';

const nodeColors: Record<string, string> = {
  File: '#6366f1',
  Class: '#06b6d4',
  Method: '#a855f7',
  Service: '#10b981',
  Developer: '#f59e0b',
  API: '#f43f5e',
  Table: '#ec4899',
  Commit: '#8b5cf6',
};

export default function GraphExplorer() {
  const repoId = useCurrentRepoId();
  const { data, loading, error, refetch: _refetch } = useApi<GraphResponse>(
    repoId,
    (id) => repositoryApi.getGraph(id, undefined, 200),
  );

  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [nodeFilter, setNodeFilter] = useState<string>('all');

  const graphNodes = useMemo(() => data?.nodes ?? [], [data]);
  const graphEdges = useMemo(() => data?.edges ?? [], [data]);

  useEffect(() => {
    if (!containerRef.current) return;
    
    if (cyRef.current) {
      cyRef.current.destroy();
      cyRef.current = null;
    }

    const elements: cytoscape.ElementDefinition[] = [];

    graphNodes.forEach((node) => {
      const props = node.properties ?? {};
      const label =
        props.name || props.label || props.path || node.id;
      const nodeType = node.label || props.type || 'Unknown';

      elements.push({
        data: {
          id: node.id,
          label,
          type: nodeType,
          ...props,
        },
      });
    });

    graphEdges.forEach((edge) => {
      elements.push({
        data: {
          source: edge.source,
          target: edge.target,
          label: edge.type,
          ...(edge.properties ?? {}),
        },
      });
    });

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            'text-valign': 'bottom',
            'text-halign': 'center',
            'font-size': '10px',
            color: '#94a3b8',
            'text-margin-y': 8,
            width: 40,
            height: 40,
            'border-width': 2,
            'background-color': '#1e293b',
          },
        },
        {
          selector: 'edge',
          style: {
            width: 1.5,
            'line-color': 'rgba(99,102,241,0.3)',
            'target-arrow-color': 'rgba(99,102,241,0.5)',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            label: 'data(label)',
            'font-size': '8px',
            color: '#64748b',
            'text-rotation': 'autorotate',
          },
        },
        {
          selector: 'node:selected',
          style: {
            'border-color': '#06b6d4',
            'border-width': 3,
            'background-color': '#0f172a',
          },
        },
      ],
      layout: {
        name: 'cose',
        animate: true,
        animationDuration: 500,
        nodeOverlap: 20,
        idealEdgeLength: () => 120,
        nodeRepulsion: () => 8000,
      },
    });

    cy.nodes().forEach((node) => {
      const type = node.data('type');
      if (nodeColors[type]) {
        node.style('border-color', nodeColors[type]);
      }
    });

    if (nodeFilter !== 'all') {
      cy.nodes().forEach((node) => {
        if (node.data('type') !== nodeFilter) {
          node.style('display', 'none');
        }
      });
    }

    cy.on('tap', 'node', (evt) => {
      setSelectedNode(evt.target.data());
    });

    cy.on('tap', (evt) => {
      if (evt.target === cy) setSelectedNode(null);
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [graphNodes, graphEdges, nodeFilter]);

  if (!repoId && !loading && !data) {
    return <NoRepository />;
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold gradient-text">Graph Explorer</h2>
          <p className="text-[var(--text-muted)] text-sm mt-1">
            Interactive knowledge graph visualization
          </p>
        </div>
        {data && (
          <div className="text-sm text-[var(--text-muted)]">
            {data.total_nodes} nodes · {data.total_edges} edges
          </div>
        )}
      </div>

      <DataShell
        loading={loading}
        error={error}
        isEmpty={graphNodes.length === 0}
        emptyTitle="No graph data"
        emptyDescription="The knowledge graph has not been built yet. Wait for the scan to reach the 'Building Graph' phase."
      >
        {/* Controls */}
        <div className="flex items-center gap-4 mb-4">
          <select
            value={nodeFilter}
            onChange={(e) => setNodeFilter(e.target.value)}
            className="px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-sm text-[var(--text-primary)] focus:outline-none"
          >
            <option value="all">All Types</option>
            {Object.keys(nodeColors).map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <button
            onClick={() => cyRef.current?.fit()}
            className="btn-secondary p-2"
          >
            <Maximize className="w-4 h-4" />
          </button>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap gap-4 mb-4">
          {Object.entries(nodeColors).map(([type, color]) => (
            <div key={type} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: color }}
              />
              <span className="text-xs text-[var(--text-muted)]">{type}</span>
            </div>
          ))}
        </div>

        <div className="flex gap-4">
          {/* Graph Container */}
          <div
            ref={containerRef}
            className="glass-card flex-1"
            style={{ height: '600px' }}
          />

          {/* Node Detail Panel */}
          {selectedNode && (
            <div className="glass-card w-72 p-4 animate-fade-in">
              <h3 className="font-semibold text-lg mb-3">
                {selectedNode.label || selectedNode.id}
              </h3>
              <div className="space-y-2">
                <div>
                  <span className="text-xs text-[var(--text-muted)]">Type</span>
                  <p
                    className="text-sm font-medium"
                    style={{
                      color: nodeColors[selectedNode.type] || 'var(--text-secondary)',
                    }}
                  >
                    {selectedNode.type || 'Unknown'}
                  </p>
                </div>
                <div>
                  <span className="text-xs text-[var(--text-muted)]">ID</span>
                  <p className="text-sm font-mono">{selectedNode.id}</p>
                </div>
                {selectedNode.name && (
                  <div>
                    <span className="text-xs text-[var(--text-muted)]">Name</span>
                    <p className="text-sm font-mono">{selectedNode.name}</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </DataShell>
    </div>
  );
}
