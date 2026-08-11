<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { useRoute, useRouter } from "vue-router";

import {
  createWorkspaceInvitation,
  deleteWorkspaceInvitation,
  getWorkspaceInvitations,
} from "../lib/api";
import {
  formatCount,
  formatDateTime,
  getCreateErrorMessage,
  getDeleteErrorMessage,
  getRequestErrorMessage,
} from "../lib/format";
import { canManageMembers, formatWorkspaceRole } from "../lib/permissions";
import { activeWorkspace, activeWorkspaceId } from "../lib/workspaceSession";
import type {
  WorkspaceInvitationCreatePayload,
  WorkspaceInvitationResponse,
  WorkspaceInvitationRole,
} from "../types/api";

type InvitationStatus = "pending" | "accepted" | "revoked" | "expired";
type MembersTab = "members" | "invitations";

const ROLE_OPTIONS: { value: WorkspaceInvitationRole; label: string }[] = [
  { value: "viewer", label: "Наблюдатель" },
  { value: "operator", label: "Оператор" },
  { value: "manager", label: "Менеджер" },
  { value: "admin", label: "Администратор" },
];

const route = useRoute();
const router = useRouter();
const queryClient = useQueryClient();
const searchForm = ref<HTMLFormElement | null>(null);
const createFormElement = ref<HTMLFormElement | null>(null);
const searchDraft = ref(currentSearchFromRoute());
const createError = ref("");
const deleteError = ref("");
const deletingInvitationId = ref("");
const invitationForm = reactive({
  email: "",
  role: "viewer" as WorkspaceInvitationRole,
});

const currentSearch = computed(() => currentSearchFromRoute());
const currentTab = computed(() => currentTabFromRoute());
const canManageCurrentWorkspaceMembers = computed(() => (
  canManageMembers(activeWorkspace.value?.role)
));
const invitationsQuery = useQuery({
  queryKey: computed(() => [
    "workspace-invitations",
    activeWorkspaceId.value,
    "list",
    currentSearch.value,
  ]),
  queryFn: () => getWorkspaceInvitations({ search: currentSearch.value }),
  enabled: computed(() => (
    Boolean(activeWorkspaceId.value)
      && canManageCurrentWorkspaceMembers.value
      && currentTab.value === "invitations"
  )),
});
const createInvitationMutation = useMutation({
  mutationFn: createInvitationFromForm,
  onSuccess: handleInvitationCreateSuccess,
  onError: (error) => {
    createError.value = getCreateErrorMessage(error, "приглашение");
  },
});
const deleteInvitationMutation = useMutation({
  mutationFn: (invitationId: string) => deleteWorkspaceInvitation(invitationId),
  onSuccess: handleInvitationDeleteSuccess,
  onError: (error) => {
    deleteError.value = getDeleteErrorMessage(error, "приглашение");
  },
  onSettled: () => {
    deletingInvitationId.value = "";
  },
});

const invitations = computed(() => sortInvitations(invitationsQuery.data.value || []));
const invitationsError = computed(() => (
  invitationsQuery.error.value
    ? getRequestErrorMessage(invitationsQuery.error.value, "приглашения")
    : ""
));
const shouldShowInvitationsEmpty = computed(() => (
  !invitationsQuery.isLoading.value
    && !invitationsError.value
    && invitations.value.length === 0
));
const workspaceLabel = computed(() => activeWorkspace.value?.name || "Рабочее пространство");

watch(currentSearch, (nextSearch) => {
  searchDraft.value = nextSearch;
});

function submitSearch() {
  if (!searchForm.value?.reportValidity()) {
    return;
  }

  navigateMembers({ tab: "invitations", search: searchDraft.value });
}

function clearSearch() {
  searchDraft.value = "";
  navigateMembers({ tab: "invitations", search: "" });
}

function submitInvitationCreate() {
  createError.value = "";

  if (!createFormElement.value?.reportValidity()) {
    return;
  }

  createInvitationMutation.mutate();
}

function createInvitationFromForm() {
  const payload: WorkspaceInvitationCreatePayload = {
    email: normalizeText(invitationForm.email),
    role: invitationForm.role,
  };

  return createWorkspaceInvitation(payload);
}

async function handleInvitationCreateSuccess() {
  const invitedEmail = normalizeText(invitationForm.email);

  resetCreateForm();
  navigateMembers({ tab: "invitations", search: invitedEmail });
  await invalidateInvitationQueries();
}

function deleteInvitation(invitation: WorkspaceInvitationResponse) {
  if (!canDeleteInvitation(invitation)) {
    return;
  }

  deleteError.value = "";
  deletingInvitationId.value = invitation.id;
  deleteInvitationMutation.mutate(invitation.id);
}

async function handleInvitationDeleteSuccess() {
  await invalidateInvitationQueries();
}

async function invalidateInvitationQueries() {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ["workspace-invitations", activeWorkspaceId.value] }),
    queryClient.invalidateQueries({ queryKey: ["me", "invitations"] }),
  ]);
}

function canDeleteInvitation(invitation: WorkspaceInvitationResponse) {
  return !invitation.accepted_at;
}

function getInvitationStatus(invitation: WorkspaceInvitationResponse): InvitationStatus {
  if (invitation.accepted_at) {
    return "accepted";
  }

  if (invitation.revoked_at) {
    return "revoked";
  }

  if (getTime(invitation.expires_at) > 0 && getTime(invitation.expires_at) <= Date.now()) {
    return "expired";
  }

  return "pending";
}

function getStatusLabel(invitation: WorkspaceInvitationResponse) {
  switch (getInvitationStatus(invitation)) {
    case "accepted":
      return "Принято";
    case "revoked":
      return "Отозвано";
    case "expired":
      return "Истекло";
    default:
      return "Ожидает";
  }
}

function getStatusClass(invitation: WorkspaceInvitationResponse) {
  switch (getInvitationStatus(invitation)) {
    case "accepted":
      return "text-bg-success";
    case "revoked":
      return "text-bg-secondary";
    case "expired":
      return "text-bg-warning";
    default:
      return "text-bg-primary";
  }
}

function sortInvitations(invitations: WorkspaceInvitationResponse[]) {
  return [...invitations].sort((left, right) => (
    getTime(right.created_at) - getTime(left.created_at)
  ));
}

function resetCreateForm() {
  invitationForm.email = "";
  invitationForm.role = "viewer";
  createError.value = "";
}

function navigateMembers({ tab, search }: { tab: MembersTab; search: string }) {
  const trimmedSearch = normalizeText(search);
  const query: Record<string, string> = { tab };

  if (tab === "invitations" && trimmedSearch) {
    query.search = trimmedSearch;
  }

  void router.push({ name: "members", query });
}

function currentSearchFromRoute() {
  return normalizeRouteString(route.query.search);
}

function currentTabFromRoute(): MembersTab {
  return normalizeRouteString(route.query.tab) === "invitations"
    ? "invitations"
    : "members";
}

function normalizeRouteString(value: unknown) {
  const rawValue = Array.isArray(value) ? value[0] : value;

  return typeof rawValue === "string" ? rawValue.trim() : "";
}

function normalizeText(value: string) {
  return String(value || "").trim();
}

function getTime(value: string) {
  const time = new Date(value).getTime();

  return Number.isNaN(time) ? 0 : time;
}
</script>

<template>
  <section class="container-fluid p-4 members-page">
    <div class="members-toolbar d-flex align-items-end justify-content-between flex-wrap gap-3 mb-3">
      <div>
        <h1 class="fs-4 mb-1">Участники</h1>
        <p class="text-secondary mb-0">
          {{ workspaceLabel }} · {{ formatWorkspaceRole(activeWorkspace?.role) }}
        </p>
      </div>
      <span
        v-if="canManageCurrentWorkspaceMembers && currentTab === 'invitations'"
        class="badge text-bg-secondary members-count"
      >
        {{ formatCount(invitations.length) }} приглашений
      </span>
    </div>

    <div v-if="!canManageCurrentWorkspaceMembers" class="alert alert-warning" role="alert">
      Недостаточно прав для управления участниками этого рабочего пространства.
    </div>

    <template v-else>
      <section
        v-if="currentTab === 'members'"
        class="members-management-panel"
        role="tabpanel"
      >
        <div class="members-section-header">
          <div>
            <h2 class="fs-5 mb-1">Участники рабочего пространства</h2>
            <p class="text-secondary mb-0">Роли и доступ текущих пользователей.</p>
          </div>
        </div>
        <div class="alert alert-light border mb-0" role="status">
          Список участников, изменение ролей и удаление пользователей ждут backend endpoints для memberships.
        </div>
      </section>

      <section
        v-else
        class="members-management-panel"
        role="tabpanel"
      >
        <div class="members-section-header">
          <div>
            <h2 class="fs-5 mb-1">Отправленные приглашения</h2>
            <p class="text-secondary mb-0">Поиск работает по email приглашённого пользователя.</p>
          </div>
          <form ref="searchForm" class="members-search" role="search" @submit.prevent="submitSearch">
            <label class="form-label" for="members-invitation-search">Поиск приглашения</label>
            <div class="input-group">
              <input
                id="members-invitation-search"
                v-model="searchDraft"
                class="form-control"
                name="search"
                type="search"
                maxlength="100"
                placeholder="email"
                autocomplete="off"
              >
              <button
                v-if="currentSearch"
                class="btn btn-outline-secondary"
                type="button"
                :disabled="invitationsQuery.isFetching.value"
                @click="clearSearch"
              >
                Сбросить
              </button>
              <button class="btn btn-primary" type="submit" :disabled="invitationsQuery.isFetching.value">
                Поиск
              </button>
            </div>
          </form>
        </div>

        <form
          ref="createFormElement"
          class="row g-2 align-items-end invitation-create-form"
          @submit.prevent="submitInvitationCreate"
        >
          <div class="col-12 col-md-6">
            <label class="form-label" for="members-invitation-email">Почта</label>
            <input
              id="members-invitation-email"
              v-model.trim="invitationForm.email"
              class="form-control"
              name="email"
              type="email"
              autocomplete="email"
              maxlength="254"
              required
            >
          </div>
          <div class="col-12 col-md-3">
            <label class="form-label" for="members-invitation-role">Роль</label>
            <select
              id="members-invitation-role"
              v-model="invitationForm.role"
              class="form-select"
              name="role"
              required
            >
              <option
                v-for="roleOption in ROLE_OPTIONS"
                :key="roleOption.value"
                :value="roleOption.value"
              >
                {{ roleOption.label }}
              </option>
            </select>
          </div>
          <div class="col-12 col-md-3 d-grid">
            <button
              class="btn btn-success"
              type="submit"
              :disabled="createInvitationMutation.isPending.value"
            >
              {{ createInvitationMutation.isPending.value ? "Отправка..." : "Пригласить" }}
            </button>
          </div>
        </form>

        <div v-if="createError" class="alert alert-danger mt-3" role="alert">
          {{ createError }}
        </div>
        <div v-if="deleteError" class="alert alert-danger mt-3" role="alert">
          {{ deleteError }}
        </div>

        <div
          v-if="invitationsQuery.isLoading.value"
          class="text-secondary py-4"
          aria-live="polite"
        >
          Загрузка приглашений...
        </div>
        <div v-else-if="invitationsError" class="alert alert-danger mt-3" role="alert">
          {{ invitationsError }}
        </div>
        <div v-else-if="shouldShowInvitationsEmpty" class="alert alert-light border mt-3" role="status">
          {{ currentSearch ? "По запросу ничего не найдено." : "Приглашений пока нет." }}
        </div>

        <div v-if="invitations.length > 0 && !invitationsError" class="invitation-list mt-3">
          <article
            v-for="invitation in invitations"
            :key="invitation.id"
            class="invitation-list-item"
          >
            <div class="invitation-list-header">
              <div>
                <h3 class="invitation-title">{{ invitation.email }}</h3>
                <div class="invitation-meta">
                  <span>{{ formatWorkspaceRole(invitation.role) }}</span>
                  <span>Создано: {{ formatDateTime(invitation.created_at) }}</span>
                  <span>Истекает: {{ formatDateTime(invitation.expires_at) }}</span>
                </div>
              </div>
              <div class="invitation-actions">
                <span class="badge" :class="getStatusClass(invitation)">
                  {{ getStatusLabel(invitation) }}
                </span>
                <button
                  v-if="canDeleteInvitation(invitation)"
                  class="btn btn-outline-danger btn-sm"
                  type="button"
                  :disabled="deleteInvitationMutation.isPending.value"
                  @click="deleteInvitation(invitation)"
                >
                  {{ deletingInvitationId === invitation.id ? "Удаление..." : "Удалить" }}
                </button>
              </div>
            </div>
          </article>
        </div>
      </section>
    </template>
  </section>
</template>
