function resetSaleForm() {
  refs.saleForm.reset();
  clearMovementProductSearchTimers();
  refs.saleLines.innerHTML = "";
  addSaleLine(null, 1, { focus: false });
  updateSaleLineRemoveState();
  updateSaleFormTotal();
}

function addSaleLine(product = null, quantity = 1, options = {}) {
  saleLineCounter += 1;

  const lineId = `sale-${saleLineCounter}`;
  const productSearchInputId = `sale-product-search-${saleLineCounter}`;
  const productInputId = `sale-product-${saleLineCounter}`;
  const quantityInputId = `sale-quantity-${saleLineCounter}`;
  const priceInputId = `sale-unit-price-${saleLineCounter}`;
  const unitPrice = product?.sale_price ?? "";
  const quantityUnit = normalizeQuantityUnit(product?.quantity_unit);
  const selectedProductMarkup = product
    ? renderMovementSelectedProduct(product, { showSalePrice: false })
    : "";

  refs.saleLines.insertAdjacentHTML(
    "beforeend",
    `
      <div class="sale-form-line" data-sale-line data-movement-line data-movement-line-id="${lineId}">
        <div class="movement-line-field sale-line-product">
          <label for="${productSearchInputId}">Товар</label>
          <div class="movement-product-picker" data-movement-product-picker>
            <input id="${productSearchInputId}" data-movement-product-search name="product_search" type="search" autocomplete="off" maxlength="255" placeholder="Начните вводить название" value="${escapeHtml(product?.name ?? "")}">
            <input id="${productInputId}" data-movement-product-id name="product_id" type="hidden" value="${escapeHtml(product?.id ?? "")}">
            <div class="movement-product-selected${product ? "" : " hidden"}" data-movement-product-selected>${selectedProductMarkup}</div>
            <div class="movement-product-suggestions hidden" data-movement-product-suggestions></div>
          </div>
        </div>
        <div class="sale-line-details">
          <div class="movement-line-field">
            <label for="${quantityInputId}">Количество, <span data-sale-quantity-unit>${escapeHtml(quantityUnit)}</span></label>
            <input id="${quantityInputId}" data-sale-quantity name="quantity" type="number" min="1" step="1" value="${escapeHtml(quantity)}" required>
          </div>
          <div class="movement-line-field sale-price-field">
            <label for="${priceInputId}">Цена за единицу</label>
            <input id="${priceInputId}" data-sale-unit-price name="unit_price" type="number" min="1" step="1" value="${escapeHtml(unitPrice)}" required>
            <span class="sale-price-reference">
              Обычная: <strong data-sale-list-price>${product ? formatNumber(product.sale_price) : "—"}</strong>
              · Минимальная: <strong data-sale-floor-price>${product ? formatNumber(product.floor_price) : "—"}</strong>
            </span>
          </div>
          <div class="sale-line-subtotal">
            <span>Сумма</span>
            <strong data-sale-line-subtotal>0</strong>
          </div>
          <button class="secondary-button sale-line-remove" type="button" data-remove-sale-line aria-label="Удалить товар" title="Удалить товар">×</button>
        </div>
        <span class="sale-line-warning hidden" data-sale-price-warning></span>
      </div>
    `,
  );

  updateSaleLineRemoveState();
  updateSaleLinePricing(getSaleLineRows().at(-1));

  if (options.focus !== false) {
    getSaleLineRows()
      .at(-1)
      ?.querySelector("[data-movement-product-search]")
      ?.focus();
  }
}

function getSaleLineRows() {
  return [...refs.saleLines.querySelectorAll("[data-sale-line]")];
}

function updateSaleLineRemoveState() {
  const rows = getSaleLineRows();

  rows.forEach((row) => {
    const button = row.querySelector("[data-remove-sale-line]");
    button.disabled = rows.length <= 1;
  });
}

function handleSaleLineListClick(event) {
  const productButton = event.target.closest("[data-select-movement-product]");

  if (productButton) {
    const row = productButton.closest("[data-sale-line]");
    selectMovementProduct(row, Number(productButton.dataset.productId));
    return;
  }

  const button = event.target.closest("[data-remove-sale-line]");

  if (!button || button.disabled) {
    return;
  }

  const row = button.closest("[data-sale-line]");

  clearMovementProductSearchTimer(row);
  row?.remove();
  updateSaleLineRemoveState();
  updateSaleFormTotal();
}

function handleSaleLineListInput(event) {
  const input = event.target.closest("[data-movement-product-search]");

  if (input) {
    const row = input.closest("[data-sale-line]");

    clearMovementProductSelection(row);
    scheduleMovementProductSearch(row, input.value);
    return;
  }

  const pricingInput = event.target.closest(
    "[data-sale-quantity], [data-sale-unit-price]",
  );

  if (!pricingInput) {
    return;
  }

  updateSaleLinePricing(pricingInput.closest("[data-sale-line]"));
}

function fillSaleLineProductPrice(row, product) {
  if (!row?.matches("[data-sale-line]")) {
    return;
  }

  row.querySelector("[data-sale-unit-price]").value = product.sale_price;
  updateSaleLineProductContext(row, product);
  updateSaleLinePricing(row);
}

function updateSaleLineProductContext(row, product) {
  row.querySelector("[data-sale-quantity-unit]").textContent =
    normalizeQuantityUnit(product?.quantity_unit);
  row.querySelector("[data-sale-list-price]").textContent = product
    ? formatNumber(product.sale_price)
    : "—";
  row.querySelector("[data-sale-floor-price]").textContent = product
    ? formatNumber(product.floor_price)
    : "—";
}

function updateSaleLinePricing(row) {
  if (!row) {
    return;
  }

  const productId = Number(row.querySelector("[data-movement-product-id]").value);
  const unitPrice = Number(row.querySelector("[data-sale-unit-price]").value);
  const subtotal = getSaleLineSubtotal(row);
  const product = Number.isInteger(productId)
    ? getCachedMovementProduct(productId)
    : null;
  const subtotalEl = row.querySelector("[data-sale-line-subtotal]");
  const warningEl = row.querySelector("[data-sale-price-warning]");

  subtotalEl.textContent = formatNumber(subtotal);

  if (
    product &&
    Number.isInteger(unitPrice) &&
    unitPrice >= 1 &&
    unitPrice < product.floor_price
  ) {
    warningEl.textContent = `Ниже минимальной цены ${formatNumber(product.floor_price)}`;
    warningEl.classList.remove("hidden");
  } else {
    warningEl.textContent = "";
    warningEl.classList.add("hidden");
  }

  updateSaleFormTotal();
}

function getSaleLineSubtotal(row) {
  const quantity = Number(row.querySelector("[data-sale-quantity]").value);
  const unitPrice = Number(row.querySelector("[data-sale-unit-price]").value);

  if (
    !Number.isInteger(quantity) ||
    !Number.isInteger(unitPrice) ||
    quantity < 1 ||
    unitPrice < 1
  ) {
    return 0;
  }

  return quantity * unitPrice;
}

function updateSaleFormTotal() {
  const total = getSaleLineRows().reduce(
    (sum, row) => sum + getSaleLineSubtotal(row),
    0,
  );

  refs.saleTotal.textContent = formatNumber(total);
}

function buildSalePayload() {
  const productIds = new Set();
  const lines = getSaleLineRows().map((row) => {
    const productId = Number(row.querySelector("[data-movement-product-id]").value);
    const quantity = Number(row.querySelector("[data-sale-quantity]").value);
    const unitPrice = Number(row.querySelector("[data-sale-unit-price]").value);

    if (!Number.isInteger(productId) || productId < 1) {
      throw new Error("Выберите товар из списка в каждой строке.");
    }

    if (!Number.isInteger(quantity) || quantity < 1) {
      throw new Error("Укажите количество больше нуля в каждой строке.");
    }

    if (!Number.isInteger(unitPrice) || unitPrice < 1) {
      throw new Error("Укажите цену больше нуля в каждой строке.");
    }

    if (productIds.has(productId)) {
      throw new Error("Один товар нельзя добавить в продажу дважды.");
    }

    productIds.add(productId);

    return {
      product_id: productId,
      quantity,
      unit_price: unitPrice,
    };
  });

  if (lines.length === 0) {
    throw new Error("Добавьте хотя бы одну строку продажи.");
  }

  return {
    note: refs.saleNote.value.trim() || null,
    lines,
  };
}

async function handleSaleSubmit(event) {
  event.preventDefault();

  let payload;

  try {
    payload = buildSalePayload();
  } catch (error) {
    showNotice(error.message, true);
    return;
  }

  setBusy(true);

  try {
    await request("/sales", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    closeDrawer();
    state.pagination.stockMovements.page = 1;

    const [
      productSummary,
      salesSummary,
      dashboardMovements,
      products,
      stockMovements,
    ] = await Promise.all([
      request("/products/summary"),
      request(buildSalesSummaryPath()),
      request(buildDashboardMovementsPath()),
      request(buildProductsPath()),
      request(getPagePath("stockMovements")),
    ]);

    state.productSummary = productSummary;
    state.salesSummary = salesSummary;
    state.dashboardMovements = dashboardMovements.items;
    applyPage("products", products);
    applyPage("stockMovements", stockMovements);
    state.stockMovementsLoaded = true;
    render();
    showNotice("Продажа добавлена.");
  } catch (error) {
    showNotice(error.message, true);
  } finally {
    setBusy(false);
  }
}
