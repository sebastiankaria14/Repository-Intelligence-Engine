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
  Database,
  Table as TableIcon,
  Key,
  ArrowRight,
  Search,
  X,
  FileCode,
  Copy,
  Check,
  List,
  Network,
} from 'lucide-react';

import NoRepository from '../components/NoRepository';
import DataShell from '../components/DataShell';
import { useCurrentRepoId, useApi } from '../hooks/useRepository';
import type { DatabaseResponse, DatabaseTable, DatabaseColumn } from '../types/api';
import { repositoryApi } from '../lib/api';

// ── Custom Entity Node ───────────────────────────────────────

function EntityNode({ data, selected }: NodeProps) {
  const nodeData = data as any;
  const table: DatabaseTable | undefined = nodeData.table;
  const tableName = table?.name || nodeData.label || 'Unknown Table';
  const columns: DatabaseColumn[] = table?.columns || [];
  const foreignKeys = table?.foreign_keys || [];
  const ormModel = table?.orm_model;

  return (
    <div
      className={`relative min-w-[280px] max-w-[340px] rounded-xl border bg-[#0d131f]/95 shadow-2xl backdrop-blur-md transition-all duration-200 ${
        selected
          ? 'border-[var(--accent-purple)] ring-2 ring-[var(--accent-purple)]/40 shadow-[0_0_24px_rgba(168,85,247,0.3)]'
          : 'border-[rgba(255,255,255,0.08)] hover:border-[rgba(168,85,247,0.4)]'
      }`}
    >
      {/* Handles */}
      <Handle
        type="target"
        position={Position.Left}
        className="!w-2.5 !h-2.5 !bg-[var(--accent-purple)] !border-2 !border-[#0d131f] !-left-1.5"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!w-2.5 !h-2.5 !bg-[var(--accent-cyan)] !border-2 !border-[#0d131f] !-right-1.5"
      />
      <Handle
        type="target"
        position={Position.Top}
        className="!w-2.5 !h-2.5 !bg-[var(--accent-purple)] !border-2 !border-[#0d131f] !-top-1.5"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-2.5 !h-2.5 !bg-[var(--accent-cyan)] !border-2 !border-[#0d131f] !-bottom-1.5"
      />

      {/* Table Header */}
      <div className="flex items-center justify-between gap-2 border-b border-[rgba(255,255,255,0.08)] bg-gradient-to-r from-[rgba(168,85,247,0.12)] to-[rgba(6,182,212,0.06)] px-3.5 py-2.5 rounded-t-xl">
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-[rgba(168,85,247,0.18)] border border-[rgba(168,85,247,0.3)]">
            <TableIcon className="h-3.5 w-3.5 text-[var(--accent-purple)]" />
          </div>
          <span className="font-mono text-xs font-semibold text-[var(--text-primary)] truncate">
            {tableName}
          </span>
        </div>
        {ormModel && (
          <span className="shrink-0 rounded bg-[rgba(6,182,212,0.12)] px-1.5 py-0.5 font-mono text-[9px] font-medium text-[var(--accent-cyan)] border border-[rgba(6,182,212,0.25)]">
            {ormModel}
          </span>
        )}
      </div>

      {/* Columns List */}
      <div className="divide-y divide-[rgba(255,255,255,0.03)] px-3 py-2 text-[11px] max-h-56 overflow-y-auto font-mono">
        {columns.slice(0, 8).map((col) => {
          const isPk = col.name.toLowerCase() === 'id' || col.name.toLowerCase().endsWith('_pk');
          const isFk = foreignKeys.some((fk) => fk.column === col.name);

          return (
            <div
              key={col.name}
              className="flex items-center justify-between py-1 px-1 hover:bg-[rgba(255,255,255,0.03)] rounded transition-colors"
            >
              <div className="flex items-center gap-1.5 min-w-0">
                {isPk ? (
                  <span className="flex items-center gap-0.5 rounded bg-[rgba(245,158,11,0.15)] px-1 py-0.2 text-[8px] font-bold text-[#f59e0b] border border-[rgba(245,158,11,0.3)]">
                    <Key className="w-2.5 h-2.5" />
                    PK
                  </span>
                ) : isFk ? (
                  <span className="rounded bg-[rgba(168,85,247,0.15)] px-1 py-0.2 text-[8px] font-semibold text-[var(--accent-purple)] border border-[rgba(168,85,247,0.3)]">
                    FK
                  </span>
                ) : (
                  <span className="w-1.5 h-1.5 rounded-full bg-[var(--text-muted)] opacity-30 shrink-0" />
                )}
                <span className={`truncate ${isPk ? 'font-semibold text-[var(--text-primary)]' : 'text-[var(--text-secondary)]'}`}>
                  {col.name}
                </span>
              </div>
              <div className="flex items-center gap-1 shrink-0 ml-2">
                <span className="text-[10px] text-[var(--text-muted)]">{col.type}</span>
                {col.nullable && (
                  <span className="text-[9px] text-[var(--text-muted)] opacity-60">?</span>
                )}
              </div>
            </div>
          );
        })}
        {columns.length > 8 && (
          <div className="py-1 text-center text-[10px] text-[var(--text-muted)] font-sans">
            +{columns.length - 8} more columns
          </div>
        )}
      </div>

      {/* Footer / Relations Summary */}
      {foreignKeys.length > 0 && (
        <div className="flex items-center justify-between border-t border-[rgba(255,255,255,0.06)] bg-[rgba(0,0,0,0.2)] px-3 py-1.5 rounded-b-xl text-[10px] text-[var(--text-muted)]">
          <span className="flex items-center gap-1">
            <ArrowRight className="w-2.5 h-2.5 text-[var(--accent-purple)]" />
            {foreignKeys.length} relation{foreignKeys.length > 1 ? 's' : ''}
          </span>
          <span className="font-mono text-[9px] text-[var(--accent-purple)]">FK Connected</span>
        </div>
      )}
    </div>
  );
}

const nodeTypes = {
  entityNode: EntityNode,
};

// ── Inner Canvas Component ───────────────────────────────────

function ERCanvas({
  tables,
  rawNodes,
  rawEdges,
  onSelectTable,
}: {
  tables: DatabaseTable[];
  rawNodes: Array<Record<string, unknown>>;
  rawEdges: Array<Record<string, unknown>>;
  onSelectTable: (table: DatabaseTable) => void;
}) {
  const [searchTerm, setSearchTerm] = useState('');

  // Build clean React Flow nodes
  const initialNodes: Node[] = useMemo(() => {
    const tableMap = new Map<string, DatabaseTable>(tables.map((t) => [t.name, t]));

    if (rawNodes && rawNodes.length > 0) {
      return rawNodes.map((n, i) => {
        const id = String(n.id || `table-${i}`);
        const tbl = tableMap.get(id) || tables[i];
        const pos = (n.position as { x: number; y: number }) || {
          x: (i % 3) * 360 + 50,
          y: Math.floor(i / 3) * 320 + 50,
        };
        return {
          id,
          type: 'entityNode',
          position: pos,
          data: {
            label: tbl?.name || id,
            table: tbl,
          },
        };
      });
    }

    // Fallback: construct directly from tables
    return tables.map((t, i) => ({
      id: t.name,
      type: 'entityNode',
      position: {
        x: (i % 3) * 360 + 50,
        y: Math.floor(i / 3) * 320 + 50,
      },
      data: {
        label: t.name,
        table: t,
      },
    }));
  }, [tables, rawNodes]);

  // Build clean React Flow edges
  const initialEdges: Edge[] = useMemo(() => {
    if (rawEdges && rawEdges.length > 0) {
      return rawEdges.map((e, idx) => ({
        id: String(e.id || `edge-${idx}`),
        source: String(e.source),
        target: String(e.target),
        label: String(e.label || 'references'),
        animated: true,
        style: { stroke: '#a855f7', strokeWidth: 1.8 },
        labelStyle: { fill: '#c084fc', fontSize: 10, fontFamily: 'monospace' },
        labelBgStyle: { fill: '#0d131f', fillOpacity: 0.8 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: '#a855f7',
          width: 14,
          height: 14,
        },
      }));
    }

    // Fallback: generate from foreign keys
    const edges: Edge[] = [];
    tables.forEach((t) => {
      (t.foreign_keys || []).forEach((fk, fkIdx) => {
        edges.push({
          id: `fk-${t.name}-${fk.referenced_table}-${fkIdx}`,
          source: t.name,
          target: fk.referenced_table,
          label: `${fk.column} -> ${fk.referenced_column || 'id'}`,
          animated: true,
          style: { stroke: '#a855f7', strokeWidth: 1.8 },
          labelStyle: { fill: '#c084fc', fontSize: 10, fontFamily: 'monospace' },
          labelBgStyle: { fill: '#0d131f', fillOpacity: 0.8 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#a855f7',
            width: 14,
            height: 14,
          },
        });
      });
    });
    return edges;
  }, [tables, rawEdges]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
  }, [initialNodes, setNodes]);

  useEffect(() => {
    setEdges(initialEdges);
  }, [initialEdges, setEdges]);

  // Filter highlighting
  const filteredNodes = useMemo(() => {
    if (!searchTerm.trim()) return nodes;
    const term = searchTerm.toLowerCase();
    return nodes.map((node) => {
      const match =
        node.id.toLowerCase().includes(term) ||
        (node.data?.table as DatabaseTable)?.columns?.some((c) =>
          c.name.toLowerCase().includes(term)
        );
      return {
        ...node,
        style: {
          ...node.style,
          opacity: match ? 1 : 0.25,
        },
      };
    });
  }, [nodes, searchTerm]);

  const onNodeClick = useCallback(
    (_: any, node: Node) => {
      const tableData = (node.data as any)?.table;
      if (tableData) {
        onSelectTable(tableData);
      }
    },
    [onSelectTable]
  );

  return (
    <div className="relative w-full h-[640px] rounded-xl border border-[var(--border-subtle)] bg-[#070b13] overflow-hidden shadow-inner">
      {/* Search & Actions Toolbar */}
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--text-muted)]" />
          <input
            type="text"
            placeholder="Search table or column..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="h-8 pl-8 pr-3 text-xs rounded-lg bg-[#0d131f]/90 border border-[rgba(255,255,255,0.1)] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-purple)] w-56 backdrop-blur-md"
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
          nodeColor="#a855f7"
          maskColor="rgba(7, 11, 19, 0.75)"
          className="!bg-[#0d131f] !border-[rgba(255,255,255,0.1)] !rounded-lg"
        />
      </ReactFlow>
    </div>
  );
}

// ── Table Inspector Drawer ───────────────────────────────────

function TableInspector({
  table,
  onClose,
}: {
  table: DatabaseTable;
  onClose: () => void;
}) {
  const [copied, setCopied] = useState(false);

  // Generate DDL for the table
  const ddl = useMemo(() => {
    const lines = [`CREATE TABLE ${table.name} (`];
    const colLines = table.columns.map((c) => {
      const parts = [`  ${c.name} ${c.type}`];
      if (!c.nullable) parts.push('NOT NULL');
      if (c.default_value) parts.push(`DEFAULT ${c.default_value}`);
      return parts.join(' ');
    });

    const fkLines = table.foreign_keys.map(
      (fk) =>
        `  FOREIGN KEY (${fk.column}) REFERENCES ${fk.referenced_table}(${fk.referenced_column || 'id'})`
    );

    const allLines = [...colLines, ...fkLines];
    lines.push(allLines.join(',\n'));
    lines.push(');');
    return lines.join('\n');
  }, [table]);

  const handleCopy = () => {
    navigator.clipboard.writeText(ddl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="glass-card p-5 border border-[rgba(168,85,247,0.3)] shadow-2xl animate-fade-in">
      <div className="flex items-center justify-between pb-3 border-b border-[var(--border-subtle)] mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[rgba(168,85,247,0.15)] flex items-center justify-center border border-[rgba(168,85,247,0.3)]">
            <TableIcon className="w-4 h-4 text-[var(--accent-purple)]" />
          </div>
          <div>
            <h3 className="text-sm font-semibold font-mono text-[var(--text-primary)]">
              {table.name}
            </h3>
            <p className="text-[11px] text-[var(--text-muted)]">
              {table.orm_model ? `ORM Model: ${table.orm_model}` : 'Database Table Entity'}
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 text-[var(--text-muted)] hover:text-white rounded-lg hover:bg-[rgba(255,255,255,0.05)] transition-colors"
          style={{ border: 'none' }}
          title="Close table details"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div>
          <h4 className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-2">
            Columns ({table.columns.length})
          </h4>
          <div className="max-h-60 overflow-y-auto space-y-1 pr-1 font-mono text-xs">
            {table.columns.map((c) => (
              <div
                key={c.name}
                className="flex items-center justify-between p-2 rounded bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.04)]"
              >
                <div className="flex items-center gap-1.5 truncate">
                  <span className="font-semibold text-[var(--accent-cyan)]">{c.name}</span>
                </div>
                <div className="flex items-center gap-1 text-[11px]">
                  <span className="text-[var(--text-muted)]">{c.type}</span>
                  <span className="text-[10px] text-[var(--text-muted)] opacity-60">
                    {c.nullable ? 'nullable' : 'required'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
              Schema DDL
            </h4>
            <button
              onClick={handleCopy}
              className="inline-flex items-center gap-1 text-[11px] text-[var(--accent-cyan)] hover:text-white px-2 py-0.5 rounded bg-[rgba(6,182,212,0.1)] transition-colors"
              style={{ border: 'none' }}
            >
              {copied ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
              {copied ? 'Copied' : 'Copy SQL'}
            </button>
          </div>
          <pre className="p-3 rounded-lg bg-[#070b13] border border-[rgba(255,255,255,0.06)] font-mono text-[11px] text-[var(--text-secondary)] overflow-x-auto max-h-60 leading-relaxed">
            {ddl}
          </pre>
        </div>
      </div>

      {/* Foreign Keys & Source File */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-3 border-t border-[var(--border-subtle)] text-[11px] text-[var(--text-muted)]">
        {table.source_file ? (
          <div className="flex items-center gap-1.5 font-mono">
            <FileCode className="w-3.5 h-3.5 text-[var(--text-muted)]" />
            <span>{table.source_file}</span>
          </div>
        ) : (
          <div />
        )}
        {table.foreign_keys.length > 0 && (
          <div className="flex items-center gap-1.5">
            <Key className="w-3.5 h-3.5 text-[var(--accent-purple)]" />
            <span>
              {table.foreign_keys.length} foreign key relation{table.foreign_keys.length > 1 ? 's' : ''}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main Database Explorer View ──────────────────────────────

export default function DatabaseExplorer() {
  const repoId = useCurrentRepoId();
  const { data, loading, error, refetch: _refetch } = useApi<DatabaseResponse>(
    repoId,
    repositoryApi.getDatabase
  );

  const [viewMode, setViewMode] = useState<'canvas' | 'grid'>('canvas');
  const [selectedTable, setSelectedTable] = useState<DatabaseTable | null>(null);

  if (!repoId && !loading && !data) {
    return <NoRepository />;
  }

  const tables = data?.tables ?? [];
  const foreignKeyCount = tables.reduce(
    (sum: number, t: any) => sum + (t.foreign_keys?.length ?? 0),
    0
  );

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="page-header !mb-0">
          <h2 className="gradient-text">Database Intelligence</h2>
          <p>Entity-Relationship schema graph, foreign keys, and migration models</p>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center gap-1 p-1 rounded-xl bg-[rgba(255,255,255,0.03)] border border-[var(--border-subtle)] self-start">
          <button
            onClick={() => setViewMode('canvas')}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
              viewMode === 'canvas'
                ? 'bg-[var(--accent-purple)] text-white shadow-md'
                : 'text-[var(--text-muted)] hover:text-white'
            }`}
            style={{ border: 'none' }}
          >
            <Network className="w-3.5 h-3.5" />
            ER Canvas
          </button>
          <button
            onClick={() => setViewMode('grid')}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
              viewMode === 'grid'
                ? 'bg-[var(--accent-purple)] text-white shadow-md'
                : 'text-[var(--text-muted)] hover:text-white'
            }`}
            style={{ border: 'none' }}
          >
            <List className="w-3.5 h-3.5" />
            Table List
          </button>
        </div>
      </div>

      <DataShell
        loading={loading}
        error={error}
        isEmpty={tables.length === 0}
        emptyTitle="No database schema discovered"
        emptyDescription="No ORM models, migrations, or raw DDL were detected in this repository."
      >
        <div className="space-y-6">
          {/* Stats Bar */}
          <div className="stats-grid-3">
            <div className="stat-card">
              <div className="flex items-center gap-2 mb-2">
                <TableIcon className="w-3.5 h-3.5 text-[var(--accent-blue)]" />
                <span className="text-[11px] text-[var(--text-muted)] font-medium">Tables</span>
              </div>
              <p className="text-2xl font-bold text-[var(--accent-blue)]">{tables.length}</p>
            </div>
            <div className="stat-card">
              <div className="flex items-center gap-2 mb-2">
                <Key className="w-3.5 h-3.5 text-[var(--accent-purple)]" />
                <span className="text-[11px] text-[var(--text-muted)] font-medium">Foreign Keys</span>
              </div>
              <p className="text-2xl font-bold text-[var(--accent-purple)]">{foreignKeyCount}</p>
            </div>
            <div className="stat-card">
              <div className="flex items-center gap-2 mb-2">
                <Database className="w-3.5 h-3.5 text-[var(--accent-green)]" />
                <span className="text-[11px] text-[var(--text-muted)] font-medium">Migrations</span>
              </div>
              <p className="text-2xl font-bold text-[var(--accent-green)]">
                {data?.migrations?.length ?? 0}
              </p>
            </div>
          </div>

          {/* Selected Table Inspector */}
          {selectedTable && (
            <TableInspector table={selectedTable} onClose={() => setSelectedTable(null)} />
          )}

          {/* Canvas or Grid View */}
          {viewMode === 'canvas' ? (
            <ReactFlowProvider>
              <ERCanvas
                tables={tables}
                rawNodes={data?.er_diagram?.nodes || []}
                rawEdges={data?.er_diagram?.edges || []}
                onSelectTable={(table) => setSelectedTable(table)}
              />
            </ReactFlowProvider>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {tables.map((table) => (
                <div
                  key={table.name}
                  onClick={() => setSelectedTable(table)}
                  className="glass-card p-5 flex flex-col cursor-pointer hover:border-[var(--accent-purple)] transition-colors"
                >
                  <div className="flex items-center justify-between gap-2 mb-4">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-lg bg-[rgba(6,182,212,0.1)] flex items-center justify-center border border-[rgba(6,182,212,0.2)] flex-shrink-0">
                        <TableIcon className="w-3.5 h-3.5 text-[var(--accent-cyan)]" />
                      </div>
                      <h3 className="font-semibold font-mono text-sm text-[var(--accent-cyan)] truncate">
                        {table.name}
                      </h3>
                    </div>
                    {table.orm_model && (
                      <span className="text-[10px] text-[var(--text-muted)] bg-[rgba(255,255,255,0.05)] px-2 py-0.5 rounded font-mono">
                        {table.orm_model}
                      </span>
                    )}
                  </div>

                  <div className="space-y-0.5 mb-4 max-h-40 overflow-y-auto pr-1">
                    {table.columns.map((col) => (
                      <p
                        key={col.name}
                        className="text-[11px] font-mono text-[var(--text-secondary)] pl-2.5 border-l-2 border-[var(--border-subtle)] py-0.5 flex justify-between"
                      >
                        <span>{col.name}</span>
                        <span className="text-[var(--text-muted)] text-[10px]">
                          {col.type} {col.nullable ? '(null)' : ''}
                        </span>
                      </p>
                    ))}
                  </div>

                  {table.foreign_keys.length > 0 && (
                    <div className="border-t border-[var(--border-subtle)] pt-3 mb-3">
                      <p className="text-[10px] text-[var(--text-muted)] mb-1.5 font-medium uppercase tracking-wider">
                        Foreign Keys
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {table.foreign_keys.map((fk, i) => (
                          <span
                            key={i}
                            className="inline-flex items-center gap-1 text-[10px] text-[var(--accent-purple)] bg-[rgba(168,85,247,0.06)] px-2 py-0.5 rounded border border-[rgba(168,85,247,0.15)]"
                          >
                            <ArrowRight className="w-2.5 h-2.5" />
                            {fk.column} → {fk.referenced_table}.{fk.referenced_column || 'id'}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {table.indexes.length > 0 && (
                    <div className="border-t border-[var(--border-subtle)] pt-3 mt-auto">
                      <p className="text-[10px] text-[var(--text-muted)] mb-1.5 font-medium uppercase tracking-wider">
                        Indexes
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {table.indexes.map((idx, i) => (
                          <span
                            key={i}
                            className="text-[10px] text-[var(--accent-cyan)] bg-[rgba(6,182,212,0.06)] px-2 py-0.5 rounded border border-[rgba(6,182,212,0.12)]"
                          >
                            {idx}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Relationships Card */}
          {data?.relationships && data.relationships.length > 0 && (
            <div className="glass-card p-5">
              <h3 className="text-sm font-semibold mb-3 text-[var(--text-primary)]">
                Foreign Key Relationships
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                {data.relationships.map((rel, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between p-2.5 rounded-lg bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.04)] text-xs text-[var(--text-secondary)]"
                  >
                    <div className="flex items-center gap-2 truncate">
                      <span className="font-mono text-[var(--accent-cyan)]">{rel.from_table}</span>
                      <ArrowRight className="w-3 h-3 text-[var(--accent-purple)] shrink-0" />
                      <span className="font-mono text-[var(--accent-cyan)]">{rel.to_table}</span>
                    </div>
                    <span className="text-[10px] text-[var(--text-muted)] bg-[var(--bg-primary)] px-1.5 py-0.5 rounded shrink-0">
                      {rel.type}
                    </span>
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
