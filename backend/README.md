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
- Accepts optional `low_stock_threshold`, defaulting to `5`
- Rejects `sale_price` lower than calculated `floor_price`

#### `PATCH /products/{id}`

- Updating data of an instance for table Products
- Can update `purchase_price`, `margin_percent`, and `sale_price`
- Can update `low_stock_threshold`
- Rejects pricing changes that would make `sale_price` lower than calculated `floor_price`

#### `GET /products`

- Returns a paginated list of products
- Product responses include `purchase_price`, `margin_percent`, calculated `floor_price`, and `sale_price`
- Product responses include calculated `stock_status`
- Product responses include `company_name` and `supplier_name` for display
- Supports `search` by product, company, or supplier name
- Supports `stock` values: `all`, `available`, `low`, `empty`

#### `GET /products/summary`

- Returns global product totals for dashboard summary tiles

#### `GET /products/{id}`

- Returns a single instance of Products referenced by `id`
- Product responses include `purchase_price`, `margin_percent`, calculated `floor_price`, and `sale_price`
- Product responses include calculated `stock_status`
- Product responses include `company_name` and `supplier_name` for display

#### `DELETE /products/{id}`

- Deletes a product
- Returns conflict if the product has stock movement history

Product `stock_status` values:

- `out` when `quantity` is `0`
- `low` when `low_stock_threshold` is greater than `0` and quantity is within the threshold
- `available` otherwise

---

### Stock movements

#### `POST /stock-movements`

- Creates one stock movement with one or more product lines
- Updates product quantities in the same database transaction
- Rejects movements that would make product quantity negative

#### `GET /stock-movements`

- Returns a paginated list of stock movements with their lines

#### `GET /stock-movements/{id}`

- Returns one stock movement with its lines

#### `GET /products/{product_id}/movements`

- Returns paginated stock movements connected to a product

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
