"""
WebDAV handler for IfcGit Server.

Provides WebDAV access to project files, backed by Git repositories.
External tools (Revit, Bonsai, FreeCAD) can open/save IFC files via WebDAV.

Mount point: /dav/projects/{slug}/files/
"""

import hashlib
import logging
import os
import tempfile
from io import BytesIO

from wsgidav.dav_provider import DAVProvider, DAVCollection, DAVNonCollection
from wsgidav.wsgidav_app import WsgiDAVApp

from src.config import settings

logger = logging.getLogger(__name__)


class IfcGitFile(DAVNonCollection):
    """A file in an IfcGit project repository."""

    def __init__(self, path, environ, file_data, file_name):
        super().__init__(path, environ)
        self._file_data = file_data
        self._file_name = file_name

    def get_content_length(self):
        return len(self._file_data) if self._file_data else 0

    def get_content_type(self):
        if self._file_name.lower().endswith(".ifc"):
            return "application/x-step"
        return "application/octet-stream"

    def get_content(self):
        return BytesIO(self._file_data) if self._file_data else BytesIO(b"")

    def get_display_name(self):
        return self._file_name

    def support_etag(self):
        return True

    def get_etag(self):
        if self._file_data:
            return hashlib.md5(self._file_data).hexdigest()
        return None


class ProjectFilesCollection(DAVCollection):
    """Collection representing files in a project's Git repository."""

    def __init__(self, path, environ, project_slug, repo_path):
        super().__init__(path, environ)
        self._project_slug = project_slug
        self._repo_path = repo_path

    def get_display_name(self):
        return self._project_slug

    def get_member_names(self):
        from src.git.service import list_files
        try:
            files = list_files(self._repo_path, branch="main")
            return [f["name"] for f in files]
        except Exception:
            return []

    def get_member(self, name):
        from src.git.service import get_file_content, list_files

        # Check if it's a file
        content = get_file_content(self._repo_path, name, branch="main")
        if content is not None:
            return IfcGitFile(
                f"{self.path}/{name}",
                self.environ,
                content,
                name,
            )
        return None

    def handle_delete(self):
        return False

    def handle_copy(self, dest_path, depth_infinity):
        return False

    def handle_move(self, dest_path):
        return False

    def create_empty_resource(self, name):
        return None

    def create_collection(self, name):
        return False


class RootCollection(DAVCollection):
    """Root collection listing all projects."""

    def __init__(self, path, environ):
        super().__init__(path, environ)

    def get_display_name(self):
        return "IfcGit Projects"

    def get_member_names(self):
        repos_dir = settings.repos_dir
        if not os.path.exists(repos_dir):
            return []
        return [
            d.replace(".git", "")
            for d in os.listdir(repos_dir)
            if d.endswith(".git") and os.path.isdir(os.path.join(repos_dir, d))
        ]

    def get_member(self, name):
        repo_path = os.path.join(settings.repos_dir, f"{name}.git")
        if os.path.exists(repo_path):
            return ProjectFilesCollection(
                f"{self.path}/{name}",
                self.environ,
                name,
                repo_path,
            )
        return None


class IfcGitDAVProvider(DAVProvider):
    """WebDAV provider backed by IfcGit Git repositories."""

    def get_resource_inst(self, path, environ):
        path = path.rstrip("/")

        if not path or path == "/":
            return RootCollection("/", environ)

        parts = path.strip("/").split("/")

        if len(parts) == 1:
            # Project level
            slug = parts[0]
            repo_path = os.path.join(settings.repos_dir, f"{slug}.git")
            if os.path.exists(repo_path):
                return ProjectFilesCollection(path, environ, slug, repo_path)
            return None

        if len(parts) == 2:
            # File level
            slug = parts[0]
            filename = parts[1]
            repo_path = os.path.join(settings.repos_dir, f"{slug}.git")
            if os.path.exists(repo_path):
                from src.git.service import get_file_content
                content = get_file_content(repo_path, filename, branch="main")
                if content is not None:
                    return IfcGitFile(path, environ, content, filename)

        return None


def create_webdav_app() -> WsgiDAVApp:
    """Create a WsgiDAV application configured for IfcGit."""
    config = {
        "provider_mapping": {"/": IfcGitDAVProvider()},
        "simple_dc": {"user_mapping": {"*": True}},  # Auth handled by API gateway
        "verbose": 1,
        "logging": {
            "enable": True,
            "enable_loggers": [],
        },
        "property_manager": True,
        "lock_storage": True,
    }
    return WsgiDAVApp(config)
