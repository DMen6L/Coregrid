import { request } from "./utils.js";
import {
  elements,
  state,
  setActiveView,
  setAppMessage,
  resetProductCreateForm,
  setProductCreateError,
  setProductCreateSubmitting,
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
  bindProductCreate();
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

function bindProductCreate() {
  elements.products.createForm.addEventListener("submit", (event) => {
    event.preventDefault();

    if (
      elements.products.createSubmitButton.disabled ||
      !elements.products.createForm.reportValidity()
    ) {
      return;
    }

    createProduct();
  });

  elements.products.createModal.addEventListener("hidden.bs.modal", () => {
    if (!state.products.isCreating) {
      resetProductCreateForm();
    }
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

async function createProduct() {
  setProductCreateSubmitting(true);
  setProductCreateError("");

  try {
    await request("/products", {
      method: "POST",
      body: JSON.stringify(getProductCreatePayload()),
    });

    hideProductCreateModal();
    resetProductCreateForm();

    await Promise.all([
      loadDashboardSummary(),
      loadProducts(state.products.searchTerm, state.products.page),
    ]);
  } catch (error) {
    console.error("Could not create product:", error);
    setProductCreateError(getCreateProductErrorMessage(error));
  } finally {
    setProductCreateSubmitting(false);
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

function getProductCreatePayload() {
  const formData = new FormData(elements.products.createForm);

  return {
    name: getTextField(formData, "name"),
    purchase_price: getNumberField(formData, "purchase_price"),
    margin_percent: getNumberField(formData, "margin_percent"),
    sale_price: getOptionalNumberField(formData, "sale_price"),
    quantity: getNumberField(formData, "quantity"),
    quantity_unit: getTextField(formData, "quantity_unit") || "шт",
    low_stock_threshold: getNumberField(formData, "low_stock_threshold"),
    company_id: getOptionalNumberField(formData, "company_id"),
    supplier_id: getOptionalNumberField(formData, "supplier_id"),
    tags: getTagsField(formData),
  };
}

function getTextField(formData, key) {
  return String(formData.get(key) || "").trim();
}

function getNumberField(formData, key) {
  return Number(getTextField(formData, key));
}

function getOptionalNumberField(formData, key) {
  const value = getTextField(formData, key);
  return value ? Number(value) : null;
}

function getTagsField(formData) {
  const tags = getTextField(formData, "tags");

  if (!tags) {
    return [];
  }

  return tags
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function hideProductCreateModal() {
  const Modal = window.bootstrap?.Modal;

  if (!Modal) {
    return;
  }

  Modal.getOrCreateInstance(elements.products.createModal).hide();
}

function getCreateProductErrorMessage(error) {
  const detail = error?.data?.detail;

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const field = Array.isArray(item.loc) ? item.loc.slice(1).join(".") : "";
        return field ? `${field}: ${item.msg}` : item.msg;
      })
      .filter(Boolean)
      .join(" ");
  }

  if (typeof detail === "string") {
    return detail;
  }

  if (error?.status) {
    return `Не удалось создать товар. API вернул статус ${error.status}.`;
  }

  return "Не удалось создать товар. Проверьте, что API запущен.";
}

function getRequestErrorMessage(error, label) {
  if (error?.status) {
    return `Не удалось загрузить ${label}. API вернул статус ${error.status}.`;
  }

  return `Не удалось загрузить ${label}. Проверьте, что API запущен.`;
}
