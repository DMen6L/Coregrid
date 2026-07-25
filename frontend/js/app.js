import { elements } from "./dom.js";
import { bindCompaniesFeature, loadCompanies } from "./companies.js";
import { bindProductsFeature, loadProducts } from "./products.js";
import { bindSuppliersFeature, loadSuppliers } from "./suppliers.js";
import { renderParkedViews, setActiveView } from "./render.js";

initializeApp();

function initializeApp() {
  bindNavigation();
  bindProductsFeature();
  bindCompaniesFeature();
  bindSuppliersFeature();
  renderParkedViews();
  setActiveView("products");

  void Promise.all([
    loadProducts(),
    loadCompanies(),
    loadSuppliers(),
  ]);
}

function bindNavigation() {
  for (const tab of elements.navTabs) {
    tab.addEventListener("click", () => {
      setActiveView(tab.dataset.viewTab);
    });
  }
}
