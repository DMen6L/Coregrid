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
- AuditLog
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
summary endpoint, and includes routers for health, auth, workspaces, personal
user actions, members, invitations, companies, suppliers, products, tags,
restocks, and sales.

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

### `helpers/transactions.py`

Centralizes commit/flush error handling and audit-log creation. Mutating
workspace-scoped endpoints use `record_audit_log(...)` to store actor snapshots,
target snapshots, action names, entity details, structured changes, and metadata.

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

The current active suite covers the main endpoint groups:

- `test_health.py`: `/health` and `/ready`
- `test_auth.py`: registration, validation failures, login, rejected login, and
  `/auth/me`
- `test_workspaces.py`: workspace creation, workspace detail, and paginated
  workspace audit-log listing
- `test_companies.py`: company create/list/detail/update and validation
- `test_suppliers.py`: supplier create/list/detail/update and validation
- `test_products.py`: product create/list/detail/filter/update, tags, atomic
  create/update, and product-supplier link update/delete
- `test_tags.py`: tag list/search/delete
- `test_invitations.py`: invitation create/list/search/revoke and conflicts
- `test_members.py`: member list/detail/role update/delete and forbidden cases
- `test_me.py`: personal overview, profile/password update, invitation
  acceptance, and leaving workspaces
- `test_restocks.py`: restock create/list/detail and invalid line handling
- `test_sales.py`: sale create/list/detail, over-stock conflict, and invalid
  line handling
- `test_summaries.py`: dashboard summaries and query validation

Tests run against the configured local development database and truncate
Coregrid tables between tests. Apply migrations before running the suite and do
not use production database settings.

```bash
# Run from backend/
uv run alembic upgrade head
uv run pytest -s
```

GitHub Actions uses `.github/workflows/tests.yml` to start PostgreSQL, apply
Alembic migrations, and run the current endpoint test files as separate steps.
Validate workflow syntax locally with `actionlint .github/workflows/tests.yml`.

## Alembic

Purpose is to save and generate transaction scripts to dynamically update the tables if such needs occur.

- Current migrations include product constraints, product-supplier inventory,
  product tags, product low-stock thresholds, product quantity units, restocks,
  sales, workspace/user/membership tables, workspace invitations, and later
  workspace-scoped inventory relationship updates, audit logs, and related
  indexes.
