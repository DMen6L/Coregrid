<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { useRoute, useRouter } from "vue-router";

import SupplierDetailModal from "../components/SupplierDetailModal.vue";
import { createSupplier, DEFAULT_PAGE_SIZE, FIRST_PAGE, getSuppliers } from "../lib/api";
import { formatCount, getCreateErrorMessage, getRequestErrorMessage } from "../lib/format";
import type {
  PaginatedResponse,
  SupplierCreatePayload,
  SupplierResponse,
  SupplierSummaryResponse,
} from "../types/api";

const EMPTY_SUPPLIERS_PAGE: PaginatedResponse<SupplierSummaryResponse> = {
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
const isCreateModalOpen = ref(false);
const isDetailModalOpen = ref(false);
const selectedSupplierId = ref<number | null>(null);
const createError = ref("");
const supplierCreateForm = reactive({
  name: "",
  phoneNumber: "",
});

const currentSearch = computed(() => currentSearchFromRoute());
const currentPage = computed(() => currentPageFromRoute());
const suppliersQuery = useQuery({
  queryKey: computed(() => [
    "suppliers",
    "list",
    currentSearch.value,
    currentPage.value,
    DEFAULT_PAGE_SIZE,
  ]),
  queryFn: () => getSuppliers({
    search: currentSearch.value,
    page: currentPage.value,
    pageSize: DEFAULT_PAGE_SIZE,
  }),
});
const createSupplierMutation = useMutation({
  mutationFn: createSupplierFromForm,
  onSuccess: handleSupplierCreateSuccess,
  onError: (error) => {
    createError.value = getCreateErrorMessage(error, "поставщика");
  },
});

const suppliersPage = computed(() => suppliersQuery.data.value || EMPTY_SUPPLIERS_PAGE);
const suppliersError = computed(() => (
  suppliersQuery.error.value
    ? getRequestErrorMessage(suppliersQuery.error.value, "поставщиков")
    : ""
));
const hasSuppliers = computed(() => suppliersPage.value.items.length > 0);
const shouldShowSuppliersTable = computed(() => (
  hasSuppliers.value
    && !suppliersQuery.isLoading.value
    && !suppliersError.value
));
const shouldShowSuppliersEmpty = computed(() => (
  !suppliersQuery.isLoading.value
    && !suppliersError.value
    && suppliersPage.value.items.length === 0
));
const shouldShowSuppliersPagination = computed(() => (
  suppliersPage.value.total > 0
    && !suppliersQuery.isLoading.value
    && !suppliersError.value
));
const totalSupplierPages = computed(() => Math.max(suppliersPage.value.total_pages, 1));

watch(currentSearch, (nextSearch) => {
  searchDraft.value = nextSearch;
});

function submitSearch() {
  if (!searchForm.value?.reportValidity()) {
    return;
  }

  navigateSuppliers({
    search: searchDraft.value,
    page: FIRST_PAGE,
  });
}

function goToPage(page: number) {
  navigateSuppliers({
    search: currentSearch.value,
    page,
  });
}

function openSupplierDetail(supplier: SupplierSummaryResponse) {
  selectedSupplierId.value = supplier.id;
  isDetailModalOpen.value = true;
}

function closeSupplierDetail() {
  isDetailModalOpen.value = false;
  selectedSupplierId.value = null;
}

function openCreateModal() {
  resetSupplierCreateForm();
  createError.value = "";
  isCreateModalOpen.value = true;
}

function closeCreateModal() {
  if (createSupplierMutation.isPending.value) {
    return;
  }

  isCreateModalOpen.value = false;
}

function submitSupplierCreate() {
  createError.value = "";

  if (!createFormElement.value?.reportValidity()) {
    return;
  }

  createSupplierMutation.mutate();
}

function createSupplierFromForm() {
  const payload: SupplierCreatePayload = {
    name: normalizeText(supplierCreateForm.name),
    phone_number: normalizeText(supplierCreateForm.phoneNumber),
  };

  return createSupplier(payload);
}

async function handleSupplierCreateSuccess(supplier: SupplierResponse) {
  const supplierName = supplier.name || normalizeText(supplierCreateForm.name);

  isCreateModalOpen.value = false;
  resetSupplierCreateForm();
  navigateSuppliers({
    search: supplierName,
    page: FIRST_PAGE,
  });

  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ["suppliers"] }),
    queryClient.invalidateQueries({ queryKey: ["summaries"] }),
  ]);
}

function resetSupplierCreateForm() {
  supplierCreateForm.name = "";
  supplierCreateForm.phoneNumber = "";
}

function navigateSuppliers({ search, page }: { search: string; page: number }) {
  const trimmedSearch = String(search || "").trim();
  const nextPage = Math.max(Number(page) || FIRST_PAGE, FIRST_PAGE);
  const query: Record<string, string> = {};

  if (trimmedSearch) {
    query.search = trimmedSearch;
  }

  if (nextPage > FIRST_PAGE) {
    query.page = String(nextPage);
  }

  void router.push({ name: "suppliers", query });
}

function currentSearchFromRoute() {
  return normalizeRouteString(route.query.search);
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
</script>

<template>
  <section class="container-fluid p-4">
    <div class="suppliers-toolbar d-flex align-items-end justify-content-between flex-wrap gap-3 mb-3">
      <form ref="searchForm" class="suppliers-search" role="search" @submit.prevent="submitSearch">
        <label class="form-label" for="suppliers-search-input">Поиск поставщика</label>
        <div class="input-group">
          <input
            id="suppliers-search-input"
            v-model="searchDraft"
            class="form-control"
            name="search"
            type="search"
            maxlength="100"
            placeholder="Введите название поставщика"
            autocomplete="off"
          >
          <button class="btn btn-primary" type="submit" :disabled="suppliersQuery.isFetching.value">
            Поиск
          </button>
        </div>
      </form>
      <div class="suppliers-actions">
        <button class="btn btn-success" type="button" @click="openCreateModal">
          Добавить поставщика
        </button>
        <span class="badge text-bg-secondary suppliers-count">
          {{ formatCount(suppliersPage.total) }} поставщиков
        </span>
      </div>
    </div>

    <div v-if="suppliersQuery.isLoading.value" class="text-secondary py-4" aria-live="polite">
      Загрузка поставщиков...
    </div>
    <div v-else-if="suppliersError" class="alert alert-danger" role="alert">
      {{ suppliersError }}
    </div>
    <div v-else-if="shouldShowSuppliersEmpty" class="alert alert-light border" role="status">
      {{ currentSearch ? "По запросу ничего не найдено." : "Поставщики пока не добавлены." }}
    </div>

    <div v-if="shouldShowSuppliersTable" class="table-responsive suppliers-table">
      <table class="table table-hover align-middle mb-0">
        <thead>
          <tr>
            <th scope="col">Поставщик</th>
            <th scope="col">Телефон</th>
            <th scope="col">Товары</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="supplier in suppliersPage.items"
            :key="supplier.id"
            class="supplier-summary-row"
            tabindex="0"
            role="button"
            :aria-label="`Открыть поставщика ${supplier.name || `#${formatCount(supplier.id)}`}`"
            @click="openSupplierDetail(supplier)"
            @keydown.enter.prevent="openSupplierDetail(supplier)"
          >
            <td class="supplier-name-cell">
              <div class="fw-semibold">{{ supplier.name || "Без названия" }}</div>
              <div class="supplier-meta">ID {{ formatCount(supplier.id) }}</div>
            </td>
            <td>{{ supplier.phone_number || "Не указан" }}</td>
            <td>
              <span :class="supplier.product_links_count > 0 ? 'fw-semibold' : 'text-secondary'">
                {{ formatCount(supplier.product_links_count) }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <nav
      v-if="shouldShowSuppliersPagination"
      class="suppliers-pagination mt-3"
      aria-label="Пагинация поставщиков"
    >
      <button
        class="btn btn-outline-primary"
        type="button"
        :disabled="!suppliersPage.has_previous || suppliersQuery.isFetching.value"
        @click="goToPage(suppliersPage.page - 1)"
      >
        Назад
      </button>
      <span class="suppliers-page-summary">
        Страница {{ formatCount(suppliersPage.page) }} из {{ formatCount(totalSupplierPages) }}
      </span>
      <button
        class="btn btn-outline-primary"
        type="button"
        :disabled="!suppliersPage.has_next || suppliersQuery.isFetching.value"
        @click="goToPage(suppliersPage.page + 1)"
      >
        Вперед
      </button>
    </nav>

    <Teleport to="body">
      <div
        v-if="isCreateModalOpen"
        class="modal fade show d-block"
        tabindex="-1"
        role="dialog"
        aria-modal="true"
        aria-labelledby="supplier-create-modal-title"
        @click.self="closeCreateModal"
      >
        <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
          <form ref="createFormElement" class="modal-content supplier-create-form" @submit.prevent="submitSupplierCreate">
            <div class="modal-header">
              <h2 id="supplier-create-modal-title" class="modal-title fs-5">Добавить поставщика</h2>
              <button
                class="btn-close"
                type="button"
                aria-label="Закрыть"
                :disabled="createSupplierMutation.isPending.value"
                @click="closeCreateModal"
              ></button>
            </div>

            <div class="modal-body">
              <div v-if="createError" class="alert alert-danger" role="alert">
                {{ createError }}
              </div>

              <div class="row g-3">
                <div class="col-12 col-lg-7">
                  <label class="form-label" for="supplier-create-name">Название</label>
                  <input
                    id="supplier-create-name"
                    v-model="supplierCreateForm.name"
                    class="form-control"
                    name="name"
                    type="text"
                    maxlength="255"
                    autocomplete="organization"
                    required
                    :disabled="createSupplierMutation.isPending.value"
                  >
                </div>
                <div class="col-12 col-lg-5">
                  <label class="form-label" for="supplier-create-phone-number">Телефон</label>
                  <input
                    id="supplier-create-phone-number"
                    v-model="supplierCreateForm.phoneNumber"
                    class="form-control"
                    name="phone_number"
                    type="tel"
                    inputmode="tel"
                    pattern="(8[0-9]{10}|[+]7[0-9]{10})"
                    maxlength="12"
                    autocomplete="tel"
                    placeholder="+77001234567"
                    required
                    :disabled="createSupplierMutation.isPending.value"
                  >
                  <div class="form-text">Формат: +7XXXXXXXXXX или 8XXXXXXXXXX.</div>
                </div>
              </div>
            </div>

            <div class="modal-footer supplier-create-footer">
              <button
                class="btn btn-outline-secondary"
                type="button"
                :disabled="createSupplierMutation.isPending.value"
                @click="closeCreateModal"
              >
                Отмена
              </button>
              <button class="btn btn-primary" type="submit" :disabled="createSupplierMutation.isPending.value">
                {{ createSupplierMutation.isPending.value ? "Сохранение..." : "Создать поставщика" }}
              </button>
            </div>
          </form>
        </div>
      </div>
      <div v-if="isCreateModalOpen" class="modal-backdrop fade show"></div>
    </Teleport>

    <SupplierDetailModal
      :supplier-id="selectedSupplierId"
      :is-open="isDetailModalOpen"
      @close="closeSupplierDetail"
    />
  </section>
</template>
