import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_db


def make_client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_add_and_list_inventory_item(db_session):
    client = make_client(db_session)

    create_response = client.post("/inventory", json={
        "household_id": "roommates",
        "ingredient_name": "chicken breast",
        "quantity": 2,
        "unit": "lb",
    })
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["ingredient_name"] == "chicken breast"
    assert body["quantity"] == 2

    list_response = client.get("/inventory", params={"household_id": "roommates"})
    assert list_response.status_code == 200
    items = list_response.json()
    assert len(items) == 1
    assert items[0]["ingredient_name"] == "chicken breast"

    app.dependency_overrides.clear()


def test_delete_inventory_item(db_session):
    client = make_client(db_session)

    create_response = client.post("/inventory", json={
        "household_id": "roommates",
        "ingredient_name": "rice",
        "quantity": 1,
        "unit": "bag",
    })
    item_id = create_response.json()["id"]

    delete_response = client.delete(f"/inventory/{item_id}")
    assert delete_response.status_code == 204

    list_response = client.get("/inventory", params={"household_id": "roommates"})
    assert list_response.json() == []

    app.dependency_overrides.clear()


def add(client, name, quantity, unit, household_id="roommates"):
    return client.post("/inventory", json={
        "household_id": household_id,
        "ingredient_name": name,
        "quantity": quantity,
        "unit": unit,
    })


def test_repeat_add_merges_and_sums_quantity(db_session):
    client = make_client(db_session)

    first = add(client, "chicken breast", 2, "lb")
    second = add(client, "chicken breast", 1.5, "lb")

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["quantity"] == 3.5

    items = client.get("/inventory", params={"household_id": "roommates"}).json()
    assert len(items) == 1
    assert items[0]["quantity"] == 3.5

    app.dependency_overrides.clear()


def test_different_unit_makes_a_second_row(db_session):
    client = make_client(db_session)

    add(client, "chicken breast", 2, "lb")
    response = add(client, "chicken breast", 500, "g")

    assert response.status_code == 201
    items = client.get("/inventory", params={"household_id": "roommates"}).json()
    assert sorted((i["quantity"], i["unit"]) for i in items) == [(2, "lb"), (500, "g")]

    app.dependency_overrides.clear()


@pytest.mark.parametrize(("first_unit", "second_unit"), [("cups", "cup"), ("cup", "cups")])
def test_unit_aliases_merge_into_one_row(db_session, first_unit, second_unit):
    client = make_client(db_session)

    first = add(client, "rice", 1, first_unit)
    second = add(client, "rice", 2, second_unit)

    assert first.status_code == 201
    assert first.json()["unit"] == "cup"
    assert second.status_code == 200
    assert second.json()["quantity"] == 3
    assert len(client.get("/inventory", params={"household_id": "roommates"}).json()) == 1

    app.dependency_overrides.clear()


def test_different_ingredients_with_the_same_unit_stay_separate(db_session):
    client = make_client(db_session)

    add(client, "chicken breast", 2, "lb")
    response = add(client, "ground beef", 1, "lb")

    assert response.status_code == 201
    items = client.get("/inventory", params={"household_id": "roommates"}).json()
    assert sorted((i["ingredient_name"], i["quantity"]) for i in items) == [("chicken breast", 2), ("ground beef", 1)]

    app.dependency_overrides.clear()


def test_unit_is_normalized_on_create(db_session):
    client = make_client(db_session)

    assert add(client, "flour", 1, "Pounds").json()["unit"] == "lb"
    assert add(client, "saffron", 1, "pinch").json()["unit"] == "pinch"
    assert add(client, "eggs", 12, "").json()["unit"] == "each"

    app.dependency_overrides.clear()


def test_same_ingredient_in_another_household_does_not_merge(db_session):
    client = make_client(db_session)

    add(client, "milk", 1, "l", household_id="roommates")
    response = add(client, "milk", 1, "l", household_id="other-flat")

    assert response.status_code == 201
    assert len(client.get("/inventory", params={"household_id": "roommates"}).json()) == 1
    assert len(client.get("/inventory", params={"household_id": "other-flat"}).json()) == 1

    app.dependency_overrides.clear()


def test_name_that_resolves_to_existing_ingredient_merges(db_session):
    client = make_client(db_session)

    add(client, "chicken breast", 2, "lb")
    response = add(client, "  Chicken Breast ", 1, "lbs")

    assert response.status_code == 200
    assert response.json()["quantity"] == 3
    assert response.json()["ingredient_name"] == "chicken breast"

    app.dependency_overrides.clear()
