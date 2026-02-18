import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json",
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 responses
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      window.location.href = "/app/login";
    }
    return Promise.reject(error);
  }
);

export default api;

// --- Auth ---
export const authApi = {
  register(data: { username: string; email: string; password: string }) {
    return api.post("/auth/register", data);
  },
  login(data: { username: string; password: string }) {
    return api.post("/auth/login", data);
  },
  me() {
    return api.get("/auth/me");
  },
  createToken(data: { name: string; expires_days?: number }) {
    return api.post("/auth/tokens", data);
  },
  listTokens() {
    return api.get("/auth/tokens");
  },
  deleteToken(id: string) {
    return api.delete(`/auth/tokens/${id}`);
  },
};

// --- Settings ---
export const settingsApi = {
  get() {
    return api.get("/auth/settings");
  },
  update(data: {
    erpnext_url?: string | null;
    erpnext_api_key?: string | null;
    erpnext_api_secret?: string | null;
    nextcloud_url?: string | null;
    nextcloud_username?: string | null;
    nextcloud_password?: string | null;
  }) {
    return api.put("/auth/settings", data);
  },
  testErpnext() {
    return api.post("/auth/settings/erpnext/test");
  },
  testNextcloud() {
    return api.post("/auth/settings/nextcloud/test");
  },
};

// --- Projects ---
export const projectsApi = {
  list() {
    return api.get("/projects");
  },
  create(data: { name: string; description?: string }) {
    return api.post("/projects", data);
  },
  get(slug: string) {
    return api.get(`/projects/${slug}`);
  },
  update(slug: string, data: { name?: string; description?: string }) {
    return api.put(`/projects/${slug}`, data);
  },
  delete(slug: string) {
    return api.delete(`/projects/${slug}`);
  },
};

// --- Files & Git ---
export const filesApi = {
  list(slug: string, branch = "main", path = "") {
    return api.get(`/projects/${slug}/files`, { params: { branch, path } });
  },
  upload(slug: string, file: File, branch = "main", message = "") {
    const formData = new FormData();
    formData.append("file", file);
    return api.post(`/projects/${slug}/files`, formData, {
      params: { branch, message },
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  download(slug: string, filePath: string, branch = "main") {
    return api.get(`/projects/${slug}/files/${filePath}`, {
      params: { branch },
      responseType: "blob",
    });
  },
};

export const gitApi = {
  log(slug: string, branch = "main", limit = 50) {
    return api.get(`/projects/${slug}/git/log`, { params: { branch, limit } });
  },
  branches(slug: string) {
    return api.get(`/projects/${slug}/git/branches`);
  },
  createBranch(slug: string, data: { name: string; source?: string }) {
    return api.post(`/projects/${slug}/git/branches`, data);
  },
};

// --- Graph ---
export const graphApi = {
  getData(slug: string, params?: { ifc_class?: string; depth?: number; limit?: number }) {
    return api.get(`/projects/${slug}/graph/data`, { params });
  },
  getStats(slug: string) {
    return api.get(`/projects/${slug}/graph/stats`);
  },
  getNode(slug: string, globalId: string, depth = 1) {
    return api.get(`/projects/${slug}/graph/node/${globalId}`, { params: { depth } });
  },
  search(slug: string, q: string, limit = 50) {
    return api.get(`/projects/${slug}/graph/search`, { params: { q, limit } });
  },
  importIfc(slug: string, filePath: string, background = true) {
    return api.post(`/projects/${slug}/graph/import`, null, {
      params: { file_path: filePath, background },
    });
  },
  getImportStatus(slug: string, jobId: string) {
    return api.get(`/projects/${slug}/graph/import/${jobId}`);
  },
};

// --- Fragments ---
export const fragmentsApi = {
  getFragmentUrl(slug: string, filePath: string, commit?: string) {
    const params = commit ? `?commit=${commit}` : "";
    return `/api/projects/${slug}/fragments/${filePath}${params}`;
  },
  getPropertiesUrl(slug: string, filePath: string, commit?: string) {
    const params = commit ? `?commit=${commit}` : "";
    return `/api/projects/${slug}/fragments/${filePath}/properties${params}`;
  },
  getSpatialUrl(slug: string, filePath: string, commit?: string) {
    const params = commit ? `?commit=${commit}` : "";
    return `/api/projects/${slug}/fragments/${filePath}/spatial${params}`;
  },
  getProperties(slug: string, filePath: string, commit?: string) {
    return api.get(`/projects/${slug}/fragments/${filePath}/properties`, {
      params: { commit },
    });
  },
  getSpatialTree(slug: string, filePath: string, commit?: string) {
    return api.get(`/projects/${slug}/fragments/${filePath}/spatial`, {
      params: { commit },
    });
  },
};
