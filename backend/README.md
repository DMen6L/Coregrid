# FastAPI

> [!NOTE]
> Check all table structures [here](/docs/DATABASE.md)

#### CRUD checklist

- [x] Create
- [x] Read
- [x] Update
- [x] Delete

## Current endpoints

### `GET /`

- Testing endpoint health

---

### Companies

#### `POST /companies`

- Creating new instance for table Companies

#### `PATCH /companies/{id}`

- Updating data of an instance for table Companies

#### `GET /companies`

- Returns all instances of table Companies

#### `GET /companies/{id}`

- Returns a single instance of Companies referenced by `id`

---

### Suppliers

#### `POST /suppliers`

- Creating new instance for table Suppliers

#### `PATCH /suppliers/{id}`

- Updating data of an instance for table Suppliers

#### `GET /suppliers`

- Returns all instances of table Suppliers

#### `GET /suppliers/{id}`

- Returns a single instance of Suppliers referenced by `id`

---

### Products

#### `/products`

- Creating new instance for table Products

#### `PATCH /products/{id}`

- Updating data of an instance for table Products

#### `GET /products`

- Returns all instances of table Products

#### `GET /products/{id}`

- Returns a single instance of Products referenced by `id`

---

### `DELETE /cleanup`

- Cleans out the tables present in Coregrid database

## Running the server

```bash
# from backend/
source .venv/bin/activate
fastapi dev main.py

# or directly
uv run fastapi dev main.py
```

> [!NOTE]
> Check http://127.0.0.1:8000/docs after running dev server for tests
