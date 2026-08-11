# Coregrid

App meant for automation of core operations inside businesses.

## Features

- [storing products, suppliers, supplier companies/brands](docs/DATABASE.md)
- [configuration and maintenance of backend and database on Python](docs/BACKEND.md)
- [stock movement history for inventory changes](docs/STOCK_MOVEMENTS.md)
- [roadmap and next feature ideas](docs/ROADMAP.md)
- JWT authentication with user accounts
- workspace-scoped inventory data with role-based permissions
- workspace invitations, personal invitation acceptance, and member listing/detail views
- per-product low-stock thresholds with calculated stock status
- Vue inventory operations UI for product, supplier, company, member, invitation, and stock movement workflows

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

Run the scripts

```bash
# from backend/
uv run pytest -s
```

> [!NOTE]
> Some backend tests still need to be migrated to authenticated,
> workspace-scoped API requests after the user/workspace permission work.

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
│   │   ├── test_api.py
│   │   └── test_products.py
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
