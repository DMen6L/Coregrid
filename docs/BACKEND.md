# Coregrid Backend

## Libraries

- FastAPI
- SQLAlchemy
- Pydantic
- Alembic
- Pytest
- JWT/password hashing helpers

## App

### `config.py`

Reads database connection settings and JWT settings from environment variables.

### `db.py`

Initializes and holds essentials for the transactions with the database:
- engine
- Base
- session factory

### `models.py`

Holds actual table models that the database has, essential for both initialization and transactions.

- User
- Workspace
- WorkspaceMembership
- WorkspaceInvitation
- Company
- Supplier
- Product
- Tag
- ProductSupplier
- Restock
- RestockLine
- Sale
- SaleLine

> [!NOTE]
> for the actual database tables refer to [this](/docs/DATABASE.md)

### `main.py`

Defines the FastAPI app, local development CORS, the workspace-scoped dashboard
summary endpoint, and includes routers for auth, workspaces, personal user
actions, members, invitations, companies, suppliers, products, tags, restocks,
and sales.

> [!NOTE]
> Check current endpoints and their functions in [here](/backend/README.md)

### `helpers/auth.py`

Hashes and verifies passwords, creates JWT access tokens, and decodes bearer
tokens for authenticated requests.

### `helpers/dependencies.py`

Defines shared FastAPI dependencies:

- database session injection
- current authenticated user from `Authorization: Bearer <token>`
- workspace membership lookup from `workspace_id`
- permission checks through `require_workspace_permission(...)`

Workspace-scoped inventory endpoints return `403 Forbidden` when the user is not
a member of the workspace or does not have the required permission.

### `pagination.py`

Defines shared pagination helpers for ORM rows and aggregate/select mappings.
Collection endpoints generally accept `page` and `page_size`.

### `type_definitions.py`

Defines shared literal types and constants, including workspace role
permissions:

- `owner`: all current permissions
- `admin`: inventory, catalog, stock movement, member, and workspace management
- `manager`: inventory, catalog, and stock movement work
- `operator`: inventory and stock movement work
- `viewer`: inventory read access only

## Tests

### `backend/tests`

Automated tests use FastAPI `TestClient` and pytest.

> [!NOTE]
> The current test files still need migration to authenticated,
> workspace-scoped requests. They predate the user/workspace permission layer and
> should be updated before using them as a release signal.

```bash
# Run from backend/
uv run pytest -s
```

## Alembic

Purpose is to save and generate transaction scripts to dynamically update the tables if such needs occur.

- Current migrations include product constraints, product-supplier inventory,
  product tags, product low-stock thresholds, product quantity units, restocks,
  sales, workspace/user/membership tables, workspace invitations, and later
  workspace-scoped inventory relationship updates.
