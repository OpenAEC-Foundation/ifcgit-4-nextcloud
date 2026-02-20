import logging
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pygit2

from src.config import settings

logger = logging.getLogger(__name__)


@dataclass
class CommitInfo:
    hash: str
    message: str
    author_name: str
    author_email: str
    timestamp: int
    files_changed: list[str] | None = None


def init_bare_repo(repo_path: str) -> pygit2.Repository:
    """Initialize a new bare Git repository."""
    os.makedirs(repo_path, exist_ok=True)
    repo = pygit2.init_repository(repo_path, bare=True)
    logger.info(f"Initialized bare repo at {repo_path}")
    return repo


def open_repo(repo_path: str) -> pygit2.Repository:
    """Open an existing Git repository."""
    return pygit2.Repository(repo_path)


def get_working_dir(project_slug: str, branch: str = "main") -> str:
    """Get or create a working directory for a project branch."""
    work_dir = os.path.join(settings.working_dir, project_slug, branch)
    os.makedirs(work_dir, exist_ok=True)
    return work_dir


def checkout_to_working_dir(repo_path: str, project_slug: str, branch: str = "main") -> str:
    """Checkout the latest commit of a branch into a working directory."""
    repo = open_repo(repo_path)
    work_dir = get_working_dir(project_slug, branch)

    # Resolve branch reference
    ref_name = f"refs/heads/{branch}"
    if ref_name not in repo.references:
        return work_dir  # Empty repo, return empty dir

    ref = repo.references[ref_name]
    commit = repo.get(ref.target)
    tree = commit.tree

    _extract_tree(repo, tree, work_dir)
    return work_dir


def _extract_tree(repo: pygit2.Repository, tree: pygit2.Tree, dest: str):
    """Recursively extract a Git tree to a directory."""
    for entry in tree:
        entry_path = os.path.join(dest, entry.name)
        obj = repo.get(entry.id)
        if obj.type == pygit2.GIT_OBJECT_BLOB:
            with open(entry_path, "wb") as f:
                f.write(obj.data)
        elif obj.type == pygit2.GIT_OBJECT_TREE:
            os.makedirs(entry_path, exist_ok=True)
            _extract_tree(repo, obj, entry_path)


def commit_file(
    repo_path: str,
    file_path: str,
    file_data: bytes,
    message: str,
    author_name: str,
    author_email: str,
    branch: str = "main",
) -> str:
    """Add or update a file in the repo and create a commit. Returns commit hash."""
    repo = open_repo(repo_path)
    ref_name = f"refs/heads/{branch}"

    # Build tree
    if ref_name in repo.references:
        ref = repo.references[ref_name]
        parent_commit = repo.get(ref.target)
        tree_builder = repo.TreeBuilder(parent_commit.tree)
        parents = [parent_commit.id]
    else:
        tree_builder = repo.TreeBuilder()
        parents = []

    # Handle nested paths: build tree hierarchy
    parts = file_path.split("/")
    if len(parts) == 1:
        # Simple file at root
        blob_id = repo.create_blob(file_data)
        tree_builder.insert(file_path, blob_id, pygit2.GIT_FILEMODE_BLOB)
    else:
        # Nested: need to build subtrees
        blob_id = repo.create_blob(file_data)
        tree_id = _insert_nested(repo, tree_builder, parts, blob_id)
        # tree_builder already has the root entry inserted
        pass

    tree_id = tree_builder.write()

    # Create commit
    sig = pygit2.Signature(author_name, author_email)
    commit_id = repo.create_commit(
        ref_name,
        sig,  # author
        sig,  # committer
        message,
        tree_id,
        parents,
    )

    logger.info(f"Created commit {commit_id} on {branch}: {message}")
    return str(commit_id)


def _insert_nested(
    repo: pygit2.Repository,
    parent_builder: pygit2.TreeBuilder,
    parts: list[str],
    blob_id: pygit2.Oid,
) -> pygit2.Oid:
    """Insert a blob at a nested path by building subtrees."""
    if len(parts) == 1:
        parent_builder.insert(parts[0], blob_id, pygit2.GIT_FILEMODE_BLOB)
        return parent_builder.write()

    dir_name = parts[0]
    remaining = parts[1:]

    # Check if directory already exists in parent
    try:
        existing = parent_builder.get(dir_name)
        if existing:
            sub_tree = repo.get(existing.id)
            sub_builder = repo.TreeBuilder(sub_tree)
        else:
            sub_builder = repo.TreeBuilder()
    except Exception:
        sub_builder = repo.TreeBuilder()

    _insert_nested(repo, sub_builder, remaining, blob_id)
    sub_tree_id = sub_builder.write()
    parent_builder.insert(dir_name, sub_tree_id, pygit2.GIT_FILEMODE_TREE)
    return parent_builder.write()


def delete_file(
    repo_path: str,
    file_path: str,
    message: str,
    author_name: str,
    author_email: str,
    branch: str = "main",
) -> str | None:
    """Delete a file from the repo. Returns commit hash or None if file not found."""
    repo = open_repo(repo_path)
    ref_name = f"refs/heads/{branch}"

    if ref_name not in repo.references:
        return None

    ref = repo.references[ref_name]
    parent_commit = repo.get(ref.target)
    tree_builder = repo.TreeBuilder(parent_commit.tree)

    try:
        tree_builder.remove(file_path)
    except KeyError:
        return None

    tree_id = tree_builder.write()
    sig = pygit2.Signature(author_name, author_email)
    commit_id = repo.create_commit(
        ref_name, sig, sig, message, tree_id, [parent_commit.id]
    )
    return str(commit_id)


def get_commit_log(repo_path: str, branch: str = "main", limit: int = 50) -> list[CommitInfo]:
    """Get commit history for a branch."""
    repo = open_repo(repo_path)
    ref_name = f"refs/heads/{branch}"

    if ref_name not in repo.references:
        return []

    ref = repo.references[ref_name]
    commits = []
    for commit in repo.walk(ref.target, pygit2.GIT_SORT_TIME):
        commits.append(CommitInfo(
            hash=str(commit.id),
            message=commit.message.strip(),
            author_name=commit.author.name,
            author_email=commit.author.email,
            timestamp=commit.commit_time,
        ))
        if len(commits) >= limit:
            break

    return commits


def list_files(repo_path: str, branch: str = "main", path: str = "") -> list[dict]:
    """List files in a branch at a given path."""
    repo = open_repo(repo_path)
    ref_name = f"refs/heads/{branch}"

    if ref_name not in repo.references:
        return []

    ref = repo.references[ref_name]
    commit = repo.get(ref.target)
    tree = commit.tree

    # Navigate to path
    if path:
        for part in path.strip("/").split("/"):
            entry = tree[part]
            tree = repo.get(entry.id)

    files = []
    for entry in tree:
        obj = repo.get(entry.id)
        files.append({
            "name": entry.name,
            "type": "dir" if obj.type == pygit2.GIT_OBJECT_TREE else "file",
            "size": len(obj.data) if obj.type == pygit2.GIT_OBJECT_BLOB else None,
            "oid": str(entry.id),
        })

    return files


def get_file_content(repo_path: str, file_path: str, branch: str = "main") -> bytes | None:
    """Get the content of a file from a branch."""
    repo = open_repo(repo_path)
    ref_name = f"refs/heads/{branch}"

    if ref_name not in repo.references:
        return None

    ref = repo.references[ref_name]
    commit = repo.get(ref.target)
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


def get_file_content_at_commit(repo_path: str, file_path: str, commit_hash: str) -> bytes | None:
    """Get the content of a file at a specific commit."""
    repo = open_repo(repo_path)
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


def list_branches(repo_path: str) -> list[dict]:
    """List all branches in a repository."""
    repo = open_repo(repo_path)
    branches = []
    for ref_name in repo.references:
        if ref_name.startswith("refs/heads/"):
            branch_name = ref_name[len("refs/heads/"):]
            ref = repo.references[ref_name]
            commit = repo.get(ref.target)
            branches.append({
                "name": branch_name,
                "commit": str(commit.id),
                "message": commit.message.strip(),
                "timestamp": commit.commit_time,
            })
    return branches


def create_branch(repo_path: str, branch_name: str, source_branch: str = "main") -> dict | None:
    """Create a new branch from an existing one."""
    repo = open_repo(repo_path)
    ref_name = f"refs/heads/{source_branch}"

    if ref_name not in repo.references:
        return None

    ref = repo.references[ref_name]
    commit = repo.get(ref.target)

    new_ref = f"refs/heads/{branch_name}"
    repo.references.create(new_ref, commit.id)

    return {
        "name": branch_name,
        "commit": str(commit.id),
        "source": source_branch,
    }
