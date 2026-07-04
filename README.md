# Coregrid

App meant for automation of core operations inside businesses.

## Features

 - [storing products, suppliers, supplier companies/brands](docs/DATABASE.md)
 - [configuration and maintenance of backend and database on python](docs/BACKEND.md)
 - [stock movement history for inventory changes](docs/STOCK_MOVEMENTS.md)
 - per-product low-stock thresholds with calculated stock status
 - static inventory operations UI for testing product workflows

## Tech stack

### Backend

- PostgreSQL
- Python
- FastAPI

### Frontend

- HTML
- CSS
- JavaScript

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

Start the static frontend:

```bash
# from frontend/
python3 -m http.server 5173
```

Open `http://127.0.0.1:5173` and keep the API base set to `http://127.0.0.1:8000`.


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
├── frontend
│   ├── css
│   ├── js
│   └── index.html
└── README.md
```
