import { createRouter, createWebHistory } from "vue-router";

import CompaniesView from "../views/CompaniesView.vue";
import DashboardView from "../views/DashboardView.vue";
import PlaceholderView from "../views/PlaceholderView.vue";
import ProductsView from "../views/ProductsView.vue";
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
      component: PlaceholderView,
      props: { title: "Пополнения" },
    },
    {
      path: "/sales",
      name: "sales",
      component: PlaceholderView,
      props: { title: "Продажи" },
    },
  ],
});

export default router;
