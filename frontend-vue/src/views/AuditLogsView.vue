<script setup lang="ts">
import { computed } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { useRoute, useRouter } from "vue-router";

import { DEFAULT_PAGE_SIZE, FIRST_PAGE, getWorkspaceAuditLogs } from "../lib/api";
import { formatCount, formatDateTime, getRequestErrorMessage } from "../lib/format";
import { canManageWorkspace, formatWorkspaceRole } from "../lib/permissions";
import { activeWorkspace, activeWorkspaceId } from "../lib/workspaceSession";
import type { AuditLogResponse, PaginatedResponse } from "../types/api";

const EMPTY_AUDIT_LOGS_PAGE: PaginatedResponse<AuditLogResponse> = {
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

const currentPage = computed(() => currentPageFromRoute());
const canViewAuditLogs = computed(() => canManageWorkspace(activeWorkspace.value?.role));
const workspaceLabel = computed(() => activeWorkspace.value?.name || "Рабочее пространство");
const auditLogsQuery = useQuery({
  queryKey: computed(() => [
    "workspace-audit-logs",
    activeWorkspaceId.value,
    currentPage.value,
    DEFAULT_PAGE_SIZE,
  ]),
  queryFn: () => getWorkspaceAuditLogs({
    page: currentPage.value,
    pageSize: DEFAULT_PAGE_SIZE,
  }),
  enabled: computed(() => Boolean(activeWorkspaceId.value) && canViewAuditLogs.value),
});

const auditLogsPage = computed(() => auditLogsQuery.data.value || EMPTY_AUDIT_LOGS_PAGE);
const auditLogsError = computed(() => (
  auditLogsQuery.error.value
    ? getRequestErrorMessage(auditLogsQuery.error.value, "журнал действий")
    : ""
));
const shouldShowAuditLogsEmpty = computed(() => (
  !auditLogsQuery.isLoading.value
    && !auditLogsError.value
    && auditLogsPage.value.items.length === 0
));
const shouldShowAuditLogsPagination = computed(() => (
  auditLogsPage.value.total > 0
    && !auditLogsQuery.isLoading.value
    && !auditLogsError.value
));
const totalAuditLogPages = computed(() => Math.max(auditLogsPage.value.total_pages, 1));

function goToPage(page: number) {
  const nextPage = Math.max(Number(page) || FIRST_PAGE, FIRST_PAGE);
  const query: Record<string, string> = {};

  if (nextPage > FIRST_PAGE) {
    query.page = String(nextPage);
  }

  void router.push({ name: "audit-logs", query });
}

function getAuditSummary(log: AuditLogResponse) {
  const actor = getActorLabel(log);
  const entity = getEntityLabel(log);
  const target = getTargetLabel(log);

  switch (log.action) {
    case "workspace.created":
      return `${actor} создал рабочее пространство ${entity}.`;
    case "member.created":
    case "member.joined":
      return `${actor} присоединился к рабочему пространству.`;
    case "member.left":
      return `${actor} покинул рабочее пространство.`;
    case "member.removed":
    case "member.deleted":
      return `${actor} удалил участника ${target || entity}.`;
    case "member.role_updated":
    case "member.updated":
      return `${actor} изменил роль участника ${target || entity}.`;
    case "invitation.created":
    case "invitation.create":
      return `${actor} отправил приглашение ${entity}.`;
    case "invitation.revoked":
    case "invitation.delete":
      return `${actor} отозвал приглашение ${entity}.`;
    case "company.created":
    case "company.create":
      return `${actor} добавил компанию ${entity}.`;
    case "company.updated":
      return `${actor} обновил компанию ${entity}.`;
    case "supplier.created":
      return `${actor} добавил поставщика ${entity}.`;
    case "supplier.updated":
      return `${actor} обновил поставщика ${entity}.`;
    case "product.created":
      return `${actor} добавил товар ${entity}.`;
    case "product.updated":
      return `${actor} обновил товар ${entity}.`;
    case "product_supplier.created":
      return `${actor} добавил связь товара с поставщиком ${entity}.`;
    case "product_supplier.updated":
      return `${actor} обновил связь товара с поставщиком ${entity}.`;
    case "product_supplier.deleted":
      return `${actor} удалил связь товара с поставщиком ${entity}.`;
    case "restock.created":
      return `${actor} создал пополнение ${entity}.`;
    case "sale.created":
      return `${actor} создал продажу ${entity}.`;
    case "tag.created":
      return `${actor} создал тег ${entity}.`;
    case "tag.deleted":
      return `${actor} удалил тег ${entity}.`;
    default:
      return `${actor} выполнил действие ${log.action} для ${entity}.`;
  }
}

function getActorLabel(log: AuditLogResponse) {
  return log.actor_name || log.actor_email || "Удаленный пользователь";
}

function getTargetLabel(log: AuditLogResponse) {
  return log.target_name || log.target_email || "";
}

function getEntityLabel(log: AuditLogResponse) {
  if (log.entity_label) {
    return `«${log.entity_label}»`;
  }

  if (log.entity_id) {
    return `${formatEntityType(log.entity_type)} #${log.entity_id}`;
  }

  return formatEntityType(log.entity_type);
}

function getEntityMeta(log: AuditLogResponse) {
  if (!log.entity_id) {
    return formatEntityType(log.entity_type);
  }

  return `${formatEntityType(log.entity_type)} #${log.entity_id}`;
}

function getChangeEntries(log: AuditLogResponse) {
  return Object.entries(log.changes || {}).map(([field, change]) => ({
    field,
    before: getChangeValue(change, "before", "old"),
    after: getChangeValue(change, "after", "new"),
  }));
}

function getExtraDataEntries(log: AuditLogResponse) {
  return Object.entries(log.extra_data || {});
}

function getChangeValue(change: unknown, preferredKey: string, fallbackKey: string) {
  if (change && typeof change === "object") {
    const record = change as Record<string, unknown>;

    if (preferredKey in record) {
      return record[preferredKey];
    }

    if (fallbackKey in record) {
      return record[fallbackKey];
    }
  }

  return null;
}

function formatEntityType(entityType: string) {
  switch (entityType) {
    case "workspace":
      return "Пространство";
    case "member":
    case "membership":
      return "Участник";
    case "invitation":
      return "Приглашение";
    case "company":
      return "Компания";
    case "supplier":
      return "Поставщик";
    case "product":
      return "Товар";
    case "product_supplier":
      return "Связь поставщика";
    case "restock":
      return "Пополнение";
    case "sale":
      return "Продажа";
    case "tag":
      return "Тег";
    default:
      return entityType || "Объект";
  }
}

function formatFieldName(fieldName: string) {
  switch (fieldName) {
    case "name":
      return "Название";
    case "email":
      return "Email";
    case "role":
      return "Роль";
    case "iin":
      return "ИИН";
    case "phone_number":
      return "Телефон";
    case "company_id":
      return "Компания";
    case "quantity_unit":
      return "Единица";
    case "low_stock_threshold":
      return "Нижний порог";
    case "tags":
      return "Теги";
    case "purchase_price":
      return "Цена закупки";
    case "margin_percent":
      return "Маржа";
    case "sale_price":
      return "Цена продажи";
    case "quantity":
      return "Количество";
    case "lines_count":
      return "Строк";
    case "total_quantity":
      return "Всего единиц";
    case "total_cost":
      return "Сумма";
    case "supplier_links_count":
      return "Поставщиков";
    default:
      return fieldName.replaceAll("_", " ");
  }
}

function formatAuditValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "Не указано";
  }

  if (Array.isArray(value)) {
    return value.length ? value.map(formatAuditValue).join(", ") : "Пусто";
  }

  if (typeof value === "boolean") {
    return value ? "Да" : "Нет";
  }

  if (typeof value === "number") {
    return formatCount(value);
  }

  if (typeof value === "string") {
    return looksLikeDateTime(value) ? formatDateTime(value) : value;
  }

  return JSON.stringify(value);
}

function looksLikeDateTime(value: string) {
  return /^\d{4}-\d{2}-\d{2}T/.test(value);
}

function currentPageFromRoute() {
  const routePage = Array.isArray(route.query.page)
    ? route.query.page[0]
    : route.query.page;
  const page = Number(routePage || FIRST_PAGE);

  return Number.isFinite(page) && page >= FIRST_PAGE ? Math.trunc(page) : FIRST_PAGE;
}
</script>

<template>
  <section class="container-fluid p-4 audit-logs-page">
    <div class="audit-logs-toolbar d-flex align-items-end justify-content-between flex-wrap gap-3 mb-3">
      <div>
        <h1 class="fs-4 mb-1">Журнал действий</h1>
        <p class="text-secondary mb-0">
          {{ workspaceLabel }} · {{ formatWorkspaceRole(activeWorkspace?.role) }}
        </p>
      </div>
      <span v-if="canViewAuditLogs" class="badge text-bg-secondary audit-logs-count">
        {{ formatCount(auditLogsPage.total) }} записей
      </span>
    </div>

    <div v-if="!canViewAuditLogs" class="alert alert-warning" role="alert">
      Недостаточно прав для просмотра журнала действий этого рабочего пространства.
    </div>

    <template v-else>
      <div v-if="auditLogsQuery.isLoading.value" class="text-secondary py-4" aria-live="polite">
        Загрузка журнала действий...
      </div>
      <div v-else-if="auditLogsError" class="alert alert-danger" role="alert">
        {{ auditLogsError }}
      </div>
      <div v-else-if="shouldShowAuditLogsEmpty" class="alert alert-light border mb-0" role="status">
        Записей журнала пока нет.
      </div>

      <div v-if="auditLogsPage.items.length > 0 && !auditLogsError" class="audit-timeline">
        <article
          v-for="log in auditLogsPage.items"
          :key="log.id"
          class="audit-timeline-item"
        >
          <div class="audit-timeline-marker" aria-hidden="true"></div>
          <div class="audit-timeline-content">
            <div class="audit-timeline-header">
              <div>
                <h2 class="audit-timeline-title">{{ getAuditSummary(log) }}</h2>
                <div class="audit-timeline-meta">
                  <span>{{ formatDateTime(log.created_at) }}</span>
                  <span>{{ getEntityMeta(log) }}</span>
                  <span v-if="getTargetLabel(log)">Затронут: {{ getTargetLabel(log) }}</span>
                </div>
              </div>
              <span class="badge text-bg-light border audit-action-badge">{{ log.action }}</span>
            </div>

            <div
              v-if="getChangeEntries(log).length > 0"
              class="audit-detail-group"
              aria-label="Изменения"
            >
              <div
                v-for="change in getChangeEntries(log)"
                :key="change.field"
                class="audit-change-row"
              >
                <span class="audit-detail-label">{{ formatFieldName(change.field) }}</span>
                <span class="audit-change-value">{{ formatAuditValue(change.before) }}</span>
                <span class="audit-change-arrow" aria-hidden="true">→</span>
                <span class="audit-change-value">{{ formatAuditValue(change.after) }}</span>
              </div>
            </div>

            <div
              v-if="getExtraDataEntries(log).length > 0"
              class="audit-extra-data"
              aria-label="Дополнительные данные"
            >
              <span
                v-for="[key, value] in getExtraDataEntries(log)"
                :key="key"
                class="audit-extra-chip"
              >
                <span class="audit-detail-label">{{ formatFieldName(key) }}:</span>
                {{ formatAuditValue(value) }}
              </span>
            </div>
          </div>
        </article>
      </div>

      <nav
        v-if="shouldShowAuditLogsPagination"
        class="audit-logs-pagination mt-3"
        aria-label="Пагинация журнала действий"
      >
        <button
          class="btn btn-outline-primary"
          type="button"
          :disabled="!auditLogsPage.has_previous || auditLogsQuery.isFetching.value"
          @click="goToPage(auditLogsPage.page - 1)"
        >
          Назад
        </button>
        <span class="audit-logs-page-summary">
          Страница {{ formatCount(auditLogsPage.page) }} из {{ formatCount(totalAuditLogPages) }}
        </span>
        <button
          class="btn btn-outline-primary"
          type="button"
          :disabled="!auditLogsPage.has_next || auditLogsQuery.isFetching.value"
          @click="goToPage(auditLogsPage.page + 1)"
        >
          Вперед
        </button>
      </nav>
    </template>
  </section>
</template>
