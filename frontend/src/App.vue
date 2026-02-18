<template>
  <div id="app-root">
    <nav v-if="authStore.isAuthenticated" class="app-nav">
      <div class="nav-left">
        <router-link to="/app/" class="nav-brand">
          <svg width="22" height="22" viewBox="0 0 40 40" fill="none">
            <path d="M20 4L4 12v16l16 8 16-8V12L20 4z" stroke="url(#nb)" stroke-width="2.5" fill="none"/>
            <defs><linearGradient id="nb" x1="4" y1="4" x2="36" y2="36"><stop stop-color="#E07B3C"/><stop offset="1" stop-color="#4A90B8"/></linearGradient></defs>
          </svg>
          <span>Open<span class="nav-brand-accent">AEC</span></span>
        </router-link>
        <div class="nav-sep"></div>
        <router-link to="/app/projects" class="nav-link">Projects</router-link>
      </div>
      <div class="nav-right">
        <router-link to="/app/settings" class="nav-icon-link" title="Settings">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M6.5 1.5L6.8 3.1a4.5 4.5 0 011.4.6l1.4-.9 1.4 1.4-.9 1.4c.3.4.5.9.6 1.4l1.6.3v2l-1.6.3a4.5 4.5 0 01-.6 1.4l.9 1.4-1.4 1.4-1.4-.9c-.4.3-.9.5-1.4.6l-.3 1.6h-2l-.3-1.6a4.5 4.5 0 01-1.4-.6l-1.4.9-1.4-1.4.9-1.4a4.5 4.5 0 01-.6-1.4L1.5 9.5v-2l1.6-.3c.1-.5.3-1 .6-1.4l-.9-1.4 1.4-1.4 1.4.9c.4-.3.9-.5 1.4-.6L6.5 1.5h2z" stroke="currentColor" stroke-width="1.2" fill="none"/>
            <circle cx="8" cy="8" r="2" stroke="currentColor" stroke-width="1.2" fill="none"/>
          </svg>
        </router-link>
        <span class="nav-user">{{ authStore.user?.username }}</span>
        <button class="nav-avatar" @click="authStore.logout()" title="Sign out">
          {{ (authStore.user?.username || 'U')[0].toUpperCase() }}
        </button>
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
  --bg-primary: #0f1520;
  --bg-secondary: #151d2e;
  --bg-surface: #1c2740;
  --bg-hover: #1e2d45;
  --text-primary: #e8eaed;
  --text-secondary: #8b95a5;
  --accent: #4A90B8;
  --accent-hover: #5BA0C8;
  --accent-warm: #E07B3C;
  --accent-warm-hover: #C45A20;
  --danger: #e63946;
  --success: #5AAD58;
  --warning: #E07B3C;
  --border: #1e2940;
  --border-hover: #2a3a55;
  --sidebar-width: 300px;
  --nav-height: 48px;
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  -webkit-font-smoothing: antialiased;
}

#app-root {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

/* ── Navigation ── */
.app-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 16px;
  height: var(--nav-height);
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.nav-left, .nav-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  font-size: 16px;
  color: #fff;
  text-decoration: none;
  letter-spacing: -0.3px;
}

.nav-brand-accent {
  color: #E07B3C;
}

.nav-sep {
  width: 1px;
  height: 20px;
  background: var(--border);
}

.nav-link {
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  transition: color 0.15s, background 0.15s;
}

.nav-link:hover, .nav-link.router-link-active {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.04);
}

.nav-icon-link {
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  padding: 4px;
  border-radius: var(--radius-sm);
  transition: color 0.15s, background 0.15s;
}

.nav-icon-link:hover, .nav-icon-link.router-link-active {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.04);
}

.nav-user {
  font-size: 13px;
  color: var(--text-secondary);
}

.nav-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: none;
  background: linear-gradient(135deg, #E07B3C, #4A90B8);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: opacity 0.15s;
}

.nav-avatar:hover {
  opacity: 0.85;
}

/* ── Main ── */
.app-main {
  flex: 1;
  overflow: hidden;
}

/* ── Shared Buttons ── */
.btn {
  padding: 7px 14px;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  background: var(--accent);
  color: white;
  transition: background 0.15s;
}

.btn:hover { background: var(--accent-hover); }

.btn-warm {
  background: linear-gradient(135deg, #E07B3C, #C45A20);
}

.btn-warm:hover {
  background: linear-gradient(135deg, #e8864a, #d06828);
}

.btn-sm {
  padding: 4px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 12px;
  background: transparent;
  color: var(--text-secondary);
  transition: all 0.15s;
}

.btn-sm:hover {
  background: var(--bg-surface);
  color: var(--text-primary);
  border-color: var(--border-hover);
}

.btn-danger { background: var(--danger); }

/* ── Forms ── */
input, select, textarea {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-primary);
  font-size: 13px;
  width: 100%;
  transition: border-color 0.15s, box-shadow 0.15s;
}

input:focus, select:focus, textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(74, 144, 184, 0.12);
}

input::placeholder, textarea::placeholder {
  color: var(--text-secondary);
  opacity: 0.4;
}

label {
  display: block;
  margin-bottom: 4px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
}

.form-group {
  margin-bottom: 14px;
}

/* ── Scrollbar ── */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.14);
}
</style>
