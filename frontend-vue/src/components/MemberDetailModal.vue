<script setup lang="ts">
import { computed } from "vue";
import { useQuery } from "@tanstack/vue-query";

import { getWorkspaceMember } from "../lib/api";
import { formatCount, getRequestErrorMessage } from "../lib/format";
import { formatWorkspaceRole } from "../lib/permissions";
import { activeWorkspaceId } from "../lib/workspaceSession";

const props = defineProps<{
  memberId: number | null;
  isOpen: boolean;
}>();
const emit = defineEmits<{
  (event: "close"): void;
}>();

const detailId = computed(() => Number(props.memberId || 0));
const memberQuery = useQuery({
  queryKey: computed(() => ["workspace-members", activeWorkspaceId.value, "detail", detailId.value]),
  queryFn: () => getWorkspaceMember(detailId.value),
  enabled: computed(() => Boolean(activeWorkspaceId.value) && props.isOpen && detailId.value > 0),
});

const member = computed(() => memberQuery.data.value || null);
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

function closeModal() {
  emit("close");
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
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn btn-outline-secondary" type="button" @click="closeModal">
              Закрыть
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="isOpen" class="modal-backdrop fade show"></div>
  </Teleport>
</template>
