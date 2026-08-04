# Coregrid database

## Tables

***All table structures are defined in `backend/app/models.py`***

### Companies

Stores supplier companies whose products are stored.

- `id` unique identifier given to the company/brand
- `IIN` unique identifier used in referring to the company in documents or receipts
- `name` name of the referred company/brand

### Suppliers

Stores identities and contact information of the people that provide the listed products.

- `id` unique identifier given to each individual or contact
- `name` name of the individual used to refer them
- `phone_number` contact information in Kazakh local `8XXXXXXXXXX` or international `+7XXXXXXXXXX` format

### Products

Stores catalog product identities. Supplier-specific stock and pricing lives in
`product_suppliers`.

- `id` unique identifier of each product
- `company_id` required reference to the company/brand connected to the product
- `name` stores the names of each of the products
- `created_at` needed to identify the creation time of the product
- `quantity_unit` stores the short unit label used for this product, default set
  to `шт`
- `low_stock_threshold` stores the warning threshold for aggregated stock,
  default set to 5

### Product suppliers

Stores the many-to-many relationship between products and suppliers. This is the
current inventory and pricing row used by restocks and sales.

- `id` unique identifier of each product-supplier link
- `product_id` reference to the catalog product
- `supplier_id` reference to the supplier
- `purchase_price` stores the price paid when buying this product from this supplier
- `margin_percent` stores the desired markup percentage over `purchase_price`
- `sale_price` stores the final editable selling price shown to sellers
- `quantity` stores the currently stored amount for this product-supplier link

`(product_id, supplier_id)` is unique, so one supplier has only one active link
for a given product.

`floor_price` is calculated by the API and is not stored as a column:

```text
floor_price = ceil(purchase_price * (1 + margin_percent / 100))
```

`sale_price` must be equal to or higher than `floor_price`. This lets sellers
round prices up to cleaner values while preserving the minimum margin.

Stock status is calculated by the API and is not stored as a column:

- `out` when `quantity` is `0`
- `low` when quantity is above `0` and at or below the product's
  `low_stock_threshold`
- `available` otherwise

Product list summaries calculate status from aggregated supplier-link quantity.

### Tags

Stores reusable product labels used for filtering and search.

- `id` unique identifier of each tag
- `name` normalized lowercase tag name, unique across all tags
- `created_at` time when the tag was created

### Product tags

Stores the many-to-many relationship between products and tags.

- `product_id` reference to the tagged product
- `tag_id` reference to the reusable tag
- `(product_id, tag_id)` is unique through the composite primary key

Deleting a product removes only rows from `product_tags`; reusable tag records
remain available for other products.

Deleting a tag removes its `product_tags` rows through database cascade.

### Restocks

Stores incoming stock transaction headers.

- `id` unique identifier of each restock
- `note` optional text note for the restock
- `created_at` time when the restock was created

### Restock lines

Stores the product-supplier level changes inside a restock.

- `id` unique identifier of each restock line
- `restock_id` reference to the restock header
- `product_supplier_id` reference to the product-supplier link that changed
- `restock_quantity` positive quantity added to stock
- `unit_cost_snapshot` optional copied or entered purchase cost
- `quantity_unit_snapshot` product quantity unit copied when created

### Sales

Stores commercial sale records.

- `id` unique identifier of each sale
- `note` optional text note for the sale
- `created_at` time when the sale was created

### Sale lines

Stores the product-supplier level changes inside a sale.

- `id` unique identifier of each sale line
- `sale_id` reference to the sale header
- `product_supplier_id` reference to the product-supplier link that changed
- `sale_quantity` positive quantity removed from stock
- `unit_cost_snapshot` purchase price copied when the sale was created
- `unit_sale_price_snapshot` sale price copied when the sale was created
- `quantity_unit_snapshot` product quantity unit copied when created

## Connection and working with Coregrid database

```bash
# connect
psql -U postgres -d coregrid

# list the tables
\dt

# check tables individually
# table_name is to be substituted with proper name of the table
SELECT * FROM table_name;

# exit
\q
```
