<template>
  <div class="file-upload">
    <input
      ref="fileInput"
      type="file"
      accept=".ifc,.ifczip"
      style="display: none"
      @change="handleFile"
    />
    <button class="btn-sm" @click="fileInput?.click()" :disabled="uploading">
      {{ uploading ? "Uploading..." : "+ Upload" }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useProjectStore } from "@/stores/project";

const props = defineProps<{
  slug: string;
}>();

const emit = defineEmits<{
  uploaded: [];
}>();

const store = useProjectStore();
const fileInput = ref<HTMLInputElement | null>(null);
const uploading = ref(false);

async function handleFile(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;

  uploading.value = true;
  try {
    await store.uploadFile(props.slug, file);
    emit("uploaded");
  } catch (err) {
    console.error("Upload failed:", err);
  } finally {
    uploading.value = false;
    input.value = "";
  }
}
</script>

<style scoped>
.file-upload {
  display: inline-block;
}
</style>
