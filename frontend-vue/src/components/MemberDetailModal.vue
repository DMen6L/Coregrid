<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";

import {
  deleteWorkspaceMember,
  getWorkspaceMember,
  patchWorkspaceMemberRole,
} from "../lib/api";
import {
  formatCount,
  getCreateErrorMessage,
  getDeleteErrorMessage,
  getRequestErrorMessage,
} from "../lib/format";
import { formatWorkspaceRole } from "../lib/permissions";
import { activeWorkspaceId } from "../lib/workspaceSession";
import type { WorkspaceAssignableRole, WorkspaceMembershipResponse } from "../types/api";

const ROLE_OPTIONS: { value: WorkspaceAssignableRole; label: string }[] = [
  { value: "viewer", label: "Наблюдатель" },
  { value: "operator", label: "Оператор" },
  { value: "manager", label: "Менеджер" },
  { value: "admin", label: "Администратор" },
];

const props = defineProps<{
  memberId: number | null;
  isOpen: boolean;
}>();
const emit = defineEmits<{
  (event: "close"): void;
  (event: "changed", member: WorkspaceMembershipResponse): void;
  (event: "deleted", memberId: number): void;
}>();

const queryClient = useQueryClient();
const roleFormElement = ref<HTMLFormElement | null>(null);
const roleForm = reactive({
  role: "viewer" as WorkspaceAssignableRole,
});
const roleError = ref("");
const deleteError = ref("");
const detailId = computed(() => Number(props.memberId || 0));
const detailQueryKey = computed(() => [
  "workspace-members",
  activeWorkspaceId.value,
  "detail",
  detailId.value,
]);
const memberQuery = useQuery({
  queryKey: detailQueryKey,
  queryFn: () => getWorkspaceMember(detailId.value),
  enabled: computed(() => Boolean(activeWorkspaceId.value) && props.isOpen && detailId.value > 0),
});
const updateRoleMutation = useMutation({
  mutationFn: (newRole: WorkspaceAssignableRole) => patchWorkspaceMemberRole(detailId.value, newRole),
  onSuccess: handleMemberRoleUpdateSuccess,
  onError: (error) => {
    roleError.value = getCreateErrorMessage(error, "роль участника");
  },
});
const deleteMemberMutation = useMutation({
  mutationFn: () => deleteWorkspaceMember(detailId.value),
  onSuccess: handleMemberDeleteSuccess,
  onError: (error) => {
    deleteError.value = getDeleteErrorMessage(error, "участника");
  },
});

const member = computed(() => memberQuery.data.value || null);
const isOwnerMember = computed(() => member.value?.role === "owner");
const isActionPending = computed(() => (
  updateRoleMutation.isPending.value || deleteMemberMutation.isPending.value
));
const canSubmitRole = computed(() => (
  Boolean(member.value)
    && !isOwnerMember.value
    && roleForm.role !== member.value?.role
    && !isActionPending.value
));
const detailError = computed(() => (
  memberQuery.error.value
    ? getRequestErrorMessage(memberQuery.error.value, "детали участника")
    : ""
));
const shouldShowContent = computed(() => (
  Boolean(member.value)
    && !memberQuery.isLoading.value
    && !detailError.value
));

watch(member, (nextMember) => {
  resetActionErrors();

  roleForm.role = isAssignableRole(nextMember?.role)
    ? nextMember.role
    : "viewer";
}, { immediate: true });

watch(() => props.isOpen, (isOpen) => {
  if (!isOpen) {
    resetActionErrors();
  }
});

function closeModal() {
  if (isActionPending.value) {
    return;
  }

  emit("close");
}

function submitRoleUpdate() {
  roleError.value = "";
  deleteError.value = "";

  if (!roleFormElement.value?.reportValidity()) {
    return;
  }

  if (!member.value || isOwnerMember.value || roleForm.role === member.value.role) {
    return;
  }

  updateRoleMutation.mutate(roleForm.role);
}

function deleteMember() {
  if (!member.value || isOwnerMember.value || deleteMemberMutation.isPending.value) {
    return;
  }

  const memberLabel = member.value.name || member.value.email || `#${formatCount(member.value.id)}`;

  if (!window.confirm(`Удалить участника ${memberLabel} из рабочего пространства?`)) {
    return;
  }

  roleError.value = "";
  deleteError.value = "";
  deleteMemberMutation.mutate();
}

function handleMemberRoleUpdateSuccess(updatedMember: WorkspaceMembershipResponse) {
  queryClient.setQueryData(detailQueryKey.value, updatedMember);
  roleError.value = "";

  if (isAssignableRole(updatedMember.role)) {
    roleForm.role = updatedMember.role;
  }

  emit("changed", updatedMember);
}

function handleMemberDeleteSuccess() {
  const deletedId = detailId.value;

  deleteError.value = "";
  emit("deleted", deletedId);
}

function resetActionErrors() {
  roleError.value = "";
  deleteError.value = "";
}

function isAssignableRole(role: unknown): role is WorkspaceAssignableRole {
  return role === "viewer"
    || role === "operator"
    || role === "manager"
    || role === "admin";
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
      aria-labelledby="member-detail-modal-title"
      @click.self="closeModal"
    >
      <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header">
            <h2 id="member-detail-modal-title" class="modal-title fs-5">
              {{ member ? member.name || member.email || `Участник #${formatCount(member.id)}` : "Участник" }}
            </h2>
            <button
              class="btn-close"
              type="button"
              aria-label="Закрыть"
              :disabled="isActionPending"
              @click="closeModal"
            ></button>
          </div>

          <div class="modal-body">
            <div v-if="memberQuery.isLoading.value" class="text-secondary py-4" aria-live="polite">
              Загрузка участника...
            </div>
            <div v-else-if="detailError" class="alert alert-danger" role="alert">
              {{ detailError }}
            </div>

            <div v-if="shouldShowContent" class="member-detail-content">
              <div class="member-detail-summary">
                <div>
                  <div class="member-detail-label">Membership ID</div>
                  <div class="fw-semibold">{{ formatCount(member?.id) }}</div>
                </div>
                <div>
                  <div class="member-detail-label">User ID</div>
                  <div class="fw-semibold">{{ formatCount(member?.user_id) }}</div>
                </div>
                <div>
                  <div class="member-detail-label">Имя</div>
                  <div class="fw-semibold">{{ member?.name || "Не указано" }}</div>
                </div>
                <div>
                  <div class="member-detail-label">Роль</div>
                  <span class="badge text-bg-primary">{{ formatWorkspaceRole(member?.role) }}</span>
                </div>
              </div>

              <div class="mt-3">
                <div class="member-detail-label mb-1">Email</div>
                <div class="fw-semibold member-email">{{ member?.email || "Не указан" }}</div>
              </div>

              <div v-if="isOwnerMember" class="alert alert-light border mt-4 mb-0" role="status">
                Роль владельца нельзя изменить или удалить из этого окна.
              </div>

              <form
                ref="roleFormElement"
                class="member-role-form mt-4"
                @submit.prevent="submitRoleUpdate"
              >
                <div v-if="roleError" class="alert alert-danger" role="alert">
                  {{ roleError }}
                </div>

                <div class="row g-2 align-items-end">
                  <div class="col-12 col-md-7">
                    <label class="form-label" for="member-detail-role">Новая роль</label>
                    <select
                      id="member-detail-role"
                      v-model="roleForm.role"
                      class="form-select"
                      name="role"
                      required
                      :disabled="isOwnerMember || isActionPending"
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
                  <div class="col-12 col-md-5 d-grid">
                    <button
                      class="btn btn-primary"
                      type="submit"
                      :disabled="!canSubmitRole"
                    >
                      {{ updateRoleMutation.isPending.value ? "Сохранение..." : "Сохранить роль" }}
                    </button>
                  </div>
                </div>
              </form>

              <div class="member-danger-zone mt-4">
                <div>
                  <div class="member-detail-label mb-1">Доступ</div>
                  <div class="fw-semibold">Удаление из рабочего пространства</div>
                </div>
                <button
                  class="btn btn-outline-danger"
                  type="button"
                  :disabled="isOwnerMember || isActionPending"
                  @click="deleteMember"
                >
                  {{ deleteMemberMutation.isPending.value ? "Удаление..." : "Удалить участника" }}
                </button>
              </div>
              <div v-if="deleteError" class="alert alert-danger mt-3 mb-0" role="alert">
                {{ deleteError }}
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button
              class="btn btn-outline-secondary"
              type="button"
              :disabled="isActionPending"
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
