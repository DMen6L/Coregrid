import {
  FIRST_PAGE,
  buildLookupPath,
  createCompany,
  createProduct,
  createProductSupplierLinks,
  createSupplier,
  getProducts,
} from "./api.js";
import { elements } from "./dom.js";
import {
  DEFAULT_QUANTITY_UNIT,
  getCreateErrorMessage,
  getRequestErrorMessage,
} from "./format.js";
import {
  renderLookup,
  renderProductCreateMode,
  renderProducts,
  setAppMessage,
  setCreateError,
  setSubmitting,
} from "./render.js";
import { createLookupState, applyPage, resetPage, state } from "./state.js";
import { loadCompanies } from "./companies.js";
import { loadDashboard } from "./dashboard.js";
import { loadSuppliers } from "./suppliers.js";
import { request } from "./utils.js";

const LOOKUP_MIN_LENGTH = 2;
const LOOKUP_DEBOUNCE_MS = 300;

const lookupRequests = {
  company: { controller: null, debounceId: null },
  supplier: { controller: null, debounceId: null },
};

export function bindProductsFeature() {
  elements.products.searchForm.addEventListener("submit", (event) => {
    event.preventDefault();
    loadProducts(elements.products.searchInput.value.trim(), FIRST_PAGE);
  });

  elements.products.previousPageButton.addEventListener("click", () => {
    if (!elements.products.previousPageButton.disabled) {
      loadProducts(state.products.searchTerm, state.products.page - 1);
    }
  });

  elements.products.nextPageButton.addEventListener("click", () => {
    if (!elements.products.nextPageButton.disabled) {
      loadProducts(state.products.searchTerm, state.products.page + 1);
    }
  });

  bindProductCreateForm();
  bindCompanyLookup();
  bindSupplierLookup();
  syncProductCreateMode();
}

export async function loadProducts(searchTerm = "", page = FIRST_PAGE) {
  state.products.isLoading = true;
  state.products.searchTerm = searchTerm;
  state.products.error = "";
  renderProducts();

  try {
    const response = await getProducts({ search: searchTerm, page });
    applyPage(state.products, response, page);
  } catch (error) {
    console.error("Could not load products:", error);
    resetPage(state.products, page);
    state.products.error = getRequestErrorMessage(error, "товары");
  } finally {
    state.products.isLoading = false;
    renderProducts();
  }
}

function bindProductCreateForm() {
  elements.products.form.addEventListener("submit", (event) => {
    event.preventDefault();

    if (!elements.products.form.reportValidity() || state.productCreate.isSubmitting) {
      return;
    }

    submitProductCreate();
  });

  elements.products.modal.addEventListener("hidden.bs.modal", () => {
    if (!state.productCreate.isSubmitting) {
      resetProductCreateForm();
    }
  });

  for (const input of elements.products.companyModeInputs) {
    input.addEventListener("change", () => {
      state.productCreate.companyMode = getCheckedValue(elements.products.companyModeInputs);
      clearSelectedCompany();
      syncProductCreateMode();
    });
  }

  elements.products.linkEnabledInput.addEventListener("change", () => {
    state.productCreate.linkEnabled = elements.products.linkEnabledInput.checked;
    clearSelectedSupplier();
    syncProductCreateMode();
  });

  for (const input of elements.products.supplierModeInputs) {
    input.addEventListener("change", () => {
      state.productCreate.supplierMode = getCheckedValue(elements.products.supplierModeInputs);
      clearSelectedSupplier();
      syncProductCreateMode();
    });
  }
}

function bindCompanyLookup() {
  elements.products.companySearchInput.addEventListener("keydown", preventEnter);
  elements.products.companySearchInput.addEventListener("input", () => {
    scheduleLookup("company", elements.products.companySearchInput.value.trim());
  });
  elements.products.companyClearButton.addEventListener("click", () => {
    clearSelectedCompany();
    elements.products.companySearchInput.focus();
  });
  elements.products.companyResults.addEventListener("click", (event) => {
    const button = event.target instanceof Element
      ? event.target.closest("[data-company-id]")
      : null;

    if (!button) {
      return;
    }

    const company = state.productCreate.companyLookup.results.find(
      (item) => String(item.id) === button.dataset.companyId,
    );

    if (company) {
      cancelLookup("company");
      state.productCreate.selectedCompany = company;
      elements.products.companyIdInput.value = String(company.id);
      state.productCreate.companyLookup = createLookupState();
      renderLookup({ kind: "company" });
      setCreateError(elements.products.createError);
    }
  });
}

function bindSupplierLookup() {
  elements.products.supplierSearchInput.addEventListener("keydown", preventEnter);
  elements.products.supplierSearchInput.addEventListener("input", () => {
    scheduleLookup("supplier", elements.products.supplierSearchInput.value.trim());
  });
  elements.products.supplierClearButton.addEventListener("click", () => {
    clearSelectedSupplier();
    elements.products.supplierSearchInput.focus();
  });
  elements.products.supplierResults.addEventListener("click", (event) => {
    const button = event.target instanceof Element
      ? event.target.closest("[data-supplier-id]")
      : null;

    if (!button) {
      return;
    }

    const supplier = state.productCreate.supplierLookup.results.find(
      (item) => String(item.id) === button.dataset.supplierId,
    );

    if (supplier) {
      cancelLookup("supplier");
      state.productCreate.selectedSupplier = supplier;
      elements.products.supplierIdInput.value = String(supplier.id);
      state.productCreate.supplierLookup = createLookupState();
      renderLookup({ kind: "supplier" });
      setCreateError(elements.products.createError);
    }
  });
}

async function submitProductCreate() {
  const productPayload = getProductBasePayload();
  const inlineCompanyPayload = state.productCreate.companyMode === "new"
    ? getInlineCompanyPayload()
    : null;
  const shouldCreateLink = state.productCreate.linkEnabled;
  const inlineSupplierPayload = shouldCreateLink && state.productCreate.supplierMode === "new"
    ? getInlineSupplierPayload()
    : null;
  const supplierLinkPayload = shouldCreateLink
    ? getSupplierLinkBasePayload()
    : null;

  state.productCreate.isSubmitting = true;
  setCreateError(elements.products.createError);
  setAppMessage("");
  setSubmitting(elements.products.form, true);

  try {
    const company = await resolveCompany(inlineCompanyPayload);
    const product = await createProduct({
      ...productPayload,
      company_id: Number(company.id),
    });
    let linkError = null;

    if (shouldCreateLink) {
      try {
        const supplier = await resolveSupplier(inlineSupplierPayload);
        await createProductSupplierLinks(product.id, [{
          ...supplierLinkPayload,
          supplier_id: Number(supplier.id),
        }]);
      } catch (error) {
        linkError = error;
        console.error("Could not create product supplier link:", error);
      }
    }

    hideModal(elements.products.modal);
    resetProductCreateForm();

    if (linkError) {
      setAppMessage(
        `Товар создан, но связь с поставщиком не создана: ${getCreateErrorMessage(linkError, "связь с поставщиком")}`,
        "warning",
      );
    }

    await Promise.all([
      loadDashboard(),
      loadProducts(state.products.searchTerm, state.products.page),
      loadCompanies(state.companies.searchTerm, state.companies.page),
      loadSuppliers(state.suppliers.searchTerm, state.suppliers.page),
    ]);
  } catch (error) {
    console.error("Could not create product:", error);
    setCreateError(elements.products.createError, getCreateErrorMessage(error, "товар"));
  } finally {
    state.productCreate.isSubmitting = false;
    setSubmitting(elements.products.form, false);
    syncProductCreateMode();
  }
}

async function resolveCompany(inlinePayload) {
  if (state.productCreate.companyMode === "new") {
    return createCompany(inlinePayload);
  }

  if (!state.productCreate.selectedCompany) {
    throw createLocalValidationError("Выберите компанию или создайте новую.");
  }

  return state.productCreate.selectedCompany;
}

async function resolveSupplier(inlinePayload) {
  if (state.productCreate.supplierMode === "new") {
    return createSupplier(inlinePayload);
  }

  if (!state.productCreate.selectedSupplier) {
    throw createLocalValidationError("Выберите поставщика или создайте нового.");
  }

  return state.productCreate.selectedSupplier;
}

function getProductBasePayload() {
  const formData = new FormData(elements.products.form);

  return {
    name: getText(formData, "name"),
    quantity_unit: getText(formData, "quantity_unit") || DEFAULT_QUANTITY_UNIT,
    low_stock_threshold: getNumber(formData, "low_stock_threshold"),
    tags: getTags(formData),
  };
}

function getSupplierLinkBasePayload() {
  const formData = new FormData(elements.products.form);

  return {
    purchase_price: getNumber(formData, "purchase_price"),
    margin_percent: getNumber(formData, "margin_percent"),
    sale_price: getOptionalNumber(formData, "sale_price"),
    quantity: getNumber(formData, "quantity"),
  };
}

function getInlineCompanyPayload() {
  const formData = new FormData(elements.products.form);

  return {
    name: getText(formData, "new_company_name"),
    iin: getOptionalText(formData, "new_company_iin"),
  };
}

function getInlineSupplierPayload() {
  const formData = new FormData(elements.products.form);

  return {
    name: getText(formData, "new_supplier_name"),
    phone_number: getText(formData, "new_supplier_phone_number"),
  };
}

function scheduleLookup(kind, searchTerm) {
  cancelLookup(kind);
  clearLookupState(kind, false);

  if (searchTerm.length < LOOKUP_MIN_LENGTH) {
    return;
  }

  lookupRequests[kind].debounceId = window.setTimeout(() => {
    lookupRequests[kind].debounceId = null;
    runLookup(kind, searchTerm);
  }, LOOKUP_DEBOUNCE_MS);
}

async function runLookup(kind, searchTerm) {
  const requestState = lookupRequests[kind];
  const lookup = getLookupState(kind);
  const controller = new AbortController();
  const input = kind === "supplier"
    ? elements.products.supplierSearchInput
    : elements.products.companySearchInput;

  requestState.controller = controller;
  lookup.isLoading = true;
  lookup.error = "";
  lookup.hasSearched = true;
  renderLookup({ kind });

  try {
    const response = await fetchLookup(kind, searchTerm, controller);

    if (requestState.controller !== controller || input.value.trim() !== searchTerm) {
      return;
    }

    lookup.results = Array.isArray(response?.items) ? response.items : [];
  } catch (error) {
    if (error?.name !== "AbortError") {
      console.error(`Could not search ${kind}:`, error);
      lookup.error = getRequestErrorMessage(error, kind === "supplier" ? "поставщиков" : "компании");
    }
  } finally {
    if (requestState.controller === controller) {
      requestState.controller = null;
      lookup.isLoading = false;
      renderLookup({ kind });
    }
  }
}

async function fetchLookup(kind, searchTerm, controller) {
  return request(buildLookupPath(kind, searchTerm), { signal: controller.signal });
}

function cancelLookup(kind) {
  const requestState = lookupRequests[kind];

  if (requestState.debounceId !== null) {
    window.clearTimeout(requestState.debounceId);
    requestState.debounceId = null;
  }

  if (requestState.controller) {
    requestState.controller.abort();
    requestState.controller = null;
  }
}

function clearSelectedCompany() {
  cancelLookup("company");
  state.productCreate.selectedCompany = null;
  state.productCreate.companyLookup = createLookupState();
  elements.products.companyIdInput.value = "";
  elements.products.companySearchInput.value = "";
  renderLookup({ kind: "company" });
}

function clearSelectedSupplier() {
  cancelLookup("supplier");
  state.productCreate.selectedSupplier = null;
  state.productCreate.supplierLookup = createLookupState();
  elements.products.supplierIdInput.value = "";
  elements.products.supplierSearchInput.value = "";
  renderLookup({ kind: "supplier" });
}

function clearLookupState(kind, hasSearched) {
  const lookup = getLookupState(kind);
  lookup.results = [];
  lookup.error = "";
  lookup.hasSearched = hasSearched;
  renderLookup({ kind });
}

function getLookupState(kind) {
  return kind === "supplier"
    ? state.productCreate.supplierLookup
    : state.productCreate.companyLookup;
}

function resetProductCreateForm() {
  cancelLookup("company");
  cancelLookup("supplier");
  elements.products.form.reset();
  state.productCreate.selectedCompany = null;
  state.productCreate.selectedSupplier = null;
  state.productCreate.companyLookup = createLookupState();
  state.productCreate.supplierLookup = createLookupState();
  state.productCreate.companyMode = "existing";
  state.productCreate.supplierMode = "existing";
  state.productCreate.linkEnabled = false;
  elements.products.companyIdInput.value = "";
  elements.products.supplierIdInput.value = "";
  setCreateError(elements.products.createError);
  syncProductCreateMode();
  renderLookup({ kind: "company" });
  renderLookup({ kind: "supplier" });
}

function syncProductCreateMode() {
  state.productCreate.companyMode = getCheckedValue(elements.products.companyModeInputs);
  state.productCreate.supplierMode = getCheckedValue(elements.products.supplierModeInputs);
  state.productCreate.linkEnabled = elements.products.linkEnabledInput.checked;
  renderProductCreateMode();
  syncPanelControls();
}

function syncPanelControls() {
  setDisabledForPanel(elements.products.companyExistingPanel, state.productCreate.companyMode !== "existing");
  setDisabledForPanel(elements.products.companyNewPanel, state.productCreate.companyMode !== "new");
  setDisabledForPanel(elements.products.supplierSection, !state.productCreate.linkEnabled);
  setDisabledForPanel(
    elements.products.supplierExistingPanel,
    !state.productCreate.linkEnabled || state.productCreate.supplierMode !== "existing",
  );
  setDisabledForPanel(
    elements.products.supplierNewPanel,
    !state.productCreate.linkEnabled || state.productCreate.supplierMode !== "new",
  );
}

function setDisabledForPanel(panel, isDisabled) {
  for (const control of panel.querySelectorAll("input, button, select, textarea")) {
    if (!control.matches("[name='product_company_mode'], [name='product_supplier_mode'], #product-create-link-enabled")) {
      control.disabled = isDisabled || state.productCreate.isSubmitting;
    }
  }
}

function preventEnter(event) {
  if (event.key === "Enter") {
    event.preventDefault();
  }
}

function getCheckedValue(inputs) {
  return inputs.find((input) => input.checked)?.value || "existing";
}

function getText(formData, key) {
  return String(formData.get(key) || "").trim();
}

function getOptionalText(formData, key) {
  return getText(formData, key) || null;
}

function getNumber(formData, key) {
  return Number(getText(formData, key));
}

function getOptionalNumber(formData, key) {
  const value = getText(formData, key);
  return value ? Number(value) : null;
}

function getTags(formData) {
  const tags = getText(formData, "tags");

  if (!tags) {
    return [];
  }

  return tags.split(",").map((tag) => tag.trim()).filter(Boolean);
}

function createLocalValidationError(message) {
  const error = new Error(message);
  error.data = { detail: message };
  return error;
}

function hideModal(modalElement) {
  window.bootstrap?.Modal.getOrCreateInstance(modalElement).hide();
}
