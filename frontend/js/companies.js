import {
  FIRST_PAGE,
  createCompany,
  getCompanies,
  getCompany,
  patchCompany,
} from "./api.js";
import { elements } from "./dom.js";
import { getCreateErrorMessage, getRequestErrorMessage } from "./format.js";
import {
  renderCompanies,
  renderCompanyDetail,
  setAppMessage,
  setCreateError,
  setSubmitting,
} from "./render.js";
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

  elements.companies.tableBody.addEventListener("click", (event) => {
    const companyId = getCompanyIdFromEvent(event);

    if (companyId !== null) {
      openCompanyDetail(companyId);
    }
  });

  elements.companies.tableBody.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }

    const companyId = getCompanyIdFromEvent(event);

    if (companyId !== null) {
      event.preventDefault();
      openCompanyDetail(companyId);
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

  elements.companies.detailEditButton.addEventListener("click", () => {
    enterCompanyDetailEdit();
    renderCompanyDetail();
    elements.companies.detailEditNameInput.focus();
  });

  elements.companies.detailCancelEditButton.addEventListener("click", () => {
    exitCompanyDetailEdit();
    renderCompanyDetail();
  });

  elements.companies.detailEditForm.addEventListener("submit", (event) => {
    event.preventDefault();

    if (!elements.companies.detailEditForm.reportValidity() || state.companyDetail.isSubmitting) {
      return;
    }

    submitCompanyDetailEdit();
  });

  elements.companies.detailModal.addEventListener("hidden.bs.modal", () => {
    resetCompanyDetail();
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

async function openCompanyDetail(companyId) {
  state.companyDetail.id = companyId;
  state.companyDetail.data = null;
  state.companyDetail.error = "";
  state.companyDetail.editError = "";
  state.companyDetail.isEditing = false;
  state.companyDetail.isSubmitting = false;
  state.companyDetail.isLoading = true;
  renderCompanyDetail();
  showModal(elements.companies.detailModal);

  try {
    const company = await getCompany(companyId);

    if (state.companyDetail.id !== companyId) {
      return;
    }

    state.companyDetail.data = company;
  } catch (error) {
    if (state.companyDetail.id !== companyId) {
      return;
    }

    console.error("Could not load company detail:", error);
    state.companyDetail.error = getRequestErrorMessage(error, "детали компании");
  } finally {
    if (state.companyDetail.id === companyId) {
      state.companyDetail.isLoading = false;
      renderCompanyDetail();
    }
  }
}

async function submitCompanyDetailEdit() {
  const companyId = state.companyDetail.id;

  if (!companyId) {
    return;
  }

  const payload = getCompanyUpdatePayload();

  state.companyDetail.isSubmitting = true;
  state.companyDetail.editError = "";
  renderCompanyDetail();

  try {
    const company = await patchCompany(companyId, payload);

    if (state.companyDetail.id !== companyId) {
      return;
    }

    state.companyDetail.data = company;
    state.companyDetail.isEditing = false;

    try {
      await loadCompanies(state.companies.searchTerm, state.companies.page);
    } catch (refreshError) {
      console.error("Could not refresh companies after company update:", refreshError);
      setAppMessage(
        "Компания обновлена, но список не удалось обновить автоматически.",
        "warning",
      );
    }
  } catch (error) {
    if (state.companyDetail.id !== companyId) {
      return;
    }

    console.error("Could not update company:", error);
    state.companyDetail.editError = getCreateErrorMessage(error, "компанию");
  } finally {
    if (state.companyDetail.id === companyId) {
      state.companyDetail.isSubmitting = false;
      renderCompanyDetail();
    }
  }
}

export function getCompanyCreatePayload(form = elements.companies.form) {
  const formData = new FormData(form);

  return {
    name: getText(formData, "name"),
    iin: getOptionalText(formData, "iin"),
  };
}

function getCompanyUpdatePayload() {
  const formData = new FormData(elements.companies.detailEditForm);

  return {
    name: getText(formData, "name"),
    iin: getOptionalText(formData, "iin"),
  };
}

function resetCompanyCreateForm() {
  elements.companies.form.reset();
  setCreateError(elements.companies.createError);
}

function resetCompanyDetail() {
  state.companyDetail.data = null;
  state.companyDetail.id = null;
  state.companyDetail.error = "";
  state.companyDetail.editError = "";
  state.companyDetail.isEditing = false;
  state.companyDetail.isSubmitting = false;
  state.companyDetail.isLoading = false;
  renderCompanyDetail();
}

function enterCompanyDetailEdit() {
  const company = state.companyDetail.data;

  if (!company) {
    return;
  }

  state.companyDetail.isEditing = true;
  state.companyDetail.editError = "";
  elements.companies.detailEditNameInput.value = company.name || "";
  elements.companies.detailEditIinInput.value = company.iin || "";
}

function exitCompanyDetailEdit() {
  state.companyDetail.isEditing = false;
  state.companyDetail.editError = "";
}

function getCompanyIdFromEvent(event) {
  const row = event.target instanceof Element
    ? event.target.closest("[data-company-id]")
    : null;
  const companyId = Number(row?.dataset.companyId || 0);

  return Number.isInteger(companyId) && companyId > 0 ? companyId : null;
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

function showModal(modalElement) {
  window.bootstrap?.Modal.getOrCreateInstance(modalElement).show();
}
