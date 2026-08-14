"""
Repository Intelligence Engine — Graph Repository Interface
Abstract interface for knowledge graph operations.
Designed to be swappable between Neo4j and Memgraph.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class GraphNode:
    """Represents a node in the knowledge graph."""
    id: str
    labels: List[str]
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphRelationship:
    """Represents a relationship (edge) in the knowledge graph."""
    source_id: str
    target_id: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SubgraphResult:
    """A subgraph query result containing nodes and relationships."""
    nodes: List[GraphNode]
    relationships: List[GraphRelationship]


class GraphRepository(ABC):
    """
    Abstract interface for graph database operations.
    Implement this for Neo4j (default) or Memgraph (drop-in replacement).
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the graph database."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the connection."""
        ...

    @abstractmethod
    async def create_node(self, labels: List[str], properties: Dict[str, Any]) -> str:
        """Create a node and return its ID."""
        ...

    @abstractmethod
    async def create_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Create a relationship between two nodes."""
        ...

    @abstractmethod
    async def batch_create_nodes(self, nodes: List[Tuple[List[str], Dict[str, Any]]]) -> List[str]:
        """Batch create nodes for performance. Returns list of node IDs."""
        ...

    @abstractmethod
    async def batch_create_relationships(self, relationships: List[GraphRelationship]) -> None:
        """Batch create relationships for performance."""
        ...

    @abstractmethod
    async def query(self, cypher: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a raw Cypher query and return results."""
        ...

    @abstractmethod
    async def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a single node by ID."""
        ...

    @abstractmethod
    async def get_neighbors(
        self,
        node_id: str,
        rel_type: Optional[str] = None,
        direction: str = "both",
        limit: int = 50,
    ) -> SubgraphResult:
        """Get neighboring nodes and relationships."""
        ...

    @abstractmethod
    async def get_subgraph(
        self,
        repo_id: str,
        node_types: Optional[List[str]] = None,
        limit: int = 200,
    ) -> SubgraphResult:
        """Get a subgraph for a repository, optionally filtered by node type."""
        ...

    @abstractmethod
    async def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
    ) -> List[List[GraphNode]]:
        """Find paths between two nodes."""
        ...

    @abstractmethod
    async def clear_repository(self, repo_id: str) -> None:
        """Delete all nodes/relationships for a given repository."""
        ...
