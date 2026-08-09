<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";

import {
  createProductSupplierLinks,
  createSupplier,
  deleteProductSupplierLink,
  getCompanies,
  getProduct,
  getSuppliers,
  patchProduct,
  patchProductSupplierLink,
} from "../lib/api";
import {
  DEFAULT_QUANTITY_UNIT,
  formatCount,
  formatCurrency,
  formatDateTime,
  formatQuantity,
  getCreateErrorMessage,
  getDeleteErrorMessage,
  getRequestErrorMessage,
} from "../lib/format";
import { activeWorkspaceId } from "../lib/workspaceSession";
import type {
  CompanyResponse,
  ProductResponse,
  ProductSupplierCreatePayload,
  ProductSupplierResponse,
  ProductSupplierUpdatePayload,
  ProductSummaryResponse,
  ProductUpdatePayload,
  StockStatus,
  SupplierCreatePayload,
  SupplierSummaryResponse,
} from "../types/api";

type ProductStockStatus = StockStatus | "none";
type SupplierMode = "existing" | "new";
type LinkEditValue = {
  purchasePrice: number;
  marginPercent: number;
  salePrice: number;
  quantity: number;
};
type NewLinkDraft = {
  id: number;
  supplierMode: SupplierMode;
  supplierSearch: string;
  selectedSupplier: SupplierSummaryResponse | null;
  lookupTerm: string;
  lookupResults: SupplierSummaryResponse[];
  lookupError: string;
  isLookupLoading: boolean;
  newSupplierName: string;
  newSupplierPhoneNumber: string;
  purchasePrice: number;
  marginPercent: number;
  salePrice: string;
  quantity: number;
};
type DeleteLinkInput = {
  productId: number;
  linkId: number;
};
type DeleteLinkResult = {
  product: ProductResponse;
  linkId: number;
};

const props = defineProps<{
  productId: number | null;
  isOpen: boolean;
  summary?: ProductSummaryResponse | null;
}>();
const emit = defineEmits<{
  (event: "close"): void;
  (event: "saved", product: ProductResponse): void;
}>();

const COMPANY_LOOKUP_PAGE_SIZE = 10;
const SUPPLIER_LOOKUP_PAGE_SIZE = 10;
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
const companyLookupTerm = ref("");
const nextLinkDraftId = ref(1);
const deletingLinkId = ref<number | null>(null);
const newLinkDrafts = ref<NewLinkDraft[]>([]);
const linkEditValues = reactive<Record<number, LinkEditValue>>({});
const editForm = reactive({
  name: "",
  quantityUnit: DEFAULT_QUANTITY_UNIT,
  lowStockThreshold: 5,
  tags: "",
  companySearch: "",
  selectedCompany: null as CompanyResponse | null,
});

const detailId = computed(() => Number(props.productId || 0));
const productQuery = useQuery({
  queryKey: computed(() => ["products", activeWorkspaceId.value, "detail", detailId.value]),
  queryFn: () => getProduct(detailId.value),
  enabled: computed(() => Boolean(activeWorkspaceId.value) && props.isOpen && detailId.value > 0),
});
const companyLookupQuery = useQuery({
  queryKey: computed(() => [
    "companies",
    activeWorkspaceId.value,
    "product-detail-lookup",
    companyLookupTerm.value,
    COMPANY_LOOKUP_PAGE_SIZE,
  ]),
  queryFn: () => getCompanies({
    search: companyLookupTerm.value,
    page: 1,
    pageSize: COMPANY_LOOKUP_PAGE_SIZE,
  }),
  enabled: computed(() => (
    Boolean(activeWorkspaceId.value)
      && props.isOpen
      && isEditing.value
      && !editForm.selectedCompany
      && companyLookupTerm.value.length >= 2
  )),
});
const updateProductMutation = useMutation({
  mutationFn: updateProductFromForm,
  onSuccess: handleProductUpdateSuccess,
  onError: (error) => {
    editError.value = getCreateErrorMessage(error, "товар");
  },
});
const deleteProductSupplierLinkMutation = useMutation({
  mutationFn: deleteProductSupplierLinkFromModal,
  onSuccess: handleProductSupplierLinkDeleteSuccess,
  onError: (error) => {
    editError.value = getDeleteErrorMessage(error, "связь с поставщиком");
  },
  onSettled: () => {
    deletingLinkId.value = null;
  },
});

const product = computed(() => productQuery.data.value || null);
const supplierLinks = computed(() => product.value?.supplier_links || []);
const companyLookupResults = computed(() => companyLookupQuery.data.value?.items || []);
const productUnit = computed(() => (
  normalizeText(product.value?.quantity_unit || props.summary?.quantity_unit || DEFAULT_QUANTITY_UNIT)
    || DEFAULT_QUANTITY_UNIT
));
const productTags = computed(() => {
  if (product.value) {
    return product.value.tags.map((tag) => tag.name).filter(Boolean);
  }

  return props.summary?.tags || [];
});
const totalQuantity = computed(() => (
  supplierLinks.value.reduce((sum, link) => sum + Number(link.quantity || 0), 0)
));
const detailError = computed(() => (
  productQuery.error.value
    ? getRequestErrorMessage(productQuery.error.value, "детали товара")
    : ""
));
const companyLookupError = computed(() => (
  companyLookupQuery.error.value
    ? getRequestErrorMessage(companyLookupQuery.error.value, "компании")
    : ""
));
const shouldShowContent = computed(() => (
  Boolean(product.value)
    && !productQuery.isLoading.value
    && !detailError.value
));
const isEditRequestPending = computed(() => (
  updateProductMutation.isPending.value
    || deleteProductSupplierLinkMutation.isPending.value
));

watch(() => props.isOpen, (isOpen) => {
  if (!isOpen) {
    resetDetailState();
  }
});

function closeModal() {
  if (isEditRequestPending.value) {
    return;
  }

  emit("close");
}

function startEdit() {
  if (!product.value) {
    return;
  }

  editError.value = "";
  editForm.name = product.value.name || "";
  editForm.quantityUnit = product.value.quantity_unit || DEFAULT_QUANTITY_UNIT;
  editForm.lowStockThreshold = Number(product.value.low_stock_threshold || 0);
  editForm.tags = product.value.tags.map((tag) => tag.name).join(", ");
  editForm.companySearch = "";
  editForm.selectedCompany = {
    id: product.value.company_id,
    name: product.value.company_name || `Компания #${formatCount(product.value.company_id)}`,
    iin: null,
  };
  companyLookupTerm.value = "";
  resetLinkEditValues();
  for (const link of supplierLinks.value) {
    linkEditValues[link.id] = {
      purchasePrice: Number(link.purchase_price || 1),
      marginPercent: Number(link.margin_percent || 0),
      salePrice: Number(link.sale_price || 1),
      quantity: Number(link.quantity || 0),
    };
  }
  newLinkDrafts.value = [];
  nextLinkDraftId.value = 1;
  isEditing.value = true;
}

function cancelEdit() {
  if (isEditRequestPending.value) {
    return;
  }

  isEditing.value = false;
  editError.value = "";
  companyLookupTerm.value = "";
  newLinkDrafts.value = [];
  resetLinkEditValues();
}

function runCompanyLookup() {
  const search = normalizeText(editForm.companySearch);

  editForm.companySearch = search;
  editForm.selectedCompany = null;
  editError.value = "";

  if (search.length < 2) {
    companyLookupTerm.value = "";
    return;
  }

  companyLookupTerm.value = search;
}

function selectCompany(company: CompanyResponse) {
  editForm.selectedCompany = company;
  editForm.companySearch = "";
  companyLookupTerm.value = "";
  editError.value = "";
}

function clearSelectedCompany() {
  editForm.selectedCompany = null;
  editForm.companySearch = "";
  companyLookupTerm.value = "";
}

function addNewLinkDraft() {
  newLinkDrafts.value.push({
    id: nextLinkDraftId.value,
    supplierMode: "existing",
    supplierSearch: "",
    selectedSupplier: null,
    lookupTerm: "",
    lookupResults: [],
    lookupError: "",
    isLookupLoading: false,
    newSupplierName: "",
    newSupplierPhoneNumber: "",
    purchasePrice: 1,
    marginPercent: 0,
    salePrice: "",
    quantity: 0,
  });
  nextLinkDraftId.value += 1;
}

function removeNewLinkDraft(draftId: number) {
  newLinkDrafts.value = newLinkDrafts.value.filter((draft) => draft.id !== draftId);
}

function setDraftSupplierMode(draft: NewLinkDraft, mode: SupplierMode) {
  draft.supplierMode = mode;
  draft.supplierSearch = "";
  draft.selectedSupplier = null;
  draft.lookupTerm = "";
  draft.lookupResults = [];
  draft.lookupError = "";
  draft.newSupplierName = "";
  draft.newSupplierPhoneNumber = "";
  editError.value = "";
}

function deleteExistingLink(link: ProductSupplierResponse) {
  if (!product.value || isEditRequestPending.value) {
    return;
  }

  const supplierName = link.supplier_name || `поставщиком #${formatCount(link.supplier_id)}`;
  if (!window.confirm(`Удалить связь с ${supplierName}?`)) {
    return;
  }

  editError.value = "";
  deletingLinkId.value = link.id;
  deleteProductSupplierLinkMutation.mutate({
    productId: product.value.id,
    linkId: link.id,
  });
}

async function runDraftSupplierLookup(draft: NewLinkDraft) {
  if (draft.supplierMode !== "existing") {
    return;
  }

  const search = normalizeText(draft.supplierSearch);

  draft.supplierSearch = search;
  draft.selectedSupplier = null;
  draft.lookupTerm = search;
  draft.lookupResults = [];
  draft.lookupError = "";
  editError.value = "";

  if (search.length < 2) {
    return;
  }

  draft.isLookupLoading = true;
  try {
    const response = await getSuppliers({
      search,
      page: 1,
      pageSize: SUPPLIER_LOOKUP_PAGE_SIZE,
    });

    if (draft.lookupTerm === search) {
      draft.lookupResults = response.items;
    }
  } catch (error) {
    draft.lookupError = getRequestErrorMessage(error, "поставщиков");
  } finally {
    draft.isLookupLoading = false;
  }
}

function selectDraftSupplier(draft: NewLinkDraft, supplier: SupplierSummaryResponse) {
  draft.selectedSupplier = supplier;
  draft.supplierSearch = "";
  draft.lookupTerm = "";
  draft.lookupResults = [];
  draft.lookupError = "";
  editError.value = "";
}

function clearDraftSupplier(draft: NewLinkDraft) {
  draft.selectedSupplier = null;
  draft.supplierSearch = "";
  draft.lookupTerm = "";
  draft.lookupResults = [];
  draft.lookupError = "";
}

function submitProductEdit() {
  editError.value = "";

  if (deleteProductSupplierLinkMutation.isPending.value) {
    return;
  }

  if (!editFormElement.value?.reportValidity()) {
    return;
  }

  updateProductMutation.mutate();
}

async function updateProductFromForm() {
  if (!product.value) {
    throw createLocalValidationError("Товар не загружен.");
  }

  validateProductEdit();

  const productId = product.value.id;
  const productPayload: ProductUpdatePayload = {
    name: normalizeText(editForm.name),
    company_id: Number(editForm.selectedCompany?.id),
    quantity_unit: normalizeText(editForm.quantityUnit) || DEFAULT_QUANTITY_UNIT,
    low_stock_threshold: normalizeRequiredNumber(editForm.lowStockThreshold, 0),
    tags: parseTags(editForm.tags),
  };

  await patchProduct(productId, productPayload);

  const existingLinkRequests: Promise<unknown>[] = supplierLinks.value.map((link) => (
    patchProductSupplierLink(productId, link.id, getExistingLinkPayload(link))
  ));

  if (existingLinkRequests.length > 0) {
    await Promise.all(existingLinkRequests);
  }

  const createdSupplierNames: string[] = [];

  try {
    const newLinkPayloads = await getNewLinkPayloads(createdSupplierNames);

    if (newLinkPayloads.length > 0) {
      await createProductSupplierLinks(productId, newLinkPayloads);
    }
  } catch (error) {
    if (createdSupplierNames.length > 0) {
      throw createLocalValidationError([
        `Новый поставщик ${createdSupplierNames.join(", ")} мог быть создан,`,
        `но связь с товаром не создана: ${getCreateErrorMessage(error, "связь с поставщиком")}`,
      ].join(" "));
    }

    throw error;
  }

  return getProduct(productId);
}

async function deleteProductSupplierLinkFromModal({
  productId,
  linkId,
}: DeleteLinkInput): Promise<DeleteLinkResult> {
  await deleteProductSupplierLink(productId, linkId);

  return {
    product: await getProduct(productId),
    linkId,
  };
}

async function handleProductUpdateSuccess(updatedProduct: ProductResponse) {
  queryClient.setQueryData(
    ["products", activeWorkspaceId.value, "detail", updatedProduct.id],
    updatedProduct,
  );
  isEditing.value = false;
  editError.value = "";
  companyLookupTerm.value = "";
  newLinkDrafts.value = [];
  resetLinkEditValues();

  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ["products", activeWorkspaceId.value] }),
    queryClient.invalidateQueries({ queryKey: ["suppliers", activeWorkspaceId.value] }),
    queryClient.invalidateQueries({ queryKey: ["summaries"] }),
    queryClient.invalidateQueries({ queryKey: ["tags", activeWorkspaceId.value] }),
  ]);
  emit("saved", updatedProduct);
}

async function handleProductSupplierLinkDeleteSuccess({
  product: updatedProduct,
  linkId,
}: DeleteLinkResult) {
  queryClient.setQueryData(
    ["products", activeWorkspaceId.value, "detail", updatedProduct.id],
    updatedProduct,
  );
  delete linkEditValues[linkId];
  editError.value = "";

  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ["products", activeWorkspaceId.value] }),
    queryClient.invalidateQueries({ queryKey: ["suppliers", activeWorkspaceId.value] }),
    queryClient.invalidateQueries({ queryKey: ["summaries"] }),
  ]);
  emit("saved", updatedProduct);
}

function validateProductEdit() {
  if (!editForm.selectedCompany) {
    throw createLocalValidationError("Выберите компанию.");
  }

  const usedSupplierIds = new Set(supplierLinks.value.map((link) => Number(link.supplier_id)));

  for (const draft of newLinkDrafts.value) {
    if (draft.supplierMode === "new") {
      if (!normalizeText(draft.newSupplierName)) {
        throw createLocalValidationError("Введите название нового поставщика для каждой новой связи.");
      }

      if (!normalizeText(draft.newSupplierPhoneNumber)) {
        throw createLocalValidationError("Введите телефон нового поставщика для каждой новой связи.");
      }

      continue;
    }

    if (!draft.selectedSupplier) {
      throw createLocalValidationError("Выберите поставщика для каждой новой связи.");
    }

    const supplierId = Number(draft.selectedSupplier.id);
    if (usedSupplierIds.has(supplierId)) {
      throw createLocalValidationError("Один поставщик не может быть связан с товаром дважды.");
    }
    usedSupplierIds.add(supplierId);
  }
}

function getExistingLinkPayload(link: ProductSupplierResponse): ProductSupplierUpdatePayload {
  const values = linkEditValues[link.id] || {
    purchasePrice: link.purchase_price,
    marginPercent: link.margin_percent,
    salePrice: link.sale_price,
    quantity: link.quantity,
  };

  return {
    purchase_price: normalizeRequiredNumber(values.purchasePrice, link.purchase_price),
    margin_percent: normalizeRequiredNumber(values.marginPercent, link.margin_percent),
    sale_price: normalizeRequiredNumber(values.salePrice, link.sale_price),
    quantity: normalizeRequiredNumber(values.quantity, link.quantity),
  };
}

async function getNewLinkPayloads(createdSupplierNames: string[]) {
  const payloads: ProductSupplierCreatePayload[] = [];

  for (const draft of newLinkDrafts.value) {
    const supplierId = await resolveDraftSupplierId(draft, createdSupplierNames);

    payloads.push(getNewLinkPayload(draft, supplierId));
  }

  return payloads;
}

async function resolveDraftSupplierId(
  draft: NewLinkDraft,
  createdSupplierNames: string[],
) {
  if (draft.supplierMode === "new") {
    const supplier = await createSupplier(getDraftInlineSupplierPayload(draft));

    createdSupplierNames.push(supplier.name || normalizeText(draft.newSupplierName));
    return Number(supplier.id);
  }

  return Number(draft.selectedSupplier?.id);
}

function getDraftInlineSupplierPayload(draft: NewLinkDraft): SupplierCreatePayload {
  return {
    name: normalizeText(draft.newSupplierName),
    phone_number: normalizeText(draft.newSupplierPhoneNumber),
  };
}

function getNewLinkPayload(draft: NewLinkDraft, supplierId: number): ProductSupplierCreatePayload {
  return {
    supplier_id: supplierId,
    purchase_price: normalizeRequiredNumber(draft.purchasePrice, 1),
    margin_percent: normalizeRequiredNumber(draft.marginPercent, 0),
    sale_price: normalizeOptionalNumber(draft.salePrice),
    quantity: normalizeRequiredNumber(draft.quantity, 0),
  };
}

function resetDetailState() {
  isEditing.value = false;
  editError.value = "";
  companyLookupTerm.value = "";
  editForm.name = "";
  editForm.quantityUnit = DEFAULT_QUANTITY_UNIT;
  editForm.lowStockThreshold = 5;
  editForm.tags = "";
  editForm.companySearch = "";
  editForm.selectedCompany = null;
  newLinkDrafts.value = [];
  nextLinkDraftId.value = 1;
  resetLinkEditValues();
}

function resetLinkEditValues() {
  for (const key of Object.keys(linkEditValues)) {
    delete linkEditValues[Number(key)];
  }
}

function getStatusConfig(status: StockStatus | undefined) {
  return STOCK_STATUS[status || "none"] || STOCK_STATUS.none;
}

function parseTags(value: string) {
  return Array.from(
    new Set(
      String(value || "")
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean),
    ),
  );
}

function normalizeText(value: string) {
  return String(value || "").trim();
}

function normalizeRequiredNumber(value: number | string, fallback: number) {
  const numberValue = Number(value);

  return Number.isFinite(numberValue) ? numberValue : fallback;
}

function normalizeOptionalNumber(value: number | string) {
  if (value === "" || value === null || value === undefined) {
    return null;
  }

  const numberValue = Number(value);

  return Number.isFinite(numberValue) ? numberValue : null;
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
      aria-labelledby="product-detail-modal-title"
      @click.self="closeModal"
    >
      <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
        <div class="modal-content product-detail-modal-content">
          <div class="modal-header">
            <h2 id="product-detail-modal-title" class="modal-title fs-5">
              {{ product ? product.name || `Товар #${formatCount(product.id)}` : "Товар" }}
            </h2>
            <div class="ms-auto d-flex align-items-center gap-2">
              <button
                v-if="shouldShowContent && !isEditing"
                class="btn btn-sm btn-outline-primary"
                type="button"
                :disabled="isEditRequestPending"
                @click="startEdit"
              >
                Редактировать
              </button>
              <button
                class="btn-close"
                type="button"
                aria-label="Закрыть"
                :disabled="isEditRequestPending"
                @click="closeModal"
              ></button>
            </div>
          </div>

          <div class="modal-body">
            <div v-if="productQuery.isLoading.value" class="text-secondary py-4" aria-live="polite">
              Загрузка товара...
            </div>
            <div v-else-if="detailError" class="alert alert-danger" role="alert">
              {{ detailError }}
            </div>

            <div v-if="shouldShowContent" class="product-detail-content">
              <div v-if="editError" class="alert alert-danger" role="alert">
                {{ editError }}
              </div>

              <div v-if="!isEditing">
                <div class="product-detail-summary mb-4">
                  <div>
                    <div class="product-detail-label">ID</div>
                    <div class="fw-semibold">{{ formatCount(product?.id) }}</div>
                  </div>
                  <div>
                    <div class="product-detail-label">Создан</div>
                    <div class="fw-semibold">{{ formatDateTime(product?.created_at) }}</div>
                  </div>
                  <div>
                    <div class="product-detail-label">Компания</div>
                    <div class="fw-semibold">{{ product?.company_name || "Не указана" }}</div>
                  </div>
                  <div>
                    <div class="product-detail-label">Единица</div>
                    <div class="fw-semibold">{{ productUnit }}</div>
                  </div>
                  <div>
                    <div class="product-detail-label">Порог</div>
                    <div class="fw-semibold">
                      {{ formatQuantity(product?.low_stock_threshold, productUnit) }}
                    </div>
                  </div>
                  <div>
                    <div class="product-detail-label">Всего</div>
                    <div class="fw-semibold">{{ formatQuantity(totalQuantity, productUnit) }}</div>
                  </div>
                </div>

                <div class="mb-4">
                  <div class="product-detail-label mb-2">Теги</div>
                  <div v-if="productTags.length === 0" class="text-secondary">Без тегов</div>
                  <div v-else class="product-detail-tags">
                    <span
                      v-for="tag in productTags"
                      :key="tag"
                      class="badge rounded-pill text-bg-light border"
                    >
                      {{ tag }}
                    </span>
                  </div>
                </div>

                <div class="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-2">
                  <h3 class="fs-6 mb-0">Поставщики</h3>
                  <span class="badge text-bg-secondary">
                    {{ formatCount(supplierLinks.length) }} поставщиков
                  </span>
                </div>
                <div v-if="supplierLinks.length === 0" class="alert alert-light border" role="status">
                  У товара пока нет поставщиков.
                </div>
                <div v-else class="table-responsive product-detail-suppliers-table">
                  <table class="table table-hover align-middle mb-0">
                    <thead>
                      <tr>
                        <th scope="col">Поставщик</th>
                        <th scope="col">Остаток</th>
                        <th scope="col">Закупка</th>
                        <th scope="col">Маржа</th>
                        <th scope="col">Продажа</th>
                        <th scope="col">Статус</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="link in supplierLinks" :key="link.id">
                        <td>
                          <div class="fw-semibold">
                            {{ link.supplier_name || `Поставщик #${formatCount(link.supplier_id)}` }}
                          </div>
                          <div class="product-meta">ID {{ formatCount(link.supplier_id) }}</div>
                        </td>
                        <td>{{ formatQuantity(link.quantity, productUnit) }}</td>
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
                class="product-detail-edit-form"
                @submit.prevent="submitProductEdit"
              >
                <div class="row g-3">
                  <div class="col-12 col-lg-6">
                    <label class="form-label" for="product-detail-edit-name">Название</label>
                    <input
                      id="product-detail-edit-name"
                      v-model="editForm.name"
                      class="form-control"
                      name="name"
                      type="text"
                      maxlength="255"
                      required
                      :disabled="isEditRequestPending"
                    >
                  </div>
                  <div class="col-12 col-lg-6">
                    <label class="form-label" for="product-detail-edit-company-search">Компания</label>
                    <div
                      v-if="editForm.selectedCompany"
                      class="product-company-selected"
                    >
                      <div>
                        <div class="fw-semibold">{{ editForm.selectedCompany.name }}</div>
                        <div class="product-meta">
                          ID {{ formatCount(editForm.selectedCompany.id) }}
                          <span v-if="editForm.selectedCompany.iin">| ИИН {{ editForm.selectedCompany.iin }}</span>
                        </div>
                      </div>
                      <button
                        class="btn btn-sm btn-outline-primary"
                        type="button"
                        :disabled="isEditRequestPending"
                        @click="clearSelectedCompany"
                      >
                        Сменить
                      </button>
                    </div>
                    <div v-else>
                      <div class="input-group">
                        <input
                          id="product-detail-edit-company-search"
                          v-model="editForm.companySearch"
                          class="form-control"
                          type="search"
                          minlength="2"
                          maxlength="100"
                          autocomplete="off"
                          placeholder="Начните вводить название"
                          :disabled="isEditRequestPending"
                          @keydown.enter.prevent="runCompanyLookup"
                        >
                        <button
                          class="btn btn-outline-primary"
                          type="button"
                          :disabled="isEditRequestPending || editForm.companySearch.trim().length < 2"
                          @click="runCompanyLookup"
                        >
                          Найти
                        </button>
                      </div>
                      <div v-if="companyLookupQuery.isLoading.value" class="text-secondary small mt-2">
                        Поиск компаний...
                      </div>
                      <div v-else-if="companyLookupError" class="text-danger small mt-2">
                        {{ companyLookupError }}
                      </div>
                      <div
                        v-else-if="companyLookupTerm && companyLookupResults.length === 0"
                        class="text-secondary small mt-2"
                      >
                        Компании не найдены.
                      </div>
                      <div v-if="companyLookupResults.length > 0" class="list-group product-company-results mt-2">
                        <button
                          v-for="company in companyLookupResults"
                          :key="company.id"
                          class="list-group-item list-group-item-action product-company-result"
                          type="button"
                          :disabled="isEditRequestPending"
                          @click="selectCompany(company)"
                        >
                          <span class="fw-semibold d-block">{{ company.name }}</span>
                          <span class="product-meta d-block">
                            ID {{ formatCount(company.id) }}
                            <span v-if="company.iin">| ИИН {{ company.iin }}</span>
                          </span>
                        </button>
                      </div>
                    </div>
                  </div>
                  <div class="col-12 col-sm-6 col-lg-3">
                    <label class="form-label" for="product-detail-edit-unit">Единица</label>
                    <input
                      id="product-detail-edit-unit"
                      v-model="editForm.quantityUnit"
                      class="form-control"
                      name="quantity_unit"
                      type="text"
                      maxlength="20"
                      required
                      :disabled="isEditRequestPending"
                    >
                  </div>
                  <div class="col-12 col-sm-6 col-lg-3">
                    <label class="form-label" for="product-detail-edit-threshold">Порог остатков</label>
                    <input
                      id="product-detail-edit-threshold"
                      v-model.number="editForm.lowStockThreshold"
                      class="form-control"
                      name="low_stock_threshold"
                      type="number"
                      min="0"
                      step="1"
                      required
                      :disabled="isEditRequestPending"
                    >
                  </div>
                  <div class="col-12 col-lg-6">
                    <label class="form-label" for="product-detail-edit-tags">Теги</label>
                    <input
                      id="product-detail-edit-tags"
                      v-model="editForm.tags"
                      class="form-control"
                      name="tags"
                      type="text"
                      maxlength="500"
                      placeholder="склад, сезон, импорт"
                      :disabled="isEditRequestPending"
                    >
                  </div>
                </div>

                <section class="product-detail-edit-links mt-4">
                  <div class="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-2">
                    <h3 class="fs-6 mb-0">Поставщики</h3>
                    <button
                      class="btn btn-sm btn-outline-primary"
                      type="button"
                      :disabled="isEditRequestPending"
                      @click="addNewLinkDraft"
                    >
                      Добавить поставщика
                    </button>
                  </div>

                  <div v-if="supplierLinks.length === 0" class="alert alert-light border" role="status">
                    У товара пока нет поставщиков.
                  </div>
                  <div v-else class="table-responsive product-detail-edit-links-table">
                    <table class="table table-sm align-middle mb-0">
                      <thead>
                        <tr>
                          <th scope="col">Поставщик</th>
                          <th scope="col">Остаток</th>
                          <th scope="col">Закупка</th>
                          <th scope="col">Маржа</th>
                          <th scope="col">Продажа</th>
                          <th scope="col" class="text-end">Действие</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="link in supplierLinks" :key="link.id">
                          <td>
                            <div class="fw-semibold">
                              {{ link.supplier_name || `Поставщик #${formatCount(link.supplier_id)}` }}
                            </div>
                            <div class="product-meta">ID {{ formatCount(link.supplier_id) }}</div>
                          </td>
                          <td>
                            <input
                              v-model.number="linkEditValues[link.id].quantity"
                              class="form-control form-control-sm product-detail-link-number"
                              type="number"
                              min="0"
                              step="1"
                              required
                              :aria-label="`Остаток поставщика ${link.supplier_name || link.supplier_id}`"
                              :disabled="isEditRequestPending"
                            >
                          </td>
                          <td>
                            <input
                              v-model.number="linkEditValues[link.id].purchasePrice"
                              class="form-control form-control-sm product-detail-link-number"
                              type="number"
                              min="1"
                              step="1"
                              required
                              :aria-label="`Цена закупки поставщика ${link.supplier_name || link.supplier_id}`"
                              :disabled="isEditRequestPending"
                            >
                          </td>
                          <td>
                            <input
                              v-model.number="linkEditValues[link.id].marginPercent"
                              class="form-control form-control-sm product-detail-link-number"
                              type="number"
                              min="0"
                              step="1"
                              required
                              :aria-label="`Маржа поставщика ${link.supplier_name || link.supplier_id}`"
                              :disabled="isEditRequestPending"
                            >
                          </td>
                          <td>
                            <input
                              v-model.number="linkEditValues[link.id].salePrice"
                              class="form-control form-control-sm product-detail-link-number"
                              type="number"
                              min="1"
                              step="1"
                              required
                              :aria-label="`Цена продажи поставщика ${link.supplier_name || link.supplier_id}`"
                              :disabled="isEditRequestPending"
                            >
                          </td>
                          <td class="text-end">
                            <button
                              class="btn btn-sm btn-outline-danger product-detail-link-delete-button"
                              type="button"
                              :disabled="isEditRequestPending"
                              @click="deleteExistingLink(link)"
                            >
                              {{ deletingLinkId === link.id ? "Удаление..." : "Удалить" }}
                            </button>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  <div v-if="newLinkDrafts.length > 0" class="product-detail-new-links mt-3">
                    <section
                      v-for="draft in newLinkDrafts"
                      :key="draft.id"
                      class="product-detail-link-draft"
                    >
                      <div class="product-detail-link-draft-header">
                        <h4 class="fs-6 mb-0">Новая связь</h4>
                        <button
                          class="btn btn-sm btn-outline-danger"
                          type="button"
                          :disabled="isEditRequestPending"
                          @click="removeNewLinkDraft(draft.id)"
                        >
                          Удалить
                        </button>
                      </div>

                      <div class="mb-3">
                        <div class="product-detail-link-mode mb-2" role="radiogroup" aria-label="Способ выбора поставщика">
                          <div class="form-check form-check-inline">
                            <input
                              :id="`product-detail-new-link-${draft.id}-supplier-existing`"
                              class="form-check-input"
                              type="radio"
                              :name="`product-detail-new-link-${draft.id}-supplier-mode`"
                              value="existing"
                              :checked="draft.supplierMode === 'existing'"
                              :disabled="isEditRequestPending"
                              @change="setDraftSupplierMode(draft, 'existing')"
                            >
                            <label
                              class="form-check-label"
                              :for="`product-detail-new-link-${draft.id}-supplier-existing`"
                            >
                              Существующий
                            </label>
                          </div>
                          <div class="form-check form-check-inline">
                            <input
                              :id="`product-detail-new-link-${draft.id}-supplier-new`"
                              class="form-check-input"
                              type="radio"
                              :name="`product-detail-new-link-${draft.id}-supplier-mode`"
                              value="new"
                              :checked="draft.supplierMode === 'new'"
                              :disabled="isEditRequestPending"
                              @change="setDraftSupplierMode(draft, 'new')"
                            >
                            <label
                              class="form-check-label"
                              :for="`product-detail-new-link-${draft.id}-supplier-new`"
                            >
                              Новый
                            </label>
                          </div>
                        </div>

                        <div v-if="draft.supplierMode === 'existing'">
                          <label class="form-label" :for="`product-detail-new-link-${draft.id}-supplier-search`">
                            Поставщик
                          </label>
                          <div v-if="draft.selectedSupplier" class="product-supplier-selected">
                            <div>
                              <div class="fw-semibold">{{ draft.selectedSupplier.name }}</div>
                              <div class="product-meta">
                                ID {{ formatCount(draft.selectedSupplier.id) }}
                                <span v-if="draft.selectedSupplier.phone_number">
                                  | {{ draft.selectedSupplier.phone_number }}
                                </span>
                              </div>
                            </div>
                            <button
                              class="btn btn-sm btn-outline-secondary"
                              type="button"
                              :disabled="isEditRequestPending"
                              @click="clearDraftSupplier(draft)"
                            >
                              Сбросить
                            </button>
                          </div>
                          <div v-else>
                            <div class="input-group">
                              <input
                                :id="`product-detail-new-link-${draft.id}-supplier-search`"
                                v-model="draft.supplierSearch"
                                class="form-control"
                                type="search"
                                minlength="2"
                                maxlength="100"
                                autocomplete="off"
                                placeholder="Введите название поставщика"
                                :disabled="isEditRequestPending"
                                @keydown.enter.prevent="runDraftSupplierLookup(draft)"
                              >
                              <button
                                class="btn btn-outline-primary"
                                type="button"
                                :disabled="isEditRequestPending || draft.supplierSearch.trim().length < 2"
                                @click="runDraftSupplierLookup(draft)"
                              >
                                Найти
                              </button>
                            </div>
                            <div v-if="draft.isLookupLoading" class="text-secondary small mt-2">
                              Поиск поставщиков...
                            </div>
                            <div v-else-if="draft.lookupError" class="text-danger small mt-2">
                              {{ draft.lookupError }}
                            </div>
                            <div
                              v-else-if="draft.lookupTerm && draft.lookupResults.length === 0"
                              class="text-secondary small mt-2"
                            >
                              Поставщики не найдены.
                            </div>
                            <div v-if="draft.lookupResults.length > 0" class="list-group product-supplier-results mt-2">
                              <button
                                v-for="supplier in draft.lookupResults"
                                :key="supplier.id"
                                class="list-group-item list-group-item-action product-supplier-result"
                                type="button"
                                :disabled="isEditRequestPending"
                                @click="selectDraftSupplier(draft, supplier)"
                              >
                                <span class="fw-semibold d-block">{{ supplier.name }}</span>
                                <span class="product-meta d-block">
                                  ID {{ formatCount(supplier.id) }}
                                  <span v-if="supplier.phone_number">| {{ supplier.phone_number }}</span>
                                </span>
                              </button>
                            </div>
                          </div>
                        </div>

                        <div v-else class="row g-3">
                          <div class="col-12 col-lg-7">
                            <label
                              class="form-label"
                              :for="`product-detail-new-link-${draft.id}-new-supplier-name`"
                            >
                              Название поставщика
                            </label>
                            <input
                              :id="`product-detail-new-link-${draft.id}-new-supplier-name`"
                              v-model="draft.newSupplierName"
                              class="form-control"
                              type="text"
                              maxlength="255"
                              autocomplete="organization"
                              required
                              :disabled="isEditRequestPending"
                            >
                          </div>
                          <div class="col-12 col-lg-5">
                            <label
                              class="form-label"
                              :for="`product-detail-new-link-${draft.id}-new-supplier-phone`"
                            >
                              Телефон
                            </label>
                            <input
                              :id="`product-detail-new-link-${draft.id}-new-supplier-phone`"
                              v-model="draft.newSupplierPhoneNumber"
                              class="form-control"
                              type="tel"
                              inputmode="tel"
                              pattern="(8[0-9]{10}|[+]7[0-9]{10})"
                              maxlength="12"
                              autocomplete="tel"
                              placeholder="+77001234567"
                              required
                              :disabled="isEditRequestPending"
                            >
                            <div class="form-text">Формат: +7XXXXXXXXXX или 8XXXXXXXXXX.</div>
                          </div>
                        </div>
                      </div>

                      <div class="row g-3">
                        <div class="col-12 col-md-6 col-xl-3">
                          <label class="form-label" :for="`product-detail-new-link-${draft.id}-purchase-price`">
                            Цена закупки
                          </label>
                          <input
                            :id="`product-detail-new-link-${draft.id}-purchase-price`"
                            v-model.number="draft.purchasePrice"
                            class="form-control"
                            type="number"
                            min="1"
                            step="1"
                            required
                            :disabled="isEditRequestPending"
                          >
                        </div>
                        <div class="col-12 col-md-6 col-xl-3">
                          <label class="form-label" :for="`product-detail-new-link-${draft.id}-margin-percent`">
                            Маржа, %
                          </label>
                          <input
                            :id="`product-detail-new-link-${draft.id}-margin-percent`"
                            v-model.number="draft.marginPercent"
                            class="form-control"
                            type="number"
                            min="0"
                            step="1"
                            required
                            :disabled="isEditRequestPending"
                          >
                        </div>
                        <div class="col-12 col-md-6 col-xl-3">
                          <label class="form-label" :for="`product-detail-new-link-${draft.id}-sale-price`">
                            Цена продажи
                          </label>
                          <input
                            :id="`product-detail-new-link-${draft.id}-sale-price`"
                            v-model="draft.salePrice"
                            class="form-control"
                            type="number"
                            min="1"
                            step="1"
                            placeholder="Авто"
                            :disabled="isEditRequestPending"
                          >
                        </div>
                        <div class="col-12 col-md-6 col-xl-3">
                          <label class="form-label" :for="`product-detail-new-link-${draft.id}-quantity`">
                            Количество
                          </label>
                          <input
                            :id="`product-detail-new-link-${draft.id}-quantity`"
                            v-model.number="draft.quantity"
                            class="form-control"
                            type="number"
                            min="0"
                            step="1"
                            required
                            :disabled="isEditRequestPending"
                          >
                        </div>
                      </div>
                    </section>
                  </div>
                </section>
              </form>
            </div>
          </div>

          <div class="modal-footer">
            <button
              v-if="isEditing"
              class="btn btn-outline-secondary"
              type="button"
              :disabled="isEditRequestPending"
              @click="cancelEdit"
            >
              Отмена
            </button>
            <button
              v-if="isEditing"
              class="btn btn-primary"
              type="button"
              :disabled="isEditRequestPending"
              @click="submitProductEdit"
            >
              {{ updateProductMutation.isPending.value ? "Сохранение..." : "Сохранить" }}
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="isOpen" class="modal-backdrop fade show"></div>
  </Teleport>
</template>
