<template>
  <div class="login-page">
    <div class="login-card">
      <h1 class="login-title">IfcGit Server</h1>
      <p class="login-subtitle">Open-source IFC version control</p>

      <div v-if="error" class="error-msg">{{ error }}</div>

      <form @submit.prevent="isRegistering ? handleRegister() : handleLogin()">
        <div class="form-group">
          <label>Username</label>
          <input v-model="username" type="text" required autocomplete="username" />
        </div>

        <div v-if="isRegistering" class="form-group">
          <label>Email</label>
          <input v-model="email" type="email" required autocomplete="email" />
        </div>

        <div class="form-group">
          <label>Password</label>
          <input v-model="password" type="password" required autocomplete="current-password" />
        </div>

        <button type="submit" class="btn" style="width: 100%" :disabled="loading">
          {{ loading ? "..." : isRegistering ? "Register" : "Login" }}
        </button>
      </form>

      <p class="toggle-link">
        <span v-if="!isRegistering">
          No account? <a href="#" @click.prevent="isRegistering = true">Register</a>
        </span>
        <span v-else>
          Have an account? <a href="#" @click.prevent="isRegistering = false">Login</a>
        </span>
      </p>
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
const loading = ref(false);
const error = ref("");

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
  align-items: center;
  justify-content: center;
  height: 100%;
  background: var(--bg-primary);
}

.login-card {
  width: 380px;
  padding: 40px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
}

.login-title {
  text-align: center;
  color: var(--accent);
  margin-bottom: 4px;
}

.login-subtitle {
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
  margin-bottom: 32px;
}

.error-msg {
  background: rgba(230, 57, 70, 0.1);
  border: 1px solid var(--danger);
  color: var(--danger);
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 13px;
  margin-bottom: 16px;
}

.toggle-link {
  text-align: center;
  margin-top: 16px;
  font-size: 13px;
  color: var(--text-secondary);
}
.toggle-link a {
  color: var(--accent);
  text-decoration: none;
}
</style>
