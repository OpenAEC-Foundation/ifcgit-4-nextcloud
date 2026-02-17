<template>
  <div id="app-root">
    <nav v-if="authStore.isAuthenticated" class="app-nav">
      <div class="nav-left">
        <router-link to="/app/" class="nav-brand">IfcGit</router-link>
        <router-link to="/app/projects" class="nav-link">Projects</router-link>
      </div>
      <div class="nav-right">
        <span class="nav-user">{{ authStore.user?.username }}</span>
        <button class="btn-sm" @click="authStore.logout()">Logout</button>
      </div>
    </nav>
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from "@/stores/auth";

const authStore = useAuthStore();
</script>

<style>
:root {
  --bg-primary: #1a1a2e;
  --bg-secondary: #16213e;
  --bg-surface: #0f3460;
  --text-primary: #e4e4e4;
  --text-secondary: #a0a0a0;
  --accent: #00b4d8;
  --accent-hover: #0096c7;
  --danger: #e63946;
  --success: #2d9a3e;
  --border: #2a2a4a;
  --sidebar-width: 320px;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
}

#app-root {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.app-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 16px;
  height: 48px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.nav-left, .nav-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.nav-brand {
  font-weight: 700;
  font-size: 18px;
  color: var(--accent);
  text-decoration: none;
}

.nav-link {
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
}
.nav-link:hover, .nav-link.router-link-active {
  color: var(--text-primary);
}

.nav-user {
  font-size: 13px;
  color: var(--text-secondary);
}

.app-main {
  flex: 1;
  overflow: hidden;
}

/* Shared button styles */
.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  background: var(--accent);
  color: white;
}
.btn:hover { background: var(--accent-hover); }
.btn-sm {
  padding: 4px 10px;
  border: 1px solid var(--border);
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  background: transparent;
  color: var(--text-secondary);
}
.btn-sm:hover { background: var(--bg-surface); color: var(--text-primary); }

.btn-danger { background: var(--danger); }

/* Form styles */
input, select, textarea {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 14px;
  width: 100%;
}
input:focus, select:focus, textarea:focus {
  outline: none;
  border-color: var(--accent);
}

label {
  display: block;
  margin-bottom: 4px;
  font-size: 13px;
  color: var(--text-secondary);
}

.form-group {
  margin-bottom: 16px;
}
</style>
