import { request } from "./utils.js";
import {
  elements,
  state,
  setActiveView,
  setAppMessage,
  setProductsError,
  setProductsLoading,
  setProductsPagination,
  setProductsSearchTerm,
  setState,
} from "./states.js";

const FIRST_PRODUCTS_PAGE = 1;

initializeApp();

function initializeApp() {
  bindNavigation();
  bindProductSearch();
  bindProductPagination();
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
    loadProducts(searchTerm, FIRST_PRODUCTS_PAGE);
  });
}

function bindProductPagination() {
  elements.products.previousPageButton.addEventListener("click", () => {
    if (elements.products.previousPageButton.disabled) {
      return;
    }

    loadProducts(state.products.searchTerm, state.products.page - 1);
  });

  elements.products.nextPageButton.addEventListener("click", () => {
    if (elements.products.nextPageButton.disabled) {
      return;
    }

    loadProducts(state.products.searchTerm, state.products.page + 1);
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

async function loadProducts(searchTerm = "", page = FIRST_PRODUCTS_PAGE) {
  setProductsLoading(true);
  setProductsSearchTerm(searchTerm);
  setProductsError("");

  try {
    const productsResponse = await request(getProductsPath(searchTerm, page));
    const productsPage = getProductsPage(productsResponse);

    setProductsPagination(productsPage.pagination);
    setState("products.list", productsPage.items);
  } catch (error) {
    console.error("Could not load products:", error);
    setProductsPagination({
      page,
      pageSize: state.products.pageSize,
      total: 0,
      totalPages: 0,
      hasNext: false,
      hasPrevious: false,
    });
    setState("products.list", []);
    setProductsError(getRequestErrorMessage(error, "товары"));
  } finally {
    setProductsLoading(false);
  }
}

function getProductsPath(searchTerm, page) {
  const params = new URLSearchParams();

  if (searchTerm) {
    params.set("search", searchTerm);
  }

  params.set("page", String(Math.max(page, FIRST_PRODUCTS_PAGE)));

  const queryString = params.toString();
  return queryString ? `/products?${queryString}` : "/products";
}

function getProductsPage(productsResponse) {
  if (Array.isArray(productsResponse)) {
    return {
      items: productsResponse,
      pagination: {
        page: FIRST_PRODUCTS_PAGE,
        pageSize: productsResponse.length,
        total: productsResponse.length,
        totalPages: productsResponse.length > 0 ? 1 : 0,
        hasNext: false,
        hasPrevious: false,
      },
    };
  }

  return {
    items: Array.isArray(productsResponse?.items) ? productsResponse.items : [],
    pagination: {
      page: Number(productsResponse?.page || FIRST_PRODUCTS_PAGE),
      pageSize: Number(productsResponse?.page_size || 20),
      total: Number(productsResponse?.total || 0),
      totalPages: Number(productsResponse?.total_pages || 0),
      hasNext: Boolean(productsResponse?.has_next),
      hasPrevious: Boolean(productsResponse?.has_previous),
    },
  };
}

function getRequestErrorMessage(error, label) {
  if (error?.status) {
    return `Не удалось загрузить ${label}. API вернул статус ${error.status}.`;
  }

  return `Не удалось загрузить ${label}. Проверьте, что API запущен.`;
}
