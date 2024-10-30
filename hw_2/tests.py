from http import HTTPStatus
from typing import Any
from uuid import uuid4

import pytest
from faker import Faker
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)
faker = Faker()


# Фикстуры для подготовки данных

@pytest.fixture()
def empty_cart_id() -> int:
    return client.post("/cart").json()["id"]

@pytest.fixture(scope="session")
def item_ids() -> list[int]:
    items = [
        {
            "name": f"Тестовый товар {i}",
            "price": faker.pyfloat(positive=True, min_value=10.0, max_value=500.0),
        }
        for i in range(10)
    ]
    return [client.post("/item", json=item).json()["id"] for item in items]

@pytest.fixture(scope="session", autouse=True)
def filled_cart_ids(item_ids: list[int]) -> list[int]:
    carts = []
    for i in range(20):
        cart_id: int = client.post("/cart").json()["id"]
        for item_id in faker.random_elements(item_ids, unique=False, length=i):
            client.post(f"/cart/{cart_id}/add/{item_id}")
        carts.append(cart_id)
    return carts

@pytest.fixture()
def filled_cart_id(empty_cart_id: int, item_ids: list[int]) -> int:
    for item_id in faker.random_elements(item_ids, unique=False, length=3):
        client.post(f"/cart/{empty_cart_id}/add/{item_id}")
    return empty_cart_id

@pytest.fixture()
def single_item() -> dict[str, Any]:
    return client.post(
        "/item",
        json={
            "name": f"Тестовый товар {uuid4().hex}",
            "price": faker.pyfloat(min_value=10.0, max_value=100.0),
        },
    ).json()

@pytest.fixture()
def deleted_item(single_item: dict[str, Any]) -> dict[str, Any]:
    item_id = single_item["id"]
    client.delete(f"/item/{item_id}")
    single_item["deleted"] = True
    return single_item


# Тесты для Cart

def test_create_cart() -> None:
    response = client.post("/cart")
    assert response.status_code == HTTPStatus.CREATED
    assert "location" in response.headers
    assert "id" in response.json()

@pytest.mark.parametrize(
    ("cart_fixture", "should_be_filled"),
    [
        ("empty_cart_id", False),
        ("filled_cart_id", True),
    ],
)
def test_get_cart(request, cart_fixture: int, should_be_filled: bool) -> None:
    cart_id = request.getfixturevalue(cart_fixture)
    response = client.get(f"/cart/{cart_id}")
    assert response.status_code == HTTPStatus.OK

    response_json = response.json()
    items_count = len(response_json["items"])
    assert (items_count > 0) if should_be_filled else (items_count == 0)

    if should_be_filled:
        total_price = sum(
            client.get(f"/item/{item['id']}").json()["price"] * item["quantity"]
            for item in response_json["items"]
        )
        assert response_json["price"] == pytest.approx(total_price, 1e-8)
    else:
        assert response_json["price"] == 0.0

@pytest.mark.parametrize(
    ("params", "expected_status"),
    [
        ({}, HTTPStatus.OK),
        ({"offset": 1, "limit": 2}, HTTPStatus.OK),
        ({"min_price": 1000.0}, HTTPStatus.OK),
        ({"max_price": 20.0}, HTTPStatus.OK),
        ({"min_quantity": 1}, HTTPStatus.OK),
        ({"max_quantity": 0}, HTTPStatus.OK),
        ({"offset": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": 0}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"min_price": -1.0}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"max_price": -1.0}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"min_quantity": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"max_quantity": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
    ],
)
def test_get_cart_list(params: dict[str, Any], expected_status: int):
    response = client.get("/cart", params=params)
    assert response.status_code == expected_status

    if expected_status == HTTPStatus.OK:
        data = response.json()
        assert isinstance(data, list)
        if "min_price" in params:
            assert all(item["price"] >= params["min_price"] for item in data)
        if "max_price" in params:
            assert all(item["price"] <= params["max_price"] for item in data)
        if "min_quantity" in params:
            assert sum(item["quantity"] for cart in data for item in cart["items"]) >= params["min_quantity"]
        if "max_quantity" in params:
            assert sum(item["quantity"] for cart in data for item in cart["items"]) <= params["max_quantity"]


# Тесты для Item

def test_create_item() -> None:
    item = {"name": "test item", "price": 9.99}
    response = client.post("/item", json=item)
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()["name"] == item["name"]
    assert response.json()["price"] == item["price"]

def test_get_item(single_item: dict[str, Any]) -> None:
    item_id = single_item["id"]
    response = client.get(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == single_item

@pytest.mark.parametrize(
    ("params", "expected_status"),
    [
        ({"offset": 2, "limit": 5}, HTTPStatus.OK),
        ({"min_price": 5.0}, HTTPStatus.OK),
        ({"max_price": 5.0}, HTTPStatus.OK),
        ({"show_deleted": True}, HTTPStatus.OK),
        ({"offset": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": 0}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"min_price": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"max_price": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
    ],
)
def test_get_item_list(params: dict[str, Any], expected_status: int) -> None:
    response = client.get("/item", params=params)
    assert response.status_code == expected_status

    if expected_status == HTTPStatus.OK:
        data = response.json()
        assert isinstance(data, list)
        if "min_price" in params:
            assert all(item["price"] >= params["min_price"] for item in data)
        if "max_price" in params:
            assert all(item["price"] <= params["max_price"] for item in data)
        if "show_deleted" in params and not params["show_deleted"]:
            assert all(item["deleted"] is False for item in data)

@pytest.mark.parametrize(
    ("body", "expected_status"),
    [
        ({}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"price": 9.99}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"name": "new name", "price": 9.99}, HTTPStatus.OK),
    ],
)
def test_update_item(single_item: dict[str, Any], body: dict[str, Any], expected_status: int) -> None:
    item_id = single_item["id"]
    response = client.put(f"/item/{item_id}", json=body)
    assert response.status_code == expected_status
    if expected_status == HTTPStatus.OK:
        updated_item = single_item.copy()
        updated_item.update(body)
        assert response.json() == updated_item


@pytest.mark.parametrize(
    ("item_fixture", "body", "expected_status"),
    [
        ("deleted_item", {}, HTTPStatus.NOT_MODIFIED),
        ("deleted_item", {"price": 9.99}, HTTPStatus.NOT_MODIFIED),
        ("deleted_item", {"name": "new name", "price": 9.99}, HTTPStatus.NOT_MODIFIED),
        ("single_item", {}, HTTPStatus.OK),
        ("single_item", {"price": 9.99}, HTTPStatus.OK),
        ("single_item", {"name": "new name", "price": 9.99}, HTTPStatus.OK),
        (
            "single_item",
            {"name": "new name", "price": 9.99, "odd": "value"},
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
        (
            "single_item",
            {"name": "new name", "price": 9.99, "deleted": True},
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
    ],
)
def test_patch_item(request, item_fixture: str, body: dict[str, Any], expected_status: int) -> None:
    item_data: dict[str, Any] = request.getfixturevalue(item_fixture)
    item_id = item_data["id"]
    response = client.patch(f"/item/{item_id}", json=body)
    assert response.status_code == expected_status
    if expected_status == HTTPStatus.OK:
        patched_item = response.json()
        response = client.get(f"/item/{item_id}")
        assert response.json() == patched_item


def test_delete_item(single_item: dict[str, Any]) -> None:
    item_id = single_item["id"]
    response = client.delete(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.OK
    response = client.get(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND
    response = client.delete(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.OK
