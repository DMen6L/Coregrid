<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useRoute, useRouter } from "vue-router";

import StockMovementCreateModal from "../components/StockMovementCreateModal.vue";
import StockMovementDetailModal from "../components/StockMovementDetailModal.vue";
import { DEFAULT_PAGE_SIZE, FIRST_PAGE, getRestocks } from "../lib/api";
import {
  formatCount,
  formatCurrency,
  formatDateTime,
  getRequestErrorMessage,
} from "../lib/format";
import type { PaginatedResponse, RestockSummaryResponse } from "../types/api";

const EMPTY_RESTOCKS_PAGE: PaginatedResponse<RestockSummaryResponse> = {
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
const selectedRestockId = ref<number | null>(null);
const filterDraft = reactive({
  dateFrom: currentDateFromRoute("from"),
  dateTo: currentDateFromRoute("to"),
});

const currentDateFrom = computed(() => currentDateFromRoute("from"));
const currentDateTo = computed(() => currentDateFromRoute("to"));
const currentPage = computed(() => currentPageFromRoute());
const restocksQuery = useQuery({
  queryKey: computed(() => [
    "restocks",
    "list",
    currentDateFrom.value,
    currentDateTo.value,
    currentPage.value,
    DEFAULT_PAGE_SIZE,
  ]),
  queryFn: () => getRestocks({
    dateFrom: currentDateFrom.value,
    dateTo: currentDateTo.value,
    page: currentPage.value,
    pageSize: DEFAULT_PAGE_SIZE,
  }),
});

const restocksPage = computed(() => restocksQuery.data.value || EMPTY_RESTOCKS_PAGE);
const restocksError = computed(() => (
  restocksQuery.error.value
    ? getRequestErrorMessage(restocksQuery.error.value, "пополнения")
    : ""
));
const hasRestocks = computed(() => restocksPage.value.items.length > 0);
const shouldShowRestocksTable = computed(() => (
  hasRestocks.value
    && !restocksQuery.isLoading.value
    && !restocksError.value
));
const shouldShowRestocksEmpty = computed(() => (
  !restocksQuery.isLoading.value
    && !restocksError.value
    && restocksPage.value.items.length === 0
));
const shouldShowRestocksPagination = computed(() => (
  restocksPage.value.total > 0
    && !restocksQuery.isLoading.value
    && !restocksError.value
));
const totalRestockPages = computed(() => Math.max(restocksPage.value.total_pages, 1));
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

  navigateRestocks({
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
  navigateRestocks({
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

function openRestockDetail(restock: RestockSummaryResponse) {
  selectedRestockId.value = restock.id;
  isDetailModalOpen.value = true;
}

function closeRestockDetail() {
  isDetailModalOpen.value = false;
  selectedRestockId.value = null;
}

function handleRestockRowKeydown(event: KeyboardEvent, restock: RestockSummaryResponse) {
  if (event.key !== "Enter" && event.key !== " ") {
    return;
  }

  event.preventDefault();
  openRestockDetail(restock);
}

async function handleRestockCreated() {
  isCreateModalOpen.value = false;

  navigateRestocks({
    dateFrom: currentDateFrom.value,
    dateTo: currentDateTo.value,
    page: FIRST_PAGE,
  });

  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ["restocks"] }),
    queryClient.invalidateQueries({ queryKey: ["products"] }),
    queryClient.invalidateQueries({ queryKey: ["summaries"] }),
  ]);
}

function goToPage(page: number) {
  navigateRestocks({
    dateFrom: currentDateFrom.value,
    dateTo: currentDateTo.value,
    page,
  });
}

function navigateRestocks({
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

  void router.push({ name: "restocks", query });
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
    <div class="restocks-toolbar d-flex align-items-end justify-content-between flex-wrap gap-3 mb-3">
      <form ref="filterForm" class="restocks-filters" @submit.prevent="submitFilters">
        <div class="movement-filter-header">
          <label class="form-label" for="restocks-date-from-input">Период пополнений</label>
          <button
            v-if="hasFilterDraft || hasActiveFilters"
            class="btn btn-link movement-filter-reset"
            type="button"
            :disabled="restocksQuery.isFetching.value && !hasActiveFilters"
            @click="resetFilters"
          >
            Сбросить
          </button>
        </div>
        <div class="restocks-filter-controls">
          <input
            id="restocks-date-from-input"
            v-model="filterDraft.dateFrom"
            class="form-control"
            name="from"
            type="date"
            aria-label="Дата начала"
            @change="submitFilters"
          >
          <input
            id="restocks-date-to-input"
            v-model="filterDraft.dateTo"
            class="form-control"
            name="to"
            type="date"
            aria-label="Дата окончания"
            @change="submitFilters"
          >
        </div>
      </form>
      <div class="restocks-actions">
        <button class="btn btn-success" type="button" @click="openCreateModal">
          Добавить пополнение
        </button>
        <span class="badge text-bg-secondary restocks-count">
          {{ formatCount(restocksPage.total) }} пополнений
        </span>
      </div>
    </div>

    <div v-if="restocksQuery.isLoading.value" class="text-secondary py-4" aria-live="polite">
      Загрузка пополнений...
    </div>
    <div v-else-if="restocksError" class="alert alert-danger" role="alert">
      {{ restocksError }}
    </div>
    <div v-else-if="shouldShowRestocksEmpty" class="alert alert-light border" role="status">
      {{ hasActiveFilters ? "За выбранный период ничего не найдено." : "Пополнения пока не добавлены." }}
    </div>

    <div v-if="shouldShowRestocksTable" class="table-responsive restocks-table">
      <table class="table table-hover align-middle mb-0">
        <thead>
          <tr>
            <th scope="col">Пополнение</th>
            <th scope="col">Дата</th>
            <th scope="col">Позиции</th>
            <th scope="col">Сумма закупки</th>
            <th scope="col">Комментарий</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="restock in restocksPage.items"
            :key="restock.id"
            class="restock-summary-row"
            tabindex="0"
            role="button"
            :aria-label="`Открыть пополнение #${formatCount(restock.id)}`"
            @click="openRestockDetail(restock)"
            @keydown="handleRestockRowKeydown($event, restock)"
          >
            <td class="restock-summary-cell">
              <div class="fw-semibold">Пополнение #{{ formatCount(restock.id) }}</div>
            </td>
            <td>{{ formatDateTime(restock.created_at) }}</td>
            <td>{{ formatCount(restock.lines_count) }} позиций</td>
            <td class="fw-semibold">{{ formatCurrency(restock.costs) }}</td>
            <td :class="{ 'text-secondary': !restock.note }">
              {{ getNoteText(restock.note) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <nav
      v-if="shouldShowRestocksPagination"
      class="restocks-pagination mt-3"
      aria-label="Пагинация пополнений"
    >
      <button
        class="btn btn-outline-primary"
        type="button"
        :disabled="!restocksPage.has_previous || restocksQuery.isFetching.value"
        @click="goToPage(restocksPage.page - 1)"
      >
        Назад
      </button>
      <span class="restocks-page-summary">
        Страница {{ formatCount(restocksPage.page) }} из {{ formatCount(totalRestockPages) }}
      </span>
      <button
        class="btn btn-outline-primary"
        type="button"
        :disabled="!restocksPage.has_next || restocksQuery.isFetching.value"
        @click="goToPage(restocksPage.page + 1)"
      >
        Вперед
      </button>
    </nav>

    <StockMovementCreateModal
      :is-open="isCreateModalOpen"
      kind="restock"
      @close="closeCreateModal"
      @created="handleRestockCreated"
    />

    <StockMovementDetailModal
      :is-open="isDetailModalOpen"
      :movement-id="selectedRestockId"
      kind="restock"
      @close="closeRestockDetail"
    />
  </section>
</template>
