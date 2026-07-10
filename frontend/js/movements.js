function resetMovementForm() {
  refs.movementForm.reset();
  clearMovementProductSearchTimers();
  refs.movementLines.innerHTML = "";
  addMovementLine(null, 1, { focus: false });
  updateMovementQuantityMode();
}

function addMovementLine(product = null, quantity = 1, options = {}) {
  movementLineCounter += 1;

  const lineId = String(movementLineCounter);
  const productSearchInputId = `movement-product-search-${lineId}`;
  const productInputId = `movement-product-${movementLineCounter}`;
  const quantityInputId = `movement-quantity-${movementLineCounter}`;
  const minAttribute = refs.movementType.value === "adjustment" ? "" : ' min="1"';
  const selectedProductMarkup = product
    ? renderMovementSelectedProduct(product)
    : "";

  refs.movementLines.insertAdjacentHTML(
    "beforeend",
    `
      <div class="movement-form-line" data-movement-line data-movement-line-id="${lineId}">
        <div class="movement-line-field">
          <label for="${productSearchInputId}">Товар</label>
          <div class="movement-product-picker" data-movement-product-picker>
            <input id="${productSearchInputId}" data-movement-product-search name="product_search" type="search" autocomplete="off" maxlength="255" placeholder="Начните вводить название" value="${escapeHtml(product?.name ?? "")}">
            <input id="${productInputId}" data-movement-product-id name="product_id" type="hidden" value="${escapeHtml(product?.id ?? "")}">
            <div class="movement-product-selected${product ? "" : " hidden"}" data-movement-product-selected>${selectedProductMarkup}</div>
            <div class="movement-product-suggestions hidden" data-movement-product-suggestions></div>
          </div>
        </div>
        <div class="movement-line-field">
          <label for="${quantityInputId}" data-movement-quantity-label>${getMovementQuantityLabel()}</label>
          <input id="${quantityInputId}" data-movement-quantity name="quantity" type="number"${minAttribute} step="1" value="${escapeHtml(quantity)}" required>
        </div>
        <button class="secondary-button movement-line-remove" type="button" data-remove-movement-line>Удалить</button>
      </div>
    `,
  );

  updateMovementLineRemoveState();

  if (options.focus !== false) {
    getMovementLineRows()
      .at(-1)
      ?.querySelector("[data-movement-product-search]")
      ?.focus();
  }
}

function getMovementLineRows() {
  return [...refs.movementLines.querySelectorAll("[data-movement-line]")];
}

function getMovementQuantityLabel() {
  return refs.movementType.value === "adjustment" ? "Изменение" : "Количество";
}

function updateMovementLineRemoveState() {
  const rows = getMovementLineRows();

  rows.forEach((row) => {
    const button = row.querySelector("[data-remove-movement-line]");
    button.disabled = rows.length <= 1;
  });
}

function handleMovementLineListClick(event) {
  const productButton = event.target.closest("[data-select-movement-product]");

  if (productButton) {
    const row = productButton.closest("[data-movement-line]");
    selectMovementProduct(row, Number(productButton.dataset.productId));
    return;
  }

  const button = event.target.closest("[data-remove-movement-line]");

  if (!button || button.disabled) {
    return;
  }

  const row = button.closest("[data-movement-line]");

  clearMovementProductSearchTimer(row);
  row?.remove();
  updateMovementLineRemoveState();
}

function handleMovementLineListInput(event) {
  const input = event.target.closest("[data-movement-product-search]");

  if (!input) {
    return;
  }

  const row = input.closest("[data-movement-line]");

  clearMovementProductSelection(row);
  scheduleMovementProductSearch(row, input.value);
}

function clearMovementProductSearchTimers() {
  movementProductSearchTimers.forEach((timerId) => {
    window.clearTimeout(timerId);
  });
  movementProductSearchTimers.clear();
}

function clearMovementProductSearchTimer(row) {
  const lineId = row?.dataset.movementLineId;

  if (!lineId || !movementProductSearchTimers.has(lineId)) {
    return;
  }

  window.clearTimeout(movementProductSearchTimers.get(lineId));
  movementProductSearchTimers.delete(lineId);
}

function scheduleMovementProductSearch(row, value) {
  if (!row) {
    return;
  }

  const searchTerm = value.trim();
  const token = String(++movementProductSearchCounter);

  clearMovementProductSearchTimer(row);
  row.dataset.movementSearchToken = token;

  if (!searchTerm) {
    hideMovementProductSuggestions(row);
    return;
  }

  const timerId = window.setTimeout(() => {
    movementProductSearchTimers.delete(row.dataset.movementLineId);
    searchMovementProducts(row, searchTerm, token);
  }, MOVEMENT_PRODUCT_SEARCH_DELAY_MS);

  movementProductSearchTimers.set(row.dataset.movementLineId, timerId);
}

async function searchMovementProducts(row, searchTerm, token) {
  if (!row?.isConnected || row.dataset.movementSearchToken !== token) {
    return;
  }

  renderMovementProductSuggestionMessage(row, "Ищем товары...");

  try {
    const payload = await request(buildMovementProductSearchPath(searchTerm));

    if (!row.isConnected || row.dataset.movementSearchToken !== token) {
      return;
    }

    rememberMovementProducts(payload.items);
    renderMovementProductSuggestions(row, payload.items);
  } catch (error) {
    if (row.isConnected && row.dataset.movementSearchToken === token) {
      renderMovementProductSuggestionMessage(row, error.message, true);
    }
  }
}

function renderMovementProductSuggestions(row, products) {
  const suggestions = row.querySelector("[data-movement-product-suggestions]");

  if (products.length === 0) {
    renderMovementProductSuggestionMessage(row, "Товары не найдены.");
    return;
  }

  suggestions.innerHTML = products
    .map(
      (product) => `
        <button class="movement-product-suggestion" type="button" data-select-movement-product data-product-id="${product.id}">
          <span class="movement-product-suggestion-name">${escapeHtml(product.name)}</span>
          <span class="movement-product-suggestion-meta">Остаток: ${escapeHtml(formatQuantity(product.quantity, product.quantity_unit))} · Продажа: ${formatNumber(product.sale_price)}</span>
          ${renderMovementSuggestionTags(product.tags)}
        </button>
      `,
    )
    .join("");
  suggestions.classList.remove("hidden");
}

function renderMovementProductSuggestionMessage(row, message, isError = false) {
  const suggestions = row.querySelector("[data-movement-product-suggestions]");

  suggestions.innerHTML = `
    <div class="movement-product-suggestion-empty${isError ? " error" : ""}">
      ${escapeHtml(message)}
    </div>
  `;
  suggestions.classList.remove("hidden");
}

function hideMovementProductSuggestions(row) {
  const suggestions = row?.querySelector("[data-movement-product-suggestions]");

  if (!suggestions) {
    return;
  }

  suggestions.innerHTML = "";
  suggestions.classList.add("hidden");
}

function selectMovementProduct(row, productId) {
  const product = getCachedMovementProduct(productId);

  if (!row || !product) {
    showNotice("Товар не найден в результатах поиска.", true);
    return;
  }

  clearMovementProductSearchTimer(row);
  row.dataset.movementSearchToken = "";
  row.querySelector("[data-movement-product-search]").value = product.name;
  row.querySelector("[data-movement-product-id]").value = product.id;

  const selected = row.querySelector("[data-movement-product-selected]");
  selected.innerHTML = renderMovementSelectedProduct(product, {
    showSalePrice: !row.matches("[data-sale-line]"),
  });
  selected.classList.remove("hidden");
  hideMovementProductSuggestions(row);
  fillSaleLineProductPrice(row, product);
}

function clearMovementProductSelection(row) {
  const productIdInput = row?.querySelector("[data-movement-product-id]");
  const selected = row?.querySelector("[data-movement-product-selected]");

  if (!productIdInput || !selected) {
    return;
  }

  productIdInput.value = "";
  selected.innerHTML = "";
  selected.classList.add("hidden");

  if (row?.matches("[data-sale-line]")) {
    const unitPriceInput = row.querySelector("[data-sale-unit-price]");
    unitPriceInput.value = "";
    updateSaleLineProductContext(row, null);
    updateSaleLinePricing(row);
  }
}

function getCachedMovementProduct(productId) {
  return (
    state.movementProductCache.get(productId) ||
    state.products.find((product) => product.id === productId)
  );
}

function rememberMovementProducts(products) {
  products.forEach((product) => {
    state.movementProductCache.set(product.id, product);
  });
}

function renderMovementSelectedProduct(product, options = {}) {
  const salePrice = options.showSalePrice === false
    ? ""
    : ` · Продажа: ${formatNumber(product.sale_price)}`;

  return `
    <span class="movement-product-selected-name">${escapeHtml(product.name)}</span>
    <span class="movement-product-selected-meta">Остаток: ${escapeHtml(formatQuantity(product.quantity, product.quantity_unit))}${salePrice}</span>
    ${renderMovementSuggestionTags(product.tags)}
  `;
}

function renderMovementSuggestionTags(tags = []) {
  if (!tags.length) {
    return "";
  }

  return `
    <span class="movement-product-suggestion-tags">
      ${tags.map((tag) => `#${escapeHtml(tag.name)}`).join(" ")}
    </span>
  `;
}

function updateMovementQuantityMode() {
  const isAdjustment = refs.movementType.value === "adjustment";

  getMovementLineRows().forEach((row) => {
    const label = row.querySelector("[data-movement-quantity-label]");
    const quantityInput = row.querySelector("[data-movement-quantity]");

    label.textContent = getMovementQuantityLabel();

    if (isAdjustment) {
      quantityInput.removeAttribute("min");
      return;
    }

    quantityInput.min = "1";

    if (Number(quantityInput.value) < 1) {
      quantityInput.value = 1;
    }
  });
}

function buildMovementPayload() {
  const movementType = refs.movementType.value;
  const productIds = new Set();
  const lines = getMovementLineRows().map((row) => {
    const productId = Number(row.querySelector("[data-movement-product-id]").value);
    const quantity = Number(row.querySelector("[data-movement-quantity]").value);

    if (!Number.isInteger(productId) || productId < 1) {
      throw new Error("Выберите товар из списка в каждой строке.");
    }

    if (!Number.isInteger(quantity) || quantity === 0) {
      throw new Error(
        movementType === "adjustment"
          ? "Укажите ненулевое изменение в каждой строке."
          : "Укажите количество в каждой строке.",
      );
    }

    if (movementType !== "adjustment" && quantity < 1) {
      throw new Error("Количество должно быть больше нуля.");
    }

    if (productIds.has(productId)) {
      throw new Error("Один товар нельзя добавить в движение дважды.");
    }

    productIds.add(productId);

    let quantityDelta = quantity;

    if (movementType === "in") {
      quantityDelta = Math.abs(quantity);
    }

    if (movementType === "out") {
      quantityDelta = -Math.abs(quantity);
    }

    return {
      product_id: productId,
      quantity_delta: quantityDelta,
    };
  });

  if (lines.length === 0) {
    throw new Error("Добавьте хотя бы одну строку движения.");
  }

  return {
    movement_type: movementType,
    note: refs.movementNote.value.trim() || null,
    lines,
  };
}

async function handleMovementSubmit(event) {
  event.preventDefault();

  let payload;

  try {
    payload = buildMovementPayload();
  } catch (error) {
    showNotice(error.message, true);
    return;
  }

  setBusy(true);

  try {
    await request("/stock-movements", {
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
    showNotice("Движение добавлено.");
  } catch (error) {
    showNotice(error.message, true);
  } finally {
    setBusy(false);
  }
}
