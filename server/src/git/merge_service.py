import logging
import os
import subprocess
import tempfile

import pygit2

from src.git.service import open_repo

logger = logging.getLogger(__name__)


def merge_branches(
    repo_path: str,
    source_branch: str,
    target_branch: str,
    author_name: str,
    author_email: str,
    message: str | None = None,
) -> dict:
    """
    Merge source_branch into target_branch.
    For IFC files, attempts to use ifcmerge for 3-way merge.
    Returns merge result with status and details.
    """
    repo = open_repo(repo_path)
    source_ref = f"refs/heads/{source_branch}"
    target_ref = f"refs/heads/{target_branch}"

    if source_ref not in repo.references or target_ref not in repo.references:
        return {"status": "error", "message": "Branch not found"}

    source_commit = repo.get(repo.references[source_ref].target)
    target_commit = repo.get(repo.references[target_ref].target)

    # Find merge base
    merge_base = repo.merge_base(source_commit.id, target_commit.id)
    if not merge_base:
        return {"status": "error", "message": "No common ancestor found"}

    # Check if fast-forward is possible
    if merge_base == target_commit.id:
        # Fast-forward
        repo.references[target_ref].set_target(source_commit.id)
        return {
            "status": "fast-forward",
            "commit": str(source_commit.id),
            "message": f"Fast-forwarded {target_branch} to {source_branch}",
        }

    # Perform merge
    merge_result = repo.merge_analysis(source_commit.id)

    if merge_result[0] & pygit2.GIT_MERGE_ANALYSIS_UP_TO_DATE:
        return {"status": "up-to-date", "message": "Already up to date"}

    # Try automatic merge via index
    index = repo.merge_commits(target_commit, source_commit)

    if index.conflicts:
        # Check if conflicts are in IFC files - try ifcmerge
        ifc_conflicts = [
            path for path in _get_conflict_paths(index)
            if path.lower().endswith(".ifc")
        ]

        if ifc_conflicts:
            resolved = _try_ifcmerge(repo, merge_base, target_commit, source_commit, ifc_conflicts)
            if resolved:
                # Remove resolved conflicts from index
                for path in ifc_conflicts:
                    if path in resolved:
                        # TODO: Update index with resolved content
                        pass

        remaining_conflicts = [
            path for path in _get_conflict_paths(index)
            if path not in (ifc_conflicts if ifc_conflicts else [])
        ]

        if remaining_conflicts:
            return {
                "status": "conflict",
                "conflicts": remaining_conflicts,
                "message": "Merge conflicts detected",
            }

    # Write tree and create merge commit
    tree_id = index.write_tree(repo)

    if not message:
        message = f"Merge branch '{source_branch}' into {target_branch}"

    sig = pygit2.Signature(author_name, author_email)
    commit_id = repo.create_commit(
        target_ref,
        sig,
        sig,
        message,
        tree_id,
        [target_commit.id, source_commit.id],
    )

    return {
        "status": "merged",
        "commit": str(commit_id),
        "message": message,
    }


def _get_conflict_paths(index) -> list[str]:
    """Extract conflicting file paths from a merge index."""
    paths = []
    if index.conflicts:
        for conflict in index.conflicts:
            ancestor, ours, theirs = conflict
            path = (ours or theirs or ancestor).path
            if path not in paths:
                paths.append(path)
    return paths


def _try_ifcmerge(
    repo: pygit2.Repository,
    base_oid: pygit2.Oid,
    ours_commit: pygit2.Commit,
    theirs_commit: pygit2.Commit,
    ifc_paths: list[str],
) -> dict[str, bytes] | None:
    """
    Try to merge IFC files using ifcmerge.
    Returns dict of path -> merged content, or None if ifcmerge is not available.
    """
    # Check if ifcmerge is available
    try:
        subprocess.run(["ifcmerge", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        logger.warning("ifcmerge not available, IFC conflicts cannot be auto-resolved")
        return None

    base_commit = repo.get(base_oid)
    resolved = {}

    for ifc_path in ifc_paths:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract the three versions
            base_file = os.path.join(tmpdir, "base.ifc")
            ours_file = os.path.join(tmpdir, "ours.ifc")
            theirs_file = os.path.join(tmpdir, "theirs.ifc")
            output_file = os.path.join(tmpdir, "merged.ifc")

            _extract_file(repo, base_commit.tree, ifc_path, base_file)
            _extract_file(repo, ours_commit.tree, ifc_path, ours_file)
            _extract_file(repo, theirs_commit.tree, ifc_path, theirs_file)

            try:
                result = subprocess.run(
                    ["ifcmerge", base_file, ours_file, theirs_file, "-o", output_file],
                    capture_output=True,
                    timeout=300,
                )
                if result.returncode == 0 and os.path.exists(output_file):
                    with open(output_file, "rb") as f:
                        resolved[ifc_path] = f.read()
                    logger.info(f"ifcmerge resolved {ifc_path}")
                else:
                    logger.warning(f"ifcmerge failed for {ifc_path}: {result.stderr.decode()}")
            except subprocess.TimeoutExpired:
                logger.warning(f"ifcmerge timed out for {ifc_path}")

    return resolved if resolved else None


def _extract_file(repo: pygit2.Repository, tree: pygit2.Tree, path: str, dest: str):
    """Extract a single file from a tree to disk."""
    parts = path.split("/")
    for part in parts[:-1]:
        entry = tree[part]
        tree = repo.get(entry.id)
    entry = tree[parts[-1]]
    blob = repo.get(entry.id)
    with open(dest, "wb") as f:
        f.write(blob.data)
