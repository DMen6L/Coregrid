# Coregrid

App meant for automation of core operations inside businesses.

## Features

 - [storing products, suppliers, supplier companies/brands](docs/DATABASE.md)
 - [configuration and maintenance of backend and database on python](docs/BACKEND.md)

## Tech stack

### Backend

- PostgeSQL
- Python - SQLAlchemy, psycopg, Alembic

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
source .venv/bin/activate
python main.py
```

Test the results

```bash
# connect
psql -U user -d coregrid

# list the tables
\dt

# exit
\q
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
│   │   └── models.py
│   ├── main.py
│   ├── pyproject.toml
│   ├── README.md
│   └── uv.lock
├── docs
│   ├── BACKEND.md
│   └── DATABASE.md
├── .env
├── .gitignore
└── README.md
```
