import { defineStore } from "pinia";
import { ref, shallowRef } from "vue";

interface SpatialNode {
  type: string;
  name: string;
  expressID?: number;
  children?: SpatialNode[];
}

interface ElementProperties {
  expressID: number;
  GlobalId: string;
  Class: string;
  Name: string | null;
  ObjectType: string | null;
  propertySets: Record<string, Record<string, any>>;
}

export const useViewerStore = defineStore("viewer", () => {
  const selectedElementId = ref<number | null>(null);
  const selectedProperties = ref<ElementProperties | null>(null);
  const spatialTree = ref<SpatialNode | null>(null);
  const propertiesMap = ref<Record<string, ElementProperties>>({});
  const loading = ref(false);
  const activeFile = ref<string | null>(null);

  function selectElement(expressID: number | null) {
    selectedElementId.value = expressID;
    if (expressID !== null && propertiesMap.value[String(expressID)]) {
      selectedProperties.value = propertiesMap.value[String(expressID)];
    } else {
      selectedProperties.value = null;
    }
  }

  function setPropertiesMap(map: Record<string, ElementProperties>) {
    propertiesMap.value = map;
  }

  function setSpatialTree(tree: SpatialNode) {
    spatialTree.value = tree;
  }

  function clearViewer() {
    selectedElementId.value = null;
    selectedProperties.value = null;
    spatialTree.value = null;
    propertiesMap.value = {};
    activeFile.value = null;
  }

  return {
    selectedElementId,
    selectedProperties,
    spatialTree,
    propertiesMap,
    loading,
    activeFile,
    selectElement,
    setPropertiesMap,
    setSpatialTree,
    clearViewer,
  };
});
