const ROUTE_ROOT = "";

const SECTION_ROUTES = {
  dashboard: `${ROUTE_ROOT}/dashboard`,
  products: `${ROUTE_ROOT}/products`,
  suppliers: `${ROUTE_ROOT}/suppliers`,
  companies: `${ROUTE_ROOT}/companies`,
  stockMovements: `${ROUTE_ROOT}/stock-movements`,
};

const DEFAULT_ROUTE = SECTION_ROUTES.dashboard;

function initializeRouting() {
  window.addEventListener("popstate", () => {
    applyCurrentRoute();
  });

  const route = getCurrentRoute();
  replaceRouteState(route);
  applyRoute(route);
}

function navigateToSection(tab) {
  navigateToRoute(SECTION_ROUTES[tab] || DEFAULT_ROUTE);
}

function navigateToProductCreate() {
  navigateToRoute(`${ROUTE_ROOT}/products/new`);
}

function navigateToProductEdit(productId) {
  navigateToRoute(`${ROUTE_ROOT}/products/${productId}/edit`);
}

function navigateToSupplierCreate() {
  navigateToRoute(`${ROUTE_ROOT}/suppliers/new`);
}

function navigateToCompanyCreate() {
  navigateToRoute(`${ROUTE_ROOT}/companies/new`);
}

function navigateToMovementCreate() {
  navigateToRoute(`${ROUTE_ROOT}/stock-movements/new`);
}

function navigateToSaleCreate() {
  navigateToRoute(`${ROUTE_ROOT}/sales/new`);
}

function navigateToRoute(path, options = {}) {
  const route = parseRoute(path);

  if (!route) {
    return;
  }

  const statePayload = buildRouteState(route, options);
  const isCurrentRoute = normalizeRoutePath(window.location.pathname) === route.path;

  if (canUsePathRouting() && !isCurrentRoute) {
    const method = options.replace ? "replaceState" : "pushState";
    window.history[method](statePayload, "", route.path);
  }

  applyRoute(route);
}

function closeRoutedModal() {
  const route = getCurrentRoute();

  if (!route.modal) {
    return false;
  }

  const returnTo = window.history.state?.returnTo || route.sectionPath;

  closeDrawer({ syncRoute: false });

  if (!canUsePathRouting()) {
    applyRoute(parseRoute(returnTo));
    return true;
  }

  if (window.history.state?.directModal) {
    navigateToRoute(returnTo, { replace: true });
    return true;
  }

  window.history.back();
  return true;
}

function applyCurrentRoute() {
  applyRoute(getCurrentRoute());
}

function applyRoute(route) {
  if (!route) {
    navigateToRoute(DEFAULT_ROUTE, { replace: true });
    return;
  }

  activateTab(route.tab, { syncRoute: false });

  if (!route.modal) {
    closeDrawer({ syncRoute: false });
    return;
  }

  if (route.modal === "productCreate") {
    showProductCreateWorkflow();
    return;
  }

  if (route.modal === "productEdit") {
    showProductEditWorkflow(route.id);
    return;
  }

  if (route.modal === "supplierCreate") {
    showSupplierCreateWorkflow();
    return;
  }

  if (route.modal === "companyCreate") {
    showCompanyCreateWorkflow();
    return;
  }

  if (route.modal === "movementCreate") {
    showMovementCreateWorkflow();
    return;
  }

  if (route.modal === "saleCreate") {
    showSaleCreateWorkflow();
  }
}

function getCurrentRoute() {
  return parseRoute(window.location.pathname) || parseRoute(DEFAULT_ROUTE);
}

function parseRoute(path) {
  const normalizedPath = normalizeRoutePath(path);

  if (normalizedPath === ROUTE_ROOT || normalizedPath === "/") {
    return buildSectionRoute("dashboard", DEFAULT_ROUTE);
  }

  const sectionEntry = Object.entries(SECTION_ROUTES).find(
    ([, routePath]) => routePath === normalizedPath,
  );

  if (sectionEntry) {
    return buildSectionRoute(sectionEntry[0], normalizedPath);
  }

  if (normalizedPath === `${ROUTE_ROOT}/products/new`) {
    return buildModalRoute("products", normalizedPath, "productCreate");
  }

const productEditMatch = normalizedPath.match(
    /^\/products\/([1-9]\d*)\/edit$/,
  );

  if (productEditMatch) {
    return buildModalRoute(
      "products",
      normalizedPath,
      "productEdit",
      Number(productEditMatch[1]),
    );
  }

  if (normalizedPath === `${ROUTE_ROOT}/suppliers/new`) {
    return buildModalRoute("suppliers", normalizedPath, "supplierCreate");
  }

  if (normalizedPath === `${ROUTE_ROOT}/companies/new`) {
    return buildModalRoute("companies", normalizedPath, "companyCreate");
  }

  if (normalizedPath === `${ROUTE_ROOT}/stock-movements/new`) {
    return buildModalRoute("stockMovements", normalizedPath, "movementCreate");
  }

  if (normalizedPath === `${ROUTE_ROOT}/sales/new`) {
    return buildModalRoute("dashboard", normalizedPath, "saleCreate");
  }

  return null;
}

function buildSectionRoute(tab, path) {
  return {
    tab,
    path,
    sectionPath: path,
    modal: null,
    id: null,
  };
}

function buildModalRoute(tab, path, modal, id = null) {
  return {
    tab,
    path,
    sectionPath: SECTION_ROUTES[tab],
    modal,
    id,
  };
}

function normalizeRoutePath(path) {
  if (!path || path === "/index.html") {
    return DEFAULT_ROUTE;
  }

  return path.replace(/\/$/, "") || "/";
}

function replaceRouteState(route) {
  if (!canUsePathRouting()) {
    return;
  }

  window.history.replaceState(
    buildRouteState(route, { directModal: Boolean(route.modal) }),
    "",
    route.path,
  );
}

function buildRouteState(route, options = {}) {
  return {
    managedRoute: true,
    path: route.path,
    modal: Boolean(route.modal),
    directModal: Boolean(options.directModal),
    returnTo: route.modal ? getCurrentMeaningfulRoute() : null,
  };
}

function getCurrentMeaningfulRoute() {
  const currentRoute = parseRoute(window.location.pathname);

  if (!currentRoute) {
    return SECTION_ROUTES[state.activeTab] || DEFAULT_ROUTE;
  }

  if (currentRoute.modal) {
    return window.history.state?.returnTo || currentRoute.sectionPath;
  }

  return currentRoute.path;
}

function canUsePathRouting() {
  return window.location.protocol !== "file:";
}
