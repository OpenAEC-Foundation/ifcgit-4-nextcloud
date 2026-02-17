<template>
  <div class="tree-node" :style="{ paddingLeft: depth * 12 + 'px' }">
    <div
      class="tree-label"
      @click="toggle"
      :class="{ clickable: node.expressID }"
    >
      <span v-if="hasChildren" class="tree-toggle">{{ expanded ? "▾" : "▸" }}</span>
      <span v-else class="tree-toggle-placeholder"></span>
      <span class="tree-type" :class="typeClass">{{ shortType }}</span>
      <span class="tree-name" @click.stop="selectNode">{{ node.name }}</span>
    </div>
    <div v-if="expanded && hasChildren" class="tree-children">
      <SpatialTreeNode
        v-for="(child, i) in node.children"
        :key="i"
        :node="child"
        :depth="depth + 1"
        @select="$emit('select', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";

interface SpatialNode {
  type: string;
  name: string;
  expressID?: number;
  children?: SpatialNode[];
}

const props = defineProps<{
  node: SpatialNode;
  depth: number;
}>();

const emit = defineEmits<{
  select: [expressID: number];
}>();

const expanded = ref(props.depth < 3);

const hasChildren = computed(() => props.node.children && props.node.children.length > 0);

const shortType = computed(() => {
  return props.node.type.replace("Ifc", "").substring(0, 3);
});

const typeClass = computed(() => {
  const t = props.node.type;
  if (t.includes("Site")) return "type-site";
  if (t.includes("Building") && !t.includes("Storey")) return "type-building";
  if (t.includes("Storey")) return "type-storey";
  if (t.includes("Space")) return "type-space";
  if (t.includes("Wall")) return "type-wall";
  if (t.includes("Slab")) return "type-slab";
  if (t.includes("Window") || t.includes("Door")) return "type-opening";
  return "type-default";
});

function toggle() {
  if (hasChildren.value) {
    expanded.value = !expanded.value;
  }
}

function selectNode() {
  if (props.node.expressID) {
    emit("select", props.node.expressID);
  }
}
</script>

<style scoped>
.tree-label {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 4px;
  border-radius: 3px;
  cursor: default;
  white-space: nowrap;
}
.tree-label:hover {
  background: var(--bg-surface);
}
.tree-label.clickable {
  cursor: pointer;
}

.tree-toggle {
  width: 12px;
  font-size: 10px;
  color: var(--text-secondary);
  cursor: pointer;
}
.tree-toggle-placeholder {
  width: 12px;
}

.tree-type {
  font-size: 10px;
  padding: 0 4px;
  border-radius: 2px;
  font-weight: 600;
  min-width: 24px;
  text-align: center;
}

.type-site { background: #2d5a27; color: #8fbc8f; }
.type-building { background: #4a3728; color: #d2a679; }
.type-storey { background: #28424a; color: #79b8d2; }
.type-space { background: #3a2850; color: #b079d2; }
.type-wall { background: #4a4a28; color: #d2d279; }
.type-slab { background: #4a2828; color: #d27979; }
.type-opening { background: #28424a; color: #79d2b0; }
.type-default { background: #3a3a3a; color: #aaa; }

.tree-name {
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
