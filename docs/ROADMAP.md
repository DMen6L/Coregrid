# Coregrid roadmap

This file keeps the next Coregrid work organized as an action map. It is not a
promise that every item will be implemented immediately.

## Current baseline

Coregrid currently has the foundation for a small inventory control tool:

- FastAPI backend with PostgreSQL, SQLAlchemy, Pydantic, and Alembic migrations
- Vue, Vite, TypeScript frontend with Vue Router and TanStack Query
- Docker Compose setup for backend, frontend, and local PostgreSQL
- JWT authentication, users, workspaces, memberships, static roles, and
  permission checks
- workspace invitations with in-app acceptance
- workspace member list/detail views for users with `members.manage`
- workspace-scoped products, companies, suppliers, tags, supplier links,
  restocks, and sales
- product search that includes product names and tags
- popular tag display in the product list
- product detail and edit modal with supplier link add/update/delete behavior
- atomic product creation with existing or inline-created company and supplier
- company and supplier list/create/detail/edit workflows
- restock and sale list/create/detail workflows
- user account dropdown with workspace switching, workspace creation,
  invitations, and sign out
- dashboard sales, stock-risk, top-product, and top-supplier summaries

The next work should make Coregrid feel less like a CRUD interface and more like
a daily inventory assistant while hardening the new multi-user layer.

## Recommended order

### 1. Stabilize local Docker development

Goal: make local setup predictable before cloud deployment.

- document rebuild commands for frontend, backend, package changes, and Alembic
- keep Docker Postgres data in a named volume
- add a backend health endpoint when ready
- keep `.env.docker` as local-only configuration

### 2. Finish atomic product update endpoints

Goal: remove frontend partial-failure workflows.

Atomic product create exists for product + tags + company + supplier links. The
remaining multi-request risk is product update:

- update product metadata
- update/create/delete product-supplier links

Useful backend direction:

- add a composite product update endpoint with explicit `create`, `update`, and
  `delete` link operations
- keep the existing smaller endpoints for direct CRUD and simpler testing
- commit only once after all related operations succeed
- roll back if any child operation fails

### 3. Complete workspace member administration

Goal: turn current membership visibility and invitations into full member
administration.

Current implemented foundation:

- users can register, log in, and fetch `/auth/me`
- users can create and switch workspaces
- owners/admins can list members, inspect member details, list sent
  invitations, create invitations, and delete pending invitations
- invited users can see and accept active invitations from `/me/invitations`

Useful next steps:

- role change endpoint with checks that prevent removing the last owner
- member removal endpoint with checks that prevent deleting yourself or the last
  owner
- invitation revoke behavior using `revoked_at` instead of only hard delete, if
  auditability matters
- email delivery for invitation links
- endpoint tests for auth, workspace membership, permissions, invitations, and
  member list/detail

### 4. Audit log

Goal: make inventory mistakes traceable.

Useful events:

- product created or updated
- supplier/company created or updated
- product-supplier link created, updated, or deleted
- tag deleted or merged
- restock created
- sale created

An audit log becomes more valuable now that auth exists, because each event can
include the acting user.

### 5. Stock adjustment workflow

Goal: handle real inventory corrections separately from sales and restocks.

Useful first version:

- choose product-supplier link
- enter corrected quantity or delta
- require a reason such as damaged, lost, expired, recount, or correction
- store before/after quantity snapshots

This should not be hidden inside product editing because stock changes need
history.

### 6. Low-stock purchasing workflow

Goal: turn dashboard warnings into actions.

Useful first version:

- list low-stock and out-of-stock product-supplier links
- group rows by supplier
- show current quantity, threshold, sale price, and purchase price
- let the user prepare a restock draft from selected rows

Later:

- recommended reorder quantity
- supplier price history
- purchase-order export

### 7. Better product filtering

Goal: make the product list useful at scale.

Useful filters:

- stock status
- company
- supplier
- one or more tags
- low-stock threshold range
- has supplier links / missing supplier links

Keep search as a broad text search, but move exact narrowing into filters.

### 8. Import and export

Goal: make adoption easier for spreadsheet-based users.

Useful first version:

- CSV export for products, suppliers, companies, tags, restocks, and sales
- CSV import for initial products, companies, suppliers, and supplier links
- row-level validation errors for rejected imports

### 9. Tag management

Goal: make reusable tags maintainable.

Useful first version:

- tag list with usage counts
- delete unused or intentionally removed tags
- rename tag
- merge duplicate tags

### 10. Reporting improvements

Goal: make Coregrid answer business questions, not only show records.

Useful reports:

- inventory value report
- low-stock report
- sales by product, supplier, company, or tag
- gross profit by product or supplier
- stock received by date range
- slow-moving stock

## AWS deployment path

Do not connect full AWS production just because Docker now works locally. Treat
AWS as a staging goal until auth flows are hardened, backups exist, endpoint
tests cover workspace permissions, and production configuration is clearer.

Recommended learning path:

1. Keep local Docker Compose working first.
2. Deploy the Vue frontend as static build output.
3. Deploy the backend as a container in a staging environment.
4. Use managed PostgreSQL when the app needs reliable backups.
5. Add production CORS, environment variables, secrets, logging, and health
   checks before real users depend on it.

AWS service notes:

- AWS Amplify Hosting is a reasonable first AWS step for the built Vue frontend.
- AWS App Runner is not a good new target because AWS says it stopped accepting
  new customers on April 30, 2026.
- For backend containers, evaluate ECS Express Mode, Lightsail containers, or a
  small Lightsail/EC2 instance running Docker Compose.
- For PostgreSQL, use local Docker for development and RDS PostgreSQL for a
  more production-like managed database.

Useful AWS references:

- AWS App Runner availability change:
  https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html
- AWS Amplify Hosting:
  https://docs.amplify.aws/vue/how-amplify-works/
- Amazon RDS for PostgreSQL:
  https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html
- Amazon Lightsail containers:
  https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-container-services.html

## Documentation follow-ups

Keep documentation synchronized when these areas change:

- `README.md` for setup, Docker, and frontend/backend run commands
- `backend/README.md` for API endpoint contracts
- `docs/DATABASE.md` for model and migration changes
- `docs/STOCK_MOVEMENTS.md` for restock, sale, and future adjustment behavior
- frontend docs if the Vue module structure or API integration rules change
