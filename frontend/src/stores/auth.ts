import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { authApi } from "@/services/api";
import router from "@/router";

interface User {
  id: string;
  username: string;
  email: string;
  role: string;
}

export const useAuthStore = defineStore("auth", () => {
  const token = ref<string | null>(localStorage.getItem("token"));
  const user = ref<User | null>(
    localStorage.getItem("user")
      ? JSON.parse(localStorage.getItem("user")!)
      : null
  );

  const isAuthenticated = computed(() => !!token.value);

  async function login(username: string, password: string) {
    const res = await authApi.login({ username, password });
    token.value = res.data.access_token;
    localStorage.setItem("token", res.data.access_token);

    // Fetch user info
    const meRes = await authApi.me();
    user.value = meRes.data;
    localStorage.setItem("user", JSON.stringify(meRes.data));

    router.push("/projects");
  }

  async function register(username: string, email: string, password: string) {
    await authApi.register({ username, email, password });
    await login(username, password);
  }

  function logout() {
    token.value = null;
    user.value = null;
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    router.push("/login");
  }

  return { token, user, isAuthenticated, login, register, logout };
});
