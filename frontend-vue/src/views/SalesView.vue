<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useRoute, useRouter } from "vue-router";

import StockMovementCreateModal from "../components/StockMovementCreateModal.vue";
import StockMovementDetailModal from "../components/StockMovementDetailModal.vue";
import { DEFAULT_PAGE_SIZE, FIRST_PAGE, getSales } from "../lib/api";
import {
  formatCount,
  formatCurrency,
  formatDateTime,
  getRequestErrorMessage,
} from "../lib/format";
import type { PaginatedResponse, SaleSummaryResponse } from "../types/api";

const EMPTY_SALES_PAGE: PaginatedResponse<SaleSummaryResponse> = {
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
const filterForm = ref<HTMLFormElement | null>(null);
const isCreateModalOpen = ref(false);
const isDetailModalOpen = ref(false);
const selectedSaleId = ref<number | null>(null);
const filterDraft = reactive({
  dateFrom: currentDateFromRoute("from"),
  dateTo: currentDateFromRoute("to"),
});

const currentDateFrom = computed(() => currentDateFromRoute("from"));
const currentDateTo = computed(() => currentDateFromRoute("to"));
const currentPage = computed(() => currentPageFromRoute());
const salesQuery = useQuery({
  queryKey: computed(() => [
    "sales",
    "list",
    currentDateFrom.value,
    currentDateTo.value,
    currentPage.value,
    DEFAULT_PAGE_SIZE,
  ]),
  queryFn: () => getSales({
    dateFrom: currentDateFrom.value,
    dateTo: currentDateTo.value,
    page: currentPage.value,
    pageSize: DEFAULT_PAGE_SIZE,
  }),
});

const salesPage = computed(() => salesQuery.data.value || EMPTY_SALES_PAGE);
const salesError = computed(() => (
  salesQuery.error.value
    ? getRequestErrorMessage(salesQuery.error.value, "продажи")
    : ""
));
const hasSales = computed(() => salesPage.value.items.length > 0);
const shouldShowSalesTable = computed(() => (
  hasSales.value
    && !salesQuery.isLoading.value
    && !salesError.value
));
const shouldShowSalesEmpty = computed(() => (
  !salesQuery.isLoading.value
    && !salesError.value
    && salesPage.value.items.length === 0
));
const shouldShowSalesPagination = computed(() => (
  salesPage.value.total > 0
    && !salesQuery.isLoading.value
    && !salesError.value
));
const totalSalePages = computed(() => Math.max(salesPage.value.total_pages, 1));
const hasActiveFilters = computed(() => Boolean(currentDateFrom.value || currentDateTo.value));
const hasFilterDraft = computed(() => Boolean(filterDraft.dateFrom || filterDraft.dateTo));

watch([currentDateFrom, currentDateTo], ([nextFrom, nextTo]) => {
  filterDraft.dateFrom = nextFrom;
  filterDraft.dateTo = nextTo;
});

function submitFilters() {
  if (!filterForm.value?.reportValidity()) {
    return;
  }

  if (
    filterDraft.dateFrom === currentDateFrom.value
      && filterDraft.dateTo === currentDateTo.value
      && currentPage.value === FIRST_PAGE
  ) {
    return;
  }

  navigateSales({
    dateFrom: filterDraft.dateFrom,
    dateTo: filterDraft.dateTo,
    page: FIRST_PAGE,
  });
}

function resetFilters() {
  if (!hasFilterDraft.value && !hasActiveFilters.value && currentPage.value === FIRST_PAGE) {
    return;
  }

  filterDraft.dateFrom = "";
  filterDraft.dateTo = "";
  navigateSales({
    dateFrom: "",
    dateTo: "",
    page: FIRST_PAGE,
  });
}

function openCreateModal() {
  isCreateModalOpen.value = true;
}

function closeCreateModal() {
  isCreateModalOpen.value = false;
}

function openSaleDetail(sale: SaleSummaryResponse) {
  selectedSaleId.value = sale.id;
  isDetailModalOpen.value = true;
}

function closeSaleDetail() {
  isDetailModalOpen.value = false;
  selectedSaleId.value = null;
}

function handleSaleRowKeydown(event: KeyboardEvent, sale: SaleSummaryResponse) {
  if (event.key !== "Enter" && event.key !== " ") {
    return;
  }

  event.preventDefault();
  openSaleDetail(sale);
}

async function handleSaleCreated() {
  isCreateModalOpen.value = false;

  navigateSales({
    dateFrom: currentDateFrom.value,
    dateTo: currentDateTo.value,
    page: FIRST_PAGE,
  });

  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ["sales"] }),
    queryClient.invalidateQueries({ queryKey: ["products"] }),
    queryClient.invalidateQueries({ queryKey: ["summaries"] }),
  ]);
}

function goToPage(page: number) {
  navigateSales({
    dateFrom: currentDateFrom.value,
    dateTo: currentDateTo.value,
    page,
  });
}

function navigateSales({
  dateFrom,
  dateTo,
  page,
}: {
  dateFrom: string;
  dateTo: string;
  page: number;
}) {
  const nextPage = Math.max(Number(page) || FIRST_PAGE, FIRST_PAGE);
  const query: Record<string, string> = {};

  if (dateFrom) {
    query.from = dateFrom;
  }

  if (dateTo) {
    query.to = dateTo;
  }

  if (nextPage > FIRST_PAGE) {
    query.page = String(nextPage);
  }

  void router.push({ name: "sales", query });
}

function currentDateFromRoute(key: "from" | "to") {
  return normalizeRouteString(route.query[key]);
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

function getNoteText(note: string | null) {
  return String(note || "").trim() || "Без комментария";
}
</script>

<template>
  <section class="container-fluid p-4">
    <div class="sales-toolbar d-flex align-items-end justify-content-between flex-wrap gap-3 mb-3">
      <form ref="filterForm" class="sales-filters" @submit.prevent="submitFilters">
        <div class="movement-filter-header">
          <label class="form-label" for="sales-date-from-input">Период продаж</label>
          <button
            v-if="hasFilterDraft || hasActiveFilters"
            class="btn btn-link movement-filter-reset"
            type="button"
            :disabled="salesQuery.isFetching.value && !hasActiveFilters"
            @click="resetFilters"
          >
            Сбросить
          </button>
        </div>
        <div class="sales-filter-controls">
          <input
            id="sales-date-from-input"
            v-model="filterDraft.dateFrom"
            class="form-control"
            name="from"
            type="date"
            aria-label="Дата начала"
            @change="submitFilters"
          >
          <input
            id="sales-date-to-input"
            v-model="filterDraft.dateTo"
            class="form-control"
            name="to"
            type="date"
            aria-label="Дата окончания"
            @change="submitFilters"
          >
        </div>
      </form>
      <div class="sales-actions">
        <button class="btn btn-success" type="button" @click="openCreateModal">
          Добавить продажу
        </button>
        <span class="badge text-bg-secondary sales-count">
          {{ formatCount(salesPage.total) }} продаж
        </span>
      </div>
    </div>

    <div v-if="salesQuery.isLoading.value" class="text-secondary py-4" aria-live="polite">
      Загрузка продаж...
    </div>
    <div v-else-if="salesError" class="alert alert-danger" role="alert">
      {{ salesError }}
    </div>
    <div v-else-if="shouldShowSalesEmpty" class="alert alert-light border" role="status">
      {{ hasActiveFilters ? "За выбранный период ничего не найдено." : "Продажи пока не зарегистрированы." }}
    </div>

    <div v-if="shouldShowSalesTable" class="table-responsive sales-table">
      <table class="table table-hover align-middle mb-0">
        <thead>
          <tr>
            <th scope="col">Продажа</th>
            <th scope="col">Дата</th>
            <th scope="col">Позиции</th>
            <th scope="col">Выручка</th>
            <th scope="col">Комментарий</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="sale in salesPage.items"
            :key="sale.id"
            class="sale-summary-row"
            tabindex="0"
            role="button"
            :aria-label="`Открыть продажу #${formatCount(sale.id)}`"
            @click="openSaleDetail(sale)"
            @keydown="handleSaleRowKeydown($event, sale)"
          >
            <td class="sale-summary-cell">
              <div class="fw-semibold">Продажа #{{ formatCount(sale.id) }}</div>
            </td>
            <td>{{ formatDateTime(sale.created_at) }}</td>
            <td>{{ formatCount(sale.lines_count) }} позиций</td>
            <td class="fw-semibold">{{ formatCurrency(sale.revenue) }}</td>
            <td :class="{ 'text-secondary': !sale.note }">
              {{ getNoteText(sale.note) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <nav
      v-if="shouldShowSalesPagination"
      class="sales-pagination mt-3"
      aria-label="Пагинация продаж"
    >
      <button
        class="btn btn-outline-primary"
        type="button"
        :disabled="!salesPage.has_previous || salesQuery.isFetching.value"
        @click="goToPage(salesPage.page - 1)"
      >
        Назад
      </button>
      <span class="sales-page-summary">
        Страница {{ formatCount(salesPage.page) }} из {{ formatCount(totalSalePages) }}
      </span>
      <button
        class="btn btn-outline-primary"
        type="button"
        :disabled="!salesPage.has_next || salesQuery.isFetching.value"
        @click="goToPage(salesPage.page + 1)"
      >
        Вперед
      </button>
    </nav>

    <StockMovementCreateModal
      :is-open="isCreateModalOpen"
      kind="sale"
      @close="closeCreateModal"
      @created="handleSaleCreated"
    />

    <StockMovementDetailModal
      :is-open="isDetailModalOpen"
      :movement-id="selectedSaleId"
      kind="sale"
      @close="closeSaleDetail"
    />
  </section>
</template>
