import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


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
            "sku": "TEC-MEC-001",
            "unit_price": 299.90,
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
            "sku": "TEC-MEC-001",
            "unit_price": "299.90",
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
