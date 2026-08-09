<script setup lang="ts">
import { computed } from "vue";
import { useQuery } from "@tanstack/vue-query";

import { getRestock, getSale } from "../lib/api";
import {
  DEFAULT_QUANTITY_UNIT,
  formatCount,
  formatCurrency,
  formatDateTime,
  formatQuantity,
  getRequestErrorMessage,
} from "../lib/format";
import { activeWorkspaceId } from "../lib/workspaceSession";
import type {
  RestockLineResponse,
  RestockResponse,
  SaleLineResponse,
  SaleResponse,
} from "../types/api";

type MovementKind = "restock" | "sale";
type MovementResponse = RestockResponse | SaleResponse;
type MovementLine = RestockLineResponse | SaleLineResponse;

const props = defineProps<{
  isOpen: boolean;
  kind: MovementKind;
  movementId: number | null;
}>();
const emit = defineEmits<{
  (event: "close"): void;
}>();

const detailId = computed(() => Number(props.movementId || 0));
const detailQuery = useQuery<MovementResponse>({
  queryKey: computed(() => [props.kind, activeWorkspaceId.value, "detail", detailId.value]),
  queryFn: () => (
    props.kind === "restock"
      ? getRestock(detailId.value)
      : getSale(detailId.value)
  ),
  enabled: computed(() => Boolean(activeWorkspaceId.value) && props.isOpen && detailId.value > 0),
});

const movement = computed(() => detailQuery.data.value || null);
const lines = computed<MovementLine[]>(() => movement.value?.lines || []);
const note = computed(() => String(movement.value?.note || "").trim());
const labels = computed(() => (
  props.kind === "restock"
    ? {
      title: "Пополнение",
      loading: "Загрузка пополнения...",
      error: "детали пополнения",
      linesEmpty: "В пополнении нет позиций.",
      summaryAmount: "Сумма закупки",
    }
    : {
      title: "Продажа",
      loading: "Загрузка продажи...",
      error: "детали продажи",
      linesEmpty: "В продаже нет позиций.",
      summaryAmount: "Выручка",
    }
));
const detailError = computed(() => (
  detailQuery.error.value
    ? getRequestErrorMessage(detailQuery.error.value, labels.value.error)
    : ""
));
const shouldShowContent = computed(() => (
  Boolean(movement.value)
    && !detailQuery.isLoading.value
    && !detailError.value
));
const totalCost = computed(() => (
  lines.value.reduce((sum, line) => sum + getLineCost(line), 0)
));
const totalRevenue = computed(() => (
  lines.value.reduce((sum, line) => sum + getLineRevenue(line), 0)
));
const primaryAmount = computed(() => (
  props.kind === "restock" ? totalCost.value : totalRevenue.value
));

function closeModal() {
  emit("close");
}

function isRestockLine(line: MovementLine): line is RestockLineResponse {
  return "restock_quantity" in line;
}

function getLineQuantity(line: MovementLine) {
  return isRestockLine(line)
    ? Number(line.restock_quantity || 0)
    : Number(line.sale_quantity || 0);
}

function getLineUnit(line: MovementLine) {
  return line.quantity_unit_snapshot || DEFAULT_QUANTITY_UNIT;
}

function getLineUnitCost(line: MovementLine) {
  return Number(line.unit_cost_snapshot || 0);
}

function getLineUnitSalePrice(line: MovementLine) {
  return isRestockLine(line) ? 0 : Number(line.unit_sale_price_snapshot || 0);
}

function getLineCost(line: MovementLine) {
  return getLineQuantity(line) * getLineUnitCost(line);
}

function getLineRevenue(line: MovementLine) {
  return isRestockLine(line)
    ? getLineCost(line)
    : getLineQuantity(line) * getLineUnitSalePrice(line);
}

function getLineProfit(line: MovementLine) {
  return getLineRevenue(line) - getLineCost(line);
}

function getProductName(line: MovementLine) {
  return line.product_name || `Товар #${formatCount(line.product_id)}`;
}

function getSupplierName(line: MovementLine) {
  return line.supplier_name || `Поставщик #${formatCount(line.supplier_id)}`;
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
      aria-labelledby="stock-movement-detail-modal-title"
      @click.self="closeModal"
    >
      <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
        <div class="modal-content stock-movement-detail-modal-content">
          <div class="modal-header">
            <h2 id="stock-movement-detail-modal-title" class="modal-title fs-5">
              {{ movement ? `${labels.title} #${formatCount(movement.id)}` : labels.title }}
            </h2>
            <button
              class="btn-close"
              type="button"
              aria-label="Закрыть"
              @click="closeModal"
            ></button>
          </div>

          <div class="modal-body">
            <div v-if="detailQuery.isLoading.value" class="text-secondary py-4" aria-live="polite">
              {{ labels.loading }}
            </div>
            <div v-else-if="detailError" class="alert alert-danger" role="alert">
              {{ detailError }}
            </div>

            <div v-if="shouldShowContent && movement" class="stock-movement-detail-content">
              <div
                class="stock-movement-detail-summary"
                :class="kind === 'sale' ? 'sale-detail-summary' : 'restock-detail-summary'"
              >
                <div>
                  <div class="stock-movement-detail-label">ID</div>
                  <div class="fw-semibold">{{ formatCount(movement.id) }}</div>
                </div>
                <div>
                  <div class="stock-movement-detail-label">Дата</div>
                  <div class="fw-semibold">{{ formatDateTime(movement.created_at) }}</div>
                </div>
                <div>
                  <div class="stock-movement-detail-label">Позиции</div>
                  <div class="fw-semibold">{{ formatCount(lines.length) }} позиций</div>
                </div>
                <div>
                  <div class="stock-movement-detail-label">{{ labels.summaryAmount }}</div>
                  <div class="fw-semibold">{{ formatCurrency(primaryAmount) }}</div>
                </div>
                <div v-if="kind === 'sale'">
                  <div class="stock-movement-detail-label">Себестоимость</div>
                  <div class="fw-semibold">{{ formatCurrency(totalCost) }}</div>
                </div>
                <div v-if="kind === 'sale'">
                  <div class="stock-movement-detail-label">Прибыль</div>
                  <div class="fw-semibold">{{ formatCurrency(totalRevenue - totalCost) }}</div>
                </div>
              </div>

              <section class="mt-4">
                <h3 class="fs-6">Комментарий</h3>
                <p class="mb-0" :class="{ 'text-secondary': !note }">
                  {{ note || "Без комментария" }}
                </p>
              </section>

              <section class="mt-4">
                <h3 class="fs-6">Позиции</h3>
                <div v-if="lines.length === 0" class="alert alert-light border" role="status">
                  {{ labels.linesEmpty }}
                </div>
                <div
                  v-else
                  class="table-responsive stock-movement-detail-lines-table"
                  :class="kind === 'sale' ? 'sale-detail-lines-table' : 'restock-detail-lines-table'"
                >
                  <table class="table table-sm align-middle mb-0">
                    <thead>
                      <tr>
                        <th scope="col">Товар</th>
                        <th scope="col">Поставщик</th>
                        <th scope="col">Количество</th>
                        <th scope="col">{{ kind === "sale" ? "Себестоимость" : "Цена закупки" }}</th>
                        <th v-if="kind === 'sale'" scope="col">Цена продажи</th>
                        <th scope="col">{{ kind === "sale" ? "Выручка" : "Сумма" }}</th>
                        <th v-if="kind === 'sale'" scope="col">Прибыль</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="line in lines" :key="line.id">
                        <td>
                          <div class="fw-semibold">{{ getProductName(line) }}</div>
                          <div class="stock-movement-detail-meta">ID {{ formatCount(line.product_id) }}</div>
                        </td>
                        <td>
                          <div class="fw-semibold">{{ getSupplierName(line) }}</div>
                          <div class="stock-movement-detail-meta">ID {{ formatCount(line.supplier_id) }}</div>
                        </td>
                        <td>{{ formatQuantity(getLineQuantity(line), getLineUnit(line)) }}</td>
                        <td>{{ formatCurrency(getLineUnitCost(line)) }}</td>
                        <td v-if="kind === 'sale'">{{ formatCurrency(getLineUnitSalePrice(line)) }}</td>
                        <td class="fw-semibold">{{ formatCurrency(getLineRevenue(line)) }}</td>
                        <td v-if="kind === 'sale'" class="fw-semibold">
                          {{ formatCurrency(getLineProfit(line)) }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </section>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-if="isOpen" class="modal-backdrop fade show"></div>
  </Teleport>
</template>
