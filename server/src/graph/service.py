"""Neo4j graph database service for IFC model storage and querying.

Stores IFC entities as graph nodes with their relationships, enabling
spatial queries, type traversal, and visual graph exploration.
"""
import logging
from typing import Any

from neo4j import AsyncGraphDatabase, AsyncDriver

from src.config import settings

logger = logging.getLogger(__name__)

_driver: AsyncDriver | None = None


async def get_driver() -> AsyncDriver:
    """Get or create the Neo4j async driver."""
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


async def close_driver():
    """Close the Neo4j driver on shutdown."""
    global _driver
    if _driver:
        await _driver.close()
        _driver = None


async def ensure_indexes():
    """Create indexes and constraints for IFC graph nodes."""
    driver = await get_driver()
    async with driver.session() as session:
        # Unique constraint on GlobalId
        await session.run(
            "CREATE CONSTRAINT ifc_global_id IF NOT EXISTS "
            "FOR (n:IfcEntity) REQUIRE n.global_id IS UNIQUE"
        )
        # Index on ifc_class for fast type queries
        await session.run(
            "CREATE INDEX ifc_class_idx IF NOT EXISTS "
            "FOR (n:IfcEntity) ON (n.ifc_class)"
        )
        # Index on project for isolation
        await session.run(
            "CREATE INDEX ifc_project_idx IF NOT EXISTS "
            "FOR (n:IfcEntity) ON (n.project_id)"
        )
        logger.info("Neo4j indexes ensured")


async def import_ifc_to_graph(project_id: str, ifc_path: str) -> dict:
    """Parse an IFC file and import entities + relationships into Neo4j.

    Creates nodes for each IFC entity with properties:
    - global_id, ifc_class, name, description, project_id
    Creates relationships based on IFC spatial structure:
    - CONTAINS, AGGREGATES, DEFINED_BY, ASSOCIATES, etc.
    """
    try:
        import ifcopenshell
    except ImportError:
        return {"success": False, "error": "ifcopenshell not available"}

    ifc_file = ifcopenshell.open(ifc_path)
    driver = await get_driver()

    nodes_created = 0
    rels_created = 0

    async with driver.session() as session:
        # Clear existing data for this project
        await session.run(
            "MATCH (n:IfcEntity {project_id: $pid}) DETACH DELETE n",
            pid=project_id,
        )

        # Import entities as nodes
        entities = []
        for entity in ifc_file:
            if not hasattr(entity, "GlobalId"):
                continue
            node = {
                "global_id": entity.GlobalId,
                "ifc_class": entity.is_a(),
                "name": getattr(entity, "Name", None) or "",
                "description": getattr(entity, "Description", None) or "",
                "project_id": project_id,
                "ifc_id": entity.id(),
            }
            entities.append(node)

        # Batch insert nodes (500 at a time)
        for i in range(0, len(entities), 500):
            batch = entities[i : i + 500]
            result = await session.run(
                """
                UNWIND $batch AS props
                CREATE (n:IfcEntity)
                SET n = props
                SET n:` + props.ifc_class + `
                RETURN count(n) AS cnt
                """,
                batch=batch,
            )
            record = await result.single()
            nodes_created += record["cnt"]

        # Add dynamic label for ifc_class
        await session.run(
            """
            MATCH (n:IfcEntity {project_id: $pid})
            WITH n, n.ifc_class AS cls
            CALL apoc.create.addLabels(n, [cls]) YIELD node
            RETURN count(node)
            """,
            pid=project_id,
        )

        # Import spatial containment relationships
        for rel_entity in ifc_file.by_type("IfcRelContainedInSpatialStructure"):
            container_id = rel_entity.RelatingStructure.GlobalId
            for element in rel_entity.RelatedElements:
                if hasattr(element, "GlobalId"):
                    result = await session.run(
                        """
                        MATCH (a:IfcEntity {global_id: $from_id, project_id: $pid})
                        MATCH (b:IfcEntity {global_id: $to_id, project_id: $pid})
                        CREATE (a)-[:CONTAINED_IN]->(b)
                        RETURN count(*) AS cnt
                        """,
                        from_id=element.GlobalId,
                        to_id=container_id,
                        pid=project_id,
                    )
                    record = await result.single()
                    rels_created += record["cnt"]

        # Import aggregation relationships
        for rel_entity in ifc_file.by_type("IfcRelAggregates"):
            parent_id = rel_entity.RelatingObject.GlobalId
            for child in rel_entity.RelatedObjects:
                if hasattr(child, "GlobalId"):
                    result = await session.run(
                        """
                        MATCH (a:IfcEntity {global_id: $from_id, project_id: $pid})
                        MATCH (b:IfcEntity {global_id: $to_id, project_id: $pid})
                        CREATE (a)-[:PART_OF]->(b)
                        RETURN count(*) AS cnt
                        """,
                        from_id=child.GlobalId,
                        to_id=parent_id,
                        pid=project_id,
                    )
                    record = await result.single()
                    rels_created += record["cnt"]

        # Import property set associations
        for rel_entity in ifc_file.by_type("IfcRelDefinesByProperties"):
            pset = rel_entity.RelatingPropertyDefinition
            if not hasattr(pset, "GlobalId"):
                continue
            for obj in rel_entity.RelatedObjects:
                if hasattr(obj, "GlobalId"):
                    result = await session.run(
                        """
                        MATCH (a:IfcEntity {global_id: $from_id, project_id: $pid})
                        MATCH (b:IfcEntity {global_id: $to_id, project_id: $pid})
                        CREATE (a)-[:DEFINED_BY]->(b)
                        RETURN count(*) AS cnt
                        """,
                        from_id=obj.GlobalId,
                        to_id=pset.GlobalId,
                        pid=project_id,
                    )
                    record = await result.single()
                    rels_created += record["cnt"]

        # Import type associations
        for rel_entity in ifc_file.by_type("IfcRelDefinesByType"):
            type_obj = rel_entity.RelatingType
            if not hasattr(type_obj, "GlobalId"):
                continue
            for obj in rel_entity.RelatedObjects:
                if hasattr(obj, "GlobalId"):
                    result = await session.run(
                        """
                        MATCH (a:IfcEntity {global_id: $from_id, project_id: $pid})
                        MATCH (b:IfcEntity {global_id: $to_id, project_id: $pid})
                        CREATE (a)-[:HAS_TYPE]->(b)
                        RETURN count(*) AS cnt
                        """,
                        from_id=obj.GlobalId,
                        to_id=type_obj.GlobalId,
                        pid=project_id,
                    )
                    record = await result.single()
                    rels_created += record["cnt"]

    return {
        "success": True,
        "nodes_created": nodes_created,
        "relationships_created": rels_created,
    }


async def get_graph_data(
    project_id: str,
    ifc_class: str | None = None,
    depth: int = 2,
    limit: int = 200,
) -> dict[str, list]:
    """Get graph nodes and edges for visualization.

    Returns data in a format suitable for frontend graph libraries (d3, vis.js, cytoscape).
    """
    driver = await get_driver()

    async with driver.session() as session:
        if ifc_class:
            result = await session.run(
                """
                MATCH (n:IfcEntity {project_id: $pid, ifc_class: $cls})
                WITH n LIMIT $limit
                OPTIONAL MATCH path = (n)-[r*1..""" + str(depth) + """]->(m:IfcEntity {project_id: $pid})
                WITH collect(DISTINCT n) + collect(DISTINCT m) AS allNodes,
                     collect(DISTINCT r) AS allRels
                UNWIND allNodes AS node
                WITH collect(DISTINCT node) AS nodes, allRels
                UNWIND allRels AS relList
                UNWIND relList AS rel
                WITH nodes, collect(DISTINCT rel) AS rels
                RETURN nodes, rels
                """,
                pid=project_id,
                cls=ifc_class,
                limit=limit,
            )
        else:
            result = await session.run(
                """
                MATCH (n:IfcEntity {project_id: $pid})
                WITH n LIMIT $limit
                OPTIONAL MATCH (n)-[r]->(m:IfcEntity {project_id: $pid})
                WITH collect(DISTINCT n) + collect(DISTINCT m) AS allNodes,
                     collect(DISTINCT r) AS rels
                UNWIND allNodes AS node
                WITH collect(DISTINCT node) AS nodes, rels
                RETURN nodes, rels
                """,
                pid=project_id,
                limit=limit,
            )

        record = await result.single()
        if not record:
            return {"nodes": [], "edges": []}

        nodes = []
        seen_ids = set()
        for node in record["nodes"]:
            if node is None:
                continue
            gid = node.get("global_id", "")
            if gid in seen_ids:
                continue
            seen_ids.add(gid)
            nodes.append({
                "id": gid,
                "label": node.get("name") or node.get("ifc_class", ""),
                "ifc_class": node.get("ifc_class", ""),
                "name": node.get("name", ""),
                "group": _get_class_group(node.get("ifc_class", "")),
            })

        edges = []
        for rel in record["rels"]:
            if rel is None:
                continue
            edges.append({
                "source": rel.start_node.get("global_id", ""),
                "target": rel.end_node.get("global_id", ""),
                "type": rel.type,
            })

        return {"nodes": nodes, "edges": edges}


async def get_graph_stats(project_id: str) -> dict:
    """Get statistics about the graph for a project."""
    driver = await get_driver()

    async with driver.session() as session:
        # Node count
        result = await session.run(
            "MATCH (n:IfcEntity {project_id: $pid}) RETURN count(n) AS cnt",
            pid=project_id,
        )
        record = await result.single()
        node_count = record["cnt"]

        # Relationship count
        result = await session.run(
            """
            MATCH (n:IfcEntity {project_id: $pid})-[r]->()
            RETURN count(r) AS cnt
            """,
            pid=project_id,
        )
        record = await result.single()
        rel_count = record["cnt"]

        # Class distribution
        result = await session.run(
            """
            MATCH (n:IfcEntity {project_id: $pid})
            RETURN n.ifc_class AS ifc_class, count(n) AS count
            ORDER BY count DESC
            LIMIT 30
            """,
            pid=project_id,
        )
        class_dist = []
        async for record in result:
            class_dist.append({
                "ifc_class": record["ifc_class"],
                "count": record["count"],
            })

        # Relationship type distribution
        result = await session.run(
            """
            MATCH (n:IfcEntity {project_id: $pid})-[r]->()
            RETURN type(r) AS rel_type, count(r) AS count
            ORDER BY count DESC
            """,
            pid=project_id,
        )
        rel_dist = []
        async for record in result:
            rel_dist.append({
                "type": record["rel_type"],
                "count": record["count"],
            })

        return {
            "node_count": node_count,
            "relationship_count": rel_count,
            "class_distribution": class_dist,
            "relationship_distribution": rel_dist,
        }


async def query_neighbors(
    project_id: str,
    global_id: str,
    depth: int = 1,
) -> dict:
    """Get neighbors of a specific entity."""
    driver = await get_driver()

    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (center:IfcEntity {global_id: $gid, project_id: $pid})
            OPTIONAL MATCH path = (center)-[r*1..""" + str(min(depth, 3)) + """]-(neighbor:IfcEntity {project_id: $pid})
            WITH center,
                 collect(DISTINCT neighbor) AS neighbors,
                 [p IN collect(DISTINCT path) | relationships(p)] AS relPaths
            UNWIND relPaths AS relPath
            UNWIND relPath AS rel
            WITH center, neighbors, collect(DISTINCT rel) AS rels
            RETURN center, neighbors, rels
            """,
            gid=global_id,
            pid=project_id,
        )

        record = await result.single()
        if not record:
            return {"center": None, "nodes": [], "edges": []}

        center_node = record["center"]
        center = {
            "id": center_node.get("global_id"),
            "label": center_node.get("name") or center_node.get("ifc_class"),
            "ifc_class": center_node.get("ifc_class"),
            "name": center_node.get("name", ""),
            "group": _get_class_group(center_node.get("ifc_class", "")),
        }

        nodes = [center]
        seen = {center["id"]}
        for node in record["neighbors"]:
            if node is None:
                continue
            gid = node.get("global_id")
            if gid in seen:
                continue
            seen.add(gid)
            nodes.append({
                "id": gid,
                "label": node.get("name") or node.get("ifc_class"),
                "ifc_class": node.get("ifc_class"),
                "name": node.get("name", ""),
                "group": _get_class_group(node.get("ifc_class", "")),
            })

        edges = []
        for rel in record["rels"]:
            if rel is None:
                continue
            edges.append({
                "source": rel.start_node.get("global_id"),
                "target": rel.end_node.get("global_id"),
                "type": rel.type,
            })

        return {"center": center, "nodes": nodes, "edges": edges}


async def search_graph(
    project_id: str,
    query: str,
    limit: int = 50,
) -> list[dict]:
    """Full-text search on graph nodes."""
    driver = await get_driver()

    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (n:IfcEntity {project_id: $pid})
            WHERE n.name CONTAINS $query
               OR n.ifc_class CONTAINS $query
               OR n.description CONTAINS $query
            RETURN n
            ORDER BY n.ifc_class, n.name
            LIMIT $limit
            """,
            pid=project_id,
            query=query,
            limit=limit,
        )

        nodes = []
        async for record in result:
            node = record["n"]
            nodes.append({
                "id": node.get("global_id"),
                "ifc_class": node.get("ifc_class"),
                "name": node.get("name", ""),
                "description": node.get("description", ""),
            })
        return nodes


def _get_class_group(ifc_class: str) -> str:
    """Map IFC class to a visual group for coloring in the graph."""
    if "Site" in ifc_class:
        return "site"
    if "Building" in ifc_class and "Element" not in ifc_class:
        return "building"
    if "Storey" in ifc_class or "Floor" in ifc_class:
        return "storey"
    if "Space" in ifc_class or "Room" in ifc_class:
        return "space"
    if "Wall" in ifc_class:
        return "wall"
    if "Slab" in ifc_class or "Roof" in ifc_class:
        return "slab"
    if "Column" in ifc_class or "Beam" in ifc_class or "Member" in ifc_class:
        return "structural"
    if "Window" in ifc_class or "Door" in ifc_class:
        return "opening"
    if "Pipe" in ifc_class or "Duct" in ifc_class or "Flow" in ifc_class:
        return "mep"
    if "Property" in ifc_class or "Quantity" in ifc_class:
        return "property"
    if "Type" in ifc_class:
        return "type"
    return "other"
