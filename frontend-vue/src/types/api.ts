export type BestSalesMode = "quantity" | "revenue" | "gross_profit";
export type StockStatus = "available" | "low" | "out";

export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface DailySalesResponse {
  date: string;
  sales_value: number;
}

export interface TopProduct {
  product_id: number;
  product_name: string;
  metric: number;
}

export interface TopSupplier {
  supplier_id: number;
  supplier_name: string;
  supplied_products: number;
}

export interface SummariesResponse {
  dashboard_sales_value: number;
  dashboard_sales_count: number;
  low_stock: number;
  out_of_stock: number;
  latest_sales: DailySalesResponse[];
  top_products: TopProduct[];
  top_suppliers: TopSupplier[];
}

export interface ProductSummaryResponse {
  id: number;
  name: string;
  created_at: string;
  quantity_unit: string;
  low_stock_threshold: number;
  company_name: string;
  tags: string[];
  suppliers_count: number;
  total_quantity: number;
  min_purchase_price: number | null;
  margin_percent: number | null;
  min_sale_price: number | null;
  stock_status: StockStatus;
}

export interface RestockSummaryResponse {
  id: number;
  note: string | null;
  created_at: string;
  costs: number;
  lines_count: number;
}

export interface SaleSummaryResponse {
  id: number;
  note: string | null;
  created_at: string;
  revenue: number;
  lines_count: number;
}

export interface RestockLineCreatePayload {
  product_supplier_id: number;
  restock_quantity: number;
  unit_cost_snapshot?: number;
}

export interface RestockCreatePayload {
  note?: string | null;
  lines: RestockLineCreatePayload[];
}

export interface RestockLineResponse {
  id: number;
  product_supplier_id: number;
  product_id: number;
  product_name: string;
  supplier_id: number;
  supplier_name: string | null;
  restock_quantity: number;
  unit_cost_snapshot: number;
  quantity_unit_snapshot: string;
}

export interface RestockResponse {
  id: number;
  note: string | null;
  created_at: string;
  lines: RestockLineResponse[];
}

export interface SaleLineCreatePayload {
  product_supplier_id: number;
  sale_quantity: number;
}

export interface SaleCreatePayload {
  note?: string | null;
  lines: SaleLineCreatePayload[];
}

export interface SaleLineResponse {
  id: number;
  product_supplier_id: number;
  product_id: number;
  product_name: string;
  supplier_id: number;
  supplier_name: string;
  sale_quantity: number;
  unit_cost_snapshot: number;
  unit_sale_price_snapshot: number;
  quantity_unit_snapshot: string;
}

export interface SaleResponse {
  id: number;
  note: string | null;
  created_at: string;
  lines: SaleLineResponse[];
}

export interface TagResponse {
  id: number;
  name: string;
}

export interface TagSummaryResponse {
  id: number;
  name: string;
  usage_count: number;
}

export interface CompanyResponse {
  id: number;
  name: string;
  iin: string | null;
}

export interface CompanyCreatePayload {
  name: string;
  iin?: string | null;
}

export interface CompanyUpdatePayload {
  name?: string;
  iin?: string | null;
}

export interface SupplierSummaryResponse {
  id: number;
  name: string;
  phone_number: string;
  product_links_count: number;
}

export interface SupplierCreatePayload {
  name: string;
  phone_number: string;
}

export interface SupplierUpdatePayload {
  name?: string;
  phone_number?: string;
}

export interface ProductSupplierCreatePayload {
  supplier_id: number;
  purchase_price: number;
  margin_percent: number;
  sale_price?: number | null;
  quantity: number;
}

export interface ProductSupplierUpdatePayload {
  supplier_id?: number;
  purchase_price?: number;
  margin_percent?: number;
  sale_price?: number;
  quantity?: number;
}

export interface ProductSupplierResponse {
  id: number;
  product_id: number;
  supplier_id: number;
  product_name: string | null;
  supplier_name: string | null;
  purchase_price: number;
  margin_percent: number;
  floor_price: number;
  sale_price: number;
  quantity: number;
  stock_status: StockStatus;
}

export interface SupplierResponse {
  id: number;
  name: string;
  phone_number: string;
  product_links: ProductSupplierResponse[];
}

export interface ProductCreatePayload {
  name: string;
  company_id: number;
  tags: string[];
  quantity_unit: string;
  low_stock_threshold: number;
}

export interface ProductUpdatePayload {
  name?: string;
  company_id?: number;
  tags?: string[];
  quantity_unit?: string;
  low_stock_threshold?: number;
}

export interface ProductResponse {
  id: number;
  name: string;
  created_at: string;
  company_id: number;
  company_name: string;
  quantity_unit: string;
  low_stock_threshold: number;
  tags: TagResponse[];
  supplier_links: ProductSupplierResponse[];
}
