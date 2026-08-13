<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { useRouter } from "vue-router";

import {
  acceptMyInvitation,
  createWorkspace,
  getMe,
  leaveMyWorkspace,
  patchMe,
  patchMePassword,
} from "../lib/api";
import { clearAuthToken } from "../lib/authSession";
import {
  formatCount,
  formatDateTime,
  getCreateErrorMessage,
  getDeleteErrorMessage,
  getRequestErrorMessage,
} from "../lib/format";
import { formatWorkspaceRole } from "../lib/permissions";
import {
  activeWorkspaceId,
  clearWorkspaceSession,
  selectInitialWorkspace,
  setActiveWorkspaceId,
  setWorkspaces,
} from "../lib/workspaceSession";
import type {
  MeResponse,
  UserInvitationResponse,
  UserPasswordUpdatePayload,
  UserUpdatePayload,
  WorkspaceCreatePayload,
  WorkspaceResponse,
} from "../types/api";

const router = useRouter();
const queryClient = useQueryClient();
const profileFormElement = ref<HTMLFormElement | null>(null);
const passwordFormElement = ref<HTMLFormElement | null>(null);
const workspaceCreateFormElement = ref<HTMLFormElement | null>(null);
const profileError = ref("");
const profileSuccess = ref("");
const passwordError = ref("");
const passwordSuccess = ref("");
const invitationError = ref("");
const acceptingInvitationId = ref("");
const workspaceCreateError = ref("");
const workspaceLeaveError = ref("");
const workspaceToLeave = ref<WorkspaceResponse | null>(null);
const leavingWorkspaceId = ref<number | null>(null);
const profileForm = reactive({
  name: "",
  email: "",
});
const passwordForm = reactive({
  currentPassword: "",
  newPassword: "",
  confirmPassword: "",
});
const workspaceForm = reactive({
  name: "",
});

const meQuery = useQuery({
  queryKey: ["me"],
  queryFn: getMe,
});
const updateProfileMutation = useMutation({
  mutationFn: updateProfileFromForm,
  onSuccess: handleProfileUpdateSuccess,
  onError: (error) => {
    profileError.value = getCreateErrorMessage(error, "профиль");
  },
});
const updatePasswordMutation = useMutation({
  mutationFn: updatePasswordFromForm,
  onSuccess: handlePasswordUpdateSuccess,
  onError: (error) => {
    passwordError.value = getCreateErrorMessage(error, "пароль");
  },
});
const acceptInvitationMutation = useMutation({
  mutationFn: (invitationId: string) => acceptMyInvitation(invitationId),
  onSuccess: handleInvitationAccepted,
  onError: (error) => {
    invitationError.value = getCreateErrorMessage(error, "приглашение");
  },
  onSettled: () => {
    acceptingInvitationId.value = "";
  },
});
const createWorkspaceMutation = useMutation({
  mutationFn: createWorkspaceFromForm,
  onSuccess: handleWorkspaceCreateSuccess,
  onError: (error) => {
    workspaceCreateError.value = getCreateErrorMessage(error, "рабочее пространство");
  },
});
const leaveWorkspaceMutation = useMutation({
  mutationFn: (workspaceId: number) => leaveMyWorkspace(workspaceId),
  onSuccess: (_result, workspaceId) => handleWorkspaceLeaveSuccess(workspaceId),
  onError: (error) => {
    workspaceLeaveError.value = getDeleteErrorMessage(error, "участие в рабочем пространстве");
  },
  onSettled: () => {
    leavingWorkspaceId.value = null;
  },
});

const me = computed(() => meQuery.data.value || null);
const user = computed(() => me.value?.user || null);
const invitations = computed(() => sortInvitations(me.value?.invitations || []));
const userWorkspaces = computed(() => me.value?.workspaces || []);
const pageError = computed(() => (
  meQuery.error.value
    ? getRequestErrorMessage(meQuery.error.value, "данные аккаунта")
    : ""
));
const canSubmitProfile = computed(() => (
  Boolean(user.value)
    && (
      normalizeText(profileForm.name) !== user.value?.name
        || normalizeText(profileForm.email) !== user.value?.email
    )
    && !updateProfileMutation.isPending.value
));
const canSubmitPassword = computed(() => (
  Boolean(passwordForm.currentPassword)
    && Boolean(passwordForm.newPassword)
    && Boolean(passwordForm.confirmPassword)
    && !updatePasswordMutation.isPending.value
));
const hasWorkspaces = computed(() => userWorkspaces.value.length > 0);

watch(() => me.value, (overview) => {
  if (overview) {
    syncWorkspaceSession(overview);
  }
}, { immediate: true });

watch(() => user.value, (nextUser) => {
  if (!updateProfileMutation.isPending.value) {
    profileForm.name = nextUser?.name || "";
    profileForm.email = nextUser?.email || "";
  }
}, { immediate: true });

function submitProfileUpdate() {
  profileError.value = "";
  profileSuccess.value = "";

  if (!profileFormElement.value?.reportValidity()) {
    return;
  }

  if (
    !user.value
      || (
        normalizeText(profileForm.name) === user.value.name
          && normalizeText(profileForm.email) === user.value.email
      )
  ) {
    return;
  }

  updateProfileMutation.mutate();
}

function updateProfileFromForm() {
  const payload: UserUpdatePayload = {
    name: normalizeText(profileForm.name),
    email: normalizeText(profileForm.email),
  };

  return patchMe(payload);
}

function handleProfileUpdateSuccess(overview: MeResponse) {
  queryClient.setQueryData(["me"], overview);
  syncWorkspaceSession(overview);
  profileForm.name = overview.user.name;
  profileForm.email = overview.user.email;
  profileError.value = "";
  profileSuccess.value = "Данные профиля обновлены.";
}

function submitPasswordUpdate() {
  passwordError.value = "";
  passwordSuccess.value = "";

  if (!passwordFormElement.value?.reportValidity()) {
    return;
  }

  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    passwordError.value = "Новый пароль и подтверждение не совпадают.";
    return;
  }

  if (passwordForm.currentPassword === passwordForm.newPassword) {
    passwordError.value = "Новый пароль должен отличаться от текущего.";
    return;
  }

  updatePasswordMutation.mutate();
}

function updatePasswordFromForm() {
  const payload: UserPasswordUpdatePayload = {
    current_password: passwordForm.currentPassword,
    new_password: passwordForm.newPassword,
  };

  return patchMePassword(payload);
}

function handlePasswordUpdateSuccess(overview: MeResponse) {
  queryClient.setQueryData(["me"], overview);
  syncWorkspaceSession(overview);
  passwordForm.currentPassword = "";
  passwordForm.newPassword = "";
  passwordForm.confirmPassword = "";
  passwordError.value = "";
  passwordSuccess.value = "Пароль обновлен.";
}

function acceptInvitation(invitation: UserInvitationResponse) {
  invitationError.value = "";
  acceptingInvitationId.value = invitation.id;
  acceptInvitationMutation.mutate(invitation.id);
}

async function handleInvitationAccepted(workspace: WorkspaceResponse) {
  setActiveWorkspaceId(workspace.id);
  invitationError.value = "";

  try {
    await refreshMeOverview(workspace.id);
  } catch (error) {
    invitationError.value = getRequestErrorMessage(error, "данные аккаунта");
  }
}

function submitWorkspaceCreate() {
  workspaceCreateError.value = "";

  if (!workspaceCreateFormElement.value?.reportValidity()) {
    return;
  }

  createWorkspaceMutation.mutate();
}

function createWorkspaceFromForm() {
  const payload: WorkspaceCreatePayload = {
    name: normalizeText(workspaceForm.name),
  };

  return createWorkspace(payload);
}

async function handleWorkspaceCreateSuccess(workspace: WorkspaceResponse) {
  workspaceCreateError.value = "";
  workspaceForm.name = "";
  setActiveWorkspaceId(workspace.id);

  try {
    await refreshMeOverview(workspace.id);
  } catch (error) {
    workspaceCreateError.value = getRequestErrorMessage(error, "данные аккаунта");
  }
}

function openLeaveWorkspaceDialog(workspace: WorkspaceResponse) {
  if (workspace.role === "owner") {
    workspaceLeaveError.value = "Владелец должен передать владение перед выходом из пространства.";
    return;
  }

  workspaceLeaveError.value = "";
  workspaceToLeave.value = workspace;
}

function closeLeaveWorkspaceDialog() {
  if (leaveWorkspaceMutation.isPending.value) {
    return;
  }

  workspaceToLeave.value = null;
}

function confirmLeaveWorkspace() {
  if (!workspaceToLeave.value || workspaceToLeave.value.role === "owner") {
    return;
  }

  workspaceLeaveError.value = "";
  leavingWorkspaceId.value = workspaceToLeave.value.id;
  leaveWorkspaceMutation.mutate(workspaceToLeave.value.id);
}

async function handleWorkspaceLeaveSuccess(workspaceId: number) {
  workspaceLeaveError.value = "";
  workspaceToLeave.value = null;

  try {
    await refreshMeOverview(activeWorkspaceId.value === workspaceId ? null : activeWorkspaceId.value);
    await queryClient.invalidateQueries();
  } catch (error) {
    workspaceLeaveError.value = getRequestErrorMessage(error, "данные аккаунта");
  }
}

async function refreshMeOverview(preferredWorkspaceId: number | null = null) {
  const overview = await queryClient.fetchQuery({
    queryKey: ["me"],
    queryFn: getMe,
  });

  syncWorkspaceSession(overview, preferredWorkspaceId);
}

function selectWorkspace(workspace: WorkspaceResponse) {
  if (activeWorkspaceId.value === workspace.id) {
    return;
  }

  setActiveWorkspaceId(workspace.id);
  void queryClient.invalidateQueries();
}

async function signOut() {
  clearAuthToken();
  clearWorkspaceSession();
  queryClient.clear();
  await router.push({ path: "/auth", query: { mode: "login" } });
}

function syncWorkspaceSession(
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
}

function sortInvitations(invitations: UserInvitationResponse[]) {
  return [...invitations].sort((left, right) => (
    getTime(right.created_at) - getTime(left.created_at)
  ));
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
  <section class="container-fluid p-4 me-page">
    <div class="me-toolbar d-flex align-items-end justify-content-between flex-wrap gap-3 mb-3">
      <div>
        <h1 class="fs-4 mb-1">Аккаунт</h1>
        <p class="text-secondary mb-0">
          {{ user?.email || "Личные данные и рабочие пространства" }}
        </p>
      </div>
    </div>

    <div v-if="meQuery.isLoading.value" class="alert alert-light border" role="status">
      Загрузка аккаунта...
    </div>
    <div v-else-if="pageError" class="alert alert-danger" role="alert">
      {{ pageError }}
    </div>

    <template v-if="me && !pageError">
      <section class="me-panel">
        <div class="me-section-header">
          <div>
            <h2 class="fs-5 mb-1">Личные данные</h2>
            <p class="text-secondary mb-0">Имя отображается в рабочем пространстве и приглашениях.</p>
          </div>
        </div>

        <div class="me-profile-grid mb-3">
          <div>
            <div class="me-detail-label">User ID</div>
            <div class="fw-semibold">{{ formatCount(user?.id) }}</div>
          </div>
          <div>
            <div class="me-detail-label">Текущая почта</div>
            <div class="fw-semibold me-email">{{ user?.email || "Не указана" }}</div>
          </div>
        </div>

        <form ref="profileFormElement" class="me-profile-form" @submit.prevent="submitProfileUpdate">
          <div v-if="profileError" class="alert alert-danger" role="alert">
            {{ profileError }}
          </div>
          <div v-if="profileSuccess" class="alert alert-success" role="status">
            {{ profileSuccess }}
          </div>

          <div class="row g-2 align-items-end">
            <div class="col-12 col-lg-5">
              <label class="form-label" for="me-profile-name">Имя</label>
              <input
                id="me-profile-name"
                v-model.trim="profileForm.name"
                class="form-control"
                name="name"
                type="text"
                maxlength="255"
                required
              >
            </div>
            <div class="col-12 col-lg-5">
              <label class="form-label" for="me-profile-email">Email</label>
              <input
                id="me-profile-email"
                v-model.trim="profileForm.email"
                class="form-control"
                name="email"
                type="email"
                maxlength="254"
                autocomplete="email"
                required
              >
            </div>
            <div class="col-12 col-lg-2 d-grid">
              <button
                class="btn btn-primary"
                type="submit"
                :disabled="!canSubmitProfile"
              >
                {{ updateProfileMutation.isPending.value ? "Сохранение..." : "Сохранить" }}
              </button>
            </div>
          </div>
        </form>
      </section>

      <section class="me-panel">
        <div class="me-section-header">
          <div>
            <h2 class="fs-5 mb-1">Пароль</h2>
            <p class="text-secondary mb-0">Смена пароля требует текущий пароль аккаунта.</p>
          </div>
        </div>

        <form
          ref="passwordFormElement"
          class="me-password-form"
          @submit.prevent="submitPasswordUpdate"
        >
          <div v-if="passwordError" class="alert alert-danger" role="alert">
            {{ passwordError }}
          </div>
          <div v-if="passwordSuccess" class="alert alert-success" role="status">
            {{ passwordSuccess }}
          </div>

          <div class="row g-2 align-items-end">
            <div class="col-12 col-lg-4">
              <label class="form-label" for="me-current-password">Текущий пароль</label>
              <input
                id="me-current-password"
                v-model="passwordForm.currentPassword"
                class="form-control"
                name="current_password"
                type="password"
                autocomplete="current-password"
                maxlength="128"
                :disabled="updatePasswordMutation.isPending.value"
                required
              >
            </div>
            <div class="col-12 col-lg-4">
              <label class="form-label" for="me-new-password">Новый пароль</label>
              <input
                id="me-new-password"
                v-model="passwordForm.newPassword"
                class="form-control"
                name="new_password"
                type="password"
                autocomplete="new-password"
                minlength="12"
                maxlength="128"
                :disabled="updatePasswordMutation.isPending.value"
                required
              >
            </div>
            <div class="col-12 col-lg-4">
              <label class="form-label" for="me-confirm-password">Повторите пароль</label>
              <input
                id="me-confirm-password"
                v-model="passwordForm.confirmPassword"
                class="form-control"
                name="confirm_password"
                type="password"
                autocomplete="new-password"
                minlength="12"
                maxlength="128"
                :disabled="updatePasswordMutation.isPending.value"
                required
              >
            </div>
            <div class="col-12 d-flex justify-content-end">
              <button
                class="btn btn-outline-primary"
                type="submit"
                :disabled="!canSubmitPassword"
              >
                {{
                  updatePasswordMutation.isPending.value
                    ? "Обновление..."
                    : "Обновить пароль"
                }}
              </button>
            </div>
          </div>
        </form>
      </section>

      <section class="me-panel">
        <div class="me-section-header">
          <div>
            <h2 class="fs-5 mb-1">Приглашения</h2>
            <p class="text-secondary mb-0">Активные приглашения для вашей почты.</p>
          </div>
          <span class="badge text-bg-secondary">
            {{ formatCount(invitations.length) }}
          </span>
        </div>

        <div v-if="invitationError" class="alert alert-danger" role="alert">
          {{ invitationError }}
        </div>
        <div v-if="invitations.length === 0" class="alert alert-light border mb-0" role="status">
          Активных приглашений нет.
        </div>
        <div v-else class="me-list">
          <article
            v-for="invitation in invitations"
            :key="invitation.id"
            class="me-list-item"
          >
            <div class="me-list-header">
              <div>
                <h3 class="me-list-title">{{ invitation.workspace_name }}</h3>
                <div class="me-meta">
                  <span>{{ formatWorkspaceRole(invitation.role) }}</span>
                  <span>Истекает: {{ formatDateTime(invitation.expires_at) }}</span>
                  <span v-if="invitation.inviter_user_name || invitation.inviter_user_email">
                    Пригласил: {{ invitation.inviter_user_name || invitation.inviter_user_email }}
                  </span>
                </div>
              </div>
              <button
                class="btn btn-primary btn-sm"
                type="button"
                :disabled="acceptInvitationMutation.isPending.value"
                @click="acceptInvitation(invitation)"
              >
                {{ acceptingInvitationId === invitation.id ? "Принятие..." : "Принять" }}
              </button>
            </div>
          </article>
        </div>
      </section>

      <section class="me-panel">
        <div class="me-section-header">
          <div>
            <h2 class="fs-5 mb-1">Рабочие пространства</h2>
            <p class="text-secondary mb-0">Пространства, где у вас есть роль участника.</p>
          </div>
          <span class="badge text-bg-secondary">
            {{ formatCount(userWorkspaces.length) }}
          </span>
        </div>

        <form
          ref="workspaceCreateFormElement"
          class="row g-2 align-items-end workspace-create-inline-form"
          @submit.prevent="submitWorkspaceCreate"
        >
          <div class="col-12 col-md-8">
            <label class="form-label" for="me-workspace-name">Новое рабочее пространство</label>
            <input
              id="me-workspace-name"
              v-model.trim="workspaceForm.name"
              class="form-control"
              name="workspace_name"
              type="text"
              maxlength="255"
              required
            >
          </div>
          <div class="col-12 col-md-4 d-grid">
            <button
              class="btn btn-success"
              type="submit"
              :disabled="createWorkspaceMutation.isPending.value"
            >
              {{ createWorkspaceMutation.isPending.value ? "Создание..." : "Создать" }}
            </button>
          </div>
        </form>

        <div v-if="workspaceCreateError" class="alert alert-danger mt-3" role="alert">
          {{ workspaceCreateError }}
        </div>
        <div
          v-if="workspaceLeaveError && !workspaceToLeave"
          class="alert alert-danger mt-3"
          role="alert"
        >
          {{ workspaceLeaveError }}
        </div>
        <div v-if="!hasWorkspaces" class="alert alert-light border mt-3 mb-0" role="status">
          Рабочих пространств пока нет.
        </div>
        <div v-else class="me-list mt-3">
          <article
            v-for="workspace in userWorkspaces"
            :key="workspace.id"
            class="me-list-item"
          >
            <div class="me-list-header">
              <div>
                <h3 class="me-list-title">{{ workspace.name }}</h3>
                <div class="me-meta">
                  <span>{{ formatWorkspaceRole(workspace.role) }}</span>
                  <span>Workspace ID {{ formatCount(workspace.id) }}</span>
                </div>
              </div>
              <div class="me-actions">
                <span
                  v-if="activeWorkspaceId === workspace.id"
                  class="badge text-bg-primary"
                >
                  Активно
                </span>
                <button
                  class="btn btn-outline-primary btn-sm"
                  type="button"
                  :disabled="activeWorkspaceId === workspace.id"
                  @click="selectWorkspace(workspace)"
                >
                  {{ activeWorkspaceId === workspace.id ? "Выбрано" : "Выбрать" }}
                </button>
                <button
                  v-if="workspace.role !== 'owner'"
                  class="btn btn-outline-danger btn-sm"
                  type="button"
                  :disabled="leaveWorkspaceMutation.isPending.value"
                  @click="openLeaveWorkspaceDialog(workspace)"
                >
                  {{ leavingWorkspaceId === workspace.id ? "Выход..." : "Покинуть" }}
                </button>
              </div>
            </div>
          </article>
        </div>
      </section>

      <section class="me-panel me-account-actions">
        <div>
          <h2 class="fs-5 mb-1">Сессия</h2>
          <p class="text-secondary mb-0">Завершить работу с текущим аккаунтом.</p>
        </div>
        <button class="btn btn-outline-danger" type="button" @click="signOut">
          Выйти
        </button>
      </section>

      <Teleport to="body">
        <div
          v-if="workspaceToLeave"
          class="modal fade show d-block"
          tabindex="-1"
          role="dialog"
          aria-modal="true"
          aria-labelledby="leave-workspace-modal-title"
          @click.self="closeLeaveWorkspaceDialog"
        >
          <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
              <div class="modal-header">
                <h2 id="leave-workspace-modal-title" class="modal-title fs-5">
                  Покинуть пространство
                </h2>
                <button
                  class="btn-close"
                  type="button"
                  aria-label="Закрыть"
                  :disabled="leaveWorkspaceMutation.isPending.value"
                  @click="closeLeaveWorkspaceDialog"
                ></button>
              </div>
              <div class="modal-body">
                <div v-if="workspaceLeaveError" class="alert alert-danger" role="alert">
                  {{ workspaceLeaveError }}
                </div>
                <p class="mb-0">
                  Покинуть «{{ workspaceToLeave.name }}»?
                </p>
              </div>
              <div class="modal-footer">
                <button
                  class="btn btn-outline-secondary"
                  type="button"
                  :disabled="leaveWorkspaceMutation.isPending.value"
                  @click="closeLeaveWorkspaceDialog"
                >
                  Отмена
                </button>
                <button
                  class="btn btn-danger"
                  type="button"
                  :disabled="leaveWorkspaceMutation.isPending.value"
                  @click="confirmLeaveWorkspace"
                >
                  {{
                    leavingWorkspaceId === workspaceToLeave.id
                      ? "Выход..."
                      : "Покинуть"
                  }}
                </button>
              </div>
            </div>
          </div>
        </div>
        <div v-if="workspaceToLeave" class="modal-backdrop fade show"></div>
      </Teleport>
    </template>
  </section>
</template>
