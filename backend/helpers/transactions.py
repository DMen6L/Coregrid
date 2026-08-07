from typing import cast

from fastapi import HTTPException, status
from psycopg.errors import CheckViolation, ForeignKeyViolation, UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Company, Supplier, Tag
from app.schemas import ProductAtomicCreate, ProductSupplierAtomicCreate
from helpers.update_helpers import check_unique_constraints
from utils import normalize_tag_names


def raise_integrity_error(exc: IntegrityError) -> None:
    if isinstance(exc.orig, UniqueViolation):
        raise HTTPException(
            status_code=409, detail="Duplicate value conflicts existing row"
        ) from exc
    if isinstance(exc.orig, ForeignKeyViolation):
        raise HTTPException(
            status_code=409, detail="Referenced row does not exist or was changed"
        ) from exc
    if isinstance(exc.orig, CheckViolation):
        raise HTTPException(
            status_code=422, detail="Value violates a database constraint"
        ) from exc

    raise HTTPException(status_code=500, detail="Database error") from exc


def flush_or_raise(db: Session) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise_integrity_error(exc)


def commit_or_raise(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise_integrity_error(exc)


def create_or_resolve_company(
    data: ProductAtomicCreate,
    db: Session,
) -> int:
    if data.company_id is not None:
        company = db.get(Company, data.company_id)
        if company is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company with this id is not found.",
            )
        return company.id

    if data.company is not None:
        company_data = cast(
            dict[str, object],
            data.company.model_dump(),
        )

        check_unique_constraints(
            db=db,
            model=Company,
            constraint_name="uq_companies_workspace_name",
            values=company_data,
        )
        check_unique_constraints(
            db=db,
            model=Company,
            constraint_name="uq_companies_workspace_iin",
            values=company_data,
        )
        company = Company(**company_data)

        db.add(company)
        flush_or_raise(db)

        return company.id
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Company could not be created or extracted.",
    )


def create_or_resolve_supplier(
    product_link: ProductSupplierAtomicCreate,
    db: Session,
) -> int:
    if product_link.supplier_id is not None:
        supplier = db.get(Supplier, product_link.supplier_id)
        if supplier is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier with this id is not found.",
            )
        return supplier.id

    if product_link.supplier is not None:
        supplier_data = cast(
            dict[str, object],
            product_link.supplier.model_dump(),
        )

        check_unique_constraints(
            db=db,
            model=Supplier,
            constraint_name="uq_suppliers_workspace_name",
            values=supplier_data,
        )
        check_unique_constraints(
            db=db,
            model=Supplier,
            constraint_name="uq_suppliers_workspace_phone_number",
            values=supplier_data,
        )

        supplier = Supplier(**supplier_data)
        db.add(supplier)
        flush_or_raise(db)

        return supplier.id
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Supplier could not be created or extracted.",
    )


def get_or_create_tags(db: Session, tag_names: list[str]) -> list[Tag]:
    normalized_names = normalize_tag_names(tag_names)

    if not normalized_names:
        return []

    existing_tags = (
        db.query(Tag).filter(Tag.name.in_(normalized_names)).order_by(Tag.name).all()
    )
    existing_tags_by_name = {tag.name: tag for tag in existing_tags}
    new_tags = [
        Tag(name=tag_name)
        for tag_name in normalized_names
        if tag_name not in existing_tags_by_name
    ]

    db.add_all(new_tags)

    return sorted(
        [*existing_tags, *new_tags],
        key=lambda tag: tag.name,
    )
