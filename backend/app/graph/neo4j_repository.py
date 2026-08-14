"""
Repository Intelligence Engine — Neo4j Graph Repository
Concrete implementation of GraphRepository using the Neo4j Python driver.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from neo4j import AsyncGraphDatabase, AsyncDriver

from app.core.config import settings
from app.core.logging import get_logger
from app.graph.interface import GraphNode, GraphRelationship, GraphRepository, SubgraphResult

log = get_logger(__name__)


class Neo4jRepository(GraphRepository):
    """Neo4j implementation of the graph repository interface."""

    def __init__(self):
        self._driver: Optional[AsyncDriver] = None

    async def connect(self) -> None:
        self._driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            max_connection_pool_size=50,
        )
        # Verify connectivity
        async with self._driver.session() as session:
            await session.run("RETURN 1")
        log.info("neo4j_connected", uri=settings.neo4j_uri)

    async def close(self) -> None:
        if self._driver:
            await self._driver.close()
            log.info("neo4j_disconnected")

    async def create_node(self, labels: List[str], properties: Dict[str, Any]) -> str:
        node_id = properties.get("node_id", str(uuid.uuid4()))
        properties["node_id"] = node_id
        label_str = ":".join(labels)

        async with self._driver.session() as session:
            await session.run(
                f"CREATE (n:{label_str} $props) RETURN n.node_id AS id",
                props=properties,
            )
        return node_id

    async def create_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        props = properties or {}
        async with self._driver.session() as session:
            await session.run(
                f"""
                MATCH (a {{node_id: $source_id}}), (b {{node_id: $target_id}})
                CREATE (a)-[r:{rel_type} $props]->(b)
                """,
                source_id=source_id,
                target_id=target_id,
                props=props,
            )

    async def batch_create_nodes(self, nodes: List[Tuple[List[str], Dict[str, Any]]]) -> List[str]:
        ids = []
        async with self._driver.session() as session:
            for labels, props in nodes:
                node_id = props.get("node_id", str(uuid.uuid4()))
                props["node_id"] = node_id
                label_str = ":".join(labels)
                await session.run(
                    f"CREATE (n:{label_str} $props)",
                    props=props,
                )
                ids.append(node_id)
        return ids

    async def batch_create_relationships(self, relationships: List[GraphRelationship]) -> None:
        async with self._driver.session() as session:
            for rel in relationships:
                await session.run(
                    f"""
                    MATCH (a {{node_id: $source_id}}), (b {{node_id: $target_id}})
                    CREATE (a)-[r:{rel.type} $props]->(b)
                    """,
                    source_id=rel.source_id,
                    target_id=rel.target_id,
                    props=rel.properties,
                )

    async def query(self, cypher: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        async with self._driver.session() as session:
            result = await session.run(cypher, parameters or {})
            records = await result.data()
            return records

    async def get_node(self, node_id: str) -> Optional[GraphNode]:
        async with self._driver.session() as session:
            result = await session.run(
                "MATCH (n {node_id: $node_id}) RETURN n, labels(n) AS labels",
                node_id=node_id,
            )
            record = await result.single()
            if not record:
                return None
            node_data = dict(record["n"])
            return GraphNode(
                id=node_id,
                labels=record["labels"],
                properties=node_data,
            )

    async def get_neighbors(
        self,
        node_id: str,
        rel_type: Optional[str] = None,
        direction: str = "both",
        limit: int = 50,
    ) -> SubgraphResult:
        rel_filter = f":{rel_type}" if rel_type else ""

        if direction == "out":
            pattern = f"(a)-[r{rel_filter}]->(b)"
        elif direction == "in":
            pattern = f"(a)<-[r{rel_filter}]-(b)"
        else:
            pattern = f"(a)-[r{rel_filter}]-(b)"

        async with self._driver.session() as session:
            result = await session.run(
                f"""
                MATCH {pattern}
                WHERE a.node_id = $node_id
                RETURN b, labels(b) AS labels, type(r) AS rel_type, properties(r) AS rel_props,
                       a.node_id AS source_id, b.node_id AS target_id
                LIMIT $limit
                """,
                node_id=node_id,
                limit=limit,
            )
            records = await result.data()

        nodes = []
        rels = []
        for rec in records:
            node_data = dict(rec["b"])
            nodes.append(GraphNode(
                id=rec["target_id"],
                labels=rec["labels"],
                properties=node_data,
            ))
            rels.append(GraphRelationship(
                source_id=rec["source_id"],
                target_id=rec["target_id"],
                type=rec["rel_type"],
                properties=rec.get("rel_props", {}),
            ))

        return SubgraphResult(nodes=nodes, relationships=rels)

    async def get_subgraph(
        self,
        repo_id: str,
        node_types: Optional[List[str]] = None,
        limit: int = 200,
    ) -> SubgraphResult:
        if node_types:
            label_filter = " OR ".join([f"'{t}' IN labels(n)" for t in node_types])
            where_clause = f"AND ({label_filter})"
        else:
            where_clause = ""

        async with self._driver.session() as session:
            # Get nodes
            node_result = await session.run(
                f"""
                MATCH (n)
                WHERE n.repo_id = $repo_id {where_clause}
                RETURN n, labels(n) AS labels
                LIMIT $limit
                """,
                repo_id=repo_id,
                limit=limit,
            )
            node_records = await node_result.data()

            # Get relationships between those nodes
            rel_result = await session.run(
                f"""
                MATCH (a)-[r]->(b)
                WHERE a.repo_id = $repo_id AND b.repo_id = $repo_id
                {where_clause.replace('n', 'a')}
                RETURN a.node_id AS source, b.node_id AS target, type(r) AS rel_type, properties(r) AS props
                LIMIT $limit
                """,
                repo_id=repo_id,
                limit=limit * 2,
            )
            rel_records = await rel_result.data()

        nodes = [
            GraphNode(
                id=rec["n"].get("node_id", ""),
                labels=rec["labels"],
                properties=dict(rec["n"]),
            )
            for rec in node_records
        ]
        relationships = [
            GraphRelationship(
                source_id=rec["source"],
                target_id=rec["target"],
                type=rec["rel_type"],
                properties=rec.get("props", {}),
            )
            for rec in rel_records
        ]

        return SubgraphResult(nodes=nodes, relationships=relationships)

    async def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
    ) -> List[List[GraphNode]]:
        async with self._driver.session() as session:
            result = await session.run(
                f"""
                MATCH path = shortestPath(
                    (a {{node_id: $source_id}})-[*..{max_depth}]-(b {{node_id: $target_id}})
                )
                RETURN [n IN nodes(path) | {{node_id: n.node_id, labels: labels(n), props: properties(n)}}] AS path_nodes
                LIMIT 5
                """,
                source_id=source_id,
                target_id=target_id,
            )
            records = await result.data()

        paths = []
        for rec in records:
            path = [
                GraphNode(
                    id=n["node_id"],
                    labels=n["labels"],
                    properties=n["props"],
                )
                for n in rec["path_nodes"]
            ]
            paths.append(path)
        return paths

    async def clear_repository(self, repo_id: str) -> None:
        async with self._driver.session() as session:
            await session.run(
                "MATCH (n {repo_id: $repo_id}) DETACH DELETE n",
                repo_id=repo_id,
            )
        log.info("graph_cleared", repo_id=repo_id)


# Singleton instance
_graph_repo: Optional[Neo4jRepository] = None


async def get_graph_repository() -> Neo4jRepository:
    """Get or create the graph repository singleton."""
    global _graph_repo
    if _graph_repo is None:
        _graph_repo = Neo4jRepository()
        await _graph_repo.connect()
    return _graph_repo
