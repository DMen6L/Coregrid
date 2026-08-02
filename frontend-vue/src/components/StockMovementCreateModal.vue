<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useMutation } from "@tanstack/vue-query";

import {
  FIRST_PAGE,
  createRestock,
  createSale,
  getProduct,
  getProducts,
} from "../lib/api";
import {
  DEFAULT_QUANTITY_UNIT,
  formatCount,
  formatCurrency,
  formatQuantity,
  getCreateErrorMessage,
} from "../lib/format";
import type {
  ProductResponse,
  ProductSupplierResponse,
  ProductSummaryResponse,
  RestockCreatePayload,
  RestockResponse,
  SaleCreatePayload,
  SaleResponse,
} from "../types/api";

type MovementKind = "restock" | "sale";
type MovementLineDraft = {
  id: number;
  productSearch: string;
  productLookupTerm: string;
  productLookupResults: ProductSummaryResponse[];
  productLookupError: string;
  productLookupRequestId: number;
  productDetailError: string;
  productDetailRequestId: number;
  isProductLookupLoading: boolean;
  isProductDetailLoading: boolean;
  selectedProduct: ProductResponse | null;
  selectedSupplierLinkId: string;
  quantity: number | string;
  unitCostSnapshot: string;
};

const props = defineProps<{
  isOpen: boolean;
  kind: MovementKind;
}>();
const emit = defineEmits<{
  (event: "close"): void;
  (event: "created", movement: RestockResponse | SaleResponse): void;
}>();

const PRODUCT_LOOKUP_PAGE_SIZE = 10;
const PRODUCT_SEARCH_MIN_LENGTH = 2;

const formElement = ref<HTMLFormElement | null>(null);
const note = ref("");
const lines = ref<MovementLineDraft[]>([]);
const createError = ref("");
const nextLineId = ref(1);

const labels = computed(() => (
  props.kind === "restock"
    ? {
      title: "Добавить пополнение",
      movement: "пополнение",
      movementAccusative: "пополнение",
      lines: "пополнения",
      quantity: "Количество пополнения",
      submit: "Создать пополнение",
      submitting: "Сохранение пополнения...",
    }
    : {
      title: "Добавить продажу",
      movement: "продажу",
      movementAccusative: "продажу",
      lines: "продажи",
      quantity: "Количество продажи",
      submit: "Создать продажу",
      submitting: "Сохранение продажи...",
    }
));
const isSubmitting = computed(() => createMovementMutation.isPending.value);
const shouldShowUnitCost = computed(() => props.kind === "restock");

const createMovementMutation = useMutation({
  mutationFn: createMovementFromForm,
  onSuccess: (movement) => {
    emit("created", movement);
    resetForm();
  },
  onError: (error) => {
    createError.value = getCreateErrorMessage(error, labels.value.movement);
  },
});

watch(() => props.isOpen, (isOpen) => {
  if (isOpen && lines.value.length === 0) {
    addLine();
  }

  if (!isOpen && !isSubmitting.value) {
    resetForm();
  }
});

function closeModal() {
  if (isSubmitting.value) {
    return;
  }

  emit("close");
}

function addLine() {
  lines.value.push(createLineDraft());
  createError.value = "";
}

function removeLine(lineId: number) {
  if (isSubmitting.value) {
    return;
  }

  lines.value = lines.value.filter((line) => line.id !== lineId);
  createError.value = "";
}

function submitCreate() {
  createError.value = "";

  if (!formElement.value?.reportValidity()) {
    return;
  }

  const validationMessage = validateLines();
  if (validationMessage) {
    createError.value = validationMessage;
    return;
  }

  createMovementMutation.mutate();
}

async function runProductLookup(draft: MovementLineDraft) {
  const search = normalizeText(draft.productSearch);

  draft.productSearch = search;
  draft.productLookupTerm = search;
  draft.productLookupResults = [];
  draft.productLookupError = "";
  clearSelectedProduct(draft, { keepSearch: true });

  if (search.length < PRODUCT_SEARCH_MIN_LENGTH) {
    draft.productLookupTerm = "";
    draft.productLookupError = `Введите минимум ${formatCount(PRODUCT_SEARCH_MIN_LENGTH)} символа.`;
    return;
  }

  draft.isProductLookupLoading = true;
  const requestId = draft.productLookupRequestId + 1;
  draft.productLookupRequestId = requestId;

  try {
    const response = await getProducts({
      search,
      page: FIRST_PAGE,
      pageSize: PRODUCT_LOOKUP_PAGE_SIZE,
    });

    if (draft.productLookupRequestId !== requestId) {
      return;
    }

    draft.productLookupResults = response.items || [];
  } catch (error) {
    if (draft.productLookupRequestId !== requestId) {
      return;
    }

    console.error("Could not search stock movement products:", error);
    draft.productLookupError = "Не удалось загрузить товары.";
  } finally {
    if (draft.productLookupRequestId === requestId) {
      draft.isProductLookupLoading = false;
    }
  }
}

async function selectProduct(draft: MovementLineDraft, product: ProductSummaryResponse) {
  clearSelectedProduct(draft, { keepSearch: true });
  draft.productSearch = product.name || "";
  draft.productLookupResults = [];
  draft.productLookupError = "";
  draft.productDetailError = "";
  draft.isProductDetailLoading = true;

  const requestId = draft.productDetailRequestId + 1;
  draft.productDetailRequestId = requestId;

  try {
    const productDetail = await getProduct(product.id);

    if (draft.productDetailRequestId !== requestId) {
      return;
    }

    draft.selectedProduct = productDetail;
  } catch (error) {
    if (draft.productDetailRequestId !== requestId) {
      return;
    }

    console.error("Could not load stock movement product detail:", error);
    draft.productDetailError = "Не удалось загрузить поставщиков товара.";
  } finally {
    if (draft.productDetailRequestId === requestId) {
      draft.isProductDetailLoading = false;
    }
  }
}

function clearSelectedProduct(
  draft: MovementLineDraft,
  { keepSearch = false }: { keepSearch?: boolean } = {},
) {
  draft.selectedProduct = null;
  draft.selectedSupplierLinkId = "";
  draft.productDetailError = "";

  if (!keepSearch) {
    draft.productSearch = "";
  }
}

function handleSupplierChange(draft: MovementLineDraft) {
  const selectedLink = getSelectedSupplierLink(draft);

  if (props.kind === "sale" && selectedLink) {
    const availableQuantity = Number(selectedLink.quantity || 0);

    if (Number(draft.quantity || 0) > availableQuantity) {
      draft.quantity = availableQuantity || 1;
    }
  }
}

async function createMovementFromForm() {
  const payload = props.kind === "restock"
    ? getRestockPayload()
    : getSalePayload();

  return props.kind === "restock"
    ? createRestock(payload as RestockCreatePayload)
    : createSale(payload as SaleCreatePayload);
}

function getRestockPayload(): RestockCreatePayload {
  return {
    note: normalizeOptionalText(note.value),
    lines: lines.value.map((line) => {
      const payload = {
        product_supplier_id: Number(line.selectedSupplierLinkId),
        restock_quantity: normalizePositiveInteger(line.quantity),
      };
      const unitCostSnapshot = normalizeOptionalNonNegativeInteger(line.unitCostSnapshot);

      return unitCostSnapshot === null
        ? payload
        : { ...payload, unit_cost_snapshot: unitCostSnapshot };
    }),
  };
}

function getSalePayload(): SaleCreatePayload {
  return {
    note: normalizeOptionalText(note.value),
    lines: lines.value.map((line) => ({
      product_supplier_id: Number(line.selectedSupplierLinkId),
      sale_quantity: normalizePositiveInteger(line.quantity),
    })),
  };
}

function validateLines() {
  if (lines.value.length === 0) {
    return `Добавьте хотя бы одну позицию ${labels.value.lines}.`;
  }

  const selectedSupplierLinks = new Set<number>();

  for (const [index, line] of lines.value.entries()) {
    const lineLabel = `позиции ${formatCount(index + 1)}`;
    const supplierLinkId = Number(line.selectedSupplierLinkId);
    const quantity = Number(line.quantity);
    const unitCost = normalizeOptionalNonNegativeInteger(line.unitCostSnapshot);

    if (!line.selectedProduct) {
      return `Выберите товар для ${lineLabel}.`;
    }

    if (!supplierLinkId) {
      return `Выберите поставщика для ${lineLabel}.`;
    }

    if (selectedSupplierLinks.has(supplierLinkId)) {
      return `Один и тот же поставщик товара не должен повторяться в ${labels.value.lines}.`;
    }

    selectedSupplierLinks.add(supplierLinkId);

    if (!Number.isFinite(quantity) || quantity <= 0) {
      return `Введите количество для ${lineLabel}.`;
    }

    if (line.unitCostSnapshot.trim() && unitCost === null) {
      return `Введите корректную цену закупки для ${lineLabel}.`;
    }

    if (props.kind === "sale") {
      const selectedLink = getSelectedSupplierLink(line);
      const availableQuantity = Number(selectedLink?.quantity || 0);

      if (quantity > availableQuantity) {
        return `Количество продажи больше остатка для ${lineLabel}.`;
      }
    }
  }

  return "";
}

function getSupplierLinks(draft: MovementLineDraft) {
  return draft.selectedProduct?.supplier_links || [];
}

function getSelectedSupplierLink(draft: MovementLineDraft) {
  const supplierLinkId = Number(draft.selectedSupplierLinkId);

  return getSupplierLinks(draft).find((link) => link.id === supplierLinkId) || null;
}

function getSupplierPlaceholder(draft: MovementLineDraft) {
  const links = getSupplierLinks(draft);

  if (!draft.selectedProduct) {
    return "Сначала выберите товар";
  }

  if (!links.length) {
    return "У товара нет поставщиков";
  }

  if (props.kind === "sale" && links.every((link) => Number(link.quantity || 0) <= 0)) {
    return "Нет поставщиков с остатком";
  }

  return "Выберите поставщика";
}

function getProductUnit(draft: MovementLineDraft) {
  return draft.selectedProduct?.quantity_unit || DEFAULT_QUANTITY_UNIT;
}

function getProductMeta(product: ProductSummaryResponse) {
  return [
    product.company_name || "Компания не указана",
    `Остаток: ${formatQuantity(product.total_quantity, product.quantity_unit)}`,
    `Поставщиков: ${formatCount(product.suppliers_count)}`,
  ].join(" | ");
}

function getSelectedProductMeta(product: ProductResponse) {
  return [
    product.company_name || "Компания не указана",
    `Единица: ${product.quantity_unit || "не указана"}`,
    `Порог: ${formatQuantity(product.low_stock_threshold, product.quantity_unit)}`,
  ].join(" | ");
}

function getSupplierOptionLabel(link: ProductSupplierResponse, unit: string) {
  return [
    link.supplier_name || `Поставщик #${formatCount(link.supplier_id)}`,
    `остаток ${formatQuantity(link.quantity, unit)}`,
    `продажа ${formatCurrency(link.sale_price)}`,
  ].join(" | ");
}

function getSupplierMeta(draft: MovementLineDraft) {
  const selectedLink = getSelectedSupplierLink(draft);

  if (!selectedLink) {
    return "";
  }

  const unit = getProductUnit(draft);

  return [
    `Остаток: ${formatQuantity(selectedLink.quantity, unit)}`,
    `Закупка: ${formatCurrency(selectedLink.purchase_price)}`,
    `Продажа: ${formatCurrency(selectedLink.sale_price)}`,
  ].join(" | ");
}

function getQuantityMax(draft: MovementLineDraft) {
  if (props.kind !== "sale") {
    return undefined;
  }

  return Math.max(Number(getSelectedSupplierLink(draft)?.quantity || 0), 1);
}

function getUnitCostPlaceholder(draft: MovementLineDraft) {
  const selectedLink = getSelectedSupplierLink(draft);

  return selectedLink
    ? `По поставщику: ${formatCurrency(selectedLink.purchase_price)}`
    : "По поставщику";
}

function isSupplierLinkDisabled(link: ProductSupplierResponse) {
  return props.kind === "sale" && Number(link.quantity || 0) <= 0;
}

function resetForm() {
  note.value = "";
  lines.value = [];
  nextLineId.value = 1;
  createError.value = "";
  createMovementMutation.reset();
}

function createLineDraft(): MovementLineDraft {
  const lineId = nextLineId.value;
  nextLineId.value += 1;

  return {
    id: lineId,
    productSearch: "",
    productLookupTerm: "",
    productLookupResults: [],
    productLookupError: "",
    productLookupRequestId: 0,
    productDetailError: "",
    productDetailRequestId: 0,
    isProductLookupLoading: false,
    isProductDetailLoading: false,
    selectedProduct: null,
    selectedSupplierLinkId: "",
    quantity: 1,
    unitCostSnapshot: "",
  };
}

function normalizeText(value: string) {
  return String(value || "").trim();
}

function normalizeOptionalText(value: string) {
  const normalized = normalizeText(value);

  return normalized || null;
}

function normalizePositiveInteger(value: number | string) {
  return Math.max(Math.trunc(Number(value) || 0), 1);
}

function normalizeOptionalNonNegativeInteger(value: string) {
  const normalized = normalizeText(value);

  if (!normalized) {
    return null;
  }

  const numberValue = Number(normalized);

  return Number.isFinite(numberValue) && numberValue >= 0
    ? Math.trunc(numberValue)
    : null;
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
      aria-labelledby="stock-movement-create-modal-title"
      @click.self="closeModal"
    >
      <div class="modal-dialog modal-xl modal-dialog-scrollable">
        <form
          ref="formElement"
          class="modal-content stock-movement-create-form"
          @submit.prevent="submitCreate"
        >
          <div class="modal-header">
            <h2 id="stock-movement-create-modal-title" class="modal-title fs-5">
              {{ labels.title }}
            </h2>
            <button
              class="btn-close"
              type="button"
              aria-label="Закрыть"
              :disabled="isSubmitting"
              @click="closeModal"
            ></button>
          </div>

          <div class="modal-body">
            <div v-if="createError" class="alert alert-danger" role="alert">
              {{ createError }}
            </div>

            <section class="stock-movement-create-section">
              <label class="form-label" :for="`stock-movement-${kind}-note`">
                Комментарий
              </label>
              <textarea
                :id="`stock-movement-${kind}-note`"
                v-model="note"
                class="form-control"
                name="note"
                rows="2"
                maxlength="500"
                :disabled="isSubmitting"
              ></textarea>
            </section>

            <section class="stock-movement-create-section">
              <div class="stock-movement-create-section-header">
                <h3 class="stock-movement-create-section-title">Позиции</h3>
                <button
                  class="btn btn-sm btn-outline-primary"
                  type="button"
                  :disabled="isSubmitting"
                  @click="addLine"
                >
                  Добавить позицию
                </button>
              </div>

              <div v-if="lines.length === 0" class="alert alert-light border" role="status">
                Добавьте хотя бы одну позицию.
              </div>

              <div v-else class="operation-create-lines">
                <section
                  v-for="(line, index) in lines"
                  :key="line.id"
                  class="operation-create-line"
                  :class="`${kind}-create-line`"
                >
                  <div class="operation-create-line-header">
                    <h4 class="fs-6 mb-0">Позиция {{ formatCount(index + 1) }}</h4>
                    <button
                      class="btn btn-sm btn-outline-danger"
                      type="button"
                      :disabled="isSubmitting"
                      @click="removeLine(line.id)"
                    >
                      Удалить
                    </button>
                  </div>

                  <div class="operation-line-grid">
                    <div class="operation-line-product">
                      <label class="form-label" :for="`stock-movement-${kind}-product-${line.id}`">
                        Товар
                      </label>

                      <div v-if="line.selectedProduct" class="operation-product-selected">
                        <div>
                          <div class="fw-semibold">
                            {{ line.selectedProduct.name || `Товар #${formatCount(line.selectedProduct.id)}` }}
                          </div>
                          <div class="product-meta">
                            {{ getSelectedProductMeta(line.selectedProduct) }}
                          </div>
                        </div>
                        <button
                          class="btn btn-sm btn-outline-secondary"
                          type="button"
                          :disabled="isSubmitting"
                          @click="clearSelectedProduct(line)"
                        >
                          Сменить
                        </button>
                      </div>

                      <div v-else>
                        <div class="input-group">
                          <input
                            :id="`stock-movement-${kind}-product-${line.id}`"
                            v-model="line.productSearch"
                            class="form-control"
                            type="search"
                            minlength="2"
                            maxlength="255"
                            autocomplete="off"
                            placeholder="Введите название товара"
                            :disabled="isSubmitting || line.isProductLookupLoading"
                            @keydown.enter.prevent="runProductLookup(line)"
                          >
                          <button
                            class="btn btn-outline-primary"
                            type="button"
                            :disabled="isSubmitting || line.isProductLookupLoading || line.productSearch.trim().length < 2"
                            @click="runProductLookup(line)"
                          >
                            Найти
                          </button>
                        </div>

                        <div v-if="line.isProductLookupLoading" class="text-secondary small mt-2">
                          Поиск товаров...
                        </div>
                        <div v-else-if="line.productLookupError" class="text-danger small mt-2">
                          {{ line.productLookupError }}
                        </div>
                        <div
                          v-else-if="line.productLookupTerm && line.productLookupResults.length === 0"
                          class="text-secondary small mt-2"
                        >
                          Товары не найдены.
                        </div>

                        <div
                          v-if="line.productLookupResults.length > 0"
                          class="list-group operation-product-results mt-2"
                        >
                          <button
                            v-for="product in line.productLookupResults"
                            :key="product.id"
                            class="list-group-item list-group-item-action operation-product-result"
                            type="button"
                            :disabled="isSubmitting"
                            @click="selectProduct(line, product)"
                          >
                            <span class="fw-semibold d-block">{{ product.name || "Без названия" }}</span>
                            <span class="product-meta d-block">{{ getProductMeta(product) }}</span>
                          </button>
                        </div>
                      </div>

                      <div v-if="line.isProductDetailLoading" class="text-secondary small mt-2">
                        Загрузка поставщиков...
                      </div>
                      <div v-else-if="line.productDetailError" class="text-danger small mt-2">
                        {{ line.productDetailError }}
                      </div>
                    </div>

                    <div>
                      <label class="form-label" :for="`stock-movement-${kind}-supplier-${line.id}`">
                        Поставщик
                      </label>
                      <select
                        :id="`stock-movement-${kind}-supplier-${line.id}`"
                        v-model="line.selectedSupplierLinkId"
                        class="form-select"
                        name="product_supplier_id"
                        required
                        :disabled="isSubmitting || line.isProductDetailLoading || !line.selectedProduct"
                        @change="handleSupplierChange(line)"
                      >
                        <option value="">{{ getSupplierPlaceholder(line) }}</option>
                        <option
                          v-for="link in getSupplierLinks(line)"
                          :key="link.id"
                          :value="String(link.id)"
                          :disabled="isSupplierLinkDisabled(link)"
                        >
                          {{ getSupplierOptionLabel(link, getProductUnit(line)) }}
                        </option>
                      </select>
                      <div class="supplier-meta mt-1">
                        {{ getSupplierMeta(line) }}
                      </div>
                    </div>

                    <div>
                      <label class="form-label" :for="`stock-movement-${kind}-quantity-${line.id}`">
                        {{ labels.quantity }}
                      </label>
                      <input
                        :id="`stock-movement-${kind}-quantity-${line.id}`"
                        v-model.number="line.quantity"
                        class="form-control"
                        name="quantity"
                        type="number"
                        min="1"
                        :max="getQuantityMax(line)"
                        step="1"
                        required
                        :disabled="isSubmitting || !line.selectedSupplierLinkId"
                      >
                    </div>

                    <div v-if="shouldShowUnitCost">
                      <label class="form-label" :for="`stock-movement-${kind}-cost-${line.id}`">
                        Цена закупки
                      </label>
                      <input
                        :id="`stock-movement-${kind}-cost-${line.id}`"
                        v-model="line.unitCostSnapshot"
                        class="form-control"
                        name="unit_cost_snapshot"
                        type="number"
                        min="0"
                        step="1"
                        :placeholder="getUnitCostPlaceholder(line)"
                        :disabled="isSubmitting || !line.selectedSupplierLinkId"
                      >
                    </div>
                  </div>
                </section>
              </div>
            </section>
          </div>

          <div class="modal-footer stock-movement-create-footer">
            <button
              class="btn btn-outline-secondary"
              type="button"
              :disabled="isSubmitting"
              @click="closeModal"
            >
              Отмена
            </button>
            <button class="btn btn-success" type="submit" :disabled="isSubmitting">
              {{ isSubmitting ? labels.submitting : labels.submit }}
            </button>
          </div>
        </form>
      </div>
    </div>
    <div v-if="isOpen" class="modal-backdrop fade show"></div>
  </Teleport>
</template>
