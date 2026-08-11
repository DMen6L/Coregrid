# Coregrid database

## Tables

***All table structures are defined in `backend/app/models.py`***

## Workspace scope and identifiers

Coregrid is currently multi-workspace. Most business data includes
`workspace_id`, and API access is checked through the authenticated user's
`workspace_memberships` row.

Primary key `id` values are global per table, not per workspace. It is normal
for one workspace to see product ids such as `1`, `2`, and `9` because rows in
other workspaces use the same sequence. Workspace ownership is enforced with
`workspace_id` filters and workspace-scoped unique constraints, not composite
primary keys.

### Users

Stores application users.

- `id` unique identifier for the user
- `email` unique user email, normalized by schemas before storing
- `password_hash` hashed password, never the raw password
- `name` display name

### Workspaces

Stores independent business workspaces.

- `id` unique identifier for the workspace
- `name` unique workspace name
- `created_at` time when the workspace was created

Creating a workspace also creates an owner membership for the current user.

### Workspace memberships

Connects users to workspaces and stores their role.

- `id` unique identifier for the membership row
- `user_id` reference to `users`
- `workspace_id` reference to `workspaces`
- `role` one of `owner`, `admin`, `manager`, `operator`, or `viewer`

`(user_id, workspace_id)` is unique, so one user has only one role per
workspace.

Current role permissions are defined in `backend/app/type_definitions.py`:

- `owner`: inventory read, catalog write, stock movement create, member
  management, workspace management, workspace delete
- `admin`: inventory read, catalog write, stock movement create, member
  management, workspace management
- `manager`: inventory read, catalog write, stock movement create
- `operator`: inventory read, stock movement create
- `viewer`: inventory read

### Workspace invitations

Stores invitations sent by workspace admins/owners.

- `id` UUID primary key used to identify the invitation
- `workspace_id` reference to the invited workspace
- `inviter_user_id` nullable reference to the user who sent the invitation
- `email` invited email address
- `role` granted role, one of `admin`, `manager`, `operator`, or `viewer`
- `token_hash` hashed invitation token reserved for future email-link flows
- `created_at` time when the invitation was created
- `expires_at` time when the invitation becomes unusable
- `accepted_at` time when it was accepted, if accepted
- `revoked_at` time when it was revoked, if revoked

Invitation ids are UUIDs as the first non-integer-id experiment. The API does
not expose `token_hash` in response schemas.

### Companies

Stores supplier companies whose products are stored.

- `id` unique identifier given to the company/brand
- `workspace_id` reference to the owning workspace
- `IIN` unique identifier used in referring to the company in documents or receipts
- `name` name of the referred company/brand

Company `name` and non-null `IIN` are unique inside one workspace.

### Suppliers

Stores identities and contact information of the people that provide the listed products.

- `id` unique identifier given to each individual or contact
- `workspace_id` reference to the owning workspace
- `name` name of the individual used to refer them
- `phone_number` contact information in Kazakh local `8XXXXXXXXXX` or international `+7XXXXXXXXXX` format

Supplier `name` and `phone_number` are unique inside one workspace.

### Products

Stores catalog product identities. Supplier-specific stock and pricing lives in
`product_suppliers`.

- `id` unique identifier of each product
- `workspace_id` reference to the owning workspace
- `company_id` required reference to the company/brand connected to the product
- `name` stores the names of each of the products
- `created_at` needed to identify the creation time of the product
- `quantity_unit` stores the short unit label used for this product, default set
  to `шт`
- `low_stock_threshold` stores the warning threshold for aggregated stock,
  default set to 5

`(workspace_id, name, company_id, quantity_unit)` is unique.

### Product suppliers

Stores the many-to-many relationship between products and suppliers. This is the
current inventory and pricing row used by restocks and sales.

- `id` unique identifier of each product-supplier link
- `workspace_id` reference to the owning workspace
- `product_id` reference to the catalog product
- `supplier_id` reference to the supplier
- `purchase_price` stores the price paid when buying this product from this supplier
- `margin_percent` stores the desired markup percentage over `purchase_price`
- `sale_price` stores the final editable selling price shown to sellers
- `quantity` stores the currently stored amount for this product-supplier link

`(product_id, supplier_id, workspace_id)` is unique, so one supplier has only
one active link for a given product inside a workspace.

`floor_price` is calculated by the API and is not stored as a column:

```text
floor_price = ceil(purchase_price * (1 + margin_percent / 100))
```

`sale_price` must be equal to or higher than `floor_price`. This lets sellers
round prices up to cleaner values while preserving the minimum margin.

Stock status is calculated by the API and is not stored as a column:

- `out` when `quantity` is `0`
- `low` when quantity is above `0` and at or below the product's
  `low_stock_threshold`
- `available` otherwise

Product list summaries calculate status from aggregated supplier-link quantity.

### Tags

Stores reusable product labels used for filtering and search.

- `id` unique identifier of each tag
- `workspace_id` reference to the owning workspace
- `name` normalized lowercase tag name
- `created_at` time when the tag was created

Tag `name` is unique inside one workspace.

### Product tags

Stores the many-to-many relationship between products and tags.

- `product_id` reference to the tagged product
- `tag_id` reference to the reusable tag
- `(product_id, tag_id)` is unique through the composite primary key

Deleting a product removes only rows from `product_tags`; reusable tag records
remain available for other products.

Deleting a tag removes its `product_tags` rows through database cascade.

Workspace ownership is derived from the connected `products` and `tags` rows.

### Restocks

Stores incoming stock transaction headers.

- `id` unique identifier of each restock
- `workspace_id` reference to the owning workspace
- `note` optional text note for the restock
- `created_at` time when the restock was created

### Restock lines

Stores the product-supplier level changes inside a restock.

- `id` unique identifier of each restock line
- `workspace_id` reference to the owning workspace
- `restock_id` reference to the restock header
- `product_supplier_id` reference to the product-supplier link that changed
- `restock_quantity` positive quantity added to stock
- `unit_cost_snapshot` optional copied or entered purchase cost
- `quantity_unit_snapshot` product quantity unit copied when created

### Sales

Stores commercial sale records.

- `id` unique identifier of each sale
- `workspace_id` reference to the owning workspace
- `note` optional text note for the sale
- `created_at` time when the sale was created

### Sale lines

Stores the product-supplier level changes inside a sale.

- `id` unique identifier of each sale line
- `workspace_id` reference to the owning workspace
- `sale_id` reference to the sale header
- `product_supplier_id` reference to the product-supplier link that changed
- `sale_quantity` positive quantity removed from stock
- `unit_cost_snapshot` purchase price copied when the sale was created
- `unit_sale_price_snapshot` sale price copied when the sale was created
- `quantity_unit_snapshot` product quantity unit copied when created

## Connection and working with Coregrid database

```bash
# connect
psql -U postgres -d coregrid

# connect to the Docker Compose database from the host
psql -h 127.0.0.1 -p 5433 -U postgres -d coregrid

# list the tables
\dt

# check tables individually
# table_name is to be substituted with proper name of the table
SELECT * FROM table_name;

# exit
\q
```
