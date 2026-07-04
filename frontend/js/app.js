const DEFAULT_API_BASE = "http://127.0.0.1:8000";
const API_BASE_STORAGE_KEY = "coregrid.apiBase";
const DEFAULT_LOW_STOCK_THRESHOLD = 5;
const DEFAULT_PRODUCT_PAGE_SIZE = 25;
const DEFAULT_LOOKUP_PAGE_SIZE = 10;
const DEFAULT_MOVEMENT_PAGE_SIZE = 25;

const STOCK_STATUS_LABELS = {
  available: "В наличии",
  low: "Мало",
  out: "Нет на складе",
};

const MOVEMENT_TYPE_LABELS = {
  in: "Приход",
  out: "Расход",
  adjustment: "Корректировка",
};

const BACKEND_ERROR_MESSAGES = {
  "Duplicate value conflicts existing row": "Такое значение уже используется.",
  "Referenced row does not exist or was changed":
    "Связанная запись не существует или была изменена.",
  "Company not found": "Компания не найдена.",
  "Supplier not found": "Поставщик не найден.",
  "Product not found": "Товар не найден.",
  "Stock movement would make product quantity negative":
    "Движение не может сделать остаток товара отрицательным.",
};

const FIELD_LABELS = {
  name: "Название",
  iin: "ИИН",
  phone_number: "Телефон",
  price: "Цена",
  quantity: "Количество",
  low_stock_threshold: "Порог малого остатка",
  company_id: "Компания",
  supplier_id: "Поставщик",
  movement_type: "Тип движения",
  product_id: "Товар",
  quantity_delta: "Изменение",
  note: "Заметка",
};

const state = {
  apiBase: localStorage.getItem(API_BASE_STORAGE_KEY) || DEFAULT_API_BASE,
  companies: [],
  suppliers: [],
  products: [],
  stockMovements: [],
  productSummary: {
    total_products: 0,
    total_units: 0,
    inventory_value: 0,
    low_stock: 0,
  },
  pagination: {
    companies: createPageState(DEFAULT_LOOKUP_PAGE_SIZE),
    suppliers: createPageState(DEFAULT_LOOKUP_PAGE_SIZE),
    products: createPageState(DEFAULT_PRODUCT_PAGE_SIZE),
    stockMovements: createPageState(DEFAULT_MOVEMENT_PAGE_SIZE),
  },
  activeTab: "products",
  stockMovementsLoaded: false,
  editingProductId: null,
  searchTerm: "",
  stockFilter: "all",
};

const refs = {
  tabButtons: [...document.querySelectorAll("[data-tab-target]")],
  tabPanels: [...document.querySelectorAll("[data-tab-panel]")],
  apiSettings: document.querySelector("#api-settings"),
  apiBase: document.querySelector("#api-base"),
  notice: document.querySelector("#notice"),
  refreshButton: document.querySelector("#refresh-button"),
  totalProducts: document.querySelector("#total-products"),
  totalUnits: document.querySelector("#total-units"),
  inventoryValue: document.querySelector("#inventory-value"),
  lowStock: document.querySelector("#low-stock"),
  productSearch: document.querySelector("#product-search"),
  stockFilter: document.querySelector("#stock-filter"),
  productTableBody: document.querySelector("#products-table-body"),
  productPagination: document.querySelector("#product-pagination"),
  productPageInfo: document.querySelector("#product-page-info"),
  productForm: document.querySelector("#product-form"),
  productFormTitle: document.querySelector("#product-form-title"),
  productId: document.querySelector("#product-id"),
  productName: document.querySelector("#product-name"),
  productPrice: document.querySelector("#product-price"),
  productQuantity: document.querySelector("#product-quantity"),
  productLowStockThreshold: document.querySelector(
    "#product-low-stock-threshold",
  ),
  productCompany: document.querySelector("#product-company"),
  productSupplier: document.querySelector("#product-supplier"),
  productSubmit: document.querySelector("#product-submit"),
  cancelEdit: document.querySelector("#cancel-edit"),
  companyForm: document.querySelector("#company-form"),
  companyName: document.querySelector("#company-name"),
  companyIin: document.querySelector("#company-iin"),
  companyTableBody: document.querySelector("#company-table-body"),
  companyPagination: document.querySelector("#company-pagination"),
  companyPageInfo: document.querySelector("#company-page-info"),
  supplierForm: document.querySelector("#supplier-form"),
  supplierName: document.querySelector("#supplier-name"),
  supplierPhone: document.querySelector("#supplier-phone"),
  supplierTableBody: document.querySelector("#supplier-table-body"),
  supplierPagination: document.querySelector("#supplier-pagination"),
  supplierPageInfo: document.querySelector("#supplier-page-info"),
  movementRefreshButton: document.querySelector("#movement-refresh-button"),
  movementTableBody: document.querySelector("#movement-table-body"),
  movementPagination: document.querySelector("#movement-pagination"),
  movementPageInfo: document.querySelector("#movement-page-info"),
  movementForm: document.querySelector("#movement-form"),
  movementType: document.querySelector("#movement-type"),
  movementProductId: document.querySelector("#movement-product-id"),
  movementProductOptions: document.querySelector("#movement-product-options"),
  movementQuantity: document.querySelector("#movement-quantity"),
  movementQuantityLabel: document.querySelector("#movement-quantity-label"),
  movementNote: document.querySelector("#movement-note"),
  movementSubmit: document.querySelector("#movement-submit"),
};

document.addEventListener("DOMContentLoaded", init);

function init() {
  refs.apiBase.value = state.apiBase;

  refs.tabButtons.forEach((button) => {
    button.addEventListener("click", handleTabClick);
  });
  refs.apiSettings.addEventListener("submit", handleApiSettingsSubmit);
  refs.refreshButton.addEventListener("click", loadAll);
  refs.productSearch.addEventListener("input", handleSearchInput);
  refs.stockFilter.addEventListener("change", handleStockFilterChange);
  refs.productForm.addEventListener("submit", handleProductSubmit);
  refs.cancelEdit.addEventListener("click", resetProductForm);
  refs.productTableBody.addEventListener("click", handleProductTableClick);
  refs.productPagination.addEventListener("click", handlePaginationClick);
  refs.companyForm.addEventListener("submit", handleCompanySubmit);
  refs.companyTableBody.addEventListener("click", handleCompanyTableClick);
  refs.companyPagination.addEventListener("click", handlePaginationClick);
  refs.supplierForm.addEventListener("submit", handleSupplierSubmit);
  refs.supplierTableBody.addEventListener("click", handleSupplierTableClick);
  refs.supplierPagination.addEventListener("click", handlePaginationClick);
  refs.movementRefreshButton.addEventListener("click", () => {
    loadPage("stockMovements");
  });
  refs.movementPagination.addEventListener("click", handlePaginationClick);
  refs.movementForm.addEventListener("submit", handleMovementSubmit);
  refs.movementType.addEventListener("change", updateMovementQuantityMode);

  updateMovementQuantityMode();
  loadAll();
}

async function loadAll(options = {}) {
  setBusy(true);

  try {
    const [companies, suppliers, products, productSummary] = await Promise.all([
      request(buildPagePath("/companies", state.pagination.companies)),
      request(buildPagePath("/suppliers", state.pagination.suppliers)),
      request(buildProductsPath()),
      request("/products/summary"),
    ]);

    applyPage("companies", companies);
    applyPage("suppliers", suppliers);
    applyPage("products", products);
    state.productSummary = productSummary;

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

function createPageState(pageSize) {
  return {
    page: 1,
    pageSize,
    total: 0,
    pages: 0,
  };
}

function buildProductsPath() {
  return buildPagePath("/products", state.pagination.products, {
    search: state.searchTerm,
    stock: state.stockFilter,
  });
}

function buildPagePath(path, pagination, params = {}) {
  const query = new URLSearchParams({
    page: String(pagination.page),
    page_size: String(pagination.pageSize),
  });

  Object.entries(params).forEach(([key, value]) => {
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

  return `${label}: ${translateValidationMessage(issue.msg)}`;
}

function translateValidationMessage(message) {
  if (message.includes("should match pattern")) {
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

  return message;
}

function render() {
  renderTabs();
  renderSummary();
  renderProductTable();
  renderSelects();
  renderLookupTable("company");
  renderLookupTable("supplier");
  renderMovementTable();
  renderMovementProductOptions();
  renderPagination("products");
  renderPagination("companies");
  renderPagination("suppliers");
  renderPagination("stockMovements");
}

function renderTabs() {
  refs.tabButtons.forEach((button) => {
    const isActive = button.dataset.tabTarget === state.activeTab;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-selected", String(isActive));
  });

  refs.tabPanels.forEach((panel) => {
    panel.classList.toggle("hidden", panel.dataset.tabPanel !== state.activeTab);
  });
}

function renderSummary() {
  refs.totalProducts.textContent = formatNumber(
    state.productSummary.total_products,
  );
  refs.totalUnits.textContent = formatNumber(state.productSummary.total_units);
  refs.inventoryValue.textContent = formatNumber(
    state.productSummary.inventory_value,
  );
  refs.lowStock.textContent = formatNumber(state.productSummary.low_stock);
}

function renderProductTable() {
  if (state.products.length === 0) {
    refs.productTableBody.innerHTML = `
      <tr>
        <td colspan="8">
          <div class="empty-state">Нет товаров для текущего фильтра.</div>
        </td>
      </tr>
    `;
    return;
  }

  refs.productTableBody.innerHTML = state.products
    .map((product) => {
      const companyName = product.company_name ?? getCompanyName(product.company_id);
      const supplierName =
        product.supplier_name ?? getSupplierName(product.supplier_id);

      return `
        <tr>
          <td><strong>${escapeHtml(product.name)}</strong></td>
          <td>${formatNumber(product.price)}</td>
          <td>${formatNumber(product.quantity)}</td>
          <td>${renderStockStatus(product)}</td>
          <td>${escapeHtml(companyName)}</td>
          <td>${escapeHtml(supplierName)}</td>
          <td>${formatDate(product.created_at)}</td>
          <td>
            <div class="actions">
              <button class="secondary-button" type="button" data-action="edit" data-id="${product.id}">Изменить</button>
              <button class="danger-button" type="button" data-action="delete" data-id="${product.id}">Удалить</button>
            </div>
          </td>
        </tr>
      `;
    })
    .join("");
}

function renderStockStatus(product) {
  const status = getStockStatus(product);
  const label = STOCK_STATUS_LABELS[status] || status;
  const className = status === "low" || status === "out" ? ` status-${status}` : "";

  return `<span class="status-pill${className}">${escapeHtml(label)}</span>`;
}

function getStockStatus(product) {
  if (product.stock_status) {
    return product.stock_status;
  }

  if (product.quantity === 0) {
    return "out";
  }

  const threshold = product.low_stock_threshold ?? DEFAULT_LOW_STOCK_THRESHOLD;
  if (threshold > 0 && product.quantity <= threshold) {
    return "low";
  }

  return "available";
}

function renderSelects() {
  const editingProduct = state.products.find(
    (product) => product.id === state.editingProductId,
  );

  renderOptions(
    refs.productCompany,
    state.companies,
    "Без компании",
    editingProduct?.company_id,
    editingProduct?.company_name,
  );
  renderOptions(
    refs.productSupplier,
    state.suppliers,
    "Без поставщика",
    editingProduct?.supplier_id,
    editingProduct?.supplier_name,
  );
}

function renderOptions(select, items, emptyLabel, pinnedId = null, pinnedName = null) {
  const currentValue = select.value;
  const hasPinnedId = pinnedId !== null && pinnedId !== undefined;
  const hasPinnedItem =
    hasPinnedId && items.some((item) => item.id === pinnedId);
  const options = [
    `<option value="">${emptyLabel}</option>`,
    ...items.map(
      (item) => `<option value="${item.id}">${escapeHtml(item.name)}</option>`,
    ),
  ];

  if (hasPinnedId && !hasPinnedItem) {
    options.push(
      `<option value="${pinnedId}">${escapeHtml(pinnedName ?? `#${pinnedId}`)}</option>`,
    );
  }

  select.innerHTML = options.join("");

  if ([...select.options].some((option) => option.value === currentValue)) {
    select.value = currentValue;
  }
}

function renderLookupTable(type) {
  const items = type === "company" ? state.companies : state.suppliers;
  const body =
    type === "company" ? refs.companyTableBody : refs.supplierTableBody;
  const secondaryKey = type === "company" ? "iin" : "phone_number";
  const emptyText =
    type === "company" ? "Компаний пока нет." : "Поставщиков пока нет.";

  if (items.length === 0) {
    body.innerHTML = `
      <tr>
        <td colspan="3">
          <div class="empty-state">${emptyText}</div>
        </td>
      </tr>
    `;
    return;
  }

  body.innerHTML = items
    .map(
      (item) => `
        <tr>
          <td>
            <strong>${escapeHtml(item.name)}</strong>
            <div class="lookup-meta">#${item.id}</div>
          </td>
          <td>${escapeHtml(item[secondaryKey])}</td>
          <td>
            <div class="actions">
              <button class="danger-button" type="button" data-id="${item.id}">Удалить</button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");
}

function renderMovementTable() {
  if (state.stockMovements.length === 0) {
    refs.movementTableBody.innerHTML = `
      <tr>
        <td colspan="5">
          <div class="empty-state">Движений пока нет.</div>
        </td>
      </tr>
    `;
    return;
  }

  refs.movementTableBody.innerHTML = state.stockMovements
    .map(
      (movement) => `
        <tr>
          <td>#${movement.id}</td>
          <td>${escapeHtml(MOVEMENT_TYPE_LABELS[movement.movement_type] || movement.movement_type)}</td>
          <td>${renderMovementLines(movement.lines)}</td>
          <td>${formatDate(movement.created_at)}</td>
          <td>${escapeHtml(movement.note || "-")}</td>
        </tr>
      `,
    )
    .join("");
}

function renderMovementLines(lines) {
  return `
    <div class="movement-lines">
      ${lines
        .map(
          (line) => `
            <div class="movement-line">
              <strong>${escapeHtml(getProductDisplayName(line.product_id))}</strong>:
              ${formatSignedNumber(line.quantity_delta)}
              (${formatNumber(line.quantity_before)} -> ${formatNumber(line.quantity_after)})
            </div>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderMovementProductOptions() {
  refs.movementProductOptions.innerHTML = state.products
    .map(
      (product) =>
        `<option value="${product.id}" label="${escapeHtml(product.name)}"></option>`,
    )
    .join("");
}

function renderPagination(type) {
  const pagination = state.pagination[type];
  const { container, info } = getPaginationRefs(type);
  const previousButton = container.querySelector(
    '[data-pagination-action="prev"]',
  );
  const nextButton = container.querySelector('[data-pagination-action="next"]');
  const start = pagination.total === 0
    ? 0
    : (pagination.page - 1) * pagination.pageSize + 1;
  const end = Math.min(pagination.page * pagination.pageSize, pagination.total);

  info.textContent =
    pagination.total === 0
      ? "Нет записей"
      : `${formatNumber(start)}-${formatNumber(end)} из ${formatNumber(
          pagination.total,
        )}`;
  previousButton.disabled = pagination.page <= 1;
  nextButton.disabled = pagination.pages === 0 || pagination.page >= pagination.pages;
}

function getPaginationRefs(type) {
  if (type === "products") {
    return { container: refs.productPagination, info: refs.productPageInfo };
  }

  if (type === "companies") {
    return { container: refs.companyPagination, info: refs.companyPageInfo };
  }

  if (type === "suppliers") {
    return { container: refs.supplierPagination, info: refs.supplierPageInfo };
  }

  return { container: refs.movementPagination, info: refs.movementPageInfo };
}

function handleTabClick(event) {
  const tab = event.currentTarget.dataset.tabTarget;

  if (tab === state.activeTab) {
    return;
  }

  state.activeTab = tab;
  renderTabs();

  if (tab === "stockMovements" && !state.stockMovementsLoaded) {
    loadPage("stockMovements");
  }
}

async function handleApiSettingsSubmit(event) {
  event.preventDefault();

  state.apiBase = refs.apiBase.value.trim().replace(/\/$/, "") || DEFAULT_API_BASE;
  refs.apiBase.value = state.apiBase;
  localStorage.setItem(API_BASE_STORAGE_KEY, state.apiBase);

  await loadAll();
}

function handleSearchInput(event) {
  state.searchTerm = event.target.value.trim();
  state.pagination.products.page = 1;
  loadPage("products");
}

function handleStockFilterChange(event) {
  state.stockFilter = event.target.value;
  state.pagination.products.page = 1;
  loadPage("products");
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

async function handleProductSubmit(event) {
  event.preventDefault();

  const payload = {
    name: refs.productName.value.trim(),
    price: Number(refs.productPrice.value),
    quantity: Number(refs.productQuantity.value),
    low_stock_threshold: Number(refs.productLowStockThreshold.value),
    company_id: optionalNumber(refs.productCompany.value),
    supplier_id: optionalNumber(refs.productSupplier.value),
  };

  const isEditing = state.editingProductId !== null;
  const path = isEditing ? `/products/${state.editingProductId}` : "/products";
  const method = isEditing ? "PATCH" : "POST";

  try {
    await request(path, {
      method,
      body: JSON.stringify(payload),
    });

    resetProductForm();
    await loadAll({ quiet: true });
    showNotice(isEditing ? "Товар обновлен." : "Товар добавлен.");
  } catch (error) {
    showNotice(error.message, true);
  }
}

function handleProductTableClick(event) {
  const button = event.target.closest("button[data-action]");

  if (!button) {
    return;
  }

  const productId = Number(button.dataset.id);

  if (button.dataset.action === "edit") {
    startProductEdit(productId);
    return;
  }

  if (button.dataset.action === "delete") {
    deleteProduct(productId);
  }
}

function startProductEdit(productId) {
  const product = state.products.find((item) => item.id === productId);

  if (!product) {
    showNotice("Товар не найден в текущих данных.", true);
    return;
  }

  state.editingProductId = product.id;
  renderSelects();
  refs.productId.value = product.id;
  refs.productName.value = product.name;
  refs.productPrice.value = product.price;
  refs.productQuantity.value = product.quantity;
  refs.productLowStockThreshold.value =
    product.low_stock_threshold ?? DEFAULT_LOW_STOCK_THRESHOLD;
  refs.productCompany.value = product.company_id ?? "";
  refs.productSupplier.value = product.supplier_id ?? "";
  refs.productFormTitle.textContent = "Изменить товар";
  refs.productSubmit.textContent = "Сохранить";
  refs.cancelEdit.classList.remove("hidden");
  refs.productName.focus();
}

function resetProductForm() {
  state.editingProductId = null;
  refs.productForm.reset();
  renderSelects();
  refs.productQuantity.value = 0;
  refs.productLowStockThreshold.value = DEFAULT_LOW_STOCK_THRESHOLD;
  refs.productCompany.value = "";
  refs.productSupplier.value = "";
  refs.productFormTitle.textContent = "Добавить товар";
  refs.productSubmit.textContent = "Добавить товар";
  refs.cancelEdit.classList.add("hidden");
}

async function deleteProduct(productId) {
  const product = state.products.find((item) => item.id === productId);
  const productName = product ? product.name : `#${productId}`;

  if (!window.confirm(`Удалить товар "${productName}"?`)) {
    return;
  }

  try {
    await request(`/products/${productId}`, { method: "DELETE" });
    resetProductForm();
    await loadAll({ quiet: true });
    showNotice("Товар удален.");
  } catch (error) {
    showNotice(error.message, true);
  }
}

async function handleCompanySubmit(event) {
  event.preventDefault();

  try {
    await request("/companies", {
      method: "POST",
      body: JSON.stringify({
        name: refs.companyName.value.trim(),
        iin: refs.companyIin.value.trim(),
      }),
    });

    refs.companyForm.reset();
    await loadAll({ quiet: true });
    showNotice("Компания добавлена.");
  } catch (error) {
    showNotice(error.message, true);
  }
}

function handleCompanyTableClick(event) {
  const button = event.target.closest("button[data-id]");

  if (button) {
    deleteLookup("company", Number(button.dataset.id));
  }
}

async function handleSupplierSubmit(event) {
  event.preventDefault();

  try {
    await request("/suppliers", {
      method: "POST",
      body: JSON.stringify({
        name: refs.supplierName.value.trim(),
        phone_number: refs.supplierPhone.value.trim(),
      }),
    });

    refs.supplierForm.reset();
    await loadAll({ quiet: true });
    showNotice("Поставщик добавлен.");
  } catch (error) {
    showNotice(error.message, true);
  }
}

function handleSupplierTableClick(event) {
  const button = event.target.closest("button[data-id]");

  if (button) {
    deleteLookup("supplier", Number(button.dataset.id));
  }
}

function updateMovementQuantityMode() {
  if (refs.movementType.value === "adjustment") {
    refs.movementQuantityLabel.textContent = "Изменение";
    refs.movementQuantity.removeAttribute("min");
    return;
  }

  refs.movementQuantityLabel.textContent = "Количество";
  refs.movementQuantity.min = "1";

  if (Number(refs.movementQuantity.value) < 1) {
    refs.movementQuantity.value = 1;
  }
}

async function handleMovementSubmit(event) {
  event.preventDefault();

  const movementType = refs.movementType.value;
  const quantity = Number(refs.movementQuantity.value);
  let quantityDelta = quantity;

  if (movementType === "in") {
    quantityDelta = Math.abs(quantity);
  }

  if (movementType === "out") {
    quantityDelta = -Math.abs(quantity);
  }

  const payload = {
    movement_type: movementType,
    note: refs.movementNote.value.trim() || null,
    lines: [
      {
        product_id: Number(refs.movementProductId.value),
        quantity_delta: quantityDelta,
      },
    ],
  };

  setBusy(true);

  try {
    await request("/stock-movements", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    refs.movementForm.reset();
    updateMovementQuantityMode();
    state.pagination.stockMovements.page = 1;

    const [products, productSummary, stockMovements] = await Promise.all([
      request(buildProductsPath()),
      request("/products/summary"),
      request(getPagePath("stockMovements")),
    ]);

    applyPage("products", products);
    state.productSummary = productSummary;
    applyPage("stockMovements", stockMovements);
    state.stockMovementsLoaded = true;
    render();
    showNotice("Движение добавлено.");
  } catch (error) {
    showNotice(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function deleteLookup(type, id) {
  const items = type === "company" ? state.companies : state.suppliers;
  const item = items.find((candidate) => candidate.id === id);
  const label = type === "company" ? "компанию" : "поставщика";
  const successMessage =
    type === "company" ? "Компания удалена." : "Поставщик удален.";
  const endpoint = type === "company" ? "companies" : "suppliers";
  const name = item ? item.name : `#${id}`;

  if (!window.confirm(`Удалить ${label} "${name}"? Связанные товары останутся.`)) {
    return;
  }

  try {
    await request(`/${endpoint}/${id}`, { method: "DELETE" });
    resetProductForm();
    await loadAll({ quiet: true });
    showNotice(successMessage);
  } catch (error) {
    showNotice(error.message, true);
  }
}

function getCompanyName(companyId) {
  if (companyId === null) {
    return "Не указана";
  }

  return state.companies.find((company) => company.id === companyId)?.name ?? `#${companyId}`;
}

function getSupplierName(supplierId) {
  if (supplierId === null) {
    return "Не указан";
  }

  return (
    state.suppliers.find((supplier) => supplier.id === supplierId)?.name ??
    `#${supplierId}`
  );
}

function getProductDisplayName(productId) {
  const product = state.products.find((item) => item.id === productId);

  return product ? product.name : `#${productId}`;
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
  refs.refreshButton.disabled = isBusy;
  refs.productSubmit.disabled = isBusy;
  refs.movementRefreshButton.disabled = isBusy;
  refs.movementSubmit.disabled = isBusy;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
