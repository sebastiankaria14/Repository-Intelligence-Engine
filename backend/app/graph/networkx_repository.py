"""
Repository Intelligence Engine — In-Memory NetworkX Graph Repository
High-performance, 100% offline knowledge graph implementation using NetworkX.
Provides graph storage, PageRank centrality, cycle detection, and subgraph querying.
"""

import json
from pathlib import Path
import uuid
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

from app.core.config import settings
from app.core.logging import get_logger
from app.graph.interface import (
    GraphNode,
    GraphRelationship,
    GraphRepository,
    SubgraphResult,
)

log = get_logger(__name__)


class NetworkXGraphRepository(GraphRepository):
    """
    In-memory knowledge graph backed by NetworkX MultiDiGraph.
    Runs 100% offline, requires zero Docker/Neo4j containers, and delivers
    sub-millisecond centrality and cycle detection for desktop analysis.
    """

    def __init__(self) -> None:
        # MultiDiGraph allows multiple directed relationships between the same nodes
        self._graph = nx.MultiDiGraph()
        # Fast lookup mapping repo_id -> set of node_ids
        self._repo_nodes: Dict[str, set[str]] = {}

    async def connect(self) -> None:
        """In-memory initialization — always ready."""
        log.info("networkx_graph_initialized")

    async def close(self) -> None:
        """No persistent connection to close."""
        pass

    async def create_node(self, labels: List[str], properties: Dict[str, Any]) -> str:
        node_id = properties.get("id") or str(uuid.uuid4())
        repo_id = str(properties.get("repo_id") or properties.get("repository_id") or "default")

        self._graph.add_node(
            node_id,
            labels=labels,
            properties=properties,
            repo_id=repo_id,
        )

        if repo_id not in self._repo_nodes:
            self._repo_nodes[repo_id] = set()
        self._repo_nodes[repo_id].add(node_id)
        return node_id

    async def create_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        props = properties or {}
        self._graph.add_edge(
            source_id,
            target_id,
            key=rel_type,
            type=rel_type,
            properties=props,
        )

    async def batch_create_nodes(
        self, nodes: List[Tuple[List[str], Dict[str, Any]]]
    ) -> List[str]:
        node_ids = []
        for labels, properties in nodes:
            nid = await self.create_node(labels, properties)
            node_ids.append(nid)
        return node_ids

    async def batch_create_relationships(
        self, relationships: List[GraphRelationship]
    ) -> None:
        for rel in relationships:
            await self.create_relationship(
                rel.source_id,
                rel.target_id,
                rel.type,
                rel.properties,
            )

    async def query(
        self, cypher: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Lightweight query support for in-memory graph."""
        return [
            {
                "total_nodes": self._graph.number_of_nodes(),
                "total_edges": self._graph.number_of_edges(),
            }
        ]

    async def get_node(self, node_id: str) -> Optional[GraphNode]:
        if node_id not in self._graph:
            return None
        data = self._graph.nodes[node_id]
        return GraphNode(
            id=node_id,
            labels=data.get("labels", []),
            properties=data.get("properties", {}),
        )

    async def get_neighbors(
        self,
        node_id: str,
        rel_type: Optional[str] = None,
        direction: str = "both",
        limit: int = 50,
    ) -> SubgraphResult:
        if node_id not in self._graph:
            return SubgraphResult(nodes=[], relationships=[])

        neighbor_ids = set()
        relationships: List[GraphRelationship] = []

        if direction in ("out", "both"):
            for u, v, k, d in self._graph.out_edges(node_id, keys=True, data=True):
                if rel_type is None or k == rel_type or d.get("type") == rel_type:
                    neighbor_ids.add(v)
                    relationships.append(
                        GraphRelationship(
                            source_id=u,
                            target_id=v,
                            type=d.get("type", k),
                            properties=d.get("properties", {}),
                        )
                    )
                    if len(relationships) >= limit:
                        break

        if direction in ("in", "both") and len(relationships) < limit:
            for u, v, k, d in self._graph.in_edges(node_id, keys=True, data=True):
                if rel_type is None or k == rel_type or d.get("type") == rel_type:
                    neighbor_ids.add(u)
                    relationships.append(
                        GraphRelationship(
                            source_id=u,
                            target_id=v,
                            type=d.get("type", k),
                            properties=d.get("properties", {}),
                        )
                    )
                    if len(relationships) >= limit:
                        break

        all_node_ids = neighbor_ids | {node_id}
        nodes = []
        for nid in all_node_ids:
            if nid in self._graph:
                ndata = self._graph.nodes[nid]
                nodes.append(
                    GraphNode(
                        id=nid,
                        labels=ndata.get("labels", []),
                        properties=ndata.get("properties", {}),
                    )
                )

        return SubgraphResult(nodes=nodes, relationships=relationships)

    async def get_subgraph(
        self,
        repo_id: str,
        node_types: Optional[List[str]] = None,
        limit: int = 200,
    ) -> SubgraphResult:
        repo_node_ids = self._repo_nodes.get(repo_id)
        if not repo_node_ids:
            # Try to load from disk cache first
            if self.load_from_disk(repo_id):
                repo_node_ids = self._repo_nodes.get(repo_id)

        if not repo_node_ids:
            # Fallback: scan all nodes matching repo_id in properties
            repo_node_ids = {
                nid
                for nid, d in self._graph.nodes(data=True)
                if str(d.get("repo_id")) == str(repo_id)
                or str(d.get("properties", {}).get("repo_id")) == str(repo_id)
            }

        filtered_nodes: List[GraphNode] = []
        node_id_set = set()

        for nid in repo_node_ids:
            if len(filtered_nodes) >= limit:
                break
            if nid not in self._graph:
                continue
            data = self._graph.nodes[nid]
            labels = data.get("labels", [])
            if node_types and not any(t in labels for t in node_types):
                continue
            filtered_nodes.append(
                GraphNode(
                    id=nid,
                    labels=labels,
                    properties=data.get("properties", {}),
                )
            )
            node_id_set.add(nid)

        # Collect relationships between filtered nodes
        relationships: List[GraphRelationship] = []
        for u in node_id_set:
            for _, v, k, d in self._graph.out_edges(u, keys=True, data=True):
                if v in node_id_set:
                    relationships.append(
                        GraphRelationship(
                            source_id=u,
                            target_id=v,
                            type=d.get("type", k),
                            properties=d.get("properties", {}),
                        )
                    )

        return SubgraphResult(nodes=filtered_nodes, relationships=relationships)

    async def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
    ) -> List[List[GraphNode]]:
        if source_id not in self._graph or target_id not in self._graph:
            return []

        # Use simple DiGraph view for path finding
        simple_view = nx.DiGraph(self._graph)
        try:
            paths = list(
                nx.all_simple_paths(
                    simple_view, source=source_id, target=target_id, cutoff=max_depth
                )
            )
        except Exception:
            return []

        result = []
        for path in paths[:10]:
            node_path = []
            for nid in path:
                data = self._graph.nodes[nid]
                node_path.append(
                    GraphNode(
                        id=nid,
                        labels=data.get("labels", []),
                        properties=data.get("properties", {}),
                    )
                )
            result.append(node_path)
        return result

    async def clear_repository(self, repo_id: str) -> None:
        node_ids = list(self._repo_nodes.get(repo_id, set()))
        for nid in node_ids:
            if nid in self._graph:
                self._graph.remove_node(nid)
        if repo_id in self._repo_nodes:
            del self._repo_nodes[repo_id]

    def save_to_disk(self, repo_id: str) -> bool:
        """Persist repository graph to disk JSON file."""
        try:
            graphs_dir = Path(settings.storage_dir) / "graphs"
            graphs_dir.mkdir(parents=True, exist_ok=True)
            file_path = graphs_dir / f"{repo_id}.json"

            repo_nodes = self._repo_nodes.get(repo_id, set())
            nodes_data = []
            for nid in repo_nodes:
                if nid in self._graph:
                    ndata = self._graph.nodes[nid]
                    nodes_data.append({
                        "id": nid,
                        "labels": ndata.get("labels", []),
                        "properties": ndata.get("properties", {}),
                    })

            edges_data = []
            for u in repo_nodes:
                for _, v, k, d in self._graph.out_edges(u, keys=True, data=True):
                    if v in repo_nodes:
                        edges_data.append({
                            "source": u,
                            "target": v,
                            "type": d.get("type", k),
                            "properties": d.get("properties", {}),
                        })

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump({"repo_id": repo_id, "nodes": nodes_data, "edges": edges_data}, f)
            log.info("graph_saved_to_disk", repo_id=repo_id, nodes=len(nodes_data), edges=len(edges_data))
            return True
        except Exception as exc:
            log.warning("save_graph_to_disk_failed", repo_id=repo_id, error=str(exc))
            return False

    def load_from_disk(self, repo_id: str) -> bool:
        """Load repository graph from disk JSON file into memory."""
        try:
            graphs_dir = Path(settings.storage_dir) / "graphs"
            file_path = graphs_dir / f"{repo_id}.json"
            if not file_path.exists():
                return False

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for n in data.get("nodes", []):
                nid = n["id"]
                self._graph.add_node(
                    nid,
                    labels=n.get("labels", []),
                    properties=n.get("properties", {}),
                    repo_id=repo_id,
                )
                if repo_id not in self._repo_nodes:
                    self._repo_nodes[repo_id] = set()
                self._repo_nodes[repo_id].add(nid)

            for e in data.get("edges", []):
                self._graph.add_edge(
                    e["source"],
                    e["target"],
                    key=e.get("type", "RELATES_TO"),
                    type=e.get("type", "RELATES_TO"),
                    properties=e.get("properties", {}),
                )
            log.info("graph_loaded_from_disk", repo_id=repo_id, nodes=len(data.get("nodes", [])), edges=len(data.get("edges", [])))
            return True
        except Exception as exc:
            log.warning("load_graph_from_disk_failed", repo_id=repo_id, error=str(exc))
            return False

    # ── Advanced Algorithmic Centrality & Cycle Analysis ────

    def compute_pagerank(
        self, repo_id: str, alpha: float = 0.85, max_iter: int = 100, tol: float = 1e-6
    ) -> Dict[str, float]:
        """Compute PageRank centrality scores in pure Python (zero external scipy dependency)."""
        subgraph = self._get_repo_subgraph(repo_id)
        nodes = list(subgraph.nodes())
        n = len(nodes)
        if n == 0:
            return {}
        if n == 1:
            return {nodes[0]: 1.0}

        # Out-degree and in-predecessors mapping
        out_degree = {u: subgraph.out_degree(u) for u in nodes}
        in_neighbors = {v: list(subgraph.predecessors(v)) for v in nodes}

        # Uniform initial distribution
        p = {node: 1.0 / n for node in nodes}

        for _ in range(max_iter):
            p_next = {}
            dangling_sum = sum(p[u] for u in nodes if out_degree[u] == 0)
            dangling_contrib = (alpha * dangling_sum / n) + ((1.0 - alpha) / n)

            diff = 0.0
            for v in nodes:
                rank_sum = sum(p[u] / out_degree[u] for u in in_neighbors[v] if out_degree[u] > 0)
                new_rank = alpha * rank_sum + dangling_contrib
                diff += abs(new_rank - p[v])
                p_next[v] = new_rank

            p = p_next
            if diff < tol:
                break

        return p

    def detect_cycles(self, repo_id: str) -> List[List[str]]:
        """Find circular dependency loops in the repository graph."""
        subgraph = self._get_repo_subgraph(repo_id)
        if subgraph.number_of_nodes() == 0:
            return []
        try:
            simple_g = nx.DiGraph(subgraph)
            cycles = list(nx.simple_cycles(simple_g))
            # Return top 25 cycles sorted by length
            return sorted(cycles, key=len)[:25]
        except Exception as e:
            log.warning("cycle_detection_failed", error=str(e))
            return []

    def get_architectural_hubs(self, repo_id: str, top_n: int = 10) -> List[Dict[str, Any]]:
        """Identify critical modules with high in-degree / PageRank score."""
        scores = self.compute_pagerank(repo_id)
        if not scores:
            return []
        sorted_nodes = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
        hubs = []
        for nid, score in sorted_nodes:
            data = self._graph.nodes.get(nid, {})
            props = data.get("properties", {})
            hubs.append({
                "id": nid,
                "name": props.get("name") or props.get("path") or nid,
                "type": data.get("labels", ["Unknown"])[0],
                "score": round(score, 4),
                "in_degree": self._graph.in_degree(nid),
                "out_degree": self._graph.out_degree(nid),
            })
        return hubs

    def _get_repo_subgraph(self, repo_id: str) -> nx.MultiDiGraph:
        repo_nodes = self._repo_nodes.get(repo_id, set())
        return self._graph.subgraph(repo_nodes)
