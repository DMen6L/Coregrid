from app.type_definitions import BestSalesMode


def get_best_sales_expr(mode: BestSalesMode):
    from app.models import SaleLine
    from sqlalchemy import func

    match mode:
        case "quantity":
            return func.sum(SaleLine.sale_quantity)

        case "revenue":
            return func.sum(SaleLine.unit_sale_price_snapshot * SaleLine.sale_quantity)

        case "gross_profit":
            return func.sum(
                (SaleLine.unit_sale_price_snapshot - SaleLine.unit_cost_snapshot)
                * SaleLine.sale_quantity
            )


def normalize_tag_name(tag_name: str) -> str:
    return tag_name.strip().casefold()


def normalize_tag_names(tag_names: list[str]) -> list[str]:
    normalized_names = []
    seen_names = set()

    for tag_name in tag_names:
        normalized_name = normalize_tag_name(tag_name)

        if normalized_name in seen_names:
            continue

        seen_names.add(normalized_name)
        normalized_names.append(normalized_name)

    return normalized_names
