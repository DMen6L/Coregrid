# Stock movements design

This document describes the stock movement model for Coregrid.

The key rule is:

- `products.quantity` stores the current stock state.
- stock movement tables store the history of how that quantity changed.

This design is implemented in the backend and exposed in the static frontend.
The frontend can create stock movements, show movement history, show recent
dashboard movements, and use sales summaries for dashboard reporting.

Sales are now explicit commercial records. A sale creates a linked outgoing
stock movement internally, but a generic outgoing stock movement is not counted
as a sale.

## Purpose

The current product table can answer:

> How many units are in stock right now?

It cannot answer:

> Why is this the current amount?

Stock movements add that history. They should support:

- incoming stock
- outgoing stock for non-sale write-offs or removals
- manual stock corrections
- one stock event that changes multiple products
- product-specific movement history
- dashboard and reporting screens
- explicit sales linked to outgoing stock movement history

## Table model

Use two tables:

```text
stock_movements
stock_movement_lines
```

`stock_movements` is the transaction header. It stores information shared by
the whole stock event.

`stock_movement_lines` stores the per-product changes inside that event.

This avoids duplicating the same note, date, and movement type for every product
when one real-world transaction changes multiple products.

## `stock_movements`

Columns:

| Column | Type | Rules |
| --- | --- | --- |
| `id` | integer | primary key |
| `movement_type` | `String(20)` | must be `in`, `out`, or `adjustment` |
| `note` | `String(500)` or text | nullable |
| `created_at` | timestamp | server default `now()` |

Database constraint:

```text
movement_type in ('in', 'out', 'adjustment')
```

Constraint name:

```text
ck_stock_movements_type
```

Do not use PostgreSQL enum for the first version. `String` plus
`CheckConstraint` is easier to evolve while the project is still changing.

## `stock_movement_lines`

Columns:

| Column | Type | Rules |
| --- | --- | --- |
| `id` | integer | primary key |
| `movement_id` | integer | foreign key to `stock_movements.id` |
| `product_id` | integer | foreign key to `products.id` |
| `quantity_delta` | integer | cannot be `0` |
| `quantity_before` | integer | must be `>= 0` |
| `quantity_after` | integer | must be `>= 0` |
| `unit_price_snapshot` | integer | nullable, must be `> 0` when present |
| `quantity_unit_snapshot` | string | required, copied from the product unit |

Database constraints:

```text
quantity_delta != 0
quantity_before >= 0
quantity_after >= 0
unit_price_snapshot is null or unit_price_snapshot > 0
char_length(quantity_unit_snapshot) > 0
```

Constraint names:

```text
ck_stock_movement_lines_quantity_delta
ck_stock_movement_lines_quantity_before
ck_stock_movement_lines_quantity_after
ck_stock_movement_lines_unit_price_snapshot
ck_stock_movement_lines_quantity_unit_snapshot_not_empty
```

Foreign key behavior:

```text
stock_movement_lines.movement_id -> stock_movements.id ON DELETE CASCADE
stock_movement_lines.product_id -> products.id with no cascade
```

Product deletion should become stricter once movement history exists. Long term,
Coregrid should probably use archive or soft delete for products with movement
history.

## Movement types

Use controlled values:

```text
in
out
adjustment
```

Meaning:

- `in`: stock increased because products were received
- `out`: stock decreased because products were written off, used, removed, or shipped
- `adjustment`: stock changed because of recount or manual correction

Commercial sales should use the sales API. The sales API creates an outgoing
stock movement internally, so inventory history stays complete without treating
every outgoing movement as revenue.

The frontend may translate these labels for users, but the API/database values
should stay stable and English-like.

## Quantity rules

`quantity_delta` stores the change:

```text
+10 means stock increased by 10
-3 means stock decreased by 3
```

The backend must calculate:

```text
quantity_before = current product.quantity
quantity_after = quantity_before + quantity_delta
```

The backend must reject a movement line if:

```text
quantity_after < 0
```

The request schema also enforces:

```text
movement_type = in  -> quantity_delta must be positive
movement_type = out -> quantity_delta must be negative
movement_type = adjustment -> quantity_delta can be positive or negative
```

Each product can appear only once in a single movement request. If the same
product needs a larger change, the client should send one combined
`quantity_delta`.

The backend should update `products.quantity`, create `stock_movements`, and
create `stock_movement_lines` in one database transaction.

## Price snapshot

`unit_price_snapshot` should copy the current `Product.sale_price` when the
movement is created.

For explicit sales, `POST /sales` accepts an actual positive `unit_price` on
each sale line. That entered price is copied into `unit_price_snapshot`, so
discounted sales affect revenue and dashboard summaries correctly.

Reason:

- product sale price can change later
- old movement history should keep the price context from the moment of change
- current product prices are already integers, so the snapshot should also be an
  integer for the first version

If decimal currency is needed later, both product price fields and
`unit_price_snapshot` can move toward a numeric database type.

## Quantity unit snapshot

`quantity_unit_snapshot` should copy the current `Product.quantity_unit` when
the movement is created.

Reason:

- product quantity units can change later
- old movement history should still answer what the recorded quantity meant
- sales summaries can group sold quantities by unit label without converting
  unlike units

## API shape

Endpoints:

```http
POST /stock-movements
GET /stock-movements?page=1&page_size=25
GET /stock-movements/sales-summary?date_from=2026-07-05&date_to=2026-07-07
GET /stock-movements/{id}
GET /products/{product_id}/movements?page=1&page_size=25
POST /sales
GET /sales?page=1&page_size=25
GET /sales/{id}
```

The client sends intent only. It should not send calculated fields.

Create movement request:

```json
{
  "movement_type": "in",
  "note": "Поставка от поставщика",
  "lines": [
    {
      "product_id": 1,
      "quantity_delta": 10
    },
    {
      "product_id": 2,
      "quantity_delta": 5
    }
  ]
}
```

Create movement response:

```json
{
  "id": 1,
  "movement_type": "in",
  "note": "Поставка от поставщика",
  "created_at": "2026-07-03T14:30:00",
  "lines": [
    {
      "id": 1,
      "product_id": 1,
      "quantity_delta": 10,
      "quantity_before": 0,
      "quantity_after": 10,
      "unit_price_snapshot": 500,
      "quantity_unit_snapshot": "шт"
    },
    {
      "id": 2,
      "product_id": 2,
      "quantity_delta": 5,
      "quantity_before": 7,
      "quantity_after": 12,
      "unit_price_snapshot": 1200,
      "quantity_unit_snapshot": "м"
    }
  ]
}
```

Movement collection responses are paginated:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 25,
  "pages": 0
}
```

Sales summary responses include:

- aggregate revenue for the selected calendar range
- total sold quantity
- sold quantities grouped by `quantity_unit_snapshot`
- sale operation count
- `daily_totals` rows for every date in the range
- `best_sellers` with up to five products ranked by actual revenue

Dates without outgoing sales return zero values so dashboard charts can draw a
continuous trend.

Each `best_sellers` item includes the current product name, revenue, distinct
sale operation count, sold quantities grouped by their historical unit
snapshots, and current quantity, unit, and stock status. Revenue ties are
ordered by product ID. Generic outgoing movements do not affect the ranking.

Sales summary responses count explicit `sales` rows and their linked outgoing
stock movements. Generic outgoing stock movements are inventory write-offs and
do not affect sales totals.

## Sales workflow

`POST /sales` accepts positive product quantities and positive actual
`unit_price` values. The backend creates:

- one `sales` row
- one linked `stock_movements` row with `movement_type = "out"`
- one or more `stock_movement_lines` with negative `quantity_delta`
- price snapshots from the entered sale line prices

The sale response exposes the linked `stock_movement_id`, calculated revenue,
and the movement line snapshots. Payments, customers, returns, and receipt
numbers are left for later versions.

## Pydantic schema direction

Schemas are kept in the existing `backend/app/schemas.py` file.

Expected create schemas:

```text
StockMovementLineCreate
StockMovementCreate
```

Expected response schemas:

```text
StockMovementLineResponse
StockMovementResponse
SaleLineCreate
SaleCreate
SaleResponse
StockMovementSalesSummaryUnitResponse
StockMovementSalesSummaryDailyResponse
StockMovementSalesSummaryBestSellerResponse
StockMovementSalesSummaryResponse
```

`StockMovementCreate` should use a controlled Python type for movement type,
such as:

```text
Literal["in", "out", "adjustment"]
```

`lines` should require at least one item.

## SQLAlchemy model direction

Models are kept in the existing `backend/app/models.py` file.

Expected models:

```text
StockMovement
StockMovementLine
```

Expected relationships:

```text
StockMovement.lines
StockMovementLine.movement
StockMovementLine.product
Product.stock_movement_lines
```

## Product quantity editing

Direct product quantity edits should still be reconsidered.

Preferred future rule:

- `PATCH /products/{id}` can update product metadata such as name, pricing,
  company, and supplier.
- stock movement endpoints should be the main way to change quantity.

This prevents product quantity from changing without history.

Current compatibility note:

- `PATCH /products/{id}` still accepts `quantity` so the existing frontend and
  tests keep working.
- Stock movements are now the preferred API for stock changes.

## Test plan

Backend endpoint tests should cover:

- creating an incoming movement increases product quantity
- creating an outgoing movement decreases product quantity
- creating an adjustment can increase quantity
- creating an adjustment can decrease quantity
- one movement with multiple lines updates all related products
- movement that would make quantity negative returns an error
- movement with empty `lines` is rejected
- movement with `quantity_delta = 0` is rejected
- movement with an invalid `movement_type` is rejected
- movement with missing product id returns an error
- global movement history can be fetched
- one movement can be fetched by id
- product-specific movement history can be fetched
- movement lines snapshot the product quantity unit
- creating a sale decreases product quantity and creates a linked outgoing movement
- generic outgoing movements do not create sale records
- sales summary returns aggregate totals
- sales summary ignores generic outgoing movements
- sales summary returns sold quantities grouped by unit
- sales summary returns daily totals, including zero-sale days

## Assumptions

- No user/auth tracking in the first version.
- No supplier/order document tracking in the first version.
- No decimal money handling in the first version.
- No payments, customers, discount reasons/approvals, returns, or receipts in
  the first sales version.
- The static frontend has movement UI, but direct product quantity editing is
  still allowed for compatibility.
- Existing models and schemas stay in single files until they become too large.
