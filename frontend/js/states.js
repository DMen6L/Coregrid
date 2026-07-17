const DEFAULT_VIEW = "dashboard";

export const elements = {
  appMessage: getElement("#app-message"),
  navTabs: Array.from(document.querySelectorAll("[data-view-tab]")),
  navMenuToggles: Array.from(
    document.querySelectorAll("[data-view-menu-toggle], [data-view-menu-views]"),
  ),
  views: {
    dashboard: getElement("#dashboard"),
    products: getElement("#products"),
    companies: getElement("#companies"),
  },
  dashboard: {
    salesValueCard: getElement("#dashboard-sales-value-card"),
    salesCountCard: getElement("#dashboard-sales-count-card"),
    lowStockCard: getElement("#dashboard-low-stock"),
    outOfStockCard: getElement("#dashboard-out-of-stock"),
  },
  products: {
    searchForm: getElement("#products-search-form"),
    searchInput: getElement("#products-search-input"),
    searchButton: getElement("#products-search-button"),
    openCreateModalButton: getElement("#open-product-create-modal-button"),
    createModal: getElement("#product-create-modal"),
    createForm: getElement("#product-create-form"),
    createSubmitButton: getElement("#product-create-submit-button"),
    createError: getElement("#product-create-error"),
    count: getElement("#products-count"),
    loading: getElement("#products-loading"),
    error: getElement("#products-error"),
    empty: getElement("#products-empty"),
    table: getElement("#products-table"),
    tableBody: getElement("#products-table-body"),
    pagination: getElement("#products-pagination"),
    previousPageButton: getElement("#products-previous-page-button"),
    nextPageButton: getElement("#products-next-page-button"),
    pageSummary: getElement("#products-page-summary"),
  },
  companies: {
    searchForm: getElement("#companies-search-form"),
    searchInput: getElement("#companies-search-input"),
    searchButton: getElement("#companies-search-button"),
    count: getElement("#companies-count"),
    loading: getElement("#companies-loading"),
    error: getElement("#companies-error"),
    empty: getElement("#companies-empty"),
    table: getElement("#companies-table"),
    tableBody: getElement("#companies-table-body"),
    pagination: getElement("#companies-pagination"),
    previousPageButton: getElement("#companies-previous-page-button"),
    nextPageButton: getElement("#companies-next-page-button"),
    pageSummary: getElement("#companies-page-summary"),
  },
};

export const state = {
  activeView: DEFAULT_VIEW,
  appMessage: "",
  sales: {
    value: 0,
    count: 0,
  },
  products: {
    list: [],
    searchTerm: "",
    lowStock: 0,
    outOfStock: 0,
    isLoading: true,
    error: "",
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    isCreating: false,
  },
  companies: {
    list: [],
    searchTerm: "",
    isLoading: true,
    error: "",
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
  },
};

export function setState(path, value) {
  const keys = path.split(".");
  let target = state;

  for (let index = 0; index < keys.length - 1; index += 1) {
    target = target[keys[index]];
  }

  const finalKey = keys[keys.length - 1];
  target[finalKey] = value;

  const binding = stateBindings[path];

  if (binding) {
    binding.update(value);
  }
}

export function setActiveView(viewName) {
  const nextView = elements.views[viewName] ? viewName : DEFAULT_VIEW;
  state.activeView = nextView;

  for (const tab of elements.navTabs) {
    const isActive = tab.dataset.viewTab === nextView;
    tab.classList.toggle("active", isActive);
    tab.setAttribute("aria-selected", String(isActive));

    if (isActive) {
      tab.setAttribute("aria-current", "page");
    } else {
      tab.removeAttribute("aria-current");
    }
  }

  for (const toggle of elements.navMenuToggles) {
    const viewNames = getMenuToggleViews(toggle);
    const isActive = viewNames.includes(nextView);
    toggle.classList.toggle("active", isActive);

    if (isActive) {
      toggle.setAttribute("aria-current", "page");
    } else {
      toggle.removeAttribute("aria-current");
    }
  }

  for (const [viewKey, view] of Object.entries(elements.views)) {
    const isActive = viewKey === nextView;
    view.classList.toggle("d-none", !isActive);
    view.hidden = !isActive;
  }
}

export function setAppMessage(message) {
  state.appMessage = message;
  elements.appMessage.textContent = message;
  elements.appMessage.classList.toggle("d-none", !message);
}

export function setProductsLoading(isLoading) {
  state.products.isLoading = isLoading;
  elements.products.searchButton.disabled = isLoading;
  updatePaginationControls();
  renderProducts(state.products.list);
}

export function setProductsError(message) {
  state.products.error = message;
  elements.products.error.textContent = message;
  elements.products.error.classList.toggle("d-none", !message);
  renderProducts(state.products.list);
}

export function setProductsSearchTerm(searchTerm) {
  state.products.searchTerm = searchTerm;
  renderProducts(state.products.list);
}

export function setProductsPagination(pagination) {
  state.products.page = pagination.page;
  state.products.pageSize = pagination.pageSize;
  state.products.total = pagination.total;
  state.products.totalPages = pagination.totalPages;
  state.products.hasNext = pagination.hasNext;
  state.products.hasPrevious = pagination.hasPrevious;
  renderProducts(state.products.list);
}

export function setProductCreateSubmitting(isSubmitting) {
  state.products.isCreating = isSubmitting;
  elements.products.createSubmitButton.disabled = isSubmitting;
  elements.products.openCreateModalButton.disabled = isSubmitting;
  elements.products.createSubmitButton.textContent = isSubmitting
    ? "Создание..."
    : "Создать товар";
}

export function setProductCreateError(message) {
  elements.products.createError.textContent = message;
  elements.products.createError.classList.toggle("d-none", !message);
}

export function resetProductCreateForm() {
  elements.products.createForm.reset();
  setProductCreateError("");
}

export function setCompaniesLoading(isLoading) {
  state.companies.isLoading = isLoading;
  elements.companies.searchButton.disabled = isLoading;
  updateCompaniesPaginationControls();
  renderCompanies(state.companies.list);
}

export function setCompaniesError(message) {
  state.companies.error = message;
  elements.companies.error.textContent = message;
  elements.companies.error.classList.toggle("d-none", !message);
  renderCompanies(state.companies.list);
}

export function setCompaniesSearchTerm(searchTerm) {
  state.companies.searchTerm = searchTerm;
  renderCompanies(state.companies.list);
}

export function setCompaniesPagination(pagination) {
  state.companies.page = pagination.page;
  state.companies.pageSize = pagination.pageSize;
  state.companies.total = pagination.total;
  state.companies.totalPages = pagination.totalPages;
  state.companies.hasNext = pagination.hasNext;
  state.companies.hasPrevious = pagination.hasPrevious;
  renderCompanies(state.companies.list);
}

const stateBindings = {
  "sales.value": {
    update(value) {
      elements.dashboard.salesValueCard.textContent = formatCurrency(value);
    },
  },

  "sales.count": {
    update(value) {
      elements.dashboard.salesCountCard.textContent = formatCount(value);
    },
  },

  "products.list": {
    update(products) {
      renderProducts(products);
    },
  },

  "products.lowStock": {
    update(value) {
      elements.dashboard.lowStockCard.textContent = formatCount(value);
    },
  },

  "products.outOfStock": {
    update(value) {
      elements.dashboard.outOfStockCard.textContent = formatCount(value);
    },
  },

  "companies.list": {
    update(companies) {
      renderCompanies(companies);
    },
  },
};

function getMenuToggleViews(toggle) {
  const views = toggle.dataset.viewMenuViews || toggle.dataset.viewMenuToggle || "";
  return views.split(" ").filter(Boolean);
}

function renderProducts(products) {
  const productList = Array.isArray(products) ? products : [];
  const hasProducts = productList.length > 0;
  const shouldShowTable = hasProducts && !state.products.isLoading;
  const shouldShowEmpty =
    !hasProducts && !state.products.isLoading && !state.products.error;

  elements.products.count.textContent = formatProductsCount(state.products.total);
  elements.products.loading.classList.toggle("d-none", !state.products.isLoading);
  elements.products.empty.textContent = state.products.searchTerm
    ? "По запросу ничего не найдено."
    : "Товары пока не добавлены.";
  elements.products.empty.classList.toggle("d-none", !shouldShowEmpty);
  elements.products.table.classList.toggle("d-none", !shouldShowTable);
  updatePaginationControls();

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

function updatePaginationControls() {
  const shouldShowPagination =
    state.products.total > 0 && !state.products.isLoading && !state.products.error;
  const totalPages = Math.max(state.products.totalPages, 1);

  elements.products.pagination.classList.toggle("d-none", !shouldShowPagination);
  elements.products.previousPageButton.disabled =
    state.products.isLoading || !state.products.hasPrevious;
  elements.products.nextPageButton.disabled =
    state.products.isLoading || !state.products.hasNext;
  elements.products.pageSummary.textContent =
    `Страница ${formatCount(state.products.page)} из ${formatCount(totalPages)}`;
}

function renderCompanies(companies) {
  const companyList = Array.isArray(companies) ? companies : [];
  const hasCompanies = companyList.length > 0;
  const shouldShowTable = hasCompanies && !state.companies.isLoading;
  const shouldShowEmpty =
    !hasCompanies && !state.companies.isLoading && !state.companies.error;

  elements.companies.count.textContent = formatCompaniesCount(state.companies.total);
  elements.companies.loading.classList.toggle("d-none", !state.companies.isLoading);
  elements.companies.empty.textContent = state.companies.searchTerm
    ? "По запросу ничего не найдено."
    : "Компании пока не добавлены.";
  elements.companies.empty.classList.toggle("d-none", !shouldShowEmpty);
  elements.companies.table.classList.toggle("d-none", !shouldShowTable);
  updateCompaniesPaginationControls();

  elements.companies.tableBody.replaceChildren();

  if (!shouldShowTable) {
    return;
  }

  const fragment = document.createDocumentFragment();

  for (const company of companyList) {
    fragment.append(createCompanyRow(company));
  }

  elements.companies.tableBody.append(fragment);
}

function updateCompaniesPaginationControls() {
  const shouldShowPagination =
    state.companies.total > 0 && !state.companies.isLoading && !state.companies.error;
  const totalPages = Math.max(state.companies.totalPages, 1);

  elements.companies.pagination.classList.toggle("d-none", !shouldShowPagination);
  elements.companies.previousPageButton.disabled =
    state.companies.isLoading || !state.companies.hasPrevious;
  elements.companies.nextPageButton.disabled =
    state.companies.isLoading || !state.companies.hasNext;
  elements.companies.pageSummary.textContent =
    `Страница ${formatCount(state.companies.page)} из ${formatCount(totalPages)}`;
}

function createCompanyRow(company) {
  const row = document.createElement("tr");

  const companyCell = document.createElement("td");
  const name = document.createElement("div");
  name.className = "fw-semibold";
  name.textContent = company.name || "Без названия";

  const meta = document.createElement("div");
  meta.className = "company-meta";
  meta.textContent = `ID ${company.id}`;

  companyCell.append(name, meta);

  const iinCell = document.createElement("td");
  iinCell.textContent = company.iin || "Не указан";

  row.append(companyCell, iinCell);
  return row;
}

function createProductRow(product) {
  const row = document.createElement("tr");

  row.append(
    createProductNameCell(product),
    createStatusCell(product.stock_status),
    createStockCell(product),
    createPricingCell(product),
    createOwnerCell(product),
    createTagsCell(product.tags),
  );

  return row;
}

function createProductNameCell(product) {
  const cell = document.createElement("td");
  cell.className = "product-name-cell";

  const name = document.createElement("div");
  name.className = "fw-semibold";
  name.textContent = product.name || "Без названия";

  const meta = document.createElement("div");
  meta.className = "product-meta";
  meta.textContent = `ID ${product.id}`;

  const createdAt = document.createElement("div");
  createdAt.className = "product-meta";
  createdAt.textContent = `Создано: ${formatDateTime(product.created_at)}`;

  cell.append(name, meta, createdAt);
  return cell;
}

function createStatusCell(status) {
  const cell = document.createElement("td");
  const badge = document.createElement("span");
  const config = getStatusConfig(status);

  badge.className = `badge status-badge ${config.className}`;
  badge.textContent = config.label;

  cell.append(badge);
  return cell;
}

function createStockCell(product) {
  const cell = document.createElement("td");

  const quantity = document.createElement("div");
  quantity.textContent = formatQuantity(product.quantity, product.quantity_unit);

  const threshold = document.createElement("div");
  threshold.className = "product-meta";
  threshold.textContent = `Порог: ${formatCount(product.low_stock_threshold)}`;

  cell.append(quantity, threshold);
  return cell;
}

function createPricingCell(product) {
  const cell = document.createElement("td");

  const salePrice = document.createElement("div");
  salePrice.textContent = `Продажа: ${formatCurrency(product.sale_price)}`;

  const floorPrice = document.createElement("div");
  floorPrice.className = "product-meta";
  floorPrice.textContent = `Минимум: ${formatCurrency(product.floor_price)}`;

  const purchasePrice = document.createElement("div");
  purchasePrice.className = "product-meta";
  purchasePrice.textContent = `Закупка: ${formatCurrency(product.purchase_price)}`;

  const margin = document.createElement("div");
  margin.className = "product-meta";
  margin.textContent = `Маржа: ${formatCount(product.margin_percent)}%`;

  cell.append(salePrice, floorPrice, purchasePrice, margin);
  return cell;
}

function createOwnerCell(product) {
  const cell = document.createElement("td");
  const supplier = product.supplier_name || (
    product.supplier_id ? `Поставщик #${product.supplier_id}` : "Поставщик не указан"
  );
  const company = product.company_name || (
    product.company_id ? `Компания #${product.company_id}` : "Компания не указана"
  );

  const supplierLine = document.createElement("div");
  supplierLine.textContent = supplier;

  const companyLine = document.createElement("div");
  companyLine.className = "product-meta";
  companyLine.textContent = company;

  cell.append(supplierLine, companyLine);
  return cell;
}

function createTagsCell(tags) {
  const cell = document.createElement("td");
  const wrapper = document.createElement("div");
  wrapper.className = "product-tags";
  const tagList = Array.isArray(tags) ? tags : [];

  if (tagList.length === 0) {
    const emptyText = document.createElement("span");
    emptyText.className = "text-secondary";
    emptyText.textContent = "Нет тегов";
    wrapper.append(emptyText);
  } else {
    for (const tag of tagList) {
      const badge = document.createElement("span");
      badge.className = "badge text-bg-light border";
      badge.textContent = tag.name;
      wrapper.append(badge);
    }
  }

  cell.append(wrapper);
  return cell;
}

function getStatusConfig(status) {
  const configs = {
    available: {
      label: "В наличии",
      className: "text-bg-success",
    },
    low: {
      label: "Мало",
      className: "text-bg-warning",
    },
    out: {
      label: "Нет",
      className: "text-bg-danger",
    },
  };

  return configs[status] || {
    label: "Неизвестно",
    className: "text-bg-secondary",
  };
}

function formatCurrency(value) {
  return `${Number(value || 0).toLocaleString("ru-KZ")} тг`;
}

function formatCount(value) {
  return Number(value || 0).toLocaleString("ru-KZ");
}

function formatProductsCount(count) {
  const formattedCount = formatCount(count);
  return count === 1 ? `${formattedCount} товар` : `${formattedCount} товаров`;
}

function formatCompaniesCount(count) {
  const formattedCount = formatCount(count);
  return count === 1 ? `${formattedCount} компания` : `${formattedCount} компаний`;
}

function formatQuantity(quantity, unit) {
  const unitLabel = unit || "шт";
  return `${formatCount(quantity)} ${unitLabel}`;
}

function formatDateTime(value) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Дата неизвестна";
  }

  return date.toLocaleString("ru-KZ", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function getElement(selector) {
  const element = document.querySelector(selector);

  if (!element) {
    throw new Error(`Required element not found: ${selector}`);
  }

  return element;
}
