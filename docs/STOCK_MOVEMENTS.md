# Stock movement design

This document describes how Coregrid currently records inventory changes.

The key rule is:

- `product_suppliers.quantity` stores current stock for a specific
  product-supplier link.
- `restocks` and `sales` store history for stock increases and decreases.
- `audit_logs` stores who created the stock movement and summarizes the event
  for workspace history.

This design is implemented in the backend and exposed in the Vue frontend.

## Purpose

The product table answers:

> What catalog item is this?

The product-supplier link answers:

> How much stock do we have from this supplier, and at what price?

Restocks and sales answer:

> Why did this stock amount change?

This keeps catalog identity, supplier-specific inventory, and historical events
separate.

## Current movement types

Coregrid currently has two explicit movement workflows:

- `restocks`: incoming stock received from suppliers
- `sales`: outgoing stock sold to customers

Manual write-offs and inventory corrections should become a separate stock
adjustment workflow later.

## Table model

Current stock is stored on:

```text
product_suppliers
```

Historical incoming stock is stored in:

```text
restocks
restock_lines
```

Historical outgoing sales are stored in:

```text
sales
sale_lines
```

`Restock.lines` and `Sale.lines` are delete-orphan relationships from the parent
transaction header. Product-supplier links are not deleted by historical line
records.

## Product-supplier stock

`product_suppliers.quantity` is the current stock amount for one product from
one supplier.

`products.quantity_unit` stores the unit label for the product, such as `шт`.
The unit is copied into historical restock and sale lines as
`quantity_unit_snapshot`.

Stock status is calculated:

- `out` when the product-supplier quantity is `0`
- `low` when quantity is above `0` and at or below the product's
  `low_stock_threshold`
- `available` otherwise

Product list summaries aggregate all supplier-link quantities into
`total_quantity`.

## Restocks

`POST /workspaces/{workspace_id}/restocks` creates one restock header and one or
more restock lines in a single transaction.

Request shape:

```json
{
  "note": "Поставка",
  "lines": [
    {
      "product_supplier_id": 1,
      "restock_quantity": 10,
      "unit_cost_snapshot": 500
    }
  ]
}
```

Rules:

- `lines` must contain at least one item.
- `product_supplier_id` must reference an existing product-supplier link.
- `restock_quantity` must be positive.
- each product-supplier link can appear only once in one restock.
- `unit_cost_snapshot` is optional; when omitted, the current link purchase
  price is copied.
- creating a restock increases `product_suppliers.quantity`.
- the backend locks affected product-supplier rows while applying the change.
- the current user must be a member of the workspace and have
  `stock_movement.create`.
- an audit log row is recorded for the created restock.

Response shape:

```json
{
  "id": 1,
  "note": "Поставка",
  "created_at": "2026-07-03T14:30:00",
  "lines": [
    {
      "id": 1,
      "product_supplier_id": 1,
      "product_id": 1,
      "product_name": "Товар",
      "supplier_id": 2,
      "supplier_name": "Поставщик",
      "restock_quantity": 10,
      "unit_cost_snapshot": 500,
      "quantity_unit_snapshot": "шт"
    }
  ]
}
```

## Sales

`POST /workspaces/{workspace_id}/sales` creates one sale header and one or more
sale lines in a single transaction.

Request shape:

```json
{
  "note": "Продажа",
  "lines": [
    {
      "product_supplier_id": 1,
      "sale_quantity": 2
    }
  ]
}
```

Rules:

- `lines` must contain at least one item.
- `product_supplier_id` must reference an existing product-supplier link.
- `sale_quantity` must be positive.
- each product-supplier link can appear only once in one sale.
- creating a sale decreases `product_suppliers.quantity`.
- a sale is rejected with `409 Conflict` if requested quantity exceeds available
  stock.
- sale lines snapshot current purchase price, sale price, and quantity unit.
- the backend locks affected product-supplier rows while applying the change.
- the current user must be a member of the workspace and have
  `stock_movement.create`.
- an audit log row is recorded for the created sale.

Response shape:

```json
{
  "id": 1,
  "note": "Продажа",
  "created_at": "2026-07-03T14:30:00",
  "lines": [
    {
      "id": 1,
      "product_supplier_id": 1,
      "product_id": 1,
      "product_name": "Товар",
      "supplier_id": 2,
      "supplier_name": "Поставщик",
      "sale_quantity": 2,
      "unit_cost_snapshot": 500,
      "unit_sale_price_snapshot": 700,
      "quantity_unit_snapshot": "шт"
    }
  ]
}
```

## List and detail endpoints

Restocks:

```http
GET /workspaces/{workspace_id}/restocks?page=1&page_size=20
GET /workspaces/{workspace_id}/restocks?from=2026-07-01&to=2026-07-31&page=1&page_size=20
GET /workspaces/{workspace_id}/restocks/{restock_id}
POST /workspaces/{workspace_id}/restocks
```

Sales:

```http
GET /workspaces/{workspace_id}/sales?page=1&page_size=20
GET /workspaces/{workspace_id}/sales?from=2026-07-01&to=2026-07-31&page=1&page_size=20
GET /workspaces/{workspace_id}/sales/{sale_id}
POST /workspaces/{workspace_id}/sales
```

List responses are paginated:

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

## Dashboard summaries

The dashboard uses:

```http
GET /workspaces/{workspace_id}/summaries?days=7&best_sales_mode=quantity
```

`best_sales_mode` can be:

- `quantity`
- `revenue`
- `gross_profit`

The response includes:

- total dashboard sales value
- number of sales
- low-stock count
- out-of-stock count
- daily sales rows
- top products
- top suppliers

## Product quantity editing

Direct catalog product updates should not be used as the main stock-changing
workflow.

Current rule:

- product metadata lives on `products`
- current stock and supplier pricing live on `product_suppliers`
- restocks and sales should be the main way to change quantity

`PATCH /workspaces/{workspace_id}/products/{id}` updates product metadata such
as name, company, tags, quantity unit, and low-stock threshold.

`PATCH /workspaces/{workspace_id}/products/{product_id}/links/{link_id}` can
update supplier-link stock and pricing directly. For stricter inventory history
later, quantity changes should move into dedicated restock, sale, or adjustment
workflows.

## Future stock adjustments

Coregrid should add a stock adjustment workflow for non-sale inventory changes:

- damaged stock
- expired stock
- lost stock
- recount correction
- manual correction

A future adjustment should snapshot before/after quantity and require a reason.

## Test plan

Backend endpoint tests should cover:

- creating a restock increases product-supplier quantity
- creating a sale decreases product-supplier quantity
- creating a sale rejects quantities above available stock
- one restock with multiple lines updates all related links
- one sale with multiple lines updates all related links
- duplicate product-supplier links in one restock are rejected
- duplicate product-supplier links in one sale are rejected
- missing product-supplier links return `404`
- restock and sale lines snapshot quantity unit
- restock lines snapshot purchase cost
- sale lines snapshot purchase cost and sale price
- restock and sale lists support `from`, `to`, `page`, and `page_size`
- one restock can be fetched by id
- one sale can be fetched by id
- dashboard summaries include daily sales, top products, and top suppliers
