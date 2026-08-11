<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { useRoute, useRouter } from "vue-router";

import MemberDetailModal from "../components/MemberDetailModal.vue";
import {
  createWorkspaceInvitation,
  DEFAULT_PAGE_SIZE,
  deleteWorkspaceInvitation,
  FIRST_PAGE,
  getWorkspaceInvitations,
  getWorkspaceMembers,
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
  PaginatedResponse,
  WorkspaceInvitationCreatePayload,
  WorkspaceInvitationResponse,
  WorkspaceInvitationRole,
  WorkspaceMembershipSummaryResponse,
} from "../types/api";

type InvitationStatus = "pending" | "accepted" | "revoked" | "expired";
type MembersTab = "members" | "invitations";

const ROLE_OPTIONS: { value: WorkspaceInvitationRole; label: string }[] = [
  { value: "viewer", label: "Наблюдатель" },
  { value: "operator", label: "Оператор" },
  { value: "manager", label: "Менеджер" },
  { value: "admin", label: "Администратор" },
];

const EMPTY_MEMBERS_PAGE: PaginatedResponse<WorkspaceMembershipSummaryResponse> = {
  items: [],
  page: FIRST_PAGE,
  page_size: DEFAULT_PAGE_SIZE,
  total: 0,
  total_pages: 0,
  has_next: false,
  has_previous: false,
};

const route = useRoute();
const router = useRouter();
const queryClient = useQueryClient();
const searchForm = ref<HTMLFormElement | null>(null);
const createFormElement = ref<HTMLFormElement | null>(null);
const searchDraft = ref(currentSearchFromRoute());
const isMemberDetailModalOpen = ref(false);
const selectedMemberId = ref<number | null>(null);
const createError = ref("");
const deleteError = ref("");
const deletingInvitationId = ref("");
const invitationForm = reactive({
  email: "",
  role: "viewer" as WorkspaceInvitationRole,
});

const currentSearch = computed(() => currentSearchFromRoute());
const currentTab = computed(() => currentTabFromRoute());
const currentPage = computed(() => currentPageFromRoute());
const canManageCurrentWorkspaceMembers = computed(() => (
  canManageMembers(activeWorkspace.value?.role)
));
const membersQuery = useQuery({
  queryKey: computed(() => [
    "workspace-members",
    activeWorkspaceId.value,
    "list",
    currentSearch.value,
    currentPage.value,
    DEFAULT_PAGE_SIZE,
  ]),
  queryFn: () => getWorkspaceMembers({
    search: currentSearch.value,
    page: currentPage.value,
    pageSize: DEFAULT_PAGE_SIZE,
  }),
  enabled: computed(() => (
    Boolean(activeWorkspaceId.value)
      && canManageCurrentWorkspaceMembers.value
      && currentTab.value === "members"
  )),
});
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

const membersPage = computed(() => membersQuery.data.value || EMPTY_MEMBERS_PAGE);
const membersError = computed(() => (
  membersQuery.error.value
    ? getRequestErrorMessage(membersQuery.error.value, "участников")
    : ""
));
const hasMembers = computed(() => membersPage.value.items.length > 0);
const shouldShowMembersTable = computed(() => (
  hasMembers.value
    && !membersQuery.isLoading.value
    && !membersError.value
));
const shouldShowMembersEmpty = computed(() => (
  !membersQuery.isLoading.value
    && !membersError.value
    && membersPage.value.items.length === 0
));
const shouldShowMembersPagination = computed(() => (
  membersPage.value.total > 0
    && !membersQuery.isLoading.value
    && !membersError.value
));
const totalMemberPages = computed(() => Math.max(membersPage.value.total_pages, 1));
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

  navigateMembers({
    tab: currentTab.value,
    search: searchDraft.value,
    page: FIRST_PAGE,
  });
}

function clearSearch() {
  searchDraft.value = "";
  navigateMembers({
    tab: currentTab.value,
    search: "",
    page: FIRST_PAGE,
  });
}

function goToMembersPage(page: number) {
  navigateMembers({
    tab: "members",
    search: currentSearch.value,
    page,
  });
}

function openMemberDetail(member: WorkspaceMembershipSummaryResponse) {
  selectedMemberId.value = member.id;
  isMemberDetailModalOpen.value = true;
}

function closeMemberDetail() {
  isMemberDetailModalOpen.value = false;
  selectedMemberId.value = null;
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

function navigateMembers({
  tab,
  search,
  page = FIRST_PAGE,
}: {
  tab: MembersTab;
  search: string;
  page?: number;
}) {
  const trimmedSearch = normalizeText(search);
  const nextPage = Math.max(Number(page) || FIRST_PAGE, FIRST_PAGE);
  const query: Record<string, string> = { tab };

  if (trimmedSearch) {
    query.search = trimmedSearch;
  }

  if (tab === "members" && nextPage > FIRST_PAGE) {
    query.page = String(nextPage);
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

function currentPageFromRoute() {
  const routePage = Array.isArray(route.query.page)
    ? route.query.page[0]
    : route.query.page;
  const page = Number(routePage || FIRST_PAGE);

  return Number.isFinite(page) && page >= FIRST_PAGE ? Math.trunc(page) : FIRST_PAGE;
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
        v-if="canManageCurrentWorkspaceMembers && currentTab === 'members'"
        class="badge text-bg-secondary members-count"
      >
        {{ formatCount(membersPage.total) }} участников
      </span>
      <span
        v-else-if="canManageCurrentWorkspaceMembers && currentTab === 'invitations'"
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
          <form ref="searchForm" class="members-search" role="search" @submit.prevent="submitSearch">
            <label class="form-label" for="members-search-input">Поиск участника</label>
            <div class="input-group">
              <input
                id="members-search-input"
                v-model="searchDraft"
                class="form-control"
                name="search"
                type="search"
                maxlength="100"
                placeholder="имя или email"
                autocomplete="off"
              >
              <button
                v-if="currentSearch"
                class="btn btn-outline-secondary"
                type="button"
                :disabled="membersQuery.isFetching.value"
                @click="clearSearch"
              >
                Сбросить
              </button>
              <button class="btn btn-primary" type="submit" :disabled="membersQuery.isFetching.value">
                Поиск
              </button>
            </div>
          </form>
        </div>

        <div v-if="membersQuery.isLoading.value" class="text-secondary py-4" aria-live="polite">
          Загрузка участников...
        </div>
        <div v-else-if="membersError" class="alert alert-danger" role="alert">
          {{ membersError }}
        </div>
        <div v-else-if="shouldShowMembersEmpty" class="alert alert-light border mb-0" role="status">
          {{ currentSearch ? "По запросу ничего не найдено." : "Участников пока нет." }}
        </div>

        <div v-if="shouldShowMembersTable" class="table-responsive members-table">
          <table class="table table-hover align-middle mb-0">
            <thead>
              <tr>
                <th scope="col">Участник</th>
                <th scope="col">Email</th>
                <th scope="col">Роль</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="member in membersPage.items"
                :key="member.id"
                class="member-summary-row"
                tabindex="0"
                role="button"
                :aria-label="`Открыть участника ${member.name || member.email || `#${formatCount(member.id)}`}`"
                @click="openMemberDetail(member)"
                @keydown.enter.prevent="openMemberDetail(member)"
              >
                <td class="member-name-cell">
                  <div class="fw-semibold">{{ member.name || "Без имени" }}</div>
                  <div class="member-meta">Membership ID {{ formatCount(member.id) }}</div>
                </td>
                <td class="member-email">{{ member.email || "Не указан" }}</td>
                <td>
                  <span class="badge text-bg-light border">
                    {{ formatWorkspaceRole(member.role) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <nav
          v-if="shouldShowMembersPagination"
          class="members-pagination mt-3"
          aria-label="Пагинация участников"
        >
          <button
            class="btn btn-outline-primary"
            type="button"
            :disabled="!membersPage.has_previous || membersQuery.isFetching.value"
            @click="goToMembersPage(membersPage.page - 1)"
          >
            Назад
          </button>
          <span class="members-page-summary">
            Страница {{ formatCount(membersPage.page) }} из {{ formatCount(totalMemberPages) }}
          </span>
          <button
            class="btn btn-outline-primary"
            type="button"
            :disabled="!membersPage.has_next || membersQuery.isFetching.value"
            @click="goToMembersPage(membersPage.page + 1)"
          >
            Вперед
          </button>
        </nav>
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

    <MemberDetailModal
      :member-id="selectedMemberId"
      :is-open="isMemberDetailModalOpen"
      @close="closeMemberDetail"
    />
  </section>
</template>
