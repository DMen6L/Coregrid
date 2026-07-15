import { request } from "./utils.js";
import { elements, state, setState } from "./states.js";

initializeApp();

async function initializeApp() {
  try {
    const summary = await request("/summaries");

    console.log(summary);
    setState("sales.value", summary.dashboard_sales_value);
    setState("sales.count", summary.dashboard_sales_count);
    setState("products.lowStock", summary.low_stock);
    setState("products.outOfStock", summary.out_of_stock);
  } catch (error) {
    console.error("Could not load dashboard summaries:", error);
  }
}
