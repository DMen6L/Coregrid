import { elements } from "./dom.js";
import { state } from "./state.js";
import {
  DEFAULT_QUANTITY_UNIT,
  formatCount,
  formatCurrency,
  formatDateTime,
  formatQuantity,
} from "./format.js";

const STOCK_STATUS = {
  available: { label: "В наличии", className: "text-bg-success" },
  low: { label: "Мало", className: "text-bg-warning" },
  out: { label: "Нет", className: "text-bg-danger" },
  none: { label: "Без данных", className: "text-bg-secondary" },
};

const EMPTY_DASHBOARD_DATA = {
  dashboard_sales_value: 0,
  dashboard_sales_count: 0,
  low_stock: 0,
  out_of_stock: 0,
  latest_sales: [],
  top_products: [],
  top_suppliers: [],
};

const BEST_SALES_MODE_CONFIG = {
  quantity: {
    summary: "По количеству",
    heading: "Количество",
    format: formatCount,
  },
  revenue: {
    summary: "По выручке",
    heading: "Выручка",
    format: formatCurrency,
  },
  gross_profit: {
    summary: "По валовой прибыли",
    heading: "Валовая прибыль",
    format: formatCurrency,
  },
};

export function setAppMessage(message = "", variant = "danger") {
  elements.appMessage.textContent = message;
  elements.appMessage.className = `alert alert-${variant} ${message ? "" : "d-none"} mb-0`;
}

export function setActiveView(viewName) {
  const nextView = elements.views[viewName] ? viewName : "products";
  state.activeView = nextView;

  for (const [name, view] of Object.entries(elements.views)) {
    const isActive = name === nextView;
    view.hidden = !isActive;
    view.classList.toggle("d-none", !isActive);
  }

  for (const tab of elements.navTabs) {
    const isActive = tab.dataset.viewTab === nextView;
    tab.classList.toggle("active", isActive);
    tab.setAttribute("aria-selected", String(isActive));
    tab.toggleAttribute("aria-current", isActive);
  }

  for (const menuToggle of elements.navMenuToggles) {
    const views = String(menuToggle.dataset.viewMenuViews || "").split(/\s+/);
    const isActive = views.includes(nextView);
    menuToggle.classList.toggle("active", isActive);
    menuToggle.toggleAttribute("aria-current", isActive);
  }
}

export function renderDashboard() {
  const dashboard = state.dashboard;
  const data = dashboard.data || EMPTY_DASHBOARD_DATA;
  const modeConfig =
    BEST_SALES_MODE_CONFIG[dashboard.bestSalesMode] || BEST_SALES_MODE_CONFIG.quantity;

  elements.dashboard.daysInput.value = String(dashboard.days);
  elements.dashboard.bestSalesModeSelect.value = dashboard.bestSalesMode;
  elements.dashboard.refreshButton.disabled = dashboard.isLoading;
  elements.dashboard.refreshButton.textContent = dashboard.isLoading ? "Загрузка..." : "Обновить";
  elements.dashboard.salesValue.textContent = formatCurrency(data.dashboard_sales_value);
  elements.dashboard.salesCount.textContent = formatCount(data.dashboard_sales_count);
  elements.dashboard.lowStock.textContent = formatCount(data.low_stock);
  elements.dashboard.outOfStock.textContent = formatCount(data.out_of_stock);
  elements.dashboard.trendSummary.textContent = dashboard.error
    ? "Данные недоступны"
    : `Последние ${formatCount(dashboard.days)} дней`;
  elements.dashboard.bestSalesSummary.textContent = modeConfig.summary;
  elements.dashboard.bestSalesMetricHeading.textContent = modeConfig.heading;

  const dailySales = dashboard.data
    ? createDashboardDailyRange(data.latest_sales, dashboard.days)
    : [];

  renderDashboardDailySales(dailySales, {
    error: dashboard.error,
    isLoading: dashboard.isLoading,
  });
  renderDashboardTopProducts(data.top_products, modeConfig, {
    error: dashboard.error,
    isLoading: dashboard.isLoading,
  });
  renderDashboardTopSuppliers(data.top_suppliers, {
    error: dashboard.error,
    isLoading: dashboard.isLoading,
  });
}

export function renderProducts() {
  const productList = state.products.items;
  const hasProducts = productList.length > 0;
  const shouldShowTable = hasProducts && !state.products.isLoading;

  elements.products.count.textContent = `${formatCount(state.products.total)} товаров`;
  renderListChrome(elements.products, state.products, shouldShowTable, {
    empty: "Товары пока не добавлены.",
    emptySearch: "По запросу ничего не найдено.",
  });

  elements.products.tableBody.replaceChildren();

  if (!shouldShowTable) {
    return;
  }

  const fragment = document.createDocumentFragment();

  for (const product of productList) {
    fragment.append(createProductRow(product));
  }

  elements.products.tableBody.append(fragment);
}

export function renderCompanies() {
  renderSimpleList({
    elementsGroup: elements.companies,
    listState: state.companies,
    countLabel: "компаний",
    empty: "Компании пока не добавлены.",
    emptySearch: "По запросу ничего не найдено.",
    createRow: createCompanyRow,
  });
}

export function renderSuppliers() {
  renderSimpleList({
    elementsGroup: elements.suppliers,
    listState: state.suppliers,
    countLabel: "поставщиков",
    empty: "Поставщики пока не добавлены.",
    emptySearch: "По запросу ничего не найдено.",
    createRow: createSupplierRow,
  });
}

export function renderRestocks() {
  renderOperationList({
    elementsGroup: elements.restocks,
    listState: state.restocks,
    countLabel: "пополнений",
    empty: "Пополнения пока не добавлены.",
    emptyFiltered: "За выбранный период пополнения не найдены.",
    createRow: createRestockRow,
  });
}

export function renderSales() {
  renderOperationList({
    elementsGroup: elements.sales,
    listState: state.sales,
    countLabel: "продаж",
    empty: "Продажи пока не зарегистрированы.",
    emptyFiltered: "За выбранный период продажи не найдены.",
    createRow: createSaleRow,
  });
}

export function renderLookup({ kind }) {
  const productCreate = state.productCreate;
  const lookup = kind === "supplier"
    ? productCreate.supplierLookup
    : productCreate.companyLookup;
  const selected = kind === "supplier"
    ? productCreate.selectedSupplier
    : productCreate.selectedCompany;
  const group = kind === "supplier"
    ? {
        selected: elements.products.supplierSelected,
        selectedName: elements.products.supplierSelectedName,
        selectedMeta: elements.products.supplierSelectedMeta,
        message: elements.products.supplierLookupMessage,
        results: elements.products.supplierResults,
      }
    : {
        selected: elements.products.companySelected,
        selectedName: elements.products.companySelectedName,
        selectedMeta: elements.products.companySelectedMeta,
        message: elements.products.companyLookupMessage,
        results: elements.products.companyResults,
      };

  group.selected.classList.toggle("d-none", !selected);
  group.selectedName.textContent = selected?.name || "";
  group.selectedMeta.textContent = selected
    ? getLookupMeta(kind, selected)
    : "";

  const message = getLookupMessage(kind, lookup);
  group.message.textContent = message;
  group.message.classList.toggle("d-none", !message);
  group.message.classList.toggle("text-danger", Boolean(lookup.error));
  group.message.classList.toggle("text-secondary", !lookup.error);

  const shouldShowResults =
    !selected && !lookup.isLoading && !lookup.error && lookup.results.length > 0;
  group.results.classList.toggle("d-none", !shouldShowResults);
  group.results.replaceChildren();

  if (!shouldShowResults) {
    return;
  }

  const fragment = document.createDocumentFragment();

  for (const item of lookup.results) {
    fragment.append(createLookupResultButton(kind, item));
  }

  group.results.append(fragment);
}

export function renderProductCreateMode() {
  const isCompanyNew = state.productCreate.companyMode === "new";
  const isSupplierNew = state.productCreate.supplierMode === "new";

  elements.products.companyExistingPanel.classList.toggle("d-none", isCompanyNew);
  elements.products.companyNewPanel.classList.toggle("d-none", !isCompanyNew);
  elements.products.supplierSection.classList.toggle("d-none", !state.productCreate.linkEnabled);
  elements.products.supplierExistingPanel.classList.toggle("d-none", isSupplierNew);
  elements.products.supplierNewPanel.classList.toggle("d-none", !isSupplierNew);
}

export function setCreateError(element, message = "") {
  element.textContent = message;
  element.classList.toggle("d-none", !message);
}

export function setSubmitting(form, isSubmitting) {
  for (const control of form.elements) {
    if ("disabled" in control) {
      control.disabled = isSubmitting;
    }
  }
}

function renderDashboardDailySales(items, { error, isLoading }) {
  const rows = Array.isArray(items) ? items : [];
  const shouldShowEmpty = Boolean(error) || (!isLoading && rows.length === 0);

  elements.dashboard.salesTrendEmpty.textContent = error || "За выбранный период продаж не найдено.";
  elements.dashboard.salesTrendEmpty.classList.toggle("d-none", !shouldShowEmpty);
  elements.dashboard.salesChart.classList.toggle("d-none", Boolean(error) || rows.length === 0);
  elements.dashboard.salesChart.replaceChildren();
  elements.dashboard.salesDailyTableBody.replaceChildren();

  if (error || rows.length === 0) {
    return;
  }

  elements.dashboard.salesChart.append(createSalesChart(rows));

  const fragment = document.createDocumentFragment();

  for (const item of rows) {
    fragment.append(createDailySalesRow(item));
  }

  elements.dashboard.salesDailyTableBody.append(fragment);
}

function renderDashboardTopProducts(items, modeConfig, { error, isLoading }) {
  const rows = Array.isArray(items) ? items : [];
  const shouldShowEmpty = Boolean(error) || (!isLoading && rows.length === 0);

  elements.dashboard.bestSalesEmpty.textContent =
    error || "За выбранный период нет товаров для рейтинга.";
  elements.dashboard.bestSalesEmpty.classList.toggle("d-none", !shouldShowEmpty);
  elements.dashboard.bestSalesTableBody.replaceChildren();

  if (error || rows.length === 0) {
    return;
  }

  const fragment = document.createDocumentFragment();

  for (const item of rows) {
    fragment.append(createTopProductRow(item, modeConfig));
  }

  elements.dashboard.bestSalesTableBody.append(fragment);
}

function renderDashboardTopSuppliers(items, { error, isLoading }) {
  const rows = Array.isArray(items) ? items : [];
  const shouldShowEmpty = Boolean(error) || (!isLoading && rows.length === 0);

  elements.dashboard.topSuppliersEmpty.textContent =
    error || "Поставщики с товарами пока не найдены.";
  elements.dashboard.topSuppliersEmpty.classList.toggle("d-none", !shouldShowEmpty);
  elements.dashboard.topSuppliersTableBody.replaceChildren();

  if (error || rows.length === 0) {
    return;
  }

  const fragment = document.createDocumentFragment();

  for (const item of rows) {
    fragment.append(createTopSupplierRow(item));
  }

  elements.dashboard.topSuppliersTableBody.append(fragment);
}

function createSalesChart(items) {
  const wrapper = document.createElement("div");
  const maxValue = Math.max(...items.map((item) => Number(item.sales_value || 0)), 0);

  wrapper.className = "dashboard-sales-chart-bars";

  for (const item of items) {
    const value = Number(item.sales_value || 0);
    const itemElement = document.createElement("div");
    const track = document.createElement("div");
    const bar = document.createElement("div");
    const label = document.createElement("div");
    const height = maxValue > 0 ? Math.max((value / maxValue) * 100, 3) : 3;

    itemElement.className = "dashboard-sales-chart-item";
    itemElement.title = `${formatFullDate(item.date)}: ${formatCurrency(value)}`;
    track.className = "dashboard-sales-chart-track";
    bar.className = "dashboard-sales-chart-bar";
    bar.classList.toggle("is-empty", value === 0);
    bar.style.height = `${height}%`;
    label.className = "dashboard-sales-chart-label";
    label.textContent = formatShortDate(item.date);

    track.append(bar);
    itemElement.append(track, label);
    wrapper.append(itemElement);
  }

  return wrapper;
}

function createDailySalesRow(item) {
  const row = document.createElement("tr");
  const dateCell = document.createElement("td");
  const valueCell = document.createElement("td");

  dateCell.textContent = formatFullDate(item.date);
  valueCell.className = "fw-semibold";
  valueCell.textContent = formatCurrency(item.sales_value);
  row.append(dateCell, valueCell);
  return row;
}

function createTopProductRow(item, modeConfig) {
  const row = document.createElement("tr");
  const productCell = document.createElement("td");
  const metricCell = document.createElement("td");
  const productName = document.createElement("div");
  const productMeta = document.createElement("div");

  productName.className = "fw-semibold";
  productName.textContent = item.product_name || "Без названия";
  productMeta.className = "product-meta";
  productMeta.textContent = `ID ${formatCount(item.product_id)}`;
  productCell.append(productName, productMeta);
  metricCell.className = "fw-semibold";
  metricCell.textContent = modeConfig.format(item.metric);
  row.append(productCell, metricCell);
  return row;
}

function createTopSupplierRow(item) {
  const row = document.createElement("tr");
  const supplierCell = document.createElement("td");
  const countCell = document.createElement("td");
  const supplierName = document.createElement("div");
  const supplierMeta = document.createElement("div");

  supplierName.className = "fw-semibold";
  supplierName.textContent = item.supplier_name || "Без названия";
  supplierMeta.className = "supplier-meta";
  supplierMeta.textContent = `ID ${formatCount(item.supplier_id)}`;
  supplierCell.append(supplierName, supplierMeta);
  countCell.className = "fw-semibold";
  countCell.textContent = formatCount(item.supplied_products);
  row.append(supplierCell, countCell);
  return row;
}

function createDashboardDailyRange(items, days) {
  const salesByDate = new Map();

  for (const item of Array.isArray(items) ? items : []) {
    const dateKey = normalizeDateKey(item.date);

    if (dateKey) {
      salesByDate.set(dateKey, Number(item.sales_value || 0));
    }
  }

  return createDateRange(days, salesByDate).map((dateKey) => ({
    date: dateKey,
    sales_value: salesByDate.get(dateKey) || 0,
  }));
}

function createDateRange(days, salesByDate) {
  const count = Math.max(Number(days) || 1, 1);
  const endDate = getDashboardRangeEndDate(salesByDate);
  const startDate = new Date(endDate);
  const dateKeys = [];

  startDate.setDate(endDate.getDate() - count + 1);

  for (let offset = 0; offset < count; offset += 1) {
    const date = new Date(startDate);
    date.setDate(startDate.getDate() + offset);
    dateKeys.push(formatDateKey(date));
  }

  return dateKeys;
}

function getDashboardRangeEndDate(salesByDate) {
  const today = startOfDay(new Date());
  let endDate = today;

  for (const dateKey of salesByDate.keys()) {
    const date = parseDate(dateKey);

    if (date && date > endDate) {
      endDate = date;
    }
  }

  return endDate;
}

function renderSimpleList({ elementsGroup, listState, countLabel, empty, emptySearch, createRow }) {
  const hasRows = listState.items.length > 0;
  const shouldShowTable = hasRows && !listState.isLoading;

  elementsGroup.count.textContent = `${formatCount(listState.total)} ${countLabel}`;
  renderListChrome(elementsGroup, listState, shouldShowTable, { empty, emptySearch });
  elementsGroup.tableBody.replaceChildren();

  if (!shouldShowTable) {
    return;
  }

  const fragment = document.createDocumentFragment();

  for (const row of listState.items) {
    fragment.append(createRow(row));
  }

  elementsGroup.tableBody.append(fragment);
}

function renderOperationList({
  elementsGroup,
  listState,
  countLabel,
  empty,
  emptyFiltered,
  createRow,
}) {
  const hasRows = listState.items.length > 0;
  const shouldShowTable = hasRows && !listState.isLoading;

  elementsGroup.count.textContent = `${formatCount(listState.total)} ${countLabel}`;
  renderListChrome(elementsGroup, listState, shouldShowTable, {
    empty,
    emptySearch: emptyFiltered,
  });
  elementsGroup.tableBody.replaceChildren();

  if (!shouldShowTable) {
    return;
  }

  const fragment = document.createDocumentFragment();

  for (const row of listState.items) {
    fragment.append(createRow(row));
  }

  elementsGroup.tableBody.append(fragment);
}

function renderListChrome(elementsGroup, listState, shouldShowTable, messages) {
  const shouldShowEmpty =
    !listState.items.length && !listState.isLoading && !listState.error;
  const shouldShowPagination =
    listState.total > 0 && !listState.isLoading && !listState.error;
  const totalPages = Math.max(listState.totalPages, 1);

  elementsGroup.loading.classList.toggle("d-none", !listState.isLoading);
  elementsGroup.error.textContent = listState.error;
  elementsGroup.error.classList.toggle("d-none", !listState.error);
  elementsGroup.empty.textContent = listState.searchTerm
    ? messages.emptySearch
    : messages.empty;
  elementsGroup.empty.classList.toggle("d-none", !shouldShowEmpty);
  elementsGroup.table.classList.toggle("d-none", !shouldShowTable);
  elementsGroup.pagination.classList.toggle("d-none", !shouldShowPagination);
  elementsGroup.previousPageButton.disabled = listState.isLoading || !listState.hasPrevious;
  elementsGroup.nextPageButton.disabled = listState.isLoading || !listState.hasNext;
  elementsGroup.pageSummary.textContent =
    `Страница ${formatCount(listState.page)} из ${formatCount(totalPages)}`;
}

function createProductRow(product) {
  const row = document.createElement("tr");

  row.append(
    createProductNameCell(product),
    createStatusCell(product),
    createStockCell(product),
    createPricingCell(product),
    createOwnerCell(product),
    createTagsCell(product.tags),
  );

  return row;
}

function createProductNameCell(product) {
  const cell = document.createElement("td");
  const name = document.createElement("div");
  const meta = document.createElement("div");

  cell.className = "product-name-cell";
  name.className = "fw-semibold";
  name.textContent = product.name || "Без названия";
  meta.className = "product-meta";
  meta.textContent = `ID ${formatCount(product.id)} | Создан: ${formatDateTime(product.created_at)}`;
  cell.append(name, meta);
  return cell;
}

function createStatusCell(product) {
  const cell = document.createElement("td");
  const badge = document.createElement("span");
  const status = getSummaryStockStatus(product);
  const config = STOCK_STATUS[status] || STOCK_STATUS.none;

  badge.className = `badge status-badge ${config.className}`;
  badge.textContent = config.label;
  cell.append(badge);
  return cell;
}

function createStockCell(product) {
  const cell = document.createElement("td");
  const totalQuantity = Number(product.total_quantity || 0);
  const unit = getProductUnit(product);
  const quantityText = document.createElement("div");
  const meta = document.createElement("div");

  quantityText.className = "fw-semibold";
  quantityText.textContent = formatQuantity(totalQuantity, unit);
  meta.className = "product-meta";
  meta.textContent = getSummaryStockMeta(product);

  cell.append(quantityText, meta);
  return cell;
}

function createPricingCell(product) {
  const cell = document.createElement("td");
  const price = product.min_sale_price;
  const salePrice = document.createElement("div");
  const details = document.createElement("div");

  if (price === null || price === undefined) {
    cell.textContent = "Нет доступной цены";
    cell.className = "text-secondary";
    return cell;
  }

  salePrice.className = "fw-semibold";
  salePrice.textContent = formatCurrency(price);
  details.className = "product-meta";
  details.textContent = getSummaryPriceMeta(product);

  cell.append(salePrice, details);
  return cell;
}

function createOwnerCell(product) {
  const cell = document.createElement("td");
  const company = document.createElement("div");
  const suppliers = document.createElement("div");

  company.className = "fw-semibold";
  company.textContent = product.company_name || "Компания не указана";
  suppliers.className = "product-meta";
  suppliers.textContent = getSupplierCountText(product.suppliers_count);
  cell.append(company, suppliers);
  return cell;
}

function createTagsCell(tags) {
  const cell = document.createElement("td");
  const tagList = normalizeTags(tags);

  if (!tagList.length) {
    cell.textContent = "Без тегов";
    cell.className = "text-secondary";
    return cell;
  }

  const wrapper = document.createElement("div");
  wrapper.className = "product-tags";

  for (const tag of tagList) {
    const badge = document.createElement("span");
    badge.className = "badge rounded-pill text-bg-light border";
    badge.textContent = tag;
    wrapper.append(badge);
  }

  cell.append(wrapper);
  return cell;
}

function createCompanyRow(company) {
  const row = document.createElement("tr");
  const nameCell = document.createElement("td");
  const iinCell = document.createElement("td");
  const name = document.createElement("div");
  const meta = document.createElement("div");

  name.className = "fw-semibold";
  name.textContent = company.name || "Без названия";
  meta.className = "company-meta";
  meta.textContent = `ID ${formatCount(company.id)}`;
  nameCell.append(name, meta);
  iinCell.textContent = company.iin || "Не указан";
  row.append(nameCell, iinCell);
  return row;
}

function createSupplierRow(supplier) {
  const row = document.createElement("tr");
  const nameCell = document.createElement("td");
  const phoneCell = document.createElement("td");
  const name = document.createElement("div");
  const meta = document.createElement("div");

  name.className = "fw-semibold";
  name.textContent = supplier.name || "Без названия";
  meta.className = "supplier-meta";
  meta.textContent = `ID ${formatCount(supplier.id)}`;
  nameCell.append(name, meta);
  phoneCell.textContent = supplier.phone_number || "Не указан";
  row.append(nameCell, phoneCell);
  return row;
}

function createRestockRow(restock) {
  const row = document.createElement("tr");
  const lines = normalizeLines(restock.lines);
  const totalCost = lines.reduce(
    (total, line) => total + Number(line.restock_quantity || 0) * Number(line.unit_cost_snapshot || 0),
    0,
  );

  row.append(
    createOperationSummaryCell(restock, lines, "Пополнение"),
    createDateCell(restock.created_at),
    createOperationLinesCell(lines, "restock"),
    createMoneyCell(totalCost),
    createNoteCell(restock.note),
  );

  return row;
}

function createSaleRow(sale) {
  const row = document.createElement("tr");

  row.append(
    createSaleSummaryCell(sale),
    createDateCell(sale.created_at),
    createLineCountCell(sale.lines_count),
    createMoneyCell(sale.revenue),
    createNoteCell(sale.note),
  );

  return row;
}

function createSaleSummaryCell(sale) {
  const cell = document.createElement("td");
  const title = document.createElement("div");

  cell.className = "sale-summary-cell";
  title.className = "fw-semibold";
  title.textContent = `Продажа #${formatCount(sale.id)}`;
  cell.append(title);
  return cell;
}

function createLineCountCell(value) {
  const cell = document.createElement("td");

  cell.textContent = `${formatCount(value)} позиций`;
  return cell;
}

function createOperationSummaryCell(operation, lines, label) {
  const cell = document.createElement("td");
  const title = document.createElement("div");
  const meta = document.createElement("div");

  cell.className = label === "Продажа" ? "sale-summary-cell" : "restock-summary-cell";
  title.className = "fw-semibold";
  title.textContent = `${label} #${formatCount(operation.id)}`;
  meta.className = label === "Продажа" ? "sale-meta" : "restock-meta";
  meta.textContent = `${formatCount(lines.length)} позиций`;
  cell.append(title, meta);
  return cell;
}

function createDateCell(value) {
  const cell = document.createElement("td");
  cell.textContent = formatDateTime(value);
  return cell;
}

function createOperationLinesCell(lines, kind) {
  const cell = document.createElement("td");

  if (!lines.length) {
    cell.textContent = "Нет позиций";
    cell.className = "text-secondary";
    return cell;
  }

  const wrapper = document.createElement("div");
  wrapper.className = kind === "sale" ? "sale-lines" : "restock-lines";

  for (const line of lines) {
    const lineElement = document.createElement("div");
    const title = document.createElement("div");
    const meta = document.createElement("div");
    const quantity = kind === "sale" ? line.sale_quantity : line.restock_quantity;

    title.className = "fw-semibold";
    title.textContent = line.product_name || `Товар #${formatCount(line.product_id)}`;
    meta.className = kind === "sale" ? "sale-meta" : "restock-meta";
    meta.textContent = [
      line.supplier_name || `Поставщик #${formatCount(line.supplier_id)}`,
      formatQuantity(quantity, line.quantity_unit_snapshot),
    ].join(" | ");
    lineElement.append(title, meta);
    wrapper.append(lineElement);
  }

  cell.append(wrapper);
  return cell;
}

function createMoneyCell(value) {
  const cell = document.createElement("td");
  cell.className = "fw-semibold";
  cell.textContent = formatCurrency(value);
  return cell;
}

function createNoteCell(value) {
  const cell = document.createElement("td");
  const note = String(value || "").trim();

  cell.textContent = note || "Без комментария";
  cell.className = note ? "" : "text-secondary";
  return cell;
}

function createLookupResultButton(kind, item) {
  const button = document.createElement("button");
  const name = document.createElement("span");
  const meta = document.createElement("span");
  const idAttribute = kind === "supplier" ? "supplierId" : "companyId";

  button.className = "list-group-item list-group-item-action product-lookup-result";
  button.type = "button";
  button.dataset[idAttribute] = String(item.id || "");
  button.setAttribute("role", "option");
  name.className = "fw-semibold d-block";
  name.textContent = item.name || "Без названия";
  meta.className = "product-meta d-block";
  meta.textContent = getLookupMeta(kind, item);
  button.append(name, meta);
  return button;
}

function getLookupMessage(kind, lookup) {
  const label = kind === "supplier" ? "поставщиков" : "компаний";

  if (lookup.isLoading) {
    return `Поиск ${label}...`;
  }

  if (lookup.error) {
    return lookup.error;
  }

  if (lookup.hasSearched && lookup.results.length === 0) {
    return kind === "supplier" ? "Поставщики не найдены." : "Компании не найдены.";
  }

  return "";
}

function getLookupMeta(kind, item) {
  return kind === "supplier"
    ? `ID ${formatCount(item.id)} | ${item.phone_number || "Телефон не указан"}`
    : `ID ${formatCount(item.id)} | ИИН ${item.iin || "Не указан"}`;
}

function normalizeDateKey(value) {
  const date = parseDate(value);
  return date ? formatDateKey(date) : "";
}

function formatDateKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function formatFullDate(value) {
  const date = parseDate(value);
  return date
    ? date.toLocaleDateString("ru-KZ", { dateStyle: "medium" })
    : "Не указано";
}

function formatShortDate(value) {
  const date = parseDate(value);
  return date
    ? date.toLocaleDateString("ru-KZ", { day: "2-digit", month: "2-digit" })
    : "";
}

function parseDate(value) {
  if (!value) {
    return null;
  }

  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime()) ? null : date;
}

function startOfDay(date) {
  const nextDate = new Date(date);
  nextDate.setHours(0, 0, 0, 0);
  return nextDate;
}

function getSummaryStockStatus(product) {
  if (product.stock_status) {
    return product.stock_status;
  }

  const quantity = Number(product.total_quantity || 0);
  const threshold = Number(product.low_stock_threshold);

  if (!Number.isFinite(quantity) || quantity <= 0) {
    return "out";
  }

  return Number.isFinite(threshold) && quantity <= threshold ? "low" : "available";
}

function getSummaryPriceMeta(product) {
  const parts = [];

  if (product.min_purchase_price !== null && product.min_purchase_price !== undefined) {
    parts.push(`Закупка: ${formatCurrency(product.min_purchase_price)}`);
  }

  if (product.margin_percent !== null && product.margin_percent !== undefined) {
    parts.push(`Маржа: ${formatCount(product.margin_percent)}%`);
  }

  return parts.length ? parts.join(" | ") : "Детали цены не заданы";
}

function getSummaryStockMeta(product) {
  const unit = getProductUnit(product);
  const parts = [];

  if (product.low_stock_threshold !== null && product.low_stock_threshold !== undefined) {
    parts.push(`Порог: ${formatQuantity(product.low_stock_threshold, unit)}`);
  }

  return parts.length ? parts.join(" | ") : "";
}

function getProductUnit(product) {
  return String(product.quantity_unit || "").trim() || DEFAULT_QUANTITY_UNIT;
}

function getSupplierCountText(value) {
  const count = Number(value || 0);

  if (!Number.isFinite(count) || count <= 0) {
    return "Нет поставщиков";
  }

  return `Поставщиков: ${formatCount(count)}`;
}

function normalizeTags(tags) {
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

function normalizeLines(lines) {
  return Array.isArray(lines) ? lines : [];
}
