import { FIRST_PAGE, createRestock, getRestocks } from "./api.js";
import { elements } from "./dom.js";
import { getCreateErrorMessage, getRequestErrorMessage } from "./format.js";
import {
  bindOperationLinePicker,
  createOperationLineElement,
  validateOperationLines,
} from "./operationLinePicker.js";
import { renderRestocks, setCreateError, setSubmitting } from "./render.js";
import { applyPage, resetPage, state } from "./state.js";
import { loadDashboard } from "./dashboard.js";
import { loadProducts } from "./products.js";

let nextRestockLineId = 1;

export function bindRestocksFeature() {
  elements.restocks.filterForm.addEventListener("submit", (event) => {
    event.preventDefault();
    loadRestocks({
      dateFrom: elements.restocks.dateFromInput.value,
      dateTo: elements.restocks.dateToInput.value,
      page: FIRST_PAGE,
    });
  });

  elements.restocks.resetButton.addEventListener("click", () => {
    elements.restocks.dateFromInput.value = "";
    elements.restocks.dateToInput.value = "";
    loadRestocks({ dateFrom: "", dateTo: "", page: FIRST_PAGE });
  });

  elements.restocks.previousPageButton.addEventListener("click", () => {
    if (!elements.restocks.previousPageButton.disabled) {
      loadRestocks({ page: state.restocks.page - 1 });
    }
  });

  elements.restocks.nextPageButton.addEventListener("click", () => {
    if (!elements.restocks.nextPageButton.disabled) {
      loadRestocks({ page: state.restocks.page + 1 });
    }
  });

  elements.restocks.addLineButton.addEventListener("click", () => {
    addRestockLine();
  });
  bindOperationLinePicker(elements.restocks.linesContainer, { kind: "restock" });

  elements.restocks.linesContainer.addEventListener("click", (event) => {
    const button = event.target instanceof Element
      ? event.target.closest("[data-remove-restock-line]")
      : null;

    if (button) {
      button.closest(".restock-create-line")?.remove();
    }
  });

  elements.restocks.form.addEventListener("submit", (event) => {
    event.preventDefault();

    if (state.restockCreate.isSubmitting) {
      return;
    }

    submitRestockCreate();
  });

  elements.restocks.modal.addEventListener("show.bs.modal", () => {
    if (!elements.restocks.linesContainer.children.length) {
      addRestockLine();
    }
  });

  elements.restocks.modal.addEventListener("hidden.bs.modal", () => {
    if (!state.restockCreate.isSubmitting) {
      resetRestockCreateForm();
    }
  });
}

export async function loadRestocks({
  dateFrom = state.restocks.dateFrom,
  dateTo = state.restocks.dateTo,
  page = FIRST_PAGE,
} = {}) {
  state.restocks.isLoading = true;
  state.restocks.dateFrom = dateFrom;
  state.restocks.dateTo = dateTo;
  state.restocks.searchTerm = dateFrom || dateTo ? "filtered" : "";
  state.restocks.error = "";
  renderRestocks();

  try {
    const response = await getRestocks({ dateFrom, dateTo, page });
    applyPage(state.restocks, response, page);
  } catch (error) {
    console.error("Could not load restocks:", error);
    resetPage(state.restocks, page);
    state.restocks.error = getRequestErrorMessage(error, "пополнения");
  } finally {
    state.restocks.isLoading = false;
    renderRestocks();
  }
}

function addRestockLine() {
  elements.restocks.linesContainer.append(createRestockLineElement());
}

function createRestockLineElement() {
  const lineId = nextRestockLineId;
  nextRestockLineId += 1;

  return createOperationLineElement({
    lineId,
    kind: "restock",
    quantityName: "restock_quantity",
    quantityLabel: "Количество пополнения",
    includeUnitCost: true,
  });
}

async function submitRestockCreate() {
  const validationMessage = validateOperationLines(
    elements.restocks.linesContainer,
    "пополнения",
  );

  if (validationMessage) {
    setCreateError(elements.restocks.createError, validationMessage);
    return;
  }

  if (!elements.restocks.form.reportValidity()) {
    return;
  }

  const payload = getRestockCreatePayload();

  if (!payload.lines.length) {
    setCreateError(elements.restocks.createError, "Добавьте хотя бы одну позицию.");
    return;
  }

  state.restockCreate.isSubmitting = true;
  setCreateError(elements.restocks.createError);
  setSubmitting(elements.restocks.form, true);

  try {
    await createRestock(payload);
    hideModal(elements.restocks.modal);
    resetRestockCreateForm();
    await Promise.all([
      loadDashboard(),
      loadRestocks({ page: state.restocks.page }),
      loadProducts(state.products.searchTerm, state.products.page),
    ]);
  } catch (error) {
    console.error("Could not create restock:", error);
    setCreateError(elements.restocks.createError, getCreateErrorMessage(error, "пополнение"));
  } finally {
    state.restockCreate.isSubmitting = false;
    setSubmitting(elements.restocks.form, false);
  }
}

function getRestockCreatePayload() {
  const formData = new FormData(elements.restocks.form);

  return {
    note: getText(formData, "note") || null,
    lines: Array.from(elements.restocks.linesContainer.querySelectorAll(".restock-create-line"))
      .map(getRestockLinePayload),
  };
}

function getRestockLinePayload(lineElement) {
  const formData = new FormData();

  for (const control of lineElement.querySelectorAll("input, select")) {
    if (control.name) {
      formData.set(control.name, control.value);
    }
  }

  const payload = {
    product_supplier_id: getNumber(formData, "product_supplier_id"),
    restock_quantity: getNumber(formData, "restock_quantity"),
  };
  const unitCostSnapshot = getOptionalNumber(formData, "unit_cost_snapshot");

  if (unitCostSnapshot !== null) {
    payload.unit_cost_snapshot = unitCostSnapshot;
  }

  return payload;
}

function resetRestockCreateForm() {
  elements.restocks.form.reset();
  elements.restocks.linesContainer.replaceChildren();
  nextRestockLineId = 1;
  setCreateError(elements.restocks.createError);
}

function getText(formData, key) {
  return String(formData.get(key) || "").trim();
}

function getNumber(formData, key) {
  return Number(formData.get(key));
}

function getOptionalNumber(formData, key) {
  const value = String(formData.get(key) || "").trim();
  return value ? Number(value) : null;
}

function hideModal(modalElement) {
  window.bootstrap?.Modal.getOrCreateInstance(modalElement).hide();
}
