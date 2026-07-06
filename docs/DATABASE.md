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

Stores products assigning them unique identifiers and created for easier access of data on those products and for easy modification of the data.

- `id` unique identifier of each product
- `company_id` optional reference to the company/brand connected to the product
- `supplier_id` optional reference to the supplier connected to the product
- `name` stores the names of each of the products
- `purchase_price` stores the price paid when buying the product
- `margin_percent` stores the desired markup percentage over `purchase_price`
- `sale_price` stores the final editable selling price shown to sellers
- `quantity` stores the amount of currently stored products, default set to 0
- `quantity_unit` stores the short unit label for `quantity`, default set to `шт`
- `low_stock_threshold` stores the per-product low-stock warning threshold, default set to 5
- `created_at` needed to identify the creation time of the product

Product `floor_price` is calculated by the API and is not stored as a column:

```text
floor_price = ceil(purchase_price * (1 + margin_percent / 100))
```

`sale_price` must be equal to or higher than `floor_price`. This lets sellers
round prices up to cleaner values while preserving the minimum margin.

Product stock status is calculated by the API and is not stored as a column:

- `out` when `quantity` is `0`
- `low` when `low_stock_threshold > 0` and `quantity` is within the threshold
- `available` otherwise

`low_stock_threshold = 0` disables low-stock warnings for that product.

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

### Stock movements

Stores the header of each stock change transaction.

- `id` unique identifier of each stock movement
- `movement_type` controlled value of `in`, `out`, or `adjustment`
- `note` optional text note for the stock movement
- `created_at` time when the stock movement was created

### Stock movement lines

Stores the product-level changes inside a stock movement.

- `id` unique identifier of each movement line
- `movement_id` reference to the stock movement header
- `product_id` reference to the product that changed
- `quantity_delta` amount of stock change, positive or negative
- `quantity_before` product quantity before the movement line
- `quantity_after` product quantity after the movement line
- `unit_price_snapshot` product sale price copied when the movement was created
- `quantity_unit_snapshot` product quantity unit copied when the movement was created

See [stock movements design](STOCK_MOVEMENTS.md) for the detailed API and
business rules.

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
