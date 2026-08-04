# Coregrid Backend

FastAPI backend for Coregrid inventory, supplier, company, restock, sale, tag,
and dashboard workflows.

> [!NOTE]
> Table structures are documented in [`docs/DATABASE.md`](../docs/DATABASE.md).

## Current endpoints

Collection endpoints use pagination query parameters unless noted otherwise:

- `page`: page number, defaults to `1`, minimum `1`
- `page_size`: rows per page, defaults to `20`, maximum `100`

Paginated responses use:

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0,
  "total_pages": 0,
  "has_next": false,
  "has_previous": false
}
```

### Health

#### `GET /`

- Simple health/testing endpoint.

### Dashboard

#### `GET /summaries`

- Returns dashboard totals and rankings.
- Query parameters:
  - `days`: integer from `7` to `365`, default `7`
  - `best_sales_mode`: `quantity`, `revenue`, or `gross_profit`
- Response includes sales value, sales count, low-stock count, out-of-stock
  count, daily sales, top products, and top suppliers.

### Companies

#### `GET /companies`

- Returns a paginated company list.
- Supports `search` by company name.

#### `GET /companies/{id}`

- Returns one company by id.

#### `POST /companies`

- Creates a company.
- Requires `name`.
- Accepts nullable `iin`.

#### `PATCH /companies/{id}`

- Updates company fields.
- Empty update bodies are rejected.
- `iin` may be set to `null`.
- Duplicate `name` or duplicate non-null `iin` returns `409 Conflict`.

### Suppliers

#### `GET /suppliers`

- Returns a paginated supplier list.
- Supports `search` by supplier name.
- Summary rows include `product_links_count`.

#### `GET /suppliers/{id}`

- Returns one supplier by id.
- Includes linked product-supplier rows.

#### `POST /suppliers`

- Creates a supplier.
- Requires `name`.
- Requires `phone_number` in `8XXXXXXXXXX` or `+7XXXXXXXXXX` format.

#### `PATCH /suppliers/{id}`

- Updates supplier fields.
- Empty update bodies are rejected.
- `null` update values are rejected.
- Duplicate `name` or `phone_number` returns `409 Conflict`.

### Products

#### `GET /products`

- Returns a paginated product summary list.
- Supports `search` by product name or tag name.
- Product summaries include:
  - `company_name`
  - `tags`
  - `suppliers_count`
  - aggregated `total_quantity`
  - cheapest available supplier pricing fields
  - calculated `stock_status`

#### `GET /products/{id}`

- Returns one product by id.
- Includes company data, tags, and product-supplier links.

#### `POST /products`

- Creates a catalog product.
- Requires `name` and `company_id`.
- Accepts `quantity_unit`, defaulting to `шт`.
- Accepts `low_stock_threshold`, defaulting to `5`.
- Accepts `tags` as tag-name strings.
- Does not create supplier links; use `POST /products/{product_id}/links`.

#### `PATCH /products/{id}`

- Updates product metadata.
- Can update `name`, `company_id`, `quantity_unit`, `low_stock_threshold`, and
  `tags`.
- Omit `tags` to keep existing tags.
- Send `tags: []` to clear all tags.
- Empty update bodies are rejected.
- Duplicate `(name, company_id, quantity_unit)` returns `409 Conflict`.

#### `POST /products/{product_id}/links`

- Creates one or more product-supplier links for an existing product.
- Body is a non-empty list.
- Each item requires `supplier_id`, `purchase_price`, and optionally
  `margin_percent`, `sale_price`, and `quantity`.
- When `sale_price` is omitted, it defaults to the calculated floor price.
- Duplicate suppliers inside one request return `422`.
- Missing suppliers return `404`.
- Existing duplicate product-supplier links return `409`.

#### `PATCH /products/{product_id}/links/{link_id}`

- Updates one product-supplier link.
- Can update `supplier_id`, `purchase_price`, `margin_percent`, `sale_price`,
  and `quantity`.
- Empty update bodies are rejected.
- `null` update values are rejected.
- Missing product, link, or supplier references return `404`.
- Duplicate `(product_id, supplier_id)` returns `409 Conflict`.
- `sale_price` below calculated floor price returns `422`.

#### `DELETE /products/{product_id}/links/{link_id}`

- Deletes a product-supplier link.
- Returns `404` when the product or link is missing, or when the link belongs to
  a different product.
- Returns `409 Conflict` when the link has stock or restock/sale history.
- Returns `204 No Content` on successful deletion.

Product `stock_status` values:

- `out` when total quantity is `0`
- `low` when total quantity is at or below the product low-stock threshold
- `available` otherwise

### Tags

#### `GET /tags`

- Returns a paginated list of tags ordered by usage count, then name.
- Supports `search` by tag name.
- Returns only tags attached to at least one product.

#### `DELETE /tags/{id}`

- Deletes a tag.
- Product-tag join rows are removed by database cascade.
- Returns `404` when the tag does not exist.

### Restocks

#### `GET /restocks`

- Returns a paginated restock summary list.
- Supports date filters:
  - `from=YYYY-MM-DD`
  - `to=YYYY-MM-DD`
- Ordered newest first.

#### `GET /restocks/{restock_id}`

- Returns one restock with line details.

#### `POST /restocks`

- Creates one restock with one or more lines.
- Each line references `product_supplier_id`.
- Increases `product_suppliers.quantity` in the same transaction.
- Optional `unit_cost_snapshot` defaults to the link purchase price.
- Duplicate product-supplier links in one restock are rejected.

### Sales

#### `GET /sales`

- Returns a paginated sale summary list.
- Supports date filters:
  - `from=YYYY-MM-DD`
  - `to=YYYY-MM-DD`
- Ordered newest first.

#### `GET /sales/{sale_id}`

- Returns one sale with line details.

#### `POST /sales`

- Creates one sale with one or more lines.
- Each line references `product_supplier_id`.
- Decreases `product_suppliers.quantity` in the same transaction.
- Rejects a sale with `409 Conflict` when requested quantity exceeds available
  stock.
- Snapshots purchase price, sale price, and quantity unit.

## Running the server

```bash
# from backend/
source .venv/bin/activate
fastapi dev main.py

# or directly
uv run fastapi dev main.py
```

> [!NOTE]
> Check `http://127.0.0.1:8000/docs` after running the dev server.

## Local frontend access

`main.py` allows local browser requests from `http://127.0.0.1:5173` and
`http://localhost:5173` for the Vue frontend.

If the frontend runs on another local port, update CORS before using the browser
against that port.
