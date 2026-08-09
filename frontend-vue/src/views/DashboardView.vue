<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { useQuery } from "@tanstack/vue-query";

import { getSummaries } from "../lib/api";
import {
  formatCount,
  formatCurrency,
  formatFullDate,
  formatShortDate,
  getRequestErrorMessage,
} from "../lib/format";
import { activeWorkspaceId } from "../lib/workspaceSession";
import type {
  BestSalesMode,
  DailySalesResponse,
  SummariesResponse,
} from "../types/api";

const MIN_DASHBOARD_DAYS = 7;
const MAX_DASHBOARD_DAYS = 365;
const DEFAULT_DASHBOARD_DAYS = 7;
const DEFAULT_BEST_SALES_MODE: BestSalesMode = "quantity";
const BEST_SALES_MODE_CONFIG: Record<
  BestSalesMode,
  { summary: string; heading: string; format: (value: number) => string }
> = {
  quantity: {
    summary: "По количеству",
    heading: "Количество",
    format: formatCount,
  },
  revenue: {
    summary: "По выручке",
    heading: "Выручка",
    format: formatCurrency,
  },
  gross_profit: {
    summary: "По валовой прибыли",
    heading: "Валовая прибыль",
    format: formatCurrency,
  },
};
const EMPTY_DASHBOARD_DATA: SummariesResponse = {
  dashboard_sales_value: 0,
  dashboard_sales_count: 0,
  low_stock: 0,
  out_of_stock: 0,
  latest_sales: [],
  top_products: [],
  top_suppliers: [],
};

const form = reactive({
  days: DEFAULT_DASHBOARD_DAYS,
  bestSalesMode: DEFAULT_BEST_SALES_MODE,
});
const dashboardParams = ref({
  days: DEFAULT_DASHBOARD_DAYS,
  bestSalesMode: DEFAULT_BEST_SALES_MODE,
});

const dashboardQuery = useQuery({
  queryKey: computed(() => [
    "summaries",
    activeWorkspaceId.value,
    dashboardParams.value.days,
    dashboardParams.value.bestSalesMode,
  ]),
  queryFn: () => getSummaries(dashboardParams.value),
  enabled: computed(() => Boolean(activeWorkspaceId.value)),
});

const dashboardData = computed(() => dashboardQuery.data.value || EMPTY_DASHBOARD_DATA);
const modeConfig = computed(() => BEST_SALES_MODE_CONFIG[dashboardParams.value.bestSalesMode]);
const dashboardError = computed(() => (
  dashboardQuery.error.value
    ? getRequestErrorMessage(dashboardQuery.error.value, "дэшборд")
    : ""
));
const dailySales = computed(() => (
  dashboardQuery.data.value
    ? createDashboardDailyRange(
      dashboardQuery.data.value.latest_sales,
      dashboardParams.value.days,
    )
    : []
));
const maxDailySalesValue = computed(() => Math.max(
  ...dailySales.value.map((item) => Number(item.sales_value || 0)),
  0,
));
const shouldShowDailyEmpty = computed(() => (
  !dashboardQuery.isLoading.value
    && !dashboardError.value
    && dailySales.value.length === 0
));
const shouldShowTopProductsEmpty = computed(() => (
  !dashboardQuery.isLoading.value
    && !dashboardError.value
    && dashboardData.value.top_products.length === 0
));
const shouldShowTopSuppliersEmpty = computed(() => (
  !dashboardQuery.isLoading.value
    && !dashboardError.value
    && dashboardData.value.top_suppliers.length === 0
));

function applyDashboardFilters() {
  dashboardParams.value = {
    days: normalizeDays(form.days),
    bestSalesMode: form.bestSalesMode,
  };
  form.days = dashboardParams.value.days;
}

function normalizeDays(value: number) {
  const days = Number(value) || DEFAULT_DASHBOARD_DAYS;

  return Math.min(Math.max(Math.trunc(days), MIN_DASHBOARD_DAYS), MAX_DASHBOARD_DAYS);
}

function getBarHeight(value: number) {
  if (maxDailySalesValue.value <= 0) {
    return 3;
  }

  return Math.max((Number(value || 0) / maxDailySalesValue.value) * 100, 3);
}

function createDashboardDailyRange(items: DailySalesResponse[], days: number) {
  const salesByDate = new Map<string, number>();

  for (const item of Array.isArray(items) ? items : []) {
    if (item.date) {
      salesByDate.set(item.date, Number(item.sales_value || 0));
    }
  }

  return createDateRange(days).map((dateKey) => ({
    date: dateKey,
    sales_value: salesByDate.get(dateKey) || 0,
  }));
}

function createDateRange(days: number) {
  const count = Math.max(Number(days) || 1, 1);
  const endDate = new Date();
  const startDate = new Date(endDate);
  const dateKeys: string[] = [];

  endDate.setHours(0, 0, 0, 0);
  startDate.setHours(0, 0, 0, 0);
  startDate.setDate(endDate.getDate() - count + 1);

  for (let offset = 0; offset < count; offset += 1) {
    const date = new Date(startDate);

    date.setDate(startDate.getDate() + offset);
    dateKeys.push(formatDateKey(date));
  }

  return dateKeys;
}

function formatDateKey(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}
</script>

<template>
  <section class="container-fluid p-4">
    <div class="row g-3">
      <div class="col-12 col-sm-6 col-xl-3">
        <div class="card dashboard-card text-center h-100">
          <div class="card-body">
            <h5 class="card-title">Продажи</h5>
            <p class="card-text fs-1 fw-bold">{{ formatCurrency(dashboardData.dashboard_sales_value) }}</p>
          </div>
        </div>
      </div>
      <div class="col-12 col-sm-6 col-xl-3">
        <div class="card dashboard-card text-center h-100">
          <div class="card-body">
            <h5 class="card-title">Продаж сделано</h5>
            <p class="card-text fs-1 fw-bold">{{ formatCount(dashboardData.dashboard_sales_count) }}</p>
          </div>
        </div>
      </div>
      <div class="col-12 col-sm-6 col-xl-3">
        <div class="card dashboard-card text-center h-100 bg-warning-subtle">
          <div class="card-body">
            <h5 class="card-title">Мало остатков</h5>
            <p class="card-text fs-1 fw-bold">{{ formatCount(dashboardData.low_stock) }}</p>
          </div>
        </div>
      </div>
      <div class="col-12 col-sm-6 col-xl-3">
        <div class="card dashboard-card text-center h-100 bg-danger-subtle">
          <div class="card-body">
            <h5 class="card-title">Нет на складе</h5>
            <p class="card-text fs-1 fw-bold">{{ formatCount(dashboardData.out_of_stock) }}</p>
          </div>
        </div>
      </div>
    </div>

    <div class="dashboard-sales-trend mt-4">
      <div class="dashboard-sales-trend-header">
        <div>
          <h2 class="fs-5 mb-1">Продажи по дням</h2>
          <p class="text-secondary mb-0">
            {{ dashboardError ? "Данные недоступны" : `Последние ${formatCount(dashboardParams.days)} дней` }}
          </p>
        </div>
        <form class="dashboard-sales-period-form" @submit.prevent="applyDashboardFilters">
          <div class="dashboard-sales-controls">
            <div>
              <label class="form-label" for="dashboard-sales-period-input">Период</label>
              <div class="input-group">
                <input
                  id="dashboard-sales-period-input"
                  v-model.number="form.days"
                  class="form-control"
                  name="days_ago"
                  type="number"
                  :min="MIN_DASHBOARD_DAYS"
                  :max="MAX_DASHBOARD_DAYS"
                  step="1"
                  required
                >
                <span class="input-group-text">дней</span>
              </div>
            </div>
            <div>
              <label class="form-label" for="dashboard-best-sales-mode-select">Метрика</label>
              <select
                id="dashboard-best-sales-mode-select"
                v-model="form.bestSalesMode"
                class="form-select"
                name="best_sales_mode"
              >
                <option value="quantity">Количество</option>
                <option value="revenue">Выручка</option>
                <option value="gross_profit">Валовая прибыль</option>
              </select>
            </div>
            <button class="btn btn-primary" type="submit" :disabled="dashboardQuery.isFetching.value">
              {{ dashboardQuery.isFetching.value ? "Загрузка..." : "Обновить" }}
            </button>
          </div>
        </form>
      </div>

      <div v-if="dashboardQuery.isLoading.value" class="alert alert-light border mb-0" role="status">
        Загрузка дэшборда...
      </div>
      <div v-else-if="dashboardError" class="alert alert-danger mb-0" role="alert">
        {{ dashboardError }}
      </div>

      <div
        v-if="!dashboardError && dailySales.length > 0"
        class="dashboard-sales-chart"
        role="img"
        aria-label="График продаж по дням"
      >
        <div class="dashboard-sales-chart-bars">
          <div
            v-for="item in dailySales"
            :key="item.date"
            class="dashboard-sales-chart-item"
            :title="`${formatFullDate(item.date)}: ${formatCurrency(item.sales_value)}`"
          >
            <div class="dashboard-sales-chart-track">
              <div
                class="dashboard-sales-chart-bar"
                :class="{ 'is-empty': Number(item.sales_value || 0) === 0 }"
                :style="{ height: `${getBarHeight(item.sales_value)}%` }"
              ></div>
            </div>
            <div class="dashboard-sales-chart-label">{{ formatShortDate(item.date) }}</div>
          </div>
        </div>
      </div>
      <div v-if="shouldShowDailyEmpty" class="alert alert-light border mb-0" role="status">
        За выбранный период продаж не найдено.
      </div>

      <div class="dashboard-best-sales">
        <div class="dashboard-table-heading">
          <h3 class="fs-6 mb-0">Топ 5 товаров</h3>
          <span class="text-secondary">{{ modeConfig.summary }}</span>
        </div>
        <div v-if="shouldShowTopProductsEmpty" class="alert alert-light border" role="status">
          За выбранный период нет товаров для рейтинга.
        </div>
        <div class="table-responsive dashboard-best-sales-table">
          <table class="table table-hover align-middle mb-0">
            <thead>
              <tr>
                <th scope="col">Товар</th>
                <th scope="col">{{ modeConfig.heading }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in dashboardData.top_products" :key="item.product_id">
                <td>
                  <div class="fw-semibold">{{ item.product_name || "Без названия" }}</div>
                  <div class="product-meta">ID {{ formatCount(item.product_id) }}</div>
                </td>
                <td class="fw-semibold">{{ modeConfig.format(item.metric) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="table-responsive dashboard-sales-daily-table">
        <table class="table table-hover align-middle mb-0">
          <thead>
            <tr>
              <th scope="col">Дата</th>
              <th scope="col">Продажи</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in dailySales" :key="item.date">
              <td>{{ formatFullDate(item.date) }}</td>
              <td class="fw-semibold">{{ formatCurrency(item.sales_value) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="dashboard-top-suppliers">
        <div class="dashboard-table-heading">
          <h3 class="fs-6 mb-0">Топ 5 поставщиков</h3>
          <span class="text-secondary">По количеству товаров</span>
        </div>
        <div v-if="shouldShowTopSuppliersEmpty" class="alert alert-light border" role="status">
          Поставщики с товарами пока не найдены.
        </div>
        <div class="table-responsive dashboard-top-suppliers-table">
          <table class="table table-hover align-middle mb-0">
            <thead>
              <tr>
                <th scope="col">Поставщик</th>
                <th scope="col">Товаров</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in dashboardData.top_suppliers" :key="item.supplier_id">
                <td>
                  <div class="fw-semibold">{{ item.supplier_name || "Без названия" }}</div>
                  <div class="supplier-meta">ID {{ formatCount(item.supplier_id) }}</div>
                </td>
                <td class="fw-semibold">{{ formatCount(item.supplied_products) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </section>
</template>
