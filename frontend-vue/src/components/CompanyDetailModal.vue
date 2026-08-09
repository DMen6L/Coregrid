<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";

import { getCompany, patchCompany } from "../lib/api";
import { formatCount, getCreateErrorMessage, getRequestErrorMessage } from "../lib/format";
import { activeWorkspaceId } from "../lib/workspaceSession";
import type { CompanyResponse, CompanyUpdatePayload } from "../types/api";

const props = defineProps<{
  companyId: number | null;
  isOpen: boolean;
}>();
const emit = defineEmits<{
  (event: "close"): void;
  (event: "saved", company: CompanyResponse): void;
}>();

const queryClient = useQueryClient();
const editFormElement = ref<HTMLFormElement | null>(null);
const isEditing = ref(false);
const editError = ref("");
const editForm = reactive({
  name: "",
  iin: "",
});

const detailId = computed(() => Number(props.companyId || 0));
const companyQuery = useQuery({
  queryKey: computed(() => ["companies", activeWorkspaceId.value, "detail", detailId.value]),
  queryFn: () => getCompany(detailId.value),
  enabled: computed(() => Boolean(activeWorkspaceId.value) && props.isOpen && detailId.value > 0),
});
const updateCompanyMutation = useMutation({
  mutationFn: updateCompanyFromForm,
  onSuccess: handleCompanyUpdateSuccess,
  onError: (error) => {
    editError.value = getCreateErrorMessage(error, "компанию");
  },
});

const company = computed(() => companyQuery.data.value || null);
const detailError = computed(() => (
  companyQuery.error.value
    ? getRequestErrorMessage(companyQuery.error.value, "детали компании")
    : ""
));
const shouldShowContent = computed(() => (
  Boolean(company.value)
    && !companyQuery.isLoading.value
    && !detailError.value
));

watch(() => props.isOpen, (isOpen) => {
  if (!isOpen) {
    resetDetailState();
  }
});

function closeModal() {
  if (updateCompanyMutation.isPending.value) {
    return;
  }

  emit("close");
}

function startEdit() {
  if (!company.value) {
    return;
  }

  editError.value = "";
  editForm.name = company.value.name || "";
  editForm.iin = company.value.iin || "";
  isEditing.value = true;
}

function cancelEdit() {
  if (updateCompanyMutation.isPending.value) {
    return;
  }

  isEditing.value = false;
  editError.value = "";
}

function submitCompanyEdit() {
  editError.value = "";

  if (!editFormElement.value?.reportValidity()) {
    return;
  }

  updateCompanyMutation.mutate();
}

function updateCompanyFromForm() {
  if (!company.value) {
    throw createLocalValidationError("Компания не загружена.");
  }

  const payload: CompanyUpdatePayload = {
    name: normalizeText(editForm.name),
    iin: normalizeOptionalText(editForm.iin),
  };

  return patchCompany(company.value.id, payload);
}

async function handleCompanyUpdateSuccess(updatedCompany: CompanyResponse) {
  queryClient.setQueryData(
    ["companies", activeWorkspaceId.value, "detail", updatedCompany.id],
    updatedCompany,
  );
  isEditing.value = false;
  editError.value = "";

  await queryClient.invalidateQueries({ queryKey: ["companies", activeWorkspaceId.value] });
  emit("saved", updatedCompany);
}

function resetDetailState() {
  isEditing.value = false;
  editError.value = "";
  editForm.name = "";
  editForm.iin = "";
}

function normalizeText(value: string) {
  return String(value || "").trim();
}

function normalizeOptionalText(value: string) {
  return normalizeText(value) || null;
}

function createLocalValidationError(message: string) {
  const error = new Error(message) as Error & { data: { detail: string } };

  error.data = { detail: message };
  return error;
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
      aria-labelledby="company-detail-modal-title"
      @click.self="closeModal"
    >
      <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header">
            <h2 id="company-detail-modal-title" class="modal-title fs-5">
              {{ company ? company.name || `Компания #${formatCount(company.id)}` : "Компания" }}
            </h2>
            <div class="ms-auto d-flex align-items-center gap-2">
              <button
                v-if="shouldShowContent && !isEditing"
                class="btn btn-sm btn-outline-primary"
                type="button"
                :disabled="updateCompanyMutation.isPending.value"
                @click="startEdit"
              >
                Редактировать
              </button>
              <button
                class="btn-close"
                type="button"
                aria-label="Закрыть"
                :disabled="updateCompanyMutation.isPending.value"
                @click="closeModal"
              ></button>
            </div>
          </div>

          <div class="modal-body">
            <div v-if="companyQuery.isLoading.value" class="text-secondary py-4" aria-live="polite">
              Загрузка компании...
            </div>
            <div v-else-if="detailError" class="alert alert-danger" role="alert">
              {{ detailError }}
            </div>

            <div v-if="shouldShowContent" class="company-detail-content">
              <div v-if="editError" class="alert alert-danger" role="alert">
                {{ editError }}
              </div>

              <div v-if="!isEditing" class="company-detail-summary mb-4">
                <div>
                  <div class="company-detail-label">ID</div>
                  <div class="fw-semibold">{{ formatCount(company?.id) }}</div>
                </div>
                <div>
                  <div class="company-detail-label">Название</div>
                  <div class="fw-semibold">{{ company?.name || "Не указано" }}</div>
                </div>
                <div>
                  <div class="company-detail-label">ИИН</div>
                  <div class="fw-semibold" :class="{ 'text-secondary': !company?.iin }">
                    {{ company?.iin || "Не указан" }}
                  </div>
                </div>
              </div>

              <form
                v-else
                ref="editFormElement"
                class="company-detail-edit-form"
                @submit.prevent="submitCompanyEdit"
              >
                <div class="row g-3">
                  <div class="col-12 col-lg-7">
                    <label class="form-label" for="company-detail-edit-name">Название</label>
                    <input
                      id="company-detail-edit-name"
                      v-model="editForm.name"
                      class="form-control"
                      name="name"
                      type="text"
                      maxlength="255"
                      autocomplete="organization"
                      required
                      :disabled="updateCompanyMutation.isPending.value"
                    >
                  </div>
                  <div class="col-12 col-lg-5">
                    <label class="form-label" for="company-detail-edit-iin">ИИН</label>
                    <input
                      id="company-detail-edit-iin"
                      v-model="editForm.iin"
                      class="form-control"
                      name="iin"
                      type="text"
                      inputmode="numeric"
                      pattern="[0-9]{12}"
                      minlength="12"
                      maxlength="12"
                      autocomplete="off"
                      :disabled="updateCompanyMutation.isPending.value"
                    >
                    <div class="form-text">Можно оставить пустым. Если указан, 12 цифр без пробелов.</div>
                  </div>
                </div>
              </form>
            </div>
          </div>

          <div class="modal-footer">
            <button
              v-if="isEditing"
              class="btn btn-outline-secondary"
              type="button"
              :disabled="updateCompanyMutation.isPending.value"
              @click="cancelEdit"
            >
              Отмена
            </button>
            <button
              v-if="isEditing"
              class="btn btn-primary"
              type="button"
              :disabled="updateCompanyMutation.isPending.value"
              @click="submitCompanyEdit"
            >
              {{ updateCompanyMutation.isPending.value ? "Сохранение..." : "Сохранить" }}
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="isOpen" class="modal-backdrop fade show"></div>
  </Teleport>
</template>
