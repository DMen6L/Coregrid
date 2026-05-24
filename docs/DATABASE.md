# Coregrid database

## Tables

***according to latest `init.sql` configuration***

### Products

Stores products assigning them unique identifiers and created for easier access of data on those products and for easy modification of the data.

- `id` unique identifier of each product
- `name` stores the names of each of the products
- `price` stores the prices of the products, meant to be flexible due to different reasons of price changes
- `created_at` needed to identify the creation time of the product
