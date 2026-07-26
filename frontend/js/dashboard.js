import { getSummaries } from "./api.js";
import { elements } from "./dom.js";
import { getRequestErrorMessage } from "./format.js";
import { renderDashboard } from "./render.js";
import { state } from "./state.js";

const MIN_DASHBOARD_DAYS = 7;
const MAX_DASHBOARD_DAYS = 365;
const DEFAULT_DASHBOARD_DAYS = 7;
const DEFAULT_BEST_SALES_MODE = "quantity";
const BEST_SALES_MODES = new Set(["quantity", "revenue", "gross_profit"]);

export function bindDashboardFeature() {
  elements.dashboard.form.addEventListener("submit", (event) => {
    event.preventDefault();

    if (!elements.dashboard.form.reportValidity() || state.dashboard.isLoading) {
      return;
    }

    void loadDashboard({
      days: elements.dashboard.daysInput.value,
      bestSalesMode: elements.dashboard.bestSalesModeSelect.value,
    });
  });
}

export async function loadDashboard({
  days = state.dashboard.days,
  bestSalesMode = state.dashboard.bestSalesMode,
} = {}) {
  state.dashboard.days = normalizeDays(days);
  state.dashboard.bestSalesMode = normalizeBestSalesMode(bestSalesMode);
  state.dashboard.isLoading = true;
  state.dashboard.error = "";
  renderDashboard();

  try {
    state.dashboard.data = await getSummaries({
      days: state.dashboard.days,
      bestSalesMode: state.dashboard.bestSalesMode,
    });
  } catch (error) {
    console.error("Could not load dashboard summaries:", error);
    state.dashboard.data = null;
    state.dashboard.error = getRequestErrorMessage(error, "дэшборд");
  } finally {
    state.dashboard.isLoading = false;
    renderDashboard();
  }
}

function normalizeDays(value) {
  const days = Number(value) || DEFAULT_DASHBOARD_DAYS;
  return Math.min(Math.max(Math.trunc(days), MIN_DASHBOARD_DAYS), MAX_DASHBOARD_DAYS);
}

function normalizeBestSalesMode(value) {
  return BEST_SALES_MODES.has(value) ? value : DEFAULT_BEST_SALES_MODE;
}
