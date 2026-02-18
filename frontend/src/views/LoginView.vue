<template>
  <div class="login-page">
    <!-- Left: product showcase -->
    <div class="login-hero">
      <div class="hero-bg-grid"></div>
      <div class="hero-content">
        <div class="hero-brand">
          <div class="brand-logo">
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
              <path d="M20 4L4 12v16l16 8 16-8V12L20 4z" stroke="url(#logo-grad)" stroke-width="2" fill="none"/>
              <path d="M20 4v32M4 12l16 8 16-8" stroke="url(#logo-grad)" stroke-width="1.5" fill="none" opacity="0.5"/>
              <defs><linearGradient id="logo-grad" x1="4" y1="4" x2="36" y2="36"><stop stop-color="#E07B3C"/><stop offset="1" stop-color="#4A90B8"/></linearGradient></defs>
            </svg>
          </div>
          <div>
            <span class="brand-name">Open<span class="brand-accent">AEC</span></span>
            <span class="brand-sub">Cloud Platform</span>
          </div>
        </div>

        <h1 class="hero-title">The open-source<br/>BIM platform</h1>
        <p class="hero-tagline">Version control, collaboration, and lifecycle management for the built environment. Built on open standards.</p>

        <div class="product-modules">
          <div class="module-grid">
            <div class="module-chip" v-for="mod in modules" :key="mod.id">
              <span class="module-icon" :style="{ color: mod.color }">{{ mod.icon }}</span>
              <div class="module-info">
                <span class="module-name">{{ mod.name }}</span>
                <span class="module-desc">{{ mod.desc }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="hero-footer">
        <div class="hero-footer-left">
          <span class="footer-badge">IFC 4x3</span>
          <span class="footer-badge">openBIM</span>
          <span class="footer-badge">BCF 3.0</span>
          <span class="footer-badge">Git</span>
        </div>
        <span class="footer-org">OpenAEC Foundation</span>
      </div>
    </div>

    <!-- Right: auth form -->
    <div class="login-form-panel">
      <div class="form-container">
        <div class="form-mobile-brand">
          <svg width="28" height="28" viewBox="0 0 40 40" fill="none">
            <path d="M20 4L4 12v16l16 8 16-8V12L20 4z" stroke="url(#logo-grad-m)" stroke-width="2.5" fill="none"/>
            <defs><linearGradient id="logo-grad-m" x1="4" y1="4" x2="36" y2="36"><stop stop-color="#E07B3C"/><stop offset="1" stop-color="#4A90B8"/></linearGradient></defs>
          </svg>
          <span class="brand-name-sm">Open<span class="brand-accent">AEC</span></span>
        </div>

        <div class="form-header">
          <h2>{{ isRegistering ? 'Create your account' : 'Sign in' }}</h2>
          <p>{{ isRegistering ? 'Start collaborating on BIM projects' : 'Access your projects and models' }}</p>
        </div>

        <Transition name="fade" mode="out-in">
          <div v-if="error" class="error-banner" :key="error">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.5"/>
              <path d="M8 4.5v4M8 10.5v.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
            <span>{{ error }}</span>
          </div>
        </Transition>

        <form @submit.prevent="isRegistering ? handleRegister() : handleLogin()">
          <div class="input-group">
            <label for="username">Username</label>
            <div class="input-wrapper">
              <svg class="input-icon" width="18" height="18" viewBox="0 0 18 18" fill="none">
                <circle cx="9" cy="6" r="3.5" stroke="currentColor" stroke-width="1.4"/>
                <path d="M2.5 16.5c0-3.6 2.9-6.5 6.5-6.5s6.5 2.9 6.5 6.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
              </svg>
              <input id="username" v-model="username" type="text" placeholder="your username" required autocomplete="username" />
            </div>
          </div>

          <Transition name="slide">
            <div v-if="isRegistering" class="input-group">
              <label for="email">Email</label>
              <div class="input-wrapper">
                <svg class="input-icon" width="18" height="18" viewBox="0 0 18 18" fill="none">
                  <rect x="2" y="4" width="14" height="10" rx="2" stroke="currentColor" stroke-width="1.4" fill="none"/>
                  <path d="M2 6l7 4 7-4" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
                </svg>
                <input id="email" v-model="email" type="email" placeholder="you@company.com" required autocomplete="email" />
              </div>
            </div>
          </Transition>

          <div class="input-group">
            <label for="password">Password</label>
            <div class="input-wrapper">
              <svg class="input-icon" width="18" height="18" viewBox="0 0 18 18" fill="none">
                <rect x="3" y="8" width="12" height="8" rx="2" stroke="currentColor" stroke-width="1.4" fill="none"/>
                <path d="M6 8V5.5a3 3 0 016 0V8" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
              </svg>
              <input id="password" v-model="password" :type="showPassword ? 'text' : 'password'" placeholder="your password" required :autocomplete="isRegistering ? 'new-password' : 'current-password'" />
              <button type="button" class="toggle-pw" @click="showPassword = !showPassword" tabindex="-1">
                <svg v-if="!showPassword" width="16" height="16" viewBox="0 0 18 18" fill="none"><path d="M1.5 9s3-5.5 7.5-5.5S16.5 9 16.5 9s-3 5.5-7.5 5.5S1.5 9 1.5 9z" stroke="currentColor" stroke-width="1.4"/><circle cx="9" cy="9" r="2.5" stroke="currentColor" stroke-width="1.4"/></svg>
                <svg v-else width="16" height="16" viewBox="0 0 18 18" fill="none"><path d="M1.5 9s3-5.5 7.5-5.5S16.5 9 16.5 9s-3 5.5-7.5 5.5S1.5 9 1.5 9z" stroke="currentColor" stroke-width="1.4"/><line x1="3" y1="3" x2="15" y2="15" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>
              </button>
            </div>
          </div>

          <button type="submit" class="submit-btn" :disabled="loading">
            <svg v-if="loading" class="spinner" width="18" height="18" viewBox="0 0 18 18"><circle cx="9" cy="9" r="7" stroke="currentColor" stroke-width="2" stroke-dasharray="30 14" stroke-linecap="round" fill="none"/></svg>
            <span v-else>{{ isRegistering ? 'Create account' : 'Sign in' }}</span>
          </button>
        </form>

        <div class="form-divider"><span>or</span></div>

        <button class="alt-btn" @click="toggleMode">
          {{ isRegistering ? 'Sign in to existing account' : 'Create a new account' }}
        </button>

        <p class="form-footer-text">
          By continuing, you agree to the OpenAEC
          <a href="#">Terms of Service</a> and <a href="#">Privacy Policy</a>.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useAuthStore } from "@/stores/auth";

const authStore = useAuthStore();

const username = ref("");
const email = ref("");
const password = ref("");
const isRegistering = ref(false);
const showPassword = ref(false);
const loading = ref(false);
const error = ref("");

const modules = [
  { id: "vault", name: "Vault", desc: "Version control", icon: "\u{1F512}", color: "#4A90B8" },
  { id: "view", name: "View", desc: "3D/2D viewer", icon: "\u{1F441}", color: "#6BB8D4" },
  { id: "clash", name: "Clash", desc: "Clash detection", icon: "\u{26A1}", color: "#E07B3C" },
  { id: "docs", name: "Docs", desc: "Documents", icon: "\u{1F4C4}", color: "#5AAD58" },
  { id: "issues", name: "Issues", desc: "BCF management", icon: "\u{1F4CB}", color: "#C45A20" },
  { id: "takeoff", name: "Takeoff", desc: "Quantities", icon: "\u{1F4D0}", color: "#8B5CF6" },
  { id: "facility", name: "Facility", desc: "FM & operations", icon: "\u{1F3E2}", color: "#06B6D4" },
  { id: "graph", name: "Graph", desc: "Neo4J analytics", icon: "\u{1F578}", color: "#EC4899" },
];

function toggleMode() {
  isRegistering.value = !isRegistering.value;
  error.value = "";
}

async function handleLogin() {
  error.value = "";
  loading.value = true;
  try {
    await authStore.login(username.value, password.value);
  } catch (e: any) {
    error.value = e.response?.data?.detail || "Login failed";
  } finally {
    loading.value = false;
  }
}

async function handleRegister() {
  error.value = "";
  loading.value = true;
  try {
    await authStore.register(username.value, email.value, password.value);
  } catch (e: any) {
    error.value = e.response?.data?.detail || "Registration failed";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  height: 100%;
  background: var(--bg-primary);
}

/* ── Hero panel ── */
.login-hero {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  width: 52%;
  padding: 40px 48px;
  background: linear-gradient(145deg, #0c1929 0%, #111d32 40%, #162444 100%);
  position: relative;
  overflow: hidden;
}

.hero-bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(74, 144, 184, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(74, 144, 184, 0.04) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: radial-gradient(ellipse 70% 70% at 30% 50%, black, transparent);
}

.hero-content {
  position: relative;
  z-index: 1;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.hero-brand {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 48px;
}

.brand-logo {
  display: flex;
}

.brand-name {
  font-size: 20px;
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.3px;
  display: block;
  line-height: 1.2;
}

.brand-accent {
  color: #E07B3C;
}

.brand-sub {
  font-size: 11px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 1.5px;
  display: block;
}

.hero-title {
  font-size: 40px;
  font-weight: 700;
  color: #fff;
  letter-spacing: -1px;
  line-height: 1.15;
  margin-bottom: 16px;
}

.hero-tagline {
  font-size: 15px;
  color: var(--text-secondary);
  line-height: 1.7;
  max-width: 420px;
  margin-bottom: 40px;
}

/* ── Module chips ── */
.product-modules {
  max-width: 480px;
}

.module-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.module-chip {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  transition: background 0.2s, border-color 0.2s;
}

.module-chip:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.1);
}

.module-icon {
  font-size: 18px;
  width: 28px;
  text-align: center;
  flex-shrink: 0;
}

.module-name {
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  display: block;
  line-height: 1.2;
}

.module-desc {
  font-size: 11px;
  color: var(--text-secondary);
  display: block;
}

/* ── Hero footer ── */
.hero-footer {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.hero-footer-left {
  display: flex;
  gap: 6px;
}

.footer-badge {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 3px 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-secondary);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.footer-org {
  font-size: 12px;
  color: var(--text-secondary);
  opacity: 0.5;
}

/* ── Form panel ── */
.login-form-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  background: var(--bg-primary);
}

.form-container {
  width: 100%;
  max-width: 380px;
}

.form-mobile-brand {
  display: none;
  align-items: center;
  gap: 10px;
  margin-bottom: 32px;
}

.brand-name-sm {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
}

.form-header {
  margin-bottom: 28px;
}

.form-header h2 {
  font-size: 22px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 6px;
}

.form-header p {
  font-size: 14px;
  color: var(--text-secondary);
}

/* ── Error ── */
.error-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: rgba(230, 57, 70, 0.08);
  border: 1px solid rgba(230, 57, 70, 0.25);
  border-radius: 8px;
  color: #ff6b6b;
  font-size: 13px;
  margin-bottom: 20px;
}

.error-banner svg { flex-shrink: 0; }

/* ── Inputs ── */
.input-group {
  margin-bottom: 18px;
}

.input-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: 12px;
  color: var(--text-secondary);
  pointer-events: none;
  opacity: 0.4;
}

.input-wrapper input {
  width: 100%;
  padding: 10px 12px 10px 40px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 14px;
  transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
}

.input-wrapper input:focus {
  outline: none;
  border-color: #4A90B8;
  box-shadow: 0 0 0 3px rgba(74, 144, 184, 0.12);
  background: rgba(255, 255, 255, 0.06);
}

.input-wrapper input::placeholder {
  color: var(--text-secondary);
  opacity: 0.35;
}

.toggle-pw {
  position: absolute;
  right: 10px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-secondary);
  opacity: 0.4;
  padding: 4px;
  display: flex;
  transition: opacity 0.2s;
}

.toggle-pw:hover { opacity: 0.7; }

/* ── Submit ── */
.submit-btn {
  width: 100%;
  padding: 11px 16px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  background: linear-gradient(135deg, #E07B3C, #C45A20);
  color: #fff;
  transition: transform 0.1s, box-shadow 0.2s, opacity 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  margin-top: 4px;
}

.submit-btn:hover:not(:disabled) {
  box-shadow: 0 4px 16px rgba(224, 123, 60, 0.3);
  transform: translateY(-1px);
}

.submit-btn:active:not(:disabled) { transform: scale(0.98); }
.submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.spinner { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Divider ── */
.form-divider {
  display: flex;
  align-items: center;
  margin: 20px 0;
}

.form-divider::before,
.form-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}

.form-divider span {
  padding: 0 14px;
  font-size: 12px;
  color: var(--text-secondary);
  opacity: 0.5;
}

/* ── Alt button ── */
.alt-btn {
  width: 100%;
  padding: 10px 16px;
  border: 1px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  background: transparent;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.alt-btn:hover {
  border-color: #4A90B8;
  color: var(--text-primary);
  background: rgba(74, 144, 184, 0.06);
}

/* ── Footer text ── */
.form-footer-text {
  margin-top: 24px;
  font-size: 11px;
  color: var(--text-secondary);
  opacity: 0.5;
  text-align: center;
  line-height: 1.6;
}

.form-footer-text a {
  color: #4A90B8;
  text-decoration: none;
}

.form-footer-text a:hover {
  text-decoration: underline;
}

/* ── Transitions ── */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-enter-active { transition: all 0.3s ease; }
.slide-leave-active { transition: all 0.2s ease; }
.slide-enter-from { opacity: 0; transform: translateY(-8px); max-height: 0; }
.slide-enter-to { max-height: 80px; }
.slide-leave-to { opacity: 0; transform: translateY(-8px); max-height: 0; }

/* ── Responsive ── */
@media (max-width: 960px) {
  .login-hero { display: none; }
  .form-mobile-brand { display: flex; }
  .login-form-panel { padding: 32px 24px; }
}
</style>
