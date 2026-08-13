import { getBaseApi } from "./apiBase";
import { getAuthToken } from "./authSession";
import { requireActiveWorkspaceId } from "./workspaceSession";
import type {
  BestSalesMode,
  CompanyCreatePayload,
  CompanyResponse,
  CompanyUpdatePayload,
  MeResponse,
  PaginatedResponse,
  ProductAtomicCreatePayload,
  ProductCreatePayload,
  ProductResponse,
  ProductSupplierCreatePayload,
  ProductSupplierResponse,
  ProductSupplierUpdatePayload,
  ProductSummaryResponse,
  ProductUpdatePayload,
  RestockCreatePayload,
  RestockResponse,
  RestockSummaryResponse,
  SaleCreatePayload,
  SaleResponse,
  SaleSummaryResponse,
  SupplierCreatePayload,
  SupplierResponse,
  SupplierSummaryResponse,
  SupplierUpdatePayload,
  SummariesResponse,
  TagSummaryResponse,
  TokenResponse,
  UserInvitationResponse,
  UserCreatePayload,
  UserLoginPayload,
  UserPasswordUpdatePayload,
  UserResponse,
  UserUpdatePayload,
  WorkspaceCreatePayload,
  WorkspaceAssignableRole,
  WorkspaceInvitationCreatePayload,
  WorkspaceInvitationResponse,
  WorkspaceMembershipResponse,
  WorkspaceMembershipSummaryResponse,
  WorkspaceResponse,
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

  const authToken = getAuthToken();
  if (authToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${authToken}`);
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

export function registerUser(payload: UserCreatePayload) {
  return request<UserResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function loginUser(payload: UserLoginPayload) {
  return request<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getCurrentUser() {
  return request<UserResponse>("/auth/me");
}

export function getMe() {
  return request<MeResponse>("/me");
}

export function patchMe(payload: UserUpdatePayload) {
  return request<MeResponse>("/me", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function patchMePassword(payload: UserPasswordUpdatePayload) {
  return request<MeResponse>("/me/password", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function getWorkspace(workspaceId: number) {
  return request<WorkspaceResponse>(`/workspaces/${workspaceId}`);
}

export function createWorkspace(payload: WorkspaceCreatePayload) {
  return request<WorkspaceResponse>("/workspaces", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getMyInvitations(): Promise<UserInvitationResponse[]> {
  const overview = await getMe();

  return overview.invitations;
}

export function acceptMyInvitation(invitationId: string) {
  return request<WorkspaceResponse>(
    `/me/accept/${encodeURIComponent(invitationId)}`,
    {
      method: "POST",
    },
  );
}

export function leaveMyWorkspace(workspaceId: number) {
  return request<void>(`/me/workspaces/${encodeURIComponent(String(workspaceId))}`, {
    method: "DELETE",
  });
}

export function getWorkspaceInvitations({
  search = "",
  page = FIRST_PAGE,
  pageSize = DEFAULT_PAGE_SIZE,
}: {
  search?: string;
  page?: number;
  pageSize?: number;
} = {}) {
  return request<PaginatedResponse<WorkspaceInvitationResponse>>(
    buildListPath(workspacePath("/invitations"), search, page, pageSize),
  );
}

export function createWorkspaceInvitation(payload: WorkspaceInvitationCreatePayload) {
  return request<WorkspaceInvitationResponse>(workspacePath("/invitations"), {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteWorkspaceInvitation(invitationId: string) {
  return request<void>(workspacePath(`/invitations/${encodeURIComponent(invitationId)}`), {
    method: "DELETE",
  });
}

export function getWorkspaceMembers({
  search = "",
  page = FIRST_PAGE,
  pageSize = DEFAULT_PAGE_SIZE,
}: {
  search?: string;
  page?: number;
  pageSize?: number;
} = {}) {
  return request<PaginatedResponse<WorkspaceMembershipSummaryResponse>>(
    buildListPath(workspacePath("/members"), search, page, pageSize),
  );
}

export function getWorkspaceMember(memberId: number) {
  return request<WorkspaceMembershipResponse>(
    workspacePath(`/members/${encodeURIComponent(String(memberId))}`),
  );
}

export function patchWorkspaceMemberRole(memberId: number, newRole: WorkspaceAssignableRole) {
  const params = new URLSearchParams();
  params.set("new_role", newRole);

  return request<WorkspaceMembershipResponse>(
    workspacePath(`/members/${encodeURIComponent(String(memberId))}/role?${params.toString()}`),
    {
      method: "PATCH",
    },
  );
}

export function deleteWorkspaceMember(memberId: number) {
  return request<void>(workspacePath(`/members/${encodeURIComponent(String(memberId))}`), {
    method: "DELETE",
  });
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

  return request<SummariesResponse>(workspacePath(`/summaries?${params.toString()}`));
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
    buildListPath(workspacePath("/products"), search, page, pageSize),
  );
}

export function getRestocks({
  dateFrom = "",
  dateTo = "",
  page = FIRST_PAGE,
  pageSize = DEFAULT_PAGE_SIZE,
}: {
  dateFrom?: string;
  dateTo?: string;
  page?: number;
  pageSize?: number;
} = {}) {
  return request<PaginatedResponse<RestockSummaryResponse>>(
    buildDateListPath(workspacePath("/restocks"), dateFrom, dateTo, page, pageSize),
  );
}

export function createRestock(payload: RestockCreatePayload) {
  return request<RestockResponse>(workspacePath("/restocks"), {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getRestock(restockId: number) {
  return request<RestockResponse>(workspacePath(`/restocks/${restockId}`));
}

export function getSales({
  dateFrom = "",
  dateTo = "",
  page = FIRST_PAGE,
  pageSize = DEFAULT_PAGE_SIZE,
}: {
  dateFrom?: string;
  dateTo?: string;
  page?: number;
  pageSize?: number;
} = {}) {
  return request<PaginatedResponse<SaleSummaryResponse>>(
    buildDateListPath(workspacePath("/sales"), dateFrom, dateTo, page, pageSize),
  );
}

export function createSale(payload: SaleCreatePayload) {
  return request<SaleResponse>(workspacePath("/sales"), {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getSale(saleId: number) {
  return request<SaleResponse>(workspacePath(`/sales/${saleId}`));
}

export function createProduct(payload: ProductCreatePayload) {
  return request<ProductResponse>(workspacePath("/products"), {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createProductAtomic(payload: ProductAtomicCreatePayload) {
  return request<ProductResponse>(workspacePath("/products/full"), {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getProduct(productId: number) {
  return request<ProductResponse>(workspacePath(`/products/${productId}`));
}

export function patchProduct(productId: number, payload: ProductUpdatePayload) {
  return request<ProductResponse>(workspacePath(`/products/${productId}`), {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function createProductSupplierLinks(
  productId: number,
  payload: ProductSupplierCreatePayload[],
) {
  return request<ProductSupplierResponse[]>(workspacePath(`/products/${productId}/links`), {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function patchProductSupplierLink(
  productId: number,
  linkId: number,
  payload: ProductSupplierUpdatePayload,
) {
  return request<ProductSupplierResponse>(
    workspacePath(`/products/${productId}/links/${linkId}`),
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
  );
}

export function deleteProductSupplierLink(productId: number, linkId: number) {
  return request<void>(workspacePath(`/products/${productId}/links/${linkId}`), {
    method: "DELETE",
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
    buildListPath(workspacePath("/tags"), search, page, pageSize),
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
    buildListPath(workspacePath("/companies"), search, page, pageSize),
  );
}

export function createCompany(payload: CompanyCreatePayload) {
  return request<CompanyResponse>(workspacePath("/companies"), {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getCompany(companyId: number) {
  return request<CompanyResponse>(workspacePath(`/companies/${companyId}`));
}

export function patchCompany(companyId: number, payload: CompanyUpdatePayload) {
  return request<CompanyResponse>(workspacePath(`/companies/${companyId}`), {
    method: "PATCH",
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
    buildListPath(workspacePath("/suppliers"), search, page, pageSize),
  );
}

export function createSupplier(payload: SupplierCreatePayload) {
  return request<SupplierResponse>(workspacePath("/suppliers"), {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getSupplier(supplierId: number) {
  return request<SupplierResponse>(workspacePath(`/suppliers/${supplierId}`));
}

export function patchSupplier(supplierId: number, payload: SupplierUpdatePayload) {
  return request<SupplierResponse>(workspacePath(`/suppliers/${supplierId}`), {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

function workspacePath(path: string) {
  return `/workspaces/${requireActiveWorkspaceId()}${path}`;
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

function buildDateListPath(
  basePath: string,
  dateFrom: string,
  dateTo: string,
  page: number,
  pageSize: number,
) {
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
