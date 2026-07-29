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

export function renderProductPopularTags() {
  const tagState = state.products.popularTags;
  const tags = Array.isArray(tagState.items)
    ? tagState.items.filter((tag) => normalizeTagName(tag))
    : [];
  const shouldShowSection =
    tagState.isLoading || tagState.hasLoaded || Boolean(tagState.error) || tags.length > 0;
  const shouldShowEmpty =
    tagState.hasLoaded && !tagState.isLoading && !tagState.error && tags.length === 0;

  elements.products.popularTags.classList.toggle("d-none", !shouldShowSection);
  elements.products.popularTagsLoading.classList.toggle("d-none", !tagState.isLoading);
  elements.products.popularTagsError.textContent = tagState.error;
  elements.products.popularTagsError.classList.toggle("d-none", !tagState.error);
  elements.products.popularTagsEmpty.classList.toggle("d-none", !shouldShowEmpty);
  elements.products.popularTagsList.replaceChildren();

  if (!tags.length || tagState.error) {
    return;
  }

  const fragment = document.createDocumentFragment();

  for (const tag of tags) {
    fragment.append(createPopularTagButton(tag));
  }

  elements.products.popularTagsList.append(fragment);
}

export function renderProductDetail() {
  const detail = state.productDetail;
  const product = detail.data;
  const summary = detail.summary;
  const supplierLinks = normalizeProductSupplierLinks(product?.supplier_links);
  const tags = getProductDetailTags(product, summary);
  const shouldShowContent = Boolean(product) && !detail.isLoading && !detail.error;
  const isEditing = shouldShowContent && detail.isEditing;
  const totalQuantity = supplierLinks.length
    ? getProductDetailTotalQuantity(supplierLinks)
    : Number(summary?.total_quantity || 0);
  const unit = getProductUnit(product || summary || {});

  elements.products.detailTitle.textContent = product
    ? product.name || `Товар #${formatCount(product.id)}`
    : "Товар";
  elements.products.detailLoading.classList.toggle("d-none", !detail.isLoading);
  elements.products.detailError.textContent = detail.error;
  elements.products.detailError.classList.toggle("d-none", !detail.error);
  elements.products.detailContent.classList.toggle("d-none", !shouldShowContent);
  elements.products.detailEditError.textContent = detail.editError;
  elements.products.detailEditError.classList.toggle("d-none", !detail.editError);
  elements.products.detailEditButton.classList.toggle("d-none", !shouldShowContent || isEditing);
  elements.products.detailView.classList.toggle("d-none", isEditing);
  elements.products.detailEditForm.classList.toggle("d-none", !isEditing);
  elements.products.detailCancelEditButton.classList.toggle("d-none", !isEditing);
  elements.products.detailSaveButton.classList.toggle("d-none", !isEditing);
  elements.products.detailSaveButton.disabled = detail.isSubmitting;
  elements.products.detailCancelEditButton.disabled = detail.isSubmitting;
  elements.products.detailAddLinkButton.disabled = detail.isSubmitting;
  elements.products.detailSuppliersEmpty.classList.toggle(
    "d-none",
    !shouldShowContent || supplierLinks.length > 0,
  );
  elements.products.detailSuppliersTable.classList.toggle(
    "d-none",
    !shouldShowContent || supplierLinks.length === 0,
  );
  elements.products.detailSuppliersBody.replaceChildren();

  if (!shouldShowContent) {
    elements.products.detailEditLinksEmpty.classList.add("d-none");
    elements.products.detailEditLinksTable.classList.add("d-none");
    elements.products.detailEditLinksBody.replaceChildren();
    elements.products.detailNewLinks.replaceChildren();
    return;
  }

  elements.products.detailId.textContent = formatCount(product.id);
  elements.products.detailCreatedAt.textContent = formatDateTime(product.created_at);
  elements.products.detailCompany.textContent = product.company_name || "Компания не указана";
  elements.products.detailUnit.textContent = unit;
  elements.products.detailThreshold.textContent = formatQuantity(product.low_stock_threshold, unit);
  elements.products.detailTotalQuantity.textContent = formatQuantity(totalQuantity, unit);
  elements.products.detailSupplierCount.textContent = `${formatCount(supplierLinks.length)} поставщиков`;
  renderProductDetailTags(tags);
  renderLookup({ kind: "detailCompany" });
  renderProductDetailEditLinks(supplierLinks, unit, isEditing, detail.isSubmitting);

  const fragment = document.createDocumentFragment();

  for (const supplierLink of supplierLinks) {
    fragment.append(createProductSupplierDetailRow(supplierLink, unit));
  }

  elements.products.detailSuppliersBody.append(fragment);
  setProductDetailEditControlsDisabled(detail);
}

export function renderProductDetailNewLinkLookup(draftId) {
  const draft = state.productDetail.linkDrafts.find(
    (item) => Number(item.id) === Number(draftId),
  );
  const wrapper = elements.products.detailNewLinks.querySelector(
    `[data-link-draft-id="${draftId}"]`,
  );

  if (!draft || !wrapper) {
    return;
  }

  const selected = wrapper.querySelector("[data-new-link-selected]");
  const selectedName = wrapper.querySelector("[data-new-link-selected-name]");
  const selectedMeta = wrapper.querySelector("[data-new-link-selected-meta]");
  const searchInput = wrapper.querySelector("[data-new-link-supplier-search]");
  const message = wrapper.querySelector("[data-new-link-lookup-message]");
  const results = wrapper.querySelector("[data-new-link-results]");
  const hasSupplier = Boolean(draft.selectedSupplier);

  selected.classList.toggle("d-none", !hasSupplier);
  searchInput.classList.toggle("d-none", hasSupplier);
  searchInput.disabled = state.productDetail.isSubmitting || hasSupplier;

  if (document.activeElement !== searchInput) {
    searchInput.value = draft.searchTerm || "";
  }

  if (hasSupplier) {
    selectedName.textContent = draft.selectedSupplier.name || "Без названия";
    selectedMeta.textContent = getLookupMeta("supplier", draft.selectedSupplier);
  }

  const lookupMessage = getLookupMessage("supplier", draft.lookup);
  message.textContent = lookupMessage;
  message.classList.toggle("d-none", !lookupMessage);
  results.classList.toggle(
    "d-none",
    hasSupplier || draft.lookup.results.length === 0,
  );
  results.replaceChildren();

  if (!hasSupplier) {
    const fragment = document.createDocumentFragment();

    for (const supplier of draft.lookup.results) {
      fragment.append(createLookupResultButton("supplier", supplier));
    }

    results.append(fragment);
  }
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

export function renderCompanyDetail() {
  const detail = state.companyDetail;
  const company = detail.data;
  const shouldShowContent = Boolean(company) && !detail.isLoading && !detail.error;
  const isEditing = shouldShowContent && detail.isEditing;

  elements.companies.detailTitle.textContent = company
    ? company.name || `Компания #${formatCount(company.id)}`
    : "Компания";
  elements.companies.detailLoading.classList.toggle("d-none", !detail.isLoading);
  elements.companies.detailError.textContent = detail.error;
  elements.companies.detailError.classList.toggle("d-none", !detail.error);
  elements.companies.detailContent.classList.toggle("d-none", !shouldShowContent);
  elements.companies.detailEditError.textContent = detail.editError;
  elements.companies.detailEditError.classList.toggle("d-none", !detail.editError);
  elements.companies.detailEditButton.classList.toggle("d-none", !shouldShowContent || isEditing);
  elements.companies.detailView.classList.toggle("d-none", isEditing);
  elements.companies.detailEditForm.classList.toggle("d-none", !isEditing);
  elements.companies.detailCancelEditButton.classList.toggle("d-none", !isEditing);
  elements.companies.detailSaveButton.classList.toggle("d-none", !isEditing);
  elements.companies.detailCancelEditButton.disabled = detail.isSubmitting;
  elements.companies.detailSaveButton.disabled = detail.isSubmitting;

  for (const control of elements.companies.detailEditForm.elements) {
    if ("disabled" in control) {
      control.disabled = detail.isSubmitting;
    }
  }

  if (!shouldShowContent) {
    return;
  }

  elements.companies.detailId.textContent = formatCount(company.id);
  elements.companies.detailName.textContent = company.name || "Не указано";
  elements.companies.detailIin.textContent = company.iin || "Не указан";
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

export function renderSupplierDetail() {
  const detail = state.supplierDetail;
  const supplier = detail.data;
  const productLinks = normalizeProductSupplierLinks(supplier?.product_links);
  const shouldShowContent = Boolean(supplier) && !detail.isLoading && !detail.error;
  const isEditing = shouldShowContent && detail.isEditing;
  const shouldShowLinks = shouldShowContent && productLinks.length > 0;

  elements.suppliers.detailTitle.textContent = supplier
    ? supplier.name || `Поставщик #${formatCount(supplier.id)}`
    : "Поставщик";
  elements.suppliers.detailLoading.classList.toggle("d-none", !detail.isLoading);
  elements.suppliers.detailError.textContent = detail.error;
  elements.suppliers.detailError.classList.toggle("d-none", !detail.error);
  elements.suppliers.detailContent.classList.toggle("d-none", !shouldShowContent);
  elements.suppliers.detailEditError.textContent = detail.editError;
  elements.suppliers.detailEditError.classList.toggle("d-none", !detail.editError);
  elements.suppliers.detailEditButton.classList.toggle("d-none", !shouldShowContent || isEditing);
  elements.suppliers.detailView.classList.toggle("d-none", isEditing);
  elements.suppliers.detailEditForm.classList.toggle("d-none", !isEditing);
  elements.suppliers.detailCancelEditButton.classList.toggle("d-none", !isEditing);
  elements.suppliers.detailSaveButton.classList.toggle("d-none", !isEditing);
  elements.suppliers.detailCancelEditButton.disabled = detail.isSubmitting;
  elements.suppliers.detailSaveButton.disabled = detail.isSubmitting;
  elements.suppliers.detailProductLinksEmpty.classList.toggle("d-none", !shouldShowContent || shouldShowLinks);
  elements.suppliers.detailProductLinksTable.classList.toggle("d-none", !shouldShowLinks);
  elements.suppliers.detailProductLinksBody.replaceChildren();

  for (const control of elements.suppliers.detailEditForm.elements) {
    if ("disabled" in control) {
      control.disabled = detail.isSubmitting;
    }
  }

  if (!shouldShowContent) {
    return;
  }

  elements.suppliers.detailId.textContent = formatCount(supplier.id);
  elements.suppliers.detailName.textContent = supplier.name || "Не указано";
  elements.suppliers.detailPhone.textContent = supplier.phone_number || "Не указан";
  elements.suppliers.detailProductLinksCount.textContent = formatCount(productLinks.length);

  const fragment = document.createDocumentFragment();

  for (const productLink of productLinks) {
    fragment.append(createSupplierProductLinkRow(productLink));
  }

  elements.suppliers.detailProductLinksBody.append(fragment);
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

export function renderRestockDetail() {
  const detail = state.restockDetail;
  const restock = detail.data;
  const lines = normalizeRestockLines(restock?.lines);
  const shouldShowContent = Boolean(restock) && !detail.isLoading && !detail.error;
  const shouldShowLines = shouldShowContent && lines.length > 0;

  elements.restocks.detailTitle.textContent = restock
    ? `Пополнение #${formatCount(restock.id)}`
    : "Пополнение";
  elements.restocks.detailLoading.classList.toggle("d-none", !detail.isLoading);
  elements.restocks.detailError.textContent = detail.error;
  elements.restocks.detailError.classList.toggle("d-none", !detail.error);
  elements.restocks.detailContent.classList.toggle("d-none", !shouldShowContent);
  elements.restocks.detailLinesEmpty.classList.toggle("d-none", !shouldShowContent || shouldShowLines);
  elements.restocks.detailLinesTable.classList.toggle("d-none", !shouldShowLines);
  elements.restocks.detailLinesBody.replaceChildren();

  if (!shouldShowContent) {
    return;
  }

  elements.restocks.detailId.textContent = formatCount(restock.id);
  elements.restocks.detailCreatedAt.textContent = formatDateTime(restock.created_at);
  elements.restocks.detailLinesCount.textContent = `${formatCount(lines.length)} позиций`;
  elements.restocks.detailCosts.textContent = formatCurrency(getRestockLinesCost(lines));
  elements.restocks.detailNote.textContent = String(restock.note || "").trim() || "Без комментария";
  elements.restocks.detailNote.classList.toggle("text-secondary", !String(restock.note || "").trim());

  const fragment = document.createDocumentFragment();

  for (const line of lines) {
    fragment.append(createRestockDetailLineRow(line));
  }

  elements.restocks.detailLinesBody.append(fragment);
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

export function renderSaleDetail() {
  const detail = state.saleDetail;
  const sale = detail.data;
  const lines = normalizeSaleLines(sale?.lines);
  const shouldShowContent = Boolean(sale) && !detail.isLoading && !detail.error;
  const shouldShowLines = shouldShowContent && lines.length > 0;
  const note = String(sale?.note || "").trim();
  const costs = getSaleLinesCost(lines);
  const revenue = getSaleLinesRevenue(lines);

  elements.sales.detailTitle.textContent = sale
    ? `Продажа #${formatCount(sale.id)}`
    : "Продажа";
  elements.sales.detailLoading.classList.toggle("d-none", !detail.isLoading);
  elements.sales.detailError.textContent = detail.error;
  elements.sales.detailError.classList.toggle("d-none", !detail.error);
  elements.sales.detailContent.classList.toggle("d-none", !shouldShowContent);
  elements.sales.detailLinesEmpty.classList.toggle("d-none", !shouldShowContent || shouldShowLines);
  elements.sales.detailLinesTable.classList.toggle("d-none", !shouldShowLines);
  elements.sales.detailLinesBody.replaceChildren();

  if (!shouldShowContent) {
    return;
  }

  elements.sales.detailId.textContent = formatCount(sale.id);
  elements.sales.detailCreatedAt.textContent = formatDateTime(sale.created_at);
  elements.sales.detailLinesCount.textContent = `${formatCount(lines.length)} позиций`;
  elements.sales.detailRevenue.textContent = formatCurrency(revenue);
  elements.sales.detailCosts.textContent = formatCurrency(costs);
  elements.sales.detailProfit.textContent = formatCurrency(revenue - costs);
  elements.sales.detailNote.textContent = note || "Без комментария";
  elements.sales.detailNote.classList.toggle("text-secondary", !note);

  const fragment = document.createDocumentFragment();

  for (const line of lines) {
    fragment.append(createSaleDetailLineRow(line));
  }

  elements.sales.detailLinesBody.append(fragment);
}

export function renderLookup({ kind }) {
  const { lookupKind, lookup, selected, group } = getLookupRenderConfig(kind);

  group.selected.classList.toggle("d-none", !selected);
  group.selectedName.textContent = selected?.name || "";
  group.selectedMeta.textContent = selected
    ? getLookupMeta(lookupKind, selected)
    : "";

  const message = getLookupMessage(lookupKind, lookup);
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
    fragment.append(createLookupResultButton(lookupKind, item));
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

function getLookupRenderConfig(kind) {
  if (kind === "supplier") {
    return {
      lookupKind: "supplier",
      lookup: state.productCreate.supplierLookup,
      selected: state.productCreate.selectedSupplier,
      group: {
        selected: elements.products.supplierSelected,
        selectedName: elements.products.supplierSelectedName,
        selectedMeta: elements.products.supplierSelectedMeta,
        message: elements.products.supplierLookupMessage,
        results: elements.products.supplierResults,
      },
    };
  }

  if (kind === "detailCompany") {
    return {
      lookupKind: "company",
      lookup: state.productDetail.companyLookup,
      selected: state.productDetail.selectedCompany,
      group: {
        selected: elements.products.detailEditCompanySelected,
        selectedName: elements.products.detailEditCompanySelectedName,
        selectedMeta: elements.products.detailEditCompanySelectedMeta,
        message: elements.products.detailEditCompanyLookupMessage,
        results: elements.products.detailEditCompanyResults,
      },
    };
  }

  return {
    lookupKind: "company",
    lookup: state.productCreate.companyLookup,
    selected: state.productCreate.selectedCompany,
    group: {
      selected: elements.products.companySelected,
      selectedName: elements.products.companySelectedName,
      selectedMeta: elements.products.companySelectedMeta,
      message: elements.products.companyLookupMessage,
      results: elements.products.companyResults,
    },
  };
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

  row.className = "product-summary-row";
  row.dataset.productId = String(product.id || "");
  row.tabIndex = 0;
  row.setAttribute("role", "button");
  row.setAttribute("aria-label", `Открыть товар ${product.name || `#${formatCount(product.id)}`}`);
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

function createProductSupplierDetailRow(supplierLink, unit) {
  const row = document.createElement("tr");

  row.append(
    createDetailEntityCell(
      supplierLink.supplier_name || `Поставщик #${formatCount(supplierLink.supplier_id)}`,
      `ID ${formatCount(supplierLink.supplier_id)}`,
      "product-meta",
    ),
    createPlainCell(formatQuantity(supplierLink.quantity, unit)),
    createMoneyCell(supplierLink.purchase_price),
    createPlainCell(`${formatCount(supplierLink.margin_percent)}%`),
    createMoneyCell(supplierLink.sale_price),
    createProductSupplierStatusCell(supplierLink.stock_status),
  );

  return row;
}

function renderProductDetailEditLinks(supplierLinks, unit, isEditing, isSubmitting) {
  elements.products.detailEditLinksEmpty.classList.toggle(
    "d-none",
    !isEditing || supplierLinks.length > 0,
  );
  elements.products.detailEditLinksTable.classList.toggle(
    "d-none",
    !isEditing || supplierLinks.length === 0,
  );
  elements.products.detailEditLinksBody.replaceChildren();
  elements.products.detailNewLinks.replaceChildren();

  if (!isEditing) {
    return;
  }

  const editFragment = document.createDocumentFragment();

  for (const supplierLink of supplierLinks) {
    editFragment.append(createProductSupplierEditRow(supplierLink, unit));
  }

  elements.products.detailEditLinksBody.append(editFragment);

  const draftFragment = document.createDocumentFragment();

  for (const draft of state.productDetail.linkDrafts) {
    draftFragment.append(createProductSupplierDraft(draft, isSubmitting));
  }

  elements.products.detailNewLinks.append(draftFragment);

  for (const draft of state.productDetail.linkDrafts) {
    renderProductDetailNewLinkLookup(draft.id);
  }
}

function setProductDetailEditControlsDisabled(detail) {
  for (const control of elements.products.detailEditForm.elements) {
    if ("disabled" in control) {
      control.disabled = detail.isSubmitting;
    }
  }

  elements.products.detailEditCompanySearchInput.disabled =
    detail.isSubmitting || Boolean(detail.selectedCompany);

  for (const draft of state.productDetail.linkDrafts) {
    renderProductDetailNewLinkLookup(draft.id);
  }
}

function createProductSupplierEditRow(supplierLink, unit) {
  const row = document.createElement("tr");
  const linkValues = state.productDetail.linkEditValues?.[supplierLink.id] || {};

  row.dataset.productLinkId = String(supplierLink.id || "");
  row.append(
    createDetailEntityCell(
      supplierLink.supplier_name || `Поставщик #${formatCount(supplierLink.supplier_id)}`,
      `ID ${formatCount(supplierLink.supplier_id)}`,
      "product-meta",
    ),
    createLinkNumberInputCell({
      field: "quantity",
      value: linkValues.quantity ?? supplierLink.quantity,
      min: 0,
      label: `Остаток поставщика ${supplierLink.supplier_name || supplierLink.supplier_id}`,
      suffix: unit,
    }),
    createLinkNumberInputCell({
      field: "purchase_price",
      value: linkValues.purchase_price ?? supplierLink.purchase_price,
      min: 1,
      label: `Цена закупки поставщика ${supplierLink.supplier_name || supplierLink.supplier_id}`,
    }),
    createLinkNumberInputCell({
      field: "margin_percent",
      value: linkValues.margin_percent ?? supplierLink.margin_percent,
      min: 0,
      label: `Маржа поставщика ${supplierLink.supplier_name || supplierLink.supplier_id}`,
      suffix: "%",
    }),
    createLinkNumberInputCell({
      field: "sale_price",
      value: linkValues.sale_price ?? supplierLink.sale_price,
      min: 1,
      label: `Цена продажи поставщика ${supplierLink.supplier_name || supplierLink.supplier_id}`,
    }),
  );

  return row;
}

function createProductSupplierDraft(draft, isSubmitting) {
  const wrapper = document.createElement("section");
  const header = document.createElement("div");
  const heading = document.createElement("h4");
  const removeButton = document.createElement("button");
  const supplierColumn = document.createElement("div");
  const supplierLabel = document.createElement("label");
  const supplierSearch = document.createElement("input");
  const supplierSelected = document.createElement("div");
  const supplierSelectedText = document.createElement("div");
  const supplierSelectedName = document.createElement("div");
  const supplierSelectedMeta = document.createElement("div");
  const supplierClearButton = document.createElement("button");
  const lookupMessage = document.createElement("div");
  const lookupResults = document.createElement("div");
  const fieldsRow = document.createElement("div");

  wrapper.className = "product-detail-link-draft";
  wrapper.dataset.linkDraftId = String(draft.id);

  header.className = "product-detail-link-draft-header";
  heading.className = "fs-6 mb-0";
  heading.textContent = "Новая связь";
  removeButton.className = "btn btn-sm btn-outline-danger";
  removeButton.type = "button";
  removeButton.textContent = "Удалить";
  removeButton.disabled = isSubmitting;
  removeButton.dataset.removeNewLink = "";
  header.append(heading, removeButton);

  supplierColumn.className = "mb-3";
  supplierLabel.className = "form-label";
  supplierLabel.htmlFor = `product-detail-new-link-${draft.id}-supplier-search`;
  supplierLabel.textContent = "Поставщик";
  supplierSearch.className = "form-control";
  supplierSearch.id = supplierLabel.htmlFor;
  supplierSearch.type = "search";
  supplierSearch.autocomplete = "off";
  supplierSearch.placeholder = "Введите название поставщика";
  supplierSearch.value = draft.searchTerm || "";
  supplierSearch.dataset.newLinkSupplierSearch = "";

  supplierSelected.className = "product-supplier-selected d-none mt-2";
  supplierSelected.dataset.newLinkSelected = "";
  supplierSelectedName.className = "fw-semibold";
  supplierSelectedName.dataset.newLinkSelectedName = "";
  supplierSelectedMeta.className = "product-meta";
  supplierSelectedMeta.dataset.newLinkSelectedMeta = "";
  supplierSelectedText.append(supplierSelectedName, supplierSelectedMeta);
  supplierClearButton.className = "btn btn-sm btn-outline-secondary";
  supplierClearButton.type = "button";
  supplierClearButton.textContent = "Сбросить";
  supplierClearButton.dataset.clearNewLinkSupplier = "";
  supplierSelected.append(supplierSelectedText, supplierClearButton);

  lookupMessage.className = "product-supplier-lookup-message text-secondary small d-none mt-2";
  lookupMessage.dataset.newLinkLookupMessage = "";
  lookupMessage.setAttribute("role", "status");
  lookupResults.className = "list-group product-supplier-results d-none mt-2";
  lookupResults.dataset.newLinkResults = "";
  lookupResults.setAttribute("role", "listbox");
  lookupResults.setAttribute("aria-label", "Найденные поставщики");
  supplierColumn.append(
    supplierLabel,
    supplierSearch,
    supplierSelected,
    lookupMessage,
    lookupResults,
  );

  fieldsRow.className = "row g-3";
  fieldsRow.append(
    createDraftNumberField(draft, "purchase_price", "Цена закупки", 1, 1, true),
    createDraftNumberField(draft, "margin_percent", "Маржа, %", 0, 0, true),
    createDraftNumberField(draft, "sale_price", "Цена продажи", 1, "", false),
    createDraftNumberField(draft, "quantity", "Количество", 0, 0, true),
  );

  wrapper.append(header, supplierColumn, fieldsRow);
  return wrapper;
}

function createLinkNumberInputCell({
  field,
  value,
  min,
  label,
  suffix = "",
}) {
  const cell = document.createElement("td");
  const input = document.createElement("input");

  input.className = "form-control form-control-sm product-detail-link-number";
  input.type = "number";
  input.min = String(min);
  input.step = "1";
  input.required = true;
  input.value = String(value ?? min);
  input.dataset.linkField = field;
  input.setAttribute("aria-label", suffix ? `${label}, ${suffix}` : label);
  cell.append(input);
  return cell;
}

function createDraftNumberField(draft, field, label, min, defaultValue, isRequired) {
  const column = document.createElement("div");
  const labelElement = document.createElement("label");
  const input = document.createElement("input");
  const inputId = `product-detail-new-link-${draft.id}-${field}`;
  const value = draft.values?.[field] ?? defaultValue;

  column.className = "col-12 col-md-6 col-xl-3";
  labelElement.className = "form-label";
  labelElement.htmlFor = inputId;
  labelElement.textContent = label;
  input.className = "form-control";
  input.id = inputId;
  input.type = "number";
  input.min = String(min);
  input.step = "1";
  input.value = value === "" ? "" : String(value);
  input.required = isRequired;
  input.dataset.newLinkField = field;
  column.append(labelElement, input);
  return column;
}

function createProductSupplierStatusCell(status) {
  const cell = document.createElement("td");
  const badge = document.createElement("span");
  const config = STOCK_STATUS[status] || STOCK_STATUS.none;

  badge.className = `badge status-badge ${config.className}`;
  badge.textContent = config.label;
  cell.append(badge);
  return cell;
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

function createPopularTagButton(tag) {
  const button = document.createElement("button");
  const name = normalizeTagName(tag);
  const usageCount = Number(tag?.usage_count);
  const nameElement = document.createElement("span");

  button.className = "btn btn-sm btn-outline-secondary product-popular-tag";
  button.type = "button";
  button.dataset.tagName = name;
  button.title = `Искать товары с тегом ${name}`;
  nameElement.textContent = name;
  button.append(nameElement);

  if (Number.isFinite(usageCount)) {
    const count = document.createElement("span");

    count.className = "badge text-bg-light border";
    count.textContent = formatCount(usageCount);
    button.append(count);
  }

  return button;
}

function createCompanyRow(company) {
  const row = document.createElement("tr");
  const nameCell = document.createElement("td");
  const iinCell = document.createElement("td");
  const name = document.createElement("div");
  const meta = document.createElement("div");

  row.className = "company-summary-row";
  row.tabIndex = 0;
  row.dataset.companyId = String(company.id || "");
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
  const productsCell = document.createElement("td");
  const name = document.createElement("div");
  const meta = document.createElement("div");
  const productsCount = Number(supplier.product_links_count || 0);

  row.className = "supplier-summary-row";
  row.dataset.supplierId = String(supplier.id || "");
  row.tabIndex = 0;
  row.setAttribute("role", "button");
  row.setAttribute("aria-label", `Открыть поставщика ${supplier.name || `#${formatCount(supplier.id)}`}`);
  name.className = "fw-semibold";
  name.textContent = supplier.name || "Без названия";
  meta.className = "supplier-meta";
  meta.textContent = `ID ${formatCount(supplier.id)}`;
  nameCell.append(name, meta);
  phoneCell.textContent = supplier.phone_number || "Не указан";
  productsCell.textContent = formatCount(productsCount);
  productsCell.className = productsCount > 0 ? "fw-semibold" : "text-secondary";
  row.append(nameCell, phoneCell, productsCell);
  return row;
}

function createSupplierProductLinkRow(productLink) {
  const row = document.createElement("tr");

  row.append(
    createDetailEntityCell(
      productLink.product_name || `Товар #${formatCount(productLink.product_id)}`,
      `ID ${formatCount(productLink.product_id)}`,
      "supplier-meta",
    ),
    createPlainCell(formatCount(productLink.quantity)),
    createMoneyCell(productLink.purchase_price),
    createPlainCell(`${formatCount(productLink.margin_percent)}%`),
    createMoneyCell(productLink.sale_price),
    createProductSupplierStatusCell(productLink.stock_status),
  );

  return row;
}

function createRestockRow(restock) {
  const row = document.createElement("tr");

  row.className = "restock-summary-row";
  row.dataset.restockId = String(restock.id || "");
  row.tabIndex = 0;
  row.setAttribute("role", "button");
  row.setAttribute("aria-label", `Открыть пополнение #${formatCount(restock.id)}`);
  row.append(
    createRestockSummaryCell(restock),
    createDateCell(restock.created_at),
    createLineCountCell(restock.lines_count),
    createMoneyCell(restock.costs),
    createNoteCell(restock.note),
  );

  return row;
}

function createRestockDetailLineRow(line) {
  const row = document.createElement("tr");
  const quantity = Number(line.restock_quantity || 0);
  const unitCost = Number(line.unit_cost_snapshot || 0);

  row.append(
    createDetailEntityCell(
      line.product_name || `Товар #${formatCount(line.product_id)}`,
      `ID ${formatCount(line.product_id)}`,
      "restock-meta",
    ),
    createDetailEntityCell(
      line.supplier_name || `Поставщик #${formatCount(line.supplier_id)}`,
      `ID ${formatCount(line.supplier_id)}`,
      "restock-meta",
    ),
    createPlainCell(formatQuantity(quantity, line.quantity_unit_snapshot)),
    createMoneyCell(unitCost),
    createMoneyCell(quantity * unitCost),
  );

  return row;
}

function createSaleDetailLineRow(line) {
  const row = document.createElement("tr");
  const quantity = Number(line.sale_quantity || 0);
  const unitCost = Number(line.unit_cost_snapshot || 0);
  const unitPrice = Number(line.unit_sale_price_snapshot || 0);
  const revenue = quantity * unitPrice;
  const cost = quantity * unitCost;

  row.append(
    createDetailEntityCell(
      line.product_name || `Товар #${formatCount(line.product_id)}`,
      `ID ${formatCount(line.product_id)}`,
      "sale-meta",
    ),
    createDetailEntityCell(
      line.supplier_name || `Поставщик #${formatCount(line.supplier_id)}`,
      `ID ${formatCount(line.supplier_id)}`,
      "sale-meta",
    ),
    createPlainCell(formatQuantity(quantity, line.quantity_unit_snapshot)),
    createMoneyCell(unitCost),
    createMoneyCell(unitPrice),
    createMoneyCell(revenue),
    createMoneyCell(revenue - cost),
  );

  return row;
}

function createDetailEntityCell(titleText, metaText, metaClassName) {
  const cell = document.createElement("td");
  const title = document.createElement("div");
  const meta = document.createElement("div");

  title.className = "fw-semibold";
  title.textContent = titleText;
  meta.className = metaClassName;
  meta.textContent = metaText;
  cell.append(title, meta);
  return cell;
}

function createRestockSummaryCell(restock) {
  const cell = document.createElement("td");
  const title = document.createElement("div");

  cell.className = "restock-summary-cell";
  title.className = "fw-semibold";
  title.textContent = `Пополнение #${formatCount(restock.id)}`;
  cell.append(title);
  return cell;
}

function createSaleRow(sale) {
  const row = document.createElement("tr");

  row.className = "sale-summary-row";
  row.dataset.saleId = String(sale.id || "");
  row.tabIndex = 0;
  row.setAttribute("role", "button");
  row.setAttribute("aria-label", `Открыть продажу #${formatCount(sale.id)}`);
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

function createDateCell(value) {
  const cell = document.createElement("td");
  cell.textContent = formatDateTime(value);
  return cell;
}

function createMoneyCell(value) {
  const cell = document.createElement("td");
  cell.className = "fw-semibold";
  cell.textContent = formatCurrency(value);
  return cell;
}

function createPlainCell(value) {
  const cell = document.createElement("td");
  cell.textContent = value;
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
  if (kind === "supplier") {
    return `ID ${formatCount(item.id)} | ${item.phone_number || "Телефон не указан"}`;
  }

  if (item.iin === undefined) {
    return `ID ${formatCount(item.id)}`;
  }

  return `ID ${formatCount(item.id)} | ИИН ${item.iin || "Не указан"}`;
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
    .map((tag) => normalizeTagName(tag))
    .filter(Boolean);
}

function normalizeTagName(tag) {
  if (typeof tag === "string") {
    return tag.trim();
  }

  return String(tag?.name || "").trim();
}

function normalizeProductSupplierLinks(supplierLinks) {
  return Array.isArray(supplierLinks) ? supplierLinks : [];
}

function getProductDetailTags(product, summary) {
  return normalizeTags(product?.tags || summary?.tags);
}

function renderProductDetailTags(tags) {
  elements.products.detailTags.replaceChildren();
  elements.products.detailTags.classList.toggle("text-secondary", tags.length === 0);

  if (!tags.length) {
    elements.products.detailTags.textContent = "Без тегов";
    return;
  }

  const fragment = document.createDocumentFragment();

  for (const tag of tags) {
    const badge = document.createElement("span");
    badge.className = "badge rounded-pill text-bg-light border";
    badge.textContent = tag;
    fragment.append(badge);
  }

  elements.products.detailTags.append(fragment);
}

function getProductDetailTotalQuantity(supplierLinks) {
  return supplierLinks.reduce(
    (total, supplierLink) => total + Number(supplierLink.quantity || 0),
    0,
  );
}

function normalizeRestockLines(lines) {
  return Array.isArray(lines) ? lines : [];
}

function normalizeSaleLines(lines) {
  return Array.isArray(lines) ? lines : [];
}

function getRestockLinesCost(lines) {
  return lines.reduce(
    (total, line) => total + Number(line.restock_quantity || 0) * Number(line.unit_cost_snapshot || 0),
    0,
  );
}

function getSaleLinesCost(lines) {
  return lines.reduce(
    (total, line) => total + Number(line.sale_quantity || 0) * Number(line.unit_cost_snapshot || 0),
    0,
  );
}

function getSaleLinesRevenue(lines) {
  return lines.reduce(
    (total, line) => total + Number(line.sale_quantity || 0) * Number(line.unit_sale_price_snapshot || 0),
    0,
  );
}
