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

export interface SupplierSummaryResponse {
  id: number;
  name: string;
  phone_number: string;
  product_links_count: number;
}

export interface ProductCreatePayload {
  name: string;
  company_id: number;
  tags: string[];
  quantity_unit: string;
  low_stock_threshold: number;
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
}
