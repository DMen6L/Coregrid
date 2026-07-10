function openDrawer(formType, eyebrow, title) {
  state.activeDrawerForm = formType;
  refs.drawerEyebrow.textContent = eyebrow;
  refs.drawerTitle.textContent = title;
  refs.drawer.dataset.activeForm = formType;

  refs.drawerForms.forEach((form) => {
    form.classList.toggle("hidden", form.dataset.drawerForm !== formType);
  });

  refs.drawer.classList.remove("hidden");
  refs.drawerBackdrop.classList.remove("hidden");
  refs.drawer.setAttribute("aria-hidden", "false");
  document.body.classList.add("drawer-open");
}

function closeDrawer() {
  const activeForm = state.activeDrawerForm;

  if (!activeForm) {
    return;
  }

  state.activeDrawerForm = null;
  refs.drawer.classList.add("hidden");
  refs.drawerBackdrop.classList.add("hidden");
  refs.drawer.setAttribute("aria-hidden", "true");
  delete refs.drawer.dataset.activeForm;
  document.body.classList.remove("drawer-open");
  resetDrawerForm(activeForm);
}

function resetDrawerForm(formType) {
  if (formType === "product") {
    resetProductForm();
    return;
  }

  if (formType === "supplier") {
    refs.supplierForm.reset();
    return;
  }

  if (formType === "company") {
    refs.companyForm.reset();
    return;
  }

  if (formType === "movement") {
    resetMovementForm();
    return;
  }

  if (formType === "sale") {
    resetSaleForm();
  }
}

function handleDocumentKeydown(event) {
  if (event.key === "Escape" && state.activeDrawerForm) {
    closeDrawer();
  }
}

function openProductCreate() {
  resetProductForm();
  openDrawer("product", "Редактор", "Добавить товар");
  updateProductPricingPreview();
  refs.productName.focus();
}

function openSupplierCreate() {
  refs.supplierForm.reset();
  openDrawer("supplier", "Редактор", "Добавить поставщика");
  refs.supplierName.focus();
}

function openCompanyCreate() {
  refs.companyForm.reset();
  openDrawer("company", "Редактор", "Добавить компанию");
  refs.companyName.focus();
}

function openMovementCreate() {
  resetMovementForm();
  openDrawer("movement", "Операция", "Добавить движение");
  refs.movementType.focus();
}

function openSaleCreate() {
  resetSaleForm();
  openDrawer("sale", "Продажа", "Новая продажа");
  refs.saleLines
    .querySelector("[data-movement-product-search]")
    ?.focus();
}

function handleTabClick(event) {
  const tab = event.currentTarget.dataset.tabTarget;

  activateTab(tab);
}

function activateTab(tab) {
  if (tab === state.activeTab) {
    return;
  }

  closeDrawer();
  state.activeTab = tab;
  renderTabs();

  if (tab === "stockMovements" && !state.stockMovementsLoaded) {
    loadPage("stockMovements");
  }
}

function openProductsWithStockFilter(stockFilter) {
  closeDrawer();
  state.stockFilter = stockFilter;
  state.searchTerm = "";
  state.selectedTagFilters = [];
  state.pagination.products.page = 1;
  refs.stockFilter.value = stockFilter;
  refs.productSearch.value = "";
  hideTagSuggestions(refs.productSearchTagSuggestions);
  state.activeTab = "products";
  renderTabs();
  renderSelectedSearchTags();
  loadPage("products");
}
