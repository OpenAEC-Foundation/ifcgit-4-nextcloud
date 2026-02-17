<template>
  <div class="git-history">
    <div v-if="commits.length === 0" class="empty-hint">
      No commits yet
    </div>
    <div v-for="commit in commits" :key="commit.hash" class="commit-item">
      <div class="commit-hash">{{ commit.hash.substring(0, 8) }}</div>
      <div class="commit-msg">{{ commit.message }}</div>
      <div class="commit-meta">
        <span>{{ commit.author_name }}</span>
        <span>{{ formatDate(commit.timestamp) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Commit {
  hash: string;
  message: string;
  author_name: string;
  author_email: string;
  timestamp: number;
}

defineProps<{
  commits: Commit[];
}>();

function formatDate(timestamp: number) {
  const d = new Date(timestamp * 1000);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  const hours = Math.floor(diff / 3600000);
  if (hours < 1) return "just now";
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return d.toLocaleDateString();
}
</script>

<style scoped>
.git-history {
  max-height: 400px;
  overflow-y: auto;
}

.commit-item {
  padding: 8px 0;
  border-bottom: 1px solid var(--border);
}

.commit-hash {
  font-family: monospace;
  font-size: 11px;
  color: var(--accent);
  margin-bottom: 2px;
}

.commit-msg {
  font-size: 13px;
  margin-bottom: 4px;
  word-break: break-word;
}

.commit-meta {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text-secondary);
}

.empty-hint {
  font-size: 12px;
  color: var(--text-secondary);
  text-align: center;
  padding: 20px 0;
}
</style>
