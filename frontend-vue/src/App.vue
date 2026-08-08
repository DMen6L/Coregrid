<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { RouterView, useRoute, useRouter } from "vue-router";

import {
  AUTH_SESSION_CHANGE_EVENT,
  clearAuthToken,
  getAuthToken,
} from "./lib/authSession";

const route = useRoute();
const router = useRouter();
const authToken = ref(getAuthToken());

const listRouteNames = new Set(["products", "companies", "suppliers"]);
const stockRouteNames = new Set(["restocks", "sales"]);

const isListRouteActive = computed(() =>
  listRouteNames.has(String(route.name ?? "")),
);
const isStockRouteActive = computed(() =>
  stockRouteNames.has(String(route.name ?? "")),
);
const isAuthenticated = computed(() => Boolean(authToken.value));

function syncAuthSession() {
  authToken.value = getAuthToken();
}

async function signOut() {
  clearAuthToken();
  await router.push({ path: "/auth", query: { mode: "login" } });
}

onMounted(() => {
  window.addEventListener(AUTH_SESSION_CHANGE_EVENT, syncAuthSession);
  window.addEventListener("storage", syncAuthSession);
});

onUnmounted(() => {
  window.removeEventListener(AUTH_SESSION_CHANGE_EVENT, syncAuthSession);
  window.removeEventListener("storage", syncAuthSession);
});
</script>

<template>
  <nav class="navbar navbar-expand-lg bg-body-tertiary border-bottom">
    <div class="container-fluid">
      <RouterLink class="navbar-brand text-primary fs-4 fw-bold" to="/">
        Coregrid
      </RouterLink>

      <button
        class="navbar-toggler"
        type="button"
        data-bs-toggle="collapse"
        data-bs-target="#coregrid-vue-navbar"
        aria-controls="coregrid-vue-navbar"
        aria-expanded="false"
        aria-label="Toggle navigation"
      >
        <span class="navbar-toggler-icon"></span>
      </button>

      <div class="collapse navbar-collapse" id="coregrid-vue-navbar">
        <div class="navbar-nav nav nav-pills coregrid-navbar-tabs" role="navigation">
          <RouterLink class="nav-link" to="/dashboard">Дэшборд</RouterLink>

          <div class="nav-item dropdown">
            <button
              id="coregrid-list-dropdown"
              class="nav-link dropdown-toggle"
              :class="{ active: isListRouteActive }"
              type="button"
              data-bs-toggle="dropdown"
              :aria-current="isListRouteActive ? 'page' : undefined"
              aria-expanded="false"
            >
              Списки
            </button>
            <ul class="dropdown-menu" aria-labelledby="coregrid-list-dropdown">
              <li>
                <RouterLink class="dropdown-item" to="/products">Товары</RouterLink>
              </li>
              <li>
                <RouterLink class="dropdown-item" to="/companies">Компании</RouterLink>
              </li>
              <li>
                <RouterLink class="dropdown-item" to="/suppliers">Поставщики</RouterLink>
              </li>
            </ul>
          </div>

          <div class="nav-item dropdown">
            <button
              id="coregrid-stock-dropdown"
              class="nav-link dropdown-toggle"
              :class="{ active: isStockRouteActive }"
              type="button"
              data-bs-toggle="dropdown"
              :aria-current="isStockRouteActive ? 'page' : undefined"
              aria-expanded="false"
            >
              Движение склада
            </button>
            <ul class="dropdown-menu" aria-labelledby="coregrid-stock-dropdown">
              <li>
                <RouterLink class="dropdown-item" to="/restocks">Пополнения</RouterLink>
              </li>
              <li>
                <RouterLink class="dropdown-item" to="/sales">Продажи</RouterLink>
              </li>
            </ul>
          </div>
        </div>

        <div class="navbar-auth ms-lg-3 mt-3 mt-lg-0">
          <button
            v-if="isAuthenticated"
            class="btn btn-outline-secondary btn-sm"
            type="button"
            @click="signOut"
          >
            Выйти
          </button>
          <div v-else class="navbar-auth-actions">
            <RouterLink
              class="btn btn-outline-primary btn-sm"
              :to="{ path: '/auth', query: { mode: 'login' } }"
            >
              Войти
            </RouterLink>
            <RouterLink
              class="btn btn-primary btn-sm"
              :to="{ path: '/auth', query: { mode: 'register' } }"
            >
              Регистрация
            </RouterLink>
          </div>
        </div>
      </div>
    </div>
  </nav>

  <main class="container-fluid px-0">
    <RouterView />
  </main>
</template>
