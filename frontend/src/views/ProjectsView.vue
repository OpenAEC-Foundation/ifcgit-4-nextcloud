<template>
  <div class="projects-page">
    <div class="projects-header">
      <h2>Projects</h2>
      <button class="btn" @click="showCreate = true">New Project</button>
    </div>

    <div v-if="store.loading" class="loading">Loading projects...</div>

    <div v-else-if="store.projects.length === 0" class="empty-state">
      <p>No projects yet. Create your first project to get started.</p>
    </div>

    <div v-else class="projects-grid">
      <div
        v-for="project in store.projects"
        :key="project.id"
        class="project-card"
        @click="$router.push(`/projects/${project.slug}`)"
      >
        <h3>{{ project.name }}</h3>
        <p v-if="project.description" class="project-desc">{{ project.description }}</p>
        <div class="project-meta">
          <span>{{ project.slug }}</span>
          <span>{{ formatDate(project.created_at) }}</span>
        </div>
      </div>
    </div>

    <!-- Create Project Dialog -->
    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
      <div class="modal">
        <h3>New Project</h3>
        <form @submit.prevent="handleCreate">
          <div class="form-group">
            <label>Project Name</label>
            <input v-model="newName" type="text" required placeholder="My BIM Project" />
          </div>
          <div class="form-group">
            <label>Description (optional)</label>
            <textarea v-model="newDesc" rows="3" placeholder="Project description..."></textarea>
          </div>
          <div style="display: flex; gap: 8px; justify-content: flex-end">
            <button type="button" class="btn-sm" @click="showCreate = false">Cancel</button>
            <button type="submit" class="btn">Create</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useProjectStore } from "@/stores/project";

const store = useProjectStore();
const showCreate = ref(false);
const newName = ref("");
const newDesc = ref("");

onMounted(() => {
  store.fetchProjects();
});

async function handleCreate() {
  await store.createProject(newName.value, newDesc.value || undefined);
  showCreate.value = false;
  newName.value = "";
  newDesc.value = "";
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString();
}
</script>

<style scoped>
.projects-page {
  padding: 24px;
  max-width: 1000px;
  margin: 0 auto;
  height: 100%;
  overflow-y: auto;
}

.projects-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.project-card {
  padding: 20px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.15s;
}
.project-card:hover {
  border-color: var(--accent);
}
.project-card h3 {
  margin-bottom: 8px;
}

.project-desc {
  color: var(--text-secondary);
  font-size: 13px;
  margin-bottom: 12px;
}

.project-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-secondary);
}

.empty-state, .loading {
  text-align: center;
  padding: 60px;
  color: var(--text-secondary);
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 24px;
  width: 420px;
}
.modal h3 {
  margin-bottom: 16px;
}
</style>
