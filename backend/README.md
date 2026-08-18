# Coregrid Backend

FastAPI backend for Coregrid inventory, workspace, authentication, member,
invitation, supplier, company, restock, sale, tag, and dashboard workflows.

> [!NOTE]
> Table structures are documented in [`docs/DATABASE.md`](../docs/DATABASE.md).

## Request model

Public endpoints:

- `GET /health`
- `GET /ready`
- `POST /auth/register`
- `POST /auth/login`

Authenticated endpoints require:

```http
Authorization: Bearer <access_token>
```

Inventory and member-management endpoints are workspace-scoped:

```text
/workspaces/{workspace_id}/...
```

The backend first checks that the current user has a
`workspace_memberships` row for the requested `workspace_id`, then checks the
required permission for the endpoint.

## Roles and permissions

Current permissions are defined in `backend/app/type_definitions.py`.

| Role | Permissions |
| --- | --- |
| `owner` | `inventory.read`, `catalog.write`, `stock_movement.create`, `members.manage`, `workspace.manage`, `workspace.delete` |
| `admin` | `inventory.read`, `catalog.write`, `stock_movement.create`, `members.manage`, `workspace.manage` |
| `manager` | `inventory.read`, `catalog.write`, `stock_movement.create` |
| `operator` | `inventory.read`, `stock_movement.create` |
| `viewer` | `inventory.read` |

## Pagination

Collection endpoints that paginate use:

- `page`: page number, default `1`, minimum `1`
- `page_size`: rows per page, default `20`, maximum `100`

Paginated responses use:

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0,
  "total_pages": 0,
  "has_next": false,
  "has_previous": false
}
```

## Current endpoints

### Health

#### `GET /health`

- Returns `{"status": "ok"}` when the API process is running.

#### `GET /ready`

- Checks the database connection with `SELECT 1`.
- Returns `{"status": "ready", "database": "ok"}` when the API can reach the
  configured database.
- Returns `503 Service Unavailable` when the readiness check fails.

### Auth

#### `POST /auth/register`

- Creates a user.
- Requires `email`, `name`, and `password`.
- Passwords must be at least 12 characters and pass basic strength checks.
- Duplicate emails return `409 Conflict`.
- Returns the created user without password data.

#### `POST /auth/login`

- Accepts `email` and `password`.
- Returns a bearer token response:

```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

#### `GET /auth/me`

- Returns the current authenticated user.

### Personal Account

#### `GET /me`

- Returns the current authenticated user's account overview.
- Response includes:
  - `user`: current user data.
  - `workspaces`: workspaces where the user is a member, each with `id`, `name`, and the user's `role`.
  - `invitations`: active pending invitations for the user's email, including workspace and inviter details.

#### `POST /me/accept/{invitation_id}`

- Accepts one invitation for the current user's email.
- Creates a workspace membership with the invitation role.
- Marks the invitation as accepted.
- Returns the accepted workspace.
- Missing or email-mismatched invitations return `404`.
- Expired, revoked, already accepted, or duplicate-membership invitations return
  `409 Conflict`.

#### `PATCH /me`

- Updates the current authenticated user's profile.
- Accepts `name` and `email`.
- Duplicate emails return `409 Conflict`.
- Returns the updated account overview.

#### `PATCH /me/password`

- Updates the current authenticated user's password.
- Accepts `current_password` and `new_password`.
- Wrong current passwords return `403 Forbidden`.
- Reusing the current password returns `400 Bad Request`.
- Weak or identity-derived new passwords are rejected.
- Returns the updated account overview without password data.

#### `DELETE /me/workspaces/{workspace_id}`

- Lets a non-owner leave one workspace.
- Returns `204 No Content` on success.
- Returns `404` if the current user is not a member of the workspace.
- Returns `409 Conflict` when the current user is an owner and must transfer
  ownership first.

### Workspaces

#### `GET /workspaces/{workspace_id}`

- Returns one workspace membership view for the current user.
- Requires membership in that workspace.

#### `GET /workspaces/{workspace_id}/logs`

- Requires `workspace.manage`.
- Returns paginated audit log rows for the workspace, newest first.
- Each row includes actor snapshot fields, optional target-user snapshot fields,
  action, entity data, structured `changes`, structured `extra_data`, and
  `created_at`.

#### `POST /workspaces`

- Creates a workspace.
- Creates an `owner` membership for the current user.
- Duplicate workspace names return `409 Conflict`.

### Workspace Members

Requires `members.manage`.

#### `GET /workspaces/{workspace_id}/members`

- Returns a paginated member summary list.
- Supports `search` by member name or email.
- Summary rows include membership `id`, user `name`, user `email`, and `role`.

#### `GET /workspaces/{workspace_id}/members/{member_id}`

- Returns one member detail row.
- Detail rows include membership `id`, user `id`, user `name`, user `email`,
  and `role`.
- Returns `404` if the membership id is not inside the workspace.

#### `PATCH /workspaces/{workspace_id}/members/{member_id}/role`

- Updates one workspace member's role.
- Accepts `new_role` as a query parameter.
- Allowed target roles are `admin`, `manager`, `operator`, and `viewer`.
- A user cannot update their own role through this endpoint.
- The `owner` role cannot be assigned or changed through this endpoint.
- Only owners can grant `admin` or change existing admins.
- Returns the updated member detail row.

#### `DELETE /workspaces/{workspace_id}/members/{member_id}`

- Removes one member from the workspace.
- A user cannot remove themself through this endpoint.
- Owners cannot be removed through this endpoint.
- Only owners can remove admins.
- Returns `204 No Content` on success.

### Workspace Invitations

Requires `members.manage`.

#### `GET /workspaces/{workspace_id}/invitations`

- Returns a paginated list of sent invitations for the workspace.
- Supports `search` by invited email.
- Response includes invitation id, workspace id, inviter user id, email, role,
  created time, expiry time, accepted time, and revoked time.
- The stored token hash is not exposed.

#### `POST /workspaces/{workspace_id}/invitations`

- Creates an invitation for `email` and role `admin`, `manager`, `operator`, or
  `viewer`.
- Invitation ids are UUIDs.
- Invitations currently expire after 7 days.
- Raw email-token delivery is not implemented yet; the app accepts invitations
  by UUID for in-app pending invitations.
- Existing workspace members and duplicate active invitations return
  `409 Conflict`.

#### `DELETE /workspaces/{workspace_id}/invitations/{invitation_id}`

- Revokes an invitation from the workspace by setting `revoked_at`.
- Returns `204 No Content` on success.
- Repeating the delete for an already revoked invitation is a no-op `204`.
- Returns `404` if the invitation does not exist in the workspace.
- Returns `409 Conflict` if the invitation has already been accepted.

### Dashboard

Requires `inventory.read`.

#### `GET /workspaces/{workspace_id}/summaries`

- Returns dashboard totals and rankings.
- Query parameters:
  - `days`: integer from `7` to `365`, default `7`
  - `best_sales_mode`: `quantity`, `revenue`, or `gross_profit`
- Response includes sales value, sales count, low-stock count, out-of-stock
  count, daily sales, top products, and top suppliers.

### Companies

Read endpoints require `inventory.read`; create/update endpoints require
`catalog.write`.

#### `GET /workspaces/{workspace_id}/companies`

- Returns a paginated company list.
- Supports `search` by company name.

#### `GET /workspaces/{workspace_id}/companies/{id}`

- Returns one company by id inside the workspace.

#### `POST /workspaces/{workspace_id}/companies`

- Creates a company inside the workspace.
- Requires `name`.
- Accepts nullable `iin`.

#### `PATCH /workspaces/{workspace_id}/companies/{id}`

- Updates company fields.
- Empty update bodies are rejected.
- `iin` may be set to `null`.
- Duplicate workspace-local `name` or non-null `iin` returns `409 Conflict`.

### Suppliers

Read endpoints require `inventory.read`; create/update endpoints require
`catalog.write`.

#### `GET /workspaces/{workspace_id}/suppliers`

- Returns a paginated supplier list.
- Supports `search` by supplier name.
- Summary rows include `product_links_count`.

#### `GET /workspaces/{workspace_id}/suppliers/{id}`

- Returns one supplier by id inside the workspace.
- Includes linked product-supplier rows.

#### `POST /workspaces/{workspace_id}/suppliers`

- Creates a supplier.
- Requires `name`.
- Requires `phone_number` in `8XXXXXXXXXX` or `+7XXXXXXXXXX` format.

#### `PATCH /workspaces/{workspace_id}/suppliers/{id}`

- Updates supplier fields.
- Empty update bodies are rejected.
- `null` update values are rejected.
- Duplicate workspace-local `name` or `phone_number` returns `409 Conflict`.

### Products

Read endpoints require `inventory.read`; create/update/delete-link endpoints
require `catalog.write`.

#### `GET /workspaces/{workspace_id}/products`

- Returns a paginated product summary list.
- Supports `search` by product name or tag name.
- Supports `company_name` and `supplier_name` filters by partial name match.
- Supports repeated `tags` query parameters. A product must have every requested
  tag to match.
- Supports `stock_status` values `out`, `low`, and `available`.
- Product summaries include:
  - `company_name`
  - `tags`
  - `suppliers_count`
  - aggregated `total_quantity`
  - cheapest available supplier pricing fields
  - calculated `stock_status`

#### `GET /workspaces/{workspace_id}/products/{id}`

- Returns one product by id inside the workspace.
- Includes company data, tags, and product-supplier links.

#### `POST /workspaces/{workspace_id}/products`

- Creates a catalog product.
- Requires `name` and `company_id`.
- Accepts `quantity_unit`, defaulting to `шт`.
- Accepts `low_stock_threshold`, defaulting to `5`.
- Accepts `tags` as tag-name strings.
- Does not create supplier links; use
  `POST /workspaces/{workspace_id}/products/{product_id}/links`.

#### `POST /workspaces/{workspace_id}/products/full`

- Atomically creates one product with tags, company selection or inline company
  creation, and optional product-supplier links.
- The company source must be exactly one of `company_id` or `company`.
- Each supplier link source must be exactly one of `supplier_id` or `supplier`.
- Rolls back the whole operation if any child creation or validation fails.

#### `PATCH /workspaces/{workspace_id}/products/{id}/full`

- Atomically updates product metadata, tags, and listed existing
  product-supplier links.
- Product metadata fields match `PATCH /workspaces/{workspace_id}/products/{id}`.
- Omit `tags` to keep existing tags; send `tags: []` to clear all tags.
- `product_links` is optional. When provided, it must contain at least one item.
- Each `product_links` item requires the existing product-supplier link `id`
  and at least one editable link field.
- Nested link updates can change `purchase_price`, `margin_percent`,
  `sale_price`, and `quantity`.
- Missing product, company, or product-supplier link references return `404`.
- Duplicate product-supplier link ids inside one request return `422`.
- `sale_price` below calculated floor price returns `422`.
- Nested product-supplier link creation and deletion remain handled by the
  dedicated link endpoints.

#### `PATCH /workspaces/{workspace_id}/products/{id}`

- Updates product metadata.
- Can update `name`, `company_id`, `quantity_unit`, `low_stock_threshold`, and
  `tags`.
- Omit `tags` to keep existing tags.
- Send `tags: []` to clear all tags.
- Empty update bodies are rejected.
- Duplicate workspace-local `(name, company_id, quantity_unit)` returns
  `409 Conflict`.

#### `POST /workspaces/{workspace_id}/products/{product_id}/links`

- Creates one or more product-supplier links for an existing product.
- Body is a non-empty list.
- Each item requires `supplier_id`, `purchase_price`, and optionally
  `margin_percent`, `sale_price`, and `quantity`.
- When `sale_price` is omitted, it defaults to the calculated floor price.
- Duplicate suppliers inside one request return `422`.
- Missing suppliers return `404`.
- Existing duplicate product-supplier links return `409`.

#### `PATCH /workspaces/{workspace_id}/products/{product_id}/links/{link_id}`

- Updates one product-supplier link.
- Can update `supplier_id`, `purchase_price`, `margin_percent`, `sale_price`,
  and `quantity`.
- Empty update bodies are rejected.
- `null` update values are rejected.
- Missing product, link, or supplier references return `404`.
- Duplicate `(product_id, supplier_id, workspace_id)` returns `409 Conflict`.
- `sale_price` below calculated floor price returns `422`.

#### `DELETE /workspaces/{workspace_id}/products/{product_id}/links/{link_id}`

- Deletes a product-supplier link.
- Returns `404` when the product or link is missing, or when the link belongs to
  a different product/workspace.
- Returns `409 Conflict` when the link has stock or restock/sale history.
- Returns `204 No Content` on successful deletion.

Product `stock_status` values:

- `out` when total quantity is `0`
- `low` when total quantity is at or below the product low-stock threshold
- `available` otherwise

### Tags

List requires `inventory.read`; delete requires `catalog.write`.

#### `GET /workspaces/{workspace_id}/tags`

- Returns a paginated list of tags ordered by usage count, then name.
- Supports `search` by tag name.
- Returns only tags attached to at least one product.

#### `DELETE /workspaces/{workspace_id}/tags/{id}`

- Deletes a tag.
- Product-tag join rows are removed by database cascade.
- Returns `404` when the tag does not exist in the workspace.

### Restocks

Read endpoints require `inventory.read`; create requires
`stock_movement.create`.

#### `GET /workspaces/{workspace_id}/restocks`

- Returns a paginated restock summary list.
- Supports date filters:
  - `from=YYYY-MM-DD`
  - `to=YYYY-MM-DD`
- Ordered newest first.

#### `GET /workspaces/{workspace_id}/restocks/{restock_id}`

- Returns one restock with line details inside the workspace.

#### `POST /workspaces/{workspace_id}/restocks`

- Creates one restock with one or more lines.
- Each line references `product_supplier_id`.
- Increases `product_suppliers.quantity` in the same transaction.
- Optional `unit_cost_snapshot` defaults to the link purchase price.
- Duplicate product-supplier links in one restock are rejected.

### Sales

Read endpoints require `inventory.read`; create requires
`stock_movement.create`.

#### `GET /workspaces/{workspace_id}/sales`

- Returns a paginated sale summary list.
- Supports date filters:
  - `from=YYYY-MM-DD`
  - `to=YYYY-MM-DD`
- Ordered newest first.

#### `GET /workspaces/{workspace_id}/sales/{sale_id}`

- Returns one sale with line details inside the workspace.

#### `POST /workspaces/{workspace_id}/sales`

- Creates one sale with one or more lines.
- Each line references `product_supplier_id`.
- Decreases `product_suppliers.quantity` in the same transaction.
- Rejects a sale with `409 Conflict` when requested quantity exceeds available
  stock.
- Snapshots purchase price, sale price, and quantity unit.

## Running the server

```bash
# from backend/
uv run alembic upgrade head
uv run fastapi dev main.py
```

> [!NOTE]
> Check `http://127.0.0.1:8000/docs` after running the dev server.

## Local frontend access

`main.py` allows local browser requests from:

- `http://127.0.0.1:5173`
- `http://localhost:5173`
- `http://127.0.0.1:5500`
- `http://localhost:5500`

If the frontend runs on another local port, update CORS before using the browser
against that port.

## Tests

```bash
# from backend/
uv run alembic upgrade head
uv run pytest -s
```

> [!NOTE]
> The tests run against the configured local development database and truncate
> Coregrid tables between tests. Keep migrations applied before running them and
> never point test configuration at production data.

Current active test files:

- `tests/test_health.py`
- `tests/test_auth.py`
- `tests/test_workspaces.py`
- `tests/test_companies.py`
- `tests/test_suppliers.py`
- `tests/test_products.py`
- `tests/test_tags.py`
- `tests/test_invitations.py`
- `tests/test_members.py`
- `tests/test_me.py`
- `tests/test_restocks.py`
- `tests/test_sales.py`
- `tests/test_summaries.py`

The GitHub Actions workflow in `../.github/workflows/tests.yml` runs those test
files as separate CI steps after starting PostgreSQL and applying migrations.
