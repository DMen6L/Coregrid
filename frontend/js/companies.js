import { FIRST_PAGE, createCompany, getCompanies } from "./api.js";
import { elements } from "./dom.js";
import { getCreateErrorMessage, getRequestErrorMessage } from "./format.js";
import { setCreateError, setSubmitting, renderCompanies } from "./render.js";
import { applyPage, resetPage, state } from "./state.js";

export function bindCompaniesFeature() {
  elements.companies.searchForm.addEventListener("submit", (event) => {
    event.preventDefault();
    loadCompanies(elements.companies.searchInput.value.trim(), FIRST_PAGE);
  });

  elements.companies.previousPageButton.addEventListener("click", () => {
    if (!elements.companies.previousPageButton.disabled) {
      loadCompanies(state.companies.searchTerm, state.companies.page - 1);
    }
  });

  elements.companies.nextPageButton.addEventListener("click", () => {
    if (!elements.companies.nextPageButton.disabled) {
      loadCompanies(state.companies.searchTerm, state.companies.page + 1);
    }
  });

  elements.companies.form.addEventListener("submit", (event) => {
    event.preventDefault();

    if (!elements.companies.form.reportValidity() || state.companyCreate.isSubmitting) {
      return;
    }

    submitCompanyCreate();
  });

  elements.companies.modal.addEventListener("hidden.bs.modal", () => {
    if (!state.companyCreate.isSubmitting) {
      resetCompanyCreateForm();
    }
  });
}

export async function loadCompanies(searchTerm = "", page = FIRST_PAGE) {
  state.companies.isLoading = true;
  state.companies.searchTerm = searchTerm;
  state.companies.error = "";
  renderCompanies();

  try {
    const response = await getCompanies({ search: searchTerm, page });
    applyPage(state.companies, response, page);
  } catch (error) {
    console.error("Could not load companies:", error);
    resetPage(state.companies, page);
    state.companies.error = getRequestErrorMessage(error, "компании");
  } finally {
    state.companies.isLoading = false;
    renderCompanies();
  }
}

async function submitCompanyCreate() {
  const payload = getCompanyCreatePayload();

  state.companyCreate.isSubmitting = true;
  setCreateError(elements.companies.createError);
  setSubmitting(elements.companies.form, true);

  try {
    await createCompany(payload);
    hideModal(elements.companies.modal);
    resetCompanyCreateForm();
    await loadCompanies(state.companies.searchTerm, state.companies.page);
  } catch (error) {
    console.error("Could not create company:", error);
    setCreateError(elements.companies.createError, getCreateErrorMessage(error, "компанию"));
  } finally {
    state.companyCreate.isSubmitting = false;
    setSubmitting(elements.companies.form, false);
  }
}

export function getCompanyCreatePayload(form = elements.companies.form) {
  const formData = new FormData(form);

  return {
    name: getText(formData, "name"),
    iin: getOptionalText(formData, "iin"),
  };
}

function resetCompanyCreateForm() {
  elements.companies.form.reset();
  setCreateError(elements.companies.createError);
}

function getText(formData, key) {
  return String(formData.get(key) || "").trim();
}

function getOptionalText(formData, key) {
  return getText(formData, key) || null;
}

function hideModal(modalElement) {
  window.bootstrap?.Modal.getOrCreateInstance(modalElement).hide();
}
