"""
Unit tests for NetworkX in-memory graph repository.
Verifies node/edge creation, traversal, PageRank centrality, and cycle detection.
"""

import pytest

from app.graph.interface import GraphRelationship
from app.graph.networkx_repository import NetworkXGraphRepository


@pytest.mark.asyncio
async def test_networkx_graph_crud():
    repo = NetworkXGraphRepository()
    await repo.connect()

    # Create nodes
    file_id = await repo.create_node(
        labels=["File"],
        properties={"id": "file-1", "path": "src/main.py", "repo_id": "test-repo"},
    )
    class_id = await repo.create_node(
        labels=["Class"],
        properties={"id": "class-1", "name": "Engine", "file_path": "src/main.py", "repo_id": "test-repo"},
    )

    assert file_id == "file-1"
    assert class_id == "class-1"

    # Create relationship
    await repo.create_relationship(
        source_id=file_id,
        target_id=class_id,
        rel_type="DEFINES",
        properties={"line": 10},
    )

    # Verify node retrieval
    node = await repo.get_node(class_id)
    assert node is not None
    assert node.properties["name"] == "Engine"
    assert "Class" in node.labels

    # Verify neighbors
    subgraph = await repo.get_neighbors(file_id, direction="out")
    assert len(subgraph.nodes) == 2
    assert len(subgraph.relationships) == 1
    assert subgraph.relationships[0].type == "DEFINES"

    # Verify repo subgraph
    repo_subgraph = await repo.get_subgraph("test-repo")
    assert len(repo_subgraph.nodes) == 2
    assert len(repo_subgraph.relationships) == 1

    # Clear repository
    await repo.clear_repository("test-repo")
    cleared = await repo.get_subgraph("test-repo")
    assert len(cleared.nodes) == 0


@pytest.mark.asyncio
async def test_networkx_centrality_and_cycles():
    repo = NetworkXGraphRepository()
    await repo.connect()

    # Create a small circular dependency graph: A -> B -> C -> A
    for letter in ["A", "B", "C"]:
        await repo.create_node(
            labels=["Module"],
            properties={"id": f"mod-{letter}", "name": letter, "repo_id": "cycle-repo"},
        )

    await repo.batch_create_relationships([
        GraphRelationship(source_id="mod-A", target_id="mod-B", type="IMPORTS"),
        GraphRelationship(source_id="mod-B", target_id="mod-C", type="IMPORTS"),
        GraphRelationship(source_id="mod-C", target_id="mod-A", type="IMPORTS"),
    ])

    # Detect cycles
    cycles = repo.detect_cycles("cycle-repo")
    assert len(cycles) > 0

    # Compute PageRank
    scores = repo.compute_pagerank("cycle-repo")
    assert "mod-A" in scores
    assert "mod-B" in scores
    assert "mod-C" in scores
    assert all(score > 0 for score in scores.values())

    # Architectural hubs
    hubs = repo.get_architectural_hubs("cycle-repo", top_n=3)
    assert len(hubs) == 3
