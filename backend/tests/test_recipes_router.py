from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_db


def make_client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


FAKE_RECIPE_INFO = {
    "name": "Chicken Fried Rice",
    "instructions": "1. Cook rice. 2. Cook chicken. 3. Combine.",
    "ingredients": [
        {"name": "chicken breast", "quantity": 1, "unit": "lb"},
        {"name": "white rice", "quantity": 2, "unit": "cup"},
    ],
    "calories": 450,
    "protein": 35,
    "fat": 12,
    "carbs": 50,
}


@patch("app.routers.recipes.get_recipe_info", return_value=FAKE_RECIPE_INFO)
def test_search_recipe_creates_recipe_with_resolved_ingredients(mock_get_info, db_session):
    client = make_client(db_session)

    response = client.post("/recipes/search", json={"query": "chicken fried rice"})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Chicken Fried Rice"
    assert body["calories"] == 450
    assert len(body["ingredients"]) == 2
    names = {ing["ingredient_name"] for ing in body["ingredients"]}
    assert names == {"chicken breast", "white rice"}

    app.dependency_overrides.clear()
