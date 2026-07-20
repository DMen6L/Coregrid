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
  setDashboardSalesSummaryDays,
  setDashboardSalesSummaryLoading,
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
  resetRestockCreateForm,
  resetSaleCreateForm,
  setRestockCreateError,
  setRestockCreateSubmitting,
  setRestocksDateRange,
  setRestocksError,
  setRestocksLoading,
  setRestocksPagination,
  setSaleCreateError,
  setSaleCreateSubmitting,
  setSalesDateRange,
  setSalesError,
  setSalesLoading,
  setSalesPagination,
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
const DASHBOARD_SALES_MIN_DAYS = 7;
const DASHBOARD_SALES_MAX_DAYS = 365;
const DEFAULT_QUANTITY_UNIT = "шт";

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

let restockCreateLineSequence = 0;
const restockProductLookupRequests = new Map();
let saleCreateLineSequence = 0;
const saleProductLookupRequests = new Map();

initializeApp();

function initializeApp() {
  bindNavigation();
  bindDashboardSalesSummary();
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
  bindRestockFilters();
  bindRestockPagination();
  bindRestockCreate();
  bindSalesFilters();
  bindSalesPagination();
  bindSaleCreate();
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

function bindDashboardSalesSummary() {
  elements.dashboard.salesPeriodForm.addEventListener("submit", (event) => {
    event.preventDefault();

    if (
      elements.dashboard.salesPeriodButton.disabled ||
      !elements.dashboard.salesPeriodForm.reportValidity()
    ) {
      return;
    }

    const days = getDashboardSalesPeriodInputValue();

    if (days === null) {
      setAppMessage("Период продаж должен быть от 7 до 365 дней.");
      elements.dashboard.salesPeriodInput.focus();
      return;
    }

    loadDashboardSummary(days);
  });
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

function bindRestockFilters() {
  elements.restocks.filterForm.addEventListener("submit", (event) => {
    event.preventDefault();

    if (elements.restocks.filterButton.disabled) {
      return;
    }

    const dateFrom = elements.restocks.dateFromInput.value;
    const dateTo = elements.restocks.dateToInput.value;

    if (isInvalidDateRange(dateFrom, dateTo)) {
      setRestocksError("Дата начала не может быть позже даты окончания.");
      elements.restocks.dateFromInput.focus();
      return;
    }

    loadRestocks(dateFrom, dateTo, FIRST_LIST_PAGE);
  });

  elements.restocks.resetButton.addEventListener("click", () => {
    if (elements.restocks.resetButton.disabled) {
      return;
    }

    elements.restocks.dateFromInput.value = "";
    elements.restocks.dateToInput.value = "";
    loadRestocks("", "", FIRST_LIST_PAGE);
  });
}

function bindRestockPagination() {
  elements.restocks.previousPageButton.addEventListener("click", () => {
    if (elements.restocks.previousPageButton.disabled) {
      return;
    }

    loadRestocks(
      state.restocks.dateFrom,
      state.restocks.dateTo,
      state.restocks.page - 1,
    );
  });

  elements.restocks.nextPageButton.addEventListener("click", () => {
    if (elements.restocks.nextPageButton.disabled) {
      return;
    }

    loadRestocks(
      state.restocks.dateFrom,
      state.restocks.dateTo,
      state.restocks.page + 1,
    );
  });
}

function bindRestockCreate() {
  elements.restocks.createModal.addEventListener("show.bs.modal", () => {
    if (getRestockCreateLineRows().length === 0) {
      addRestockCreateLine();
    }
  });

  elements.restocks.createForm.addEventListener("submit", (event) => {
    event.preventDefault();

    if (
      elements.restocks.createSubmitButton.disabled ||
      !elements.restocks.createForm.reportValidity() ||
      !validateRestockCreateForm()
    ) {
      return;
    }

    createRestock();
  });

  elements.restocks.createAddLineButton.addEventListener("click", () => {
    if (elements.restocks.createAddLineButton.disabled) {
      return;
    }

    addRestockCreateLine();
  });

  elements.restocks.createLines.addEventListener("keydown", (event) => {
    if (
      event.key === "Enter" &&
      event.target instanceof Element &&
      event.target.matches("[data-restock-product-search]")
    ) {
      event.preventDefault();
    }
  });

  elements.restocks.createLines.addEventListener("input", (event) => {
    if (!(event.target instanceof Element)) {
      return;
    }

    if (event.target.matches("[data-restock-product-search]")) {
      scheduleRestockProductLookup(getRestockCreateLineElement(event.target));
    }
  });

  elements.restocks.createLines.addEventListener("click", (event) => {
    if (!(event.target instanceof Element)) {
      return;
    }

    const lineElement = getRestockCreateLineElement(event.target);

    if (!lineElement) {
      return;
    }

    if (event.target.closest("[data-restock-remove-line]")) {
      removeRestockCreateLine(lineElement);
      return;
    }

    if (event.target.closest("[data-restock-clear-product]")) {
      cancelRestockProductLookupRequest(lineElement.dataset.restockLineId);
      clearRestockLineSelectedProduct(lineElement);
      getRestockLineProductSearchInput(lineElement).focus();
      return;
    }

    const productButton = event.target.closest("[data-restock-product-id]");

    if (!productButton || !lineElement.contains(productButton)) {
      return;
    }

    const product = getRestockLineProducts(lineElement).find(
      (item) => String(item.id) === productButton.dataset.restockProductId,
    );

    if (!product) {
      return;
    }

    setRestockLineSelectedProduct(lineElement, product);
  });

  elements.restocks.createModal.addEventListener("hidden.bs.modal", () => {
    if (!state.restocks.isCreating) {
      resetRestockCreateModalState();
    }
  });
}

function bindSalesFilters() {
  elements.sales.filterForm.addEventListener("submit", (event) => {
    event.preventDefault();

    if (elements.sales.filterButton.disabled) {
      return;
    }

    const dateFrom = elements.sales.dateFromInput.value;
    const dateTo = elements.sales.dateToInput.value;

    if (isInvalidDateRange(dateFrom, dateTo)) {
      setSalesError("Дата начала не может быть позже даты окончания.");
      elements.sales.dateFromInput.focus();
      return;
    }

    loadSales(dateFrom, dateTo, FIRST_LIST_PAGE);
  });

  elements.sales.resetButton.addEventListener("click", () => {
    if (elements.sales.resetButton.disabled) {
      return;
    }

    elements.sales.dateFromInput.value = "";
    elements.sales.dateToInput.value = "";
    loadSales("", "", FIRST_LIST_PAGE);
  });
}

function bindSalesPagination() {
  elements.sales.previousPageButton.addEventListener("click", () => {
    if (elements.sales.previousPageButton.disabled) {
      return;
    }

    loadSales(
      state.sales.dateFrom,
      state.sales.dateTo,
      state.sales.page - 1,
    );
  });

  elements.sales.nextPageButton.addEventListener("click", () => {
    if (elements.sales.nextPageButton.disabled) {
      return;
    }

    loadSales(
      state.sales.dateFrom,
      state.sales.dateTo,
      state.sales.page + 1,
    );
  });
}

function bindSaleCreate() {
  elements.sales.createModal.addEventListener("show.bs.modal", () => {
    if (getSaleCreateLineRows().length === 0) {
      addSaleCreateLine();
    }
  });

  elements.sales.createForm.addEventListener("submit", (event) => {
    event.preventDefault();

    if (
      elements.sales.createSubmitButton.disabled ||
      !elements.sales.createForm.reportValidity() ||
      !validateSaleCreateForm()
    ) {
      return;
    }

    createSale();
  });

  elements.sales.createAddLineButton.addEventListener("click", () => {
    if (elements.sales.createAddLineButton.disabled) {
      return;
    }

    addSaleCreateLine();
  });

  elements.sales.createLines.addEventListener("keydown", (event) => {
    if (
      event.key === "Enter" &&
      event.target instanceof Element &&
      event.target.matches("[data-sale-product-search]")
    ) {
      event.preventDefault();
    }
  });

  elements.sales.createLines.addEventListener("input", (event) => {
    if (!(event.target instanceof Element)) {
      return;
    }

    if (event.target.matches("[data-sale-product-search]")) {
      scheduleSaleProductLookup(getSaleCreateLineElement(event.target));
    }
  });

  elements.sales.createLines.addEventListener("click", (event) => {
    if (!(event.target instanceof Element)) {
      return;
    }

    const lineElement = getSaleCreateLineElement(event.target);

    if (!lineElement) {
      return;
    }

    if (event.target.closest("[data-sale-remove-line]")) {
      removeSaleCreateLine(lineElement);
      return;
    }

    if (event.target.closest("[data-sale-clear-product]")) {
      cancelSaleProductLookupRequest(lineElement.dataset.saleLineId);
      clearSaleLineSelectedProduct(lineElement);
      getSaleLineProductSearchInput(lineElement).focus();
      return;
    }

    const productButton = event.target.closest("[data-sale-product-id]");

    if (!productButton || !lineElement.contains(productButton)) {
      return;
    }

    const product = getSaleLineProducts(lineElement).find(
      (item) => String(item.id) === productButton.dataset.saleProductId,
    );

    if (!product) {
      return;
    }

    setSaleLineSelectedProduct(lineElement, product);
  });

  elements.sales.createModal.addEventListener("hidden.bs.modal", () => {
    if (!state.sales.isCreating) {
      resetSaleCreateModalState();
    }
  });
}

function addRestockCreateLine(shouldFocus = true) {
  restockCreateLineSequence += 1;
  const lineElement = createRestockCreateLineElement(restockCreateLineSequence);
  elements.restocks.createLines.append(lineElement);
  updateRestockCreateLineIndexes();

  if (shouldFocus) {
    getRestockLineProductSearchInput(lineElement).focus();
  }
}

function createRestockCreateLineElement(lineId) {
  const lineElement = document.createElement("div");
  lineElement.className = "restock-create-line";
  lineElement.dataset.restockLineId = String(lineId);
  lineElement.dataset.productId = "";
  lineElement.dataset.lookupProducts = "[]";

  lineElement.innerHTML = `
    <div class="restock-create-line-header">
      <h4 class="fs-6 mb-0" data-restock-line-title>Позиция</h4>
      <button
        class="btn btn-sm btn-outline-danger"
        type="button"
        data-restock-remove-line
      >
        Удалить
      </button>
    </div>
    <div class="row g-3">
      <div class="col-12 col-lg-5">
        <label class="form-label">Товар</label>
        <input
          class="form-control"
          type="search"
          placeholder="Введите название товара"
          autocomplete="off"
          required
          aria-autocomplete="list"
          data-restock-product-search
        >
        <input type="hidden" data-restock-product-id-input>
        <div
          class="restock-create-product-selected d-none mt-2"
          data-restock-product-selected
        >
          <div>
            <div class="fw-semibold" data-restock-product-selected-name></div>
            <div class="restock-meta" data-restock-product-selected-meta></div>
          </div>
          <button
            class="btn btn-sm btn-outline-secondary"
            type="button"
            data-restock-clear-product
          >
            Сбросить
          </button>
        </div>
        <div
          class="restock-create-product-message text-secondary small d-none mt-2"
          role="status"
          data-restock-product-message
        ></div>
        <div
          class="list-group restock-create-product-results d-none mt-2"
          role="listbox"
          aria-label="Найденные товары"
          data-restock-product-results
        ></div>
      </div>
      <div class="col-12 col-md-4 col-lg-2">
        <label class="form-label">Количество</label>
        <input
          class="form-control"
          type="number"
          min="1"
          step="1"
          value="1"
          required
          data-restock-quantity
        >
      </div>
      <div class="col-12 col-md-4 col-lg-2">
        <label class="form-label">Цена закупки</label>
        <input
          class="form-control"
          type="number"
          min="0"
          step="1"
          data-restock-unit-cost
        >
      </div>
      <div class="col-12 col-md-4 col-lg-3">
        <label class="form-label">Единица</label>
        <input
          class="form-control"
          type="text"
          maxlength="20"
          value="${DEFAULT_QUANTITY_UNIT}"
          required
          data-restock-unit
        >
      </div>
    </div>
  `;

  return lineElement;
}

function removeRestockCreateLine(lineElement) {
  if (getRestockCreateLineRows().length <= 1) {
    return;
  }

  cancelRestockProductLookupRequest(lineElement.dataset.restockLineId);
  lineElement.remove();
  updateRestockCreateLineIndexes();
  setRestockCreateError("");
}

function updateRestockCreateLineIndexes() {
  const lineRows = getRestockCreateLineRows();

  lineRows.forEach((lineElement, index) => {
    const title = lineElement.querySelector("[data-restock-line-title]");
    const removeButton = lineElement.querySelector("[data-restock-remove-line]");

    title.textContent = `Позиция ${index + 1}`;
    removeButton.disabled = state.restocks.isCreating || lineRows.length <= 1;
  });
}

function getRestockCreateLineRows() {
  return Array.from(
    elements.restocks.createLines.querySelectorAll("[data-restock-line-id]"),
  );
}

function getRestockCreateLineElement(source) {
  return source?.closest("[data-restock-line-id]") || null;
}

function getRestockCreateLineById(lineId) {
  if (!lineId) {
    return null;
  }

  return elements.restocks.createLines.querySelector(
    `[data-restock-line-id="${lineId}"]`,
  );
}

function validateRestockCreateForm() {
  const productIds = new Set();
  const lineRows = getRestockCreateLineRows();

  if (lineRows.length === 0) {
    setRestockCreateError("Добавьте хотя бы одну позицию пополнения.");
    return false;
  }

  for (const lineElement of lineRows) {
    const productId = lineElement.dataset.productId;

    if (!productId) {
      setRestockCreateError("Выберите товар из результатов поиска для каждой позиции.");
      getRestockLineProductSearchInput(lineElement).focus();
      return false;
    }

    if (productIds.has(productId)) {
      setRestockCreateError("Один товар нельзя добавить в пополнение дважды.");
      getRestockLineProductSearchInput(lineElement).focus();
      return false;
    }

    productIds.add(productId);
  }

  setRestockCreateError("");
  return true;
}

function resetRestockCreateModalState() {
  cancelAllRestockProductLookupRequests();
  resetRestockCreateForm();
  elements.restocks.createLines.replaceChildren();
  restockCreateLineSequence = 0;
  addRestockCreateLine(false);
}

function setRestockCreateLineControlsDisabled(isDisabled) {
  for (const lineElement of getRestockCreateLineRows()) {
    for (const control of lineElement.querySelectorAll("input, button")) {
      control.disabled = isDisabled;
    }
  }

  updateRestockCreateLineIndexes();
}

function scheduleRestockProductLookup(lineElement) {
  if (!lineElement) {
    return;
  }

  const lineId = lineElement.dataset.restockLineId;
  const searchTerm = getRestockLineProductSearchInput(lineElement).value.trim();

  cancelRestockProductLookupRequest(lineId);
  clearRestockLineSelectedProduct(lineElement, false);
  setRestockLineProducts(lineElement, []);
  renderRestockProductResults(lineElement, []);
  renderRestockProductLookupMessage(lineElement, "");
  setRestockCreateError("");

  if (searchTerm.length < PRODUCT_LOOKUP_MIN_SEARCH_LENGTH) {
    return;
  }

  const requestState = getRestockProductLookupRequest(lineId);
  requestState.debounceId = window.setTimeout(() => {
    requestState.debounceId = null;
    searchRestockLineProducts(lineId, searchTerm);
  }, PRODUCT_LOOKUP_DEBOUNCE_MS);
}

async function searchRestockLineProducts(lineId, searchTerm) {
  const lineElement = getRestockCreateLineById(lineId);

  if (!lineElement) {
    return;
  }

  const requestState = getRestockProductLookupRequest(lineId);
  const controller = new AbortController();
  requestState.controller = controller;

  renderRestockProductLookupMessage(lineElement, "Поиск товаров...");

  try {
    const productsResponse = await request(getProductLookupPath(searchTerm), {
      signal: controller.signal,
    });

    if (!isCurrentRestockProductLookupRequest(lineId, controller, searchTerm)) {
      return;
    }

    const productsPage = getPaginatedPage(productsResponse);
    const products = productsPage.items;

    setRestockLineProducts(lineElement, products);
    renderRestockProductResults(lineElement, products);
    renderRestockProductLookupMessage(
      lineElement,
      products.length > 0 ? "" : "Товары не найдены.",
    );
  } catch (error) {
    if (isAbortError(error)) {
      return;
    }

    if (!isCurrentRestockProductLookupRequest(lineId, controller, searchTerm)) {
      return;
    }

    console.error("Could not search products for restock create:", error);
    renderRestockProductLookupMessage(
      lineElement,
      getRequestErrorMessage(error, "товары"),
      true,
    );
  } finally {
    if (requestState.controller === controller) {
      requestState.controller = null;
    }
  }
}

function isCurrentRestockProductLookupRequest(lineId, controller, searchTerm) {
  const lineElement = getRestockCreateLineById(lineId);
  const requestState = restockProductLookupRequests.get(lineId);

  return Boolean(lineElement) &&
    requestState?.controller === controller &&
    !controller.signal.aborted &&
    getRestockLineProductSearchInput(lineElement).value.trim() === searchTerm;
}

function getRestockProductLookupRequest(lineId) {
  if (!restockProductLookupRequests.has(lineId)) {
    restockProductLookupRequests.set(lineId, {
      debounceId: null,
      controller: null,
    });
  }

  return restockProductLookupRequests.get(lineId);
}

function cancelRestockProductLookupRequest(lineId) {
  const requestState = restockProductLookupRequests.get(lineId);

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

function cancelAllRestockProductLookupRequests() {
  for (const lineId of restockProductLookupRequests.keys()) {
    cancelRestockProductLookupRequest(lineId);
  }

  restockProductLookupRequests.clear();
}

function setRestockLineSelectedProduct(lineElement, product) {
  cancelRestockProductLookupRequest(lineElement.dataset.restockLineId);

  lineElement.dataset.productId = String(product.id || "");

  const productIdInput = lineElement.querySelector("[data-restock-product-id-input]");
  const searchInput = getRestockLineProductSearchInput(lineElement);
  const selected = lineElement.querySelector("[data-restock-product-selected]");
  const selectedName = lineElement.querySelector("[data-restock-product-selected-name]");
  const selectedMeta = lineElement.querySelector("[data-restock-product-selected-meta]");
  const unitCostInput = lineElement.querySelector("[data-restock-unit-cost]");
  const unitInput = lineElement.querySelector("[data-restock-unit]");

  productIdInput.value = product?.id ? String(product.id) : "";
  searchInput.value = product.name || "";
  selectedName.textContent = product.name || "Без названия";
  selectedMeta.textContent =
    `ID ${formatInlineCount(product.id)} | Остаток: ${formatInlineQuantity(
      product.quantity,
      product.quantity_unit,
    )}`;
  selected.classList.remove("d-none");

  if (!unitCostInput.value && product.purchase_price !== null && product.purchase_price !== undefined) {
    unitCostInput.value = String(product.purchase_price);
  }

  if (product.quantity_unit) {
    unitInput.value = product.quantity_unit;
  }

  setRestockLineProducts(lineElement, []);
  renderRestockProductResults(lineElement, []);
  renderRestockProductLookupMessage(lineElement, "");
  setRestockCreateError("");
}

function clearRestockLineSelectedProduct(lineElement, shouldClearInput = true) {
  lineElement.dataset.productId = "";

  const productIdInput = lineElement.querySelector("[data-restock-product-id-input]");
  const searchInput = getRestockLineProductSearchInput(lineElement);
  const selected = lineElement.querySelector("[data-restock-product-selected]");
  const selectedName = lineElement.querySelector("[data-restock-product-selected-name]");
  const selectedMeta = lineElement.querySelector("[data-restock-product-selected-meta]");

  productIdInput.value = "";
  selected.classList.add("d-none");
  selectedName.textContent = "";
  selectedMeta.textContent = "";

  if (shouldClearInput) {
    searchInput.value = "";
  }
}

function setRestockLineProducts(lineElement, products) {
  lineElement.dataset.lookupProducts = JSON.stringify(Array.isArray(products) ? products : []);
}

function getRestockLineProducts(lineElement) {
  try {
    const products = JSON.parse(lineElement.dataset.lookupProducts || "[]");
    return Array.isArray(products) ? products : [];
  } catch (error) {
    console.error("Could not parse restock product lookup data:", error);
    return [];
  }
}

function renderRestockProductResults(lineElement, products) {
  const results = lineElement.querySelector("[data-restock-product-results]");
  const productList = Array.isArray(products) ? products : [];

  results.replaceChildren();
  results.classList.toggle("d-none", productList.length === 0);

  if (productList.length === 0) {
    return;
  }

  const fragment = document.createDocumentFragment();

  for (const product of productList) {
    fragment.append(createRestockProductResultButton(product));
  }

  results.append(fragment);
}

function createRestockProductResultButton(product) {
  const button = document.createElement("button");
  button.className = "list-group-item list-group-item-action restock-create-product-result";
  button.type = "button";
  button.dataset.restockProductId = String(product.id || "");
  button.disabled = state.restocks.isCreating;
  button.setAttribute("role", "option");

  const name = document.createElement("span");
  name.className = "fw-semibold d-block";
  name.textContent = product.name || "Без названия";

  const meta = document.createElement("span");
  meta.className = "restock-meta d-block";
  meta.textContent =
    `ID ${formatInlineCount(product.id)} | Остаток: ${formatInlineQuantity(
      product.quantity,
      product.quantity_unit,
    )} | Закупка: ${formatInlineCurrency(product.purchase_price)}`;

  button.append(name, meta);
  return button;
}

function renderRestockProductLookupMessage(lineElement, message, isError = false) {
  const messageElement = lineElement.querySelector("[data-restock-product-message]");

  messageElement.textContent = message;
  messageElement.classList.toggle("d-none", !message);
  messageElement.classList.toggle("text-danger", isError);
  messageElement.classList.toggle("text-secondary", !isError);
}

function getRestockLineProductSearchInput(lineElement) {
  return lineElement.querySelector("[data-restock-product-search]");
}

function addSaleCreateLine(shouldFocus = true) {
  saleCreateLineSequence += 1;
  const lineElement = createSaleCreateLineElement(saleCreateLineSequence);
  elements.sales.createLines.append(lineElement);
  updateSaleCreateLineIndexes();

  if (shouldFocus) {
    getSaleLineProductSearchInput(lineElement).focus();
  }
}

function createSaleCreateLineElement(lineId) {
  const lineElement = document.createElement("div");
  lineElement.className = "sale-create-line";
  lineElement.dataset.saleLineId = String(lineId);
  lineElement.dataset.productId = "";
  lineElement.dataset.availableQuantity = "";
  lineElement.dataset.lookupProducts = "[]";

  lineElement.innerHTML = `
    <div class="sale-create-line-header">
      <h4 class="fs-6 mb-0" data-sale-line-title>Позиция</h4>
      <button
        class="btn btn-sm btn-outline-danger"
        type="button"
        data-sale-remove-line
      >
        Удалить
      </button>
    </div>
    <div class="row g-3">
      <div class="col-12 col-lg-8">
        <label class="form-label">Товар</label>
        <input
          class="form-control"
          type="search"
          placeholder="Введите название товара"
          autocomplete="off"
          required
          aria-autocomplete="list"
          data-sale-product-search
        >
        <input type="hidden" data-sale-product-id-input>
        <div
          class="sale-create-product-selected d-none mt-2"
          data-sale-product-selected
        >
          <div>
            <div class="fw-semibold" data-sale-product-selected-name></div>
            <div class="sale-meta" data-sale-product-selected-meta></div>
          </div>
          <button
            class="btn btn-sm btn-outline-secondary"
            type="button"
            data-sale-clear-product
          >
            Сбросить
          </button>
        </div>
        <div
          class="sale-create-product-message text-secondary small d-none mt-2"
          role="status"
          data-sale-product-message
        ></div>
        <div
          class="list-group sale-create-product-results d-none mt-2"
          role="listbox"
          aria-label="Найденные товары"
          data-sale-product-results
        ></div>
      </div>
      <div class="col-12 col-md-4 col-lg-4">
        <label class="form-label">Количество</label>
        <input
          class="form-control"
          type="number"
          min="1"
          step="1"
          value="1"
          required
          data-sale-quantity
        >
      </div>
    </div>
  `;

  return lineElement;
}

function removeSaleCreateLine(lineElement) {
  if (getSaleCreateLineRows().length <= 1) {
    return;
  }

  cancelSaleProductLookupRequest(lineElement.dataset.saleLineId);
  lineElement.remove();
  updateSaleCreateLineIndexes();
  setSaleCreateError("");
}

function updateSaleCreateLineIndexes() {
  const lineRows = getSaleCreateLineRows();

  lineRows.forEach((lineElement, index) => {
    const title = lineElement.querySelector("[data-sale-line-title]");
    const removeButton = lineElement.querySelector("[data-sale-remove-line]");

    title.textContent = `Позиция ${index + 1}`;
    removeButton.disabled = state.sales.isCreating || lineRows.length <= 1;
  });
}

function getSaleCreateLineRows() {
  return Array.from(
    elements.sales.createLines.querySelectorAll("[data-sale-line-id]"),
  );
}

function getSaleCreateLineElement(source) {
  return source?.closest("[data-sale-line-id]") || null;
}

function getSaleCreateLineById(lineId) {
  if (!lineId) {
    return null;
  }

  return elements.sales.createLines.querySelector(
    `[data-sale-line-id="${lineId}"]`,
  );
}

function validateSaleCreateForm() {
  const productIds = new Set();
  const lineRows = getSaleCreateLineRows();

  if (lineRows.length === 0) {
    setSaleCreateError("Добавьте хотя бы одну позицию продажи.");
    return false;
  }

  for (const lineElement of lineRows) {
    const productId = lineElement.dataset.productId;
    const quantity = getSaleLineNumberValue(lineElement, "[data-sale-quantity]");
    const availableQuantity = Number(lineElement.dataset.availableQuantity);

    if (!productId) {
      setSaleCreateError("Выберите товар из результатов поиска для каждой позиции.");
      getSaleLineProductSearchInput(lineElement).focus();
      return false;
    }

    if (productIds.has(productId)) {
      setSaleCreateError("Один товар нельзя добавить в продажу дважды.");
      getSaleLineProductSearchInput(lineElement).focus();
      return false;
    }

    if (!Number.isFinite(quantity) || quantity <= 0) {
      setSaleCreateError("Количество продажи должно быть больше нуля.");
      lineElement.querySelector("[data-sale-quantity]").focus();
      return false;
    }

    if (Number.isFinite(availableQuantity) && quantity > availableQuantity) {
      setSaleCreateError(
        `Нельзя продать больше остатка: доступно ${formatInlineQuantity(
          availableQuantity,
          lineElement.dataset.quantityUnit,
        )}.`,
      );
      lineElement.querySelector("[data-sale-quantity]").focus();
      return false;
    }

    productIds.add(productId);
  }

  setSaleCreateError("");
  return true;
}

function resetSaleCreateModalState() {
  cancelAllSaleProductLookupRequests();
  resetSaleCreateForm();
  elements.sales.createLines.replaceChildren();
  saleCreateLineSequence = 0;
  addSaleCreateLine(false);
}

function setSaleCreateLineControlsDisabled(isDisabled) {
  for (const lineElement of getSaleCreateLineRows()) {
    for (const control of lineElement.querySelectorAll("input, button")) {
      control.disabled = isDisabled;
    }
  }

  updateSaleCreateLineIndexes();
}

function scheduleSaleProductLookup(lineElement) {
  if (!lineElement) {
    return;
  }

  const lineId = lineElement.dataset.saleLineId;
  const searchTerm = getSaleLineProductSearchInput(lineElement).value.trim();

  cancelSaleProductLookupRequest(lineId);
  clearSaleLineSelectedProduct(lineElement, false);
  setSaleLineProducts(lineElement, []);
  renderSaleProductResults(lineElement, []);
  renderSaleProductLookupMessage(lineElement, "");
  setSaleCreateError("");

  if (searchTerm.length < PRODUCT_LOOKUP_MIN_SEARCH_LENGTH) {
    return;
  }

  const requestState = getSaleProductLookupRequest(lineId);
  requestState.debounceId = window.setTimeout(() => {
    requestState.debounceId = null;
    searchSaleLineProducts(lineId, searchTerm);
  }, PRODUCT_LOOKUP_DEBOUNCE_MS);
}

async function searchSaleLineProducts(lineId, searchTerm) {
  const lineElement = getSaleCreateLineById(lineId);

  if (!lineElement) {
    return;
  }

  const requestState = getSaleProductLookupRequest(lineId);
  const controller = new AbortController();
  requestState.controller = controller;

  renderSaleProductLookupMessage(lineElement, "Поиск товаров...");

  try {
    const productsResponse = await request(getProductLookupPath(searchTerm), {
      signal: controller.signal,
    });

    if (!isCurrentSaleProductLookupRequest(lineId, controller, searchTerm)) {
      return;
    }

    const productsPage = getPaginatedPage(productsResponse);
    const products = productsPage.items;

    setSaleLineProducts(lineElement, products);
    renderSaleProductResults(lineElement, products);
    renderSaleProductLookupMessage(
      lineElement,
      products.length > 0 ? "" : "Товары не найдены.",
    );
  } catch (error) {
    if (isAbortError(error)) {
      return;
    }

    if (!isCurrentSaleProductLookupRequest(lineId, controller, searchTerm)) {
      return;
    }

    console.error("Could not search products for sale create:", error);
    renderSaleProductLookupMessage(
      lineElement,
      getRequestErrorMessage(error, "товары"),
      true,
    );
  } finally {
    if (requestState.controller === controller) {
      requestState.controller = null;
    }
  }
}

function isCurrentSaleProductLookupRequest(lineId, controller, searchTerm) {
  const lineElement = getSaleCreateLineById(lineId);
  const requestState = saleProductLookupRequests.get(lineId);

  return Boolean(lineElement) &&
    requestState?.controller === controller &&
    !controller.signal.aborted &&
    getSaleLineProductSearchInput(lineElement).value.trim() === searchTerm;
}

function getSaleProductLookupRequest(lineId) {
  if (!saleProductLookupRequests.has(lineId)) {
    saleProductLookupRequests.set(lineId, {
      debounceId: null,
      controller: null,
    });
  }

  return saleProductLookupRequests.get(lineId);
}

function cancelSaleProductLookupRequest(lineId) {
  const requestState = saleProductLookupRequests.get(lineId);

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

function cancelAllSaleProductLookupRequests() {
  for (const lineId of saleProductLookupRequests.keys()) {
    cancelSaleProductLookupRequest(lineId);
  }

  saleProductLookupRequests.clear();
}

function setSaleLineSelectedProduct(lineElement, product) {
  cancelSaleProductLookupRequest(lineElement.dataset.saleLineId);

  lineElement.dataset.productId = String(product.id || "");
  lineElement.dataset.availableQuantity = String(product.quantity ?? "");
  lineElement.dataset.quantityUnit = product.quantity_unit || DEFAULT_QUANTITY_UNIT;

  const productIdInput = lineElement.querySelector("[data-sale-product-id-input]");
  const searchInput = getSaleLineProductSearchInput(lineElement);
  const selected = lineElement.querySelector("[data-sale-product-selected]");
  const selectedName = lineElement.querySelector("[data-sale-product-selected-name]");
  const selectedMeta = lineElement.querySelector("[data-sale-product-selected-meta]");

  productIdInput.value = product?.id ? String(product.id) : "";
  searchInput.value = product.name || "";
  selectedName.textContent = product.name || "Без названия";
  selectedMeta.textContent =
    `ID ${formatInlineCount(product.id)} | Остаток: ${formatInlineQuantity(
      product.quantity,
      product.quantity_unit,
    )} | Продажа: ${formatInlineCurrency(product.sale_price)}`;
  selected.classList.remove("d-none");

  setSaleLineProducts(lineElement, []);
  renderSaleProductResults(lineElement, []);
  renderSaleProductLookupMessage(lineElement, "");
  setSaleCreateError("");
}

function clearSaleLineSelectedProduct(lineElement, shouldClearInput = true) {
  lineElement.dataset.productId = "";
  lineElement.dataset.availableQuantity = "";
  lineElement.dataset.quantityUnit = "";

  const productIdInput = lineElement.querySelector("[data-sale-product-id-input]");
  const searchInput = getSaleLineProductSearchInput(lineElement);
  const selected = lineElement.querySelector("[data-sale-product-selected]");
  const selectedName = lineElement.querySelector("[data-sale-product-selected-name]");
  const selectedMeta = lineElement.querySelector("[data-sale-product-selected-meta]");

  productIdInput.value = "";
  selected.classList.add("d-none");
  selectedName.textContent = "";
  selectedMeta.textContent = "";

  if (shouldClearInput) {
    searchInput.value = "";
  }
}

function setSaleLineProducts(lineElement, products) {
  lineElement.dataset.lookupProducts = JSON.stringify(Array.isArray(products) ? products : []);
}

function getSaleLineProducts(lineElement) {
  try {
    const products = JSON.parse(lineElement.dataset.lookupProducts || "[]");
    return Array.isArray(products) ? products : [];
  } catch (error) {
    console.error("Could not parse sale product lookup data:", error);
    return [];
  }
}

function renderSaleProductResults(lineElement, products) {
  const results = lineElement.querySelector("[data-sale-product-results]");
  const productList = Array.isArray(products) ? products : [];

  results.replaceChildren();
  results.classList.toggle("d-none", productList.length === 0);

  if (productList.length === 0) {
    return;
  }

  const fragment = document.createDocumentFragment();

  for (const product of productList) {
    fragment.append(createSaleProductResultButton(product));
  }

  results.append(fragment);
}

function createSaleProductResultButton(product) {
  const button = document.createElement("button");
  button.className = "list-group-item list-group-item-action sale-create-product-result";
  button.type = "button";
  button.dataset.saleProductId = String(product.id || "");
  button.disabled = state.sales.isCreating || Number(product.quantity) <= 0;
  button.setAttribute("role", "option");

  const name = document.createElement("span");
  name.className = "fw-semibold d-block";
  name.textContent = product.name || "Без названия";

  const meta = document.createElement("span");
  meta.className = "sale-meta d-block";
  meta.textContent =
    `ID ${formatInlineCount(product.id)} | Остаток: ${formatInlineQuantity(
      product.quantity,
      product.quantity_unit,
    )} | Продажа: ${formatInlineCurrency(product.sale_price)}`;

  button.append(name, meta);
  return button;
}

function renderSaleProductLookupMessage(lineElement, message, isError = false) {
  const messageElement = lineElement.querySelector("[data-sale-product-message]");

  messageElement.textContent = message;
  messageElement.classList.toggle("d-none", !message);
  messageElement.classList.toggle("text-danger", isError);
  messageElement.classList.toggle("text-secondary", !isError);
}

function getSaleLineProductSearchInput(lineElement) {
  return lineElement.querySelector("[data-sale-product-search]");
}

async function loadInitialData() {
  await Promise.all([
    loadDashboardSummary(),
    loadProducts(),
    loadCompanies(),
    loadSuppliers(),
    loadRestocks(),
    loadSales(),
  ]);
}

async function loadDashboardSummary(days = state.sales.summaryDays) {
  const summaryDays = clampDashboardSalesDays(days);

  setDashboardSalesSummaryLoading(true);
  setAppMessage("");

  try {
    const summary = await request(getSummariesPath(summaryDays));

    setState("sales.value", summary.dashboard_sales_value);
    setState("sales.count", summary.dashboard_sales_count);
    setDashboardSalesSummaryDays(summaryDays);
    setState(
      "sales.dailyTotals",
      getDashboardSalesTrendRows(
        summary.latest_sales || summary.latestSales,
        summaryDays,
      ),
    );
    setState("products.lowStock", summary.low_stock);
    setState("products.outOfStock", summary.out_of_stock);
  } catch (error) {
    console.error("Could not load dashboard summaries:", error);
    setAppMessage(getRequestErrorMessage(error, "показатели дэшборда"));
  } finally {
    setDashboardSalesSummaryLoading(false);
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

async function loadRestocks(dateFrom = "", dateTo = "", page = FIRST_LIST_PAGE) {
  setRestocksLoading(true);
  setRestocksDateRange(dateFrom, dateTo);
  setRestocksError("");

  try {
    const restocksResponse = await request(getRestocksPath(dateFrom, dateTo, page));
    const restocksPage = getPaginatedPage(restocksResponse);

    setRestocksPagination(restocksPage.pagination);
    setState("restocks.list", restocksPage.items);
  } catch (error) {
    console.error("Could not load restocks:", error);
    setRestocksPagination({
      page,
      pageSize: state.restocks.pageSize,
      total: 0,
      totalPages: 0,
      hasNext: false,
      hasPrevious: false,
    });
    setState("restocks.list", []);
    setRestocksError(getRequestErrorMessage(error, "пополнения"));
  } finally {
    setRestocksLoading(false);
  }
}

async function loadSales(dateFrom = "", dateTo = "", page = FIRST_LIST_PAGE) {
  setSalesLoading(true);
  setSalesDateRange(dateFrom, dateTo);
  setSalesError("");

  try {
    const salesResponse = await request(getSalesPath(dateFrom, dateTo, page));
    const salesPage = getPaginatedPage(salesResponse);

    setSalesPagination(salesPage.pagination);
    setState("sales.list", salesPage.items);
  } catch (error) {
    console.error("Could not load sales:", error);
    setSalesPagination({
      page,
      pageSize: state.sales.pageSize,
      total: 0,
      totalPages: 0,
      hasNext: false,
      hasPrevious: false,
    });
    setState("sales.list", []);
    setSalesError(getRequestErrorMessage(error, "продажи"));
  } finally {
    setSalesLoading(false);
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

async function createRestock() {
  setRestockCreateSubmitting(true);
  setRestockCreateLineControlsDisabled(true);
  setRestockCreateError("");

  try {
    await request("/restocks", {
      method: "POST",
      body: JSON.stringify(getRestockCreatePayload()),
    });

    cancelAllRestockProductLookupRequests();
    hideRestockCreateModal();
    resetRestockCreateModalState();

    await Promise.all([
      loadDashboardSummary(),
      loadProducts(state.products.searchTerm, state.products.page),
      loadRestocks(state.restocks.dateFrom, state.restocks.dateTo, FIRST_LIST_PAGE),
    ]);
  } catch (error) {
    console.error("Could not create restock:", error);
    setRestockCreateError(getCreateRestockErrorMessage(error));
  } finally {
    setRestockCreateSubmitting(false);
    setRestockCreateLineControlsDisabled(false);
  }
}

async function createSale() {
  setSaleCreateSubmitting(true);
  setSaleCreateLineControlsDisabled(true);
  setSaleCreateError("");

  try {
    await request("/sales", {
      method: "POST",
      body: JSON.stringify(getSaleCreatePayload()),
    });

    cancelAllSaleProductLookupRequests();
    hideSaleCreateModal();
    resetSaleCreateModalState();

    await Promise.all([
      loadDashboardSummary(),
      loadProducts(state.products.searchTerm, state.products.page),
      loadSales(state.sales.dateFrom, state.sales.dateTo, FIRST_LIST_PAGE),
    ]);
  } catch (error) {
    console.error("Could not create sale:", error);
    setSaleCreateError(getCreateSaleErrorMessage(error));
  } finally {
    setSaleCreateSubmitting(false);
    setSaleCreateLineControlsDisabled(false);
  }
}

function getProductsPath(searchTerm, page) {
  return getListPath("/products", searchTerm, page);
}

function getSummariesPath(days) {
  const params = new URLSearchParams();
  params.set("days_ago", String(clampDashboardSalesDays(days)));
  return `/summaries?${params.toString()}`;
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

function getRestocksPath(dateFrom, dateTo, page) {
  const params = new URLSearchParams();

  if (dateFrom) {
    params.set("from", dateFrom);
  }

  if (dateTo) {
    params.set("to", dateTo);
  }

  params.set("page", String(Math.max(page, FIRST_LIST_PAGE)));

  return `/restocks?${params.toString()}`;
}

function getSalesPath(dateFrom, dateTo, page) {
  const params = new URLSearchParams();

  if (dateFrom) {
    params.set("from", dateFrom);
  }

  if (dateTo) {
    params.set("to", dateTo);
  }

  params.set("page", String(Math.max(page, FIRST_LIST_PAGE)));

  return `/sales?${params.toString()}`;
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

function getRestockCreatePayload() {
  const note = elements.restocks.createNoteInput.value.trim();

  return {
    note: note || null,
    lines: getRestockCreateLineRows().map(getRestockCreateLinePayload),
  };
}

function getRestockCreateLinePayload(lineElement) {
  return {
    product_id: Number(lineElement.dataset.productId),
    restock_quantity: getRestockLineNumberValue(lineElement, "[data-restock-quantity]"),
    unit_cost_snapshot: getRestockLineOptionalNumberValue(
      lineElement,
      "[data-restock-unit-cost]",
    ),
    quantity_unit_snapshot:
      getRestockLineTextValue(lineElement, "[data-restock-unit]") ||
      DEFAULT_QUANTITY_UNIT,
  };
}

function getSaleCreatePayload() {
  const note = elements.sales.createNoteInput.value.trim();

  return {
    note: note || null,
    lines: getSaleCreateLineRows().map(getSaleCreateLinePayload),
  };
}

function getSaleCreateLinePayload(lineElement) {
  return {
    product_id: Number(lineElement.dataset.productId),
    sale_quantity: getSaleLineNumberValue(lineElement, "[data-sale-quantity]"),
  };
}

function getRestockLineNumberValue(lineElement, selector) {
  return Number(getRestockLineTextValue(lineElement, selector));
}

function getSaleLineNumberValue(lineElement, selector) {
  return Number(getSaleLineTextValue(lineElement, selector));
}

function getRestockLineOptionalNumberValue(lineElement, selector) {
  const value = getRestockLineTextValue(lineElement, selector);
  return value ? Number(value) : null;
}

function getRestockLineTextValue(lineElement, selector) {
  return String(lineElement.querySelector(selector)?.value || "").trim();
}

function getSaleLineTextValue(lineElement, selector) {
  return String(lineElement.querySelector(selector)?.value || "").trim();
}

function getProductLookupPath(searchTerm) {
  const params = new URLSearchParams();
  params.set("search", searchTerm);
  params.set("page", String(FIRST_LIST_PAGE));
  params.set("page_size", String(PRODUCT_LOOKUP_PAGE_SIZE));

  return `/products?${params.toString()}`;
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

function getDashboardSalesPeriodInputValue() {
  const days = Number(elements.dashboard.salesPeriodInput.value);

  if (
    !Number.isInteger(days) ||
    days < DASHBOARD_SALES_MIN_DAYS ||
    days > DASHBOARD_SALES_MAX_DAYS
  ) {
    return null;
  }

  return days;
}

function clampDashboardSalesDays(days) {
  const numberValue = Number(days);

  if (!Number.isFinite(numberValue)) {
    return DASHBOARD_SALES_MIN_DAYS;
  }

  return Math.min(
    Math.max(Math.trunc(numberValue), DASHBOARD_SALES_MIN_DAYS),
    DASHBOARD_SALES_MAX_DAYS,
  );
}

function getDashboardSalesTrendRows(latestSales, days) {
  const dailySales = new Map();
  const sourceRows = Array.isArray(latestSales) ? latestSales : [];

  for (const row of sourceRows) {
    const dateKey = getDateKeyFromApiValue(row?.date);
    const salesValue = getDashboardSalesValueFromApiRow(row);

    if (!dateKey) {
      continue;
    }

    dailySales.set(dateKey, (dailySales.get(dateKey) || 0) + salesValue);
  }

  const clampedDays = clampDashboardSalesDays(days);
  const endDateKey = getDashboardSalesTrendEndDateKey(sourceRows);
  const startDate = getDateFromDateKey(endDateKey);
  startDate.setDate(startDate.getDate() - clampedDays + 1);

  return Array.from({ length: clampedDays }, (_, index) => {
    const currentDate = new Date(startDate);
    currentDate.setDate(startDate.getDate() + index);

    const dateKey = getDateKey(currentDate);

    return {
      date: dateKey,
      displayDate: formatDashboardDate(currentDate),
      shortDate: formatDashboardShortDate(currentDate),
      salesValue: dailySales.get(dateKey) || 0,
    };
  });
}

function getDashboardSalesValueFromApiRow(row) {
  const rawValue = row?.sales_value ?? row?.salesValue ?? 0;
  const salesValue = Number(rawValue);
  return Number.isFinite(salesValue) ? salesValue : 0;
}

function getDashboardSalesTrendEndDateKey(sourceRows) {
  const todayKey = getDateKey(getStartOfToday());
  let latestDateKey = todayKey;

  for (const row of sourceRows) {
    const dateKey = getDateKeyFromApiValue(row?.date);

    if (dateKey && dateKey > latestDateKey) {
      latestDateKey = dateKey;
    }
  }

  return latestDateKey;
}

function getDateKeyFromApiValue(value) {
  if (!value) {
    return "";
  }

  if (value instanceof Date) {
    return getDateKey(value);
  }

  const textValue = String(value);
  const isoDate = textValue.match(/^\d{4}-\d{2}-\d{2}/)?.[0];

  return isoDate || "";
}

function getDateFromDateKey(dateKey) {
  const [year, month, day] = dateKey.split("-").map(Number);

  if (!year || !month || !day) {
    return getStartOfToday();
  }

  return new Date(year, month - 1, day);
}

function getStartOfToday() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return today;
}

function getDateKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function formatDashboardDate(date) {
  return date.toLocaleDateString("ru-KZ", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

function formatDashboardShortDate(date) {
  return date.toLocaleDateString("ru-KZ", {
    day: "2-digit",
    month: "short",
  });
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

function isInvalidDateRange(dateFrom, dateTo) {
  return Boolean(dateFrom && dateTo && dateFrom > dateTo);
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

function hideRestockCreateModal() {
  hideModal(elements.restocks.createModal);
}

function hideSaleCreateModal() {
  hideModal(elements.sales.createModal);
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

function getCreateRestockErrorMessage(error) {
  return getCreateErrorMessage(error, "пополнение");
}

function getCreateSaleErrorMessage(error) {
  return getCreateErrorMessage(error, "продажу");
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

function formatInlineCurrency(value) {
  return `${Number(value || 0).toLocaleString("ru-KZ")} тг`;
}

function formatInlineCount(value) {
  return Number(value || 0).toLocaleString("ru-KZ");
}

function formatInlineQuantity(quantity, unit) {
  return `${formatInlineCount(quantity)} ${unit || DEFAULT_QUANTITY_UNIT}`;
}
