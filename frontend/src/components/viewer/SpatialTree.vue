<template>
  <div class="spatial-tree">
    <SpatialTreeNode :node="node" :depth="0" @select="$emit('select', $event)" />
  </div>
</template>

<script setup lang="ts">
import SpatialTreeNode from "./SpatialTreeNode.vue";

interface SpatialNode {
  type: string;
  name: string;
  expressID?: number;
  children?: SpatialNode[];
}

defineProps<{
  node: SpatialNode;
}>();

defineEmits<{
  select: [expressID: number];
}>();
</script>

<style scoped>
.spatial-tree {
  font-size: 13px;
  max-height: 400px;
  overflow-y: auto;
}
</style>
