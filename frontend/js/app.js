import { request } from "./utils.js";
import {
  elements,
  setActiveView,
  setAppMessage,
  setProductsError,
  setProductsLoading,
  setProductsSearchTerm,
  setState,
} from "./states.js";

initializeApp();

function initializeApp() {
  bindNavigation();
  bindProductSearch();
  setActiveView("dashboard");
  loadInitialData();
}

function bindNavigation() {
  for (const tab of elements.navTabs) {
    tab.addEventListener("click", () => {
      setActiveView(tab.dataset.viewTab);
    });
  }
}

function bindProductSearch() {
  elements.products.searchForm.addEventListener("submit", (event) => {
    event.preventDefault();

    if (elements.products.searchButton.disabled) {
      return;
    }

    const searchTerm = elements.products.searchInput.value.trim();
    loadProducts(searchTerm);
  });
}

async function loadInitialData() {
  await Promise.all([loadDashboardSummary(), loadProducts()]);
}

async function loadDashboardSummary() {
  setAppMessage("");

  try {
    const summary = await request("/summaries");

    setState("sales.value", summary.dashboard_sales_value);
    setState("sales.count", summary.dashboard_sales_count);
    setState("products.lowStock", summary.low_stock);
    setState("products.outOfStock", summary.out_of_stock);
  } catch (error) {
    console.error("Could not load dashboard summaries:", error);
    setAppMessage(getRequestErrorMessage(error, "показатели дэшборда"));
  }
}

async function loadProducts(searchTerm = "") {
  setProductsLoading(true);
  setProductsSearchTerm(searchTerm);
  setProductsError("");

  try {
    const productsResponse = await request(getProductsPath(searchTerm));
    setState("products.list", getProductItems(productsResponse));
  } catch (error) {
    console.error("Could not load products:", error);
    setState("products.list", []);
    setProductsError(getRequestErrorMessage(error, "товары"));
  } finally {
    setProductsLoading(false);
  }
}

function getProductsPath(searchTerm) {
  const params = new URLSearchParams();

  if (searchTerm) {
    params.set("search", searchTerm);
  }

  const queryString = params.toString();
  return queryString ? `/products?${queryString}` : "/products";
}

function getProductItems(productsResponse) {
  if (Array.isArray(productsResponse)) {
    return productsResponse;
  }

  return Array.isArray(productsResponse?.items) ? productsResponse.items : [];
}

function getRequestErrorMessage(error, label) {
  if (error?.status) {
    return `Не удалось загрузить ${label}. API вернул статус ${error.status}.`;
  }

  return `Не удалось загрузить ${label}. Проверьте, что API запущен.`;
}
