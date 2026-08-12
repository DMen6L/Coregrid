from .helpers import (
    assert_paginated_response,
    create_workspace_context,
    unique_iin,
    unique_phone_number,
    unique_suffix,
)


def create_company(client, workspace_id: int, headers: dict[str, str], *, name: str):
    response = client.post(
        f"/workspaces/{workspace_id}/companies",
        headers=headers,
        json={
            "name": name,
            "iin": unique_iin(),
        },
    )

    assert response.status_code == 201, response.json()
    return response.json()


def create_supplier(client, workspace_id: int, headers: dict[str, str], *, name: str):
    response = client.post(
        f"/workspaces/{workspace_id}/suppliers",
        headers=headers,
        json={
            "name": name,
            "phone_number": unique_phone_number(),
        },
    )

    assert response.status_code == 201, response.json()
    return response.json()


def create_product_full(
    client,
    workspace_id: int,
    headers: dict[str, str],
    *,
    name: str,
    company_id: int,
    supplier_id: int,
    quantity: int = 4,
    sale_price: int = 130,
):
    response = client.post(
        f"/workspaces/{workspace_id}/products/full",
        headers=headers,
        json={
            "product_name": name,
            "company_id": company_id,
            "tags": ["Retail", "retail", "Warehouse"],
            "quantity_unit": "шт",
            "low_stock_threshold": 3,
            "product_links": [
                {
                    "supplier_id": supplier_id,
                    "purchase_price": 100,
                    "margin_percent": 20,
                    "sale_price": sale_price,
                    "quantity": quantity,
                }
            ],
        },
    )

    assert response.status_code == 201, response.json()
    return response.json()


def create_product_with_link(
    client,
    context,
    *,
    quantity: int = 4,
    sale_price: int = 130,
):
    suffix = unique_suffix()
    workspace_id = context["workspace_id"]
    headers = context["headers"]
    company = create_company(
        client,
        workspace_id,
        headers,
        name=f"Company {suffix}",
    )
    supplier = create_supplier(
        client,
        workspace_id,
        headers,
        name=f"Supplier {suffix}",
    )
    product = create_product_full(
        client,
        workspace_id,
        headers,
        name=f"Product {suffix}",
        company_id=company["id"],
        supplier_id=supplier["id"],
        quantity=quantity,
        sale_price=sale_price,
    )

    return {
        "company": company,
        "supplier": supplier,
        "product": product,
        "link": product["supplier_links"][0],
    }


def test_products_are_workspace_scoped_and_searchable(client):
    first_context = create_workspace_context(client, user_prefix="first-owner")
    second_context = create_workspace_context(client, user_prefix="second-owner")
    suffix = unique_suffix()
    company = create_company(
        client,
        first_context["workspace_id"],
        first_context["headers"],
        name=f"Search company {suffix}",
    )
    supplier = create_supplier(
        client,
        first_context["workspace_id"],
        first_context["headers"],
        name=f"Search supplier {suffix}",
    )
    product = create_product_full(
        client,
        first_context["workspace_id"],
        first_context["headers"],
        name=f"Searchable product {suffix}",
        company_id=company["id"],
        supplier_id=supplier["id"],
        quantity=4,
    )

    first_list_response = client.get(
        f"/workspaces/{first_context['workspace_id']}/products",
        headers=first_context["headers"],
        params={"search": suffix, "page_size": 10},
    )
    assert first_list_response.status_code == 200
    first_list = first_list_response.json()
    assert_paginated_response(first_list)
    assert first_list["total"] == 1
    assert first_list["items"][0]["id"] == product["id"]
    assert first_list["items"][0]["company_name"] == company["name"]
    assert first_list["items"][0]["tags"] == ["retail", "warehouse"]
    assert first_list["items"][0]["suppliers_count"] == 1
    assert first_list["items"][0]["total_quantity"] == 4
    assert first_list["items"][0]["stock_status"] == "available"

    second_list_response = client.get(
        f"/workspaces/{second_context['workspace_id']}/products",
        headers=second_context["headers"],
        params={"search": suffix, "page_size": 10},
    )
    assert second_list_response.status_code == 200
    assert second_list_response.json()["total"] == 0

    cross_workspace_detail_response = client.get(
        f"/workspaces/{second_context['workspace_id']}/products/{product['id']}",
        headers=second_context["headers"],
    )
    assert cross_workspace_detail_response.status_code == 404


def test_product_supplier_link_lifecycle(client):
    context = create_workspace_context(client, user_prefix="catalog-owner")
    workspace_id = context["workspace_id"]
    headers = context["headers"]
    suffix = unique_suffix()
    company = create_company(
        client,
        workspace_id,
        headers,
        name=f"Link company {suffix}",
    )
    supplier = create_supplier(
        client,
        workspace_id,
        headers,
        name=f"Link supplier {suffix}",
    )

    product_response = client.post(
        f"/workspaces/{workspace_id}/products",
        headers=headers,
        json={
            "name": f"Linked product {suffix}",
            "company_id": company["id"],
            "tags": ["Linked"],
            "low_stock_threshold": 3,
        },
    )
    assert product_response.status_code == 201
    product = product_response.json()
    assert product["supplier_links"] == []

    link_response = client.post(
        f"/workspaces/{workspace_id}/products/{product['id']}/links",
        headers=headers,
        json=[
            {
                "supplier_id": supplier["id"],
                "purchase_price": 101,
                "margin_percent": 25,
                "quantity": 2,
            }
        ],
    )
    assert link_response.status_code == 201
    link = link_response.json()[0]
    assert link["floor_price"] == 127
    assert link["sale_price"] == 127
    assert link["stock_status"] == "low"

    patch_response = client.patch(
        f"/workspaces/{workspace_id}/products/{product['id']}/links/{link['id']}",
        headers=headers,
        json={
            "sale_price": 140,
            "quantity": 0,
        },
    )
    assert patch_response.status_code == 200
    patched_link = patch_response.json()
    assert patched_link["sale_price"] == 140
    assert patched_link["quantity"] == 0
    assert patched_link["stock_status"] == "out"

    delete_response = client.delete(
        f"/workspaces/{workspace_id}/products/{product['id']}/links/{link['id']}",
        headers=headers,
    )
    assert delete_response.status_code == 204

    detail_response = client.get(
        f"/workspaces/{workspace_id}/products/{product['id']}",
        headers=headers,
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["supplier_links"] == []


def test_restock_and_sale_update_quantity_and_dashboard(client):
    context = create_workspace_context(client, user_prefix="movement-owner")
    workspace_id = context["workspace_id"]
    headers = context["headers"]
    created = create_product_with_link(client, context, quantity=2, sale_price=130)
    product_id = created["product"]["id"]
    link_id = created["link"]["id"]

    restock_response = client.post(
        f"/workspaces/{workspace_id}/restocks",
        headers=headers,
        json={
            "note": "Test restock",
            "lines": [
                {
                    "product_supplier_id": link_id,
                    "restock_quantity": 3,
                }
            ],
        },
    )
    assert restock_response.status_code == 201
    restock = restock_response.json()
    assert restock["lines"][0]["product_supplier_id"] == link_id
    assert restock["lines"][0]["restock_quantity"] == 3
    assert restock["lines"][0]["unit_cost_snapshot"] == 100

    after_restock_response = client.get(
        f"/workspaces/{workspace_id}/products/{product_id}",
        headers=headers,
    )
    assert after_restock_response.status_code == 200
    assert after_restock_response.json()["supplier_links"][0]["quantity"] == 5

    sale_response = client.post(
        f"/workspaces/{workspace_id}/sales",
        headers=headers,
        json={
            "note": "Test sale",
            "lines": [
                {
                    "product_supplier_id": link_id,
                    "sale_quantity": 4,
                }
            ],
        },
    )
    assert sale_response.status_code == 201
    sale = sale_response.json()
    assert sale["lines"][0]["product_supplier_id"] == link_id
    assert sale["lines"][0]["sale_quantity"] == 4
    assert sale["lines"][0]["unit_cost_snapshot"] == 100
    assert sale["lines"][0]["unit_sale_price_snapshot"] == 130

    detail_response = client.get(
        f"/workspaces/{workspace_id}/products/{product_id}",
        headers=headers,
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["supplier_links"][0]["quantity"] == 1

    dashboard_response = client.get(
        f"/workspaces/{workspace_id}/summaries",
        headers=headers,
        params={"days": 7, "best_sales_mode": "quantity"},
    )
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["dashboard_sales_value"] == 520
    assert dashboard["dashboard_sales_count"] == 1
    assert dashboard["low_stock"] == 1
    assert dashboard["out_of_stock"] == 0
    assert dashboard["latest_sales"][0]["sales_value"] == 520
    assert dashboard["top_products"][0]["product_id"] == product_id
    assert dashboard["top_products"][0]["metric"] == 4
    assert dashboard["top_suppliers"][0]["supplier_id"] == created["supplier"]["id"]


def test_sale_rejects_quantity_above_available_stock(client):
    context = create_workspace_context(client, user_prefix="sale-owner")
    workspace_id = context["workspace_id"]
    headers = context["headers"]
    created = create_product_with_link(client, context, quantity=1, sale_price=125)
    product_id = created["product"]["id"]
    link_id = created["link"]["id"]

    response = client.post(
        f"/workspaces/{workspace_id}/sales",
        headers=headers,
        json={
            "lines": [
                {
                    "product_supplier_id": link_id,
                    "sale_quantity": 2,
                }
            ],
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "message": "Sale quantity exceeds available stock.",
        "product_supplier_id": link_id,
        "available_quantity": 1,
        "requested_quantity": 2,
    }

    detail_response = client.get(
        f"/workspaces/{workspace_id}/products/{product_id}",
        headers=headers,
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["supplier_links"][0]["quantity"] == 1
