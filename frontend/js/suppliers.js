import {
  FIRST_PAGE,
  createSupplier,
  getSupplier,
  getSuppliers,
  patchSupplier,
} from "./api.js";
import { elements } from "./dom.js";
import { getCreateErrorMessage, getRequestErrorMessage } from "./format.js";
import {
  renderSupplierDetail,
  renderSuppliers,
  setAppMessage,
  setCreateError,
  setSubmitting,
} from "./render.js";
import { applyPage, resetPage, state } from "./state.js";

export function bindSuppliersFeature() {
  elements.suppliers.searchForm.addEventListener("submit", (event) => {
    event.preventDefault();
    loadSuppliers(elements.suppliers.searchInput.value.trim(), FIRST_PAGE);
  });

  elements.suppliers.previousPageButton.addEventListener("click", () => {
    if (!elements.suppliers.previousPageButton.disabled) {
      loadSuppliers(state.suppliers.searchTerm, state.suppliers.page - 1);
    }
  });

  elements.suppliers.nextPageButton.addEventListener("click", () => {
    if (!elements.suppliers.nextPageButton.disabled) {
      loadSuppliers(state.suppliers.searchTerm, state.suppliers.page + 1);
    }
  });

  elements.suppliers.tableBody.addEventListener("click", (event) => {
    const supplierId = getSupplierIdFromEvent(event);

    if (supplierId !== null) {
      openSupplierDetail(supplierId);
    }
  });

  elements.suppliers.tableBody.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }

    const supplierId = getSupplierIdFromEvent(event);

    if (supplierId !== null) {
      event.preventDefault();
      openSupplierDetail(supplierId);
    }
  });

  elements.suppliers.form.addEventListener("submit", (event) => {
    event.preventDefault();

    if (!elements.suppliers.form.reportValidity() || state.supplierCreate.isSubmitting) {
      return;
    }

    submitSupplierCreate();
  });

  elements.suppliers.modal.addEventListener("hidden.bs.modal", () => {
    if (!state.supplierCreate.isSubmitting) {
      resetSupplierCreateForm();
    }
  });

  elements.suppliers.detailEditButton.addEventListener("click", () => {
    enterSupplierDetailEdit();
    renderSupplierDetail();
    elements.suppliers.detailEditNameInput.focus();
  });

  elements.suppliers.detailCancelEditButton.addEventListener("click", () => {
    exitSupplierDetailEdit();
    renderSupplierDetail();
  });

  elements.suppliers.detailEditForm.addEventListener("submit", (event) => {
    event.preventDefault();

    if (!elements.suppliers.detailEditForm.reportValidity() || state.supplierDetail.isSubmitting) {
      return;
    }

    submitSupplierDetailEdit();
  });

  elements.suppliers.detailModal.addEventListener("hidden.bs.modal", () => {
    resetSupplierDetail();
  });
}

export async function loadSuppliers(searchTerm = "", page = FIRST_PAGE) {
  state.suppliers.isLoading = true;
  state.suppliers.searchTerm = searchTerm;
  state.suppliers.error = "";
  renderSuppliers();

  try {
    const response = await getSuppliers({ search: searchTerm, page });
    applyPage(state.suppliers, response, page);
  } catch (error) {
    console.error("Could not load suppliers:", error);
    resetPage(state.suppliers, page);
    state.suppliers.error = getRequestErrorMessage(error, "поставщиков");
  } finally {
    state.suppliers.isLoading = false;
    renderSuppliers();
  }
}

async function submitSupplierCreate() {
  const payload = getSupplierCreatePayload();

  state.supplierCreate.isSubmitting = true;
  setCreateError(elements.suppliers.createError);
  setSubmitting(elements.suppliers.form, true);

  try {
    await createSupplier(payload);
    hideModal(elements.suppliers.modal);
    resetSupplierCreateForm();
    await loadSuppliers(state.suppliers.searchTerm, state.suppliers.page);
  } catch (error) {
    console.error("Could not create supplier:", error);
    setCreateError(elements.suppliers.createError, getCreateErrorMessage(error, "поставщика"));
  } finally {
    state.supplierCreate.isSubmitting = false;
    setSubmitting(elements.suppliers.form, false);
  }
}

async function openSupplierDetail(supplierId) {
  state.supplierDetail.id = supplierId;
  state.supplierDetail.data = null;
  state.supplierDetail.error = "";
  state.supplierDetail.editError = "";
  state.supplierDetail.isEditing = false;
  state.supplierDetail.isSubmitting = false;
  state.supplierDetail.isLoading = true;
  renderSupplierDetail();
  showModal(elements.suppliers.detailModal);

  try {
    const supplier = await getSupplier(supplierId);

    if (state.supplierDetail.id !== supplierId) {
      return;
    }

    state.supplierDetail.data = supplier;
  } catch (error) {
    if (state.supplierDetail.id !== supplierId) {
      return;
    }

    console.error("Could not load supplier detail:", error);
    state.supplierDetail.error = getRequestErrorMessage(error, "детали поставщика");
  } finally {
    if (state.supplierDetail.id === supplierId) {
      state.supplierDetail.isLoading = false;
      renderSupplierDetail();
    }
  }
}

async function submitSupplierDetailEdit() {
  const supplierId = state.supplierDetail.id;

  if (!supplierId) {
    return;
  }

  const payload = getSupplierUpdatePayload();

  state.supplierDetail.isSubmitting = true;
  state.supplierDetail.editError = "";
  renderSupplierDetail();

  try {
    const supplier = await patchSupplier(supplierId, payload);

    if (state.supplierDetail.id !== supplierId) {
      return;
    }

    state.supplierDetail.data = supplier;
    state.supplierDetail.isEditing = false;

    try {
      await loadSuppliers(state.suppliers.searchTerm, state.suppliers.page);
    } catch (refreshError) {
      console.error("Could not refresh suppliers after supplier update:", refreshError);
      setAppMessage(
        "Поставщик обновлен, но список не удалось обновить автоматически.",
        "warning",
      );
    }
  } catch (error) {
    if (state.supplierDetail.id !== supplierId) {
      return;
    }

    console.error("Could not update supplier:", error);
    state.supplierDetail.editError = getCreateErrorMessage(error, "поставщика");
  } finally {
    if (state.supplierDetail.id === supplierId) {
      state.supplierDetail.isSubmitting = false;
      renderSupplierDetail();
    }
  }
}

export function getSupplierCreatePayload(form = elements.suppliers.form) {
  const formData = new FormData(form);

  return {
    name: getText(formData, "name"),
    phone_number: getText(formData, "phone_number"),
  };
}

function getSupplierUpdatePayload() {
  const formData = new FormData(elements.suppliers.detailEditForm);

  return {
    name: getText(formData, "name"),
    phone_number: getText(formData, "phone_number"),
  };
}

function resetSupplierCreateForm() {
  elements.suppliers.form.reset();
  setCreateError(elements.suppliers.createError);
}

function resetSupplierDetail() {
  state.supplierDetail.data = null;
  state.supplierDetail.id = null;
  state.supplierDetail.error = "";
  state.supplierDetail.editError = "";
  state.supplierDetail.isEditing = false;
  state.supplierDetail.isSubmitting = false;
  state.supplierDetail.isLoading = false;
  renderSupplierDetail();
}

function enterSupplierDetailEdit() {
  const supplier = state.supplierDetail.data;

  if (!supplier) {
    return;
  }

  state.supplierDetail.isEditing = true;
  state.supplierDetail.editError = "";
  elements.suppliers.detailEditNameInput.value = supplier.name || "";
  elements.suppliers.detailEditPhoneInput.value = supplier.phone_number || "";
}

function exitSupplierDetailEdit() {
  state.supplierDetail.isEditing = false;
  state.supplierDetail.editError = "";
}

function getSupplierIdFromEvent(event) {
  const row = event.target instanceof Element
    ? event.target.closest("[data-supplier-id]")
    : null;
  const supplierId = Number(row?.dataset.supplierId || 0);

  return Number.isInteger(supplierId) && supplierId > 0 ? supplierId : null;
}

function getText(formData, key) {
  return String(formData.get(key) || "").trim();
}

function hideModal(modalElement) {
  window.bootstrap?.Modal.getOrCreateInstance(modalElement).hide();
}

function showModal(modalElement) {
  window.bootstrap?.Modal.getOrCreateInstance(modalElement).show();
}
