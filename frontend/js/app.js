import { request } from "./utils.js";
import {
  elements,
  state,
  setActiveView,
  setAppMessage,
  clearProductCompanyLookup,
  clearProductSupplierLookup,
  resetCompanyCreateForm,
  resetProductCreateForm,
  setCompanyCreateError,
  setCompanyCreateSubmitting,
  setCompaniesError,
  setCompaniesLoading,
  setCompaniesPagination,
  setCompaniesSearchTerm,
  setProductCompanyLookupError,
  setProductCompanyLookupLoading,
  setProductCompanyLookupResults,
  setProductCreateError,
  setProductCreateSubmitting,
  setProductSalePriceEdited,
  setProductSelectedCompany,
  setProductSelectedSupplier,
  setProductSupplierLookupError,
  setProductSupplierLookupLoading,
  setProductSupplierLookupResults,
  setProductsError,
  setProductsLoading,
  setProductsPagination,
  setProductsSearchTerm,
  setState,
  setSuppliersError,
  setSuppliersLoading,
  setSuppliersPagination,
  setSuppliersSearchTerm,
  updateProductSalePrice,
} from "./states.js";

const FIRST_LIST_PAGE = 1;
const COMPANY_LOOKUP_PAGE_SIZE = 5;
const SUPPLIER_LOOKUP_PAGE_SIZE = 5;

initializeApp();

function initializeApp() {
  bindNavigation();
  bindProductSearch();
  bindProductPagination();
  bindProductPricingCalculation();
  bindProductCompanyLookup();
  bindProductSupplierLookup();
  bindProductCreate();
  bindCompanySearch();
  bindCompanyPagination();
  bindCompanyCreate();
  bindSupplierSearch();
  bindSupplierPagination();
  setActiveView("dashboard");
  loadInitialData();
}

function bindNavigation() {
  for (const tab of elements.navTabs) {
    tab.addEventListener("click", () => {
      setActiveView(tab.dataset.viewTab);
    });
  }
}

function bindProductSearch() {
  elements.products.searchForm.addEventListener("submit", (event) => {
    event.preventDefault();

    if (elements.products.searchButton.disabled) {
      return;
    }

    const searchTerm = elements.products.searchInput.value.trim();
    loadProducts(searchTerm, FIRST_LIST_PAGE);
  });
}

function bindProductPagination() {
  elements.products.previousPageButton.addEventListener("click", () => {
    if (elements.products.previousPageButton.disabled) {
      return;
    }

    loadProducts(state.products.searchTerm, state.products.page - 1);
  });

  elements.products.nextPageButton.addEventListener("click", () => {
    if (elements.products.nextPageButton.disabled) {
      return;
    }

    loadProducts(state.products.searchTerm, state.products.page + 1);
  });
}

function bindProductPricingCalculation() {
  elements.products.purchasePriceInput.addEventListener("input", updateProductSalePrice);
  elements.products.marginPercentInput.addEventListener("input", updateProductSalePrice);
  elements.products.salePriceInput.addEventListener("input", () => {
    setProductSalePriceEdited(true);
  });
  updateProductSalePrice();
}

function bindProductCreate() {
  elements.products.createForm.addEventListener("submit", (event) => {
    event.preventDefault();

    if (
      elements.products.createSubmitButton.disabled ||
      !elements.products.createForm.reportValidity()
    ) {
      return;
    }

    if (hasUnselectedProductCompanyInput()) {
      setProductCreateError("Выберите компанию из результатов поиска или очистите поле компании.");
      elements.products.companySearchInput.focus();
      return;
    }

    if (hasUnselectedProductSupplierInput()) {
      setProductCreateError("Выберите поставщика из результатов поиска или очистите поле поставщика.");
      elements.products.supplierSearchInput.focus();
      return;
    }

    createProduct();
  });

  elements.products.createModal.addEventListener("hidden.bs.modal", () => {
    if (!state.products.isCreating) {
      resetProductCreateForm();
    }
  });
}

function bindProductCompanyLookup() {
  elements.products.companySearchButton.addEventListener("click", () => {
    if (elements.products.companySearchButton.disabled) {
      return;
    }

    searchProductCreateCompanies();
  });

  elements.products.companySearchInput.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") {
      return;
    }

    event.preventDefault();

    if (!elements.products.companySearchButton.disabled) {
      searchProductCreateCompanies();
    }
  });

  elements.products.companySearchInput.addEventListener("input", () => {
    const lookup = state.products.companyLookup;

    if (
      lookup.selectedCompany ||
      lookup.results.length > 0 ||
      lookup.error ||
      lookup.hasSearched
    ) {
      clearProductCompanyLookup(false);
    }
  });

  elements.products.companyClearButton.addEventListener("click", () => {
    clearProductCompanyLookup();
    elements.products.companySearchInput.focus();
  });

  elements.products.companyResults.addEventListener("click", (event) => {
    if (!(event.target instanceof Element)) {
      return;
    }

    const resultButton = event.target.closest("[data-company-id]");

    if (!resultButton || !elements.products.companyResults.contains(resultButton)) {
      return;
    }

    const selectedCompany = state.products.companyLookup.results.find(
      (company) => String(company.id) === resultButton.dataset.companyId,
    );

    if (!selectedCompany) {
      return;
    }

    setProductSelectedCompany(selectedCompany);
    setProductCreateError("");
  });
}

function bindProductSupplierLookup() {
  elements.products.supplierSearchButton.addEventListener("click", () => {
    if (elements.products.supplierSearchButton.disabled) {
      return;
    }

    searchProductCreateSuppliers();
  });

  elements.products.supplierSearchInput.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") {
      return;
    }

    event.preventDefault();

    if (!elements.products.supplierSearchButton.disabled) {
      searchProductCreateSuppliers();
    }
  });

  elements.products.supplierSearchInput.addEventListener("input", () => {
    const lookup = state.products.supplierLookup;

    if (
      lookup.selectedSupplier ||
      lookup.results.length > 0 ||
      lookup.error ||
      lookup.hasSearched
    ) {
      clearProductSupplierLookup(false);
    }
  });

  elements.products.supplierClearButton.addEventListener("click", () => {
    clearProductSupplierLookup();
    elements.products.supplierSearchInput.focus();
  });

  elements.products.supplierResults.addEventListener("click", (event) => {
    if (!(event.target instanceof Element)) {
      return;
    }

    const resultButton = event.target.closest("[data-supplier-id]");

    if (!resultButton || !elements.products.supplierResults.contains(resultButton)) {
      return;
    }

    const selectedSupplier = state.products.supplierLookup.results.find(
      (supplier) => String(supplier.id) === resultButton.dataset.supplierId,
    );

    if (!selectedSupplier) {
      return;
    }

    setProductSelectedSupplier(selectedSupplier);
    setProductCreateError("");
  });
}

function bindCompanySearch() {
  elements.companies.searchForm.addEventListener("submit", (event) => {
    event.preventDefault();

    if (elements.companies.searchButton.disabled) {
      return;
    }

    const searchTerm = elements.companies.searchInput.value.trim();
    loadCompanies(searchTerm, FIRST_LIST_PAGE);
  });
}

function bindCompanyPagination() {
  elements.companies.previousPageButton.addEventListener("click", () => {
    if (elements.companies.previousPageButton.disabled) {
      return;
    }

    loadCompanies(state.companies.searchTerm, state.companies.page - 1);
  });

  elements.companies.nextPageButton.addEventListener("click", () => {
    if (elements.companies.nextPageButton.disabled) {
      return;
    }

    loadCompanies(state.companies.searchTerm, state.companies.page + 1);
  });
}

function bindCompanyCreate() {
  elements.companies.createForm.addEventListener("submit", (event) => {
    event.preventDefault();

    if (
      elements.companies.createSubmitButton.disabled ||
      !elements.companies.createForm.reportValidity()
    ) {
      return;
    }

    createCompany();
  });

  elements.companies.createModal.addEventListener("hidden.bs.modal", () => {
    if (!state.companies.isCreating) {
      resetCompanyCreateForm();
    }
  });
}

function bindSupplierSearch() {
  elements.suppliers.searchForm.addEventListener("submit", (event) => {
    event.preventDefault();

    if (elements.suppliers.searchButton.disabled) {
      return;
    }

    const searchTerm = elements.suppliers.searchInput.value.trim();
    loadSuppliers(searchTerm, FIRST_LIST_PAGE);
  });
}

function bindSupplierPagination() {
  elements.suppliers.previousPageButton.addEventListener("click", () => {
    if (elements.suppliers.previousPageButton.disabled) {
      return;
    }

    loadSuppliers(state.suppliers.searchTerm, state.suppliers.page - 1);
  });

  elements.suppliers.nextPageButton.addEventListener("click", () => {
    if (elements.suppliers.nextPageButton.disabled) {
      return;
    }

    loadSuppliers(state.suppliers.searchTerm, state.suppliers.page + 1);
  });
}

async function loadInitialData() {
  await Promise.all([
    loadDashboardSummary(),
    loadProducts(),
    loadCompanies(),
    loadSuppliers(),
  ]);
}

async function loadDashboardSummary() {
  setAppMessage("");

  try {
    const summary = await request("/summaries");

    setState("sales.value", summary.dashboard_sales_value);
    setState("sales.count", summary.dashboard_sales_count);
    setState("products.lowStock", summary.low_stock);
    setState("products.outOfStock", summary.out_of_stock);
  } catch (error) {
    console.error("Could not load dashboard summaries:", error);
    setAppMessage(getRequestErrorMessage(error, "показатели дэшборда"));
  }
}

async function loadProducts(searchTerm = "", page = FIRST_LIST_PAGE) {
  setProductsLoading(true);
  setProductsSearchTerm(searchTerm);
  setProductsError("");

  try {
    const productsResponse = await request(getProductsPath(searchTerm, page));
    const productsPage = getProductsPage(productsResponse);

    setProductsPagination(productsPage.pagination);
    setState("products.list", productsPage.items);
  } catch (error) {
    console.error("Could not load products:", error);
    setProductsPagination({
      page,
      pageSize: state.products.pageSize,
      total: 0,
      totalPages: 0,
      hasNext: false,
      hasPrevious: false,
    });
    setState("products.list", []);
    setProductsError(getRequestErrorMessage(error, "товары"));
  } finally {
    setProductsLoading(false);
  }
}

async function loadCompanies(searchTerm = "", page = FIRST_LIST_PAGE) {
  setCompaniesLoading(true);
  setCompaniesSearchTerm(searchTerm);
  setCompaniesError("");

  try {
    const companiesResponse = await request(getListPath("/companies", searchTerm, page));
    const companiesPage = getPaginatedPage(companiesResponse);

    setCompaniesPagination(companiesPage.pagination);
    setState("companies.list", companiesPage.items);
  } catch (error) {
    console.error("Could not load companies:", error);
    setCompaniesPagination({
      page,
      pageSize: state.companies.pageSize,
      total: 0,
      totalPages: 0,
      hasNext: false,
      hasPrevious: false,
    });
    setState("companies.list", []);
    setCompaniesError(getRequestErrorMessage(error, "компании"));
  } finally {
    setCompaniesLoading(false);
  }
}

async function loadSuppliers(searchTerm = "", page = FIRST_LIST_PAGE) {
  setSuppliersLoading(true);
  setSuppliersSearchTerm(searchTerm);
  setSuppliersError("");

  try {
    const suppliersResponse = await request(getListPath("/suppliers", searchTerm, page));
    const suppliersPage = getPaginatedPage(suppliersResponse);

    setSuppliersPagination(suppliersPage.pagination);
    setState("suppliers.list", suppliersPage.items);
  } catch (error) {
    console.error("Could not load suppliers:", error);
    setSuppliersPagination({
      page,
      pageSize: state.suppliers.pageSize,
      total: 0,
      totalPages: 0,
      hasNext: false,
      hasPrevious: false,
    });
    setState("suppliers.list", []);
    setSuppliersError(getRequestErrorMessage(error, "поставщиков"));
  } finally {
    setSuppliersLoading(false);
  }
}

async function createProduct() {
  setProductCreateSubmitting(true);
  setProductCreateError("");

  try {
    await request("/products", {
      method: "POST",
      body: JSON.stringify(getProductCreatePayload()),
    });

    hideProductCreateModal();
    resetProductCreateForm();

    await Promise.all([
      loadDashboardSummary(),
      loadProducts(state.products.searchTerm, state.products.page),
    ]);
  } catch (error) {
    console.error("Could not create product:", error);
    setProductCreateError(getCreateProductErrorMessage(error));
  } finally {
    setProductCreateSubmitting(false);
  }
}

async function searchProductCreateCompanies() {
  const searchTerm = elements.products.companySearchInput.value.trim();

  if (!searchTerm) {
    clearProductCompanyLookup(false);
    setProductCompanyLookupError("Введите название компании для поиска.");
    elements.products.companySearchInput.focus();
    return;
  }

  setProductCompanyLookupLoading(true);
  setProductCompanyLookupError("");

  try {
    const companiesResponse = await request(getCompanyLookupPath(searchTerm));
    const companiesPage = getPaginatedPage(companiesResponse);

    setProductCompanyLookupResults(companiesPage.items);
  } catch (error) {
    console.error("Could not search companies for product create:", error);
    setProductCompanyLookupError(getRequestErrorMessage(error, "компании"));
  } finally {
    setProductCompanyLookupLoading(false);
  }
}

async function searchProductCreateSuppliers() {
  const searchTerm = elements.products.supplierSearchInput.value.trim();

  if (!searchTerm) {
    clearProductSupplierLookup(false);
    setProductSupplierLookupError("Введите название поставщика для поиска.");
    elements.products.supplierSearchInput.focus();
    return;
  }

  setProductSupplierLookupLoading(true);
  setProductSupplierLookupError("");

  try {
    const suppliersResponse = await request(getSupplierLookupPath(searchTerm));
    const suppliersPage = getPaginatedPage(suppliersResponse);

    setProductSupplierLookupResults(suppliersPage.items);
  } catch (error) {
    console.error("Could not search suppliers for product create:", error);
    setProductSupplierLookupError(getRequestErrorMessage(error, "поставщиков"));
  } finally {
    setProductSupplierLookupLoading(false);
  }
}

async function createCompany() {
  setCompanyCreateSubmitting(true);
  setCompanyCreateError("");

  try {
    await request("/companies", {
      method: "POST",
      body: JSON.stringify(getCompanyCreatePayload()),
    });

    hideCompanyCreateModal();
    resetCompanyCreateForm();

    await loadCompanies(state.companies.searchTerm, state.companies.page);
  } catch (error) {
    console.error("Could not create company:", error);
    setCompanyCreateError(getCreateCompanyErrorMessage(error));
  } finally {
    setCompanyCreateSubmitting(false);
  }
}

function getProductsPath(searchTerm, page) {
  return getListPath("/products", searchTerm, page);
}

function getListPath(basePath, searchTerm, page) {
  const params = new URLSearchParams();

  if (searchTerm) {
    params.set("search", searchTerm);
  }

  params.set("page", String(Math.max(page, FIRST_LIST_PAGE)));

  const queryString = params.toString();
  return queryString ? `${basePath}?${queryString}` : basePath;
}

function getProductsPage(productsResponse) {
  return getPaginatedPage(productsResponse);
}

function getPaginatedPage(response) {
  if (Array.isArray(response)) {
    return {
      items: response,
      pagination: {
        page: FIRST_LIST_PAGE,
        pageSize: response.length,
        total: response.length,
        totalPages: response.length > 0 ? 1 : 0,
        hasNext: false,
        hasPrevious: false,
      },
    };
  }

  return {
    items: Array.isArray(response?.items) ? response.items : [],
    pagination: {
      page: Number(response?.page || FIRST_LIST_PAGE),
      pageSize: Number(response?.page_size || 20),
      total: Number(response?.total || 0),
      totalPages: Number(response?.total_pages || 0),
      hasNext: Boolean(response?.has_next),
      hasPrevious: Boolean(response?.has_previous),
    },
  };
}

function getProductCreatePayload() {
  const formData = new FormData(elements.products.createForm);

  return {
    name: getTextField(formData, "name"),
    purchase_price: getNumberField(formData, "purchase_price"),
    margin_percent: getNumberField(formData, "margin_percent"),
    sale_price: getOptionalNumberField(formData, "sale_price"),
    quantity: getNumberField(formData, "quantity"),
    quantity_unit: getTextField(formData, "quantity_unit") || "шт",
    low_stock_threshold: getNumberField(formData, "low_stock_threshold"),
    company_id: getOptionalNumberField(formData, "company_id"),
    supplier_id: getOptionalNumberField(formData, "supplier_id"),
    tags: getTagsField(formData),
  };
}

function getCompanyCreatePayload() {
  const formData = new FormData(elements.companies.createForm);

  return {
    name: getTextField(formData, "name"),
    iin: getTextField(formData, "iin"),
  };
}

function getCompanyLookupPath(searchTerm) {
  const params = new URLSearchParams();
  params.set("search", searchTerm);
  params.set("page", String(FIRST_LIST_PAGE));
  params.set("page_size", String(COMPANY_LOOKUP_PAGE_SIZE));

  return `/companies?${params.toString()}`;
}

function getSupplierLookupPath(searchTerm) {
  const params = new URLSearchParams();
  params.set("search", searchTerm);
  params.set("page", String(FIRST_LIST_PAGE));
  params.set("page_size", String(SUPPLIER_LOOKUP_PAGE_SIZE));

  return `/suppliers?${params.toString()}`;
}

function getTextField(formData, key) {
  return String(formData.get(key) || "").trim();
}

function getNumberField(formData, key) {
  return Number(getTextField(formData, key));
}

function getOptionalNumberField(formData, key) {
  const value = getTextField(formData, key);
  return value ? Number(value) : null;
}

function getTagsField(formData) {
  const tags = getTextField(formData, "tags");

  if (!tags) {
    return [];
  }

  return tags
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function hasUnselectedProductCompanyInput() {
  return Boolean(elements.products.companySearchInput.value.trim()) &&
    !elements.products.companyIdInput.value;
}

function hasUnselectedProductSupplierInput() {
  return Boolean(elements.products.supplierSearchInput.value.trim()) &&
    !elements.products.supplierIdInput.value;
}

function hideProductCreateModal() {
  hideModal(elements.products.createModal);
}

function hideCompanyCreateModal() {
  hideModal(elements.companies.createModal);
}

function hideModal(modalElement) {
  const Modal = window.bootstrap?.Modal;

  if (!Modal) {
    return;
  }

  Modal.getOrCreateInstance(modalElement).hide();
}

function getCreateProductErrorMessage(error) {
  return getCreateErrorMessage(error, "товар");
}

function getCreateCompanyErrorMessage(error) {
  return getCreateErrorMessage(error, "компанию");
}

function getCreateErrorMessage(error, label) {
  const detail = error?.data?.detail;

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const field = Array.isArray(item.loc) ? item.loc.slice(1).join(".") : "";
        return field ? `${field}: ${item.msg}` : item.msg;
      })
      .filter(Boolean)
      .join(" ");
  }

  if (typeof detail === "string") {
    return detail;
  }

  if (error?.status) {
    return `Не удалось создать ${label}. API вернул статус ${error.status}.`;
  }

  return `Не удалось создать ${label}. Проверьте, что API запущен.`;
}

function getRequestErrorMessage(error, label) {
  if (error?.status) {
    return `Не удалось загрузить ${label}. API вернул статус ${error.status}.`;
  }

  return `Не удалось загрузить ${label}. Проверьте, что API запущен.`;
}
