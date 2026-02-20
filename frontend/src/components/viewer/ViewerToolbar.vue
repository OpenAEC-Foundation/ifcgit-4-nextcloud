<template>
  <div class="viewer-toolbar">
    <button class="tool-btn" title="Fit to view" @click="$emit('fitToView')">
      <span>Fit</span>
    </button>
    <button class="tool-btn" title="Front view" @click="$emit('setView', 'front')">
      <span>Front</span>
    </button>
    <button class="tool-btn" title="Top view" @click="$emit('setView', 'top')">
      <span>Top</span>
    </button>
    <button class="tool-btn" title="Right view" @click="$emit('setView', 'right')">
      <span>Right</span>
    </button>
    <div class="toolbar-separator"></div>
    <button class="tool-btn" title="Toggle wireframe" @click="$emit('toggleWireframe')">
      <span>Wire</span>
    </button>
  </div>
</template>

<script setup lang="ts">
defineEmits<{
  fitToView: [];
  setView: [direction: string];
  toggleWireframe: [];
}>();
</script>

<style scoped>
.viewer-toolbar {
  position: absolute;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 4px;
  padding: 4px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 6px;
  z-index: 5;
}

.tool-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 12px;
}
.tool-btn:hover {
  background: var(--bg-surface);
  color: var(--text-primary);
}

.toolbar-separator {
  width: 1px;
  background: var(--border);
  margin: 4px 2px;
}
</style>
