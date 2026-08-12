<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";

import { acceptMyInvitation, getMyInvitations } from "../lib/api";
import { formatDateTime, getCreateErrorMessage, getRequestErrorMessage } from "../lib/format";
import { formatWorkspaceRole } from "../lib/permissions";
import type { WorkspaceInvitationResponse, WorkspaceResponse } from "../types/api";

const props = defineProps<{
  isOpen: boolean;
}>();
const emit = defineEmits<{
  (event: "close"): void;
  (event: "accepted", workspace: WorkspaceResponse): void;
}>();

const queryClient = useQueryClient();
const acceptingInvitationId = ref("");
const acceptError = ref("");

const invitationsQuery = useQuery({
  queryKey: ["me", "invitations"],
  queryFn: getMyInvitations,
  enabled: computed(() => props.isOpen),
});
const acceptInvitationMutation = useMutation({
  mutationFn: (invitationId: string) => acceptMyInvitation(invitationId),
  onSuccess: handleInvitationAccepted,
  onError: (error) => {
    acceptError.value = getCreateErrorMessage(error, "приглашение");
  },
  onSettled: () => {
    acceptingInvitationId.value = "";
  },
});

const invitations = computed(() => sortInvitations(invitationsQuery.data.value || []));
const invitationsError = computed(() => (
  invitationsQuery.error.value
    ? getRequestErrorMessage(invitationsQuery.error.value, "приглашения")
    : ""
));

watch(() => props.isOpen, (isOpen) => {
  if (!isOpen) {
    acceptError.value = "";
    acceptingInvitationId.value = "";
  }
});

function closeModal() {
  if (acceptInvitationMutation.isPending.value) {
    return;
  }

  emit("close");
}

function acceptInvitation(invitation: WorkspaceInvitationResponse) {
  acceptError.value = "";
  acceptingInvitationId.value = invitation.id;
  acceptInvitationMutation.mutate(invitation.id);
}

async function handleInvitationAccepted(workspace: WorkspaceResponse) {
  acceptError.value = "";
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ["me"] }),
    queryClient.invalidateQueries({ queryKey: ["me", "invitations"] }),
  ]);
  emit("accepted", workspace);
}

function sortInvitations(invitations: WorkspaceInvitationResponse[]) {
  return [...invitations].sort((left, right) => (
    getTime(right.created_at) - getTime(left.created_at)
  ));
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
      aria-labelledby="my-invitations-modal-title"
      @click.self="closeModal"
    >
      <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header">
            <h2 id="my-invitations-modal-title" class="modal-title fs-5">
              Мои приглашения
            </h2>
            <button
              class="btn-close"
              type="button"
              aria-label="Закрыть"
              :disabled="acceptInvitationMutation.isPending.value"
              @click="closeModal"
            ></button>
          </div>
          <div class="modal-body">
            <div v-if="acceptError" class="alert alert-danger" role="alert">
              {{ acceptError }}
            </div>

            <div
              v-if="invitationsQuery.isLoading.value"
              class="alert alert-light border mb-0"
              role="status"
            >
              Загрузка приглашений...
            </div>
            <div v-else-if="invitationsError" class="alert alert-danger mb-0" role="alert">
              {{ invitationsError }}
            </div>
            <div v-else-if="invitations.length === 0" class="alert alert-light border mb-0" role="status">
              Активных приглашений нет.
            </div>
            <div v-else class="invitation-list">
              <article
                v-for="invitation in invitations"
                :key="invitation.id"
                class="invitation-list-item"
              >
                <div class="invitation-list-header">
                  <div>
                    <h3 class="invitation-title">
                      Рабочее пространство #{{ invitation.workspace_id }}
                    </h3>
                    <div class="invitation-meta">
                      <span>{{ formatWorkspaceRole(invitation.role) }}</span>
                      <span>Истекает: {{ formatDateTime(invitation.expires_at) }}</span>
                    </div>
                  </div>
                  <button
                    class="btn btn-primary btn-sm"
                    type="button"
                    :disabled="acceptInvitationMutation.isPending.value"
                    @click="acceptInvitation(invitation)"
                  >
                    {{
                      acceptingInvitationId === invitation.id
                        ? "Принятие..."
                        : "Принять"
                    }}
                  </button>
                </div>
              </article>
            </div>
          </div>
          <div class="modal-footer">
            <button
              class="btn btn-outline-secondary"
              type="button"
              :disabled="acceptInvitationMutation.isPending.value"
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
