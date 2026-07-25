import { request } from "./utils.js";

export const FIRST_PAGE = 1;
export const DEFAULT_PAGE_SIZE = 20;
export const LOOKUP_PAGE_SIZE = 10;

export function getProducts({ search = "", page = FIRST_PAGE } = {}) {
  return request(buildListPath("/products", search, page));
}

export function createProduct(payload) {
  return request("/products", {
    method: "POST",
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

export function createCompany(payload) {
  return request("/companies", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getSuppliers({ search = "", page = FIRST_PAGE, pageSize = DEFAULT_PAGE_SIZE } = {}) {
  return request(buildListPath("/suppliers", search, page, pageSize));
}

export function createSupplier(payload) {
  return request("/suppliers", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getTags({ search = "", page = FIRST_PAGE } = {}) {
  return request(buildListPath("/tags", search, page));
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
