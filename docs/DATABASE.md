# Coregrid database

## Tables

***according to latest `init.sql` configuration***

### Companies

Stores supplier companies whose products are stored.

- `id` unique identifier given to the company/brand
- `IIN` unique identifier used in referring the company in documents or receipts
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
- `created_at` needed to identify the creation time of the product
