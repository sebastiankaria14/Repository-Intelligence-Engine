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
  useReactFlow,
  ReactFlowProvider,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useNavigate } from 'react-router-dom';
import {
  Globe,
  Server,
  Cpu,
  Database,
  Wrench,
  Layers,
  Shield,
  Workflow,
  Radio,
  FileCode,
  Sparkles,
  Activity,
  Sliders,
  Table,
  GitFork,
  Search,
  Maximize2,
  Play,
  Pause,
  X,
  MessageSquare,
  ZoomIn,
  ZoomOut,
  Layout,
  Component,
  Network,
} from 'lucide-react';

import NoRepository from '../components/NoRepository';
import DataShell from '../components/DataShell';
import { useCurrentRepoId, useApi } from '../hooks/useRepository';
import type { ArchitectureResponse } from '../types/api';
import { repositoryApi } from '../lib/api';

// Map icon string to Lucide component
function getSubsystemIcon(iconName: string, className = 'w-4 h-4') {
  switch (iconName?.toLowerCase()) {
    case 'globe':
      return <Globe className={className} />;
    case 'layout':
      return <Layout className={className} />;
    case 'component':
      return <Component className={className} />;
    case 'network':
      return <Network className={className} />;
    case 'server':
      return <Server className={className} />;
    case 'radio':
      return <Radio className={className} />;
    case 'shield':
      return <Shield className={className} />;
    case 'workflow':
      return <Workflow className={className} />;
    case 'file-code':
      return <FileCode className={className} />;
    case 'sparkles':
      return <Sparkles className={className} />;
    case 'table':
      return <Table className={className} />;
    case 'git-fork':
      return <GitFork className={className} />;
    case 'database':
      return <Database className={className} />;
    case 'sliders':
      return <Sliders className={className} />;
    case 'activity':
      return <Activity className={className} />;
    case 'wrench':
      return <Wrench className={className} />;
    case 'cpu':
    default:
      return <Cpu className={className} />;
  }
}

// ── Custom React Flow Component Node (Archify Aesthetic) ──────
function ArchitectureComponentNode({ data, selected }: NodeProps) {
  const nodeData = data as any;
  const color = nodeData.color || '#818cf8';
  const borderColor = nodeData.border_color || 'rgba(129, 140, 248, 0.35)';
  const bgColor = nodeData.bg_color || 'rgba(129, 140, 248, 0.08)';

  return (
    <div
      className={`group relative rounded-2xl transition-all duration-300 cursor-pointer ${
        selected ? 'ring-2 ring-white/60 shadow-[0_0_30px_rgba(255,255,255,0.2)]' : 'hover:shadow-[0_0_24px_rgba(0,0,0,0.6)] hover:-translate-y-0.5'
      }`}
      style={{
        width: 290,
        background: 'linear-gradient(145deg, rgba(17, 24, 39, 0.94), rgba(11, 17, 30, 0.98))',
        border: `1px solid ${selected ? color : borderColor}`,
        backdropFilter: 'blur(16px)',
      }}
    >
      {/* Top Handle for Incoming Calls */}
      <Handle
        type="target"
        position={Position.Top}
        style={{
          background: color,
          width: 9,
          height: 9,
          borderRadius: '50%',
          border: '2px solid #090d16',
          top: -5,
        }}
      />

      {/* Card Content */}
      <div className="p-4">
        {/* Header: Icon + Name + Active Dot */}
        <div className="flex items-start justify-between gap-3 mb-2.5">
          <div className="flex items-center gap-2.5 min-w-0">
            <div
              className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0 transition-transform group-hover:scale-105"
              style={{
                background: bgColor,
                color: color,
                border: `1px solid ${borderColor}`,
                boxShadow: `0 0 12px ${bgColor}`,
              }}
            >
              {getSubsystemIcon(nodeData.icon, 'w-4 h-4')}
            </div>
            <div className="min-w-0">
              <h4 className="text-xs font-semibold text-white truncate group-hover:text-white transition-colors">
                {nodeData.name || nodeData.label || 'Subsystem'}
              </h4>
              <p className="text-[10px] uppercase tracking-wider font-mono text-[var(--text-muted)] truncate">
                {nodeData.tier_badge || nodeData.tier_name || 'Tier'}
              </p>
            </div>
          </div>
          {/* Active status pulse */}
          <span className="relative flex h-2 w-2 shrink-0 mt-1">
            <span
              className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
              style={{ background: color }}
            />
            <span
              className="relative inline-flex rounded-full h-2 w-2"
              style={{ background: color }}
            />
          </span>
        </div>

        {/* Description */}
        {nodeData.description && (
          <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed mb-3">
            {nodeData.description}
          </p>
        )}

        {/* Stats Row */}
        <div className="flex items-center gap-2 mb-3">
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-white/[0.04] text-[10px] text-slate-300 font-mono">
            <FileCode className="w-3 h-3 text-slate-400" />
            <span>{nodeData.file_count ?? 0} files</span>
          </div>
          {(nodeData.symbols_count ?? 0) > 0 && (
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-white/[0.04] text-[10px] text-slate-300 font-mono">
              <Cpu className="w-3 h-3 text-slate-400" />
              <span>{nodeData.symbols_count} symbols</span>
            </div>
          )}
        </div>

        {/* Key files preview pills */}
        {nodeData.key_files && nodeData.key_files.length > 0 && (
          <div className="space-y-1 pt-2 border-t border-white/[0.06]">
            <p className="text-[9px] uppercase tracking-wider text-slate-500 font-semibold mb-1">
              Sample Modules
            </p>
            <div className="flex flex-wrap gap-1">
              {nodeData.key_files.slice(0, 2).map((kf: string) => {
                const basename = kf.split('/').pop() || kf;
                return (
                  <span
                    key={kf}
                    title={kf}
                    className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-black/30 text-slate-300 truncate max-w-[125px]"
                  >
                    {basename}
                  </span>
                );
              })}
              {nodeData.key_files.length > 2 && (
                <span className="text-[9px] font-mono text-slate-500 px-1 py-0.5">
                  +{nodeData.key_files.length - 2} more
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Bottom Handle for Outgoing Calls */}
      <Handle
        type="source"
        position={Position.Bottom}
        style={{
          background: color,
          width: 9,
          height: 9,
          borderRadius: '50%',
          border: '2px solid #090d16',
          bottom: -5,
        }}
      />
    </div>
  );
}

// ── Flow Canvas Inner Component (Has access to useReactFlow) ──
interface CanvasProps {
  nodes: Node[];
  edges: Edge[];
  onNodesChange: any;
  onEdgesChange: any;
  onNodeClick: (event: any, node: Node) => void;
  motionEnabled: boolean;
}

function FlowCanvas({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onNodeClick,
  motionEnabled,
}: CanvasProps) {
  const { fitView, zoomIn, zoomOut } = useReactFlow();

  const nodeTypes = useMemo(
    () => ({
      componentNode: ArchitectureComponentNode,
    }),
    [],
  );

  // Apply motion animation toggle to edges
  const renderedEdges = useMemo(() => {
    return edges.map((e) => ({
      ...e,
      animated: motionEnabled,
    }));
  }, [edges, motionEnabled]);

  // Smooth fitView on initial node load
  useEffect(() => {
    if (nodes.length > 0) {
      const timer = setTimeout(() => {
        fitView({ padding: 0.15, duration: 600 });
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [nodes.length, fitView]);

  return (
    <div className="relative w-full h-[640px] rounded-2xl overflow-hidden border border-white/[0.08] bg-[#070b12]">
      {/* Floating Canvas Quick Controls */}
      <div className="absolute top-4 right-4 z-10 flex items-center gap-1.5 p-1.5 rounded-xl bg-slate-900/80 backdrop-blur-md border border-white/[0.08] shadow-lg">
        <button
          onClick={() => zoomIn({ duration: 300 })}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.08] transition-colors"
          title="Zoom In"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={() => zoomOut({ duration: 300 })}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.08] transition-colors"
          title="Zoom Out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={() => fitView({ padding: 0.15, duration: 400 })}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.08] transition-colors"
          title="Fit to Screen"
        >
          <Maximize2 className="w-4 h-4" />
        </button>
      </div>

      <ReactFlow
        nodes={nodes}
        edges={renderedEdges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background color="rgba(129, 140, 248, 0.06)" gap={24} size={1} />
        <Controls
          showInteractive={false}
          style={{
            background: 'rgba(15, 23, 42, 0.85)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '12px',
            backdropFilter: 'blur(12px)',
          }}
        />
        <MiniMap
          style={{
            background: 'rgba(11, 17, 30, 0.85)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '12px',
          }}
          nodeColor={(n: any) => n.data?.color || '#818cf8'}
        />
      </ReactFlow>
    </div>
  );
}

// ── Main Architecture View Component ──────────────────────────
export default function Architecture() {
  const repoId = useCurrentRepoId();
  const navigate = useNavigate();
  const { data: arch, loading, error } = useApi<ArchitectureResponse>(
    repoId,
    repositoryApi.getArchitecture,
  );

  const [selectedNode, setSelectedNode] = useState<any | null>(null);
  const [selectedTier, setSelectedTier] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [motionEnabled, setMotionEnabled] = useState<boolean>(true);

  // Compute raw nodes and edges from the API diagram response
  const rawNodes: Node[] = useMemo(() => {
    if (!arch || !arch.diagram?.nodes) return [];
    return arch.diagram.nodes.map((n: any, i: number) => ({
      id: n.id ?? `node-${i}`,
      type: 'componentNode',
      position: n.position ?? { x: 300, y: 50 + i * 180 },
      data: n.data ?? {
        name: n.label ?? `Subsystem ${i}`,
        tier: 'service',
        color: '#818cf8',
        file_count: 1,
        symbols_count: 0,
        description: 'Architectural component',
      },
    }));
  }, [arch]);

  const rawEdges: Edge[] = useMemo(() => {
    if (!arch || !arch.diagram?.edges) return [];
    return arch.diagram.edges.map((e: any, i: number) => {
      const strokeColor = e.style?.stroke || '#818cf8';
      return {
        id: e.id ?? `edge-${i}`,
        source: e.source,
        target: e.target,
        type: e.type ?? 'smoothstep',
        animated: motionEnabled,
        label: e.label || e.data?.label,
        style: {
          stroke: strokeColor,
          strokeWidth: 2,
        },
        labelStyle: {
          fill: '#cbd5e1',
          fontSize: 10,
          fontWeight: 500,
          fontFamily: 'monospace',
        },
        labelBgStyle: {
          fill: 'rgba(15, 23, 42, 0.92)',
          stroke: 'rgba(255, 255, 255, 0.1)',
          strokeWidth: 1,
          rx: 4,
          ry: 4,
        },
        labelBgPadding: [6, 4] as [number, number],
      };
    });
  }, [arch, motionEnabled]);

  // Manage React Flow internal node & edge state
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // Synchronize whenever rawNodes or filters change
  useEffect(() => {
    if (rawNodes.length === 0) {
      setNodes([]);
      setEdges([]);
      return;
    }

    const query = searchQuery.trim().toLowerCase();

    const filteredNodes = rawNodes.map((node) => {
      const d = node.data as any;
      const matchesTier = selectedTier === 'all' || d?.tier === selectedTier;
      const matchesQuery =
        !query ||
        d?.name?.toLowerCase().includes(query) ||
        d?.tier_badge?.toLowerCase().includes(query) ||
        d?.key_files?.some((kf: string) => kf.toLowerCase().includes(query));

      const isDimmed = !matchesTier || !matchesQuery;

      return {
        ...node,
        style: {
          ...node.style,
          opacity: isDimmed ? 0.2 : 1,
          filter: isDimmed ? 'grayscale(0.8)' : 'none',
          transition: 'all 0.3s ease',
        },
      };
    });

    setNodes(filteredNodes);
    setEdges(rawEdges);
  }, [rawNodes, rawEdges, selectedTier, searchQuery, setNodes, setEdges]);

  // Handle node clicks to open the inspector drawer
  const handleNodeClick = useCallback((_event: any, node: Node) => {
    setSelectedNode(node.data);
  }, []);

  const hasDiagram =
    arch &&
    arch.diagram &&
    ((arch.diagram.nodes && arch.diagram.nodes.length > 0) ||
      (arch.diagram.edges && arch.diagram.edges.length > 0));

  if (!repoId && !loading && !arch) {
    return <NoRepository />;
  }

  // Tier filter options derived from detected layers
  const tierFilters = [
    { id: 'all', label: 'All Tiers' },
    { id: 'presentation', label: 'Presentation' },
    { id: 'api', label: 'API Gateway' },
    { id: 'service', label: 'Services & Engine' },
    { id: 'data', label: 'Data & Persistence' },
    { id: 'infrastructure', label: 'Infrastructure' },
  ];

  return (
    <div className="space-y-6 animate-fade-in pb-12">
      {/* Page Header */}
      <div className="page-header flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="gradient-text text-2xl font-bold tracking-tight">Architecture View</h2>
          <p className="text-sm text-[var(--text-muted)] mt-0.5">
            Discovered system topology, tiered subsystem boundaries, and request flows
          </p>
        </div>

        {/* Quick status pill */}
        {arch && arch.pattern && (
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.04] border border-white/[0.08] backdrop-blur-sm self-start sm:self-auto">
            <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]" />
            <span className="text-xs font-medium text-slate-200">{arch.pattern}</span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300">
              {Math.round(arch.confidence * 100)}% match
            </span>
          </div>
        )}
      </div>

      <DataShell loading={loading} error={error} isEmpty={!arch || (!arch.pattern && !hasDiagram)}>
        {/* Top Metric Cards */}
        {arch && arch.pattern && arch.pattern !== 'pending_analysis' && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <div className="glass-card metric-card p-4">
              <p className="text-[11px] text-[var(--text-muted)] mb-1 font-medium flex items-center justify-between">
                <span>Architecture Pattern</span>
                <Layout className="w-3.5 h-3.5 text-sky-400" />
              </p>
              <p className="text-base font-semibold text-white truncate">{arch.pattern}</p>
              <p className="text-[11px] text-slate-400 mt-1">Classified via AST heuristics</p>
            </div>

            <div className="glass-card metric-card p-4">
              <p className="text-[11px] text-[var(--text-muted)] mb-1 font-medium flex items-center justify-between">
                <span>Pattern Confidence</span>
                <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
              </p>
              <p className="text-base font-semibold text-emerald-400">
                {Math.round(arch.confidence * 100)}%
              </p>
              <p className="text-[11px] text-slate-400 mt-1">High structural consistency</p>
            </div>

            <div className="glass-card metric-card p-4">
              <p className="text-[11px] text-[var(--text-muted)] mb-1 font-medium flex items-center justify-between">
                <span>Active Tiers</span>
                <Layers className="w-3.5 h-3.5 text-purple-400" />
              </p>
              <p className="text-base font-semibold text-purple-400">
                {arch.layers?.length || 0} Tiers
              </p>
              <p className="text-[11px] text-slate-400 mt-1">Tiered boundary separation</p>
            </div>

            <div className="glass-card metric-card p-4">
              <p className="text-[11px] text-[var(--text-muted)] mb-1 font-medium flex items-center justify-between">
                <span>Subsystems Mapped</span>
                <Component className="w-3.5 h-3.5 text-amber-400" />
              </p>
              <p className="text-base font-semibold text-amber-400">
                {rawNodes.length} Components
              </p>
              <p className="text-[11px] text-slate-400 mt-1">Connected via imports & calls</p>
            </div>
          </div>
        )}

        {/* Tier Overview Cards */}
        {arch && arch.layers && arch.layers.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3 mb-6">
            {arch.layers.map((layer) => (
              <div
                key={layer.name}
                onClick={() => {
                  const mappedId = layer.name.toLowerCase().includes('pres')
                    ? 'presentation'
                    : layer.name.toLowerCase().includes('api')
                    ? 'api'
                    : layer.name.toLowerCase().includes('serv')
                    ? 'service'
                    : layer.name.toLowerCase().includes('data')
                    ? 'data'
                    : 'infrastructure';
                  setSelectedTier(selectedTier === mappedId ? 'all' : mappedId);
                }}
                className={`glass-card p-3.5 rounded-xl cursor-pointer transition-all duration-200 border ${
                  selectedTier === layer.name.toLowerCase()
                    ? 'ring-1 ring-white/50 bg-white/[0.08]'
                    : 'hover:bg-white/[0.04]'
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <h4 className="text-xs font-semibold text-white truncate">{layer.name}</h4>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/[0.06] text-slate-300 shrink-0">
                    {layer.file_count} files
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 line-clamp-2 leading-snug mb-2">
                  {layer.description}
                </p>
                <div className="flex flex-wrap gap-1">
                  {layer.components.slice(0, 2).map((c) => (
                    <span
                      key={c}
                      className="text-[9px] px-1.5 py-0.5 rounded bg-black/40 text-slate-300 font-mono"
                    >
                      {c}
                    </span>
                  ))}
                  {layer.components.length > 2 && (
                    <span className="text-[9px] text-slate-500 px-1 py-0.5">
                      +{layer.components.length - 2}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Diagram Controls Toolbar */}
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 mb-3 p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
          {/* Tier Filter Pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 lg:pb-0 scrollbar-none">
            {tierFilters.map((tf) => (
              <button
                key={tf.id}
                onClick={() => setSelectedTier(tf.id)}
                className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-all shrink-0 ${
                  selectedTier === tf.id
                    ? 'bg-gradient-to-r from-amber-500 to-amber-600 text-white shadow-md'
                    : 'bg-white/[0.04] text-slate-400 hover:text-white hover:bg-white/[0.08]'
                }`}
              >
                {tf.label}
              </button>
            ))}
          </div>

          {/* Search + Motion Controls */}
          <div className="flex items-center gap-2 self-end lg:self-auto">
            {/* Search filter */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Find component or file..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-44 md:w-56 h-8 pl-8 pr-3 text-xs bg-black/40 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-amber-500"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>

            {/* Motion toggle */}
            <button
              onClick={() => setMotionEnabled(!motionEnabled)}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                motionEnabled
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                  : 'bg-white/[0.04] text-slate-400 hover:text-white'
              }`}
              title="Toggle animated data flow traces"
            >
              {motionEnabled ? <Play className="w-3 h-3" /> : <Pause className="w-3 h-3" />}
              <span className="hidden sm:inline">Flow Motion</span>
            </button>
          </div>
        </div>

        {/* Interactive React Flow Diagram Canvas */}
        <div className="relative">
          <ReactFlowProvider>
            <FlowCanvas
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={handleNodeClick}
              motionEnabled={motionEnabled}
            />
          </ReactFlowProvider>

          {/* Subsystem Inspection Side Drawer */}
          {selectedNode && (
            <div className="absolute top-4 right-4 bottom-4 w-80 md:w-96 rounded-2xl bg-slate-900/95 backdrop-blur-xl border border-white/[0.12] shadow-2xl p-5 overflow-y-auto z-20 animate-fade-in flex flex-col justify-between">
              <div>
                {/* Header */}
                <div className="flex items-start justify-between gap-3 mb-4">
                  <div className="flex items-center gap-3">
                    <div
                      className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
                      style={{
                        background: selectedNode.bg_color || 'rgba(129,140,248,0.1)',
                        color: selectedNode.color || '#818cf8',
                        border: `1px solid ${selectedNode.border_color || 'rgba(129,140,248,0.3)'}`,
                      }}
                    >
                      {getSubsystemIcon(selectedNode.icon, 'w-5 h-5')}
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-white">{selectedNode.name}</h3>
                      <span className="text-[10px] uppercase tracking-wider font-mono text-slate-400">
                        {selectedNode.tier_badge || selectedNode.tier_name}
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={() => setSelectedNode(null)}
                    className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.08]"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* Description */}
                {selectedNode.description && (
                  <p className="text-xs text-slate-300 leading-relaxed mb-4 p-3 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                    {selectedNode.description}
                  </p>
                )}

                {/* Metrics */}
                <div className="grid grid-cols-2 gap-2 mb-4">
                  <div className="p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                    <span className="text-[10px] text-slate-400 block mb-0.5">Files Count</span>
                    <span className="text-sm font-bold text-white">
                      {selectedNode.file_count || 0}
                    </span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                    <span className="text-[10px] text-slate-400 block mb-0.5">Total Symbols</span>
                    <span className="text-sm font-bold text-white">
                      {selectedNode.symbols_count || 0}
                    </span>
                  </div>
                </div>

                {/* Technologies */}
                {selectedNode.technologies && selectedNode.technologies.length > 0 && (
                  <div className="mb-4">
                    <h5 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                      Technologies & Grammars
                    </h5>
                    <div className="flex flex-wrap gap-1.5">
                      {selectedNode.technologies.map((t: string) => (
                        <span
                          key={t}
                          className="text-xs px-2 py-0.5 rounded-md bg-white/[0.05] text-slate-200 border border-white/[0.08]"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Files in this Subsystem */}
                {selectedNode.files && selectedNode.files.length > 0 && (
                  <div className="mb-4">
                    <h5 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center justify-between">
                      <span>Subsystem Files</span>
                      <span className="text-[10px] text-slate-500 font-mono">
                        {selectedNode.files.length} total
                      </span>
                    </h5>
                    <div className="space-y-1 max-h-48 overflow-y-auto pr-1">
                      {selectedNode.files.map((fileObj: any) => {
                        const path = typeof fileObj === 'string' ? fileObj : fileObj.path;
                        return (
                          <div
                            key={path}
                            className="p-1.5 rounded-lg bg-black/40 text-[11px] font-mono text-slate-300 truncate hover:text-white transition-colors"
                            title={path}
                          >
                            {path}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>

              {/* Action Button: Ask AI About Subsystem */}
              <div className="pt-3 border-t border-white/[0.08]">
                <button
                  onClick={() => {
                    navigate('/chat');
                  }}
                  className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 text-white font-medium text-xs shadow-lg hover:brightness-110 transition-all"
                >
                  <MessageSquare className="w-4 h-4" />
                  <span>Ask AI Assistant About This Subsystem</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </DataShell>
    </div>
  );
}
