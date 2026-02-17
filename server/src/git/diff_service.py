import logging
import os
import tempfile

import pygit2

from src.git.service import open_repo

logger = logging.getLogger(__name__)


def get_diff_between_commits(
    repo_path: str,
    from_hash: str,
    to_hash: str,
) -> dict:
    """Get a basic diff between two commits (file-level changes)."""
    repo = open_repo(repo_path)
    from_commit = repo.get(pygit2.Oid(hex=from_hash))
    to_commit = repo.get(pygit2.Oid(hex=to_hash))

    if not from_commit or not to_commit:
        return {"error": "Commit not found"}

    diff = repo.diff(from_commit, to_commit)

    changes = []
    for patch in diff:
        delta = patch.delta
        changes.append({
            "old_path": delta.old_file.path,
            "new_path": delta.new_file.path,
            "status": _status_char(delta.status),
            "old_size": delta.old_file.size,
            "new_size": delta.new_file.size,
        })

    return {
        "from_commit": from_hash,
        "to_commit": to_hash,
        "changes": changes,
        "stats": {
            "files_changed": diff.stats.files_changed,
            "insertions": diff.stats.insertions,
            "deletions": diff.stats.deletions,
        },
    }


def get_semantic_ifc_diff(
    repo_path: str,
    from_hash: str,
    to_hash: str,
    file_path: str,
) -> dict:
    """
    Get a semantic IFC diff between two commits for a specific file.
    Uses IfcOpenShell to compare IFC entities.
    """
    repo = open_repo(repo_path)

    from_content = _get_file_at_commit(repo, from_hash, file_path)
    to_content = _get_file_at_commit(repo, to_hash, file_path)

    if from_content is None and to_content is None:
        return {"error": "File not found in either commit"}

    try:
        import ifcopenshell
    except ImportError:
        return {"error": "IfcOpenShell not available"}

    with tempfile.TemporaryDirectory() as tmpdir:
        result = {"added": [], "removed": [], "modified": [], "unchanged_count": 0}

        from_model = None
        to_model = None

        if from_content:
            from_path = os.path.join(tmpdir, "from.ifc")
            with open(from_path, "wb") as f:
                f.write(from_content)
            from_model = ifcopenshell.open(from_path)

        if to_content:
            to_path = os.path.join(tmpdir, "to.ifc")
            with open(to_path, "wb") as f:
                f.write(to_content)
            to_model = ifcopenshell.open(to_path)

        if not from_model:
            # Everything in to_model is new
            for element in to_model.by_type("IfcProduct"):
                result["added"].append(_element_summary(element))
            return result

        if not to_model:
            # Everything in from_model is removed
            for element in from_model.by_type("IfcProduct"):
                result["removed"].append(_element_summary(element))
            return result

        # Compare by GlobalId
        from_elements = {e.GlobalId: e for e in from_model.by_type("IfcProduct")}
        to_elements = {e.GlobalId: e for e in to_model.by_type("IfcProduct")}

        from_ids = set(from_elements.keys())
        to_ids = set(to_elements.keys())

        # Added elements
        for gid in to_ids - from_ids:
            result["added"].append(_element_summary(to_elements[gid]))

        # Removed elements
        for gid in from_ids - to_ids:
            result["removed"].append(_element_summary(from_elements[gid]))

        # Check modified (same GlobalId, different attributes)
        for gid in from_ids & to_ids:
            old_el = from_elements[gid]
            new_el = to_elements[gid]
            changes = _compare_elements(old_el, new_el)
            if changes:
                summary = _element_summary(new_el)
                summary["changes"] = changes
                result["modified"].append(summary)
            else:
                result["unchanged_count"] += 1

        return result


def _get_file_at_commit(repo: pygit2.Repository, commit_hash: str, file_path: str) -> bytes | None:
    commit = repo.get(pygit2.Oid(hex=commit_hash))
    if not commit:
        return None
    tree = commit.tree
    try:
        parts = file_path.strip("/").split("/")
        for part in parts[:-1]:
            entry = tree[part]
            tree = repo.get(entry.id)
        entry = tree[parts[-1]]
        blob = repo.get(entry.id)
        return blob.data
    except (KeyError, TypeError):
        return None


def _element_summary(element) -> dict:
    return {
        "global_id": element.GlobalId,
        "ifc_class": element.is_a(),
        "name": getattr(element, "Name", None),
        "type": getattr(element, "ObjectType", None),
    }


def _compare_elements(old_el, new_el) -> list[dict]:
    """Compare two IFC elements with the same GlobalId."""
    changes = []
    # Compare direct attributes
    for attr_name in old_el.get_info().keys():
        if attr_name in ("id", "GlobalId", "OwnerHistory"):
            continue
        old_val = getattr(old_el, attr_name, None)
        new_val = getattr(new_el, attr_name, None)
        try:
            old_str = str(old_val) if old_val is not None else None
            new_str = str(new_val) if new_val is not None else None
            if old_str != new_str:
                changes.append({
                    "attribute": attr_name,
                    "old_value": old_str,
                    "new_value": new_str,
                })
        except Exception:
            pass
    return changes


def _status_char(status: int) -> str:
    mapping = {
        pygit2.GIT_DELTA_ADDED: "added",
        pygit2.GIT_DELTA_DELETED: "deleted",
        pygit2.GIT_DELTA_MODIFIED: "modified",
        pygit2.GIT_DELTA_RENAMED: "renamed",
        pygit2.GIT_DELTA_COPIED: "copied",
    }
    return mapping.get(status, "unknown")
