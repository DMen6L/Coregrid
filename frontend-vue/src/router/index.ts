import { createRouter, createWebHistory } from "vue-router";

import CompaniesView from "../views/CompaniesView.vue";
import DashboardView from "../views/DashboardView.vue";
import ProductsView from "../views/ProductsView.vue";
import RestocksView from "../views/RestocksView.vue";
import SalesView from "../views/SalesView.vue";
import SuppliersView from "../views/SuppliersView.vue";

const router = createRouter({
  history: createWebHistory(),
  linkActiveClass: "active",
  linkExactActiveClass: "active",
  routes: [
    { path: "/", redirect: "/dashboard" },
    {
      path: "/dashboard",
      name: "dashboard",
      component: DashboardView,
    },
    {
      path: "/products",
      name: "products",
      component: ProductsView,
    },
    {
      path: "/companies",
      name: "companies",
      component: CompaniesView,
    },
    {
      path: "/suppliers",
      name: "suppliers",
      component: SuppliersView,
    },
    {
      path: "/restocks",
      name: "restocks",
      component: RestocksView,
    },
    {
      path: "/sales",
      name: "sales",
      component: SalesView,
    },
  ],
});

export default router;
