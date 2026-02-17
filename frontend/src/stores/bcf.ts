import { defineStore } from "pinia";
import { ref } from "vue";

// BCF store - Phase 2 implementation
export const useBcfStore = defineStore("bcf", () => {
  const topics = ref<any[]>([]);
  const loading = ref(false);

  return { topics, loading };
});
