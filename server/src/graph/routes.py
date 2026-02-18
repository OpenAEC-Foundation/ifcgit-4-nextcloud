"""API routes for IFC graph database operations."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.config import settings
from src.graph.service import (
    get_graph_data,
    get_graph_stats,
    query_neighbors,
    search_graph,
    import_ifc_to_graph,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _check_neo4j_enabled():
    if not settings.neo4j_enabled:
        raise HTTPException(
            status_code=503,
            detail="Neo4j graph database is not enabled. Set NEO4J_ENABLED=true.",
        )


@router.get("/{slug}/graph/data")
async def get_project_graph(
    slug: str,
    ifc_class: str | None = Query(None, description="Filter by IFC class"),
    depth: int = Query(2, ge=1, le=5, description="Traversal depth"),
    limit: int = Query(200, ge=1, le=1000, description="Max nodes"),
    user: User = Depends(get_current_user),
):
    """Get graph nodes and edges for visualization."""
    _check_neo4j_enabled()
    data = await get_graph_data(slug, ifc_class=ifc_class, depth=depth, limit=limit)
    return data


@router.get("/{slug}/graph/stats")
async def get_project_graph_stats(
    slug: str,
    user: User = Depends(get_current_user),
):
    """Get graph statistics: node count, class distribution, etc."""
    _check_neo4j_enabled()
    stats = await get_graph_stats(slug)
    return stats


@router.get("/{slug}/graph/node/{global_id}")
async def get_node_neighbors(
    slug: str,
    global_id: str,
    depth: int = Query(1, ge=1, le=3),
    user: User = Depends(get_current_user),
):
    """Get a node and its neighbors for focused exploration."""
    _check_neo4j_enabled()
    data = await query_neighbors(slug, global_id, depth=depth)
    if not data.get("center"):
        raise HTTPException(status_code=404, detail="Entity not found in graph")
    return data


@router.get("/{slug}/graph/search")
async def search_project_graph(
    slug: str,
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
):
    """Search entities in the graph by name, class, or description."""
    _check_neo4j_enabled()
    results = await search_graph(slug, q, limit=limit)
    return {"results": results, "count": len(results)}


@router.post("/{slug}/graph/import")
async def import_to_graph(
    slug: str,
    file_path: str = Query(..., description="Path to IFC file in project repo"),
    user: User = Depends(get_current_user),
):
    """Import an IFC file into the Neo4j graph database."""
    _check_neo4j_enabled()
    # Construct the actual file path from project slug + file_path
    import os
    ifc_file = os.path.join(settings.repos_dir, slug, file_path)
    if not os.path.exists(ifc_file):
        raise HTTPException(status_code=404, detail=f"IFC file not found: {file_path}")
    result = await import_ifc_to_graph(slug, ifc_file)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Import failed"))
    return result
