import { defineStore } from "pinia";
import { ref } from "vue";
import { projectsApi, filesApi, gitApi } from "@/services/api";

interface Project {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  engine: string;
  modules: string[] | null;
  owner_id: string;
  created_at: string;
}

interface FileEntry {
  name: string;
  type: "file" | "dir";
  size: number | null;
  oid: string;
}

interface Commit {
  hash: string;
  message: string;
  author_name: string;
  author_email: string;
  timestamp: number;
}

export const useProjectStore = defineStore("project", () => {
  const projects = ref<Project[]>([]);
  const currentProject = ref<Project | null>(null);
  const files = ref<FileEntry[]>([]);
  const commits = ref<Commit[]>([]);
  const currentBranch = ref("main");
  const branches = ref<{ name: string; commit: string }[]>([]);
  const loading = ref(false);

  async function fetchProjects() {
    loading.value = true;
    try {
      const res = await projectsApi.list();
      projects.value = res.data;
    } finally {
      loading.value = false;
    }
  }

  async function fetchProject(slug: string) {
    loading.value = true;
    try {
      const res = await projectsApi.get(slug);
      currentProject.value = res.data;
      await Promise.all([fetchFiles(slug), fetchCommits(slug), fetchBranches(slug)]);
    } finally {
      loading.value = false;
    }
  }

  async function createProject(name: string, description?: string, engine?: string, modules?: string[]) {
    const res = await projectsApi.create({ name, description, engine, modules });
    await fetchProjects();
    return res.data;
  }

  async function fetchFiles(slug: string) {
    const res = await filesApi.list(slug, currentBranch.value);
    files.value = res.data.files;
  }

  async function fetchCommits(slug: string) {
    try {
      const res = await gitApi.log(slug, currentBranch.value);
      commits.value = res.data;
    } catch {
      commits.value = [];
    }
  }

  async function fetchBranches(slug: string) {
    try {
      const res = await gitApi.branches(slug);
      branches.value = res.data.branches;
    } catch {
      branches.value = [];
    }
  }

  async function uploadFile(slug: string, file: File, message?: string) {
    await filesApi.upload(slug, file, currentBranch.value, message);
    await Promise.all([fetchFiles(slug), fetchCommits(slug)]);
  }

  return {
    projects,
    currentProject,
    files,
    commits,
    currentBranch,
    branches,
    loading,
    fetchProjects,
    fetchProject,
    createProject,
    fetchFiles,
    fetchCommits,
    fetchBranches,
    uploadFile,
  };
});
