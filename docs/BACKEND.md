# Coregrid Backend

## Libraries

- SQLAlchemy
- Alembic
- FastAPI

## App

### `config.py`

Holds configurations essential for the work of other modules.

### `db.py`

Initializes and holds essentials for the transactions with the database:
- engine
- Base

### `models.py`

Holds actual table models that the database has, essential for both initialization and transactions.

- Company
- Supplier
- Product

> [!NOTE]
> for the actual database tables refer to [this](/docs/DATABASE.md)

### Alembic

Purpose is to save and generate transaction scripts to dynamically update the tables if such needs occur.

- Current migration includes updates the state of the quantity column in the products table.

### `main.py`

Here is defined FastAPI endpoints.

> [!NOTE]
> Check current endpoints and their functions in [here](/backend/README.md)
