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
