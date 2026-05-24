-- Cleaning up previous tables
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS companies CASCADE;
DROP TABLE IF EXISTS suppliers CASCADE;


CREATE TABLE IF NOT EXISTS companies(
  id SERIAL PRIMARY KEY,
  IIN VARCHAR(12) UNIQUE,
  name VARCHAR(255) NOT NULL UNIQUE
);

-- TODO Add more contact information and make rule that at least one field is required
-- TODO Add full name configuration for the suppliers
CREATE TABLE IF NOT EXISTS suppliers(
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  phone_number VARCHAR(12) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS products(
  id SERIAL PRIMARY KEY,
  supplier_id INT,
  company_id INT,
  name VARCHAR(255) NOT NULL,
  price NUMERIC(10, 2) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),

  FOREIGN KEY(company_id) REFERENCES companies(id),
  FOREIGN KEY(supplier_id) REFERENCES suppliers(id),

  UNIQUE(company_id, supplier_id, name)
);
