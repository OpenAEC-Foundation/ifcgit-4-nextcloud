<template>
  <div ref="containerRef" class="ifc-viewer">
    <div v-if="loading" class="viewer-loading">
      <div class="spinner"></div>
      <p>Loading model...</p>
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

let components: OBC.Components | null = null;
let world: OBC.SimpleWorld<OBC.SimpleScene, OBC.SimpleCamera, OBF.PostproductionRenderer> | null = null;

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
    // Try to get expressID from the intersected mesh
    const mesh = result.object as THREE.Mesh;
    const frag = (mesh as any).fragment;
    if (frag && result.faceIndex !== undefined) {
      const expressID = frag.getItemID(result.instanceId ?? 0, result.faceIndex);
      if (expressID !== undefined) {
        viewerStore.selectElement(expressID);
      }
    }
  } else {
    viewerStore.selectElement(null);
  }
}

async function loadModel(slug: string, filePath: string) {
  if (!components || !world) return;
  loading.value = true;

  try {
    // Load fragment if available
    const token = localStorage.getItem("token");
    const fragUrl = fragmentsApi.getFragmentUrl(slug, filePath);

    const response = await fetch(fragUrl, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (response.ok) {
      // Load .frag file
      const data = await response.arrayBuffer();
      const buffer = new Uint8Array(data);

      const fragmentsManager = components!.get(OBC.FragmentsManager);
      const model = fragmentsManager.load(buffer);
      world!.scene.three.add(model);

      // Fit camera to model
      world!.camera.controls.fitToSphere(model, true);
    } else {
      // Fragment not ready - try loading IFC directly
      console.warn("Fragment not available, attempting client-side IFC loading");
      await loadIfcDirectly(slug, filePath);
    }

    // Load properties and spatial tree
    await loadMetadata(slug, filePath);
  } catch (err) {
    console.error("Failed to load model:", err);
  } finally {
    loading.value = false;
  }
}

async function loadIfcDirectly(slug: string, filePath: string) {
  if (!components) return;

  const token = localStorage.getItem("token");
  const response = await fetch(`/api/projects/${slug}/files/${filePath}`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    throw new Error("Failed to download IFC file");
  }

  const data = await response.arrayBuffer();
  const buffer = new Uint8Array(data);

  const ifcLoader = components.get(OBC.IfcLoader);
  await ifcLoader.setup();
  const model = await ifcLoader.load(buffer);

  if (world) {
    world.scene.three.add(model);
    world.camera.controls.fitToSphere(model, true);
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

function highlightElement(expressID: number) {
  // Highlighting will be implemented with That Open Company's highlighter
  console.log("Highlight element:", expressID);
}

defineExpose({ loadModel, highlightElement });
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
</style>
