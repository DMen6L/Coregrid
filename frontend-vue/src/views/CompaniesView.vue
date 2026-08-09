<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { useRoute, useRouter } from "vue-router";

import CompanyDetailModal from "../components/CompanyDetailModal.vue";
import { createCompany, DEFAULT_PAGE_SIZE, FIRST_PAGE, getCompanies } from "../lib/api";
import { formatCount, getCreateErrorMessage, getRequestErrorMessage } from "../lib/format";
import { activeWorkspaceId } from "../lib/workspaceSession";
import type { CompanyCreatePayload, CompanyResponse, PaginatedResponse } from "../types/api";

const EMPTY_COMPANIES_PAGE: PaginatedResponse<CompanyResponse> = {
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
const selectedCompanyId = ref<number | null>(null);
const createError = ref("");
const companyCreateForm = reactive({
  name: "",
  iin: "",
});

const currentSearch = computed(() => currentSearchFromRoute());
const currentPage = computed(() => currentPageFromRoute());
const companiesQuery = useQuery({
  queryKey: computed(() => [
    "companies",
    activeWorkspaceId.value,
    "list",
    currentSearch.value,
    currentPage.value,
    DEFAULT_PAGE_SIZE,
  ]),
  queryFn: () => getCompanies({
    search: currentSearch.value,
    page: currentPage.value,
    pageSize: DEFAULT_PAGE_SIZE,
  }),
  enabled: computed(() => Boolean(activeWorkspaceId.value)),
});
const createCompanyMutation = useMutation({
  mutationFn: createCompanyFromForm,
  onSuccess: handleCompanyCreateSuccess,
  onError: (error) => {
    createError.value = getCreateErrorMessage(error, "компанию");
  },
});

const companiesPage = computed(() => companiesQuery.data.value || EMPTY_COMPANIES_PAGE);
const companiesError = computed(() => (
  companiesQuery.error.value
    ? getRequestErrorMessage(companiesQuery.error.value, "компании")
    : ""
));
const hasCompanies = computed(() => companiesPage.value.items.length > 0);
const shouldShowCompaniesTable = computed(() => (
  hasCompanies.value
    && !companiesQuery.isLoading.value
    && !companiesError.value
));
const shouldShowCompaniesEmpty = computed(() => (
  !companiesQuery.isLoading.value
    && !companiesError.value
    && companiesPage.value.items.length === 0
));
const shouldShowCompaniesPagination = computed(() => (
  companiesPage.value.total > 0
    && !companiesQuery.isLoading.value
    && !companiesError.value
));
const totalCompanyPages = computed(() => Math.max(companiesPage.value.total_pages, 1));

watch(currentSearch, (nextSearch) => {
  searchDraft.value = nextSearch;
});

function submitSearch() {
  if (!searchForm.value?.reportValidity()) {
    return;
  }

  navigateCompanies({
    search: searchDraft.value,
    page: FIRST_PAGE,
  });
}

function goToPage(page: number) {
  navigateCompanies({
    search: currentSearch.value,
    page,
  });
}

function openCompanyDetail(company: CompanyResponse) {
  selectedCompanyId.value = company.id;
  isDetailModalOpen.value = true;
}

function closeCompanyDetail() {
  isDetailModalOpen.value = false;
  selectedCompanyId.value = null;
}

function openCreateModal() {
  resetCompanyCreateForm();
  createError.value = "";
  isCreateModalOpen.value = true;
}

function closeCreateModal() {
  if (createCompanyMutation.isPending.value) {
    return;
  }

  isCreateModalOpen.value = false;
}

function submitCompanyCreate() {
  createError.value = "";

  if (!createFormElement.value?.reportValidity()) {
    return;
  }

  createCompanyMutation.mutate();
}

function createCompanyFromForm() {
  const payload: CompanyCreatePayload = {
    name: normalizeText(companyCreateForm.name),
    iin: normalizeOptionalText(companyCreateForm.iin),
  };

  return createCompany(payload);
}

async function handleCompanyCreateSuccess(company: CompanyResponse) {
  const companyName = company.name || normalizeText(companyCreateForm.name);

  isCreateModalOpen.value = false;
  resetCompanyCreateForm();
  navigateCompanies({
    search: companyName,
    page: FIRST_PAGE,
  });

  await queryClient.invalidateQueries({ queryKey: ["companies", activeWorkspaceId.value] });
}

function resetCompanyCreateForm() {
  companyCreateForm.name = "";
  companyCreateForm.iin = "";
}

function navigateCompanies({ search, page }: { search: string; page: number }) {
  const trimmedSearch = String(search || "").trim();
  const nextPage = Math.max(Number(page) || FIRST_PAGE, FIRST_PAGE);
  const query: Record<string, string> = {};

  if (trimmedSearch) {
    query.search = trimmedSearch;
  }

  if (nextPage > FIRST_PAGE) {
    query.page = String(nextPage);
  }

  void router.push({ name: "companies", query });
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

function normalizeOptionalText(value: string) {
  return normalizeText(value) || null;
}
</script>

<template>
  <section class="container-fluid p-4">
    <div class="companies-toolbar d-flex align-items-end justify-content-between flex-wrap gap-3 mb-3">
      <form ref="searchForm" class="companies-search" role="search" @submit.prevent="submitSearch">
        <label class="form-label" for="companies-search-input">Поиск компании</label>
        <div class="input-group">
          <input
            id="companies-search-input"
            v-model="searchDraft"
            class="form-control"
            name="search"
            type="search"
            maxlength="100"
            placeholder="Введите название компании"
            autocomplete="off"
          >
          <button class="btn btn-primary" type="submit" :disabled="companiesQuery.isFetching.value">
            Поиск
          </button>
        </div>
      </form>
      <div class="companies-actions">
        <button class="btn btn-success" type="button" @click="openCreateModal">
          Добавить компанию
        </button>
        <span class="badge text-bg-secondary companies-count">
          {{ formatCount(companiesPage.total) }} компаний
        </span>
      </div>
    </div>

    <div v-if="companiesQuery.isLoading.value" class="text-secondary py-4" aria-live="polite">
      Загрузка компаний...
    </div>
    <div v-else-if="companiesError" class="alert alert-danger" role="alert">
      {{ companiesError }}
    </div>
    <div v-else-if="shouldShowCompaniesEmpty" class="alert alert-light border" role="status">
      {{ currentSearch ? "По запросу ничего не найдено." : "Компании пока не добавлены." }}
    </div>

    <div v-if="shouldShowCompaniesTable" class="table-responsive companies-table">
      <table class="table table-hover align-middle mb-0">
        <thead>
          <tr>
            <th scope="col">Компания</th>
            <th scope="col">ИИН</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="company in companiesPage.items"
            :key="company.id"
            class="company-summary-row"
            tabindex="0"
            role="button"
            :aria-label="`Открыть компанию ${company.name || `#${formatCount(company.id)}`}`"
            @click="openCompanyDetail(company)"
            @keydown.enter.prevent="openCompanyDetail(company)"
          >
            <td class="company-name-cell">
              <div class="fw-semibold">{{ company.name || "Без названия" }}</div>
              <div class="company-meta">ID {{ formatCount(company.id) }}</div>
            </td>
            <td :class="{ 'text-secondary': !company.iin }">
              {{ company.iin || "Не указан" }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <nav
      v-if="shouldShowCompaniesPagination"
      class="companies-pagination mt-3"
      aria-label="Пагинация компаний"
    >
      <button
        class="btn btn-outline-primary"
        type="button"
        :disabled="!companiesPage.has_previous || companiesQuery.isFetching.value"
        @click="goToPage(companiesPage.page - 1)"
      >
        Назад
      </button>
      <span class="companies-page-summary">
        Страница {{ formatCount(companiesPage.page) }} из {{ formatCount(totalCompanyPages) }}
      </span>
      <button
        class="btn btn-outline-primary"
        type="button"
        :disabled="!companiesPage.has_next || companiesQuery.isFetching.value"
        @click="goToPage(companiesPage.page + 1)"
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
        aria-labelledby="company-create-modal-title"
        @click.self="closeCreateModal"
      >
        <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
          <form ref="createFormElement" class="modal-content company-create-form" @submit.prevent="submitCompanyCreate">
            <div class="modal-header">
              <h2 id="company-create-modal-title" class="modal-title fs-5">Добавить компанию</h2>
              <button
                class="btn-close"
                type="button"
                aria-label="Закрыть"
                :disabled="createCompanyMutation.isPending.value"
                @click="closeCreateModal"
              ></button>
            </div>

            <div class="modal-body">
              <div v-if="createError" class="alert alert-danger" role="alert">
                {{ createError }}
              </div>

              <div class="row g-3">
                <div class="col-12 col-lg-7">
                  <label class="form-label" for="company-create-name">Название</label>
                  <input
                    id="company-create-name"
                    v-model="companyCreateForm.name"
                    class="form-control"
                    name="name"
                    type="text"
                    maxlength="255"
                    autocomplete="organization"
                    required
                    :disabled="createCompanyMutation.isPending.value"
                  >
                </div>
                <div class="col-12 col-lg-5">
                  <label class="form-label" for="company-create-iin">ИИН</label>
                  <input
                    id="company-create-iin"
                    v-model="companyCreateForm.iin"
                    class="form-control"
                    name="iin"
                    type="text"
                    inputmode="numeric"
                    pattern="[0-9]{12}"
                    minlength="12"
                    maxlength="12"
                    autocomplete="off"
                    :disabled="createCompanyMutation.isPending.value"
                  >
                  <div class="form-text">Можно оставить пустым. Если указан, 12 цифр без пробелов.</div>
                </div>
              </div>
            </div>

            <div class="modal-footer company-create-footer">
              <button
                class="btn btn-outline-secondary"
                type="button"
                :disabled="createCompanyMutation.isPending.value"
                @click="closeCreateModal"
              >
                Отмена
              </button>
              <button class="btn btn-primary" type="submit" :disabled="createCompanyMutation.isPending.value">
                {{ createCompanyMutation.isPending.value ? "Сохранение..." : "Создать компанию" }}
              </button>
            </div>
          </form>
        </div>
      </div>
      <div v-if="isCreateModalOpen" class="modal-backdrop fade show"></div>
    </Teleport>

    <CompanyDetailModal
      :company-id="selectedCompanyId"
      :is-open="isDetailModalOpen"
      @close="closeCompanyDetail"
    />
  </section>
</template>
