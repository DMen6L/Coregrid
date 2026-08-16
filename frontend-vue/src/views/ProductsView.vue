<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { useRoute, useRouter } from "vue-router";
import type { LocationQueryRaw } from "vue-router";

import ProductDetailModal from "../components/ProductDetailModal.vue";
import {
  createProductAtomic,
  DEFAULT_PAGE_SIZE,
  FIRST_PAGE,
  getCompanies,
  getProducts,
  getSuppliers,
  getTags,
} from "../lib/api";
import {
  DEFAULT_QUANTITY_UNIT,
  formatCount,
  formatCurrency,
  formatDateTime,
  formatQuantity,
  getCreateErrorMessage,
  getRequestErrorMessage,
} from "../lib/format";
import { activeWorkspaceId } from "../lib/workspaceSession";
import type {
  CompanyResponse,
  PaginatedResponse,
  ProductAtomicCreatePayload,
  ProductResponse,
  ProductSupplierAtomicCreatePayload,
  ProductSummaryResponse,
  StockStatus,
  SupplierCreatePayload,
  SupplierSummaryResponse,
  TagSummaryResponse,
} from "../types/api";

type ProductStockStatus = StockStatus | "none";
type StockStatusFilter = StockStatus | "";
type CompanyMode = "existing" | "new";
type SupplierMode = "existing" | "new";
type ProductFilterChipType = "search" | "company" | "supplier" | "stock_status" | "tag";

interface ProductFilterChip {
  id: string;
  type: ProductFilterChipType;
  label: string;
  value: string;
}

const POPULAR_TAGS_LIMIT = 10;
const COMPANY_LOOKUP_PAGE_SIZE = 10;
const SUPPLIER_LOOKUP_PAGE_SIZE = 10;
const FILTER_LOOKUP_DEBOUNCE_MS = 300;
const FILTER_LOOKUP_PAGE_SIZE = 8;
const STOCK_STATUS: Record<ProductStockStatus, { label: string; className: string }> = {
  available: { label: "В наличии", className: "text-bg-success" },
  low: { label: "Мало", className: "text-bg-warning" },
  out: { label: "Нет", className: "text-bg-danger" },
  none: { label: "Без данных", className: "text-bg-secondary" },
};
const STOCK_STATUS_FILTER_OPTIONS: { value: StockStatusFilter; label: string }[] = [
  { value: "", label: "Все статусы" },
  { value: "available", label: STOCK_STATUS.available.label },
  { value: "low", label: STOCK_STATUS.low.label },
  { value: "out", label: STOCK_STATUS.out.label },
];
const EMPTY_PRODUCTS_PAGE: PaginatedResponse<ProductSummaryResponse> = {
  items: [],
  page: FIRST_PAGE,
  page_size: DEFAULT_PAGE_SIZE,
  total: 0,
  total_pages: 0,
  has_next: false,
  has_previous: false,
};
const EMPTY_TAGS_PAGE: PaginatedResponse<TagSummaryResponse> = {
  items: [],
  page: FIRST_PAGE,
  page_size: POPULAR_TAGS_LIMIT,
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
const filterDraft = reactive({
  companyName: currentCompanyNameFromRoute(),
  supplierName: currentSupplierNameFromRoute(),
  stockStatus: currentStockStatusFromRoute(),
});
const isCreateModalOpen = ref(false);
const isDetailModalOpen = ref(false);
const selectedProductId = ref<number | null>(null);
const createError = ref("");
const filterCompanyLookupTerm = ref("");
const filterSupplierLookupTerm = ref("");
const isCompanyFilterOpen = ref(false);
const isSupplierFilterOpen = ref(false);
const companyLookupTerm = ref("");
const supplierLookupTerm = ref("");
let companyFilterLookupTimer: number | null = null;
let supplierFilterLookupTimer: number | null = null;
const productCreateForm = reactive({
  name: "",
  tags: "",
  quantityUnit: DEFAULT_QUANTITY_UNIT,
  lowStockThreshold: 5,
  companyMode: "existing" as CompanyMode,
  companySearch: "",
  selectedCompany: null as CompanyResponse | null,
  newCompanyName: "",
  newCompanyIin: "",
  linkEnabled: false,
  supplierMode: "existing" as SupplierMode,
  supplierSearch: "",
  selectedSupplier: null as SupplierSummaryResponse | null,
  newSupplierName: "",
  newSupplierPhoneNumber: "",
  purchasePrice: 1,
  marginPercent: 0,
  salePrice: "",
  quantity: 0,
});

const currentSearch = computed(() => currentSearchFromRoute());
const currentCompanyName = computed(() => currentCompanyNameFromRoute());
const currentSupplierName = computed(() => currentSupplierNameFromRoute());
const currentStockStatus = computed(() => currentStockStatusFromRoute());
const currentTags = computed(() => currentTagsFromRoute());
const currentPage = computed(() => currentPageFromRoute());
const productsQuery = useQuery({
  queryKey: computed(() => [
    "products",
    activeWorkspaceId.value,
    currentSearch.value,
    currentCompanyName.value,
    currentSupplierName.value,
    currentStockStatus.value,
    currentTags.value,
    currentPage.value,
    DEFAULT_PAGE_SIZE,
  ]),
  queryFn: () => getProducts({
    search: currentSearch.value,
    companyName: currentCompanyName.value,
    supplierName: currentSupplierName.value,
    stockStatus: currentStockStatus.value,
    tags: currentTags.value,
    page: currentPage.value,
    pageSize: DEFAULT_PAGE_SIZE,
  }),
  enabled: computed(() => Boolean(activeWorkspaceId.value)),
});
const popularTagsQuery = useQuery({
  queryKey: computed(() => ["tags", activeWorkspaceId.value, "popular", POPULAR_TAGS_LIMIT]),
  queryFn: () => getTags({
    page: FIRST_PAGE,
    pageSize: POPULAR_TAGS_LIMIT,
  }),
  enabled: computed(() => Boolean(activeWorkspaceId.value)),
});
const companyLookupQuery = useQuery({
  queryKey: computed(() => [
    "companies",
    activeWorkspaceId.value,
    "lookup",
    companyLookupTerm.value,
    COMPANY_LOOKUP_PAGE_SIZE,
  ]),
  queryFn: () => getCompanies({
    search: companyLookupTerm.value,
    page: FIRST_PAGE,
    pageSize: COMPANY_LOOKUP_PAGE_SIZE,
  }),
  enabled: computed(() => (
    Boolean(activeWorkspaceId.value)
      && isCreateModalOpen.value
      && productCreateForm.companyMode === "existing"
      && companyLookupTerm.value.length >= 2
  )),
});
const supplierLookupQuery = useQuery({
  queryKey: computed(() => [
    "suppliers",
    activeWorkspaceId.value,
    "lookup",
    supplierLookupTerm.value,
    SUPPLIER_LOOKUP_PAGE_SIZE,
  ]),
  queryFn: () => getSuppliers({
    search: supplierLookupTerm.value,
    page: FIRST_PAGE,
    pageSize: SUPPLIER_LOOKUP_PAGE_SIZE,
  }),
  enabled: computed(() => (
    Boolean(activeWorkspaceId.value)
      && isCreateModalOpen.value
      && productCreateForm.linkEnabled
      && productCreateForm.supplierMode === "existing"
      && supplierLookupTerm.value.length >= 2
  )),
});
const companyFilterQuery = useQuery({
  queryKey: computed(() => [
    "companies",
    activeWorkspaceId.value,
    "product-filter",
    filterCompanyLookupTerm.value,
    FILTER_LOOKUP_PAGE_SIZE,
  ]),
  queryFn: () => getCompanies({
    search: filterCompanyLookupTerm.value,
    page: FIRST_PAGE,
    pageSize: FILTER_LOOKUP_PAGE_SIZE,
  }),
  enabled: computed(() => (
    Boolean(activeWorkspaceId.value)
      && isCompanyFilterOpen.value
      && filterCompanyLookupTerm.value.length >= 2
  )),
});
const supplierFilterQuery = useQuery({
  queryKey: computed(() => [
    "suppliers",
    activeWorkspaceId.value,
    "product-filter",
    filterSupplierLookupTerm.value,
    FILTER_LOOKUP_PAGE_SIZE,
  ]),
  queryFn: () => getSuppliers({
    search: filterSupplierLookupTerm.value,
    page: FIRST_PAGE,
    pageSize: FILTER_LOOKUP_PAGE_SIZE,
  }),
  enabled: computed(() => (
    Boolean(activeWorkspaceId.value)
      && isSupplierFilterOpen.value
      && filterSupplierLookupTerm.value.length >= 2
  )),
});
const createProductMutation = useMutation({
  mutationFn: createProductFromForm,
  onSuccess: handleProductCreateSuccess,
  onError: (error) => {
    createError.value = getCreateErrorMessage(error, "товар");
  },
});

const productsPage = computed(() => productsQuery.data.value || EMPTY_PRODUCTS_PAGE);
const selectedProductSummary = computed(() => (
  productsPage.value.items.find((product) => product.id === selectedProductId.value) || null
));
const popularTagsPage = computed(() => popularTagsQuery.data.value || EMPTY_TAGS_PAGE);
const companyLookupResults = computed(() => companyLookupQuery.data.value?.items || []);
const supplierLookupResults = computed(() => supplierLookupQuery.data.value?.items || []);
const companyFilterResults = computed(() => companyFilterQuery.data.value?.items || []);
const supplierFilterResults = computed(() => supplierFilterQuery.data.value?.items || []);
const productsError = computed(() => (
  productsQuery.error.value
    ? getRequestErrorMessage(productsQuery.error.value, "товары")
    : ""
));
const popularTagsError = computed(() => (
  popularTagsQuery.error.value
    ? getRequestErrorMessage(popularTagsQuery.error.value, "популярные теги")
    : ""
));
const companyLookupError = computed(() => (
  companyLookupQuery.error.value
    ? getRequestErrorMessage(companyLookupQuery.error.value, "компании")
    : ""
));
const supplierLookupError = computed(() => (
  supplierLookupQuery.error.value
    ? getRequestErrorMessage(supplierLookupQuery.error.value, "поставщиков")
    : ""
));
const companyFilterError = computed(() => (
  companyFilterQuery.error.value
    ? getRequestErrorMessage(companyFilterQuery.error.value, "компании")
    : ""
));
const supplierFilterError = computed(() => (
  supplierFilterQuery.error.value
    ? getRequestErrorMessage(supplierFilterQuery.error.value, "поставщиков")
    : ""
));
const hasProducts = computed(() => productsPage.value.items.length > 0);
const shouldShowProductsTable = computed(() => (
  hasProducts.value
    && !productsQuery.isLoading.value
    && !productsError.value
));
const shouldShowProductsEmpty = computed(() => (
  !productsQuery.isLoading.value
    && !productsError.value
    && productsPage.value.items.length === 0
));
const hasActiveProductFilters = computed(() => Boolean(
  currentSearch.value
    || currentCompanyName.value
    || currentSupplierName.value
    || currentStockStatus.value
    || currentTags.value.length,
));
const productsEmptyMessage = computed(() => (
  hasActiveProductFilters.value
    ? "По фильтрам ничего не найдено."
    : "Товары пока не добавлены."
));
const activeProductFilterChips = computed<ProductFilterChip[]>(() => {
  const chips: ProductFilterChip[] = [];

  if (currentSearch.value) {
    chips.push({
      id: "search",
      type: "search",
      label: `Поиск: ${currentSearch.value}`,
      value: currentSearch.value,
    });
  }

  if (currentCompanyName.value) {
    chips.push({
      id: "company",
      type: "company",
      label: `Компания: ${currentCompanyName.value}`,
      value: currentCompanyName.value,
    });
  }

  if (currentSupplierName.value) {
    chips.push({
      id: "supplier",
      type: "supplier",
      label: `Поставщик: ${currentSupplierName.value}`,
      value: currentSupplierName.value,
    });
  }

  if (currentStockStatus.value) {
    chips.push({
      id: "stock_status",
      type: "stock_status",
      label: `Статус: ${getStockStatusFilterLabel(currentStockStatus.value)}`,
      value: currentStockStatus.value,
    });
  }

  currentTags.value.forEach((tag) => {
    chips.push({
      id: `tag:${tag}`,
      type: "tag",
      label: `Тег: ${tag}`,
      value: tag,
    });
  });

  return chips;
});
const shouldShowProductsPagination = computed(() => (
  productsPage.value.total > 0
    && !productsQuery.isLoading.value
    && !productsError.value
));
const totalProductPages = computed(() => Math.max(productsPage.value.total_pages, 1));
const popularTags = computed(() => (
  popularTagsPage.value.items.filter((tag) => normalizeTagName(tag.name))
));
const shouldShowPopularTags = computed(() => (
  popularTagsQuery.isLoading.value
    || Boolean(popularTagsError.value)
    || popularTagsQuery.isSuccess.value
    || popularTags.value.length > 0
));
const shouldShowPopularTagsEmpty = computed(() => (
  popularTagsQuery.isSuccess.value
    && !popularTagsQuery.isLoading.value
    && !popularTagsError.value
    && popularTags.value.length === 0
));
const shouldShowCompanyFilterMenu = computed(() => (
  isCompanyFilterOpen.value && normalizeTagName(filterDraft.companyName).length >= 2
));
const shouldShowSupplierFilterMenu = computed(() => (
  isSupplierFilterOpen.value && normalizeTagName(filterDraft.supplierName).length >= 2
));

watch(currentSearch, (nextSearch) => {
  searchDraft.value = nextSearch;
});

watch(currentCompanyName, (nextCompanyName) => {
  filterDraft.companyName = nextCompanyName;
});

watch(currentSupplierName, (nextSupplierName) => {
  filterDraft.supplierName = nextSupplierName;
});

watch(currentStockStatus, (nextStockStatus) => {
  filterDraft.stockStatus = nextStockStatus;
});

watch(() => filterDraft.companyName, (nextCompanyName) => {
  if (isCompanyFilterOpen.value) {
    scheduleCompanyFilterLookup(nextCompanyName);
  }
});

watch(() => filterDraft.supplierName, (nextSupplierName) => {
  if (isSupplierFilterOpen.value) {
    scheduleSupplierFilterLookup(nextSupplierName);
  }
});

watch(() => productCreateForm.companyMode, () => {
  createError.value = "";
  companyLookupTerm.value = "";
});

watch(() => productCreateForm.supplierMode, () => {
  createError.value = "";
  supplierLookupTerm.value = "";
});

watch(() => productCreateForm.linkEnabled, (isEnabled) => {
  createError.value = "";

  if (!isEnabled) {
    supplierLookupTerm.value = "";
  }
});

onBeforeUnmount(() => {
  clearCompanyFilterLookupTimer();
  clearSupplierFilterLookupTimer();
});

function submitSearch() {
  if (!searchForm.value?.reportValidity()) {
    return;
  }

  navigateProducts({
    search: searchDraft.value,
    companyName: filterDraft.companyName,
    supplierName: filterDraft.supplierName,
    stockStatus: filterDraft.stockStatus,
    tags: currentTags.value,
    page: FIRST_PAGE,
  });
}

function resetProductFilters() {
  searchDraft.value = "";
  filterDraft.companyName = "";
  filterDraft.supplierName = "";
  filterDraft.stockStatus = "";
  filterCompanyLookupTerm.value = "";
  filterSupplierLookupTerm.value = "";
  isCompanyFilterOpen.value = false;
  isSupplierFilterOpen.value = false;
  clearCompanyFilterLookupTimer();
  clearSupplierFilterLookupTimer();

  navigateProducts({
    search: "",
    companyName: "",
    supplierName: "",
    stockStatus: "",
    tags: [],
    page: FIRST_PAGE,
  });
}

function goToPage(page: number) {
  navigateProducts({
    search: currentSearch.value,
    companyName: currentCompanyName.value,
    supplierName: currentSupplierName.value,
    stockStatus: currentStockStatus.value,
    tags: currentTags.value,
    page,
  });
}

function toggleTagFilter(tagName: string) {
  const tag = normalizeTagName(tagName);

  if (!tag) {
    return;
  }

  const currentTagSet = new Set(currentTags.value);

  if (currentTagSet.has(tag)) {
    currentTagSet.delete(tag);
  } else {
    currentTagSet.add(tag);
  }

  const nextTags = Array.from(currentTagSet);

  navigateProducts({
    search: searchDraft.value,
    companyName: filterDraft.companyName,
    supplierName: filterDraft.supplierName,
    stockStatus: filterDraft.stockStatus,
    tags: nextTags,
    page: FIRST_PAGE,
  });
}

function removeActiveFilter(chip: ProductFilterChip) {
  const nextFilters = {
    search: currentSearch.value,
    companyName: currentCompanyName.value,
    supplierName: currentSupplierName.value,
    stockStatus: currentStockStatus.value,
    tags: currentTags.value,
    page: FIRST_PAGE,
  };

  if (chip.type === "search") {
    nextFilters.search = "";
    searchDraft.value = "";
  }

  if (chip.type === "company") {
    nextFilters.companyName = "";
    filterDraft.companyName = "";
  }

  if (chip.type === "supplier") {
    nextFilters.supplierName = "";
    filterDraft.supplierName = "";
  }

  if (chip.type === "stock_status") {
    nextFilters.stockStatus = "";
    filterDraft.stockStatus = "";
  }

  if (chip.type === "tag") {
    nextFilters.tags = currentTags.value.filter((tag) => tag !== chip.value);
  }

  navigateProducts(nextFilters);
}

function isTagFilterActive(tagName: string) {
  return currentTags.value.includes(normalizeTagName(tagName));
}

function openProductDetail(product: ProductSummaryResponse) {
  selectedProductId.value = product.id;
  isDetailModalOpen.value = true;
}

function closeProductDetail() {
  isDetailModalOpen.value = false;
  selectedProductId.value = null;
}

function openCreateModal() {
  resetProductCreateForm();
  createError.value = "";
  isCreateModalOpen.value = true;
}

function closeCreateModal() {
  if (createProductMutation.isPending.value) {
    return;
  }

  isCreateModalOpen.value = false;
}

function runCompanyLookup() {
  const search = normalizeTagName(productCreateForm.companySearch);

  productCreateForm.companySearch = search;
  productCreateForm.selectedCompany = null;
  createError.value = "";

  if (search.length < 2) {
    companyLookupTerm.value = "";
    return;
  }

  companyLookupTerm.value = search;
}

function selectCompany(company: CompanyResponse) {
  productCreateForm.selectedCompany = company;
  productCreateForm.companySearch = company.name;
  companyLookupTerm.value = "";
  createError.value = "";
}

function clearSelectedCompany() {
  productCreateForm.selectedCompany = null;
  productCreateForm.companySearch = "";
  companyLookupTerm.value = "";
}

function runSupplierLookup() {
  const search = normalizeTagName(productCreateForm.supplierSearch);

  productCreateForm.supplierSearch = search;
  productCreateForm.selectedSupplier = null;
  createError.value = "";

  if (search.length < 2) {
    supplierLookupTerm.value = "";
    return;
  }

  supplierLookupTerm.value = search;
}

function selectSupplier(supplier: SupplierSummaryResponse) {
  productCreateForm.selectedSupplier = supplier;
  productCreateForm.supplierSearch = supplier.name;
  supplierLookupTerm.value = "";
  createError.value = "";
}

function clearSelectedSupplier() {
  productCreateForm.selectedSupplier = null;
  productCreateForm.supplierSearch = "";
  supplierLookupTerm.value = "";
}

function scheduleCompanyFilterLookup(value: string) {
  clearCompanyFilterLookupTimer();

  const search = normalizeTagName(value);

  if (search.length < 2) {
    filterCompanyLookupTerm.value = "";
    return;
  }

  companyFilterLookupTimer = window.setTimeout(() => {
    filterCompanyLookupTerm.value = search;
    companyFilterLookupTimer = null;
  }, FILTER_LOOKUP_DEBOUNCE_MS);
}

function scheduleSupplierFilterLookup(value: string) {
  clearSupplierFilterLookupTimer();

  const search = normalizeTagName(value);

  if (search.length < 2) {
    filterSupplierLookupTerm.value = "";
    return;
  }

  supplierFilterLookupTimer = window.setTimeout(() => {
    filterSupplierLookupTerm.value = search;
    supplierFilterLookupTimer = null;
  }, FILTER_LOOKUP_DEBOUNCE_MS);
}

function clearCompanyFilterLookupTimer() {
  if (companyFilterLookupTimer === null) {
    return;
  }

  window.clearTimeout(companyFilterLookupTimer);
  companyFilterLookupTimer = null;
}

function clearSupplierFilterLookupTimer() {
  if (supplierFilterLookupTimer === null) {
    return;
  }

  window.clearTimeout(supplierFilterLookupTimer);
  supplierFilterLookupTimer = null;
}

function openCompanyFilterDropdown() {
  isCompanyFilterOpen.value = true;
  scheduleCompanyFilterLookup(filterDraft.companyName);
}

function closeCompanyFilterDropdown() {
  isCompanyFilterOpen.value = false;
}

function selectCompanyFilter(company: CompanyResponse) {
  isCompanyFilterOpen.value = false;
  clearCompanyFilterLookupTimer();
  filterDraft.companyName = company.name;
  filterCompanyLookupTerm.value = "";
}

function clearCompanyFilterDraft() {
  filterDraft.companyName = "";
  filterCompanyLookupTerm.value = "";
  isCompanyFilterOpen.value = false;
  clearCompanyFilterLookupTimer();
}

function openSupplierFilterDropdown() {
  isSupplierFilterOpen.value = true;
  scheduleSupplierFilterLookup(filterDraft.supplierName);
}

function closeSupplierFilterDropdown() {
  isSupplierFilterOpen.value = false;
}

function selectSupplierFilter(supplier: SupplierSummaryResponse) {
  isSupplierFilterOpen.value = false;
  clearSupplierFilterLookupTimer();
  filterDraft.supplierName = supplier.name;
  filterSupplierLookupTerm.value = "";
}

function clearSupplierFilterDraft() {
  filterDraft.supplierName = "";
  filterSupplierLookupTerm.value = "";
  isSupplierFilterOpen.value = false;
  clearSupplierFilterLookupTimer();
}

function submitProductCreate() {
  createError.value = "";

  if (!createFormElement.value?.reportValidity()) {
    return;
  }

  createProductMutation.mutate();
}

async function createProductFromForm() {
  const payload: ProductAtomicCreatePayload = {
    product_name: normalizeTagName(productCreateForm.name),
    ...getAtomicCompanyPayload(),
    tags: parseTags(productCreateForm.tags),
    quantity_unit: normalizeTagName(productCreateForm.quantityUnit) || DEFAULT_QUANTITY_UNIT,
    low_stock_threshold: Math.max(Number(productCreateForm.lowStockThreshold) || 0, 0),
    product_links: getAtomicSupplierLinksPayload(),
  };

  return createProductAtomic(payload);
}

function getAtomicCompanyPayload(): Pick<ProductAtomicCreatePayload, "company_id" | "company"> {
  if (productCreateForm.companyMode === "new") {
    return {
      company: {
        name: normalizeTagName(productCreateForm.newCompanyName),
        iin: normalizeOptionalText(productCreateForm.newCompanyIin),
      },
    };
  }

  if (!productCreateForm.selectedCompany) {
    throw createLocalValidationError("Выберите компанию или создайте новую.");
  }

  return {
    company_id: Number(productCreateForm.selectedCompany.id),
  };
}

function getAtomicSupplierLinksPayload(): ProductSupplierAtomicCreatePayload[] {
  if (!productCreateForm.linkEnabled) {
    return [];
  }

  if (productCreateForm.supplierMode === "new") {
    return [
      {
        supplier: getInlineSupplierPayload(),
        ...getSupplierLinkPayload(),
      },
    ];
  }

  if (!productCreateForm.selectedSupplier) {
    throw createLocalValidationError("Выберите поставщика или создайте нового.");
  }

  return [
    {
      supplier_id: Number(productCreateForm.selectedSupplier.id),
      ...getSupplierLinkPayload(),
    },
  ];
}

function getInlineSupplierPayload(): SupplierCreatePayload {
  return {
    name: normalizeTagName(productCreateForm.newSupplierName),
    phone_number: normalizeTagName(productCreateForm.newSupplierPhoneNumber),
  };
}

function getSupplierLinkPayload(): Omit<ProductSupplierAtomicCreatePayload, "supplier_id" | "supplier"> {
  return {
    purchase_price: normalizeRequiredNumber(productCreateForm.purchasePrice, 1),
    margin_percent: normalizeRequiredNumber(productCreateForm.marginPercent, 0),
    sale_price: normalizeOptionalNumber(productCreateForm.salePrice),
    quantity: normalizeRequiredNumber(productCreateForm.quantity, 0),
  };
}

async function handleProductCreateSuccess(product: ProductResponse) {
  const productName = product.name || normalizeTagName(productCreateForm.name);

  isCreateModalOpen.value = false;
  resetProductCreateForm();

  navigateProducts({
    search: productName,
    companyName: "",
    supplierName: "",
    stockStatus: "",
    tags: [],
    page: FIRST_PAGE,
  });

  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ["products", activeWorkspaceId.value] }),
    queryClient.invalidateQueries({ queryKey: ["tags", activeWorkspaceId.value] }),
    queryClient.invalidateQueries({ queryKey: ["summaries"] }),
    queryClient.invalidateQueries({ queryKey: ["companies", activeWorkspaceId.value] }),
    queryClient.invalidateQueries({ queryKey: ["suppliers", activeWorkspaceId.value] }),
  ]);
}

function resetProductCreateForm() {
  productCreateForm.name = "";
  productCreateForm.tags = "";
  productCreateForm.quantityUnit = DEFAULT_QUANTITY_UNIT;
  productCreateForm.lowStockThreshold = 5;
  productCreateForm.companyMode = "existing";
  productCreateForm.companySearch = "";
  productCreateForm.selectedCompany = null;
  productCreateForm.newCompanyName = "";
  productCreateForm.newCompanyIin = "";
  productCreateForm.linkEnabled = false;
  productCreateForm.supplierMode = "existing";
  productCreateForm.supplierSearch = "";
  productCreateForm.selectedSupplier = null;
  productCreateForm.newSupplierName = "";
  productCreateForm.newSupplierPhoneNumber = "";
  productCreateForm.purchasePrice = 1;
  productCreateForm.marginPercent = 0;
  productCreateForm.salePrice = "";
  productCreateForm.quantity = 0;
  companyLookupTerm.value = "";
  supplierLookupTerm.value = "";
}

function navigateProducts({
  search,
  companyName,
  supplierName,
  stockStatus,
  tags,
  page,
}: {
  search: string;
  companyName: string;
  supplierName: string;
  stockStatus: StockStatusFilter;
  tags: string[];
  page: number;
}) {
  const trimmedSearch = String(search || "").trim();
  const trimmedCompanyName = String(companyName || "").trim();
  const trimmedSupplierName = String(supplierName || "").trim();
  const normalizedStockStatus = normalizeStockStatus(stockStatus);
  const normalizedTags = Array.from(
    new Set(tags.map((tag) => normalizeTagName(tag)).filter(Boolean)),
  );
  const nextPage = Math.max(Number(page) || FIRST_PAGE, FIRST_PAGE);
  const query: LocationQueryRaw = {};

  if (trimmedSearch) {
    query.search = trimmedSearch;
  }

  if (trimmedCompanyName) {
    query.company_name = trimmedCompanyName;
  }

  if (trimmedSupplierName) {
    query.supplier_name = trimmedSupplierName;
  }

  if (normalizedStockStatus) {
    query.stock_status = normalizedStockStatus;
  }

  if (normalizedTags.length > 0) {
    query.tags = normalizedTags;
  }

  if (nextPage > FIRST_PAGE) {
    query.page = String(nextPage);
  }

  void router.push({ name: "products", query });
}

function currentSearchFromRoute() {
  return normalizeRouteString(route.query.search);
}

function currentCompanyNameFromRoute() {
  return normalizeRouteString(route.query.company_name);
}

function currentSupplierNameFromRoute() {
  return normalizeRouteString(route.query.supplier_name);
}

function currentStockStatusFromRoute() {
  return normalizeStockStatus(normalizeRouteString(route.query.stock_status));
}

function currentTagsFromRoute() {
  return normalizeRouteStringList(route.query.tags);
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

function normalizeRouteStringList(value: unknown) {
  const rawValues = Array.isArray(value) ? value : [value];

  return Array.from(
    new Set(
      rawValues
        .flatMap((item) => (typeof item === "string" ? item.split(",") : []))
        .map((item) => normalizeTagName(item))
        .filter(Boolean),
    ),
  );
}

function normalizeTagName(value: string) {
  return String(value || "").trim();
}

function normalizeStockStatus(value: string): StockStatusFilter {
  const status = normalizeTagName(value);

  return isStockStatus(status) ? status : "";
}

function isStockStatus(value: string): value is StockStatus {
  return value === "available" || value === "low" || value === "out";
}

function normalizeOptionalText(value: string) {
  return normalizeTagName(value) || null;
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

function createLocalValidationError(message: string) {
  const error = new Error(message) as Error & { data: { detail: string } };

  error.data = { detail: message };
  return error;
}

function getProductUnit(product: ProductSummaryResponse) {
  return normalizeTagName(product.quantity_unit) || DEFAULT_QUANTITY_UNIT;
}

function getStatusConfig(status: StockStatus | undefined) {
  return STOCK_STATUS[status || "none"] || STOCK_STATUS.none;
}

function getStockStatusFilterLabel(status: StockStatusFilter) {
  return status ? getStatusConfig(status).label : "Все статусы";
}

function getSummaryStockMeta(product: ProductSummaryResponse) {
  if (product.low_stock_threshold === null || product.low_stock_threshold === undefined) {
    return "";
  }

  return `Порог: ${formatQuantity(product.low_stock_threshold, getProductUnit(product))}`;
}

function getSummaryPriceMeta(product: ProductSummaryResponse) {
  const parts: string[] = [];

  if (product.min_purchase_price !== null && product.min_purchase_price !== undefined) {
    parts.push(`Закупка: ${formatCurrency(product.min_purchase_price)}`);
  }

  if (product.margin_percent !== null && product.margin_percent !== undefined) {
    parts.push(`Маржа: ${formatCount(product.margin_percent)}%`);
  }

  return parts.length ? parts.join(" | ") : "Детали цены не заданы";
}

function getSupplierCountText(value: number) {
  const count = Number(value || 0);

  if (!Number.isFinite(count) || count <= 0) {
    return "Нет поставщиков";
  }

  return `Поставщиков: ${formatCount(count)}`;
}
</script>

<template>
  <section class="container-fluid p-4">
    <div class="products-toolbar d-flex align-items-end justify-content-between flex-wrap gap-3 mb-3">
      <form ref="searchForm" class="products-search" role="search" @submit.prevent="submitSearch">
        <label class="form-label" for="products-search-input">Поиск товара</label>
        <div class="input-group">
          <input
            id="products-search-input"
            v-model="searchDraft"
            class="form-control"
            name="search"
            type="search"
            minlength="2"
            maxlength="100"
            placeholder="Введите название товара или тег"
            autocomplete="off"
          >
          <button class="btn btn-primary" type="submit" :disabled="productsQuery.isFetching.value">
            Поиск
          </button>
        </div>

        <div class="products-filter-panel">
          <div class="products-filter-header">
            <span class="product-detail-label">Фильтры</span>
            <button
              v-if="hasActiveProductFilters"
              class="btn btn-link products-filter-reset"
              type="button"
              :disabled="productsQuery.isFetching.value"
              @click="resetProductFilters"
            >
              Сбросить
            </button>
          </div>

          <div class="products-filter-controls">
            <div class="product-filter-combobox">
              <label class="form-label" for="products-company-filter">Компания</label>
              <div class="input-group product-filter-input-group">
                <input
                  id="products-company-filter"
                  v-model="filterDraft.companyName"
                  class="form-control"
                  name="company_name"
                  type="search"
                  minlength="2"
                  maxlength="100"
                  autocomplete="off"
                  role="combobox"
                  aria-autocomplete="list"
                  :aria-expanded="shouldShowCompanyFilterMenu"
                  aria-controls="products-company-filter-options"
                  @focus="openCompanyFilterDropdown"
                  @blur="closeCompanyFilterDropdown"
                >
                <button
                  v-if="filterDraft.companyName"
                  class="btn btn-outline-secondary product-filter-clear"
                  type="button"
                  aria-label="Очистить фильтр компании"
                  @mousedown.prevent
                  @click="clearCompanyFilterDraft"
                >
                  <span aria-hidden="true">×</span>
                </button>
              </div>
              <div
                v-if="shouldShowCompanyFilterMenu"
                id="products-company-filter-options"
                class="product-filter-menu"
                role="listbox"
                aria-label="Компании"
              >
                <div v-if="!filterCompanyLookupTerm" class="product-filter-menu-state">
                  Поиск компаний...
                </div>
                <div
                  v-else-if="companyFilterQuery.isFetching.value"
                  class="product-filter-menu-state"
                >
                  Поиск компаний...
                </div>
                <div v-else-if="companyFilterError" class="product-filter-menu-state text-danger">
                  {{ companyFilterError }}
                </div>
                <div
                  v-else-if="companyFilterResults.length === 0"
                  class="product-filter-menu-state text-secondary"
                >
                  Компании не найдены.
                </div>
                <template v-else>
                  <button
                    v-for="company in companyFilterResults"
                    :key="company.id"
                    class="product-filter-option"
                    type="button"
                    role="option"
                    @mousedown.prevent
                    @click="selectCompanyFilter(company)"
                  >
                    <span class="product-filter-option-title">{{ company.name }}</span>
                    <span class="product-filter-option-meta">
                      ID {{ formatCount(company.id) }}
                      <span v-if="company.iin">| ИИН {{ company.iin }}</span>
                    </span>
                  </button>
                </template>
              </div>
            </div>
            <div class="product-filter-combobox">
              <label class="form-label" for="products-supplier-filter">Поставщик</label>
              <div class="input-group product-filter-input-group">
                <input
                  id="products-supplier-filter"
                  v-model="filterDraft.supplierName"
                  class="form-control"
                  name="supplier_name"
                  type="search"
                  minlength="2"
                  maxlength="100"
                  autocomplete="off"
                  role="combobox"
                  aria-autocomplete="list"
                  :aria-expanded="shouldShowSupplierFilterMenu"
                  aria-controls="products-supplier-filter-options"
                  @focus="openSupplierFilterDropdown"
                  @blur="closeSupplierFilterDropdown"
                >
                <button
                  v-if="filterDraft.supplierName"
                  class="btn btn-outline-secondary product-filter-clear"
                  type="button"
                  aria-label="Очистить фильтр поставщика"
                  @mousedown.prevent
                  @click="clearSupplierFilterDraft"
                >
                  <span aria-hidden="true">×</span>
                </button>
              </div>
              <div
                v-if="shouldShowSupplierFilterMenu"
                id="products-supplier-filter-options"
                class="product-filter-menu"
                role="listbox"
                aria-label="Поставщики"
              >
                <div v-if="!filterSupplierLookupTerm" class="product-filter-menu-state">
                  Поиск поставщиков...
                </div>
                <div
                  v-else-if="supplierFilterQuery.isFetching.value"
                  class="product-filter-menu-state"
                >
                  Поиск поставщиков...
                </div>
                <div v-else-if="supplierFilterError" class="product-filter-menu-state text-danger">
                  {{ supplierFilterError }}
                </div>
                <div
                  v-else-if="supplierFilterResults.length === 0"
                  class="product-filter-menu-state text-secondary"
                >
                  Поставщики не найдены.
                </div>
                <template v-else>
                  <button
                    v-for="supplier in supplierFilterResults"
                    :key="supplier.id"
                    class="product-filter-option"
                    type="button"
                    role="option"
                    @mousedown.prevent
                    @click="selectSupplierFilter(supplier)"
                  >
                    <span class="product-filter-option-title">{{ supplier.name }}</span>
                    <span class="product-filter-option-meta">
                      ID {{ formatCount(supplier.id) }}
                      <span v-if="supplier.phone_number">| {{ supplier.phone_number }}</span>
                      | Связей: {{ formatCount(supplier.product_links_count) }}
                    </span>
                  </button>
                </template>
              </div>
            </div>
            <div>
              <label class="form-label" for="products-stock-status-filter">Статус</label>
              <select
                id="products-stock-status-filter"
                v-model="filterDraft.stockStatus"
                class="form-select"
                name="stock_status"
              >
                <option
                  v-for="option in STOCK_STATUS_FILTER_OPTIONS"
                  :key="option.value || 'all'"
                  :value="option.value"
                >
                  {{ option.label }}
                </option>
              </select>
            </div>
          </div>

          <div v-if="activeProductFilterChips.length > 0" class="products-active-filters" aria-label="Активные фильтры">
            <button
              v-for="chip in activeProductFilterChips"
              :key="chip.id"
              class="btn btn-sm btn-light border product-filter-chip"
              type="button"
              :title="`Убрать фильтр ${chip.label}`"
              :disabled="productsQuery.isFetching.value"
              @click="removeActiveFilter(chip)"
            >
              <span>{{ chip.label }}</span>
              <span aria-hidden="true">×</span>
            </button>
          </div>
        </div>
      </form>
      <div class="products-actions">
        <button class="btn btn-success" type="button" @click="openCreateModal">
          Добавить товар
        </button>
        <span class="badge text-bg-secondary products-count">
          {{ formatCount(productsPage.total) }} товаров
        </span>
      </div>
    </div>

    <div v-if="shouldShowPopularTags" class="products-popular-tags" aria-live="polite">
      <div class="products-popular-tags-header">
        <span class="product-detail-label">Популярные теги</span>
        <span v-if="popularTagsQuery.isLoading.value" class="text-secondary small">
          Загрузка...
        </span>
        <span v-if="popularTagsError" class="text-danger small">
          {{ popularTagsError }}
        </span>
        <span v-if="shouldShowPopularTagsEmpty" class="text-secondary small">
          Теги не найдены.
        </span>
      </div>
      <div v-if="popularTags.length > 0 && !popularTagsError" class="products-popular-tags-list">
        <button
          v-for="tag in popularTags"
          :key="tag.id"
          class="btn btn-sm product-popular-tag"
          :class="isTagFilterActive(tag.name) ? 'btn-secondary' : 'btn-outline-secondary'"
          type="button"
          :title="`Фильтр по тегу ${tag.name}`"
          @click="toggleTagFilter(tag.name)"
        >
          <span>{{ tag.name }}</span>
          <span class="badge text-bg-light border">{{ formatCount(tag.usage_count) }}</span>
        </button>
      </div>
    </div>

    <div v-if="productsQuery.isLoading.value" class="text-secondary py-4" aria-live="polite">
      Загрузка товаров...
    </div>
    <div v-else-if="productsError" class="alert alert-danger" role="alert">
      {{ productsError }}
    </div>
    <div v-else-if="shouldShowProductsEmpty" class="alert alert-light border" role="status">
      {{ productsEmptyMessage }}
    </div>

    <div v-if="shouldShowProductsTable" class="table-responsive products-table">
      <table class="table table-hover align-middle mb-0">
        <thead>
          <tr>
            <th scope="col">Товар</th>
            <th scope="col">Статус</th>
            <th scope="col">Всего на складе</th>
            <th scope="col">Мин. цена</th>
            <th scope="col">Компания</th>
            <th scope="col">Теги</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="product in productsPage.items"
            :key="product.id"
            class="product-summary-row"
            tabindex="0"
            role="button"
            :aria-label="`Открыть товар ${product.name || `#${formatCount(product.id)}`}`"
            @click="openProductDetail(product)"
            @keydown.enter.prevent="openProductDetail(product)"
          >
            <td class="product-name-cell">
              <div class="fw-semibold">{{ product.name || "Без названия" }}</div>
              <div class="product-meta">
                ID {{ formatCount(product.id) }} | Создан: {{ formatDateTime(product.created_at) }}
              </div>
            </td>
            <td>
              <span class="badge status-badge" :class="getStatusConfig(product.stock_status).className">
                {{ getStatusConfig(product.stock_status).label }}
              </span>
            </td>
            <td>
              <div class="fw-semibold">
                {{ formatQuantity(product.total_quantity, getProductUnit(product)) }}
              </div>
              <div class="product-meta">{{ getSummaryStockMeta(product) }}</div>
            </td>
            <td v-if="product.min_sale_price === null || product.min_sale_price === undefined" class="text-secondary">
              Нет доступной цены
            </td>
            <td v-else>
              <div class="fw-semibold">{{ formatCurrency(product.min_sale_price) }}</div>
              <div class="product-meta">{{ getSummaryPriceMeta(product) }}</div>
            </td>
            <td>
              <div class="fw-semibold">{{ product.company_name || "Компания не указана" }}</div>
              <div class="product-meta">{{ getSupplierCountText(product.suppliers_count) }}</div>
            </td>
            <td v-if="!product.tags.length" class="text-secondary">Без тегов</td>
            <td v-else>
              <div class="product-tags">
                <span
                  v-for="tag in product.tags"
                  :key="tag"
                  class="badge rounded-pill text-bg-light border"
                >
                  {{ tag }}
                </span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <nav
      v-if="shouldShowProductsPagination"
      class="products-pagination mt-3"
      aria-label="Пагинация товаров"
    >
      <button
        class="btn btn-outline-primary"
        type="button"
        :disabled="!productsPage.has_previous || productsQuery.isFetching.value"
        @click="goToPage(productsPage.page - 1)"
      >
        Назад
      </button>
      <span class="products-page-summary">
        Страница {{ formatCount(productsPage.page) }} из {{ formatCount(totalProductPages) }}
      </span>
      <button
        class="btn btn-outline-primary"
        type="button"
        :disabled="!productsPage.has_next || productsQuery.isFetching.value"
        @click="goToPage(productsPage.page + 1)"
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
        aria-labelledby="product-create-modal-title"
        @click.self="closeCreateModal"
      >
        <div class="modal-dialog modal-lg modal-dialog-scrollable">
          <form ref="createFormElement" class="modal-content product-create-form" @submit.prevent="submitProductCreate">
            <div class="modal-header">
              <h2 id="product-create-modal-title" class="modal-title fs-5">Добавить товар</h2>
              <button
                class="btn-close"
                type="button"
                aria-label="Закрыть"
                :disabled="createProductMutation.isPending.value"
                @click="closeCreateModal"
              ></button>
            </div>

            <div class="modal-body">
              <div v-if="createError" class="alert alert-danger" role="alert">
                {{ createError }}
              </div>

              <section class="product-create-section">
                <h3 class="product-create-section-title">Товар</h3>
                <div class="row g-3">
                  <div class="col-12 col-md-6">
                    <label class="form-label" for="product-create-name">Название</label>
                    <input
                      id="product-create-name"
                      v-model="productCreateForm.name"
                      class="form-control"
                      name="name"
                      type="text"
                      maxlength="255"
                      required
                      :disabled="createProductMutation.isPending.value"
                    >
                  </div>
                  <div class="col-12 col-md-3">
                    <label class="form-label" for="product-create-unit">Единица</label>
                    <input
                      id="product-create-unit"
                      v-model="productCreateForm.quantityUnit"
                      class="form-control"
                      name="quantity_unit"
                      type="text"
                      maxlength="20"
                      required
                      :disabled="createProductMutation.isPending.value"
                    >
                  </div>
                  <div class="col-12 col-md-3">
                    <label class="form-label" for="product-create-threshold">Порог</label>
                    <input
                      id="product-create-threshold"
                      v-model.number="productCreateForm.lowStockThreshold"
                      class="form-control"
                      name="low_stock_threshold"
                      type="number"
                      min="0"
                      step="1"
                      required
                      :disabled="createProductMutation.isPending.value"
                    >
                  </div>
                  <div class="col-12">
                    <label class="form-label" for="product-create-tags">Теги</label>
                    <input
                      id="product-create-tags"
                      v-model="productCreateForm.tags"
                      class="form-control"
                      name="tags"
                      type="text"
                      placeholder="Например: кофе, расходники, склад"
                      :disabled="createProductMutation.isPending.value"
                    >
                  </div>
                </div>
              </section>

              <section class="product-create-section">
                <div class="product-create-section-header">
                  <h3 class="product-create-section-title">Компания</h3>
                  <div class="product-create-mode" role="radiogroup" aria-label="Способ выбора компании">
                    <div class="form-check form-check-inline">
                      <input
                        id="product-create-company-existing"
                        v-model="productCreateForm.companyMode"
                        class="form-check-input"
                        type="radio"
                        name="product_company_mode"
                        value="existing"
                        :disabled="createProductMutation.isPending.value"
                      >
                      <label class="form-check-label" for="product-create-company-existing">
                        Существующая
                      </label>
                    </div>
                    <div class="form-check form-check-inline">
                      <input
                        id="product-create-company-new"
                        v-model="productCreateForm.companyMode"
                        class="form-check-input"
                        type="radio"
                        name="product_company_mode"
                        value="new"
                        :disabled="createProductMutation.isPending.value"
                      >
                      <label class="form-check-label" for="product-create-company-new">
                        Новая
                      </label>
                    </div>
                  </div>
                </div>

                <div v-if="productCreateForm.companyMode === 'existing'">
                  <div
                    v-if="productCreateForm.selectedCompany"
                    class="product-company-selected mb-3"
                  >
                    <div>
                      <div class="fw-semibold">{{ productCreateForm.selectedCompany.name }}</div>
                      <div class="product-meta">
                        ID {{ formatCount(productCreateForm.selectedCompany.id) }}
                        <span v-if="productCreateForm.selectedCompany.iin">
                          | ИИН {{ productCreateForm.selectedCompany.iin }}
                        </span>
                      </div>
                    </div>
                    <button
                      class="btn btn-sm btn-outline-secondary"
                      type="button"
                      :disabled="createProductMutation.isPending.value"
                      @click="clearSelectedCompany"
                    >
                      Сменить
                    </button>
                  </div>

                  <div v-else>
                    <label class="form-label" for="product-create-company-search">
                      Поиск компании
                    </label>
                    <div class="input-group">
                      <input
                        id="product-create-company-search"
                        v-model="productCreateForm.companySearch"
                        class="form-control"
                        name="company_search"
                        type="search"
                        minlength="2"
                        maxlength="100"
                        autocomplete="off"
                        :disabled="createProductMutation.isPending.value"
                        @keydown.enter.prevent="runCompanyLookup"
                      >
                      <button
                        class="btn btn-outline-primary"
                        type="button"
                        :disabled="createProductMutation.isPending.value || productCreateForm.companySearch.trim().length < 2"
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
                        :disabled="createProductMutation.isPending.value"
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

                <div v-else class="row g-3">
                  <div class="col-12 col-md-8">
                    <label class="form-label" for="product-create-new-company-name">
                      Название компании
                    </label>
                    <input
                      id="product-create-new-company-name"
                      v-model="productCreateForm.newCompanyName"
                      class="form-control"
                      name="new_company_name"
                      type="text"
                      maxlength="255"
                      required
                      :disabled="createProductMutation.isPending.value"
                    >
                  </div>
                  <div class="col-12 col-md-4">
                    <label class="form-label" for="product-create-new-company-iin">
                      ИИН
                    </label>
                    <input
                      id="product-create-new-company-iin"
                      v-model="productCreateForm.newCompanyIin"
                      class="form-control"
                      name="new_company_iin"
                      type="text"
                      pattern="[0-9]{12}"
                      maxlength="12"
                      inputmode="numeric"
                      :disabled="createProductMutation.isPending.value"
                    >
                  </div>
                </div>
              </section>

              <section class="product-create-section">
                <div class="form-check form-switch product-create-link-toggle">
                  <input
                    id="product-create-link-enabled"
                    v-model="productCreateForm.linkEnabled"
                    class="form-check-input"
                    type="checkbox"
                    role="switch"
                    :disabled="createProductMutation.isPending.value"
                  >
                  <label class="form-check-label fw-semibold" for="product-create-link-enabled">
                    Добавить поставщика сразу
                  </label>
                </div>

                <div v-if="productCreateForm.linkEnabled" class="product-create-supplier-section">
                  <div class="product-create-section-header">
                    <h3 class="product-create-section-title">Поставщик</h3>
                    <div class="product-create-mode" role="radiogroup" aria-label="Способ выбора поставщика">
                      <div class="form-check form-check-inline">
                        <input
                          id="product-create-supplier-existing"
                          v-model="productCreateForm.supplierMode"
                          class="form-check-input"
                          type="radio"
                          name="product_supplier_mode"
                          value="existing"
                          :disabled="createProductMutation.isPending.value"
                        >
                        <label class="form-check-label" for="product-create-supplier-existing">
                          Существующий
                        </label>
                      </div>
                      <div class="form-check form-check-inline">
                        <input
                          id="product-create-supplier-new"
                          v-model="productCreateForm.supplierMode"
                          class="form-check-input"
                          type="radio"
                          name="product_supplier_mode"
                          value="new"
                          :disabled="createProductMutation.isPending.value"
                        >
                        <label class="form-check-label" for="product-create-supplier-new">
                          Новый
                        </label>
                      </div>
                    </div>
                  </div>

                  <div v-if="productCreateForm.supplierMode === 'existing'">
                    <div
                      v-if="productCreateForm.selectedSupplier"
                      class="product-supplier-selected mb-3"
                    >
                      <div>
                        <div class="fw-semibold">{{ productCreateForm.selectedSupplier.name }}</div>
                        <div class="supplier-meta">
                          ID {{ formatCount(productCreateForm.selectedSupplier.id) }}
                          <span v-if="productCreateForm.selectedSupplier.phone_number">
                            | {{ productCreateForm.selectedSupplier.phone_number }}
                          </span>
                        </div>
                      </div>
                      <button
                        class="btn btn-sm btn-outline-secondary"
                        type="button"
                        :disabled="createProductMutation.isPending.value"
                        @click="clearSelectedSupplier"
                      >
                        Сменить
                      </button>
                    </div>

                    <div v-else>
                      <label class="form-label" for="product-create-supplier-search">
                        Поиск поставщика
                      </label>
                      <div class="input-group">
                        <input
                          id="product-create-supplier-search"
                          v-model="productCreateForm.supplierSearch"
                          class="form-control"
                          name="supplier_search"
                          type="search"
                          minlength="2"
                          maxlength="100"
                          autocomplete="off"
                          :disabled="createProductMutation.isPending.value"
                          @keydown.enter.prevent="runSupplierLookup"
                        >
                        <button
                          class="btn btn-outline-primary"
                          type="button"
                          :disabled="createProductMutation.isPending.value || productCreateForm.supplierSearch.trim().length < 2"
                          @click="runSupplierLookup"
                        >
                          Найти
                        </button>
                      </div>

                      <div v-if="supplierLookupQuery.isLoading.value" class="text-secondary small mt-2">
                        Поиск поставщиков...
                      </div>
                      <div v-else-if="supplierLookupError" class="text-danger small mt-2">
                        {{ supplierLookupError }}
                      </div>
                      <div
                        v-else-if="supplierLookupTerm && supplierLookupResults.length === 0"
                        class="text-secondary small mt-2"
                      >
                        Поставщики не найдены.
                      </div>

                      <div v-if="supplierLookupResults.length > 0" class="list-group product-supplier-results mt-2">
                        <button
                          v-for="supplier in supplierLookupResults"
                          :key="supplier.id"
                          class="list-group-item list-group-item-action product-supplier-result"
                          type="button"
                          :disabled="createProductMutation.isPending.value"
                          @click="selectSupplier(supplier)"
                        >
                          <span class="fw-semibold d-block">{{ supplier.name }}</span>
                          <span class="supplier-meta d-block">
                            ID {{ formatCount(supplier.id) }}
                            <span v-if="supplier.phone_number">| {{ supplier.phone_number }}</span>
                          </span>
                        </button>
                      </div>
                    </div>
                  </div>

                  <div v-else class="row g-3">
                    <div class="col-12 col-lg-7">
                      <label class="form-label" for="product-create-new-supplier-name">
                        Название поставщика
                      </label>
                      <input
                        id="product-create-new-supplier-name"
                        v-model="productCreateForm.newSupplierName"
                        class="form-control"
                        name="new_supplier_name"
                        type="text"
                        maxlength="255"
                        autocomplete="organization"
                        required
                        :disabled="createProductMutation.isPending.value"
                      >
                    </div>
                    <div class="col-12 col-lg-5">
                      <label class="form-label" for="product-create-new-supplier-phone-number">
                        Телефон
                      </label>
                      <input
                        id="product-create-new-supplier-phone-number"
                        v-model="productCreateForm.newSupplierPhoneNumber"
                        class="form-control"
                        name="new_supplier_phone_number"
                        type="tel"
                        inputmode="tel"
                        pattern="(8[0-9]{10}|[+]7[0-9]{10})"
                        maxlength="12"
                        autocomplete="tel"
                        placeholder="+77001234567"
                        required
                        :disabled="createProductMutation.isPending.value"
                      >
                      <div class="form-text">Формат: +7XXXXXXXXXX или 8XXXXXXXXXX.</div>
                    </div>
                  </div>

                  <div class="row g-3 mt-1">
                    <div class="col-12 col-md-6 col-xl-4">
                      <label class="form-label" for="product-create-purchase-price">
                        Цена закупки
                      </label>
                      <input
                        id="product-create-purchase-price"
                        v-model.number="productCreateForm.purchasePrice"
                        class="form-control"
                        name="purchase_price"
                        type="number"
                        min="1"
                        step="1"
                        required
                        :disabled="createProductMutation.isPending.value"
                      >
                    </div>
                    <div class="col-12 col-md-6 col-xl-4">
                      <label class="form-label" for="product-create-margin-percent">
                        Маржа, %
                      </label>
                      <input
                        id="product-create-margin-percent"
                        v-model.number="productCreateForm.marginPercent"
                        class="form-control"
                        name="margin_percent"
                        type="number"
                        min="0"
                        step="1"
                        required
                        :disabled="createProductMutation.isPending.value"
                      >
                    </div>
                    <div class="col-12 col-md-6 col-xl-4">
                      <label class="form-label" for="product-create-sale-price">
                        Цена продажи
                      </label>
                      <input
                        id="product-create-sale-price"
                        v-model="productCreateForm.salePrice"
                        class="form-control"
                        name="sale_price"
                        type="number"
                        min="1"
                        step="1"
                        placeholder="Авто"
                        :disabled="createProductMutation.isPending.value"
                      >
                    </div>
                    <div class="col-12 col-md-6 col-xl-4">
                      <label class="form-label" for="product-create-quantity">
                        Количество
                      </label>
                      <input
                        id="product-create-quantity"
                        v-model.number="productCreateForm.quantity"
                        class="form-control"
                        name="quantity"
                        type="number"
                        min="0"
                        step="1"
                        required
                        :disabled="createProductMutation.isPending.value"
                      >
                    </div>
                  </div>
                </div>
              </section>
            </div>

            <div class="modal-footer product-create-footer">
              <button
                class="btn btn-outline-secondary"
                type="button"
                :disabled="createProductMutation.isPending.value"
                @click="closeCreateModal"
              >
                Отмена
              </button>
              <button class="btn btn-success" type="submit" :disabled="createProductMutation.isPending.value">
                {{ createProductMutation.isPending.value ? "Сохранение..." : "Создать" }}
              </button>
            </div>
          </form>
        </div>
      </div>
      <div v-if="isCreateModalOpen" class="modal-backdrop fade show"></div>
    </Teleport>

    <ProductDetailModal
      :product-id="selectedProductId"
      :is-open="isDetailModalOpen"
      :summary="selectedProductSummary"
      @close="closeProductDetail"
    />
  </section>
</template>
