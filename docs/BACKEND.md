# Coregrid Backend

## Libraries

- SQLAlchemy
- Alembic
- FastAPI
- Pytest

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
- Tag
- StockMovement
- StockMovementLine

> [!NOTE]
> for the actual database tables refer to [this](/docs/DATABASE.md)

### `main.py`

Defines the FastAPI app, local development CORS, and includes the routers for companies, suppliers, products, tags, and stock movements.

> [!NOTE]
> Check current endpoints and their functions in [here](/backend/README.md)

### `pagination.py`

Defines shared pagination defaults, query parameter constraints, and the helper
used by collection endpoints.

## Tests

### `test_api.py`

Automated tests to check responses of FastAPI.
Currently includes CRUD, validation, delete behavior, pagination behavior,
product tags, product pricing rules, quantity units, stock movement behavior,
explicit sales, sales summaries, dashboard daily totals, bestseller rankings,
and low-stock threshold behavior.

- Needed to lower amount of manual testing of endpoints.

```bash
# Run from backend/
uv run pytest -s
```

## Alembic

Purpose is to save and generate transaction scripts to dynamically update the tables if such needs occur.

- Current migrations include product constraints, stock movement tables, product
  tags, product low-stock thresholds, product quantity units, and stock movement
  unit snapshots, and sales backfilled from historical outgoing movements.
