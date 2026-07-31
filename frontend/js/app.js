import { elements } from "./dom.js";
import {
  API_BASE_OPTIONS,
  CUSTOM_API_BASE_OPTION,
  getApiBaseSelection,
  getBaseApi,
  setBaseApi,
} from "./config.js";
import { bindCompaniesFeature, loadCompanies } from "./companies.js";
import { bindDashboardFeature, loadDashboard } from "./dashboard.js";
import { bindProductsFeature, loadProductPopularTags, loadProducts } from "./products.js";
import { bindRestocksFeature, loadRestocks } from "./restocks.js";
import { bindSalesFeature, loadSales } from "./sales.js";
import { bindSuppliersFeature, loadSuppliers } from "./suppliers.js";
import { setActiveView, setAppMessage } from "./render.js";

initializeApp();

function initializeApp() {
  bindNavigation();
  bindApiConfig();
  bindDashboardFeature();
  bindProductsFeature();
  bindCompaniesFeature();
  bindSuppliersFeature();
  bindRestocksFeature();
  bindSalesFeature();
  setActiveView("dashboard");

  void loadInitialData();
}

function loadInitialData() {
  return Promise.all([
    loadDashboard(),
    loadProducts(),
    loadProductPopularTags(),
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

function bindApiConfig() {
  populateApiBaseSelect();
  syncApiConfigForm();

  elements.apiConfig.select.addEventListener("change", () => {
    const isCustom = elements.apiConfig.select.value === CUSTOM_API_BASE_OPTION;

    setCustomApiInputVisibility(isCustom);

    if (isCustom) {
      elements.apiConfig.customInput.value = getBaseApi();
      elements.apiConfig.customInput.focus();
    }
  });

  elements.apiConfig.form.addEventListener("submit", (event) => {
    event.preventDefault();
    applyApiConfig();
  });
}

function populateApiBaseSelect() {
  const fragment = document.createDocumentFragment();

  for (const option of API_BASE_OPTIONS) {
    const optionElement = document.createElement("option");

    optionElement.value = option.value;
    optionElement.textContent = option.label;
    fragment.append(optionElement);
  }

  const customOption = document.createElement("option");

  customOption.value = CUSTOM_API_BASE_OPTION;
  customOption.textContent = "Другой";
  fragment.append(customOption);

  elements.apiConfig.select.replaceChildren(fragment);
}

function syncApiConfigForm() {
  const baseApi = getBaseApi();
  const selectedValue = getApiBaseSelection(baseApi);
  const isCustom = selectedValue === CUSTOM_API_BASE_OPTION;

  elements.apiConfig.select.value = selectedValue;
  elements.apiConfig.customInput.value = baseApi;
  elements.apiConfig.customInput.setCustomValidity("");
  setCustomApiInputVisibility(isCustom);
}

function setCustomApiInputVisibility(isVisible) {
  elements.apiConfig.customInput.classList.toggle("d-none", !isVisible);
  elements.apiConfig.customInput.disabled = !isVisible;
  elements.apiConfig.customInput.required = isVisible;
}

function applyApiConfig() {
  const selectedValue = elements.apiConfig.select.value;
  const nextBaseApi = selectedValue === CUSTOM_API_BASE_OPTION
    ? elements.apiConfig.customInput.value
    : selectedValue;

  try {
    const baseApi = setBaseApi(nextBaseApi);

    syncApiConfigForm();
    setAppMessage(`API: ${baseApi}`, "info");
    void loadInitialData();
  } catch {
    elements.apiConfig.customInput.setCustomValidity("Введите корректный URL API.");
    elements.apiConfig.customInput.reportValidity();
    setAppMessage("Некорректный адрес API.", "danger");
  }
}
