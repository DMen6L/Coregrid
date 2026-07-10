async function loadAll(options = {}) {
  setBusy(true);

  try {
    const [
      productSummary,
      salesSummary,
      dashboardMovements,
      companies,
      suppliers,
      products,
    ] = await Promise.all([
      request("/products/summary"),
      request(buildSalesSummaryPath()),
      request(buildDashboardMovementsPath()),
      request(buildPagePath("/companies", state.pagination.companies)),
      request(buildPagePath("/suppliers", state.pagination.suppliers)),
      request(buildProductsPath()),
    ]);

    state.productSummary = productSummary;
    state.salesSummary = salesSummary;
    state.dashboardMovements = dashboardMovements.items;
    applyPage("companies", companies);
    applyPage("suppliers", suppliers);
    applyPage("products", products);

    render();

    if (!options.quiet) {
      showNotice("Данные загружены.");
    }
  } catch (error) {
    showNotice(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function loadDashboard() {
  setBusy(true);

  try {
    const [productSummary, salesSummary, dashboardMovements] = await Promise.all([
      request("/products/summary"),
      request(buildSalesSummaryPath()),
      request(buildDashboardMovementsPath()),
    ]);

    state.productSummary = productSummary;
    state.salesSummary = salesSummary;
    state.dashboardMovements = dashboardMovements.items;
    render();
    showNotice("Дашборд обновлен.");
  } catch (error) {
    showNotice(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Accept", "application/json");

  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response;

  try {
    response = await fetch(`${state.apiBase}${path}`, {
      ...options,
      headers,
    });
  } catch {
    throw new Error(`Не удалось подключиться к API по адресу ${state.apiBase}`);
  }

  if (response.status === 204) {
    return null;
  }

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(formatApiError(payload, response.status));
  }

  return payload;
}

function buildProductsPath() {
  return buildPagePath("/products", state.pagination.products, {
    search: state.searchTerm,
    tags: state.selectedTagFilters,
    stock: state.stockFilter,
    sort: state.productSort,
    order: state.productSortOrder,
  });
}

function buildTagSearchPath(searchTerm) {
  const query = new URLSearchParams({
    page: "1",
    page_size: String(DEFAULT_TAG_SEARCH_PAGE_SIZE),
    search: searchTerm,
  });

  return `/tags?${query.toString()}`;
}

function buildMovementProductSearchPath(searchTerm) {
  const query = new URLSearchParams({
    page: "1",
    page_size: String(DEFAULT_MOVEMENT_PRODUCT_SEARCH_PAGE_SIZE),
    search: searchTerm,
    stock: "all",
  });

  return `/products?${query.toString()}`;
}

function buildDashboardMovementsPath() {
  const query = new URLSearchParams({
    page: "1",
    page_size: String(DEFAULT_DASHBOARD_MOVEMENT_PAGE_SIZE),
    order: "latest",
  });

  return `/stock-movements?${query.toString()}`;
}

function buildSalesSummaryPath() {
  const query = new URLSearchParams({
    date_from: state.salesDateFrom,
    date_to: state.salesDateTo,
  });

  return `/stock-movements/sales-summary?${query.toString()}`;
}

function buildPagePath(path, pagination, params = {}) {
  const query = new URLSearchParams({
    page: String(pagination.page),
    page_size: String(pagination.pageSize),
  });

  Object.entries(params).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.forEach((item) => {
        if (item !== null && item !== undefined && item !== "") {
          query.append(key, item);
        }
      });
      return;
    }

    if (value !== null && value !== undefined && value !== "" && value !== "all") {
      query.set(key, value);
    }
  });

  return `${path}?${query.toString()}`;
}

function applyPage(type, payload) {
  state[type] = payload.items;
  state.pagination[type] = {
    ...state.pagination[type],
    page: payload.page,
    pageSize: payload.page_size,
    total: payload.total,
    pages: payload.pages,
  };

  if (type === "products") {
    rememberMovementProducts(payload.items);
  }
}

async function loadPage(type) {
  setBusy(true);

  try {
    const path = getPagePath(type);
    const payload = await request(path);

    applyPage(type, payload);
    if (type === "stockMovements") {
      state.stockMovementsLoaded = true;
    }
    render();
  } catch (error) {
    showNotice(error.message, true);
  } finally {
    setBusy(false);
  }
}

function getPagePath(type) {
  if (type === "products") {
    return buildProductsPath();
  }

  if (type === "stockMovements") {
    return buildPagePath("/stock-movements", state.pagination.stockMovements);
  }

  return buildPagePath(`/${type}`, state.pagination[type]);
}

function formatApiError(payload, status) {
  if (!payload || payload.detail === undefined) {
    return `Запрос завершился с ошибкой ${status}`;
  }

  if (typeof payload.detail === "string") {
    return BACKEND_ERROR_MESSAGES[payload.detail] || payload.detail;
  }

  if (Array.isArray(payload.detail)) {
    return payload.detail.map(formatValidationIssue).join(" ");
  }

  return `Запрос завершился с ошибкой ${status}`;
}

function formatValidationIssue(issue) {
  const field = Array.isArray(issue.loc)
    ? issue.loc.filter((part) => part !== "body").at(-1)
    : null;
  const label = FIELD_LABELS[field] || "Поле";

  return `${label}: ${translateValidationMessage(issue.msg, field)}`;
}

function translateValidationMessage(message, field = null) {
  if (message.includes("should match pattern")) {
    if (field === "phone_number") {
      return "значение должно быть в формате 8XXXXXXXXXX или +7XXXXXXXXXX.";
    }

    return "значение должно состоять из 12 цифр.";
  }

  if (message.includes("should have at least")) {
    return "значение не должно быть пустым.";
  }

  if (message.includes("greater than or equal to 0")) {
    return "значение должно быть 0 или больше.";
  }

  if (message.includes("greater than 0")) {
    return "значение должно быть больше 0.";
  }

  if (message.includes("cannot be empty")) {
    return "нужно заполнить хотя бы одно поле.";
  }

  if (message.includes("sale_price cannot be lower than floor_price")) {
    return "цена продажи не может быть ниже минимальной цены.";
  }

  return message;
}

async function handleDashboardSalesSubmit(event) {
  event.preventDefault();

  const dateFrom = refs.dashboardSalesDateFrom.value;
  const dateTo = refs.dashboardSalesDateTo.value;

  if (!dateFrom || !dateTo) {
    showNotice("Укажите период продаж.", true);
    return;
  }

  if (dateFrom > dateTo) {
    showNotice("Дата начала не может быть позже даты окончания.", true);
    return;
  }

  state.salesDateFrom = dateFrom;
  state.salesDateTo = dateTo;
  setBusy(true);

  try {
    state.salesSummary = await request(buildSalesSummaryPath());
    renderDashboard();
    showNotice("Продажи обновлены.");
  } catch (error) {
    showNotice(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function handleApiSettingsSubmit(event) {
  event.preventDefault();

  state.apiBase = refs.apiBase.value.trim().replace(/\/$/, "") || DEFAULT_API_BASE;
  refs.apiBase.value = state.apiBase;
  localStorage.setItem(API_BASE_STORAGE_KEY, state.apiBase);

  await loadAll();
}

function handlePaginationClick(event) {
  const button = event.target.closest("button[data-pagination-action]");

  if (!button || button.disabled) {
    return;
  }

  const type = button.dataset.paginationTarget;
  const action = button.dataset.paginationAction;
  const pagination = state.pagination[type];
  const nextPage =
    action === "next" ? pagination.page + 1 : pagination.page - 1;

  if (nextPage < 1 || (pagination.pages > 0 && nextPage > pagination.pages)) {
    return;
  }

  pagination.page = nextPage;
  loadPage(type);
}
