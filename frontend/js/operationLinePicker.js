import { FIRST_PAGE, LOOKUP_PAGE_SIZE, getProduct, getProducts } from "./api.js";
import { formatCount, formatCurrency, formatQuantity } from "./format.js";

const PRODUCT_SEARCH_MIN_LENGTH = 2;
const PRODUCT_SEARCH_DELAY_MS = 250;
const searchTimers = new WeakMap();
const searchRequestIds = new WeakMap();

export function createOperationLineElement({
  lineId,
  kind,
  quantityName,
  quantityLabel,
  includeUnitCost = false,
}) {
  const wrapper = document.createElement("div");
  wrapper.className = `${kind}-create-line operation-create-line`;
  wrapper.dataset.lineId = String(lineId);
  wrapper.dataset.kind = kind;
  wrapper.innerHTML = `
    <div class="${kind}-create-line-header">
      <h4 class="fs-6 mb-0">Позиция ${lineId}</h4>
      <button class="btn btn-sm btn-outline-danger" type="button" data-remove-${kind}-line>
        Удалить
      </button>
    </div>
    <div class="operation-line-grid">
      <div class="operation-line-product">
        <label class="form-label" for="${kind}-line-product-search-${lineId}">Товар</label>
        <input
          class="form-control"
          id="${kind}-line-product-search-${lineId}"
          type="search"
          placeholder="Введите название товара"
          autocomplete="off"
          data-product-search
          aria-autocomplete="list"
          aria-controls="${kind}-line-product-results-${lineId}"
        >
        <div
          class="operation-line-message text-secondary small d-none"
          data-product-message
          role="status"
        ></div>
        <div
          class="list-group operation-product-results d-none mt-2"
          id="${kind}-line-product-results-${lineId}"
          data-product-results
          role="listbox"
          aria-label="Найденные товары"
        ></div>
        <div class="operation-product-selected d-none mt-2" data-product-selected>
          <div>
            <div class="fw-semibold" data-selected-product-name></div>
            <div class="${kind}-meta" data-selected-product-meta></div>
          </div>
          <button class="btn btn-sm btn-outline-secondary" type="button" data-clear-product>
            Сбросить
          </button>
        </div>
      </div>
      <div>
        <label class="form-label" for="${kind}-line-supplier-${lineId}">Поставщик</label>
        <select
          class="form-select"
          id="${kind}-line-supplier-${lineId}"
          name="product_supplier_id"
          required
          data-supplier-select
        >
          <option value="">Сначала выберите товар</option>
        </select>
        <div class="${kind}-meta mt-1" data-supplier-meta></div>
      </div>
      <div>
        <label class="form-label" for="${kind}-line-quantity-${lineId}">${quantityLabel}</label>
        <input
          class="form-control"
          id="${kind}-line-quantity-${lineId}"
          name="${quantityName}"
          type="number"
          min="1"
          step="1"
          value="1"
          required
          data-quantity-input
        >
      </div>
      ${includeUnitCost ? createUnitCostMarkup(kind, lineId) : ""}
    </div>
  `;

  return wrapper;
}

export function bindOperationLinePicker(container, { kind }) {
  container.addEventListener("input", (event) => {
    if (
      event.target instanceof HTMLInputElement
      && event.target.matches("[data-product-search]")
    ) {
      scheduleProductSearch(event.target, kind);
    }
  });

  container.addEventListener("click", (event) => {
    if (!(event.target instanceof Element)) {
      return;
    }

    const productButton = event.target.closest("[data-product-result-id]");
    if (productButton && container.contains(productButton)) {
      void selectProductForLine(productButton, kind);
      return;
    }

    const clearButton = event.target.closest("[data-clear-product]");
    if (clearButton && container.contains(clearButton)) {
      clearSelectedProduct(getLineElement(clearButton));
    }
  });

  container.addEventListener("change", (event) => {
    if (
      event.target instanceof HTMLSelectElement
      && event.target.matches("[data-supplier-select]")
    ) {
      updateSelectedSupplierMeta(getLineElement(event.target), kind);
    }
  });
}

export function validateOperationLines(container, label) {
  const lines = Array.from(container.querySelectorAll(".operation-create-line"));

  if (!lines.length) {
    return `Добавьте хотя бы одну позицию ${label}.`;
  }

  for (const line of lines) {
    const lineLabel = getLineLabel(line);
    const productId = Number(line.dataset.productId || 0);
    const supplierSelect = getSupplierSelect(line);
    const quantityInput = getQuantityInput(line);
    const quantity = Number(quantityInput.value);

    if (!productId) {
      return `Выберите товар для ${lineLabel}.`;
    }

    if (!Number(supplierSelect.value)) {
      return `Выберите поставщика для ${lineLabel}.`;
    }

    if (!Number.isFinite(quantity) || quantity <= 0) {
      return `Введите количество для ${lineLabel}.`;
    }

    if (line.dataset.kind === "sale") {
      const availableQuantity = Number(supplierSelect.selectedOptions[0]?.dataset.quantity || 0);

      if (Number.isFinite(availableQuantity) && quantity > availableQuantity) {
        return `Количество продажи больше остатка для ${lineLabel}.`;
      }
    }
  }

  return "";
}

function createUnitCostMarkup(kind, lineId) {
  return `
    <div>
      <label class="form-label" for="${kind}-line-cost-${lineId}">Цена закупки</label>
      <input
        class="form-control"
        id="${kind}-line-cost-${lineId}"
        name="unit_cost_snapshot"
        type="number"
        min="0"
        step="1"
        placeholder="По поставщику"
        data-unit-cost-input
      >
    </div>
  `;
}

function scheduleProductSearch(input, kind) {
  const line = getLineElement(input);
  const searchTerm = input.value.trim();

  clearSelectedProduct(line, { keepSearch: true });
  window.clearTimeout(searchTimers.get(input));
  invalidateProductSearch(input);

  if (searchTerm.length < PRODUCT_SEARCH_MIN_LENGTH) {
    clearProductResults(line);
    setProductMessage(line, `Введите минимум ${PRODUCT_SEARCH_MIN_LENGTH} символа.`);
    return;
  }

  searchTimers.set(
    input,
    window.setTimeout(() => {
      void searchProductsForLine(input, searchTerm, kind);
    }, PRODUCT_SEARCH_DELAY_MS),
  );
}

async function searchProductsForLine(input, searchTerm, kind) {
  const line = getLineElement(input);
  const requestId = invalidateProductSearch(input);
  setProductMessage(line, "Поиск товаров...");
  clearProductResults(line);

  try {
    const response = await getProducts({
      search: searchTerm,
      page: FIRST_PAGE,
      pageSize: LOOKUP_PAGE_SIZE,
    });

    if (searchRequestIds.get(input) !== requestId) {
      return;
    }

    renderProductResults(line, response.items || [], kind);
  } catch (error) {
    if (searchRequestIds.get(input) !== requestId) {
      return;
    }

    console.error("Could not search products:", error);
    clearProductResults(line);
    setProductMessage(line, "Не удалось загрузить товары.");
  }
}

function renderProductResults(line, products, kind) {
  const results = getProductResults(line);
  results.replaceChildren();

  if (!products.length) {
    results.classList.add("d-none");
    setProductMessage(line, "Товары не найдены.");
    return;
  }

  const fragment = document.createDocumentFragment();

  for (const product of products) {
    fragment.append(createProductResultButton(product, kind));
  }

  setProductMessage(line);
  results.append(fragment);
  results.classList.remove("d-none");
}

function createProductResultButton(product, kind) {
  const button = document.createElement("button");
  const name = document.createElement("span");
  const meta = document.createElement("span");
  const unit = product.quantity_unit || "";

  button.className = "list-group-item list-group-item-action operation-product-result";
  button.type = "button";
  button.dataset.productResultId = String(product.id || "");
  button.setAttribute("role", "option");

  name.className = "fw-semibold d-block";
  name.textContent = product.name || "Без названия";
  meta.className = `${kind}-meta d-block`;
  meta.textContent = [
    product.company_name || "Компания не указана",
    `Остаток: ${formatQuantity(product.total_quantity, unit)}`,
    `Поставщиков: ${formatCount(product.suppliers_count)}`,
  ].join(" | ");

  button.append(name, meta);
  return button;
}

async function selectProductForLine(button, kind) {
  const line = getLineElement(button);
  const productId = Number(button.dataset.productResultId || 0);

  if (!productId) {
    return;
  }

  clearProductResults(line);
  invalidateProductSearch(getProductSearch(line));
  setProductMessage(line, "Загрузка поставщиков...");

  try {
    const product = await getProduct(productId);
    line.dataset.productId = String(product.id || "");
    line.dataset.quantityUnit = product.quantity_unit || "";
    getProductSearch(line).value = product.name || "";
    renderSelectedProduct(line, product);
    populateSupplierSelect(line, product, kind);
    setProductMessage(line);
  } catch (error) {
    console.error("Could not load product detail:", error);
    clearSelectedProduct(line, { keepSearch: true });
    setProductMessage(line, "Не удалось загрузить поставщиков товара.");
  }
}

function renderSelectedProduct(line, product) {
  const selected = getSelectedProduct(line);
  const name = line.querySelector("[data-selected-product-name]");
  const meta = line.querySelector("[data-selected-product-meta]");

  name.textContent = product.name || "Без названия";
  meta.textContent = [
    product.company_name || "Компания не указана",
    `Единица: ${product.quantity_unit || "не указана"}`,
    `Порог: ${formatQuantity(product.low_stock_threshold, product.quantity_unit)}`,
  ].join(" | ");
  selected.classList.remove("d-none");
}

function populateSupplierSelect(line, product, kind) {
  const select = getSupplierSelect(line);
  const links = Array.isArray(product.supplier_links) ? product.supplier_links : [];
  const availableLinks = kind === "sale"
    ? links.filter((link) => Number(link.quantity || 0) > 0)
    : links;

  select.replaceChildren(createPlaceholderOption(getSupplierPlaceholder(links, availableLinks, kind)));

  for (const link of links) {
    const option = document.createElement("option");
    const quantity = Number(link.quantity || 0);
    option.value = String(link.id || "");
    option.textContent = getSupplierOptionLabel(link, product.quantity_unit);
    option.dataset.supplierName = link.supplier_name || "";
    option.dataset.quantity = String(quantity);
    option.dataset.purchasePrice = String(link.purchase_price || 0);
    option.dataset.salePrice = String(link.sale_price || 0);

    if (kind === "sale" && quantity <= 0) {
      option.disabled = true;
    }

    select.append(option);
  }

  select.disabled = false;
  updateSelectedSupplierMeta(line, kind);
}

function getSupplierPlaceholder(links, availableLinks, kind) {
  if (!links.length) {
    return "У товара нет поставщиков";
  }

  if (kind === "sale" && !availableLinks.length) {
    return "Нет поставщиков с остатком";
  }

  return "Выберите поставщика";
}

function getSupplierOptionLabel(link, unit) {
  return [
    link.supplier_name || `Поставщик #${formatCount(link.supplier_id)}`,
    `остаток ${formatQuantity(link.quantity, unit)}`,
    `продажа ${formatCurrency(link.sale_price)}`,
  ].join(" | ");
}

function updateSelectedSupplierMeta(line, kind) {
  const select = getSupplierSelect(line);
  const selectedOption = select.selectedOptions[0];
  const meta = line.querySelector("[data-supplier-meta]");
  const quantityInput = getQuantityInput(line);
  const unitCostInput = line.querySelector("[data-unit-cost-input]");

  if (!selectedOption?.value) {
    meta.textContent = "";
    quantityInput.removeAttribute("max");

    if (unitCostInput instanceof HTMLInputElement) {
      unitCostInput.placeholder = "По поставщику";
    }

    return;
  }

  const quantity = Number(selectedOption.dataset.quantity || 0);
  const unit = line.dataset.quantityUnit || "";
  const purchasePrice = Number(selectedOption.dataset.purchasePrice || 0);
  const salePrice = Number(selectedOption.dataset.salePrice || 0);

  if (kind === "sale") {
    quantityInput.max = String(quantity);

    if (Number(quantityInput.value) > quantity) {
      quantityInput.value = String(quantity);
    }
  } else {
    quantityInput.removeAttribute("max");
  }

  if (unitCostInput instanceof HTMLInputElement) {
    unitCostInput.placeholder = `По поставщику: ${formatCurrency(purchasePrice)}`;
  }

  meta.textContent = [
    `Остаток: ${formatQuantity(quantity, unit)}`,
    `Закупка: ${formatCurrency(purchasePrice)}`,
    `Продажа: ${formatCurrency(salePrice)}`,
  ].join(" | ");
}

function clearSelectedProduct(line, { keepSearch = false } = {}) {
  delete line.dataset.productId;
  delete line.dataset.quantityUnit;
  getSelectedProduct(line).classList.add("d-none");

  if (!keepSearch) {
    getProductSearch(line).value = "";
  }

  resetSupplierSelect(line);
}

function resetSupplierSelect(line) {
  const select = getSupplierSelect(line);
  const meta = line.querySelector("[data-supplier-meta]");
  const quantityInput = getQuantityInput(line);
  const unitCostInput = line.querySelector("[data-unit-cost-input]");

  select.replaceChildren(createPlaceholderOption("Сначала выберите товар"));
  select.disabled = false;
  meta.textContent = "";
  quantityInput.removeAttribute("max");

  if (unitCostInput instanceof HTMLInputElement) {
    unitCostInput.placeholder = "По поставщику";
  }
}

function createPlaceholderOption(text) {
  const option = document.createElement("option");
  option.value = "";
  option.textContent = text;
  option.selected = true;
  return option;
}

function clearProductResults(line) {
  const results = getProductResults(line);
  results.replaceChildren();
  results.classList.add("d-none");
}

function invalidateProductSearch(input) {
  const requestId = (searchRequestIds.get(input) || 0) + 1;
  searchRequestIds.set(input, requestId);
  return requestId;
}

function setProductMessage(line, message = "") {
  const messageElement = line.querySelector("[data-product-message]");
  messageElement.textContent = message;
  messageElement.classList.toggle("d-none", !message);
}

function getLineElement(element) {
  const line = element.closest(".operation-create-line");

  if (!line) {
    throw new Error("Missing operation line container.");
  }

  return line;
}

function getLineLabel(line) {
  return `позиции ${line.dataset.lineId || ""}`.trim();
}

function getProductSearch(line) {
  return line.querySelector("[data-product-search]");
}

function getProductResults(line) {
  return line.querySelector("[data-product-results]");
}

function getSelectedProduct(line) {
  return line.querySelector("[data-product-selected]");
}

function getSupplierSelect(line) {
  return line.querySelector("[data-supplier-select]");
}

function getQuantityInput(line) {
  return line.querySelector("[data-quantity-input]");
}
