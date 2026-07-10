function createPageState(pageSize) {
  return {
    page: 1,
    pageSize,
    total: 0,
    pages: 0,
  };
}

function createEmptyProductSummary() {
  return {
    total_products: 0,
    total_units: 0,
    inventory_value: 0,
    low_stock: 0,
    out_of_stock: 0,
  };
}

function createEmptySalesSummary(
  dateFrom = getTodayDateInputValue(),
  dateTo = dateFrom,
) {
  return {
    revenue: 0,
    units_sold: 0,
    sale_operations: 0,
    units_sold_by_unit: [],
    daily_totals: [],
    best_sellers: [],
    date_from: dateFrom,
    date_to: dateTo,
  };
}

function getTodayDateInputValue() {
  const today = new Date();

  return formatDateInputValue(today);
}

function formatDateInputValue(value) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function parseDateInput(value) {
  const [year, month, day] = String(value).split("-").map(Number);

  if (!year || !month || !day) {
    return null;
  }

  return new Date(year, month - 1, day);
}

function formatShortDate(value) {
  const parsedDate = parseDateInput(value);

  if (!parsedDate) {
    return value;
  }

  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "short",
  }).format(parsedDate);
}

function roundChartValue(value) {
  return Math.round(value * 10) / 10;
}

function optionalNumber(value) {
  return value === "" ? null : Number(value);
}

function formatNumber(value) {
  return new Intl.NumberFormat("ru-RU").format(value);
}

function formatSignedNumber(value) {
  return value > 0 ? `+${formatNumber(value)}` : formatNumber(value);
}

function normalizeQuantityUnit(unit) {
  return String(unit || DEFAULT_QUANTITY_UNIT).trim() || DEFAULT_QUANTITY_UNIT;
}

function formatQuantity(value, unit) {
  return `${formatNumber(value)} ${normalizeQuantityUnit(unit)}`;
}

function formatSignedQuantity(value, unit) {
  return `${formatSignedNumber(value)} ${normalizeQuantityUnit(unit)}`;
}

function formatSalesQuantitySummary(salesSummary) {
  return formatQuantityGroups(
    salesSummary.units_sold_by_unit,
    salesSummary.units_sold,
  );
}

function formatQuantityGroups(unitsByUnit = [], fallbackQuantity = 0) {
  if (unitsByUnit.length > 0) {
    return unitsByUnit
      .map((item) => formatQuantity(item.quantity, item.quantity_unit))
      .join(", ");
  }

  return formatQuantity(fallbackQuantity || 0, DEFAULT_QUANTITY_UNIT);
}

function formatDate(value) {
  return new Intl.DateTimeFormat("ru-RU", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function showNotice(message, isError = false) {
  refs.notice.textContent = message;
  refs.notice.classList.toggle("error", isError);
  refs.notice.classList.remove("hidden");
}

function setBusy(isBusy) {
  refs.addProductButton.disabled = isBusy;
  refs.addSupplierButton.disabled = isBusy;
  refs.addCompanyButton.disabled = isBusy;
  refs.addMovementButton.disabled = isBusy;
  refs.dashboardAddProductButton.disabled = isBusy;
  refs.dashboardAddSaleButton.disabled = isBusy;
  refs.dashboardAddMovementButton.disabled = isBusy;
  refs.dashboardRefreshButton.disabled = isBusy;
  refs.dashboardLowStockButton.disabled = isBusy;
  refs.dashboardOutOfStockButton.disabled = isBusy;
  refs.dashboardViewMovementsButton.disabled = isBusy;
  refs.dashboardSalesDateFrom.disabled = isBusy;
  refs.dashboardSalesDateTo.disabled = isBusy;
  refs.dashboardSalesForm.querySelector("button").disabled = isBusy;
  refs.refreshButton.disabled = isBusy;
  refs.productSubmit.disabled = isBusy;
  refs.addProductTagButton.disabled = isBusy;
  refs.supplierSubmit.disabled = isBusy;
  refs.companySubmit.disabled = isBusy;
  refs.movementRefreshButton.disabled = isBusy;
  refs.addMovementLineButton.disabled = isBusy;
  refs.movementSubmit.disabled = isBusy;
  refs.addSaleLineButton.disabled = isBusy;
  refs.saleSubmit.disabled = isBusy;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
