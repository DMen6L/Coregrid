import { createRouter, createWebHistory } from "vue-router";

import CompaniesView from "../views/CompaniesView.vue";
import AuthView from "../views/AuthView.vue";
import DashboardView from "../views/DashboardView.vue";
import HomeView from "../views/HomeView.vue";
import MeView from "../views/MeView.vue";
import MembersView from "../views/MembersView.vue";
import ProductsView from "../views/ProductsView.vue";
import RestocksView from "../views/RestocksView.vue";
import SalesView from "../views/SalesView.vue";
import SuppliersView from "../views/SuppliersView.vue";
import { getAuthToken } from "../lib/authSession";

const router = createRouter({
  history: createWebHistory(),
  linkActiveClass: "active",
  linkExactActiveClass: "active",
  routes: [
    {
      path: "/",
      name: "home",
      component: HomeView,
    },
    {
      path: "/auth",
      name: "auth",
      component: AuthView,
    },
    {
      path: "/dashboard",
      name: "dashboard",
      component: DashboardView,
      meta: { requiresAuth: true, requiresWorkspace: true },
    },
    {
      path: "/me",
      name: "me",
      component: MeView,
      meta: { requiresAuth: true },
    },
    {
      path: "/products",
      name: "products",
      component: ProductsView,
      meta: { requiresAuth: true, requiresWorkspace: true },
    },
    {
      path: "/companies",
      name: "companies",
      component: CompaniesView,
      meta: { requiresAuth: true, requiresWorkspace: true },
    },
    {
      path: "/suppliers",
      name: "suppliers",
      component: SuppliersView,
      meta: { requiresAuth: true, requiresWorkspace: true },
    },
    {
      path: "/members",
      name: "members",
      component: MembersView,
      meta: { requiresAuth: true, requiresWorkspace: true },
    },
    {
      path: "/restocks",
      name: "restocks",
      component: RestocksView,
      meta: { requiresAuth: true, requiresWorkspace: true },
    },
    {
      path: "/sales",
      name: "sales",
      component: SalesView,
      meta: { requiresAuth: true, requiresWorkspace: true },
    },
  ],
});

router.beforeEach((to) => {
  const isAuthenticated = Boolean(getAuthToken());

  if (to.meta.requiresAuth && !isAuthenticated) {
    return {
      path: "/auth",
      query: {
        mode: "login",
        redirect: to.fullPath,
      },
    };
  }

  if (to.name === "auth" && isAuthenticated) {
    return { path: "/dashboard" };
  }

  return true;
});

export default router;
