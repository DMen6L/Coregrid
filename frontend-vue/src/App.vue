<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from "vue";
import { useQueryClient } from "@tanstack/vue-query";
import { RouterView, useRoute, useRouter } from "vue-router";

import { ApiRequestError, createWorkspace, getWorkspaces } from "./lib/api";
import {
  AUTH_SESSION_CHANGE_EVENT,
  clearAuthToken,
  getAuthToken,
} from "./lib/authSession";
import {
  activeWorkspace,
  clearWorkspaceSession,
  selectInitialWorkspace,
  setActiveWorkspaceId,
  setWorkspaces,
  syncActiveWorkspaceFromStorage,
  workspaces,
} from "./lib/workspaceSession";
import type { WorkspaceResponse } from "./types/api";

const route = useRoute();
const router = useRouter();
const queryClient = useQueryClient();
const authToken = ref(getAuthToken());
const workspaceCreateFormElement = ref<HTMLFormElement | null>(null);
const isWorkspaceLoading = ref(false);
const isWorkspaceCreateModalOpen = ref(false);
const isWorkspaceCreateSubmitting = ref(false);
const workspaceError = ref("");
const workspaceCreateError = ref("");
const workspaceCreateForm = reactive({
  name: "",
});

const listRouteNames = new Set(["products", "companies", "suppliers"]);
const stockRouteNames = new Set(["restocks", "sales"]);

const isListRouteActive = computed(() =>
  listRouteNames.has(String(route.name ?? "")),
);
const isStockRouteActive = computed(() =>
  stockRouteNames.has(String(route.name ?? "")),
);
const isAuthenticated = computed(() => Boolean(authToken.value));
const requiresWorkspace = computed(() => Boolean(route.meta.requiresWorkspace));
const shouldShowWorkspaceGate = computed(() => (
  isAuthenticated.value
    && requiresWorkspace.value
    && (!activeWorkspace.value || isWorkspaceLoading.value || Boolean(workspaceError.value))
));
const workspaceCreateTitle = computed(() => (
  workspaces.value.length === 0
    ? "Создать первое рабочее пространство"
    : "Создать рабочее пространство"
));

function syncAuthSession() {
  const previousToken = authToken.value;

  authToken.value = getAuthToken();

  if (!authToken.value) {
    clearWorkspaceSession();
    queryClient.clear();
    return;
  }

  if (authToken.value !== previousToken || workspaces.value.length === 0) {
    void loadWorkspaces();
  }
}

async function signOut() {
  clearAuthToken();
  queryClient.clear();
  await router.push({ path: "/auth", query: { mode: "login" } });
}

async function loadWorkspaces() {
  if (!getAuthToken()) {
    clearWorkspaceSession();
    return;
  }

  isWorkspaceLoading.value = true;
  workspaceError.value = "";

  try {
    const nextWorkspaces = await getWorkspaces();
    setWorkspaces(nextWorkspaces);
    setActiveWorkspaceId(selectInitialWorkspace(nextWorkspaces));
  } catch (error) {
    setWorkspaces([]);
    setActiveWorkspaceId(null);
    workspaceError.value = getWorkspaceErrorMessage(error);
  } finally {
    isWorkspaceLoading.value = false;
  }
}

function selectWorkspace(workspace: WorkspaceResponse) {
  if (activeWorkspace.value?.id === workspace.id) {
    return;
  }

  setActiveWorkspaceId(workspace.id);
  void queryClient.invalidateQueries();
}

function openWorkspaceCreateModal() {
  workspaceCreateForm.name = "";
  workspaceCreateError.value = "";
  isWorkspaceCreateModalOpen.value = true;
}

function closeWorkspaceCreateModal() {
  if (isWorkspaceCreateSubmitting.value) {
    return;
  }

  isWorkspaceCreateModalOpen.value = false;
}

async function submitWorkspaceCreate() {
  workspaceCreateError.value = "";

  if (!workspaceCreateFormElement.value?.reportValidity()) {
    return;
  }

  isWorkspaceCreateSubmitting.value = true;

  try {
    const workspace = await createWorkspace({
      name: normalizeText(workspaceCreateForm.name),
    });
    const nextWorkspaces = [
      ...workspaces.value.filter((item) => item.id !== workspace.id),
      workspace,
    ].sort((left, right) => left.name.localeCompare(right.name));

    setWorkspaces(nextWorkspaces);
    setActiveWorkspaceId(workspace.id);
    workspaceCreateForm.name = "";
    isWorkspaceCreateModalOpen.value = false;
    workspaceError.value = "";
    await queryClient.invalidateQueries();
  } catch (error) {
    workspaceCreateError.value = getWorkspaceErrorMessage(error);
  } finally {
    isWorkspaceCreateSubmitting.value = false;
  }
}

function handleStorageEvent() {
  syncActiveWorkspaceFromStorage();
  syncAuthSession();
}

function normalizeText(value: string) {
  return String(value || "").trim();
}

function getWorkspaceErrorMessage(error: unknown) {
  if (!(error instanceof ApiRequestError)) {
    return "Не удалось загрузить рабочие пространства.";
  }

  if (error.status === 401) {
    return "Сессия истекла. Войдите снова.";
  }

  if (error.status === 409) {
    return "Рабочее пространство с таким названием уже существует.";
  }

  if (error.status === 422) {
    return "Проверьте название рабочего пространства.";
  }

  const detail = getErrorDetail(error.data);

  return detail || "Не удалось выполнить запрос.";
}

function getErrorDetail(data: unknown) {
  if (!data || typeof data !== "object" || !("detail" in data)) {
    return "";
  }

  const detail = (data as { detail?: unknown }).detail;

  return typeof detail === "string" ? detail : "";
}

onMounted(() => {
  window.addEventListener(AUTH_SESSION_CHANGE_EVENT, syncAuthSession);
  window.addEventListener("storage", handleStorageEvent);

  if (authToken.value) {
    void loadWorkspaces();
  }
});

onUnmounted(() => {
  window.removeEventListener(AUTH_SESSION_CHANGE_EVENT, syncAuthSession);
  window.removeEventListener("storage", handleStorageEvent);
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

        <div class="navbar-session ms-lg-auto mt-3 mt-lg-0">
          <div v-if="isAuthenticated" class="dropdown navbar-workspace">
            <button
              id="coregrid-workspace-dropdown"
              class="btn btn-outline-secondary btn-sm dropdown-toggle workspace-selector-button"
              type="button"
              data-bs-toggle="dropdown"
              aria-expanded="false"
            >
              <span class="workspace-selector-name">
                {{ activeWorkspace?.name || "Рабочее пространство" }}
              </span>
              <span v-if="activeWorkspace" class="workspace-selector-role">
                {{ activeWorkspace.role }}
              </span>
            </button>
            <ul class="dropdown-menu dropdown-menu-lg-end" aria-labelledby="coregrid-workspace-dropdown">
              <li v-if="isWorkspaceLoading">
                <span class="dropdown-item-text text-secondary">Загрузка...</span>
              </li>
              <li v-for="workspace in workspaces" :key="workspace.id">
                <button
                  class="dropdown-item"
                  :class="{ active: activeWorkspace?.id === workspace.id }"
                  type="button"
                  @click="selectWorkspace(workspace)"
                >
                  <span>{{ workspace.name }}</span>
                  <span class="workspace-dropdown-role">{{ workspace.role }}</span>
                </button>
              </li>
              <li v-if="workspaceError">
                <span class="dropdown-item-text text-danger">{{ workspaceError }}</span>
              </li>
              <li><hr class="dropdown-divider"></li>
              <li>
                <button class="dropdown-item" type="button" @click="openWorkspaceCreateModal">
                  Создать рабочее пространство
                </button>
              </li>
              <li v-if="workspaceError">
                <button class="dropdown-item" type="button" @click="loadWorkspaces">
                  Повторить загрузку
                </button>
              </li>
            </ul>
          </div>

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
    <section v-if="shouldShowWorkspaceGate" class="workspace-gate">
      <div class="workspace-gate-panel">
        <div v-if="isWorkspaceLoading" class="alert alert-light border mb-0" role="status">
          Загрузка рабочих пространств...
        </div>
        <template v-else>
          <p class="workspace-gate-kicker mb-1">Coregrid</p>
          <h1 class="fs-4 mb-2">
            {{ workspaceError ? "Рабочие пространства недоступны" : "Создайте рабочее пространство" }}
          </h1>
          <p class="text-secondary mb-3">
            {{
              workspaceError
                ? workspaceError
                : "Рабочие процессы Coregrid привязаны к бизнесу. Создайте рабочее пространство, чтобы открыть списки, складские движения и настройки товаров."
            }}
          </p>
          <div class="workspace-gate-actions">
            <button class="btn btn-primary" type="button" @click="openWorkspaceCreateModal">
              Создать рабочее пространство
            </button>
            <button
              v-if="workspaceError"
              class="btn btn-outline-secondary"
              type="button"
              @click="loadWorkspaces"
            >
              Повторить
            </button>
          </div>
        </template>
      </div>
    </section>
    <RouterView v-else />
  </main>

  <div
    v-if="isWorkspaceCreateModalOpen"
    class="modal fade show d-block"
    tabindex="-1"
    role="dialog"
    aria-modal="true"
    :aria-labelledby="'workspace-create-title'"
  >
    <div class="modal-dialog modal-dialog-centered">
      <form
        ref="workspaceCreateFormElement"
        class="modal-content"
        @submit.prevent="submitWorkspaceCreate"
      >
        <div class="modal-header">
          <h2 id="workspace-create-title" class="modal-title fs-5">{{ workspaceCreateTitle }}</h2>
          <button
            class="btn-close"
            type="button"
            aria-label="Закрыть"
            :disabled="isWorkspaceCreateSubmitting"
            @click="closeWorkspaceCreateModal"
          ></button>
        </div>
        <div class="modal-body">
          <label class="form-label" for="workspace-name-input">Название</label>
          <input
            id="workspace-name-input"
            v-model.trim="workspaceCreateForm.name"
            class="form-control"
            name="workspace_name"
            type="text"
            maxlength="255"
            required
          >
          <div v-if="workspaceCreateError" class="alert alert-danger mt-3 mb-0" role="alert">
            {{ workspaceCreateError }}
          </div>
        </div>
        <div class="modal-footer">
          <button
            class="btn btn-outline-secondary"
            type="button"
            :disabled="isWorkspaceCreateSubmitting"
            @click="closeWorkspaceCreateModal"
          >
            Отмена
          </button>
          <button class="btn btn-primary" type="submit" :disabled="isWorkspaceCreateSubmitting">
            {{ isWorkspaceCreateSubmitting ? "Создание..." : "Создать" }}
          </button>
        </div>
      </form>
    </div>
  </div>
  <div v-if="isWorkspaceCreateModalOpen" class="modal-backdrop fade show"></div>
</template>
