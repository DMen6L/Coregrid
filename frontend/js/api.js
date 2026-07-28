import { request } from "./utils.js";

export const FIRST_PAGE = 1;
export const DEFAULT_PAGE_SIZE = 20;
export const LOOKUP_PAGE_SIZE = 10;

export function getSummaries({ days = 7, bestSalesMode = "quantity" } = {}) {
  const params = new URLSearchParams();
  params.set("days", String(days));
  params.set("best_sales_mode", bestSalesMode);

  return request(`/summaries?${params.toString()}`);
}

export function getProducts({
  search = "",
  page = FIRST_PAGE,
  pageSize = DEFAULT_PAGE_SIZE,
} = {}) {
  return request(buildListPath("/products", search, page, pageSize));
}

export function createProduct(payload) {
  return request("/products", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getProduct(productId) {
  return request(`/products/${productId}`);
}

export function patchProduct(productId, payload) {
  return request(`/products/${productId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function createProductSupplierLinks(productId, payload) {
  return request(`/products/${productId}/links`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getCompanies({ search = "", page = FIRST_PAGE, pageSize = DEFAULT_PAGE_SIZE } = {}) {
  return request(buildListPath("/companies", search, page, pageSize));
}

export function getCompany(companyId) {
  return request(`/companies/${companyId}`);
}

export function createCompany(payload) {
  return request("/companies", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function patchCompany(companyId, payload) {
  return request(`/companies/${companyId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function getSuppliers({ search = "", page = FIRST_PAGE, pageSize = DEFAULT_PAGE_SIZE } = {}) {
  return request(buildListPath("/suppliers", search, page, pageSize));
}

export function getSupplier(supplierId) {
  return request(`/suppliers/${supplierId}`);
}

export function createSupplier(payload) {
  return request("/suppliers", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function patchSupplier(supplierId, payload) {
  return request(`/suppliers/${supplierId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function getTags({ search = "", page = FIRST_PAGE } = {}) {
  return request(buildListPath("/tags", search, page));
}

export function getRestocks({
  dateFrom = "",
  dateTo = "",
  page = FIRST_PAGE,
  pageSize = DEFAULT_PAGE_SIZE,
} = {}) {
  return request(buildDatedListPath("/restocks", dateFrom, dateTo, page, pageSize));
}

export function getRestock(restockId) {
  return request(`/restocks/${restockId}`);
}

export function createRestock(payload) {
  return request("/restocks", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getSales({
  dateFrom = "",
  dateTo = "",
  page = FIRST_PAGE,
  pageSize = DEFAULT_PAGE_SIZE,
} = {}) {
  return request(buildDatedListPath("/sales", dateFrom, dateTo, page, pageSize));
}

export function getSale(saleId) {
  return request(`/sales/${saleId}`);
}

export function createSale(payload) {
  return request("/sales", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function buildLookupPath(kind, search) {
  const basePath = kind === "supplier" ? "/suppliers" : "/companies";
  return buildListPath(basePath, search, FIRST_PAGE, LOOKUP_PAGE_SIZE);
}

function buildListPath(basePath, search, page, pageSize = DEFAULT_PAGE_SIZE) {
  const params = new URLSearchParams();

  if (search) {
    params.set("search", search);
  }

  params.set("page", String(Math.max(Number(page) || FIRST_PAGE, FIRST_PAGE)));
  params.set("page_size", String(pageSize));

  return `${basePath}?${params.toString()}`;
}

function buildDatedListPath(basePath, dateFrom, dateTo, page, pageSize = DEFAULT_PAGE_SIZE) {
  const params = new URLSearchParams();

  if (dateFrom) {
    params.set("from", dateFrom);
  }

  if (dateTo) {
    params.set("to", dateTo);
  }

  params.set("page", String(Math.max(Number(page) || FIRST_PAGE, FIRST_PAGE)));
  params.set("page_size", String(pageSize));

  return `${basePath}?${params.toString()}`;
}
