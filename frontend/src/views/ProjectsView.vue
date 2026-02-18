<template>
  <div class="projects-page">
    <div class="projects-topbar">
      <div class="topbar-left">
        <h2 class="page-title">Projects</h2>
        <span class="project-count" v-if="store.projects.length">{{ store.projects.length }} projects</span>
      </div>
      <div class="topbar-right">
        <div class="search-box">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <circle cx="7" cy="7" r="5.5" stroke="currentColor" stroke-width="1.4"/>
            <path d="M11 11l3.5 3.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
          </svg>
          <input type="text" v-model="search" placeholder="Search projects..." />
        </div>
        <button class="btn btn-warm" @click="showCreate = true">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 2v10M2 7h10" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
          </svg>
          New Project
        </button>
      </div>
    </div>

    <div v-if="store.loading" class="state-msg">
      <div class="state-spinner"></div>
      <span>Loading projects...</span>
    </div>

    <div v-else-if="filteredProjects.length === 0 && !search" class="empty-state">
      <div class="empty-icon">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
          <rect x="8" y="8" width="32" height="32" rx="6" stroke="currentColor" stroke-width="1.5" opacity="0.3"/>
          <path d="M20 24h8M24 20v8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" opacity="0.5"/>
        </svg>
      </div>
      <h3>No projects yet</h3>
      <p>Create your first project to start managing BIM models with version control.</p>
      <button class="btn btn-warm" @click="showCreate = true">Create first project</button>
    </div>

    <div v-else class="projects-grid">
      <div
        v-for="project in filteredProjects"
        :key="project.id"
        class="project-card"
        @click="$router.push(`/projects/${project.slug}`)"
      >
        <div class="card-header">
          <div class="card-icon">
            <svg width="20" height="20" viewBox="0 0 40 40" fill="none">
              <path d="M20 4L4 12v16l16 8 16-8V12L20 4z" stroke="currentColor" stroke-width="2" fill="none"/>
            </svg>
          </div>
          <div class="card-badges">
            <span class="badge badge-vault" title="Version control active">Vault</span>
            <span class="badge badge-view" title="3D viewer">View</span>
          </div>
        </div>
        <h3 class="card-title">{{ project.name }}</h3>
        <p v-if="project.description" class="card-desc">{{ project.description }}</p>
        <div class="card-footer">
          <span class="card-slug">{{ project.slug }}</span>
          <span class="card-date">{{ formatDate(project.created_at) }}</span>
        </div>
        <div class="card-modules">
          <span class="module-dot" style="background: #4A90B8" title="Vault"></span>
          <span class="module-dot" style="background: #6BB8D4" title="View"></span>
          <span class="module-dot" style="background: #5AAD58" title="Docs"></span>
        </div>
      </div>
    </div>

    <!-- Create Project Dialog -->
    <Transition name="modal">
      <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
        <div class="modal">
          <div class="modal-header">
            <h3>New Project</h3>
            <button class="modal-close" @click="showCreate = false">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
            </button>
          </div>
          <form @submit.prevent="handleCreate">
            <div class="form-group">
              <label>Project Name</label>
              <input v-model="newName" type="text" required placeholder="e.g. Campus Building A" />
            </div>
            <div class="form-group">
              <label>Description</label>
              <textarea v-model="newDesc" rows="3" placeholder="Brief project description..."></textarea>
            </div>

            <div class="form-group">
              <label>Activate Modules</label>
              <div class="module-toggles">
                <label class="module-toggle" v-for="mod in availableModules" :key="mod.id">
                  <input type="checkbox" v-model="mod.active" />
                  <span class="toggle-chip" :style="{ '--mod-color': mod.color }">
                    <span class="toggle-icon">{{ mod.icon }}</span>
                    {{ mod.name }}
                  </span>
                </label>
              </div>
            </div>

            <div class="form-group">
              <label>Backend Engine</label>
              <div class="engine-options">
                <label class="engine-option" :class="{ selected: engine === 'git' }">
                  <input type="radio" v-model="engine" value="git" />
                  <div class="engine-info">
                    <strong>IFC-Git + STEP</strong>
                    <span>IFC4x3 with Git version control. Best for standard projects.</span>
                  </div>
                </label>
                <label class="engine-option" :class="{ selected: engine === 'graph' }">
                  <input type="radio" v-model="engine" value="graph" />
                  <div class="engine-info">
                    <strong>IFC-Git + Neo4J Graph</strong>
                    <span>Graph database backend. Handles 40GB+ models with linked data.</span>
                  </div>
                </label>
              </div>
            </div>

            <div v-if="createError" class="form-error">{{ createError }}</div>
            <div class="modal-actions">
              <button type="button" class="btn-sm" @click="showCreate = false" :disabled="creating">Cancel</button>
              <button type="submit" class="btn btn-warm" :disabled="creating || !newName.trim()">
                <span v-if="creating" class="btn-spinner"></span>
                {{ creating ? 'Creating...' : 'Create Project' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from "vue";
import { useRouter } from "vue-router";
import { useProjectStore } from "@/stores/project";

const router = useRouter();
const store = useProjectStore();
const showCreate = ref(false);
const newName = ref("");
const newDesc = ref("");
const search = ref("");
const engine = ref("git");
const creating = ref(false);
const createError = ref("");

const availableModules = reactive([
  { id: "vault", name: "Vault", icon: "\u{1F512}", color: "#4A90B8", active: true },
  { id: "view", name: "View", icon: "\u{1F441}", color: "#6BB8D4", active: true },
  { id: "docs", name: "Docs", icon: "\u{1F4C4}", color: "#5AAD58", active: true },
  { id: "clash", name: "Clash", icon: "\u{26A1}", color: "#E07B3C", active: false },
  { id: "issues", name: "Issues", icon: "\u{1F4CB}", color: "#C45A20", active: false },
  { id: "takeoff", name: "Takeoff", icon: "\u{1F4D0}", color: "#8B5CF6", active: false },
  { id: "facility", name: "Facility", icon: "\u{1F3E2}", color: "#06B6D4", active: false },
  { id: "graph", name: "Graph", icon: "\u{1F578}", color: "#EC4899", active: false },
]);

const filteredProjects = computed(() => {
  if (!search.value) return store.projects;
  const q = search.value.toLowerCase();
  return store.projects.filter(
    (p: any) => p.name.toLowerCase().includes(q) || p.slug.toLowerCase().includes(q)
  );
});

onMounted(() => {
  store.fetchProjects();
});

async function handleCreate() {
  if (!newName.value.trim()) return;
  creating.value = true;
  createError.value = "";
  try {
    const activeModules = availableModules
      .filter((m) => m.active)
      .map((m) => m.id);
    const project = await store.createProject(
      newName.value.trim(),
      newDesc.value.trim() || undefined,
      engine.value,
      activeModules,
    );
    showCreate.value = false;
    newName.value = "";
    newDesc.value = "";
    engine.value = "git";
    availableModules.forEach((m) => {
      m.active = ["vault", "view", "docs"].includes(m.id);
    });
    if (project?.slug) {
      router.push(`/projects/${project.slug}`);
    }
  } catch (err: any) {
    createError.value =
      err.response?.data?.detail || err.message || "Failed to create project";
  } finally {
    creating.value = false;
  }
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("nl-NL", { day: "numeric", month: "short", year: "numeric" });
}
</script>

<style scoped>
.projects-page {
  padding: 24px 32px;
  max-width: 1200px;
  margin: 0 auto;
  height: 100%;
  overflow-y: auto;
}

/* ── Top bar ── */
.projects-topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  gap: 16px;
}

.topbar-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
}

.project-count {
  font-size: 12px;
  color: var(--text-secondary);
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 10px;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  transition: border-color 0.15s;
}

.search-box:focus-within {
  border-color: var(--accent);
}

.search-box input {
  border: none;
  background: none;
  padding: 0;
  font-size: 13px;
  width: 180px;
  box-shadow: none;
}

.search-box input:focus {
  outline: none;
  box-shadow: none;
}

.btn svg {
  vertical-align: -2px;
  margin-right: 6px;
}

/* ── Grid ── */
.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 14px;
}

.project-card {
  padding: 20px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: border-color 0.15s, transform 0.15s, box-shadow 0.2s;
}

.project-card:hover {
  border-color: var(--border-hover);
  transform: translateY(-1px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.card-icon {
  color: var(--accent);
  opacity: 0.6;
}

.card-badges {
  display: flex;
  gap: 4px;
}

.badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.badge-vault {
  background: rgba(74, 144, 184, 0.12);
  color: #4A90B8;
}

.badge-view {
  background: rgba(107, 184, 212, 0.12);
  color: #6BB8D4;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 6px;
}

.card-desc {
  color: var(--text-secondary);
  font-size: 13px;
  margin-bottom: 12px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text-secondary);
  opacity: 0.7;
  margin-bottom: 10px;
}

.card-slug {
  font-family: 'SF Mono', 'Fira Code', monospace;
}

.card-modules {
  display: flex;
  gap: 4px;
}

.module-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  opacity: 0.7;
}

/* ── Empty / Loading ── */
.state-msg {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 60px;
  color: var(--text-secondary);
  font-size: 14px;
}

.state-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--text-secondary);
}

.empty-icon {
  margin-bottom: 16px;
  color: var(--text-secondary);
}

.empty-state h3 {
  color: var(--text-primary);
  font-size: 18px;
  margin-bottom: 8px;
}

.empty-state p {
  font-size: 14px;
  max-width: 400px;
  margin: 0 auto 20px;
  line-height: 1.6;
}

/* ── Modal ── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px;
  width: 520px;
  max-height: 85vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.modal-header h3 {
  font-size: 16px;
  font-weight: 600;
}

.modal-close {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-secondary);
  padding: 4px;
  border-radius: 4px;
  transition: color 0.15s;
}

.modal-close:hover { color: var(--text-primary); }

.modal-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

/* ── Module toggles ── */
.module-toggles {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.module-toggle {
  cursor: pointer;
  margin: 0;
}

.module-toggle input {
  display: none;
}

.toggle-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  background: transparent;
  transition: all 0.15s;
}

.toggle-icon {
  font-size: 14px;
}

.module-toggle input:checked + .toggle-chip {
  border-color: var(--mod-color);
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-primary);
}

/* ── Engine options ── */
.engine-options {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.engine-option {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.15s;
  margin: 0;
}

.engine-option:hover {
  border-color: var(--border-hover);
}

.engine-option.selected {
  border-color: var(--accent);
  background: rgba(74, 144, 184, 0.06);
}

.engine-option input {
  width: auto;
  margin-top: 2px;
}

.engine-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.engine-info strong {
  font-size: 13px;
  font-weight: 600;
}

.engine-info span {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.4;
}

/* ── Form error ── */
.form-error {
  margin-top: 12px;
  padding: 8px 12px;
  background: rgba(220, 38, 38, 0.1);
  border: 1px solid rgba(220, 38, 38, 0.3);
  border-radius: var(--radius-sm);
  color: #f87171;
  font-size: 13px;
}

.btn-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  margin-right: 6px;
  vertical-align: -2px;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* ── Modal transition ── */
.modal-enter-active { transition: all 0.2s ease; }
.modal-leave-active { transition: all 0.15s ease; }
.modal-enter-from, .modal-leave-to {
  opacity: 0;
}
.modal-enter-from .modal, .modal-leave-to .modal {
  transform: scale(0.95) translateY(10px);
}
</style>
