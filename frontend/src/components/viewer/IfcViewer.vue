<template>
  <div ref="containerRef" class="ifc-viewer">
    <div v-if="loading" class="viewer-loading">
      <div class="spinner"></div>
      <p>{{ loadStatus }}</p>
    </div>
    <div v-if="error" class="viewer-error">
      <p>{{ error }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue";
import * as OBC from "@thatopen/components";
import * as OBF from "@thatopen/components-front";
import * as THREE from "three";
import { useViewerStore } from "@/stores/viewer";
import { fragmentsApi } from "@/services/api";

const viewerStore = useViewerStore();
const containerRef = ref<HTMLDivElement | null>(null);
const loading = ref(false);
const loadStatus = ref("Loading model...");
const error = ref("");

let components: OBC.Components | null = null;
let world: OBC.SimpleWorld<OBC.SimpleScene, OBC.SimpleCamera, OBF.PostproductionRenderer> | null = null;
let currentModel: THREE.Object3D | null = null;
let modelCenter = new THREE.Vector3();
let modelRadius = 50;

onMounted(() => {
  initViewer();
});

onBeforeUnmount(() => {
  if (components) {
    components.dispose();
  }
});

function initViewer() {
  if (!containerRef.value) return;

  components = new OBC.Components();

  const worlds = components.get(OBC.Worlds);
  world = worlds.create<OBC.SimpleScene, OBC.SimpleCamera, OBF.PostproductionRenderer>();

  world.scene = new OBC.SimpleScene(components);
  world.renderer = new OBF.PostproductionRenderer(components, containerRef.value);
  world.camera = new OBC.SimpleCamera(components);

  // Disable postproduction - causes blank screen
  world.renderer.postproduction.enabled = false;

  components.init();

  world.scene.setup();
  world.camera.controls.setLookAt(20, 20, 20, 0, 0, 0);

  // Grid
  const grids = components.get(OBC.Grids);
  grids.create(world);

  // Raycaster for selection
  const casters = components.get(OBC.Raycasters);
  casters.get(world);

  // Handle window resize
  const resizeObserver = new ResizeObserver(() => {
    if (world?.renderer) {
      world.renderer.resize();
    }
  });
  resizeObserver.observe(containerRef.value);

  // Click handler for element selection
  containerRef.value.addEventListener("click", handleClick);
}

async function handleClick(event: MouseEvent) {
  if (!components || !world) return;

  const casters = components.get(OBC.Raycasters);
  const caster = casters.get(world);
  const result = caster.castRay();

  if (result && result.object) {
    const mesh = result.object as THREE.Mesh;
    const frag = (mesh as any).fragment;
    if (frag) {
      // Get expressID from fragment
      const itemId = frag.getItemID(result.instanceId ?? 0);
      if (itemId !== undefined && itemId !== null) {
        viewerStore.selectElement(itemId);
        highlightElement(itemId);
        return;
      }
    }
    // Fallback: try getting from face index
    if (result.faceIndex !== undefined) {
      viewerStore.selectElement(result.faceIndex);
    }
  } else {
    viewerStore.selectElement(null);
    clearHighlight();
  }
}

function fitCameraToModel(obj?: THREE.Object3D) {
  if (!world) return;
  const target = obj || currentModel;
  if (!target) return;

  const box = new THREE.Box3().setFromObject(target);
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  const radius = Math.max(size.x, size.y, size.z);
  const dist = radius * 2;

  modelCenter.copy(center);
  modelRadius = radius;

  world.camera.controls.setLookAt(
    center.x + dist, center.y + dist * 0.7, center.z + dist,
    center.x, center.y, center.z,
    true,
  );
}

function setView(direction: string) {
  if (!world || !currentModel) return;
  const dist = modelRadius * 2.5;
  const c = modelCenter;

  switch (direction) {
    case "front":
      world.camera.controls.setLookAt(c.x, c.y, c.z + dist, c.x, c.y, c.z, true);
      break;
    case "top":
      world.camera.controls.setLookAt(c.x, c.y + dist, c.z, c.x, c.y, c.z, true);
      break;
    case "right":
      world.camera.controls.setLookAt(c.x + dist, c.y, c.z, c.x, c.y, c.z, true);
      break;
  }
}

let wireframeActive = false;
function toggleWireframe() {
  if (!currentModel) return;
  wireframeActive = !wireframeActive;
  currentModel.traverse((child: any) => {
    if (child.isMesh && child.material) {
      const mats = Array.isArray(child.material) ? child.material : [child.material];
      mats.forEach((m: any) => { m.wireframe = wireframeActive; });
    }
  });
}

let highlightedMeshes: { mesh: THREE.Mesh; originalMaterial: THREE.Material | THREE.Material[] }[] = [];

function highlightElement(expressID: number) {
  clearHighlight();
  if (!currentModel) return;

  const highlightMat = new THREE.MeshStandardMaterial({
    color: 0x00aaff,
    transparent: true,
    opacity: 0.7,
    depthTest: true,
  });

  currentModel.traverse((child: any) => {
    if (child.isMesh && child.fragment) {
      const ids = child.fragment.ids;
      if (ids && ids.has(expressID)) {
        highlightedMeshes.push({ mesh: child, originalMaterial: child.material });
        child.material = highlightMat;
      }
    }
  });
}

function clearHighlight() {
  for (const { mesh, originalMaterial } of highlightedMeshes) {
    mesh.material = originalMaterial;
  }
  highlightedMeshes = [];
}

async function loadModel(slug: string, filePath: string) {
  if (!components || !world) return;
  loading.value = true;
  error.value = "";

  try {
    loadStatus.value = "Checking for pre-built fragments...";
    const token = localStorage.getItem("token");
    const fragUrl = fragmentsApi.getFragmentUrl(slug, filePath);

    const response = await fetch(fragUrl, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (response.ok) {
      loadStatus.value = "Loading fragments...";
      const data = await response.arrayBuffer();
      const buffer = new Uint8Array(data);

      const fragmentsManager = components!.get(OBC.FragmentsManager);
      const model = fragmentsManager.load(buffer);
      world!.scene.three.add(model);
      currentModel = model;
    } else {
      loadStatus.value = "Downloading IFC file...";
      await loadIfcDirectly(slug, filePath);
    }

    fitCameraToModel();

    loadStatus.value = "Loading metadata...";
    await loadMetadata(slug, filePath);
  } catch (err: any) {
    console.error("Failed to load model:", err);
    error.value = `Failed to load: ${err.message || err}`;
  } finally {
    loading.value = false;
  }
}

async function loadIfcDirectly(slug: string, filePath: string) {
  if (!components) return;

  const token = localStorage.getItem("token");
  const response = await fetch(`/api/projects/${slug}/files/${encodeURIComponent(filePath)}`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    throw new Error("Failed to download IFC file");
  }

  loadStatus.value = "Parsing IFC model...";
  const data = await response.arrayBuffer();
  const buffer = new Uint8Array(data);

  const ifcLoader = components.get(OBC.IfcLoader);
  await ifcLoader.setup({ autoSetWasm: false });
  ifcLoader.settings.wasm.path = "/app/";
  ifcLoader.settings.wasm.absolute = false;

  const model = await ifcLoader.load(buffer);

  if (world) {
    world.scene.three.add(model);
    currentModel = model;
  }
}

async function loadMetadata(slug: string, filePath: string) {
  try {
    const [propsRes, spatialRes] = await Promise.allSettled([
      fragmentsApi.getProperties(slug, filePath),
      fragmentsApi.getSpatialTree(slug, filePath),
    ]);

    if (propsRes.status === "fulfilled") {
      viewerStore.setPropertiesMap(propsRes.value.data);
    }

    if (spatialRes.status === "fulfilled") {
      viewerStore.setSpatialTree(spatialRes.value.data);
    }
  } catch (err) {
    console.warn("Failed to load metadata:", err);
  }
}

defineExpose({ loadModel, highlightElement, fitCameraToModel, setView, toggleWireframe });
</script>

<style scoped>
.ifc-viewer {
  width: 100%;
  height: 100%;
  position: relative;
  background: #1a1a2e;
}

.ifc-viewer canvas {
  width: 100% !important;
  height: 100% !important;
}

.viewer-loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(26, 26, 46, 0.8);
  z-index: 10;
  color: var(--text-secondary);
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 12px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.viewer-error {
  position: absolute;
  bottom: 20px;
  left: 20px;
  right: 20px;
  background: rgba(200, 50, 50, 0.9);
  color: white;
  padding: 12px;
  border-radius: 6px;
  font-size: 13px;
  z-index: 10;
}
</style>
