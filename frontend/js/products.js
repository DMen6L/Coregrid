function handleSearchInput(event) {
  const tagToken = getActiveSearchTagToken(event.target);
  const nextSearchTerm = getProductSearchText(event.target.value);
  const searchChanged = nextSearchTerm !== state.searchTerm;

  state.searchTerm = nextSearchTerm;

  if (tagToken) {
    scheduleTagSearch(
      "product-search",
      refs.productSearchTagSuggestions,
      tagToken.term,
      { allowEmpty: true },
    );
  } else {
    clearTagSearchTimer("product-search");
    hideTagSuggestions(refs.productSearchTagSuggestions);
  }

  if (searchChanged) {
    state.pagination.products.page = 1;
    loadPage("products");
  }
}

function handleSearchKeydown(event) {
  if (event.key === "Backspace" && event.target.value === "") {
    const removedTag = state.selectedTagFilters.at(-1);

    if (!removedTag) {
      return;
    }

    state.selectedTagFilters = state.selectedTagFilters.slice(0, -1);
    state.pagination.products.page = 1;
    renderSelectedSearchTags();
    loadPage("products");
    return;
  }

  if (event.key !== "Enter") {
    return;
  }

  const tagToken = getActiveSearchTagToken(event.target);

  if (!tagToken) {
    return;
  }

  event.preventDefault();
  addSearchTagFilter(tagToken.term);
}

function handleProductSearchTagSuggestionClick(event) {
  const button = event.target.closest("[data-select-tag]");

  if (!button) {
    return;
  }

  addSearchTagFilter(button.dataset.tagName);
}

function handleSelectedSearchTagsClick(event) {
  const button = event.target.closest("[data-remove-search-tag]");

  if (!button) {
    return;
  }

  state.selectedTagFilters = state.selectedTagFilters.filter(
    (tagName) => tagName !== button.dataset.removeSearchTag,
  );
  reloadProductsAfterSearchTagChange();
}

function addSearchTagFilter(tagName) {
  const normalizedTagName = normalizeTagName(tagName);

  if (!normalizedTagName) {
    return;
  }

  if (!state.selectedTagFilters.includes(normalizedTagName)) {
    state.selectedTagFilters = [...state.selectedTagFilters, normalizedTagName];
  }

  refs.productSearch.value = removeActiveSearchTagToken(refs.productSearch);
  state.searchTerm = getProductSearchText(refs.productSearch.value);
  hideTagSuggestions(refs.productSearchTagSuggestions);
  reloadProductsAfterSearchTagChange();
}

function reloadProductsAfterSearchTagChange() {
  state.pagination.products.page = 1;
  renderSelectedSearchTags();
  loadPage("products");
}

function getActiveSearchTagToken(input) {
  const cursorPosition = input.selectionStart ?? input.value.length;
  const beforeCursor = input.value.slice(0, cursorPosition);
  const hashIndex = beforeCursor.lastIndexOf("#");

  if (hashIndex === -1) {
    return null;
  }

  const tagTerm = beforeCursor.slice(hashIndex + 1);
  const charBeforeHash = hashIndex > 0 ? beforeCursor[hashIndex - 1] : "";

  if ((charBeforeHash && !/\s/.test(charBeforeHash)) || /\s/.test(tagTerm)) {
    return null;
  }

  return {
    start: hashIndex,
    end: cursorPosition,
    term: tagTerm,
  };
}

function removeActiveSearchTagToken(input) {
  const tagToken = getActiveSearchTagToken(input);

  if (!tagToken) {
    return input.value.replace(/(^|\s)#\S*$/, " ").replace(/\s+/g, " ").trim();
  }

  return `${input.value.slice(0, tagToken.start)}${input.value.slice(tagToken.end)}`
    .replace(/\s+/g, " ")
    .trim();
}

function getProductSearchText(value) {
  return String(value).replace(/(^|\s)#\S*/g, " ").replace(/\s+/g, " ").trim();
}

function handleStockFilterChange(event) {
  state.stockFilter = event.target.value;
  reloadProductsAfterFilterChange();
}

function handleProductSortChange(event) {
  state.productSort = normalizeProductSort(event.target.value);
  reloadProductsAfterFilterChange();
}

function handleProductSortOrderChange(event) {
  state.productSortOrder = normalizeProductSortOrder(event.target.value);
  reloadProductsAfterFilterChange();
}

function reloadProductsAfterFilterChange() {
  state.pagination.products.page = 1;
  loadPage("products");
}

function normalizeProductSort(productSort) {
  return Object.prototype.hasOwnProperty.call(PRODUCT_SORT_LABELS, productSort)
    ? productSort
    : DEFAULT_PRODUCT_SORT;
}

function normalizeProductSortOrder(productSortOrder) {
  return Object.prototype.hasOwnProperty.call(
    PRODUCT_SORT_ORDER_LABELS,
    productSortOrder,
  )
    ? productSortOrder
    : DEFAULT_PRODUCT_SORT_ORDER;
}

function calculateProductFloorPrice() {
  const purchasePrice = Number(refs.productPurchasePrice.value);
  const marginPercent = Number(refs.productMarginPercent.value);

  if (
    !Number.isFinite(purchasePrice) ||
    !Number.isFinite(marginPercent) ||
    purchasePrice <= 0 ||
    marginPercent < 0
  ) {
    return null;
  }

  return Math.ceil((purchasePrice * (100 + marginPercent)) / 100);
}

function updateProductPricingPreview() {
  const floorPrice = calculateProductFloorPrice();

  if (floorPrice === null) {
    refs.productFloorPrice.value = "";
    refs.productSalePrice.placeholder = "";
    return;
  }

  refs.productFloorPrice.value = floorPrice;
  refs.productSalePrice.placeholder = String(floorPrice);
}

function handleProductTagInput(event) {
  scheduleTagSearch("product-form", refs.productTagSuggestions, event.target.value);
}

function handleProductTagKeydown(event) {
  if (event.key !== "Enter" && event.key !== ",") {
    return;
  }

  event.preventDefault();
  addProductTagFromInput();
}

function handleProductTagSuggestionClick(event) {
  const button = event.target.closest("[data-select-tag]");

  if (!button) {
    return;
  }

  addProductFormTag(button.dataset.tagName);
}

function handleProductTagListClick(event) {
  const button = event.target.closest("[data-remove-product-tag]");

  if (!button) {
    return;
  }

  state.productFormTags = state.productFormTags.filter(
    (tagName) => tagName !== button.dataset.removeProductTag,
  );
  renderProductFormTags();
}

function addProductTagFromInput() {
  addProductFormTag(refs.productTagInput.value);
  refs.productTagInput.focus();
}

function addProductFormTag(tagName) {
  const normalizedTagName = normalizeTagName(tagName);

  if (!normalizedTagName) {
    return;
  }

  if (!state.productFormTags.includes(normalizedTagName)) {
    state.productFormTags = [...state.productFormTags, normalizedTagName].sort();
  }

  refs.productTagInput.value = "";
  hideTagSuggestions(refs.productTagSuggestions);
  renderProductFormTags();
}

function setProductFormTags(tags = []) {
  state.productFormTags = [
    ...new Set(tags.map((tag) => normalizeTagName(tag.name ?? tag)).filter(Boolean)),
  ].sort();
  renderProductFormTags();
}

function normalizeTagName(tagName) {
  return String(tagName).trim().toLocaleLowerCase("ru-RU");
}

function scheduleTagSearch(key, container, value, options = {}) {
  const searchTerm = normalizeTagName(value);
  const token = String(++tagSearchCounter);

  clearTagSearchTimer(key);
  container.dataset.tagSearchToken = token;

  if (!searchTerm && !options.allowEmpty) {
    hideTagSuggestions(container);
    return;
  }

  const timerId = window.setTimeout(() => {
    tagSearchTimers.delete(key);
    searchTags(container, searchTerm, token);
  }, TAG_SEARCH_DELAY_MS);

  tagSearchTimers.set(key, timerId);
}

function clearTagSearchTimer(key) {
  if (!tagSearchTimers.has(key)) {
    return;
  }

  window.clearTimeout(tagSearchTimers.get(key));
  tagSearchTimers.delete(key);
}

async function searchTags(container, searchTerm, token) {
  renderTagSuggestionMessage(container, "Ищем теги...");

  try {
    const payload = await request(buildTagSearchPath(searchTerm));

    if (container.dataset.tagSearchToken !== token) {
      return;
    }

    renderTagSuggestions(container, payload.items);
  } catch (error) {
    if (container.dataset.tagSearchToken === token) {
      renderTagSuggestionMessage(container, error.message, true);
    }
  }
}

function renderTagSuggestions(container, tags) {
  if (tags.length === 0) {
    renderTagSuggestionMessage(container, "Теги не найдены.");
    return;
  }

  container.innerHTML = tags
    .map(
      (tag) => `
        <button class="tag-suggestion" type="button" data-select-tag data-tag-name="${escapeHtml(tag.name)}">
          ${escapeHtml(tag.name)}
        </button>
      `,
    )
    .join("");
  container.classList.remove("hidden");
}

function renderTagSuggestionMessage(container, message, isError = false) {
  container.innerHTML = `
    <div class="tag-suggestion-empty${isError ? " error" : ""}">
      ${escapeHtml(message)}
    </div>
  `;
  container.classList.remove("hidden");
}

function hideTagSuggestions(container) {
  container.innerHTML = "";
  container.classList.add("hidden");
}

async function handleProductSubmit(event) {
  event.preventDefault();
  const floorPrice = calculateProductFloorPrice();
  const salePrice = refs.productSalePrice.value
    ? Number(refs.productSalePrice.value)
    : floorPrice;

  const payload = {
    name: refs.productName.value.trim(),
    purchase_price: Number(refs.productPurchasePrice.value),
    margin_percent: Number(refs.productMarginPercent.value),
    sale_price: salePrice,
    quantity: Number(refs.productQuantity.value),
    quantity_unit: refs.productQuantityUnit.value.trim() || DEFAULT_QUANTITY_UNIT,
    low_stock_threshold: Number(refs.productLowStockThreshold.value),
    company_id: optionalNumber(refs.productCompany.value),
    supplier_id: optionalNumber(refs.productSupplier.value),
    tags: state.productFormTags,
  };

  const isEditing = state.editingProductId !== null;
  const path = isEditing ? `/products/${state.editingProductId}` : "/products";
  const method = isEditing ? "PATCH" : "POST";

  setBusy(true);

  try {
    await request(path, {
      method,
      body: JSON.stringify(payload),
    });

    resetProductForm();
    closeDrawer();
    await loadAll({ quiet: true });
    showNotice(isEditing ? "Товар обновлен." : "Товар добавлен.");
  } catch (error) {
    showNotice(error.message, true);
  } finally {
    setBusy(false);
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
  navigateToProductEdit(productId);
}

async function showProductEditWorkflow(productId) {
  const product = state.products.find((item) => item.id === productId);

  if (product) {
    fillProductEditForm(product);
    return;
  }

  setBusy(true);

  try {
    const loadedProduct = await request(`/products/${productId}`);
    const currentRoute = getCurrentRoute();

    if (currentRoute.modal !== "productEdit" || currentRoute.id !== productId) {
      return;
    }

    rememberMovementProducts([loadedProduct]);
    fillProductEditForm(loadedProduct);
  } catch (error) {
    showNotice(error.message, true);
    navigateToSection("products");
  } finally {
    setBusy(false);
  }
}

function fillProductEditForm(product) {
  state.editingProductId = product.id;
  renderSelects();
  refs.productId.value = product.id;
  refs.productName.value = product.name;
  refs.productPurchasePrice.value = product.purchase_price;
  refs.productMarginPercent.value = product.margin_percent;
  refs.productFloorPrice.value = product.floor_price;
  refs.productSalePrice.value = product.sale_price;
  refs.productQuantity.value = product.quantity;
  refs.productQuantityUnit.value = product.quantity_unit || DEFAULT_QUANTITY_UNIT;
  refs.productLowStockThreshold.value =
    product.low_stock_threshold ?? DEFAULT_LOW_STOCK_THRESHOLD;
  refs.productCompany.value = product.company_id ?? "";
  refs.productSupplier.value = product.supplier_id ?? "";
  setProductFormTags(product.tags);
  refs.productSubmit.textContent = "Сохранить";
  refs.cancelEdit.classList.remove("hidden");
  openDrawer("product", "Редактор", "Изменить товар");
  updateProductPricingPreview();
  refs.productName.focus();
}

function resetProductForm() {
  state.editingProductId = null;
  refs.productForm.reset();
  renderSelects();
  refs.productMarginPercent.value = 0;
  refs.productFloorPrice.value = "";
  refs.productSalePrice.value = "";
  refs.productQuantity.value = 0;
  refs.productQuantityUnit.value = DEFAULT_QUANTITY_UNIT;
  refs.productLowStockThreshold.value = DEFAULT_LOW_STOCK_THRESHOLD;
  refs.productCompany.value = "";
  refs.productSupplier.value = "";
  setProductFormTags([]);
  refs.productTagInput.value = "";
  hideTagSuggestions(refs.productTagSuggestions);
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
