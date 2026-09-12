from datetime import date
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_db
from app.models import Ingredient, MealPlanEntry, Recipe, RecipeIngredient, InventoryItem


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

    recipe = Recipe(name="Grilled Chicken", servings=4, instructions="cook it")
    db_session.add(recipe)
    db_session.flush()

    db_session.add(RecipeIngredient(recipe_id=recipe.id, ingredient_id=chicken.id, quantity=3, unit="lb"))
    db_session.add(InventoryItem(ingredient_id=chicken.id, household_id="roommates", quantity=1, unit="lb"))
    db_session.commit()

    client = make_client(db_session)
    response = client.post("/grocery-list", json={
        "household_id": "roommates",
        "recipe_ids": [recipe.id],
        "servings": {str(recipe.id): 4},
    })

    assert response.status_code == 200
    body = response.json()

    # 3 lb feeds the whole 4-serving recipe, all 4 wanted, 1 lb on hand.
    need_line = next(line for line in body["need"] if line["ingredient_name"] == "chicken breast")
    assert need_line["needed"] == 2

    app.dependency_overrides.clear()


def test_grocery_list_servings_multiplier_scales_needed_quantity(db_session):
    rice = Ingredient(name="white rice")
    db_session.add(rice)
    db_session.flush()

    recipe = Recipe(name="Rice Bowl", servings=4, instructions="cook it")
    db_session.add(recipe)
    db_session.flush()

    db_session.add(RecipeIngredient(recipe_id=recipe.id, ingredient_id=rice.id, quantity=2, unit="cup"))
    db_session.add(InventoryItem(ingredient_id=rice.id, household_id="roommates", quantity=1, unit="cup"))
    db_session.commit()

    client = make_client(db_session)
    response = client.post("/grocery-list", json={
        "household_id": "roommates",
        "recipe_ids": [recipe.id],
        "servings": {str(recipe.id): 8},
    })

    assert response.status_code == 200
    body = response.json()

    # 2 cups feeds 4, so 8 portions needs 4 cups; 1 cup on hand leaves 3.
    need_line = next(line for line in body["need"] if line["ingredient_name"] == "white rice")
    assert need_line["needed"] == 3

    app.dependency_overrides.clear()


def test_grocery_list_aggregates_same_ingredient_across_recipes(db_session):
    chicken = Ingredient(name="chicken breast")
    db_session.add(chicken)
    db_session.flush()

    recipe_one = Recipe(name="Chicken Stir Fry", servings=4, instructions="cook it")
    recipe_two = Recipe(name="Chicken Soup", servings=4, instructions="cook it")
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
        "servings": {str(recipe_one.id): 4, str(recipe_two.id): 4},
    })

    assert response.status_code == 200
    body = response.json()

    need_line = next(line for line in body["need"] if line["ingredient_name"] == "chicken breast")
    assert need_line["needed"] == 2

    app.dependency_overrides.clear()


def test_grocery_list_nets_out_singular_and_plural_units(db_session):
    rice = Ingredient(name="white rice")
    db_session.add(rice)
    db_session.flush()

    one = Recipe(name="Rice Bowl", servings=4, instructions="cook it")
    two = Recipe(name="Fried Rice", servings=4, instructions="cook it")
    db_session.add_all([one, two])
    db_session.flush()
    db_session.add_all([
        RecipeIngredient(recipe_id=one.id, ingredient_id=rice.id, quantity=2, unit="cup"),
        RecipeIngredient(recipe_id=two.id, ingredient_id=rice.id, quantity=1, unit="cups"),
    ])
    db_session.commit()

    client = make_client(db_session)
    body = client.post("/grocery-list", json={
        "household_id": "roommates",
        "recipe_ids": [one.id, two.id],
        "servings": {str(one.id): 4, str(two.id): 4},
    }).json()

    rice_lines = [line for line in body["need"] if line["ingredient_name"] == "white rice"]
    assert len(rice_lines) == 1
    assert rice_lines[0]["needed"] == 3
    assert rice_lines[0]["unit"] == "cup"
    assert sorted(rice_lines[0]["recipes"]) == ["Fried Rice", "Rice Bowl"]

    app.dependency_overrides.clear()


def test_week_grocery_list_includes_planned_meals_that_have_no_day(db_session):
    chicken = Ingredient(name="chicken breast")
    db_session.add(chicken)
    db_session.flush()
    recipe = Recipe(name="Grilled Chicken", servings=4, instructions="cook it")
    db_session.add(recipe)
    db_session.flush()
    db_session.add(RecipeIngredient(recipe_id=recipe.id, ingredient_id=chicken.id, quantity=2, unit="lb"))
    # day is None: picked for the week but not scheduled onto a day yet.
    db_session.add(MealPlanEntry(
        household_id="roommates", week_start=date(2026, 9, 7), day=None,
        recipe_id=recipe.id, servings=4, assigned_to=None,
    ))
    db_session.commit()

    client = make_client(db_session)
    body = client.get("/grocery-list", params={"household_id": "roommates", "week_start": "2026-09-07"}).json()

    need_line = next(line for line in body["need"] if line["ingredient_name"] == "chicken breast")
    assert need_line["needed"] == 2
    assert need_line["recipes"] == ["Grilled Chicken"]
    assert need_line["ingredient_id"] == chicken.id

    app.dependency_overrides.clear()


def test_week_grocery_list_sums_servings_across_entries(db_session):
    chicken = Ingredient(name="chicken breast")
    db_session.add(chicken)
    db_session.flush()
    recipe = Recipe(name="Grilled Chicken", servings=4, instructions="cook it")
    db_session.add(recipe)
    db_session.flush()
    db_session.add(RecipeIngredient(recipe_id=recipe.id, ingredient_id=chicken.id, quantity=4, unit="lb"))
    # Same recipe twice in one week: 2 portions on Monday, 2 planned with no day = 4 portions total.
    db_session.add_all([
        MealPlanEntry(household_id="roommates", week_start=date(2026, 9, 7), day=0,
                      recipe_id=recipe.id, servings=2, assigned_to="Kam"),
        MealPlanEntry(household_id="roommates", week_start=date(2026, 9, 7), day=None,
                      recipe_id=recipe.id, servings=2, assigned_to=None),
    ])
    db_session.commit()

    client = make_client(db_session)
    body = client.get("/grocery-list", params={"household_id": "roommates", "week_start": "2026-09-07"}).json()

    need_line = next(line for line in body["need"] if line["ingredient_name"] == "chicken breast")
    assert need_line["needed"] == 4

    app.dependency_overrides.clear()


def test_week_grocery_list_ignores_other_weeks(db_session):
    chicken = Ingredient(name="chicken breast")
    db_session.add(chicken)
    db_session.flush()
    recipe = Recipe(name="Grilled Chicken", servings=4, instructions="cook it")
    db_session.add(recipe)
    db_session.flush()
    db_session.add(RecipeIngredient(recipe_id=recipe.id, ingredient_id=chicken.id, quantity=4, unit="lb"))
    db_session.add(MealPlanEntry(household_id="roommates", week_start=date(2026, 9, 14), day=0,
                                 recipe_id=recipe.id, servings=4, assigned_to="Kam"))
    db_session.commit()

    client = make_client(db_session)
    body = client.get("/grocery-list", params={"household_id": "roommates", "week_start": "2026-09-07"}).json()

    assert body["need"] == []
    assert body["have"] == []

    app.dependency_overrides.clear()
