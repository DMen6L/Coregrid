<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";

import {
  createWorkspaceInvitation,
  deleteWorkspaceInvitation,
  getWorkspaceInvitations,
} from "../lib/api";
import {
  formatDateTime,
  getCreateErrorMessage,
  getDeleteErrorMessage,
  getRequestErrorMessage,
} from "../lib/format";
import { formatWorkspaceRole } from "../lib/permissions";
import { activeWorkspace, activeWorkspaceId } from "../lib/workspaceSession";
import type {
  WorkspaceInvitationCreatePayload,
  WorkspaceInvitationResponse,
  WorkspaceInvitationRole,
} from "../types/api";

type InvitationStatus = "pending" | "accepted" | "revoked" | "expired";

const props = defineProps<{
  isOpen: boolean;
}>();
const emit = defineEmits<{
  (event: "close"): void;
  (event: "changed"): void;
}>();

const ROLE_OPTIONS: { value: WorkspaceInvitationRole; label: string }[] = [
  { value: "viewer", label: "Наблюдатель" },
  { value: "operator", label: "Оператор" },
  { value: "manager", label: "Менеджер" },
  { value: "admin", label: "Администратор" },
];

const queryClient = useQueryClient();
const createFormElement = ref<HTMLFormElement | null>(null);
const createError = ref("");
const deleteError = ref("");
const deletingInvitationId = ref("");
const invitationForm = reactive({
  email: "",
  role: "viewer" as WorkspaceInvitationRole,
});

const invitationsQuery = useQuery({
  queryKey: computed(() => ["workspace-invitations", activeWorkspaceId.value]),
  queryFn: getWorkspaceInvitations,
  enabled: computed(() => props.isOpen && Boolean(activeWorkspaceId.value)),
});
const createInvitationMutation = useMutation({
  mutationFn: submitInvitationCreateRequest,
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
const isMutating = computed(() => (
  createInvitationMutation.isPending.value || deleteInvitationMutation.isPending.value
));
const modalTitle = computed(() => (
  activeWorkspace.value
    ? `Приглашения: ${activeWorkspace.value.name}`
    : "Приглашения"
));

watch(() => props.isOpen, (isOpen) => {
  if (!isOpen) {
    resetTransientState();
  }
});

function closeModal() {
  if (isMutating.value) {
    return;
  }

  emit("close");
}

function submitInvitationCreate() {
  createError.value = "";

  if (!createFormElement.value?.reportValidity()) {
    return;
  }

  createInvitationMutation.mutate();
}

function submitInvitationCreateRequest() {
  const payload: WorkspaceInvitationCreatePayload = {
    email: normalizeText(invitationForm.email),
    role: invitationForm.role,
  };

  return createWorkspaceInvitation(payload);
}

async function handleInvitationCreateSuccess() {
  resetCreateForm();
  await invalidateInvitationQueries();
  emit("changed");
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
  emit("changed");
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

function resetTransientState() {
  resetCreateForm();
  deleteError.value = "";
  deletingInvitationId.value = "";
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
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="modal fade show d-block"
      tabindex="-1"
      role="dialog"
      aria-modal="true"
      aria-labelledby="workspace-invitations-modal-title"
      @click.self="closeModal"
    >
      <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header">
            <h2 id="workspace-invitations-modal-title" class="modal-title fs-5">
              {{ modalTitle }}
            </h2>
            <button
              class="btn-close"
              type="button"
              aria-label="Закрыть"
              :disabled="isMutating"
              @click="closeModal"
            ></button>
          </div>
          <div class="modal-body">
            <div v-if="!activeWorkspaceId" class="alert alert-light border mb-0" role="status">
              Выберите рабочее пространство.
            </div>
            <template v-else>
              <form
                ref="createFormElement"
                class="row g-2 align-items-end invitation-create-form"
                @submit.prevent="submitInvitationCreate"
              >
                <div class="col-12 col-md-6">
                  <label class="form-label" for="workspace-invitation-email">Почта</label>
                  <input
                    id="workspace-invitation-email"
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
                  <label class="form-label" for="workspace-invitation-role">Роль</label>
                  <select
                    id="workspace-invitation-role"
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
                    class="btn btn-primary"
                    type="submit"
                    :disabled="createInvitationMutation.isPending.value"
                  >
                    {{
                      createInvitationMutation.isPending.value
                        ? "Отправка..."
                        : "Пригласить"
                    }}
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
                class="alert alert-light border mt-3 mb-0"
                role="status"
              >
                Загрузка приглашений...
              </div>
              <div v-else-if="invitationsError" class="alert alert-danger mt-3 mb-0" role="alert">
                {{ invitationsError }}
              </div>
              <div
                v-else-if="invitations.length === 0"
                class="alert alert-light border mt-3 mb-0"
                role="status"
              >
                Приглашений пока нет.
              </div>
              <div v-else class="invitation-list mt-3">
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
                        {{
                          deletingInvitationId === invitation.id
                            ? "Удаление..."
                            : "Удалить"
                        }}
                      </button>
                    </div>
                  </div>
                </article>
              </div>
            </template>
          </div>
          <div class="modal-footer">
            <button
              class="btn btn-outline-secondary"
              type="button"
              :disabled="isMutating"
              @click="closeModal"
            >
              Закрыть
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="isOpen" class="modal-backdrop fade show"></div>
  </Teleport>
</template>
