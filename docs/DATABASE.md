# Coregrid database

## Tables

***according to latest init.sql configuration***

### Products

Stores products assigning them unique identifiers and created for easier access of data on those products and for easy modification of the data.

- *id* is set to SERIAL and is Primary Key identifier of the product
- *name* for now is set as VARCHAR(255) NOT NULL
- *price* used floating point numbers for current tests NUMERIC(10, 2)
- *created_at* needed to identify the creation time of the product with default TIMESTAMP DEFAULT NOW()
