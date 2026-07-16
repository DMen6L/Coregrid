import { request } from "./utils.js";
import {
  elements,
  setActiveView,
  setAppMessage,
  setProductsError,
  setProductsLoading,
  setState,
} from "./states.js";

initializeApp();

function initializeApp() {
  bindNavigation();
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

async function loadProducts() {
  setProductsLoading(true);
  setProductsError("");

  try {
    const products = await request("/products");
    setState("products.list", products);
  } catch (error) {
    console.error("Could not load products:", error);
    setState("products.list", []);
    setProductsError(getRequestErrorMessage(error, "товары"));
  } finally {
    setProductsLoading(false);
  }
}

function getRequestErrorMessage(error, label) {
  if (error?.status) {
    return `Не удалось загрузить ${label}. API вернул статус ${error.status}.`;
  }

  return `Не удалось загрузить ${label}. Проверьте, что API запущен.`;
}
