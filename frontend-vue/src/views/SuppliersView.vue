<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { useRoute, useRouter } from "vue-router";

import { DEFAULT_PAGE_SIZE, FIRST_PAGE, getSuppliers } from "../lib/api";
import { formatCount, getRequestErrorMessage } from "../lib/format";
import type { PaginatedResponse, SupplierSummaryResponse } from "../types/api";

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
const searchForm = ref<HTMLFormElement | null>(null);
const searchDraft = ref(currentSearchFromRoute());

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
          <tr v-for="supplier in suppliersPage.items" :key="supplier.id">
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
  </section>
</template>
