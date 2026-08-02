<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";

import { getSupplier, patchSupplier } from "../lib/api";
import {
  formatCount,
  formatCurrency,
  getCreateErrorMessage,
  getRequestErrorMessage,
} from "../lib/format";
import type { StockStatus, SupplierResponse, SupplierUpdatePayload } from "../types/api";

type ProductStockStatus = StockStatus | "none";

const props = defineProps<{
  supplierId: number | null;
  isOpen: boolean;
}>();
const emit = defineEmits<{
  (event: "close"): void;
  (event: "saved", supplier: SupplierResponse): void;
}>();

const STOCK_STATUS: Record<ProductStockStatus, { label: string; className: string }> = {
  available: { label: "В наличии", className: "text-bg-success" },
  low: { label: "Мало", className: "text-bg-warning" },
  out: { label: "Нет", className: "text-bg-danger" },
  none: { label: "Без данных", className: "text-bg-secondary" },
};

const queryClient = useQueryClient();
const editFormElement = ref<HTMLFormElement | null>(null);
const isEditing = ref(false);
const editError = ref("");
const editForm = reactive({
  name: "",
  phoneNumber: "",
});

const detailId = computed(() => Number(props.supplierId || 0));
const supplierQuery = useQuery({
  queryKey: computed(() => ["suppliers", "detail", detailId.value]),
  queryFn: () => getSupplier(detailId.value),
  enabled: computed(() => props.isOpen && detailId.value > 0),
});
const updateSupplierMutation = useMutation({
  mutationFn: updateSupplierFromForm,
  onSuccess: handleSupplierUpdateSuccess,
  onError: (error) => {
    editError.value = getCreateErrorMessage(error, "поставщика");
  },
});

const supplier = computed(() => supplierQuery.data.value || null);
const productLinks = computed(() => supplier.value?.product_links || []);
const detailError = computed(() => (
  supplierQuery.error.value
    ? getRequestErrorMessage(supplierQuery.error.value, "детали поставщика")
    : ""
));
const shouldShowContent = computed(() => (
  Boolean(supplier.value)
    && !supplierQuery.isLoading.value
    && !detailError.value
));

watch(() => props.isOpen, (isOpen) => {
  if (!isOpen) {
    resetDetailState();
  }
});

function closeModal() {
  if (updateSupplierMutation.isPending.value) {
    return;
  }

  emit("close");
}

function startEdit() {
  if (!supplier.value) {
    return;
  }

  editError.value = "";
  editForm.name = supplier.value.name || "";
  editForm.phoneNumber = supplier.value.phone_number || "";
  isEditing.value = true;
}

function cancelEdit() {
  if (updateSupplierMutation.isPending.value) {
    return;
  }

  isEditing.value = false;
  editError.value = "";
}

function submitSupplierEdit() {
  editError.value = "";

  if (!editFormElement.value?.reportValidity()) {
    return;
  }

  updateSupplierMutation.mutate();
}

function updateSupplierFromForm() {
  if (!supplier.value) {
    throw createLocalValidationError("Поставщик не загружен.");
  }

  const payload: SupplierUpdatePayload = {
    name: normalizeText(editForm.name),
    phone_number: normalizeText(editForm.phoneNumber),
  };

  return patchSupplier(supplier.value.id, payload);
}

async function handleSupplierUpdateSuccess(updatedSupplier: SupplierResponse) {
  queryClient.setQueryData(["suppliers", "detail", updatedSupplier.id], updatedSupplier);
  isEditing.value = false;
  editError.value = "";

  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ["suppliers"] }),
    queryClient.invalidateQueries({ queryKey: ["products"] }),
    queryClient.invalidateQueries({ queryKey: ["summaries"] }),
  ]);
  emit("saved", updatedSupplier);
}

function resetDetailState() {
  isEditing.value = false;
  editError.value = "";
  editForm.name = "";
  editForm.phoneNumber = "";
}

function getStatusConfig(status: StockStatus | undefined) {
  return STOCK_STATUS[status || "none"] || STOCK_STATUS.none;
}

function normalizeText(value: string) {
  return String(value || "").trim();
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
      aria-labelledby="supplier-detail-modal-title"
      @click.self="closeModal"
    >
      <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header">
            <h2 id="supplier-detail-modal-title" class="modal-title fs-5">
              {{ supplier ? supplier.name || `Поставщик #${formatCount(supplier.id)}` : "Поставщик" }}
            </h2>
            <div class="ms-auto d-flex align-items-center gap-2">
              <button
                v-if="shouldShowContent && !isEditing"
                class="btn btn-sm btn-outline-primary"
                type="button"
                :disabled="updateSupplierMutation.isPending.value"
                @click="startEdit"
              >
                Редактировать
              </button>
              <button
                class="btn-close"
                type="button"
                aria-label="Закрыть"
                :disabled="updateSupplierMutation.isPending.value"
                @click="closeModal"
              ></button>
            </div>
          </div>

          <div class="modal-body">
            <div v-if="supplierQuery.isLoading.value" class="text-secondary py-4" aria-live="polite">
              Загрузка поставщика...
            </div>
            <div v-else-if="detailError" class="alert alert-danger" role="alert">
              {{ detailError }}
            </div>

            <div v-if="shouldShowContent" class="supplier-detail-content">
              <div v-if="editError" class="alert alert-danger" role="alert">
                {{ editError }}
              </div>

              <div v-if="!isEditing">
                <div class="supplier-detail-summary mb-4">
                  <div>
                    <div class="supplier-detail-label">ID</div>
                    <div class="fw-semibold">{{ formatCount(supplier?.id) }}</div>
                  </div>
                  <div>
                    <div class="supplier-detail-label">Название</div>
                    <div class="fw-semibold">{{ supplier?.name || "Не указано" }}</div>
                  </div>
                  <div>
                    <div class="supplier-detail-label">Телефон</div>
                    <div class="fw-semibold">{{ supplier?.phone_number || "Не указан" }}</div>
                  </div>
                  <div>
                    <div class="supplier-detail-label">Товары</div>
                    <div class="fw-semibold">{{ formatCount(productLinks.length) }}</div>
                  </div>
                </div>

                <div class="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-2">
                  <h3 class="fs-6 mb-0">Связанные товары</h3>
                </div>
                <div v-if="productLinks.length === 0" class="alert alert-light border" role="status">
                  Поставщик пока не связан с товарами.
                </div>
                <div v-else class="table-responsive supplier-detail-product-links-table">
                  <table class="table table-hover align-middle mb-0">
                    <thead>
                      <tr>
                        <th scope="col">Товар</th>
                        <th scope="col">Остаток</th>
                        <th scope="col">Закупка</th>
                        <th scope="col">Маржа</th>
                        <th scope="col">Продажа</th>
                        <th scope="col">Статус</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="link in productLinks" :key="link.id">
                        <td>
                          <div class="fw-semibold">
                            {{ link.product_name || `Товар #${formatCount(link.product_id)}` }}
                          </div>
                          <div class="supplier-meta">ID {{ formatCount(link.product_id) }}</div>
                        </td>
                        <td>{{ formatCount(link.quantity) }}</td>
                        <td>{{ formatCurrency(link.purchase_price) }}</td>
                        <td>{{ formatCount(link.margin_percent) }}%</td>
                        <td>{{ formatCurrency(link.sale_price) }}</td>
                        <td>
                          <span class="badge status-badge" :class="getStatusConfig(link.stock_status).className">
                            {{ getStatusConfig(link.stock_status).label }}
                          </span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <form
                v-else
                ref="editFormElement"
                class="supplier-detail-edit-form"
                @submit.prevent="submitSupplierEdit"
              >
                <div class="row g-3">
                  <div class="col-12 col-lg-7">
                    <label class="form-label" for="supplier-detail-edit-name">Название</label>
                    <input
                      id="supplier-detail-edit-name"
                      v-model="editForm.name"
                      class="form-control"
                      name="name"
                      type="text"
                      maxlength="255"
                      autocomplete="organization"
                      required
                      :disabled="updateSupplierMutation.isPending.value"
                    >
                  </div>
                  <div class="col-12 col-lg-5">
                    <label class="form-label" for="supplier-detail-edit-phone-number">Телефон</label>
                    <input
                      id="supplier-detail-edit-phone-number"
                      v-model="editForm.phoneNumber"
                      class="form-control"
                      name="phone_number"
                      type="tel"
                      inputmode="tel"
                      pattern="(8[0-9]{10}|[+]7[0-9]{10})"
                      maxlength="12"
                      autocomplete="tel"
                      placeholder="+77001234567"
                      required
                      :disabled="updateSupplierMutation.isPending.value"
                    >
                    <div class="form-text">Формат: +7XXXXXXXXXX или 8XXXXXXXXXX.</div>
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
              :disabled="updateSupplierMutation.isPending.value"
              @click="cancelEdit"
            >
              Отмена
            </button>
            <button
              v-if="isEditing"
              class="btn btn-primary"
              type="button"
              :disabled="updateSupplierMutation.isPending.value"
              @click="submitSupplierEdit"
            >
              {{ updateSupplierMutation.isPending.value ? "Сохранение..." : "Сохранить" }}
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="isOpen" class="modal-backdrop fade show"></div>
  </Teleport>
</template>
