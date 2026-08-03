# Coregrid

App meant for automation of core operations inside businesses.

## Features

 - [storing products, suppliers, supplier companies/brands](docs/DATABASE.md)
 - [configuration and maintenance of backend and database on python](docs/BACKEND.md)
 - [stock movement history for inventory changes](docs/STOCK_MOVEMENTS.md)
 - per-product low-stock thresholds with calculated stock status
 - Vue inventory operations UI for product, supplier, company, and stock movement workflows

## Tech stack

### Backend

- PostgreSQL
- Python
- FastAPI

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

### Download PostgeSQL and Python+UV

Arch:

```bash
sudo pacman -S postgresql
sudo pacman -S python uv
```

### Start PostgeSQL

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

### Sync virtual environment

```bash
uv venv
uv sync
```

### Test scripts

Run the scripts

```bash
# Activate virtual environment
# from backend/
source .venv/bin/activate
pytest -s

# Or run directly
uv run pytest -s
```

### Run locally

Start the backend API:

```bash
# from backend/
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

The backend currently allows browser requests from `http://127.0.0.1:5173` and
`http://localhost:5173`. If Vite starts on a fallback port because `5173` is
busy, free port `5173` or update backend CORS for that local port.

Build/check the Vue frontend:

```bash
# from frontend-vue/
npm run type-check
npm run build
```


## Project structure

```text
.
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
│   │   └── test_api.py
│   └── uv.lock
├── docs
│   ├── BACKEND.md
│   ├── DATABASE.md
│   └── STOCK_MOVEMENTS.md
├── frontend-vue
│   ├── src
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
└── README.md
```
