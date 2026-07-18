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
  resetSupplierCreateForm,
  setSupplierCreateError,
  setSupplierCreateSubmitting,
  setSuppliersError,
  setSuppliersLoading,
  setSuppliersPagination,
  setSuppliersSearchTerm,
  updateProductSalePrice,
} from "./states.js";

const FIRST_LIST_PAGE = 1;
const PRODUCT_LOOKUP_MIN_SEARCH_LENGTH = 2;
const PRODUCT_LOOKUP_DEBOUNCE_MS = 300;
const PRODUCT_LOOKUP_PAGE_SIZE = 10;

const productLookupRequests = {
  company: {
    debounceId: null,
    controller: null,
  },
  supplier: {
    debounceId: null,
    controller: null,
  },
};

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
  bindSupplierCreate();
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
      cancelProductCompanyLookupRequest();
      cancelProductSupplierLookupRequest();
      resetProductCreateForm();
    }
  });
}

function bindProductCompanyLookup() {
  elements.products.companySearchInput.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") {
      return;
    }

    event.preventDefault();
  });

  elements.products.companySearchInput.addEventListener("input", () => {
    scheduleProductCompanyLookup();
  });

  elements.products.companyClearButton.addEventListener("click", () => {
    cancelProductCompanyLookupRequest();
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

    cancelProductCompanyLookupRequest();
    setProductSelectedCompany(selectedCompany);
    setProductCreateError("");
  });
}

function bindProductSupplierLookup() {
  elements.products.supplierSearchInput.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") {
      return;
    }

    event.preventDefault();
  });

  elements.products.supplierSearchInput.addEventListener("input", () => {
    scheduleProductSupplierLookup();
  });

  elements.products.supplierClearButton.addEventListener("click", () => {
    cancelProductSupplierLookupRequest();
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

    cancelProductSupplierLookupRequest();
    setProductSelectedSupplier(selectedSupplier);
    setProductCreateError("");
  });
}

function scheduleProductCompanyLookup() {
  scheduleProductLookup({
    lookupKey: "company",
    searchTerm: elements.products.companySearchInput.value.trim(),
    clearLookup: clearProductCompanyLookup,
    searchLookup: searchProductCreateCompanies,
  });
}

function scheduleProductSupplierLookup() {
  scheduleProductLookup({
    lookupKey: "supplier",
    searchTerm: elements.products.supplierSearchInput.value.trim(),
    clearLookup: clearProductSupplierLookup,
    searchLookup: searchProductCreateSuppliers,
  });
}

function scheduleProductLookup({ lookupKey, searchTerm, clearLookup, searchLookup }) {
  cancelProductLookupRequest(lookupKey);
  clearLookup(false);
  setProductCreateError("");

  if (searchTerm.length < PRODUCT_LOOKUP_MIN_SEARCH_LENGTH) {
    return;
  }

  productLookupRequests[lookupKey].debounceId = window.setTimeout(() => {
    productLookupRequests[lookupKey].debounceId = null;
    searchLookup(searchTerm);
  }, PRODUCT_LOOKUP_DEBOUNCE_MS);
}

function cancelProductCompanyLookupRequest() {
  cancelProductLookupRequest("company");
}

function cancelProductSupplierLookupRequest() {
  cancelProductLookupRequest("supplier");
}

function cancelProductLookupRequest(lookupKey) {
  const requestState = productLookupRequests[lookupKey];

  if (!requestState) {
    return;
  }

  if (requestState.debounceId !== null) {
    window.clearTimeout(requestState.debounceId);
    requestState.debounceId = null;
  }

  if (requestState.controller) {
    requestState.controller.abort();
    requestState.controller = null;
  }
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

function bindSupplierCreate() {
  elements.suppliers.createForm.addEventListener("submit", (event) => {
    event.preventDefault();

    if (
      elements.suppliers.createSubmitButton.disabled ||
      !elements.suppliers.createForm.reportValidity()
    ) {
      return;
    }

    createSupplier();
  });

  elements.suppliers.createModal.addEventListener("hidden.bs.modal", () => {
    if (!state.suppliers.isCreating) {
      resetSupplierCreateForm();
    }
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

    cancelProductCompanyLookupRequest();
    cancelProductSupplierLookupRequest();
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

async function searchProductCreateCompanies(searchTerm) {
  if (searchTerm.length < PRODUCT_LOOKUP_MIN_SEARCH_LENGTH) {
    clearProductCompanyLookup(false);
    return;
  }

  const controller = new AbortController();
  productLookupRequests.company.controller = controller;

  setProductCompanyLookupError("");
  setProductCompanyLookupLoading(true);

  try {
    const companiesResponse = await request(getCompanyLookupPath(searchTerm), {
      signal: controller.signal,
    });

    if (
      !isCurrentProductLookupRequest(
        "company",
        controller,
        searchTerm,
        elements.products.companySearchInput,
      )
    ) {
      return;
    }

    const companiesPage = getPaginatedPage(companiesResponse);

    setProductCompanyLookupResults(companiesPage.items);
  } catch (error) {
    if (isAbortError(error)) {
      return;
    }

    if (
      !isCurrentProductLookupRequest(
        "company",
        controller,
        searchTerm,
        elements.products.companySearchInput,
      )
    ) {
      return;
    }

    console.error("Could not search companies for product create:", error);
    setProductCompanyLookupError(getRequestErrorMessage(error, "компании"));
  } finally {
    if (productLookupRequests.company.controller === controller) {
      productLookupRequests.company.controller = null;
      setProductCompanyLookupLoading(false);
    }
  }
}

async function searchProductCreateSuppliers(searchTerm) {
  if (searchTerm.length < PRODUCT_LOOKUP_MIN_SEARCH_LENGTH) {
    clearProductSupplierLookup(false);
    return;
  }

  const controller = new AbortController();
  productLookupRequests.supplier.controller = controller;

  setProductSupplierLookupError("");
  setProductSupplierLookupLoading(true);

  try {
    const suppliersResponse = await request(getSupplierLookupPath(searchTerm), {
      signal: controller.signal,
    });

    if (
      !isCurrentProductLookupRequest(
        "supplier",
        controller,
        searchTerm,
        elements.products.supplierSearchInput,
      )
    ) {
      return;
    }

    const suppliersPage = getPaginatedPage(suppliersResponse);

    setProductSupplierLookupResults(suppliersPage.items);
  } catch (error) {
    if (isAbortError(error)) {
      return;
    }

    if (
      !isCurrentProductLookupRequest(
        "supplier",
        controller,
        searchTerm,
        elements.products.supplierSearchInput,
      )
    ) {
      return;
    }

    console.error("Could not search suppliers for product create:", error);
    setProductSupplierLookupError(getRequestErrorMessage(error, "поставщиков"));
  } finally {
    if (productLookupRequests.supplier.controller === controller) {
      productLookupRequests.supplier.controller = null;
      setProductSupplierLookupLoading(false);
    }
  }
}

function isCurrentProductLookupRequest(lookupKey, controller, searchTerm, input) {
  return productLookupRequests[lookupKey]?.controller === controller &&
    !controller.signal.aborted &&
    input.value.trim() === searchTerm;
}

function isAbortError(error) {
  return error?.name === "AbortError";
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

async function createSupplier() {
  setSupplierCreateSubmitting(true);
  setSupplierCreateError("");

  try {
    await request("/suppliers", {
      method: "POST",
      body: JSON.stringify(getSupplierCreatePayload()),
    });

    hideSupplierCreateModal();
    resetSupplierCreateForm();

    await loadSuppliers(state.suppliers.searchTerm, state.suppliers.page);
  } catch (error) {
    console.error("Could not create supplier:", error);
    setSupplierCreateError(getCreateSupplierErrorMessage(error));
  } finally {
    setSupplierCreateSubmitting(false);
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

function getSupplierCreatePayload() {
  const formData = new FormData(elements.suppliers.createForm);

  return {
    name: getTextField(formData, "name"),
    phone_number: getTextField(formData, "phone_number"),
  };
}

function getCompanyLookupPath(searchTerm) {
  const params = new URLSearchParams();
  params.set("search", searchTerm);
  params.set("page", String(FIRST_LIST_PAGE));
  params.set("page_size", String(PRODUCT_LOOKUP_PAGE_SIZE));

  return `/companies?${params.toString()}`;
}

function getSupplierLookupPath(searchTerm) {
  const params = new URLSearchParams();
  params.set("search", searchTerm);
  params.set("page", String(FIRST_LIST_PAGE));
  params.set("page_size", String(PRODUCT_LOOKUP_PAGE_SIZE));

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

function hideSupplierCreateModal() {
  hideModal(elements.suppliers.createModal);
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

function getCreateSupplierErrorMessage(error) {
  return getCreateErrorMessage(error, "поставщика");
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
