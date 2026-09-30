import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import cytoscape from 'cytoscape';
import { Maximize, ZoomIn, ZoomOut, RotateCcw, Search } from 'lucide-react';

import NoRepository from '../components/NoRepository';
import DataShell from '../components/DataShell';
import { useCurrentRepoId, useApi } from '../hooks/useRepository';
import type { GraphResponse } from '../types/api';
import { repositoryApi } from '../lib/api';

const nodeColorConfig: Record<string, { border: string; bg: string }> = {
  Repository: { border: '#f59e0b', bg: 'rgba(245, 158, 11, 0.3)' },
  File: { border: '#6366f1', bg: 'rgba(99, 102, 241, 0.3)' },
  Class: { border: '#06b6d4', bg: 'rgba(6, 182, 212, 0.3)' },
  Interface: { border: '#10b981', bg: 'rgba(16, 185, 129, 0.3)' },
  Function: { border: '#ec4899', bg: 'rgba(236, 72, 153, 0.3)' },
  Method: { border: '#a855f7', bg: 'rgba(168, 85, 247, 0.3)' },
  Module: { border: '#3b82f6', bg: 'rgba(59, 130, 246, 0.3)' },
  Variable: { border: '#f97316', bg: 'rgba(249, 115, 22, 0.3)' },
  TypeAlias: { border: '#14b8a6', bg: 'rgba(20, 184, 166, 0.3)' },
  Service: { border: '#10b981', bg: 'rgba(16, 185, 129, 0.3)' },
  API: { border: '#f43f5e', bg: 'rgba(244, 63, 94, 0.3)' },
  Table: { border: '#e11d48', bg: 'rgba(225, 29, 72, 0.3)' },
  Commit: { border: '#8b5cf6', bg: 'rgba(139, 92, 246, 0.3)' },
  Developer: { border: '#eab308', bg: 'rgba(234, 179, 8, 0.3)' },
};

const defaultColor = { border: '#94a3b8', bg: 'rgba(148, 163, 184, 0.25)' };

function normalizeNodeType(raw: string | undefined | null): string {
  if (!raw) return 'Unknown';
  const lower = String(raw).toLowerCase().replace(/[\s_-]+/g, '');
  if (lower === 'class') return 'Class';
  if (lower === 'interface') return 'Interface';
  if (lower === 'function') return 'Function';
  if (lower === 'method') return 'Method';
  if (lower === 'typealias' || lower === 'type') return 'TypeAlias';
  if (lower === 'file') return 'File';
  if (lower === 'module') return 'Module';
  if (lower === 'repository' || lower === 'repo') return 'Repository';
  if (lower === 'variable' || lower === 'var') return 'Variable';
  if (lower === 'service') return 'Service';
  if (lower === 'api' || lower === 'endpoint') return 'API';
  if (lower === 'table') return 'Table';
  if (lower === 'commit') return 'Commit';
  if (lower === 'developer' || lower === 'author') return 'Developer';
  return raw.charAt(0).toUpperCase() + raw.slice(1);
}

export default function GraphExplorer() {
  const repoId = useCurrentRepoId();

  // Stable API fetcher to prevent infinite re-render loops
  const fetchGraph = useCallback(
    (id: string) => repositoryApi.getGraph(id, undefined, 300),
    [],
  );

  const { data, loading, error, refetch: _refetch } = useApi<GraphResponse>(
    repoId,
    fetchGraph,
  );

  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [nodeFilter, setNodeFilter] = useState<string>('all');
  const [showParentFiles, setShowParentFiles] = useState<boolean>(false);
  const [layoutName, setLayoutName] = useState<string>('cose');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const graphNodes = useMemo(() => data?.nodes ?? [], [data]);
  const graphEdges = useMemo(() => data?.edges ?? [], [data]);

  // Compute node type distribution
  const typeCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    graphNodes.forEach((n) => {
      const raw = n.label || (n.properties as any)?.type || 'Other';
      const t = normalizeNodeType(raw);
      counts[t] = (counts[t] || 0) + 1;
    });
    return counts;
  }, [graphNodes]);

  // Initialize Cytoscape ONLY once when graph data arrives
  useEffect(() => {
    if (!containerRef.current || graphNodes.length === 0) return;

    if (cyRef.current) {
      cyRef.current.destroy();
      cyRef.current = null;
    }

    const validNodeIds = new Set(graphNodes.map((n) => n.id));
    const elements: cytoscape.ElementDefinition[] = [];

    graphNodes.forEach((node) => {
      const props = node.properties ?? {};
      const rawType = node.label || (props as any).type || 'Unknown';
      const nodeType = normalizeNodeType(rawType);
      const label = (props as any).name || (props as any).label || (props as any).path || node.id;

      elements.push({
        data: {
          ...props,
          id: node.id,
          label: String(label),
          type: nodeType,
          canonicalType: nodeType,
        },
      });
    });

    graphEdges.forEach((edge) => {
      // CRITICAL: only add edge if both endpoints exist to avoid Cytoscape crash
      if (validNodeIds.has(edge.source) && validNodeIds.has(edge.target)) {
        elements.push({
          data: {
            id: `edge-${edge.source}-${edge.target}-${edge.type}`,
            source: edge.source,
            target: edge.target,
            label: edge.type,
            ...(edge.properties ?? {}),
          },
        });
      }
    });

    try {
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
              color: '#cbd5e1',
              'text-margin-y': 6,
              'text-outline-width': 2,
              'text-outline-color': '#0f172a',
              width: (ele: any) => {
                const t = ele.data('type');
                if (t === 'Repository') return 52;
                if (t === 'File') return 40;
                if (t === 'Class' || t === 'Interface' || t === 'Module') return 36;
                return 28;
              },
              height: (ele: any) => {
                const t = ele.data('type');
                if (t === 'Repository') return 52;
                if (t === 'File') return 40;
                if (t === 'Class' || t === 'Interface' || t === 'Module') return 36;
                return 28;
              },
              'border-width': 2,
              'border-color': (ele: any) =>
                (nodeColorConfig[ele.data('type')] || defaultColor).border,
              'background-color': (ele: any) =>
                (nodeColorConfig[ele.data('type')] || defaultColor).bg,
            },
          },
          {
            selector: 'edge',
            style: {
              width: 1.5,
              'line-color': 'rgba(148, 163, 184, 0.3)',
              'target-arrow-color': 'rgba(148, 163, 184, 0.6)',
              'target-arrow-shape': 'triangle',
              'curve-style': 'bezier',
              label: 'data(label)',
              'font-size': '8px',
              color: '#94a3b8',
              'text-rotation': 'autorotate',
              'text-background-opacity': 0.85,
              'text-background-color': '#0f172a',
              'text-background-padding': '2px',
            },
          },
          {
            selector: 'node:selected',
            style: {
              'border-color': '#38bdf8',
              'border-width': 4,
              'background-color': 'rgba(56, 189, 248, 0.45)',
            },
          },
          {
            selector: '.highlighted',
            style: {
              'border-color': '#f59e0b',
              'border-width': 3,
              'background-color': 'rgba(245, 158, 11, 0.5)',
            },
          },
        ],
        layout: {
          name: 'cose',
          animate: false, // Instant calculation to eliminate layout blinking
          fit: true,
          padding: 40,
          nodeOverlap: 20,
          idealEdgeLength: () => 100,
          nodeRepulsion: () => 6000,
        } as any,
      });

      cy.on('tap', 'node', (evt) => {
        setSelectedNode(evt.target.data());
      });

      cy.on('tap', (evt) => {
        if (evt.target === cy) setSelectedNode(null);
      });

      cyRef.current = cy;

      // Force container sizing & fit on mount
      requestAnimationFrame(() => {
        if (cyRef.current) {
          cyRef.current.resize();
          cyRef.current.fit(undefined, 30);
        }
      });

      const resizeTimer = setTimeout(() => {
        if (cyRef.current) {
          cyRef.current.resize();
          cyRef.current.fit(undefined, 30);
        }
      }, 150);

      return () => {
        clearTimeout(resizeTimer);
        cy.destroy();
        cyRef.current = null;
      };
    } catch (err) {
      console.error('Cytoscape initialization error:', err);
    }
  }, [graphNodes, graphEdges]);

  // Fast type filtering and layout re-run so individual graphs are centered and visible
  useEffect(() => {
    if (!cyRef.current) return;
    const cy = cyRef.current;

    cy.batch(() => {
      // Determine matching nodes
      const targetNodeIds = new Set<string>();
      cy.nodes().forEach((node) => {
        const t = String(node.data('type') || node.data('canonicalType') || '');
        if (nodeFilter === 'all' || t.toLowerCase() === nodeFilter.toLowerCase()) {
          targetNodeIds.add(node.id());
        }
      });

      // If showParentFiles is active, also include parent files defining these symbols
      const parentFileIds = new Set<string>();
      if (nodeFilter !== 'all' && showParentFiles && nodeFilter !== 'File' && nodeFilter !== 'Module') {
        cy.edges().forEach((edge) => {
          if (targetNodeIds.has(edge.data('target')) && edge.data('label') === 'DEFINES') {
            parentFileIds.add(edge.data('source'));
          }
        });
      }

      // Apply visibility
      cy.nodes().forEach((node) => {
        if (targetNodeIds.has(node.id()) || parentFileIds.has(node.id())) {
          node.style('display', 'element');
        } else {
          node.style('display', 'none');
        }
      });
    });

    // Re-layout and fit visible elements so individual graphs are neatly arranged and centered
    const visibleElements = cy.elements(':visible');
    if (visibleElements.length > 0) {
      const visibleNodes = visibleElements.nodes();
      const visibleEdges = visibleElements.edges();

      let activeLayout = layoutName;
      if (nodeFilter !== 'all') {
        // If there are no internal edges between the filtered nodes, grid or concentric creates a beautiful clean layout
        if (visibleEdges.length === 0 && layoutName === 'cose') {
          activeLayout = visibleNodes.length <= 36 ? 'concentric' : 'grid';
        }
      }

      try {
        const l = cy.layout({
          name: activeLayout,
          eles: visibleElements,
          animate: true,
          animationDuration: 350,
          fit: true,
          padding: 40,
          avoidOverlap: true,
          nodeDimensionsIncludeLabels: true,
        } as any);
        l.run();
      } catch (e) {
        console.error('Layout run error:', e);
        cy.fit(visibleElements, 40);
      }
    }
  }, [nodeFilter, layoutName, showParentFiles]);

  // Search highlighting
  useEffect(() => {
    if (!cyRef.current) return;
    const cy = cyRef.current;
    cy.nodes().removeClass('highlighted');
    if (!searchQuery.trim()) return;

    const q = searchQuery.toLowerCase();
    const matching = cy.nodes().filter((n) => {
      const label = String(n.data('label') || '').toLowerCase();
      const type = String(n.data('type') || '').toLowerCase();
      return label.includes(q) || type.includes(q);
    });

    matching.addClass('highlighted');
    if (matching.length > 0) {
      cy.animate({
        center: { eles: matching.first() },
        zoom: 1.2,
        duration: 300,
      });
    }
  }, [searchQuery]);

  const handleZoomIn = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 1.3);
    }
  };

  const handleZoomOut = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() / 1.3);
    }
  };

  const handleFit = () => {
    if (cyRef.current) {
      cyRef.current.fit(undefined, 30);
    }
  };

  const handleResetLayout = () => {
    if (cyRef.current) {
      cyRef.current.layout({
        name: layoutName,
        animate: true,
        animationDuration: 400,
        fit: true,
        padding: 30,
      } as any).run();
    }
  };

  if (!repoId && !loading && !data) {
    return <NoRepository />;
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold gradient-text">Graph Explorer</h2>
          <p className="text-[var(--text-muted)] text-sm mt-1">
            Interactive AST & architectural knowledge graph
          </p>
        </div>
        {data && (
          <div className="text-sm font-mono text-[var(--accent-cyan)]">
            {data.total_nodes} nodes · {data.total_edges} relationships
          </div>
        )}
      </div>

      <DataShell
        loading={loading}
        error={error}
        isEmpty={graphNodes.length === 0}
        emptyTitle="No graph data"
        emptyDescription="The knowledge graph is empty or has not been built yet. Start a scan to index the codebase into nodes and relationships."
      >
        {/* Controls Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4 p-3 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)]">
          <div className="flex flex-wrap items-center gap-3">
            {/* Type Filter */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-[var(--text-muted)]">Type:</span>
              <select
                value={nodeFilter}
                onChange={(e) => setNodeFilter(e.target.value)}
                className="px-3 py-1.5 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-xs text-[var(--text-primary)] focus:outline-none"
              >
                <option value="all">All Types ({graphNodes.length})</option>
                {Object.entries(typeCounts).map(([type, count]) => (
                  <option key={type} value={type}>
                    {type} ({count})
                  </option>
                ))}
              </select>
            </div>

            {/* Layout Selector */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-[var(--text-muted)]">Layout:</span>
              <select
                value={layoutName}
                onChange={(e) => setLayoutName(e.target.value)}
                className="px-3 py-1.5 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-xs text-[var(--text-primary)] focus:outline-none"
              >
                <option value="cose">Force Directed (COSE)</option>
                <option value="concentric">Concentric Rings</option>
                <option value="circle">Circle</option>
                <option value="breadthfirst">Hierarchical</option>
                <option value="grid">Grid</option>
              </select>
            </div>

            {/* Show Source Files Toggle for Symbol Types */}
            {nodeFilter !== 'all' && nodeFilter !== 'File' && nodeFilter !== 'Module' && (
              <button
                type="button"
                onClick={() => setShowParentFiles((prev) => !prev)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  showParentFiles
                    ? 'bg-[var(--accent-blue)] text-white'
                    : 'bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
                style={{ border: showParentFiles ? 'none' : undefined }}
              >
                {showParentFiles ? 'Showing Source Files' : 'Show Source Files'}
              </button>
            )}

            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-[var(--text-muted)]" />
              <input
                type="text"
                placeholder="Find node..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-1.5 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none w-40"
              />
            </div>
          </div>

          {/* Canvas Actions */}
          <div className="flex items-center gap-1.5">
            <button
              onClick={handleZoomIn}
              title="Zoom In"
              className="p-1.5 rounded-lg bg-[var(--bg-primary)] hover:bg-[var(--border-color)] text-[var(--text-secondary)] transition-colors border-none"
              style={{ border: 'none' }}
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              onClick={handleZoomOut}
              title="Zoom Out"
              className="p-1.5 rounded-lg bg-[var(--bg-primary)] hover:bg-[var(--border-color)] text-[var(--text-secondary)] transition-colors border-none"
              style={{ border: 'none' }}
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <button
              onClick={handleFit}
              title="Fit to Screen"
              className="p-1.5 rounded-lg bg-[var(--bg-primary)] hover:bg-[var(--border-color)] text-[var(--text-secondary)] transition-colors border-none"
              style={{ border: 'none' }}
            >
              <Maximize className="w-4 h-4" />
            </button>
            <button
              onClick={handleResetLayout}
              title="Re-run Layout"
              className="p-1.5 rounded-lg bg-[var(--bg-primary)] hover:bg-[var(--border-color)] text-[var(--text-secondary)] transition-colors border-none"
              style={{ border: 'none' }}
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap gap-3 mb-4 px-1">
          {Object.entries(nodeColorConfig)
            .filter(([t]) => typeCounts[t])
            .map(([type, colors]) => (
              <div
                key={type}
                onClick={() => setNodeFilter(nodeFilter === type ? 'all' : type)}
                className={`flex items-center gap-1.5 px-2 py-0.5 rounded-md cursor-pointer transition-all ${
                  nodeFilter === type
                    ? 'bg-[var(--bg-secondary)] border border-[var(--accent-blue)]'
                    : 'hover:opacity-80'
                }`}
              >
                <div
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: colors.border }}
                />
                <span className="text-[11px] text-[var(--text-secondary)]">
                  {type} ({typeCounts[type]})
                </span>
              </div>
            ))}
        </div>

        {/* Main Canvas & Detail Split */}
        <div className="flex gap-4">
          <div
            ref={containerRef}
            className="glass-card flex-1 relative overflow-hidden"
            style={{ height: '620px', minHeight: '620px', backgroundColor: '#090d16' }}
          />

          {/* Node Detail Drawer */}
          {selectedNode && (
            <div className="glass-card w-80 p-5 animate-fade-in flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2 border-b border-[var(--border-color)] pb-3">
                  <div>
                    <span
                      className="px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider"
                      style={{
                        backgroundColor: (nodeColorConfig[selectedNode.type] || defaultColor).bg,
                        color: (nodeColorConfig[selectedNode.type] || defaultColor).border,
                        border: `1px solid ${(nodeColorConfig[selectedNode.type] || defaultColor).border}`,
                      }}
                    >
                      {selectedNode.type || 'Unknown'}
                    </span>
                    <h3 className="font-bold text-base mt-2 text-[var(--text-primary)] break-all">
                      {selectedNode.label || selectedNode.id}
                    </h3>
                  </div>
                </div>

                <div className="space-y-2.5 text-xs">
                  <div>
                    <span className="text-[var(--text-muted)] block mb-0.5">Node ID</span>
                    <p className="font-mono bg-[var(--bg-primary)] p-1.5 rounded text-[11px] text-[var(--text-secondary)] break-all border border-[var(--border-color)]">
                      {selectedNode.id}
                    </p>
                  </div>

                  {selectedNode.path && (
                    <div>
                      <span className="text-[var(--text-muted)] block mb-0.5">File Path</span>
                      <p className="font-mono text-[var(--accent-cyan)] break-all">
                        {selectedNode.path}
                      </p>
                    </div>
                  )}

                  {selectedNode.file_path && selectedNode.file_path !== selectedNode.path && (
                    <div>
                      <span className="text-[var(--text-muted)] block mb-0.5">Source File</span>
                      <p className="font-mono text-[var(--accent-cyan)] break-all">
                        {selectedNode.file_path}
                      </p>
                    </div>
                  )}

                  {selectedNode.line_start != null && (
                    <div className="flex gap-4">
                      <div>
                        <span className="text-[var(--text-muted)]">Lines</span>
                        <p className="font-mono font-semibold">
                          {selectedNode.line_start}
                          {selectedNode.line_end ? ` - ${selectedNode.line_end}` : ''}
                        </p>
                      </div>
                      {selectedNode.lines != null && (
                        <div>
                          <span className="text-[var(--text-muted)]">Total Lines</span>
                          <p className="font-mono font-semibold">{selectedNode.lines}</p>
                        </div>
                      )}
                    </div>
                  )}

                  {selectedNode.language && (
                    <div>
                      <span className="text-[var(--text-muted)]">Language</span>
                      <p className="font-medium text-[var(--accent-purple)]">{selectedNode.language}</p>
                    </div>
                  )}

                  {selectedNode.signature && (
                    <div>
                      <span className="text-[var(--text-muted)] block mb-0.5">Signature</span>
                      <pre className="p-2 rounded bg-[var(--bg-primary)] font-mono text-[10px] text-[var(--accent-amber)] overflow-x-auto border border-[var(--border-color)]">
                        {selectedNode.signature}
                      </pre>
                    </div>
                  )}
                </div>
              </div>

              <button
                onClick={() => setSelectedNode(null)}
                className="btn-secondary w-full text-xs mt-4"
                style={{ border: 'none' }}
              >
                Close Inspector
              </button>
            </div>
          )}
        </div>
      </DataShell>
    </div>
  );
}
