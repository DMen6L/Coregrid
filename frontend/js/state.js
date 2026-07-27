export const state = {
  activeView: "dashboard",
  dashboard: createDashboardState(),
  products: createListState(),
  companies: createListState(),
  suppliers: createListState(),
  restocks: createDatedListState(),
  sales: createDatedListState(),
  productCreate: {
    isSubmitting: false,
    selectedCompany: null,
    selectedSupplier: null,
    companyLookup: createLookupState(),
    supplierLookup: createLookupState(),
    companyMode: "existing",
    supplierMode: "existing",
    linkEnabled: false,
  },
  productDetail: createProductDetailState(),
  companyCreate: {
    isSubmitting: false,
  },
  supplierCreate: {
    isSubmitting: false,
  },
  restockCreate: {
    isSubmitting: false,
  },
  restockDetail: createDetailState(),
  saleCreate: {
    isSubmitting: false,
  },
  saleDetail: createDetailState(),
};

export function createDashboardState() {
  return {
    data: null,
    days: 7,
    bestSalesMode: "quantity",
    isLoading: true,
    error: "",
  };
}

export function createListState() {
  return {
    items: [],
    searchTerm: "",
    isLoading: true,
    error: "",
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
  };
}

export function createLookupState() {
  return {
    isLoading: false,
    error: "",
    hasSearched: false,
    results: [],
  };
}

export function createDatedListState() {
  return {
    ...createListState(),
    dateFrom: "",
    dateTo: "",
  };
}

export function createDetailState() {
  return {
    data: null,
    id: null,
    isLoading: false,
    error: "",
  };
}

export function createProductDetailState() {
  return {
    ...createDetailState(),
    summary: null,
    isEditing: false,
    isSubmitting: false,
    editError: "",
  };
}

export function applyPage(target, response, fallbackPage = 1) {
  const page = normalizePage(response, fallbackPage);

  target.items = page.items;
  target.page = page.page;
  target.pageSize = page.pageSize;
  target.total = page.total;
  target.totalPages = page.totalPages;
  target.hasNext = page.hasNext;
  target.hasPrevious = page.hasPrevious;
}

export function resetPage(target, page = 1) {
  target.items = [];
  target.page = page;
  target.total = 0;
  target.totalPages = 0;
  target.hasNext = false;
  target.hasPrevious = false;
}

export function normalizePage(response, fallbackPage = 1) {
  return {
    items: Array.isArray(response?.items) ? response.items : [],
    page: Number(response?.page || fallbackPage),
    pageSize: Number(response?.page_size || 20),
    total: Number(response?.total || 0),
    totalPages: Number(response?.total_pages || 0),
    hasNext: Boolean(response?.has_next),
    hasPrevious: Boolean(response?.has_previous),
  };
}
