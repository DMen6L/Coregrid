# Coregrid

App meant for automation of core operations inside businesses.

## Features

- [storing products, suppliers, supplier companies/brands](docs/DATABASE.md)
- [configuration and maintenance of backend and database on Python](docs/BACKEND.md)
- [stock movement history for inventory changes](docs/STOCK_MOVEMENTS.md)
- [roadmap and next feature ideas](docs/ROADMAP.md)
- JWT authentication with user accounts
- workspace-scoped inventory data with role-based permissions
- workspace invitations, personal invitation acceptance, member listing/detail,
  member role changes, and member removal
- personal account page for profile updates, invitations, workspace switching,
  workspace creation, password updates, workspace leaving, and sign out
- workspace audit log listing for member, invitation, catalog, stock movement,
  and workspace events
- per-product low-stock thresholds with calculated stock status
- product filters for search text, company, supplier, tags, and stock status
- Vue inventory operations UI for product, supplier, company, member,
  invitation, audit log, and stock movement workflows
- GitHub Actions workflow for the current backend endpoint tests

## Tech stack

### Backend

- PostgreSQL
- Python
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- Pytest

### Frontend

- Vue
- Vite
- TypeScript
- Vue Router
- TanStack Query
- Bootstrap

---

## Setup

### Clone repo

```bash
git clone git@github.com:DMen6L/Coregrid.git
cd Coregrid
```

### Download PostgreSQL and Python+UV

Arch:

```bash
sudo pacman -S postgresql
sudo pacman -S python uv
```

### Start PostgreSQL

```bash
sudo systemctl enable postgresql
sudo systemctl start postgresql
# Optional checks
systemctl status postgresql
```

### Create databases

```bash
sudo -iu postgres psql
```

```sql
CREATE DATABASE coregrid;
```

### Sync backend virtual environment

```bash
# from backend/
uv venv
uv sync
```

### Configure backend environment

The backend reads database and JWT settings from environment variables. For
local development, put values in `.env`; for Docker Compose, use `.env.docker`.

Required variables:

```text
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=
DB_NAME=
JWT_SECRET_KEY=
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

When using Compose, `DB_HOST` should point at the database service name and
`DB_PORT` should use the container PostgreSQL port.

### Test scripts

Run the backend tests:

```bash
# from backend/
uv run alembic upgrade head
uv run pytest -s
```

> [!NOTE]
> Backend tests use the configured local development database and clean the
> Coregrid tables before and after each test. Do not point test environment
> variables at production data.

The repository also has a GitHub Actions workflow at
`.github/workflows/tests.yml`. It starts PostgreSQL, applies Alembic migrations,
and runs the current endpoint test files as separate steps.
You can validate workflow syntax locally with:

```bash
actionlint .github/workflows/tests.yml
```

### Run locally

Start the backend API:

```bash
# from backend/
uv run alembic upgrade head
uv run fastapi dev main.py
```

Start the Vue frontend:

```bash
# from frontend-vue/
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. The navbar API selector defaults to
`http://127.0.0.1:8000`; choose another configured option or `Другой` if the
backend is published on a different host port. You can also preselect an API
base with a query parameter, for example:

```text
http://127.0.0.1:5173/?api_base=http://127.0.0.1:8001
```

The backend currently allows browser requests from `http://127.0.0.1:5173`,
`http://localhost:5173`, `http://127.0.0.1:5500`, and
`http://localhost:5500`. If Vite starts on a fallback port because `5173` is
busy, free port `5173` or update backend CORS for that local port.

Build/check the Vue frontend:

```bash
# from frontend-vue/
npm run type-check
npm run build
```

### Run with Docker Compose

`compose.yaml` defines three services:

- `db`: PostgreSQL, exposed on host port `5433`
- `backend`: FastAPI, exposed on host port `8000`
- `frontend`: Vite dev server, exposed on host port `5173`

Start or rebuild the stack:

```bash
docker compose --env-file .env.docker up -d --build
```

Apply migrations inside the backend container:

```bash
docker compose --env-file .env.docker exec backend uv run --no-sync alembic upgrade head
```

Rebuild only one changed service:

```bash
docker compose --env-file .env.docker up -d --build backend
docker compose --env-file .env.docker up -d --build frontend
```

Stop the stack:

```bash
docker compose --env-file .env.docker down --remove-orphans
```


## Project structure

```text
.
├── compose.yaml
├── .github
│   └── workflows
│       └── tests.yml
├── backend
│   ├── alembic
│   │   ├── env.py
│   │   ├── README
│   │   ├── script.py.mako
│   │   └── versions
│   ├── alembic.ini
│   ├── app
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── schemas.py
│   ├── main.py
│   ├── pyproject.toml
│   ├── README.md
│   ├── routers
│   ├── tests
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_companies.py
│   │   ├── test_health.py
│   │   ├── test_invitations.py
│   │   ├── test_me.py
│   │   ├── test_members.py
│   │   ├── test_products.py
│   │   ├── test_restocks.py
│   │   ├── test_sales.py
│   │   ├── test_summaries.py
│   │   ├── test_suppliers.py
│   │   ├── test_tags.py
│   │   └── test_workspaces.py
│   └── uv.lock
├── docs
│   ├── BACKEND.md
│   ├── DATABASE.md
│   ├── ROADMAP.md
│   └── STOCK_MOVEMENTS.md
├── frontend-vue
│   ├── src
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
└── README.md
```
