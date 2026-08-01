import { getBaseApi } from "./apiBase";
import type {
  BestSalesMode,
  CompanyCreatePayload,
  CompanyResponse,
  PaginatedResponse,
  ProductCreatePayload,
  ProductResponse,
  ProductSummaryResponse,
  SupplierSummaryResponse,
  SummariesResponse,
  TagSummaryResponse,
} from "../types/api";

export const FIRST_PAGE = 1;
export const DEFAULT_PAGE_SIZE = 20;

export class ApiRequestError extends Error {
  readonly status: number;
  readonly data: unknown;

  constructor(status: number, data: unknown) {
    super(`API request failed: ${status}`);
    this.name = "ApiRequestError";
    this.status = status;
    this.data = data;
  }
}

export async function request<T>(path: string, options: RequestInit = {}) {
  const headers = new Headers(options.headers);

  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${getBaseApi()}${path}`, {
    ...options,
    headers,
  });
  const data = response.status === 204 ? null : await response.json();

  if (!response.ok) {
    throw new ApiRequestError(response.status, data);
  }

  return data as T;
}

export function getSummaries({
  days = 7,
  bestSalesMode = "quantity",
}: {
  days?: number;
  bestSalesMode?: BestSalesMode;
} = {}) {
  const params = new URLSearchParams();

  params.set("days", String(days));
  params.set("best_sales_mode", bestSalesMode);

  return request<SummariesResponse>(`/summaries?${params.toString()}`);
}

export function getProducts({
  search = "",
  page = FIRST_PAGE,
  pageSize = DEFAULT_PAGE_SIZE,
}: {
  search?: string;
  page?: number;
  pageSize?: number;
} = {}) {
  return request<PaginatedResponse<ProductSummaryResponse>>(
    buildListPath("/products", search, page, pageSize),
  );
}

export function createProduct(payload: ProductCreatePayload) {
  return request<ProductResponse>("/products", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getTags({
  search = "",
  page = FIRST_PAGE,
  pageSize = DEFAULT_PAGE_SIZE,
}: {
  search?: string;
  page?: number;
  pageSize?: number;
} = {}) {
  return request<PaginatedResponse<TagSummaryResponse>>(
    buildListPath("/tags", search, page, pageSize),
  );
}

export function getCompanies({
  search = "",
  page = FIRST_PAGE,
  pageSize = DEFAULT_PAGE_SIZE,
}: {
  search?: string;
  page?: number;
  pageSize?: number;
} = {}) {
  return request<PaginatedResponse<CompanyResponse>>(
    buildListPath("/companies", search, page, pageSize),
  );
}

export function createCompany(payload: CompanyCreatePayload) {
  return request<CompanyResponse>("/companies", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getSuppliers({
  search = "",
  page = FIRST_PAGE,
  pageSize = DEFAULT_PAGE_SIZE,
}: {
  search?: string;
  page?: number;
  pageSize?: number;
} = {}) {
  return request<PaginatedResponse<SupplierSummaryResponse>>(
    buildListPath("/suppliers", search, page, pageSize),
  );
}

function buildListPath(basePath: string, search: string, page: number, pageSize: number) {
  const params = new URLSearchParams();

  if (search) {
    params.set("search", search);
  }

  params.set("page", String(Math.max(Number(page) || FIRST_PAGE, FIRST_PAGE)));
  params.set("page_size", String(pageSize));

  return `${basePath}?${params.toString()}`;
}
