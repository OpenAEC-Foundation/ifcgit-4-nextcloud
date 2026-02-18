<template>
  <div class="project-view">
    <!-- Left Sidebar: Files & Spatial Tree -->
    <aside class="sidebar left-sidebar">
      <div class="sidebar-section">
        <div class="section-header">
          <h4>Files</h4>
          <div style="display: flex; gap: 6px; align-items: center;">
            <router-link :to="`/app/projects/${slug}/graph`" class="btn-sm" title="Graph Explorer">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="5" cy="12" r="2"/><circle cx="19" cy="6" r="2"/><circle cx="19" cy="18" r="2"/>
                <path d="M7 11l10-4M7 13l10 4"/>
              </svg>
            </router-link>
            <FileUpload :slug="slug" @uploaded="onFileUploaded" />
          </div>
        </div>
        <div class="file-list">
          <div
            v-for="f in store.files"
            :key="f.name"
            class="file-item"
            :class="{ active: viewerStore.activeFile === f.name }"
            @click="f.type === 'file' && openFile(f.name)"
          >
            <span class="file-icon">{{ f.type === "dir" ? "📁" : "📄" }}</span>
            <span class="file-name">{{ f.name }}</span>
            <span v-if="f.size" class="file-size">{{ formatSize(f.size) }}</span>
          </div>
          <div v-if="store.files.length === 0" class="empty-hint">
            Upload an IFC file to get started
          </div>
        </div>
      </div>

      <div class="sidebar-section" v-if="viewerStore.spatialTree">
        <h4>Spatial Tree</h4>
        <SpatialTree
          :node="viewerStore.spatialTree"
          @select="onTreeSelect"
        />
      </div>
    </aside>

    <!-- Center: 3D Viewer -->
    <div class="viewer-container">
      <IfcViewer ref="viewerRef" />
      <ViewerToolbar />
    </div>

    <!-- Right Sidebar: Properties & Git History -->
    <aside class="sidebar right-sidebar">
      <div class="sidebar-section" v-if="viewerStore.selectedProperties">
        <h4>Properties</h4>
        <PropertiesPanel :properties="viewerStore.selectedProperties" />
      </div>

      <div class="sidebar-section">
        <h4>Git History</h4>
        <GitHistory :commits="store.commits" />
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useProjectStore } from "@/stores/project";
import { useViewerStore } from "@/stores/viewer";
import IfcViewer from "@/components/viewer/IfcViewer.vue";
import ViewerToolbar from "@/components/viewer/ViewerToolbar.vue";
import SpatialTree from "@/components/viewer/SpatialTree.vue";
import PropertiesPanel from "@/components/viewer/PropertiesPanel.vue";
import FileUpload from "@/components/common/FileUpload.vue";
import GitHistory from "@/components/git/GitHistory.vue";

const route = useRoute();
const router = useRouter();
const store = useProjectStore();
const viewerStore = useViewerStore();

const slug = computed(() => route.params.slug as string);
const viewerRef = ref<InstanceType<typeof IfcViewer> | null>(null);

onMounted(async () => {
  await store.fetchProject(slug.value);
});

async function openFile(fileName: string) {
  if (!fileName.toLowerCase().endsWith(".ifc")) return;
  viewerStore.activeFile = fileName;
  viewerRef.value?.loadModel(slug.value, fileName);
}

function onFileUploaded() {
  store.fetchFiles(slug.value);
  store.fetchCommits(slug.value);
}

function onTreeSelect(expressID: number) {
  viewerStore.selectElement(expressID);
  viewerRef.value?.highlightElement(expressID);
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
</script>

<style scoped>
.project-view {
  display: flex;
  height: 100%;
}

.sidebar {
  width: var(--sidebar-width);
  background: var(--bg-secondary);
  border-right: 1px solid var(--border);
  overflow-y: auto;
  flex-shrink: 0;
}

.right-sidebar {
  border-right: none;
  border-left: 1px solid var(--border);
}

.sidebar-section {
  padding: 12px;
  border-bottom: 1px solid var(--border);
}
.sidebar-section h4 {
  font-size: 12px;
  text-transform: uppercase;
  color: var(--text-secondary);
  margin-bottom: 8px;
  letter-spacing: 0.5px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}
.file-item:hover {
  background: var(--bg-surface);
}
.file-item.active {
  background: var(--bg-surface);
  border-left: 2px solid var(--accent);
}

.file-icon { font-size: 14px; }
.file-name { flex: 1; }
.file-size {
  font-size: 11px;
  color: var(--text-secondary);
}

.empty-hint {
  font-size: 12px;
  color: var(--text-secondary);
  text-align: center;
  padding: 20px 0;
}

.viewer-container {
  flex: 1;
  position: relative;
  overflow: hidden;
}
</style>
