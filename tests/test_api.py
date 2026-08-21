import base64
import json
import pytest

from itsdangerous import TimestampSigner

from app.security import SESSION_SECRET

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, engine, get_db
from app.main import app


def authenticate_warehouse(client: TestClient) -> None:
    session_data = json.dumps({"warehouse_access": True}).encode("utf-8")
    signed_session = TimestampSigner(SESSION_SECRET).sign(
        base64.b64encode(session_data)
    )
    client.cookies.set("session", signed_session.decode("utf-8"))


@pytest.fixture()
def client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False)

    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def create_category(client: TestClient) -> int:
    response = client.post("/categories", json={"name": "Eletrônicos"})
    assert response.status_code == 201
    return response.json()["id"]


def create_product(client: TestClient, category_id: int, quantity: int = 10) -> int:
    response = client.post(
        "/products",
        json={
            "name": "Teclado mecânico",
            "quantity": quantity,
            "category_id": category_id,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_create_category_and_product(client: TestClient):
    category_id = create_category(client)
    product_id = create_product(client, category_id)

    response = client.get("/products")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": product_id,
            "name": "Teclado mecânico",
            "quantity": 10,
            "minimum_quantity": 3,
            "category_id": category_id,
        }
    ]


def test_valid_stock_movement_updates_quantity(client: TestClient):
    category_id = create_category(client)
    product_id = create_product(client, category_id, quantity=10)

    movement_response = client.post(
        "/stock-movements",
        json={
            "product_id": product_id,
            "movement_type": "out",
            "quantity": 3,
        },
    )

    assert movement_response.status_code == 201

    products = client.get("/products").json()
    assert products[0]["quantity"] == 7

    history = client.get(f"/products/{product_id}/movements").json()
    assert len(history) == 1
    assert history[0]["movement_type"] == "out"
    assert history[0]["quantity"] == 3


def test_negative_stock_is_rejected_without_changing_quantity(client: TestClient):
    category_id = create_category(client)
    product_id = create_product(client, category_id, quantity=2)

    response = client.post(
        "/stock-movements",
        json={
            "product_id": product_id,
            "movement_type": "out",
            "quantity": 3,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Insufficient stock for this movement."

    products = client.get("/products").json()
    assert products[0]["quantity"] == 2

    history = client.get(f"/products/{product_id}/movements").json()
    assert history == []


def test_root_redirects_to_login(client: TestClient):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"

def test_health_reports_database_diagnostics(client: TestClient):
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert data["database_backend"] == engine.url.get_backend_name()
    assert set(data["counts"]) == {
        "categories",
        "products",
        "stock_movements",
    }


def test_category_creation_route_is_unique():
    category_creation_routes = [
        route
        for route in app.routes
        if getattr(route, "path", None) == "/categories"
        and "POST" in (getattr(route, "methods", set()) or set())
    ]

    assert len(category_creation_routes) == 1

def test_update_category_name(client: TestClient):
    category_id = create_category(client)

    response = client.put(
        f"/categories/{category_id}",
        json={"name": "Bebidas"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": category_id,
        "name": "Bebidas",
    }

    categories = client.get("/categories").json()
    assert categories == [{"id": category_id, "name": "Bebidas"}]



def test_update_product_moves_category_without_changing_quantity(client: TestClient):
    original_category_id = create_category(client)
    product_id = create_product(client, original_category_id, quantity=7)

    category_response = client.post("/categories", json={"name": "Bebidas"})
    assert category_response.status_code == 201
    new_category_id = category_response.json()["id"]

    response = client.put(
        f"/products/{product_id}",
        json={
            "name": "Vela branca",
            "category_id": new_category_id,
            "minimum_quantity": 5,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": product_id,
        "name": "Vela branca",
        "quantity": 7,
        "minimum_quantity": 5,
        "category_id": new_category_id,
    }


def test_delete_product_without_movements(client: TestClient):
    category_id = create_category(client)
    product_id = create_product(client, category_id, quantity=0)

    response = client.delete(f"/products/{product_id}")

    assert response.status_code == 204
    assert client.get("/products").json() == []


def test_delete_product_with_movements_is_blocked(client: TestClient):
    category_id = create_category(client)
    product_id = create_product(client, category_id, quantity=0)

    movement_response = client.post(
        "/stock-movements",
        json={
            "product_id": product_id,
            "movement_type": "in",
            "quantity": 5,
        },
    )
    assert movement_response.status_code == 201

    response = client.delete(f"/products/{product_id}")

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Não é possível remover um item que possui movimentações."
    )
    assert len(client.get("/products").json()) == 1


def test_list_products_by_category(client: TestClient):
    first_category_id = create_category(client)

    second_category_response = client.post(
        "/categories",
        json={"name": "Velas"},
    )
    assert second_category_response.status_code == 201
    second_category_id = second_category_response.json()["id"]

    first_product_id = create_product(client, first_category_id, quantity=4)

    response = client.get(f"/products?category_id={first_category_id}")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": first_product_id,
            "name": "Teclado mecânico",
            "quantity": 4,
            "minimum_quantity": 3,
            "category_id": first_category_id,
        }
    ]

    empty_response = client.get(f"/products?category_id={second_category_id}")
    assert empty_response.status_code == 200
    assert empty_response.json() == []


def test_category_products_page_lists_items_and_edit_link(client: TestClient):
    category_id = create_category(client)
    product_id = create_product(client, category_id, quantity=4)
    authenticate_warehouse(client)

    response = client.get(f"/warehouse/categories/{category_id}")

    assert response.status_code == 200
    assert "Teclado mecânico" in response.text
    assert f"/warehouse/products/{product_id}/edit" in response.text


def test_reorganize_item_from_category_page(client: TestClient):
    source_category_id = create_category(client)

    destination_response = client.post(
        "/categories",
        json={"name": "Destino"},
    )
    assert destination_response.status_code == 201
    destination_category_id = destination_response.json()["id"]

    product_id = create_product(client, source_category_id, quantity=0)
    authenticate_warehouse(client)

    edit_response = client.post(
        f"/warehouse/products/{product_id}/edit",
        data={
            "name": "Item reorganizado",
            "category_id": destination_category_id,
            "minimum_quantity": 2,
        },
        follow_redirects=False,
    )

    assert edit_response.status_code == 303

    source_page = client.get(f"/warehouse/categories/{source_category_id}")
    assert "Nenhum item nesta categoria" in source_page.text

    destination_page = client.get(
        f"/warehouse/categories/{destination_category_id}"
    )
    assert "Item reorganizado" in destination_page.text
