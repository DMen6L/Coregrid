document.addEventListener("DOMContentLoaded", init);

function init() {
  refs.apiBase.value = state.apiBase;
  refs.dashboardSalesDateFrom.value = state.salesDateFrom;
  refs.dashboardSalesDateTo.value = state.salesDateTo;

  refs.tabButtons.forEach((button) => {
    button.addEventListener("click", handleTabClick);
  });
  refs.apiSettings.addEventListener("submit", handleApiSettingsSubmit);
  refs.drawerBackdrop.addEventListener("click", closeDrawer);
  refs.drawerClose.addEventListener("click", closeDrawer);
  document.addEventListener("keydown", handleDocumentKeydown);
  refs.addProductButton.addEventListener("click", openProductCreate);
  refs.addSupplierButton.addEventListener("click", openSupplierCreate);
  refs.addCompanyButton.addEventListener("click", openCompanyCreate);
  refs.addMovementButton.addEventListener("click", openMovementCreate);
  refs.dashboardAddProductButton.addEventListener("click", openProductCreate);
  refs.dashboardAddSaleButton.addEventListener("click", openSaleCreate);
  refs.dashboardAddMovementButton.addEventListener("click", openMovementCreate);
  refs.dashboardRefreshButton.addEventListener("click", loadDashboard);
  refs.dashboardLowStockButton.addEventListener("click", () => {
    openProductsWithStockFilter("low");
  });
  refs.dashboardOutOfStockButton.addEventListener("click", () => {
    openProductsWithStockFilter("empty");
  });
  refs.dashboardViewMovementsButton.addEventListener("click", () => {
    activateTab("stockMovements");
  });
  refs.dashboardSalesForm.addEventListener("submit", handleDashboardSalesSubmit);
  refs.refreshButton.addEventListener("click", loadAll);
  refs.productSearch.addEventListener("input", handleSearchInput);
  refs.productSearch.addEventListener("keydown", handleSearchKeydown);
  refs.productSearchTagSuggestions.addEventListener(
    "click",
    handleProductSearchTagSuggestionClick,
  );
  refs.selectedSearchTags.addEventListener("click", handleSelectedSearchTagsClick);
  refs.stockFilter.addEventListener("change", handleStockFilterChange);
  refs.productPurchasePrice.addEventListener("input", updateProductPricingPreview);
  refs.productMarginPercent.addEventListener("input", updateProductPricingPreview);
  refs.productForm.addEventListener("submit", handleProductSubmit);
  refs.productTagInput.addEventListener("input", handleProductTagInput);
  refs.productTagInput.addEventListener("keydown", handleProductTagKeydown);
  refs.addProductTagButton.addEventListener("click", addProductTagFromInput);
  refs.productTagList.addEventListener("click", handleProductTagListClick);
  refs.productTagSuggestions.addEventListener("click", handleProductTagSuggestionClick);
  refs.cancelEdit.addEventListener("click", closeDrawer);
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
  refs.addMovementLineButton.addEventListener("click", () => addMovementLine());
  refs.movementLines.addEventListener("click", handleMovementLineListClick);
  refs.movementLines.addEventListener("input", handleMovementLineListInput);
  refs.movementType.addEventListener("change", updateMovementQuantityMode);
  refs.saleForm.addEventListener("submit", handleSaleSubmit);
  refs.addSaleLineButton.addEventListener("click", () => addSaleLine());
  refs.saleLines.addEventListener("click", handleSaleLineListClick);
  refs.saleLines.addEventListener("input", handleSaleLineListInput);

  updateMovementQuantityMode();
  loadAll();
}
