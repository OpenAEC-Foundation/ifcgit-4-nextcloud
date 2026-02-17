import json
import logging
import os
import subprocess
import tempfile
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.fragments.models import FragmentCache
from src.git.service import get_file_content, get_file_content_at_commit

logger = logging.getLogger(__name__)


def get_fragment_cache_dir(project_slug: str, commit_hash: str) -> str:
    """Get the cache directory for fragments of a specific commit."""
    cache_dir = os.path.join(settings.cache_dir, project_slug, "fragments", commit_hash)
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def get_cached_fragment_path(project_slug: str, commit_hash: str, file_path: str) -> str | None:
    """Check if a fragment is cached and return its path."""
    cache_dir = get_fragment_cache_dir(project_slug, commit_hash)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    frag_path = os.path.join(cache_dir, f"{base_name}.frag")
    if os.path.exists(frag_path):
        return frag_path
    return None


async def get_or_generate_fragment(
    db: AsyncSession,
    project_id: uuid.UUID,
    project_slug: str,
    repo_path: str,
    file_path: str,
    commit_hash: str,
    branch: str = "main",
) -> str | None:
    """
    Get a cached fragment or generate a new one.
    Returns the path to the .frag file, or None on failure.
    """
    # Check database cache
    result = await db.execute(
        select(FragmentCache).where(
            FragmentCache.project_id == project_id,
            FragmentCache.file_path == file_path,
            FragmentCache.commit_hash == commit_hash,
        )
    )
    cached = result.scalar_one_or_none()
    if cached and os.path.exists(cached.fragment_path):
        return cached.fragment_path

    # Check filesystem cache
    existing = get_cached_fragment_path(project_slug, commit_hash, file_path)
    if existing:
        return existing

    # Generate fragment
    frag_path = await generate_fragment(project_slug, repo_path, file_path, commit_hash, branch)
    if frag_path:
        # Store in database
        cache_entry = FragmentCache(
            project_id=project_id,
            file_path=file_path,
            commit_hash=commit_hash,
            fragment_path=frag_path,
            file_size=os.path.getsize(frag_path),
        )
        db.add(cache_entry)
        await db.commit()

    return frag_path


async def generate_fragment(
    project_slug: str,
    repo_path: str,
    file_path: str,
    commit_hash: str,
    branch: str = "main",
) -> str | None:
    """
    Generate a .frag file from an IFC file.
    Uses the Node.js converter script with @thatopen/fragments.
    """
    # Get IFC content from git
    if commit_hash:
        ifc_content = get_file_content_at_commit(repo_path, file_path, commit_hash)
    else:
        ifc_content = get_file_content(repo_path, file_path, branch)

    if not ifc_content:
        logger.error(f"IFC file not found: {file_path} at {commit_hash or branch}")
        return None

    cache_dir = get_fragment_cache_dir(project_slug, commit_hash)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    frag_output = os.path.join(cache_dir, f"{base_name}.frag")
    props_output = os.path.join(cache_dir, f"{base_name}.properties.json")

    # Write IFC to temp file
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as tmp:
        tmp.write(ifc_content)
        tmp_path = tmp.name

    try:
        # Run Node.js converter
        result = subprocess.run(
            ["node", settings.node_converter_path, tmp_path, frag_output],
            capture_output=True,
            timeout=600,  # 10 min timeout
        )

        if result.returncode != 0:
            logger.error(f"Fragment conversion failed: {result.stderr.decode()}")
            # Fallback: try Python-based conversion
            return await _generate_fragment_python(ifc_content, frag_output, props_output)

        # Generate properties JSON using IfcOpenShell
        await _generate_properties(ifc_content, props_output)

        # Generate spatial tree
        spatial_output = os.path.join(cache_dir, f"{base_name}.spatial-tree.json")
        await _generate_spatial_tree(ifc_content, spatial_output)

        logger.info(f"Fragment generated: {frag_output}")
        return frag_output

    except subprocess.TimeoutExpired:
        logger.error(f"Fragment conversion timed out for {file_path}")
        return None
    except FileNotFoundError:
        logger.warning("Node.js converter not available, trying Python fallback")
        return await _generate_fragment_python(ifc_content, frag_output, props_output)
    finally:
        os.unlink(tmp_path)


async def _generate_fragment_python(
    ifc_content: bytes, frag_output: str, props_output: str
) -> str | None:
    """Fallback: generate properties using IfcOpenShell (without .frag)."""
    try:
        await _generate_properties(ifc_content, props_output)
        # Without Node.js, we can't generate .frag files
        # The frontend will need to convert IFC client-side
        logger.warning("No .frag generated (Node.js unavailable), frontend will convert client-side")
        return None
    except Exception as e:
        logger.error(f"Python fragment fallback failed: {e}")
        return None


async def _generate_properties(ifc_content: bytes, output_path: str):
    """Generate a properties JSON file from IFC content using IfcOpenShell."""
    try:
        import ifcopenshell
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as tmp:
            tmp.write(ifc_content)
            tmp_path = tmp.name

        try:
            model = ifcopenshell.open(tmp_path)
            properties = {}

            for element in model.by_type("IfcProduct"):
                express_id = element.id()
                props = {
                    "expressID": express_id,
                    "GlobalId": element.GlobalId,
                    "Class": element.is_a(),
                    "Name": getattr(element, "Name", None),
                    "ObjectType": getattr(element, "ObjectType", None),
                    "Description": getattr(element, "Description", None),
                    "Tag": getattr(element, "Tag", None),
                }

                # Get property sets
                psets = {}
                if hasattr(element, "IsDefinedBy"):
                    for rel in element.IsDefinedBy:
                        if rel.is_a("IfcRelDefinesByProperties"):
                            pset = rel.RelatingPropertyDefinition
                            if pset.is_a("IfcPropertySet"):
                                pset_props = {}
                                for prop in pset.HasProperties:
                                    if prop.is_a("IfcPropertySingleValue"):
                                        val = prop.NominalValue
                                        pset_props[prop.Name] = val.wrappedValue if val else None
                                psets[pset.Name] = pset_props

                props["propertySets"] = psets
                properties[str(express_id)] = props

            with open(output_path, "w") as f:
                json.dump(properties, f)

        finally:
            os.unlink(tmp_path)

    except ImportError:
        logger.warning("IfcOpenShell not available for properties generation")
    except Exception as e:
        logger.error(f"Properties generation failed: {e}")


async def _generate_spatial_tree(ifc_content: bytes, output_path: str):
    """Generate a spatial tree JSON from IFC content."""
    try:
        import ifcopenshell
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as tmp:
            tmp.write(ifc_content)
            tmp_path = tmp.name

        try:
            model = ifcopenshell.open(tmp_path)
            tree = _build_spatial_tree(model)

            with open(output_path, "w") as f:
                json.dump(tree, f)

        finally:
            os.unlink(tmp_path)

    except ImportError:
        logger.warning("IfcOpenShell not available for spatial tree generation")
    except Exception as e:
        logger.error(f"Spatial tree generation failed: {e}")


def _build_spatial_tree(model) -> dict:
    """Build a hierarchical spatial tree from an IFC model."""
    tree = {"type": "IfcProject", "name": "", "children": []}

    projects = model.by_type("IfcProject")
    if projects:
        project = projects[0]
        tree["name"] = getattr(project, "Name", "Project") or "Project"
        tree["expressID"] = project.id()

    # Build hierarchy: Project -> Site -> Building -> Storey -> Space
    for site in model.by_type("IfcSite"):
        site_node = {
            "type": "IfcSite",
            "name": getattr(site, "Name", "Site") or "Site",
            "expressID": site.id(),
            "children": [],
        }
        tree["children"].append(site_node)

        for building in model.by_type("IfcBuilding"):
            building_node = {
                "type": "IfcBuilding",
                "name": getattr(building, "Name", "Building") or "Building",
                "expressID": building.id(),
                "children": [],
            }
            site_node["children"].append(building_node)

            for storey in model.by_type("IfcBuildingStorey"):
                storey_node = {
                    "type": "IfcBuildingStorey",
                    "name": getattr(storey, "Name", "Storey") or "Storey",
                    "expressID": storey.id(),
                    "children": [],
                }
                building_node["children"].append(storey_node)

                # Get elements contained in this storey
                if hasattr(storey, "ContainsElements"):
                    for rel in storey.ContainsElements:
                        for element in rel.RelatedElements:
                            storey_node["children"].append({
                                "type": element.is_a(),
                                "name": getattr(element, "Name", None) or element.is_a(),
                                "expressID": element.id(),
                            })

    return tree
