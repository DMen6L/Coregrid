# FastAPI

> [!NOTE]
> Check all table structures [here](/docs/DATABASE.md)

#### CRUD checklist

- [x] Create
- [x] Read
- [x] Update
- [x] Delete

## Current endpoints

Collection endpoints use pagination query parameters:

- `page`: page number, defaults to `1`, minimum `1`
- `page_size`: number of rows per page, defaults to `25`, maximum `100`

Paginated responses use:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 25,
  "pages": 0
}
```

### `GET /`

- Testing endpoint health

---

### Companies

#### `POST /companies`

- Creating new instance for table Companies

#### `PATCH /companies/{id}`

- Updating data of an instance for table Companies

#### `GET /companies`

- Returns a paginated list of companies

#### `GET /companies/{id}`

- Returns a single instance of Companies referenced by `id`

#### `DELETE /companies/{id}`

- Deletes a company and clears `company_id` from linked products

---

### Suppliers

#### `POST /suppliers`

- Creating new instance for table Suppliers
- `phone_number` accepts `8XXXXXXXXXX` or `+7XXXXXXXXXX`

#### `PATCH /suppliers/{id}`

- Updating data of an instance for table Suppliers
- `phone_number` accepts `8XXXXXXXXXX` or `+7XXXXXXXXXX`

#### `GET /suppliers`

- Returns a paginated list of suppliers

#### `GET /suppliers/{id}`

- Returns a single instance of Suppliers referenced by `id`

#### `DELETE /suppliers/{id}`

- Deletes a supplier and clears `supplier_id` from linked products

---

### Products

#### `POST /products`

- Creating new instance for table Products
- Requires `purchase_price`
- Accepts `margin_percent`, defaulting to `0`
- Accepts optional `sale_price`; when omitted, it defaults to calculated `floor_price`
- Accepts optional `quantity_unit`, defaulting to `шт`
- Accepts optional `low_stock_threshold`, defaulting to `5`
- Accepts optional `tags` as tag-name strings; names are trimmed, lowercased, deduplicated, and created if missing
- Rejects `sale_price` lower than calculated `floor_price`

#### `PATCH /products/{id}`

- Updating data of an instance for table Products
- Can update `purchase_price`, `margin_percent`, and `sale_price`
- Can update `quantity_unit`
- Can update `low_stock_threshold`
- Can update `tags`; omit `tags` to keep existing tags, send `tags: []` to clear them
- Rejects pricing changes that would make `sale_price` lower than calculated `floor_price`

#### `GET /products`

- Returns a paginated list of products
- Product responses include `purchase_price`, `margin_percent`, calculated `floor_price`, and `sale_price`
- Product responses include `quantity` and `quantity_unit`
- Product responses include calculated `stock_status`
- Product responses include `company_name` and `supplier_name` for display
- Product responses include reusable `tags`
- Supports `search` by product, company, supplier, or tag name
- Supports repeated exact `tags` filtering by tag name; products must match all selected tags
- Keeps legacy exact `tag` filtering by tag name or tag id
- Supports `stock` values: `all`, `available`, `low`, `empty`
- Supports `sort` values: `name`, `quantity`, `stock_status`, `inventory_value`, `company`, `supplier`, `created_at`
- Supports `order` values: `asc`, `desc`

#### `GET /products/summary`

- Returns global product totals for dashboard summary tiles
- Includes product count, total units, purchase-value inventory total, low-stock count, and out-of-stock count

#### `GET /products/{id}`

- Returns a single instance of Products referenced by `id`
- Product responses include `purchase_price`, `margin_percent`, calculated `floor_price`, and `sale_price`
- Product responses include `quantity` and `quantity_unit`
- Product responses include calculated `stock_status`
- Product responses include `company_name` and `supplier_name` for display
- Product responses include reusable `tags`

#### `DELETE /products/{id}`

- Deletes a product
- Returns conflict if the product has stock movement history

Product `stock_status` values:

- `out` when `quantity` is `0`
- `low` when `low_stock_threshold` is greater than `0` and quantity is within the threshold
- `available` otherwise

### Tags

#### `POST /tags`

- Creates a reusable product tag
- Stores tag names normalized to lowercase
- Returns conflict if the normalized tag already exists

#### `GET /tags`

- Returns a paginated list of tags
- Supports `search` by tag name

---

### Stock movements

#### `POST /stock-movements`

- Creates one stock movement with one or more product lines
- Updates product quantities in the same database transaction
- Rejects movements that would make product quantity negative

#### `GET /stock-movements`

- Returns a paginated list of stock movements with their lines
- Supports `order=oldest` by default and `order=latest` for recent activity panels

#### `GET /stock-movements/sales-summary`

- Returns actual sales totals for a calendar date range
- Requires `date_from=YYYY-MM-DD` and `date_to=YYYY-MM-DD`
- Counts explicit sales and their linked outgoing stock movements
- Returns revenue from sale line price snapshots, sold quantity, sold quantities grouped by unit label, and sale operation count
- Includes `daily_totals` with one row per selected calendar day, including zero-sale days, for dashboard charts
- Includes `best_sellers` with the top five products by actual revenue, unit-aware sold quantities, sale counts, and current stock status

#### `GET /stock-movements/{id}`

- Returns one stock movement with its lines

#### `GET /products/{product_id}/movements`

- Returns paginated stock movements connected to a product

---

### Sales

#### `POST /sales`

- Creates a commercial sale with one or more product lines
- Accepts positive line quantities as `quantity`
- Accepts positive actual sale prices as `unit_price`
- Creates a linked outgoing stock movement internally
- Stores each entered `unit_price` as the movement line price snapshot
- Updates product quantities in the same database transaction
- Rejects sales that would make product quantity negative

#### `GET /sales`

- Returns a paginated list of sales
- Supports `order=latest` by default and `order=oldest`
- Sale responses include linked stock movement id, revenue, note, created date, and movement line snapshots

#### `GET /sales/{id}`

- Returns one sale with linked movement line snapshots

## Running the server

```bash
# from backend/
source .venv/bin/activate
fastapi dev main.py

# or directly
uv run fastapi dev main.py
```

> [!NOTE]
> Check http://127.0.0.1:8000/docs after running dev server for tests

## Local frontend access

`main.py` allows local browser requests from `http://127.0.0.1:5173` and `http://localhost:5173` for the static frontend.
