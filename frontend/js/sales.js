import { FIRST_PAGE, createSale, getSales } from "./api.js";
import { elements } from "./dom.js";
import { getCreateErrorMessage, getRequestErrorMessage } from "./format.js";
import {
  bindOperationLinePicker,
  createOperationLineElement,
  validateOperationLines,
} from "./operationLinePicker.js";
import { renderSales, setCreateError, setSubmitting } from "./render.js";
import { applyPage, resetPage, state } from "./state.js";
import { loadDashboard } from "./dashboard.js";
import { loadProducts } from "./products.js";

let nextSaleLineId = 1;

export function bindSalesFeature() {
  elements.sales.filterForm.addEventListener("submit", (event) => {
    event.preventDefault();
    loadSales({
      dateFrom: elements.sales.dateFromInput.value,
      dateTo: elements.sales.dateToInput.value,
      page: FIRST_PAGE,
    });
  });

  elements.sales.resetButton.addEventListener("click", () => {
    elements.sales.dateFromInput.value = "";
    elements.sales.dateToInput.value = "";
    loadSales({ dateFrom: "", dateTo: "", page: FIRST_PAGE });
  });

  elements.sales.previousPageButton.addEventListener("click", () => {
    if (!elements.sales.previousPageButton.disabled) {
      loadSales({ page: state.sales.page - 1 });
    }
  });

  elements.sales.nextPageButton.addEventListener("click", () => {
    if (!elements.sales.nextPageButton.disabled) {
      loadSales({ page: state.sales.page + 1 });
    }
  });

  elements.sales.addLineButton.addEventListener("click", () => {
    addSaleLine();
  });
  bindOperationLinePicker(elements.sales.linesContainer, { kind: "sale" });

  elements.sales.linesContainer.addEventListener("click", (event) => {
    const button = event.target instanceof Element
      ? event.target.closest("[data-remove-sale-line]")
      : null;

    if (button) {
      button.closest(".sale-create-line")?.remove();
    }
  });

  elements.sales.form.addEventListener("submit", (event) => {
    event.preventDefault();

    if (state.saleCreate.isSubmitting) {
      return;
    }

    submitSaleCreate();
  });

  elements.sales.modal.addEventListener("show.bs.modal", () => {
    if (!elements.sales.linesContainer.children.length) {
      addSaleLine();
    }
  });

  elements.sales.modal.addEventListener("hidden.bs.modal", () => {
    if (!state.saleCreate.isSubmitting) {
      resetSaleCreateForm();
    }
  });
}

export async function loadSales({
  dateFrom = state.sales.dateFrom,
  dateTo = state.sales.dateTo,
  page = FIRST_PAGE,
} = {}) {
  state.sales.isLoading = true;
  state.sales.dateFrom = dateFrom;
  state.sales.dateTo = dateTo;
  state.sales.searchTerm = dateFrom || dateTo ? "filtered" : "";
  state.sales.error = "";
  renderSales();

  try {
    const response = await getSales({ dateFrom, dateTo, page });
    applyPage(state.sales, response, page);
  } catch (error) {
    console.error("Could not load sales:", error);
    resetPage(state.sales, page);
    state.sales.error = getRequestErrorMessage(error, "продажи");
  } finally {
    state.sales.isLoading = false;
    renderSales();
  }
}

function addSaleLine() {
  elements.sales.linesContainer.append(createSaleLineElement());
}

function createSaleLineElement() {
  const lineId = nextSaleLineId;
  nextSaleLineId += 1;

  return createOperationLineElement({
    lineId,
    kind: "sale",
    quantityName: "sale_quantity",
    quantityLabel: "Количество продажи",
  });
}

async function submitSaleCreate() {
  const validationMessage = validateOperationLines(
    elements.sales.linesContainer,
    "продажи",
  );

  if (validationMessage) {
    setCreateError(elements.sales.createError, validationMessage);
    return;
  }

  if (!elements.sales.form.reportValidity()) {
    return;
  }

  const payload = getSaleCreatePayload();

  if (!payload.lines.length) {
    setCreateError(elements.sales.createError, "Добавьте хотя бы одну позицию.");
    return;
  }

  state.saleCreate.isSubmitting = true;
  setCreateError(elements.sales.createError);
  setSubmitting(elements.sales.form, true);

  try {
    await createSale(payload);
    hideModal(elements.sales.modal);
    resetSaleCreateForm();
    await Promise.all([
      loadDashboard(),
      loadSales({ page: state.sales.page }),
      loadProducts(state.products.searchTerm, state.products.page),
    ]);
  } catch (error) {
    console.error("Could not create sale:", error);
    setCreateError(elements.sales.createError, getCreateErrorMessage(error, "продажу"));
  } finally {
    state.saleCreate.isSubmitting = false;
    setSubmitting(elements.sales.form, false);
  }
}

function getSaleCreatePayload() {
  const formData = new FormData(elements.sales.form);

  return {
    note: getText(formData, "note") || null,
    lines: Array.from(elements.sales.linesContainer.querySelectorAll(".sale-create-line"))
      .map(getSaleLinePayload),
  };
}

function getSaleLinePayload(lineElement) {
  const formData = new FormData();

  for (const control of lineElement.querySelectorAll("input, select")) {
    if (control.name) {
      formData.set(control.name, control.value);
    }
  }

  return {
    product_supplier_id: getNumber(formData, "product_supplier_id"),
    sale_quantity: getNumber(formData, "sale_quantity"),
  };
}

function resetSaleCreateForm() {
  elements.sales.form.reset();
  elements.sales.linesContainer.replaceChildren();
  nextSaleLineId = 1;
  setCreateError(elements.sales.createError);
}

function getText(formData, key) {
  return String(formData.get(key) || "").trim();
}

function getNumber(formData, key) {
  return Number(formData.get(key));
}

function hideModal(modalElement) {
  window.bootstrap?.Modal.getOrCreateInstance(modalElement).hide();
}
