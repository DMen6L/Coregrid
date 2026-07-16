const DEFAULT_VIEW = "dashboard";

export const elements = {
  appMessage: getElement("#app-message"),
  navTabs: Array.from(document.querySelectorAll("[data-view-tab]")),
  views: {
    dashboard: getElement("#dashboard"),
    products: getElement("#products"),
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
};

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

function createProductRow(product) {
  const row = document.createElement("tr");

  row.append(
    createProductNameCell(product),
    createStatusCell(product.stock_status),
    createTextCell(formatQuantity(product.quantity, product.quantity_unit)),
    createTextCell(formatCurrency(product.sale_price)),
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

  cell.append(name, meta);
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

function createOwnerCell(product) {
  const cell = document.createElement("td");
  const supplier = product.supplier_name || "Поставщик не указан";
  const company = product.company_name || "Компания не указана";

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

function createTextCell(text) {
  const cell = document.createElement("td");
  cell.textContent = text;
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

function formatQuantity(quantity, unit) {
  const unitLabel = unit || "шт";
  return `${formatCount(quantity)} ${unitLabel}`;
}

function getElement(selector) {
  const element = document.querySelector(selector);

  if (!element) {
    throw new Error(`Required element not found: ${selector}`);
  }

  return element;
}
