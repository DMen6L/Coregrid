<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from "vue";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { RouterView, useRoute, useRouter } from "vue-router";

import MyInvitationsModal from "./components/MyInvitationsModal.vue";
import {
  ApiRequestError,
  createWorkspace,
  getCurrentUser,
  getMyInvitations,
  getWorkspaces,
} from "./lib/api";
import {
  AUTH_SESSION_CHANGE_EVENT,
  clearAuthToken,
  getAuthToken,
} from "./lib/authSession";
import { closeOpenDropdowns } from "./lib/dropdowns";
import { canManageMembers } from "./lib/permissions";
import {
  activeWorkspace,
  clearWorkspaceSession,
  selectInitialWorkspace,
  setActiveWorkspaceId,
  setWorkspaces,
  syncActiveWorkspaceFromStorage,
  workspaces,
} from "./lib/workspaceSession";
import type { UserResponse, WorkspaceResponse } from "./types/api";

const route = useRoute();
const router = useRouter();
const queryClient = useQueryClient();
const authToken = ref(getAuthToken());
const workspaceCreateFormElement = ref<HTMLFormElement | null>(null);
const isWorkspaceLoading = ref(false);
const isWorkspaceCreateModalOpen = ref(false);
const isMyInvitationsModalOpen = ref(false);
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
const isAuthenticated = computed(() => Boolean(authToken.value));
const currentUserQuery = useQuery({
  queryKey: ["auth", "me"],
  queryFn: getCurrentUser,
  enabled: computed(() => isAuthenticated.value),
});
const myInvitationsQuery = useQuery({
  queryKey: ["me", "invitations"],
  queryFn: getMyInvitations,
  enabled: computed(() => isAuthenticated.value),
});
const requiresWorkspace = computed(() => Boolean(route.meta.requiresWorkspace));
const shouldShowWorkspaceGate = computed(() => (
  isAuthenticated.value
    && requiresWorkspace.value
    && (!activeWorkspace.value || isWorkspaceLoading.value || Boolean(workspaceError.value))
));
const myInvitationsCount = computed(() => myInvitationsQuery.data.value?.length || 0);
const canManageCurrentWorkspaceMembers = computed(() => (
  canManageMembers(activeWorkspace.value?.role)
));
const currentUser = computed(() => currentUserQuery.data.value || null);
const accountDisplayName = computed(() => getAccountDisplayName(currentUser.value));
const accountSecondaryText = computed(() => currentUser.value?.email || "Аккаунт Coregrid");
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

  if (authToken.value !== previousToken || workspaces.value.length === 0) {
    void loadWorkspaces();
  }
}

async function signOut() {
  closeOpenDropdowns();
  closeWorkspaceModals();
  clearAuthToken();
  queryClient.clear();
  await router.push({ path: "/auth", query: { mode: "login" } });
}

async function loadWorkspaces(preferredWorkspaceId: number | null = null) {
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
    const nextWorkspaces = await getWorkspaces();
    const preferredWorkspaceExists = Boolean(
      nextPreferredWorkspaceId
        && nextWorkspaces.some((workspace) => workspace.id === nextPreferredWorkspaceId),
    );

    setWorkspaces(nextWorkspaces);
    setActiveWorkspaceId(
      preferredWorkspaceExists
        ? nextPreferredWorkspaceId
        : selectInitialWorkspace(nextWorkspaces),
    );
  } catch (error) {
    setWorkspaces([]);
    setActiveWorkspaceId(null);
    workspaceError.value = getWorkspaceErrorMessage(error);
  } finally {
    isWorkspaceLoading.value = false;
  }
}

function selectWorkspace(workspace: WorkspaceResponse) {
  closeOpenDropdowns();

  if (activeWorkspace.value?.id === workspace.id) {
    return;
  }

  setActiveWorkspaceId(workspace.id);
  void queryClient.invalidateQueries();
}

function openWorkspaceCreateModal() {
  closeOpenDropdowns();
  isMyInvitationsModalOpen.value = false;
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
    await queryClient.invalidateQueries();
  } catch (error) {
    workspaceCreateError.value = getWorkspaceErrorMessage(error);
  } finally {
    isWorkspaceCreateSubmitting.value = false;
  }
}

function openMyInvitationsModal() {
  closeOpenDropdowns();
  isWorkspaceCreateModalOpen.value = false;
  isMyInvitationsModalOpen.value = true;
  void myInvitationsQuery.refetch();
}

function closeMyInvitationsModal() {
  isMyInvitationsModalOpen.value = false;
}

async function handleInvitationAccepted(workspace: WorkspaceResponse) {
  upsertWorkspace(workspace);
  setActiveWorkspaceId(workspace.id);
  isMyInvitationsModalOpen.value = false;
  workspaceError.value = "";

  await loadWorkspaces(workspace.id);
  await queryClient.invalidateQueries();
}

function closeWorkspaceModals() {
  isWorkspaceCreateModalOpen.value = false;
  isMyInvitationsModalOpen.value = false;
}

function retryWorkspaceLoadFromDropdown() {
  closeOpenDropdowns();
  void loadWorkspaces();
}

function openMembersSection(tab: "members" | "invitations") {
  closeOpenDropdowns();
  void router.push({ name: "members", query: { tab } });
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

function normalizeText(value: string) {
  return String(value || "").trim();
}

function getAccountDisplayName(user: UserResponse | null) {
  return user?.name || user?.email || "Аккаунт";
}

function getAccountInitials(user: UserResponse | null) {
  const source = user?.name || user?.email || "A";
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
    void loadWorkspaces();
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
          <RouterLink class="nav-link" to="/dashboard" @click="closeOpenDropdowns">
            Дэшборд
          </RouterLink>
          <div v-if="canManageCurrentWorkspaceMembers" class="nav-item dropdown">
            <button
              id="coregrid-members-dropdown"
              class="nav-link dropdown-toggle"
              :class="{ active: isMembersRouteActive }"
              type="button"
              data-bs-toggle="dropdown"
              :aria-current="isMembersRouteActive ? 'page' : undefined"
              aria-expanded="false"
            >
              Участники
            </button>
            <ul class="dropdown-menu" aria-labelledby="coregrid-members-dropdown">
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
            </ul>
          </div>

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
          <div v-if="isAuthenticated" class="dropdown navbar-account">
            <button
              id="coregrid-account-dropdown"
              class="btn btn-outline-secondary btn-sm dropdown-toggle account-menu-button"
              type="button"
              data-bs-toggle="dropdown"
              aria-expanded="false"
            >
              <span class="account-avatar" aria-hidden="true">{{ accountInitials }}</span>
              <span class="account-menu-name">{{ accountDisplayName }}</span>
            </button>
            <ul class="dropdown-menu dropdown-menu-lg-end account-menu" aria-labelledby="coregrid-account-dropdown">
              <li>
                <div class="dropdown-item-text account-menu-header">
                  <span class="account-avatar account-avatar-lg" aria-hidden="true">
                    {{ accountInitials }}
                  </span>
                  <span class="account-menu-user">
                    <span class="account-menu-user-name">{{ accountDisplayName }}</span>
                    <span class="account-menu-user-email">{{ accountSecondaryText }}</span>
                  </span>
                </div>
              </li>
              <li><hr class="dropdown-divider"></li>
              <li>
                <span class="dropdown-header">Рабочие пространства</span>
              </li>
              <li v-if="isWorkspaceLoading">
                <span class="dropdown-item-text text-secondary">Загрузка...</span>
              </li>
              <li v-for="workspace in workspaces" :key="workspace.id">
                <button
                  class="dropdown-item account-workspace-option"
                  :class="{ active: activeWorkspace?.id === workspace.id }"
                  type="button"
                  @click="selectWorkspace(workspace)"
                >
                  <span class="account-workspace-name">{{ workspace.name }}</span>
                  <span class="workspace-dropdown-role">{{ workspace.role }}</span>
                </button>
              </li>
              <li v-if="workspaceError">
                <span class="dropdown-item-text text-danger">{{ workspaceError }}</span>
              </li>
              <li>
                <button class="dropdown-item" type="button" @click="openWorkspaceCreateModal">
                  Создать рабочее пространство
                </button>
              </li>
              <li v-if="workspaceError">
                <button class="dropdown-item" type="button" @click="retryWorkspaceLoadFromDropdown">
                  Повторить загрузку
                </button>
              </li>
              <li><hr class="dropdown-divider"></li>
              <li>
                <button
                  class="dropdown-item d-flex align-items-center justify-content-between gap-3"
                  type="button"
                  @click="openMyInvitationsModal"
                >
                  <span>Мои приглашения</span>
                  <span v-if="myInvitationsCount > 0" class="badge rounded-pill text-bg-primary">
                    {{ myInvitationsCount }}
                  </span>
                </button>
              </li>
              <li><hr class="dropdown-divider"></li>
              <li>
                <button class="dropdown-item text-danger" type="button" @click="signOut">
                  Выйти
                </button>
              </li>
            </ul>
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
            <button
              v-if="workspaceError"
              class="btn btn-outline-secondary"
              type="button"
              @click="loadWorkspaces()"
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

  <MyInvitationsModal
    :is-open="isMyInvitationsModalOpen"
    @close="closeMyInvitationsModal"
    @accepted="handleInvitationAccepted"
  />
</template>
