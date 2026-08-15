<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { RouterView, useRoute, useRouter } from "vue-router";

import {
  ApiRequestError,
  createWorkspace,
  getMe,
} from "./lib/api";
import {
  AUTH_SESSION_CHANGE_EVENT,
  clearAuthToken,
  getAuthToken,
} from "./lib/authSession";
import { closeOpenDropdowns } from "./lib/dropdowns";
import { canManageWorkspace } from "./lib/permissions";
import {
  activeWorkspace,
  clearWorkspaceSession,
  selectInitialWorkspace,
  setActiveWorkspaceId,
  setWorkspaces,
  syncActiveWorkspaceFromStorage,
  workspaces,
} from "./lib/workspaceSession";
import type { MeResponse, UserResponse, WorkspaceResponse } from "./types/api";

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
const isMembersRouteActive = computed(() => String(route.name ?? "") === "members");
const isMembersListRouteActive = computed(() => (
  isMembersRouteActive.value && route.query.tab !== "invitations"
));
const isMembersInvitationsRouteActive = computed(() => (
  isMembersRouteActive.value && route.query.tab === "invitations"
));
const isAuditLogsRouteActive = computed(() => String(route.name ?? "") === "audit-logs");
const isWorkspaceAdminRouteActive = computed(() => (
  isMembersRouteActive.value || isAuditLogsRouteActive.value
));
const isAccountRouteActive = computed(() => String(route.name ?? "") === "me");
const isAuthenticated = computed(() => Boolean(authToken.value));
const meQuery = useQuery({
  queryKey: ["me"],
  queryFn: getMe,
  enabled: false,
});
const requiresWorkspace = computed(() => Boolean(route.meta.requiresWorkspace));
const shouldShowWorkspaceGate = computed(() => (
  hasVerifiedAccount.value
    && requiresWorkspace.value
    && (!activeWorkspace.value || isWorkspaceLoading.value || Boolean(workspaceError.value))
));
const hasVerifiedAccount = computed(() => Boolean(isAuthenticated.value && currentUser.value));
const canManageCurrentWorkspace = computed(() => (
  canManageWorkspace(activeWorkspace.value?.role)
));
const currentUser = computed(() => meQuery.data.value?.user || null);
const accountDisplayName = computed(() => getAccountDisplayName(currentUser.value));
const accountInitials = computed(() => getAccountInitials(currentUser.value));
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

  if (authToken.value !== previousToken || !meQuery.data.value) {
    void refreshMeOverview();
  }
}

async function refreshMeOverview(preferredWorkspaceId: number | null = null) {
  if (!getAuthToken()) {
    clearWorkspaceSession();
    return;
  }

  const nextPreferredWorkspaceId = typeof preferredWorkspaceId === "number"
    ? preferredWorkspaceId
    : null;

  isWorkspaceLoading.value = true;
  workspaceError.value = "";

  try {
    const result = await meQuery.refetch();

    if (result.error) {
      throw result.error;
    }

    if (result.data) {
      applyUserOverview(result.data, nextPreferredWorkspaceId);
    }
  } catch (error) {
    if (error instanceof ApiRequestError && error.status === 401) {
      await resetInvalidSession();
      return;
    }

    setWorkspaces([]);
    setActiveWorkspaceId(null);
    workspaceError.value = getWorkspaceErrorMessage(error);
  } finally {
    isWorkspaceLoading.value = false;
  }
}

function applyUserOverview(
  overview: MeResponse,
  preferredWorkspaceId: number | null = null,
) {
  const preferredWorkspaceExists = Boolean(
    preferredWorkspaceId
      && overview.workspaces.some((workspace) => workspace.id === preferredWorkspaceId),
  );

  setWorkspaces(overview.workspaces);
  setActiveWorkspaceId(
    preferredWorkspaceExists
      ? preferredWorkspaceId
      : selectInitialWorkspace(overview.workspaces),
  );
  workspaceError.value = "";
}

function openWorkspaceCreateModal() {
  closeOpenDropdowns();
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

    upsertWorkspace(workspace);
    setActiveWorkspaceId(workspace.id);
    workspaceCreateForm.name = "";
    isWorkspaceCreateModalOpen.value = false;
    workspaceError.value = "";
    await refreshMeOverview(workspace.id);
    await queryClient.invalidateQueries();
  } catch (error) {
    workspaceCreateError.value = getWorkspaceErrorMessage(error);
  } finally {
    isWorkspaceCreateSubmitting.value = false;
  }
}

function openMembersSection(tab: "members" | "invitations") {
  closeOpenDropdowns();
  void router.push({ name: "members", query: { tab } });
}

async function signOut() {
  closeOpenDropdowns();
  clearAuthToken();
  clearWorkspaceSession();
  queryClient.clear();

  if (route.name !== "home") {
    await router.push({ name: "home" });
  }
}

async function resetInvalidSession() {
  clearAuthToken();
  clearWorkspaceSession();
  queryClient.clear();
  workspaceError.value = "";

  if (route.meta.requiresAuth) {
    await router.replace({ name: "home" });
  }
}

function upsertWorkspace(workspace: WorkspaceResponse) {
  const nextWorkspaces = [
    ...workspaces.value.filter((item) => item.id !== workspace.id),
    workspace,
  ].sort((left, right) => left.name.localeCompare(right.name));

  setWorkspaces(nextWorkspaces);
}

function handleStorageEvent() {
  syncActiveWorkspaceFromStorage();
  syncAuthSession();
}

function handleDropdownShow(event: Event) {
  const nextToggle = event.target instanceof HTMLElement ? event.target : null;

  closeOpenDropdowns(nextToggle);
}

watch(() => meQuery.data.value, (overview) => {
  if (overview) {
    applyUserOverview(overview);
  }
});

function normalizeText(value: string) {
  return String(value || "").trim();
}

function getAccountDisplayName(user: UserResponse | null) {
  return user?.name || user?.email || "";
}

function getAccountInitials(user: UserResponse | null) {
  const source = user?.name || user?.email || "";
  if (!source) {
    return "";
  }

  const parts = source
    .split(/\s+/)
    .map((part) => part.trim())
    .filter(Boolean);

  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[1][0]}`.toLocaleUpperCase("ru-KZ");
  }

  return source.slice(0, 1).toLocaleUpperCase("ru-KZ");
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
  document.addEventListener("show.bs.dropdown", handleDropdownShow);
  window.addEventListener(AUTH_SESSION_CHANGE_EVENT, syncAuthSession);
  window.addEventListener("storage", handleStorageEvent);

  if (authToken.value) {
    void refreshMeOverview();
  }
});

onUnmounted(() => {
  document.removeEventListener("show.bs.dropdown", handleDropdownShow);
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
          <template v-if="hasVerifiedAccount">
            <RouterLink class="nav-link" to="/dashboard" @click="closeOpenDropdowns">
              Дэшборд
            </RouterLink>
          </template>
          <div v-if="canManageCurrentWorkspace" class="nav-item dropdown">
            <button
              id="coregrid-workspace-dropdown"
              class="nav-link dropdown-toggle"
              :class="{ active: isWorkspaceAdminRouteActive }"
              type="button"
              data-bs-toggle="dropdown"
              :aria-current="isWorkspaceAdminRouteActive ? 'page' : undefined"
              aria-expanded="false"
            >
              Рабочее пространство
            </button>
            <ul class="dropdown-menu" aria-labelledby="coregrid-workspace-dropdown">
              <li>
                <button
                  class="dropdown-item"
                  :class="{ active: isMembersListRouteActive }"
                  type="button"
                  @click="openMembersSection('members')"
                >
                  Список участников
                </button>
              </li>
              <li>
                <button
                  class="dropdown-item"
                  :class="{ active: isMembersInvitationsRouteActive }"
                  type="button"
                  @click="openMembersSection('invitations')"
                >
                  Приглашения
                </button>
              </li>
              <li><hr class="dropdown-divider"></li>
              <li>
                <RouterLink
                  class="dropdown-item"
                  :class="{ active: isAuditLogsRouteActive }"
                  to="/audit-logs"
                  @click="closeOpenDropdowns"
                >
                  Журнал действий
                </RouterLink>
              </li>
            </ul>
          </div>

          <div v-if="hasVerifiedAccount" class="nav-item dropdown">
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
                <RouterLink class="dropdown-item" to="/products" @click="closeOpenDropdowns">
                  Товары
                </RouterLink>
              </li>
              <li>
                <RouterLink class="dropdown-item" to="/companies" @click="closeOpenDropdowns">
                  Компании
                </RouterLink>
              </li>
              <li>
                <RouterLink class="dropdown-item" to="/suppliers" @click="closeOpenDropdowns">
                  Поставщики
                </RouterLink>
              </li>
            </ul>
          </div>

          <div v-if="hasVerifiedAccount" class="nav-item dropdown">
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
                <RouterLink class="dropdown-item" to="/restocks" @click="closeOpenDropdowns">
                  Пополнения
                </RouterLink>
              </li>
              <li>
                <RouterLink class="dropdown-item" to="/sales" @click="closeOpenDropdowns">
                  Продажи
                </RouterLink>
              </li>
            </ul>
          </div>
        </div>

        <div class="navbar-session ms-lg-auto mt-3 mt-lg-0">
          <div v-if="hasVerifiedAccount" class="navbar-account">
            <RouterLink
              class="btn btn-outline-secondary account-menu-button"
              :class="{ active: isAccountRouteActive }"
              to="/me"
              :aria-current="isAccountRouteActive ? 'page' : undefined"
              @click="closeOpenDropdowns"
            >
              <span class="account-avatar" aria-hidden="true">{{ accountInitials }}</span>
              <span class="account-menu-name">{{ accountDisplayName }}</span>
            </RouterLink>
          </div>
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
            <RouterLink class="btn btn-outline-secondary" to="/">
              На главную
            </RouterLink>
            <button class="btn btn-outline-danger" type="button" @click="signOut">
              Выйти
            </button>
            <button
              v-if="workspaceError"
              class="btn btn-outline-secondary"
              type="button"
              @click="refreshMeOverview()"
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
