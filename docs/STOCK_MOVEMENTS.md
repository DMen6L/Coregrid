# Stock movements design

This document describes the stock movement model for Coregrid.

The key rule is:

- `products.quantity` stores the current stock state.
- stock movement tables store the history of how that quantity changed.

This design is implemented in the backend. Frontend controls for stock
movements are still a follow-up task.

## Purpose

The current product table can answer:

> How many units are in stock right now?

It cannot answer:

> Why is this the current amount?

Stock movements add that history. They should support:

- incoming stock
- outgoing stock
- manual stock corrections
- one stock event that changes multiple products
- product-specific movement history
- future dashboard and reporting screens

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

Database constraints:

```text
quantity_delta != 0
quantity_before >= 0
quantity_after >= 0
unit_price_snapshot is null or unit_price_snapshot > 0
```

Constraint names:

```text
ck_stock_movement_lines_quantity_delta
ck_stock_movement_lines_quantity_before
ck_stock_movement_lines_quantity_after
ck_stock_movement_lines_unit_price_snapshot
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
- `out`: stock decreased because products were sold, used, removed, or shipped
- `adjustment`: stock changed because of recount or manual correction

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

Reason:

- product sale price can change later
- old movement history should keep the price context from the moment of change
- current product prices are already integers, so the snapshot should also be an
  integer for the first version

If decimal currency is needed later, both product price fields and
`unit_price_snapshot` can move toward a numeric database type.

## API shape

Endpoints:

```http
POST /stock-movements
GET /stock-movements?page=1&page_size=25
GET /stock-movements/{id}
GET /products/{product_id}/movements?page=1&page_size=25
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
      "unit_price_snapshot": 500
    },
    {
      "id": 2,
      "product_id": 2,
      "quantity_delta": 5,
      "quantity_before": 7,
      "quantity_after": 12,
      "unit_price_snapshot": 1200
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

## Assumptions

- No user/auth tracking in the first version.
- No supplier/order document tracking in the first version.
- No decimal money handling in the first version.
- No frontend movement UI until backend behavior is stable.
- Existing models and schemas stay in single files until they become too large.
