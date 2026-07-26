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

export function renderParkedViews() {
  elements.dashboard.salesValue.textContent = "0 тг";
  elements.dashboard.salesCount.textContent = "0";
  elements.dashboard.lowStock.textContent = "0";
  elements.dashboard.outOfStock.textContent = "0";
  elements.dashboard.salesButton.textContent = "Отключено";
  elements.dashboard.salesTrendEmpty.textContent = "Дэшборд будет подключен после обновления складских операций.";
  elements.dashboard.bestSalesEmpty.textContent = "Рейтинг товаров временно отключен.";
  elements.dashboard.salesTrendEmpty.classList.remove("d-none");
  elements.dashboard.bestSalesEmpty.classList.remove("d-none");
  elements.dashboard.salesDailyTableBody.replaceChildren();
  elements.dashboard.bestSalesTableBody.replaceChildren();

  disableControls(elements.parked.dashboardControls);
  disableControls(elements.parked.restockControls);
  disableControls(elements.parked.saleControls);

  setParkedEmpty("restocks", "Пополнения временно отключены до повторной привязки к product_supplier_id.");
  setParkedEmpty("sales", "Продажи временно отключены до повторной привязки к product_supplier_id.");
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

function disableControls(controls) {
  for (const control of controls) {
    control.disabled = true;
  }
}

function setParkedEmpty(viewName, message) {
  const viewElements = viewName === "sales"
    ? {
        loading: document.querySelector("#sales-loading"),
        empty: document.querySelector("#sales-empty"),
        table: document.querySelector("#sales-table"),
        pagination: document.querySelector("#sales-pagination"),
        count: document.querySelector("#sales-count"),
      }
    : {
        loading: document.querySelector("#restocks-loading"),
        empty: document.querySelector("#restocks-empty"),
        table: document.querySelector("#restocks-table"),
        pagination: document.querySelector("#restocks-pagination"),
        count: document.querySelector("#restocks-count"),
      };

  viewElements.loading?.classList.add("d-none");
  viewElements.table?.classList.add("d-none");
  viewElements.pagination?.classList.add("d-none");
  viewElements.empty?.classList.remove("d-none");
  if (viewElements.empty) {
    viewElements.empty.textContent = message;
  }
  if (viewElements.count) {
    viewElements.count.textContent = viewName === "sales" ? "0 продаж" : "0 пополнений";
  }
}
