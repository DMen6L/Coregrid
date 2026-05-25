from app.db import engine, Base
from app.models import Company, Supplier, Product


def main():
    # create all tables
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    main()
