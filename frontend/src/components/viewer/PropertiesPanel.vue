<template>
  <div class="properties-panel">
    <div class="prop-section">
      <div class="prop-row">
        <span class="prop-key">Class</span>
        <span class="prop-val">{{ properties.Class }}</span>
      </div>
      <div class="prop-row">
        <span class="prop-key">Name</span>
        <span class="prop-val">{{ properties.Name || "—" }}</span>
      </div>
      <div class="prop-row">
        <span class="prop-key">GlobalId</span>
        <span class="prop-val mono">{{ properties.GlobalId }}</span>
      </div>
      <div v-if="properties.ObjectType" class="prop-row">
        <span class="prop-key">Type</span>
        <span class="prop-val">{{ properties.ObjectType }}</span>
      </div>
      <div class="prop-row">
        <span class="prop-key">Express ID</span>
        <span class="prop-val mono">{{ properties.expressID }}</span>
      </div>
    </div>

    <div
      v-for="(pset, psetName) in properties.propertySets"
      :key="psetName"
      class="prop-section"
    >
      <h5 class="pset-name" @click="togglePset(psetName as string)">
        <span>{{ expandedPsets.has(psetName as string) ? "▾" : "▸" }}</span>
        {{ psetName }}
      </h5>
      <template v-if="expandedPsets.has(psetName as string)">
        <div v-for="(val, key) in pset" :key="key" class="prop-row">
          <span class="prop-key">{{ key }}</span>
          <span class="prop-val">{{ val ?? "—" }}</span>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";

interface ElementProperties {
  expressID: number;
  GlobalId: string;
  Class: string;
  Name: string | null;
  ObjectType: string | null;
  propertySets: Record<string, Record<string, any>>;
}

defineProps<{
  properties: ElementProperties;
}>();

const expandedPsets = ref<Set<string>>(new Set());

function togglePset(name: string) {
  if (expandedPsets.value.has(name)) {
    expandedPsets.value.delete(name);
  } else {
    expandedPsets.value.add(name);
  }
}
</script>

<style scoped>
.properties-panel {
  font-size: 12px;
  max-height: 500px;
  overflow-y: auto;
}

.prop-section {
  padding: 8px 0;
  border-bottom: 1px solid var(--border);
}

.prop-row {
  display: flex;
  justify-content: space-between;
  padding: 3px 0;
  gap: 8px;
}

.prop-key {
  color: var(--text-secondary);
  flex-shrink: 0;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.prop-val {
  text-align: right;
  word-break: break-all;
}

.mono {
  font-family: monospace;
  font-size: 11px;
}

.pset-name {
  font-size: 12px;
  color: var(--accent);
  cursor: pointer;
  margin-bottom: 4px;
  display: flex;
  gap: 4px;
  align-items: center;
}
.pset-name:hover {
  color: var(--accent-hover);
}
</style>
