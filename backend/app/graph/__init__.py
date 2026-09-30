"""Graph package — knowledge graph interface and implementations."""

from app.graph.interface import GraphNode, GraphRelationship, GraphRepository, SubgraphResult
from app.graph.networkx_repository import NetworkXGraphRepository

_graph_instance: NetworkXGraphRepository | None = None


async def get_graph_repository() -> NetworkXGraphRepository:
    """Get the active knowledge graph repository singleton."""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = NetworkXGraphRepository()
        await _graph_instance.connect()
    return _graph_instance


__all__ = [
    "GraphNode",
    "GraphRelationship",
    "GraphRepository",
    "SubgraphResult",
    "NetworkXGraphRepository",
    "get_graph_repository",
]
