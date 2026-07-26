import { elements } from "./dom.js";
import { bindCompaniesFeature, loadCompanies } from "./companies.js";
import { bindDashboardFeature, loadDashboard } from "./dashboard.js";
import { bindProductsFeature, loadProducts } from "./products.js";
import { bindRestocksFeature, loadRestocks } from "./restocks.js";
import { bindSalesFeature, loadSales } from "./sales.js";
import { bindSuppliersFeature, loadSuppliers } from "./suppliers.js";
import { setActiveView } from "./render.js";

initializeApp();

function initializeApp() {
  bindNavigation();
  bindDashboardFeature();
  bindProductsFeature();
  bindCompaniesFeature();
  bindSuppliersFeature();
  bindRestocksFeature();
  bindSalesFeature();
  setActiveView("dashboard");

  void Promise.all([
    loadDashboard(),
    loadProducts(),
    loadCompanies(),
    loadSuppliers(),
    loadRestocks(),
    loadSales(),
  ]);
}

function bindNavigation() {
  for (const tab of elements.navTabs) {
    tab.addEventListener("click", () => {
      setActiveView(tab.dataset.viewTab);
    });
  }
}
