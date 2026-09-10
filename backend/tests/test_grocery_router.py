from fastapi.testclient import TestClient
from app.main import app
from app.db import get_db
from app.models import Ingredient, Recipe, RecipeIngredient, InventoryItem


def make_client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_grocery_list_splits_have_and_need(db_session):
    chicken = Ingredient(name="chicken breast")
    rice = Ingredient(name="white rice")
    db_session.add_all([chicken, rice])
    db_session.flush()

    recipe = Recipe(name="Chicken Fried Rice", instructions="cook it")
    db_session.add(recipe)
    db_session.flush()

    db_session.add_all([
        RecipeIngredient(recipe_id=recipe.id, ingredient_id=chicken.id, quantity=1, unit="lb"),
        RecipeIngredient(recipe_id=recipe.id, ingredient_id=rice.id, quantity=2, unit="cup"),
    ])
    db_session.add(InventoryItem(ingredient_id=rice.id, household_id="roommates", quantity=3, unit="cup"))
    db_session.commit()

    client = make_client(db_session)
    response = client.post("/grocery-list", json={
        "household_id": "roommates",
        "recipe_ids": [recipe.id],
        "servings": {str(recipe.id): 1},
    })

    assert response.status_code == 200
    body = response.json()

    have_names = {line["ingredient_name"] for line in body["have"]}
    need_names = {line["ingredient_name"] for line in body["need"]}

    assert "white rice" in have_names
    assert "chicken breast" in need_names

    app.dependency_overrides.clear()


def test_grocery_list_need_quantity_reflects_deficit(db_session):
    chicken = Ingredient(name="chicken breast")
    db_session.add(chicken)
    db_session.flush()

    recipe = Recipe(name="Grilled Chicken", instructions="cook it")
    db_session.add(recipe)
    db_session.flush()

    db_session.add(RecipeIngredient(recipe_id=recipe.id, ingredient_id=chicken.id, quantity=3, unit="lb"))
    db_session.add(InventoryItem(ingredient_id=chicken.id, household_id="roommates", quantity=1, unit="lb"))
    db_session.commit()

    client = make_client(db_session)
    response = client.post("/grocery-list", json={
        "household_id": "roommates",
        "recipe_ids": [recipe.id],
        "servings": {str(recipe.id): 1},
    })

    assert response.status_code == 200
    body = response.json()

    need_line = next(line for line in body["need"] if line["ingredient_name"] == "chicken breast")
    assert need_line["needed"] == 2

    app.dependency_overrides.clear()


def test_grocery_list_servings_multiplier_scales_needed_quantity(db_session):
    rice = Ingredient(name="white rice")
    db_session.add(rice)
    db_session.flush()

    recipe = Recipe(name="Rice Bowl", instructions="cook it")
    db_session.add(recipe)
    db_session.flush()

    db_session.add(RecipeIngredient(recipe_id=recipe.id, ingredient_id=rice.id, quantity=2, unit="cup"))
    db_session.add(InventoryItem(ingredient_id=rice.id, household_id="roommates", quantity=1, unit="cup"))
    db_session.commit()

    client = make_client(db_session)
    response = client.post("/grocery-list", json={
        "household_id": "roommates",
        "recipe_ids": [recipe.id],
        "servings": {str(recipe.id): 2},
    })

    assert response.status_code == 200
    body = response.json()

    need_line = next(line for line in body["need"] if line["ingredient_name"] == "white rice")
    assert need_line["needed"] == 3

    app.dependency_overrides.clear()


def test_grocery_list_aggregates_same_ingredient_across_recipes(db_session):
    chicken = Ingredient(name="chicken breast")
    db_session.add(chicken)
    db_session.flush()

    recipe_one = Recipe(name="Chicken Stir Fry", instructions="cook it")
    recipe_two = Recipe(name="Chicken Soup", instructions="cook it")
    db_session.add_all([recipe_one, recipe_two])
    db_session.flush()

    db_session.add_all([
        RecipeIngredient(recipe_id=recipe_one.id, ingredient_id=chicken.id, quantity=1, unit="lb"),
        RecipeIngredient(recipe_id=recipe_two.id, ingredient_id=chicken.id, quantity=2, unit="lb"),
    ])
    db_session.add(InventoryItem(ingredient_id=chicken.id, household_id="roommates", quantity=1, unit="lb"))
    db_session.commit()

    client = make_client(db_session)
    response = client.post("/grocery-list", json={
        "household_id": "roommates",
        "recipe_ids": [recipe_one.id, recipe_two.id],
        "servings": {str(recipe_one.id): 1, str(recipe_two.id): 1},
    })

    assert response.status_code == 200
    body = response.json()

    need_line = next(line for line in body["need"] if line["ingredient_name"] == "chicken breast")
    assert need_line["needed"] == 2

    app.dependency_overrides.clear()
