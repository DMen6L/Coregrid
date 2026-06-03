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
- `phone_number` contact information(for simplicity only phone number is added currently)

### Products

Stores products assigning them unique identifiers and created for easier access of data on those products and for easy modification of the data.

- `id` unique identifier of each product
- `name` stores the names of each of the products
- `price` stores the prices of the products, meant to be flexible due to different reasons of price changes
- `quantity` stores the amount of currently stored products, default set to 0
- `created_at` needed to identify the creation time of the product

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
