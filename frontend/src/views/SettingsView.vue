<template>
  <div class="settings-page">
    <div class="settings-container">
      <h1 class="settings-title">Account Settings</h1>

      <!-- Profile Section -->
      <section class="settings-section">
        <h2 class="section-title">Profile</h2>
        <div class="section-body">
          <div class="profile-grid">
            <div class="profile-item">
              <label>Username</label>
              <div class="profile-value">{{ settings.username }}</div>
            </div>
            <div class="profile-item">
              <label>Email</label>
              <div class="profile-value">{{ settings.email }}</div>
            </div>
            <div class="profile-item">
              <label>Role</label>
              <div class="profile-value">
                <span class="role-badge" :class="'role-' + settings.role">{{ settings.role }}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ERPNext Section -->
      <section class="settings-section">
        <h2 class="section-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="2" y="3" width="20" height="18" rx="2"/>
            <path d="M8 7h8M8 11h8M8 15h5"/>
          </svg>
          ERPNext Integration
        </h2>
        <div class="section-body">
          <div class="form-group">
            <label for="erpnext-url">ERPNext URL</label>
            <input id="erpnext-url" v-model="form.erpnext_url" type="url" placeholder="https://erp.company.com" />
          </div>
          <div class="form-group">
            <label for="erpnext-key">API Key</label>
            <input id="erpnext-key" v-model="form.erpnext_api_key" type="text" placeholder="API Key from ERPNext" />
          </div>
          <div class="form-group">
            <label for="erpnext-secret">API Secret</label>
            <div class="input-with-status">
              <input
                id="erpnext-secret"
                v-model="form.erpnext_api_secret"
                type="password"
                :placeholder="settings.erpnext_api_secret_set ? '••••••••  (saved)' : 'API Secret from ERPNext'"
              />
            </div>
          </div>
          <div class="section-actions">
            <button class="btn" @click="saveErpnext" :disabled="saving">
              {{ saving ? 'Saving...' : 'Save ERPNext Settings' }}
            </button>
            <button class="btn-sm" @click="testErpnext" :disabled="testingErpnext">
              {{ testingErpnext ? 'Testing...' : 'Test Connection' }}
            </button>
            <span v-if="erpnextStatus" class="status-msg" :class="erpnextStatus.success ? 'status-ok' : 'status-err'">
              {{ erpnextStatus.success ? 'Connected as ' + erpnextStatus.user : erpnextStatus.error }}
            </span>
          </div>
        </div>
      </section>

      <!-- Nextcloud Section -->
      <section class="settings-section">
        <h2 class="section-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2z"/>
            <path d="M8 14a3 3 0 106 0 3 3 0 00-6 0zM14 10a3 3 0 106 0 3 3 0 00-6 0zM4 10a3 3 0 106 0 3 3 0 00-6 0z"/>
          </svg>
          Nextcloud Integration
        </h2>
        <div class="section-body">
          <div class="form-group">
            <label for="nc-url">Nextcloud URL</label>
            <input id="nc-url" v-model="form.nextcloud_url" type="url" placeholder="https://cloud.company.com" />
          </div>
          <div class="form-group">
            <label for="nc-user">Username</label>
            <input id="nc-user" v-model="form.nextcloud_username" type="text" placeholder="Nextcloud username" />
          </div>
          <div class="form-group">
            <label for="nc-pass">Password / App Token</label>
            <input
              id="nc-pass"
              v-model="form.nextcloud_password"
              type="password"
              :placeholder="settings.nextcloud_password_set ? '••••••••  (saved)' : 'Password or app token'"
            />
          </div>
          <div class="section-actions">
            <button class="btn" @click="saveNextcloud" :disabled="saving">
              {{ saving ? 'Saving...' : 'Save Nextcloud Settings' }}
            </button>
            <button class="btn-sm" @click="testNextcloud" :disabled="testingNextcloud">
              {{ testingNextcloud ? 'Testing...' : 'Test Connection' }}
            </button>
            <span v-if="nextcloudStatus" class="status-msg" :class="nextcloudStatus.success ? 'status-ok' : 'status-err'">
              {{ nextcloudStatus.success ? 'Connected as ' + nextcloudStatus.user : nextcloudStatus.error }}
            </span>
          </div>
        </div>
      </section>

      <!-- Error banner -->
      <div v-if="error" class="error-banner">{{ error }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from "vue";
import { settingsApi } from "@/services/api";

const settings = reactive({
  username: "",
  email: "",
  role: "",
  erpnext_url: null as string | null,
  erpnext_api_key: null as string | null,
  erpnext_api_secret_set: false,
  nextcloud_url: null as string | null,
  nextcloud_username: null as string | null,
  nextcloud_password_set: false,
});

const form = reactive({
  erpnext_url: "",
  erpnext_api_key: "",
  erpnext_api_secret: "",
  nextcloud_url: "",
  nextcloud_username: "",
  nextcloud_password: "",
});

const saving = ref(false);
const testingErpnext = ref(false);
const testingNextcloud = ref(false);
const erpnextStatus = ref<{ success: boolean; user?: string; error?: string } | null>(null);
const nextcloudStatus = ref<{ success: boolean; user?: string; error?: string } | null>(null);
const error = ref("");

async function loadSettings() {
  try {
    const { data } = await settingsApi.get();
    Object.assign(settings, data);
    form.erpnext_url = data.erpnext_url || "";
    form.erpnext_api_key = data.erpnext_api_key || "";
    form.erpnext_api_secret = "";
    form.nextcloud_url = data.nextcloud_url || "";
    form.nextcloud_username = data.nextcloud_username || "";
    form.nextcloud_password = "";
  } catch (e: any) {
    error.value = e.response?.data?.detail || "Failed to load settings";
  }
}

async function saveErpnext() {
  saving.value = true;
  error.value = "";
  try {
    const payload: any = {
      erpnext_url: form.erpnext_url,
      erpnext_api_key: form.erpnext_api_key,
    };
    if (form.erpnext_api_secret) {
      payload.erpnext_api_secret = form.erpnext_api_secret;
    }
    const { data } = await settingsApi.update(payload);
    Object.assign(settings, data);
    form.erpnext_api_secret = "";
  } catch (e: any) {
    error.value = e.response?.data?.detail || "Failed to save";
  } finally {
    saving.value = false;
  }
}

async function saveNextcloud() {
  saving.value = true;
  error.value = "";
  try {
    const payload: any = {
      nextcloud_url: form.nextcloud_url,
      nextcloud_username: form.nextcloud_username,
    };
    if (form.nextcloud_password) {
      payload.nextcloud_password = form.nextcloud_password;
    }
    const { data } = await settingsApi.update(payload);
    Object.assign(settings, data);
    form.nextcloud_password = "";
  } catch (e: any) {
    error.value = e.response?.data?.detail || "Failed to save";
  } finally {
    saving.value = false;
  }
}

async function testErpnext() {
  testingErpnext.value = true;
  erpnextStatus.value = null;
  try {
    const { data } = await settingsApi.testErpnext();
    erpnextStatus.value = data;
  } catch (e: any) {
    erpnextStatus.value = { success: false, error: e.response?.data?.detail || "Test failed" };
  } finally {
    testingErpnext.value = false;
  }
}

async function testNextcloud() {
  testingNextcloud.value = true;
  nextcloudStatus.value = null;
  try {
    const { data } = await settingsApi.testNextcloud();
    nextcloudStatus.value = data;
  } catch (e: any) {
    nextcloudStatus.value = { success: false, error: e.response?.data?.detail || "Test failed" };
  } finally {
    testingNextcloud.value = false;
  }
}

onMounted(loadSettings);
</script>

<style scoped>
.settings-page {
  padding: 32px;
  overflow-y: auto;
  height: 100%;
}

.settings-container {
  max-width: 640px;
  margin: 0 auto;
}

.settings-title {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 28px;
  color: var(--text-primary);
}

.settings-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  margin-bottom: 20px;
  overflow: hidden;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-body {
  padding: 20px;
}

.profile-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 16px;
}

.profile-item label {
  margin-bottom: 4px;
}

.profile-value {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
}

.role-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.role-admin {
  background: rgba(224, 123, 60, 0.15);
  color: var(--accent-warm);
}

.role-editor {
  background: rgba(74, 144, 184, 0.15);
  color: var(--accent);
}

.role-viewer {
  background: rgba(139, 149, 165, 0.12);
  color: var(--text-secondary);
}

.section-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.status-msg {
  font-size: 12px;
  font-weight: 500;
}

.status-ok {
  color: var(--success);
}

.status-err {
  color: var(--danger);
}

.error-banner {
  background: rgba(230, 57, 70, 0.1);
  border: 1px solid rgba(230, 57, 70, 0.3);
  color: var(--danger);
  padding: 10px 16px;
  border-radius: var(--radius-md);
  font-size: 13px;
}

.input-with-status {
  position: relative;
}

@media (max-width: 600px) {
  .settings-page {
    padding: 16px;
  }

  .profile-grid {
    grid-template-columns: 1fr;
  }
}
</style>
