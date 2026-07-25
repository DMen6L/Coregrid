import { FIRST_PAGE, createSupplier, getSuppliers } from "./api.js";
import { elements } from "./dom.js";
import { getCreateErrorMessage, getRequestErrorMessage } from "./format.js";
import { setCreateError, setSubmitting, renderSuppliers } from "./render.js";
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

export function getSupplierCreatePayload(form = elements.suppliers.form) {
  const formData = new FormData(form);

  return {
    name: getText(formData, "name"),
    phone_number: getText(formData, "phone_number"),
  };
}

function resetSupplierCreateForm() {
  elements.suppliers.form.reset();
  setCreateError(elements.suppliers.createError);
}

function getText(formData, key) {
  return String(formData.get(key) || "").trim();
}

function hideModal(modalElement) {
  window.bootstrap?.Modal.getOrCreateInstance(modalElement).hide();
}
