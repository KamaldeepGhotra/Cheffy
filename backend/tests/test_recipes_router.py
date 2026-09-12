from unittest.mock import patch
from fastapi.testclient import TestClient
from app.gemini_client import GeminiError
from app.main import app
from app.db import get_db
from app.models import Ingredient, InventoryItem, Recipe, RecipeIngredient


def make_client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


FAKE_RECIPE_INFO = {
    "name": "Chicken Fried Rice",
    "servings": 4,
    "instructions": "1. Cook rice. 2. Cook chicken. 3. Combine.",
    "ingredients": [
        {"name": "chicken breast", "prep": "diced", "quantity": 1, "unit": "lb"},
        {"name": "white rice", "prep": "", "quantity": 2, "unit": "cups"},
    ],
    "calories": 450,
    "protein": 35,
    "fat": 12,
    "carbs": 50,
}


def seed_ingredient(db_session, name):
    ingredient = Ingredient(name=name)
    db_session.add(ingredient)
    db_session.flush()
    return ingredient


def seed_recipe(db_session, name, ingredients):
    recipe = Recipe(name=name, instructions="cook it")
    db_session.add(recipe)
    db_session.flush()
    for ingredient in ingredients:
        db_session.add(RecipeIngredient(recipe_id=recipe.id, ingredient_id=ingredient.id, quantity=1, unit="each"))
    db_session.commit()
    return recipe


def stock(db_session, ingredient, household_id="roommates"):
    db_session.add(InventoryItem(ingredient_id=ingredient.id, household_id=household_id, quantity=1, unit="each"))
    db_session.commit()


@patch("app.routers.recipes.get_recipe_info", return_value=FAKE_RECIPE_INFO)
def test_search_saves_recipe_with_servings_and_normalized_units(mock_get_info, db_session):
    client = make_client(db_session)

    response = client.post("/recipes/search", json={"query": "chicken fried rice"})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Chicken Fried Rice"
    assert body["servings"] == 4
    assert body["calories"] == 450
    assert {ing["ingredient_name"] for ing in body["ingredients"]} == {"chicken breast", "white rice"}
    assert {ing["unit"] for ing in body["ingredients"]} == {"lb", "cup"}
    assert body["match_percentage"] == 0
    assert body["missing_ingredients"] == ["chicken breast", "white rice"]

    app.dependency_overrides.clear()


@patch("app.routers.recipes.get_recipe_info")
def test_search_defaults_and_clamps_servings(mock_get_info, db_session):
    client = make_client(db_session)

    mock_get_info.return_value = {**FAKE_RECIPE_INFO, "servings": 40}
    assert client.post("/recipes/search", json={"query": "a"}).json()["servings"] == 12

    mock_get_info.return_value = {k: v for k, v in FAKE_RECIPE_INFO.items() if k != "servings"}
    assert client.post("/recipes/search", json={"query": "b"}).json()["servings"] == 4

    app.dependency_overrides.clear()


@patch("app.routers.recipes.get_recipe_info", return_value=FAKE_RECIPE_INFO)
def test_search_ranks_against_the_household_inventory(mock_get_info, db_session):
    stock(db_session, seed_ingredient(db_session, "chicken breast"))
    client = make_client(db_session)

    body = client.post("/recipes/search", json={"query": "chicken fried rice", "household_id": "roommates"}).json()

    assert body["match_percentage"] == 50
    assert body["missing_ingredients"] == ["white rice"]

    app.dependency_overrides.clear()


def test_list_is_sorted_by_match_then_newest_with_missing_names(db_session):
    chicken = seed_ingredient(db_session, "chicken breast")
    rice = seed_ingredient(db_session, "white rice")
    stock(db_session, chicken)
    seed_recipe(db_session, "Rice only", [rice])
    seed_recipe(db_session, "Chicken and rice", [chicken, rice])
    seed_recipe(db_session, "Chicken only", [chicken])
    client = make_client(db_session)

    body = client.get("/recipes", params={"household_id": "roommates"}).json()

    assert [r["name"] for r in body] == ["Chicken only", "Chicken and rice", "Rice only"]
    assert [r["match_percentage"] for r in body] == [100, 50, 0]
    assert body[1]["missing_ingredients"] == ["white rice"]
    assert body[0]["missing_ingredients"] == []

    app.dependency_overrides.clear()


def test_list_without_household_is_newest_first_with_nothing_on_hand(db_session):
    rice = seed_ingredient(db_session, "white rice")
    seed_recipe(db_session, "First", [])
    seed_recipe(db_session, "Second", [rice])
    client = make_client(db_session)

    body = client.get("/recipes").json()

    assert [r["name"] for r in body] == ["Second", "First"]
    assert body[0]["match_percentage"] == 0
    assert body[0]["missing_ingredients"] == ["white rice"]
    assert body[0]["ingredients"][0]["ingredient_name"] == "white rice"

    app.dependency_overrides.clear()


@patch("app.routers.recipes.suggest_recipes")
def test_suggest_uses_on_hand_names_and_skips_recipes_already_saved(mock_suggest, db_session):
    chicken = seed_ingredient(db_session, "chicken breast")
    stock(db_session, chicken)
    seed_recipe(db_session, "Chicken Fried Rice", [chicken])
    mock_suggest.return_value = [
        FAKE_RECIPE_INFO,
        {**FAKE_RECIPE_INFO, "name": "Chicken Salad", "ingredients": [{"name": "chicken breast", "quantity": 1, "unit": "lb"}]},
    ]
    client = make_client(db_session)

    response = client.post("/recipes/suggest", json={"household_id": "roommates", "count": 2})

    assert response.status_code == 201
    mock_suggest.assert_called_once_with(["chicken breast"], 2)
    body = response.json()
    assert [r["name"] for r in body] == ["Chicken Salad"]
    assert body[0]["match_percentage"] == 100
    assert db_session.query(Recipe).count() == 2

    app.dependency_overrides.clear()


@patch("app.routers.recipes.suggest_recipes", side_effect=GeminiError("boom"))
@patch("app.routers.recipes.get_recipe_info", side_effect=GeminiError("boom"))
def test_gemini_failures_are_502(mock_get_info, mock_suggest, db_session):
    client = make_client(db_session)

    search = client.post("/recipes/search", json={"query": "anything"})
    suggest = client.post("/recipes/suggest", json={"household_id": "roommates"})

    assert search.status_code == 502
    assert search.json()["detail"] == "Recipe service unavailable, try again"
    assert suggest.status_code == 502

    app.dependency_overrides.clear()


@patch("app.routers.recipes.get_recipe_info")
def test_blank_ingredient_name_is_502_and_stores_nothing(mock_get_info, db_session):
    mock_get_info.return_value = {
        **FAKE_RECIPE_INFO,
        "ingredients": [{"name": "chicken breast", "quantity": 1, "unit": "lb"}, {"name": "(", "quantity": 1, "unit": "each"}],
    }
    client = make_client(db_session)

    response = client.post("/recipes/search", json={"query": "broken"})

    assert response.status_code == 502
    assert db_session.query(Recipe).count() == 0

    app.dependency_overrides.clear()
