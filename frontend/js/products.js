import {
  FIRST_PAGE,
  buildLookupPath,
  createCompany,
  createProduct,
  createProductSupplierLinks,
  createSupplier,
  getProduct,
  getProducts,
  patchProductSupplierLink,
  patchProduct,
} from "./api.js";
import { elements } from "./dom.js";
import {
  DEFAULT_QUANTITY_UNIT,
  getCreateErrorMessage,
  getRequestErrorMessage,
} from "./format.js";
import {
  renderLookup,
  renderProductDetail,
  renderProductDetailNewLinkLookup,
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
  detailCompany: { controller: null, debounceId: null },
  supplier: { controller: null, debounceId: null },
};
const detailSupplierLookupRequests = new Map();

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

  elements.products.tableBody.addEventListener("click", (event) => {
    const productId = getProductIdFromEvent(event);

    if (productId !== null) {
      openProductDetail(productId);
    }
  });

  elements.products.tableBody.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }

    const productId = getProductIdFromEvent(event);

    if (productId !== null) {
      event.preventDefault();
      openProductDetail(productId);
    }
  });

  elements.products.detailEditButton.addEventListener("click", () => {
    enterProductDetailEdit();
    renderProductDetail();
    elements.products.detailEditNameInput.focus();
  });

  elements.products.detailCancelEditButton.addEventListener("click", () => {
    exitProductDetailEdit();
    renderProductDetail();
  });

  elements.products.detailEditForm.addEventListener("submit", (event) => {
    event.preventDefault();

    if (!elements.products.detailEditForm.reportValidity() || state.productDetail.isSubmitting) {
      return;
    }

    submitProductDetailEdit();
  });

  elements.products.detailModal.addEventListener("hidden.bs.modal", () => {
    resetProductDetail();
  });

  bindProductCreateForm();
  bindProductDetailCompanyLookup();
  bindProductDetailLinkEditing();
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

async function openProductDetail(productId) {
  state.productDetail.id = productId;
  state.productDetail.summary = getProductSummary(productId);
  state.productDetail.data = null;
  state.productDetail.error = "";
  state.productDetail.editError = "";
  state.productDetail.isEditing = false;
  state.productDetail.isSubmitting = false;
  state.productDetail.isLoading = true;
  renderProductDetail();
  showModal(elements.products.detailModal);

  try {
    const product = await getProduct(productId);

    if (state.productDetail.id !== productId) {
      return;
    }

    state.productDetail.data = product;
  } catch (error) {
    if (state.productDetail.id !== productId) {
      return;
    }

    console.error("Could not load product detail:", error);
    state.productDetail.error = getRequestErrorMessage(error, "детали товара");
  } finally {
    if (state.productDetail.id === productId) {
      state.productDetail.isLoading = false;
      renderProductDetail();
    }
  }
}

async function submitProductDetailEdit() {
  const productId = state.productDetail.id;

  if (!productId) {
    return;
  }

  let editData;

  try {
    editData = getProductDetailEditData();
  } catch (error) {
    state.productDetail.editError = getCreateErrorMessage(error, "товар");
    renderProductDetail();
    return;
  }

  state.productDetail.isSubmitting = true;
  state.productDetail.editError = "";
  renderProductDetail();

  try {
    await patchProduct(productId, editData.productPayload);

    const linkRequests = editData.existingLinkUpdates.map((linkUpdate) => (
      patchProductSupplierLink(productId, linkUpdate.linkId, linkUpdate.payload)
    ));

    if (editData.newLinkPayloads.length > 0) {
      linkRequests.push(createProductSupplierLinks(productId, editData.newLinkPayloads));
    }

    if (linkRequests.length > 0) {
      await Promise.all(linkRequests);
    }

    const product = await getProduct(productId);

    if (state.productDetail.id !== productId) {
      return;
    }

    state.productDetail.data = product;
    state.productDetail.isEditing = false;
    state.productDetail.linkEditValues = {};
    state.productDetail.linkDrafts = [];
    state.productDetail.nextLinkDraftId = 1;
    cancelAllDetailSupplierLookups();

    try {
      await Promise.all([
        loadDashboard(),
        loadProducts(state.products.searchTerm, state.products.page),
        loadSuppliers(state.suppliers.searchTerm, state.suppliers.page),
      ]);
      state.productDetail.summary = getProductSummary(productId);
    } catch (refreshError) {
      console.error("Could not refresh products after product update:", refreshError);
      setAppMessage(
        "Товар обновлен, но списки не удалось обновить автоматически.",
        "warning",
      );
    }
  } catch (error) {
    if (state.productDetail.id !== productId) {
      return;
    }

    console.error("Could not update product:", error);
    state.productDetail.editError = getCreateErrorMessage(error, "товар");
  } finally {
    if (state.productDetail.id === productId) {
      state.productDetail.isSubmitting = false;
      renderProductDetail();
    }
  }
}

function bindProductDetailCompanyLookup() {
  elements.products.detailEditCompanySearchInput.addEventListener("keydown", preventEnter);
  elements.products.detailEditCompanySearchInput.addEventListener("input", () => {
    scheduleLookup("detailCompany", elements.products.detailEditCompanySearchInput.value.trim());
  });
  elements.products.detailEditCompanyClearButton.addEventListener("click", () => {
    clearSelectedProductDetailCompany();
    renderProductDetail();
    elements.products.detailEditCompanySearchInput.focus();
  });
  elements.products.detailEditCompanyResults.addEventListener("click", (event) => {
    const button = event.target instanceof Element
      ? event.target.closest("[data-company-id]")
      : null;

    if (!button) {
      return;
    }

    const company = state.productDetail.companyLookup.results.find(
      (item) => String(item.id) === button.dataset.companyId,
    );

    if (company) {
      cancelLookup("detailCompany");
      state.productDetail.selectedCompany = company;
      elements.products.detailEditCompanyIdInput.value = String(company.id);
      elements.products.detailEditCompanySearchInput.value = "";
      state.productDetail.companyLookup = createLookupState();
      state.productDetail.editError = "";
      renderLookup({ kind: "detailCompany" });
      renderProductDetail();
    }
  });
}

function bindProductDetailLinkEditing() {
  elements.products.detailAddLinkButton.addEventListener("click", () => {
    addProductDetailLinkDraft();
  });

  elements.products.detailEditLinksBody.addEventListener("input", (event) => {
    const target = event.target instanceof HTMLInputElement ? event.target : null;

    if (!target || !target.matches("[data-link-field]")) {
      return;
    }

    const row = target.closest("[data-product-link-id]");
    const linkId = Number(row?.dataset.productLinkId || 0);

    if (!Number.isInteger(linkId) || linkId <= 0) {
      return;
    }

    state.productDetail.linkEditValues[linkId] ||= {};
    state.productDetail.linkEditValues[linkId][target.dataset.linkField] = target.value;
  });

  elements.products.detailNewLinks.addEventListener("keydown", (event) => {
    if (
      event.target instanceof Element
      && event.target.matches("[data-new-link-supplier-search]")
    ) {
      preventEnter(event);
    }
  });

  elements.products.detailNewLinks.addEventListener("input", (event) => {
    const target = event.target instanceof HTMLInputElement ? event.target : null;

    if (!target) {
      return;
    }

    const draft = getProductDetailLinkDraftFromElement(target);

    if (!draft) {
      return;
    }

    if (target.matches("[data-new-link-supplier-search]")) {
      draft.searchTerm = target.value;
      scheduleDetailSupplierLookup(draft.id, target.value.trim());
      return;
    }

    if (target.matches("[data-new-link-field]")) {
      draft.values[target.dataset.newLinkField] = target.value;
    }
  });

  elements.products.detailNewLinks.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target : null;

    if (!target) {
      return;
    }

    const removeButton = target.closest("[data-remove-new-link]");
    if (removeButton) {
      const draft = getProductDetailLinkDraftFromElement(removeButton);

      if (draft) {
        removeProductDetailLinkDraft(draft.id);
      }
      return;
    }

    const clearButton = target.closest("[data-clear-new-link-supplier]");
    if (clearButton) {
      const draft = getProductDetailLinkDraftFromElement(clearButton);

      if (draft) {
        clearSelectedDetailLinkSupplier(draft.id);
      }
      return;
    }

    const supplierButton = target.closest("[data-supplier-id]");
    if (supplierButton) {
      const draft = getProductDetailLinkDraftFromElement(supplierButton);
      const supplier = draft?.lookup.results.find(
        (item) => String(item.id) === supplierButton.dataset.supplierId,
      );

      if (draft && supplier) {
        selectDetailLinkSupplier(draft.id, supplier);
      }
    }
  });
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
  const input = getLookupInput(kind);

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

function scheduleDetailSupplierLookup(draftId, searchTerm) {
  const draft = getProductDetailLinkDraft(draftId);

  if (!draft) {
    return;
  }

  cancelDetailSupplierLookup(draftId);
  draft.lookup.isLoading = false;
  draft.lookup.results = [];
  draft.lookup.error = "";
  draft.lookup.hasSearched = false;
  renderProductDetailNewLinkLookup(draftId);

  if (searchTerm.length < LOOKUP_MIN_LENGTH) {
    return;
  }

  const requestState = getDetailSupplierLookupRequest(draftId);
  requestState.debounceId = window.setTimeout(() => {
    requestState.debounceId = null;
    runDetailSupplierLookup(draftId, searchTerm);
  }, LOOKUP_DEBOUNCE_MS);
}

async function runDetailSupplierLookup(draftId, searchTerm) {
  const draft = getProductDetailLinkDraft(draftId);

  if (!draft) {
    return;
  }

  const requestState = getDetailSupplierLookupRequest(draftId);
  const controller = new AbortController();

  requestState.controller = controller;
  draft.lookup.isLoading = true;
  draft.lookup.error = "";
  draft.lookup.hasSearched = true;
  renderProductDetailNewLinkLookup(draftId);

  try {
    const response = await fetchLookup("supplier", searchTerm, controller);
    const currentDraft = getProductDetailLinkDraft(draftId);

    if (
      requestState.controller !== controller
      || !currentDraft
      || currentDraft.searchTerm.trim() !== searchTerm
    ) {
      return;
    }

    currentDraft.lookup.results = Array.isArray(response?.items) ? response.items : [];
  } catch (error) {
    if (error?.name !== "AbortError") {
      console.error("Could not search detail supplier:", error);
      draft.lookup.error = getRequestErrorMessage(error, "поставщиков");
    }
  } finally {
    if (requestState.controller === controller) {
      requestState.controller = null;
      draft.lookup.isLoading = false;
      renderProductDetailNewLinkLookup(draftId);
    }
  }
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

function getDetailSupplierLookupRequest(draftId) {
  const key = Number(draftId);

  if (!detailSupplierLookupRequests.has(key)) {
    detailSupplierLookupRequests.set(key, { controller: null, debounceId: null });
  }

  return detailSupplierLookupRequests.get(key);
}

function cancelDetailSupplierLookup(draftId) {
  const key = Number(draftId);
  const requestState = detailSupplierLookupRequests.get(key);

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

function cancelAllDetailSupplierLookups() {
  for (const draftId of detailSupplierLookupRequests.keys()) {
    cancelDetailSupplierLookup(draftId);
  }

  detailSupplierLookupRequests.clear();
}

function clearSelectedCompany() {
  cancelLookup("company");
  state.productCreate.selectedCompany = null;
  state.productCreate.companyLookup = createLookupState();
  elements.products.companyIdInput.value = "";
  elements.products.companySearchInput.value = "";
  renderLookup({ kind: "company" });
}

function clearSelectedProductDetailCompany() {
  cancelLookup("detailCompany");
  state.productDetail.selectedCompany = null;
  state.productDetail.companyLookup = createLookupState();
  elements.products.detailEditCompanyIdInput.value = "";
  elements.products.detailEditCompanySearchInput.value = "";
  renderLookup({ kind: "detailCompany" });
}

function clearSelectedSupplier() {
  cancelLookup("supplier");
  state.productCreate.selectedSupplier = null;
  state.productCreate.supplierLookup = createLookupState();
  elements.products.supplierIdInput.value = "";
  elements.products.supplierSearchInput.value = "";
  renderLookup({ kind: "supplier" });
}

function addProductDetailLinkDraft() {
  const draft = {
    id: state.productDetail.nextLinkDraftId,
    selectedSupplier: null,
    searchTerm: "",
    lookup: createLookupState(),
    values: {
      purchase_price: "1",
      margin_percent: "0",
      sale_price: "",
      quantity: "0",
    },
  };

  state.productDetail.nextLinkDraftId += 1;
  state.productDetail.linkDrafts.push(draft);
  renderProductDetail();
  elements.products.detailNewLinks
    .querySelector(`[data-link-draft-id="${draft.id}"] [data-new-link-supplier-search]`)
    ?.focus();
}

function removeProductDetailLinkDraft(draftId) {
  cancelDetailSupplierLookup(draftId);
  detailSupplierLookupRequests.delete(Number(draftId));
  state.productDetail.linkDrafts = state.productDetail.linkDrafts.filter(
    (draft) => Number(draft.id) !== Number(draftId),
  );
  renderProductDetail();
}

function selectDetailLinkSupplier(draftId, supplier) {
  const draft = getProductDetailLinkDraft(draftId);

  if (!draft) {
    return;
  }

  cancelDetailSupplierLookup(draftId);
  draft.selectedSupplier = supplier;
  draft.searchTerm = "";
  draft.lookup = createLookupState();
  state.productDetail.editError = "";
  renderProductDetail();
}

function clearSelectedDetailLinkSupplier(draftId) {
  const draft = getProductDetailLinkDraft(draftId);

  if (!draft) {
    return;
  }

  cancelDetailSupplierLookup(draftId);
  draft.selectedSupplier = null;
  draft.searchTerm = "";
  draft.lookup = createLookupState();
  renderProductDetail();
  elements.products.detailNewLinks
    .querySelector(`[data-link-draft-id="${draftId}"] [data-new-link-supplier-search]`)
    ?.focus();
}

function clearLookupState(kind, hasSearched) {
  const lookup = getLookupState(kind);
  lookup.results = [];
  lookup.error = "";
  lookup.hasSearched = hasSearched;
  renderLookup({ kind });
}

function getLookupState(kind) {
  if (kind === "supplier") {
    return state.productCreate.supplierLookup;
  }

  if (kind === "detailCompany") {
    return state.productDetail.companyLookup;
  }

  return state.productCreate.companyLookup;
}

function getLookupInput(kind) {
  if (kind === "supplier") {
    return elements.products.supplierSearchInput;
  }

  if (kind === "detailCompany") {
    return elements.products.detailEditCompanySearchInput;
  }

  return elements.products.companySearchInput;
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

function resetProductDetail() {
  cancelLookup("detailCompany");
  cancelAllDetailSupplierLookups();
  state.productDetail.data = null;
  state.productDetail.summary = null;
  state.productDetail.id = null;
  state.productDetail.selectedCompany = null;
  state.productDetail.companyLookup = createLookupState();
  state.productDetail.linkEditValues = {};
  state.productDetail.linkDrafts = [];
  state.productDetail.nextLinkDraftId = 1;
  state.productDetail.error = "";
  state.productDetail.editError = "";
  state.productDetail.isEditing = false;
  state.productDetail.isSubmitting = false;
  state.productDetail.isLoading = false;
  elements.products.detailEditCompanyIdInput.value = "";
  elements.products.detailEditCompanySearchInput.value = "";
  renderProductDetail();
}

function enterProductDetailEdit() {
  const product = state.productDetail.data;

  if (!product) {
    return;
  }

  const unit = String(product.quantity_unit || "").trim() || DEFAULT_QUANTITY_UNIT;
  const selectedCompany = product.company_id
    ? {
        id: product.company_id,
        name: product.company_name || `Компания #${product.company_id}`,
      }
    : null;

  cancelLookup("detailCompany");
  cancelAllDetailSupplierLookups();
  state.productDetail.selectedCompany = selectedCompany;
  state.productDetail.companyLookup = createLookupState();
  state.productDetail.linkEditValues = getProductSupplierLinkEditValues(product);
  state.productDetail.linkDrafts = [];
  state.productDetail.nextLinkDraftId = 1;
  state.productDetail.isEditing = true;
  state.productDetail.editError = "";
  elements.products.detailEditNameInput.value = product.name || "";
  elements.products.detailEditCompanyIdInput.value = selectedCompany
    ? String(selectedCompany.id)
    : "";
  elements.products.detailEditCompanySearchInput.value = "";
  elements.products.detailEditUnitInput.value = unit;
  elements.products.detailEditThresholdInput.value = String(product.low_stock_threshold ?? 0);
  elements.products.detailEditTagsInput.value = getTagNames(product.tags).join(", ");
}

function exitProductDetailEdit() {
  cancelLookup("detailCompany");
  cancelAllDetailSupplierLookups();
  state.productDetail.isEditing = false;
  state.productDetail.editError = "";
  state.productDetail.selectedCompany = null;
  state.productDetail.companyLookup = createLookupState();
  state.productDetail.linkEditValues = {};
  state.productDetail.linkDrafts = [];
  state.productDetail.nextLinkDraftId = 1;
  elements.products.detailEditCompanyIdInput.value = "";
  elements.products.detailEditCompanySearchInput.value = "";
}

function getProductDetailEditData() {
  const productPayload = getProductDetailEditPayload();
  const existingLinkUpdates = getProductDetailExistingLinkUpdates();
  const newLinkPayloads = getProductDetailNewLinkPayloads();

  validateProductDetailNewLinkSuppliers(newLinkPayloads);

  return {
    productPayload,
    existingLinkUpdates,
    newLinkPayloads,
  };
}

function getProductDetailEditPayload() {
  const formData = new FormData(elements.products.detailEditForm);
  const companyId = Number(
    state.productDetail.selectedCompany?.id
      || elements.products.detailEditCompanyIdInput.value
      || 0,
  );

  if (!Number.isInteger(companyId) || companyId <= 0) {
    throw createLocalValidationError("Выберите компанию.");
  }

  return {
    name: getText(formData, "name"),
    company_id: companyId,
    quantity_unit: getText(formData, "quantity_unit") || DEFAULT_QUANTITY_UNIT,
    low_stock_threshold: getNumber(formData, "low_stock_threshold"),
    tags: getTags(formData),
  };
}

function getProductDetailExistingLinkUpdates() {
  const supplierLinks = getCurrentProductSupplierLinks();
  const linksById = new Map(
    supplierLinks.map((supplierLink) => [Number(supplierLink.id), supplierLink]),
  );
  const updates = [];

  for (const row of elements.products.detailEditLinksBody.querySelectorAll("[data-product-link-id]")) {
    const linkId = Number(row.dataset.productLinkId || 0);
    const originalLink = linksById.get(linkId);

    if (!Number.isInteger(linkId) || linkId <= 0 || !originalLink) {
      continue;
    }

    const payload = {
      purchase_price: getLinkInputNumber(row, "purchase_price"),
      margin_percent: getLinkInputNumber(row, "margin_percent"),
      sale_price: getLinkInputNumber(row, "sale_price"),
      quantity: getLinkInputNumber(row, "quantity"),
    };

    if (hasProductSupplierLinkChanged(originalLink, payload)) {
      updates.push({ linkId, payload });
    }
  }

  return updates;
}

function getProductDetailNewLinkPayloads() {
  return state.productDetail.linkDrafts.map((draft) => {
    if (!draft.selectedSupplier) {
      throw createLocalValidationError("Выберите поставщика для новой связи.");
    }

    const wrapper = elements.products.detailNewLinks.querySelector(
      `[data-link-draft-id="${draft.id}"]`,
    );

    if (!wrapper) {
      throw createLocalValidationError("Новая связь с поставщиком не найдена в форме.");
    }

    const payload = {
      supplier_id: Number(draft.selectedSupplier.id),
      purchase_price: getDraftInputNumber(wrapper, "purchase_price"),
      margin_percent: getDraftInputNumber(wrapper, "margin_percent"),
      quantity: getDraftInputNumber(wrapper, "quantity"),
    };
    const salePrice = getDraftInputOptionalNumber(wrapper, "sale_price");

    if (salePrice !== null) {
      payload.sale_price = salePrice;
    }

    return payload;
  });
}

function validateProductDetailNewLinkSuppliers(newLinkPayloads) {
  const supplierIds = new Set(
    getCurrentProductSupplierLinks().map((supplierLink) => Number(supplierLink.supplier_id)),
  );

  for (const payload of newLinkPayloads) {
    if (!Number.isInteger(payload.supplier_id) || payload.supplier_id <= 0) {
      throw createLocalValidationError("Выберите поставщика для новой связи.");
    }

    if (supplierIds.has(payload.supplier_id)) {
      throw createLocalValidationError("Поставщик уже связан с этим товаром.");
    }

    supplierIds.add(payload.supplier_id);
  }
}

function getCurrentProductSupplierLinks() {
  const supplierLinks = state.productDetail.data?.supplier_links;

  return Array.isArray(supplierLinks) ? supplierLinks : [];
}

function getProductSupplierLinkEditValues(product) {
  const values = {};
  const supplierLinks = Array.isArray(product?.supplier_links)
    ? product.supplier_links
    : [];

  for (const supplierLink of supplierLinks) {
    values[supplierLink.id] = {
      purchase_price: String(supplierLink.purchase_price ?? ""),
      margin_percent: String(supplierLink.margin_percent ?? ""),
      sale_price: String(supplierLink.sale_price ?? ""),
      quantity: String(supplierLink.quantity ?? ""),
    };
  }

  return values;
}

function getLinkInputNumber(row, field) {
  const input = row.querySelector(`[data-link-field="${field}"]`);

  return getElementNumber(input);
}

function getDraftInputNumber(wrapper, field) {
  const input = wrapper.querySelector(`[data-new-link-field="${field}"]`);

  return getElementNumber(input);
}

function getDraftInputOptionalNumber(wrapper, field) {
  const input = wrapper.querySelector(`[data-new-link-field="${field}"]`);
  const value = String(input?.value || "").trim();

  return value ? getElementNumber(input) : null;
}

function getElementNumber(input) {
  const value = Number(input?.value || "");

  if (!Number.isInteger(value)) {
    throw createLocalValidationError("Числовые поля должны быть целыми числами.");
  }

  return value;
}

function hasProductSupplierLinkChanged(originalLink, payload) {
  return (
    Number(originalLink.purchase_price) !== payload.purchase_price
    || Number(originalLink.margin_percent) !== payload.margin_percent
    || Number(originalLink.sale_price) !== payload.sale_price
    || Number(originalLink.quantity) !== payload.quantity
  );
}

function getProductDetailLinkDraftFromElement(element) {
  const wrapper = element.closest("[data-link-draft-id]");
  const draftId = Number(wrapper?.dataset.linkDraftId || 0);

  return getProductDetailLinkDraft(draftId);
}

function getProductDetailLinkDraft(draftId) {
  return state.productDetail.linkDrafts.find(
    (draft) => Number(draft.id) === Number(draftId),
  ) || null;
}

function getProductIdFromEvent(event) {
  const row = event.target instanceof Element
    ? event.target.closest("[data-product-id]")
    : null;
  const productId = Number(row?.dataset.productId || 0);

  return Number.isInteger(productId) && productId > 0 ? productId : null;
}

function getProductSummary(productId) {
  return state.products.items.find((product) => Number(product.id) === productId) || null;
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

function getTagNames(tags) {
  if (!Array.isArray(tags)) {
    return [];
  }

  return tags
    .map((tag) => {
      if (typeof tag === "string") {
        return tag.trim();
      }

      return String(tag?.name || "").trim();
    })
    .filter(Boolean);
}

function createLocalValidationError(message) {
  const error = new Error(message);
  error.data = { detail: message };
  return error;
}

function hideModal(modalElement) {
  window.bootstrap?.Modal.getOrCreateInstance(modalElement).hide();
}

function showModal(modalElement) {
  window.bootstrap?.Modal.getOrCreateInstance(modalElement).show();
}
