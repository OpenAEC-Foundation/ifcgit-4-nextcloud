<template>
  <div class="graph-page">
    <!-- Toolbar -->
    <div class="graph-toolbar">
      <div class="toolbar-left">
        <router-link :to="`/app/projects/${slug}`" class="btn-sm">
          &larr; Back to Project
        </router-link>
        <h2 class="toolbar-title">IFC Graph Explorer</h2>
        <span class="toolbar-badge" v-if="stats">
          {{ stats.node_count }} nodes &middot; {{ stats.relationship_count }} edges
        </span>
      </div>
      <div class="toolbar-right">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search entities..."
          class="search-input"
          @keyup.enter="doSearch"
        />
        <select v-model="filterClass" @change="loadGraph" class="filter-select">
          <option value="">All classes</option>
          <option v-for="cls in classOptions" :key="cls.ifc_class" :value="cls.ifc_class">
            {{ cls.ifc_class }} ({{ cls.count }})
          </option>
        </select>
        <select v-model="depth" @change="loadGraph" class="filter-select">
          <option :value="1">Depth 1</option>
          <option :value="2">Depth 2</option>
          <option :value="3">Depth 3</option>
        </select>
        <button class="btn" @click="showImportModal = true" :disabled="importing">
          {{ importing ? 'Importing...' : 'Import IFC' }}
        </button>
      </div>
    </div>

    <!-- Import progress banner -->
    <div v-if="importJob" class="import-progress-bar">
      <div class="import-progress-info">
        <span class="import-phase">{{ importJob.phase_label || importJob.status }}</span>
        <span class="import-pct">{{ importJob.progress || 0 }}%</span>
      </div>
      <div class="import-bar-track">
        <div class="import-bar-fill" :style="{ width: (importJob.progress || 0) + '%' }"></div>
      </div>
      <div v-if="importJob.status === 'completed'" class="import-done">
        {{ importJob.nodes_created }} nodes, {{ importJob.relationships_created }} rels
        in {{ importJob.total_time_s }}s
        <button class="btn-sm" @click="onImportDone" style="margin-left: 8px;">Load Graph</button>
      </div>
      <div v-if="importJob.status === 'failed'" class="import-error">
        Failed: {{ importJob.error }}
      </div>
    </div>

    <!-- Import modal -->
    <div v-if="showImportModal" class="modal-overlay" @click.self="showImportModal = false">
      <div class="modal-box">
        <h3>Import IFC to Graph</h3>
        <div class="form-group">
          <label>IFC file path (relative to project repo)</label>
          <input v-model="importFilePath" type="text" placeholder="e.g. model.ifc" />
        </div>
        <div style="display: flex; gap: 8px; justify-content: flex-end;">
          <button class="btn-sm" @click="showImportModal = false">Cancel</button>
          <button class="btn" @click="startImport" :disabled="!importFilePath.trim()">Start Import</button>
        </div>
      </div>
    </div>

    <!-- Main content -->
    <div class="graph-content">
      <!-- Graph Canvas -->
      <div class="graph-canvas-container" ref="canvasContainer">
        <canvas
          ref="canvas"
          @mousedown="onMouseDown"
          @mousemove="onMouseMove"
          @mouseup="onMouseUp"
          @wheel="onWheel"
          @dblclick="onDblClick"
        ></canvas>

        <!-- Loading overlay -->
        <div v-if="loading" class="graph-loading">
          <div class="loading-spinner"></div>
          <span>Loading graph...</span>
        </div>

        <!-- Empty state -->
        <div v-if="!loading && nodes.length === 0" class="graph-empty">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" stroke-width="1.5">
            <circle cx="5" cy="12" r="2"/><circle cx="19" cy="6" r="2"/><circle cx="19" cy="18" r="2"/>
            <path d="M7 12h8m0 0l-2-4m2 4l-2 4"/>
          </svg>
          <p>No graph data yet.</p>
          <p class="graph-empty-sub">Import an IFC file to visualize its structure as a graph.</p>
        </div>
      </div>

      <!-- Side panel -->
      <div class="graph-sidebar" :class="{ open: selectedNode }">
        <div v-if="selectedNode" class="sidebar-content">
          <div class="sidebar-header">
            <h3>{{ selectedNode.name || selectedNode.ifc_class }}</h3>
            <button class="btn-sm" @click="selectedNode = null">&times;</button>
          </div>
          <div class="sidebar-props">
            <div class="prop-row">
              <span class="prop-label">IFC Class</span>
              <span class="prop-value class-badge" :style="{ background: groupColors[selectedNode.group] || '#666' }">
                {{ selectedNode.ifc_class }}
              </span>
            </div>
            <div class="prop-row">
              <span class="prop-label">Global ID</span>
              <span class="prop-value mono">{{ selectedNode.id }}</span>
            </div>
            <div class="prop-row">
              <span class="prop-label">Group</span>
              <span class="prop-value">{{ selectedNode.group }}</span>
            </div>
          </div>
          <button class="btn" @click="expandNode(selectedNode.id)" style="margin-top: 12px; width: 100%;">
            Expand neighbors
          </button>

          <!-- Connected edges -->
          <div v-if="connectedEdges.length" class="sidebar-edges">
            <h4>Connections ({{ connectedEdges.length }})</h4>
            <div v-for="edge in connectedEdges" :key="edge.source + edge.target + edge.type" class="edge-item">
              <span class="edge-type">{{ edge.type }}</span>
              <span class="edge-target" @click="focusNode(edge.source === selectedNode.id ? edge.target : edge.source)">
                {{ getNodeLabel(edge.source === selectedNode.id ? edge.target : edge.source) }}
              </span>
            </div>
          </div>
        </div>

        <!-- Search results -->
        <div v-if="searchResults.length && !selectedNode" class="sidebar-content">
          <div class="sidebar-header">
            <h3>Search Results ({{ searchResults.length }})</h3>
            <button class="btn-sm" @click="searchResults = []">&times;</button>
          </div>
          <div v-for="result in searchResults" :key="result.id" class="search-result" @click="focusNode(result.id)">
            <span class="result-class">{{ result.ifc_class }}</span>
            <span class="result-name">{{ result.name || result.id }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Legend -->
    <div class="graph-legend">
      <div v-for="(color, group) in groupColors" :key="group" class="legend-item">
        <span class="legend-dot" :style="{ background: color }"></span>
        <span>{{ group }}</span>
      </div>
    </div>

    <!-- Stats panel -->
    <div v-if="stats && stats.class_distribution.length" class="stats-panel">
      <h4>Class Distribution</h4>
      <div class="stats-bars">
        <div v-for="cls in stats.class_distribution.slice(0, 10)" :key="cls.ifc_class" class="stat-bar-row">
          <span class="stat-label">{{ cls.ifc_class }}</span>
          <div class="stat-bar">
            <div class="stat-fill" :style="{ width: (cls.count / maxClassCount * 100) + '%' }"></div>
          </div>
          <span class="stat-count">{{ cls.count }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from "vue";
import { useRoute } from "vue-router";
import { graphApi } from "@/services/api";

const route = useRoute();
const slug = computed(() => route.params.slug as string);

// State
const loading = ref(false);
const nodes = ref<any[]>([]);
const edges = ref<any[]>([]);
const stats = ref<any>(null);
const selectedNode = ref<any>(null);
const searchQuery = ref("");
const searchResults = ref<any[]>([]);
const filterClass = ref("");
const depth = ref(2);

// Import state
const showImportModal = ref(false);
const importFilePath = ref("");
const importing = ref(false);
const importJob = ref<any>(null);
let pollTimer: ReturnType<typeof setInterval> | null = null;

// Canvas refs
const canvas = ref<HTMLCanvasElement | null>(null);
const canvasContainer = ref<HTMLDivElement | null>(null);

// Simulation state
interface SimNode {
  id: string;
  label: string;
  ifc_class: string;
  name: string;
  group: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  fx?: number | null;
  fy?: number | null;
}

let simNodes: SimNode[] = [];
let simEdges: { source: string; target: string; type: string }[] = [];
let animFrame = 0;
let camera = { x: 0, y: 0, zoom: 1 };
let dragging: SimNode | null = null;
let panning = false;
let panStart = { x: 0, y: 0 };
let hovered: SimNode | null = null;

const groupColors: Record<string, string> = {
  site: "#4CAF50",
  building: "#2196F3",
  storey: "#03A9F4",
  space: "#00BCD4",
  wall: "#FF9800",
  slab: "#795548",
  structural: "#F44336",
  opening: "#9C27B0",
  mep: "#E91E63",
  property: "#607D8B",
  type: "#FFC107",
  other: "#9E9E9E",
};

const classOptions = computed(() => stats.value?.class_distribution || []);
const maxClassCount = computed(() => {
  if (!stats.value?.class_distribution?.length) return 1;
  return stats.value.class_distribution[0].count;
});

const connectedEdges = computed(() => {
  if (!selectedNode.value) return [];
  const id = selectedNode.value.id;
  return simEdges.filter((e) => e.source === id || e.target === id);
});

function getNodeLabel(id: string): string {
  const node = simNodes.find((n) => n.id === id);
  return node ? node.name || node.ifc_class : id.substring(0, 8);
}

// Graph data loading
async function loadGraph() {
  loading.value = true;
  try {
    const params: any = { depth: depth.value, limit: 200 };
    if (filterClass.value) params.ifc_class = filterClass.value;
    const { data } = await graphApi.getData(slug.value, params);
    nodes.value = data.nodes || [];
    edges.value = data.edges || [];
    initSimulation();
  } catch (e: any) {
    console.error("Failed to load graph:", e);
  } finally {
    loading.value = false;
  }
}

async function loadStats() {
  try {
    const { data } = await graphApi.getStats(slug.value);
    stats.value = data;
  } catch (e) {
    console.error("Failed to load stats:", e);
  }
}

async function doSearch() {
  if (!searchQuery.value.trim()) return;
  try {
    const { data } = await graphApi.search(slug.value, searchQuery.value);
    searchResults.value = data.results;
    selectedNode.value = null;
  } catch (e) {
    console.error("Search failed:", e);
  }
}

async function expandNode(globalId: string) {
  try {
    const { data } = await graphApi.getNode(slug.value, globalId, 1);
    // Merge new nodes/edges into existing
    const existingIds = new Set(simNodes.map((n) => n.id));
    for (const node of data.nodes || []) {
      if (!existingIds.has(node.id)) {
        const center = simNodes.find((n) => n.id === globalId);
        simNodes.push({
          ...node,
          x: (center?.x || 0) + (Math.random() - 0.5) * 100,
          y: (center?.y || 0) + (Math.random() - 0.5) * 100,
          vx: 0,
          vy: 0,
        });
        existingIds.add(node.id);
      }
    }
    const existingEdgeKeys = new Set(simEdges.map((e) => `${e.source}-${e.target}-${e.type}`));
    for (const edge of data.edges || []) {
      const key = `${edge.source}-${edge.target}-${edge.type}`;
      if (!existingEdgeKeys.has(key)) {
        simEdges.push(edge);
      }
    }
  } catch (e) {
    console.error("Expand failed:", e);
  }
}

function focusNode(id: string) {
  const node = simNodes.find((n) => n.id === id);
  if (node) {
    selectedNode.value = node;
    camera.x = -node.x;
    camera.y = -node.y;
  }
}

// Force simulation
function initSimulation() {
  const w = canvas.value?.width || 800;
  const h = canvas.value?.height || 600;

  simNodes = nodes.value.map((n, i) => ({
    ...n,
    x: (w / 2) + (Math.random() - 0.5) * Math.min(w, nodes.value.length * 3),
    y: (h / 2) + (Math.random() - 0.5) * Math.min(h, nodes.value.length * 3),
    vx: 0,
    vy: 0,
  }));

  simEdges = [...edges.value];
  camera = { x: 0, y: 0, zoom: 1 };
}

function simulate() {
  const alpha = 0.3;
  const repulsion = 800;
  const attraction = 0.005;
  const damping = 0.85;
  const centerForce = 0.01;

  const nodeMap = new Map(simNodes.map((n) => [n.id, n]));

  // Center gravity
  const cx = (canvas.value?.width || 800) / 2;
  const cy = (canvas.value?.height || 600) / 2;

  for (const node of simNodes) {
    if (node.fx != null) continue;
    node.vx += (cx - node.x) * centerForce;
    node.vy += (cy - node.y) * centerForce;
  }

  // Repulsion (Barnes-Hut would be better for large graphs, simple O(n^2) for now)
  for (let i = 0; i < simNodes.length; i++) {
    for (let j = i + 1; j < simNodes.length; j++) {
      const a = simNodes[i];
      const b = simNodes[j];
      let dx = b.x - a.x;
      let dy = b.y - a.y;
      let dist = Math.sqrt(dx * dx + dy * dy) || 1;
      if (dist > 500) continue;
      const force = repulsion / (dist * dist);
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      if (a.fx == null) { a.vx -= fx; a.vy -= fy; }
      if (b.fx == null) { b.vx += fx; b.vy += fy; }
    }
  }

  // Attraction along edges
  for (const edge of simEdges) {
    const source = nodeMap.get(edge.source);
    const target = nodeMap.get(edge.target);
    if (!source || !target) continue;
    const dx = target.x - source.x;
    const dy = target.y - source.y;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;
    const force = (dist - 80) * attraction;
    const fx = (dx / dist) * force;
    const fy = (dy / dist) * force;
    if (source.fx == null) { source.vx += fx; source.vy += fy; }
    if (target.fx == null) { target.vx -= fx; target.vy -= fy; }
  }

  // Apply velocities
  for (const node of simNodes) {
    if (node.fx != null) {
      node.x = node.fx;
      node.y = node.fy!;
      node.vx = 0;
      node.vy = 0;
      continue;
    }
    node.vx *= damping;
    node.vy *= damping;
    node.x += node.vx * alpha;
    node.y += node.vy * alpha;
  }
}

function render() {
  const ctx = canvas.value?.getContext("2d");
  if (!ctx || !canvas.value) return;

  const w = canvas.value.width;
  const h = canvas.value.height;

  ctx.clearRect(0, 0, w, h);
  ctx.save();

  // Apply camera
  ctx.translate(w / 2 + camera.x * camera.zoom, h / 2 + camera.y * camera.zoom);
  ctx.scale(camera.zoom, camera.zoom);
  ctx.translate(-w / 2, -h / 2);

  // Draw edges
  ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
  ctx.lineWidth = 1;
  const nodeMap = new Map(simNodes.map((n) => [n.id, n]));

  for (const edge of simEdges) {
    const source = nodeMap.get(edge.source);
    const target = nodeMap.get(edge.target);
    if (!source || !target) continue;

    ctx.beginPath();
    ctx.moveTo(source.x, source.y);
    ctx.lineTo(target.x, target.y);

    // Highlight edges of selected node
    if (selectedNode.value && (edge.source === selectedNode.value.id || edge.target === selectedNode.value.id)) {
      ctx.strokeStyle = "rgba(74, 144, 184, 0.5)";
      ctx.lineWidth = 2;
    } else {
      ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
      ctx.lineWidth = 1;
    }
    ctx.stroke();
  }

  // Draw nodes
  for (const node of simNodes) {
    const color = groupColors[node.group] || "#9E9E9E";
    const isSelected = selectedNode.value?.id === node.id;
    const isHovered = hovered?.id === node.id;
    const radius = isSelected ? 8 : isHovered ? 7 : 5;

    ctx.beginPath();
    ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();

    if (isSelected) {
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = 2;
      ctx.stroke();
    } else if (isHovered) {
      ctx.strokeStyle = "rgba(255,255,255,0.5)";
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    // Labels for selected/hovered or zoomed-in nodes
    if (isSelected || isHovered || camera.zoom > 1.5) {
      const label = node.name || node.ifc_class;
      ctx.fillStyle = "rgba(255, 255, 255, 0.85)";
      ctx.font = `${isSelected ? "bold " : ""}11px Inter, sans-serif`;
      ctx.textAlign = "center";
      ctx.fillText(label, node.x, node.y - radius - 4);
    }
  }

  ctx.restore();
}

function animationLoop() {
  simulate();
  render();
  animFrame = requestAnimationFrame(animationLoop);
}

// Mouse interaction
function screenToWorld(sx: number, sy: number): { x: number; y: number } {
  const w = canvas.value?.width || 800;
  const h = canvas.value?.height || 600;
  return {
    x: (sx - w / 2 - camera.x * camera.zoom) / camera.zoom + w / 2,
    y: (sy - h / 2 - camera.y * camera.zoom) / camera.zoom + h / 2,
  };
}

function findNodeAt(mx: number, my: number): SimNode | null {
  const { x, y } = screenToWorld(mx, my);
  for (let i = simNodes.length - 1; i >= 0; i--) {
    const n = simNodes[i];
    const dx = n.x - x;
    const dy = n.y - y;
    if (dx * dx + dy * dy < 100) return n;
  }
  return null;
}

function onMouseDown(e: MouseEvent) {
  const rect = canvas.value!.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;
  const node = findNodeAt(mx, my);

  if (node) {
    dragging = node;
    node.fx = node.x;
    node.fy = node.y;
    selectedNode.value = node;
    searchResults.value = [];
  } else {
    panning = true;
    panStart = { x: e.clientX - camera.x, y: e.clientY - camera.y };
  }
}

function onMouseMove(e: MouseEvent) {
  const rect = canvas.value!.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;

  if (dragging) {
    const world = screenToWorld(mx, my);
    dragging.fx = world.x;
    dragging.fy = world.y;
  } else if (panning) {
    camera.x = e.clientX - panStart.x;
    camera.y = e.clientY - panStart.y;
  } else {
    const node = findNodeAt(mx, my);
    hovered = node;
    canvas.value!.style.cursor = node ? "pointer" : "grab";
  }
}

function onMouseUp() {
  if (dragging) {
    dragging.fx = null;
    dragging.fy = null;
    dragging = null;
  }
  panning = false;
}

function onWheel(e: WheelEvent) {
  e.preventDefault();
  const factor = e.deltaY > 0 ? 0.9 : 1.1;
  camera.zoom = Math.max(0.1, Math.min(10, camera.zoom * factor));
}

function onDblClick(e: MouseEvent) {
  const rect = canvas.value!.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;
  const node = findNodeAt(mx, my);
  if (node) {
    expandNode(node.id);
  }
}

function resizeCanvas() {
  if (!canvas.value || !canvasContainer.value) return;
  const rect = canvasContainer.value.getBoundingClientRect();
  canvas.value.width = rect.width;
  canvas.value.height = rect.height;
}

async function startImport() {
  if (!importFilePath.value.trim()) return;
  showImportModal.value = false;
  importing.value = true;
  importJob.value = { status: "queued", progress: 0, phase_label: "Queuing..." };

  try {
    const { data } = await graphApi.importIfc(slug.value, importFilePath.value.trim());
    if (data.job_id) {
      pollImportProgress(data.job_id);
    } else {
      // Synchronous result
      importJob.value = { status: "completed", progress: 100, ...data };
      importing.value = false;
    }
  } catch (e: any) {
    importJob.value = { status: "failed", error: e.response?.data?.detail || "Import failed", progress: 0 };
    importing.value = false;
  }
}

function pollImportProgress(jobId: string) {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      const { data } = await graphApi.getImportStatus(slug.value, jobId);
      importJob.value = data;
      if (data.status === "completed" || data.status === "failed") {
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = null;
        importing.value = false;
      }
    } catch {
      // Job not found yet, keep polling
    }
  }, 1000);
}

function onImportDone() {
  importJob.value = null;
  loadStats();
  loadGraph();
}

onMounted(async () => {
  await nextTick();
  resizeCanvas();
  window.addEventListener("resize", resizeCanvas);

  await Promise.all([loadStats(), loadGraph()]);
  animFrame = requestAnimationFrame(animationLoop);
});

onUnmounted(() => {
  cancelAnimationFrame(animFrame);
  window.removeEventListener("resize", resizeCanvas);
  if (pollTimer) clearInterval(pollTimer);
});
</script>

<style scoped>
.graph-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative;
  overflow: hidden;
}

.graph-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  gap: 12px;
}

.toolbar-left, .toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.toolbar-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.toolbar-badge {
  font-size: 11px;
  color: var(--text-secondary);
  background: var(--bg-surface);
  padding: 2px 8px;
  border-radius: 10px;
}

.search-input {
  width: 180px;
  padding: 5px 10px;
  font-size: 12px;
}

.filter-select {
  padding: 5px 8px;
  font-size: 12px;
  min-width: 120px;
}

.graph-content {
  flex: 1;
  display: flex;
  position: relative;
  overflow: hidden;
}

.graph-canvas-container {
  flex: 1;
  position: relative;
}

.graph-canvas-container canvas {
  width: 100%;
  height: 100%;
  display: block;
  background: var(--bg-primary);
}

.graph-loading {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-secondary);
  font-size: 14px;
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.graph-empty {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  color: var(--text-secondary);
}

.graph-empty p {
  margin: 8px 0 0;
  font-size: 14px;
}

.graph-empty-sub {
  font-size: 12px;
  opacity: 0.7;
}

/* Sidebar */
.graph-sidebar {
  width: 0;
  overflow: hidden;
  background: var(--bg-secondary);
  border-left: 1px solid var(--border);
  transition: width 0.2s ease;
}

.graph-sidebar.open {
  width: 300px;
}

.sidebar-content {
  padding: 16px;
  width: 300px;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.sidebar-header h3 {
  font-size: 14px;
  font-weight: 600;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-props {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.prop-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.prop-label {
  font-size: 11px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.prop-value {
  font-size: 12px;
  color: var(--text-primary);
  text-align: right;
}

.prop-value.mono {
  font-family: monospace;
  font-size: 10px;
  word-break: break-all;
}

.class-badge {
  padding: 2px 6px;
  border-radius: 4px;
  color: #fff;
  font-size: 11px;
  font-weight: 600;
}

.sidebar-edges {
  margin-top: 16px;
}

.sidebar-edges h4 {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 0 0 8px;
}

.edge-item {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 4px 0;
  border-bottom: 1px solid var(--border);
  font-size: 11px;
}

.edge-type {
  color: var(--accent);
  font-weight: 600;
  flex-shrink: 0;
}

.edge-target {
  color: var(--text-secondary);
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.edge-target:hover {
  color: var(--text-primary);
}

.search-result {
  padding: 8px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  transition: background 0.1s;
}

.search-result:hover {
  background: var(--bg-hover);
}

.result-class {
  display: block;
  font-size: 10px;
  color: var(--accent);
  text-transform: uppercase;
}

.result-name {
  font-size: 12px;
  color: var(--text-primary);
}

/* Legend */
.graph-legend {
  position: absolute;
  bottom: 12px;
  left: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  background: rgba(15, 21, 32, 0.85);
  padding: 8px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
  max-width: 400px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  color: var(--text-secondary);
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* Stats panel */
.stats-panel {
  position: absolute;
  bottom: 12px;
  right: 12px;
  background: rgba(15, 21, 32, 0.9);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 12px;
  width: 220px;
}

.stats-panel h4 {
  font-size: 11px;
  color: var(--text-secondary);
  margin: 0 0 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stats-bars {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-bar-row {
  display: grid;
  grid-template-columns: 90px 1fr 30px;
  align-items: center;
  gap: 6px;
}

.stat-label {
  font-size: 10px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stat-bar {
  height: 6px;
  background: var(--bg-surface);
  border-radius: 3px;
  overflow: hidden;
}

.stat-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 3px;
  transition: width 0.3s;
}

.stat-count {
  font-size: 10px;
  color: var(--text-secondary);
  text-align: right;
}

/* Import progress */
.import-progress-bar {
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
  padding: 8px 16px;
  flex-shrink: 0;
}

.import-progress-info {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  margin-bottom: 4px;
}

.import-phase {
  color: var(--text-secondary);
}

.import-pct {
  color: var(--accent);
  font-weight: 600;
}

.import-bar-track {
  height: 4px;
  background: var(--bg-surface);
  border-radius: 2px;
  overflow: hidden;
}

.import-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent), var(--accent-warm));
  border-radius: 2px;
  transition: width 0.3s ease;
}

.import-done {
  margin-top: 6px;
  font-size: 12px;
  color: var(--success);
  display: flex;
  align-items: center;
}

.import-error {
  margin-top: 6px;
  font-size: 12px;
  color: var(--danger);
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-box {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px;
  width: 400px;
  max-width: 90vw;
}

.modal-box h3 {
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 600;
}
</style>
