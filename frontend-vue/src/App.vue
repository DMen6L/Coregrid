<script setup lang="ts">
import { computed, ref } from "vue";
import { RouterView, useRoute } from "vue-router";

import ApiBaseSelector from "./components/ApiBaseSelector.vue";

const appMessage = ref("");
const route = useRoute();

const listRouteNames = new Set(["products", "companies", "suppliers"]);
const stockRouteNames = new Set(["restocks", "sales"]);

const isListRouteActive = computed(() =>
  listRouteNames.has(String(route.name ?? "")),
);
const isStockRouteActive = computed(() =>
  stockRouteNames.has(String(route.name ?? "")),
);

function handleApiBaseChange(baseApi: string) {
  appMessage.value = `API: ${baseApi}`;
}
</script>

<template>
  <nav class="navbar navbar-expand-lg bg-body-tertiary border-bottom">
    <div class="container-fluid">
      <RouterLink class="navbar-brand text-primary fs-4 fw-bold" to="/dashboard">
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

        <ApiBaseSelector @api-base-change="handleApiBaseChange" />
      </div>
    </div>
  </nav>

  <main class="container-fluid px-0">
    <div class="container-fluid px-4 pt-4">
      <div
        class="alert alert-info mb-0"
        :class="{ 'd-none': !appMessage }"
        role="status"
      >
        {{ appMessage }}
      </div>
    </div>

    <RouterView />
  </main>
</template>
