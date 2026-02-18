"""Neo4j graph database service for IFC model storage and querying.

High-performance IFC-to-graph importer optimised for large (40GB+) models:
- CPU-bound IFC parsing offloaded to a ProcessPoolExecutor
- Batched Neo4j UNWIND inserts (nodes & relationships in chunks of 2000)
- Redis-backed progress tracking with phases, percentages, and ETA
- Extracts 10 relationship types covering the full IFC spatial/type/property model
"""
import json
import logging
import os
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Any

from neo4j import AsyncGraphDatabase, AsyncDriver

from src.config import settings

logger = logging.getLogger(__name__)

_driver: AsyncDriver | None = None

# Batch size for Neo4j UNWIND operations
NODE_BATCH_SIZE = 2000
REL_BATCH_SIZE = 2000


# ──────────────────────────────────────────────────────────────────────
# Neo4j driver lifecycle
# ──────────────────────────────────────────────────────────────────────

async def get_driver() -> AsyncDriver:
    """Get or create the Neo4j async driver."""
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            max_connection_pool_size=50,
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
        await session.run(
            "CREATE CONSTRAINT ifc_global_id IF NOT EXISTS "
            "FOR (n:IfcEntity) REQUIRE n.global_id IS UNIQUE"
        )
        await session.run(
            "CREATE INDEX ifc_class_idx IF NOT EXISTS "
            "FOR (n:IfcEntity) ON (n.ifc_class)"
        )
        await session.run(
            "CREATE INDEX ifc_project_idx IF NOT EXISTS "
            "FOR (n:IfcEntity) ON (n.project_id)"
        )
        await session.run(
            "CREATE INDEX ifc_project_class_idx IF NOT EXISTS "
            "FOR (n:IfcEntity) ON (n.project_id, n.ifc_class)"
        )
        logger.info("Neo4j indexes ensured")


# ──────────────────────────────────────────────────────────────────────
# Redis progress tracking
# ──────────────────────────────────────────────────────────────────────

async def _get_redis():
    """Get a Redis connection for progress tracking."""
    import redis.asyncio as aioredis
    return aioredis.from_url(settings.redis_url)


async def set_import_progress(job_id: str, data: dict):
    """Store import job progress in Redis (expires after 1 hour)."""
    r = await _get_redis()
    await r.setex(f"graph:import:{job_id}", 3600, json.dumps(data))
    await r.close()


async def get_import_progress(job_id: str) -> dict | None:
    """Read import job progress from Redis."""
    r = await _get_redis()
    raw = await r.get(f"graph:import:{job_id}")
    await r.close()
    if raw:
        return json.loads(raw)
    return None


# ──────────────────────────────────────────────────────────────────────
# CPU-bound IFC parsing (runs in ProcessPoolExecutor)
# ──────────────────────────────────────────────────────────────────────

def _parse_ifc_file(ifc_path: str, project_id: str) -> dict:
    """
    Parse an IFC file and extract all entities + relationships.

    This is a CPU-bound function designed to run in a separate process.
    Returns a dict with 'nodes' and 'relationships' lists ready for Neo4j.
    """
    import ifcopenshell

    file_size_mb = os.path.getsize(ifc_path) / (1024 * 1024)
    logger.info(f"Parsing IFC file: {ifc_path} ({file_size_mb:.1f} MB)")
    t0 = time.time()

    ifc_file = ifcopenshell.open(ifc_path)

    # ── Phase 1: Extract entities as nodes ──
    nodes = []
    global_id_set = set()  # track for dedup

    for entity in ifc_file:
        gid = getattr(entity, "GlobalId", None)
        if not gid:
            continue
        if gid in global_id_set:
            continue
        global_id_set.add(gid)

        ifc_class = entity.is_a()
        name = getattr(entity, "Name", None) or ""
        description = getattr(entity, "Description", None) or ""
        object_type = getattr(entity, "ObjectType", None) or ""
        tag = getattr(entity, "Tag", None) or ""
        predefined_type = ""
        if hasattr(entity, "PredefinedType"):
            try:
                pt = entity.PredefinedType
                predefined_type = pt if isinstance(pt, str) else ""
            except Exception:
                pass

        nodes.append({
            "global_id": gid,
            "ifc_class": ifc_class,
            "name": name,
            "description": description,
            "object_type": object_type,
            "tag": tag,
            "predefined_type": predefined_type,
            "project_id": project_id,
            "ifc_id": entity.id(),
        })

    # ── Phase 2: Extract relationships in bulk ──
    relationships = []

    # Map of (rel_type_ifc, relating_attr, related_attr, neo4j_rel_type)
    REL_EXTRACTORS = [
        ("IfcRelContainedInSpatialStructure", "RelatingStructure", "RelatedElements", "CONTAINED_IN"),
        ("IfcRelAggregates", "RelatingObject", "RelatedObjects", "PART_OF"),
        ("IfcRelDefinesByProperties", "RelatingPropertyDefinition", "RelatedObjects", "DEFINED_BY"),
        ("IfcRelDefinesByType", "RelatingType", "RelatedObjects", "HAS_TYPE"),
        ("IfcRelAssociatesMaterial", "RelatingMaterial", "RelatedObjects", "HAS_MATERIAL"),
        ("IfcRelAssociatesClassification", "RelatingClassification", "RelatedObjects", "CLASSIFIED_BY"),
        ("IfcRelVoidsElement", "RelatingBuildingElement", "RelatedOpeningElement", "HAS_OPENING"),
        ("IfcRelFillsElement", "RelatingOpeningElement", "RelatedBuildingElement", "FILLS"),
        ("IfcRelSpaceBoundary", "RelatingSpace", "RelatedBuildingElement", "BOUNDED_BY"),
        ("IfcRelConnectsElements", "RelatingElement", "RelatedElement", "CONNECTED_TO"),
    ]

    for ifc_rel_type, relating_attr, related_attr, neo4j_type in REL_EXTRACTORS:
        try:
            rel_entities = ifc_file.by_type(ifc_rel_type)
        except Exception:
            continue

        for rel_entity in rel_entities:
            relating = getattr(rel_entity, relating_attr, None)
            if relating is None:
                continue
            relating_gid = getattr(relating, "GlobalId", None)
            if not relating_gid or relating_gid not in global_id_set:
                # For materials/classifications without GlobalId, skip
                continue

            related = getattr(rel_entity, related_attr, None)
            if related is None:
                continue

            # Handle single entity vs list
            if not isinstance(related, (list, tuple)):
                related = [related]

            for obj in related:
                obj_gid = getattr(obj, "GlobalId", None)
                if obj_gid and obj_gid in global_id_set:
                    relationships.append({
                        "from_id": obj_gid,
                        "to_id": relating_gid,
                        "type": neo4j_type,
                    })

    elapsed = time.time() - t0
    logger.info(
        f"IFC parsed in {elapsed:.1f}s: "
        f"{len(nodes)} entities, {len(relationships)} relationships"
    )

    return {
        "nodes": nodes,
        "relationships": relationships,
        "parse_time": elapsed,
        "file_size_mb": file_size_mb,
    }


# ──────────────────────────────────────────────────────────────────────
# Neo4j batch import
# ──────────────────────────────────────────────────────────────────────

async def _batch_insert_nodes(
    session, nodes: list[dict], project_id: str, job_id: str | None = None,
) -> int:
    """Insert nodes in batches using UNWIND for maximum throughput."""
    total = len(nodes)
    created = 0

    for i in range(0, total, NODE_BATCH_SIZE):
        batch = nodes[i: i + NODE_BATCH_SIZE]
        result = await session.run(
            """
            UNWIND $batch AS props
            CREATE (n:IfcEntity)
            SET n = props
            RETURN count(n) AS cnt
            """,
            batch=batch,
        )
        record = await result.single()
        created += record["cnt"]

        if job_id:
            pct = min(30 + int((i / total) * 30), 59)  # 30-59%
            await set_import_progress(job_id, {
                "status": "running",
                "phase": "inserting_nodes",
                "phase_label": f"Inserting nodes ({created}/{total})",
                "progress": pct,
                "nodes_created": created,
                "nodes_total": total,
            })

    # Add dynamic labels via APOC (if available) or skip gracefully
    try:
        await session.run(
            """
            MATCH (n:IfcEntity {project_id: $pid})
            WHERE NOT n.ifc_class IN labels(n)
            WITH n, n.ifc_class AS cls
            CALL apoc.create.addLabels(n, [cls]) YIELD node
            RETURN count(node)
            """,
            pid=project_id,
        )
    except Exception as e:
        logger.warning(f"APOC addLabels not available, skipping dynamic labels: {e}")

    return created


async def _batch_insert_relationships(
    session, relationships: list[dict], project_id: str, job_id: str | None = None,
) -> int:
    """Insert relationships in batches, grouped by type for UNWIND efficiency."""
    # Group by relationship type for optimal Cypher
    by_type: dict[str, list[dict]] = {}
    for rel in relationships:
        rt = rel["type"]
        by_type.setdefault(rt, []).append(rel)

    total = len(relationships)
    created = 0

    for rel_type, rels in by_type.items():
        # Use UNWIND with dynamic relationship type via APOC or fallback
        for i in range(0, len(rels), REL_BATCH_SIZE):
            batch = rels[i: i + REL_BATCH_SIZE]
            pairs = [{"f": r["from_id"], "t": r["to_id"]} for r in batch]

            try:
                # Try APOC for dynamic rel type (fastest)
                result = await session.run(
                    """
                    UNWIND $pairs AS pair
                    MATCH (a:IfcEntity {global_id: pair.f, project_id: $pid})
                    MATCH (b:IfcEntity {global_id: pair.t, project_id: $pid})
                    CALL apoc.create.relationship(a, $relType, {}, b) YIELD rel
                    RETURN count(rel) AS cnt
                    """,
                    pairs=pairs,
                    pid=project_id,
                    relType=rel_type,
                )
                record = await result.single()
                created += record["cnt"]
            except Exception:
                # Fallback: per-type static Cypher (still batched)
                cypher = f"""
                    UNWIND $pairs AS pair
                    MATCH (a:IfcEntity {{global_id: pair.f, project_id: $pid}})
                    MATCH (b:IfcEntity {{global_id: pair.t, project_id: $pid}})
                    CREATE (a)-[:`{rel_type}`]->(b)
                    RETURN count(*) AS cnt
                """
                result = await session.run(cypher, pairs=pairs, pid=project_id)
                record = await result.single()
                created += record["cnt"]

            if job_id:
                pct = min(60 + int((created / max(total, 1)) * 35), 94)  # 60-94%
                await set_import_progress(job_id, {
                    "status": "running",
                    "phase": "inserting_relationships",
                    "phase_label": f"Inserting relationships ({created}/{total})",
                    "progress": pct,
                    "rels_created": created,
                    "rels_total": total,
                })

    return created


# ──────────────────────────────────────────────────────────────────────
# Main import function (async, uses ProcessPool for parsing)
# ──────────────────────────────────────────────────────────────────────

async def import_ifc_to_graph(
    project_id: str,
    ifc_path: str,
    job_id: str | None = None,
) -> dict:
    """
    High-performance IFC-to-Neo4j import pipeline.

    1. Parse IFC file in a separate process (CPU-bound, no GIL)
    2. Clear existing project graph data
    3. Batch-insert nodes (UNWIND, 2000/batch)
    4. Batch-insert relationships (UNWIND per type, 2000/batch)
    5. Track progress in Redis throughout

    For 40GB+ files, the parsing phase runs in a ProcessPoolExecutor
    so the event loop stays responsive.
    """
    import asyncio

    t0 = time.time()

    if job_id:
        await set_import_progress(job_id, {
            "status": "running",
            "phase": "parsing",
            "phase_label": "Parsing IFC file...",
            "progress": 5,
        })

    # ── Phase 1: Parse IFC in separate process ──
    try:
        loop = asyncio.get_event_loop()
        with ProcessPoolExecutor(max_workers=1) as pool:
            parsed = await loop.run_in_executor(
                pool, _parse_ifc_file, ifc_path, project_id
            )
    except Exception as e:
        error_msg = f"IFC parsing failed: {e}"
        logger.error(error_msg)
        if job_id:
            await set_import_progress(job_id, {
                "status": "failed", "error": error_msg, "progress": 0,
            })
        return {"success": False, "error": error_msg}

    nodes = parsed["nodes"]
    relationships = parsed["relationships"]

    if not nodes:
        if job_id:
            await set_import_progress(job_id, {
                "status": "completed",
                "progress": 100,
                "nodes_created": 0,
                "relationships_created": 0,
            })
        return {"success": True, "nodes_created": 0, "relationships_created": 0}

    if job_id:
        await set_import_progress(job_id, {
            "status": "running",
            "phase": "clearing",
            "phase_label": "Clearing previous graph data...",
            "progress": 28,
        })

    driver = await get_driver()

    async with driver.session() as session:
        # ── Phase 2: Clear old data (batched delete for large graphs) ──
        while True:
            result = await session.run(
                """
                MATCH (n:IfcEntity {project_id: $pid})
                WITH n LIMIT 10000
                DETACH DELETE n
                RETURN count(*) AS deleted
                """,
                pid=project_id,
            )
            record = await result.single()
            if record["deleted"] == 0:
                break

        # ── Phase 3: Insert nodes ──
        nodes_created = await _batch_insert_nodes(session, nodes, project_id, job_id)

        # ── Phase 4: Insert relationships ──
        rels_created = await _batch_insert_relationships(
            session, relationships, project_id, job_id
        )

    elapsed = time.time() - t0

    result_data = {
        "success": True,
        "nodes_created": nodes_created,
        "relationships_created": rels_created,
        "parse_time_s": round(parsed["parse_time"], 1),
        "total_time_s": round(elapsed, 1),
        "file_size_mb": round(parsed["file_size_mb"], 1),
        "throughput_nodes_per_s": round(nodes_created / max(elapsed, 0.01)),
    }

    if job_id:
        await set_import_progress(job_id, {
            "status": "completed",
            "progress": 100,
            **result_data,
        })

    logger.info(
        f"Graph import complete: {nodes_created} nodes, {rels_created} rels "
        f"in {elapsed:.1f}s ({result_data['throughput_nodes_per_s']} nodes/s)"
    )

    return result_data


# ──────────────────────────────────────────────────────────────────────
# Query functions (unchanged from before)
# ──────────────────────────────────────────────────────────────────────

async def get_graph_data(
    project_id: str,
    ifc_class: str | None = None,
    depth: int = 2,
    limit: int = 200,
) -> dict[str, list]:
    """Get graph nodes and edges for visualization."""
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
        result = await session.run(
            "MATCH (n:IfcEntity {project_id: $pid}) RETURN count(n) AS cnt",
            pid=project_id,
        )
        record = await result.single()
        node_count = record["cnt"]

        result = await session.run(
            "MATCH (n:IfcEntity {project_id: $pid})-[r]->() RETURN count(r) AS cnt",
            pid=project_id,
        )
        record = await result.single()
        rel_count = record["cnt"]

        result = await session.run(
            """
            MATCH (n:IfcEntity {project_id: $pid})
            RETURN n.ifc_class AS ifc_class, count(n) AS count
            ORDER BY count DESC LIMIT 30
            """,
            pid=project_id,
        )
        class_dist = [{"ifc_class": r["ifc_class"], "count": r["count"]} async for r in result]

        result = await session.run(
            """
            MATCH (n:IfcEntity {project_id: $pid})-[r]->()
            RETURN type(r) AS rel_type, count(r) AS count
            ORDER BY count DESC
            """,
            pid=project_id,
        )
        rel_dist = [{"type": r["rel_type"], "count": r["count"]} async for r in result]

        return {
            "node_count": node_count,
            "relationship_count": rel_count,
            "class_distribution": class_dist,
            "relationship_distribution": rel_dist,
        }


async def query_neighbors(
    project_id: str, global_id: str, depth: int = 1,
) -> dict:
    """Get neighbors of a specific entity."""
    driver = await get_driver()
    depth = min(depth, 3)

    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (center:IfcEntity {global_id: $gid, project_id: $pid})
            OPTIONAL MATCH path = (center)-[r*1..""" + str(depth) + """]-(neighbor:IfcEntity {project_id: $pid})
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
    project_id: str, query: str, limit: int = 50,
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
            pid=project_id, query=query, limit=limit,
        )

        return [
            {
                "id": r["n"].get("global_id"),
                "ifc_class": r["n"].get("ifc_class"),
                "name": r["n"].get("name", ""),
                "description": r["n"].get("description", ""),
            }
            async for r in result
        ]


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
    if "Material" in ifc_class:
        return "material"
    return "other"
