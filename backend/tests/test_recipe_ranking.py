import pytest
from app.models import Ingredient, Recipe, RecipeIngredient
from app.recipe_ranking import compute_match


def test_full_match_returns_100_percent_and_no_missing(db_session):
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
    db_session.commit()
    db_session.refresh(recipe)

    percentage, missing = compute_match(recipe, {chicken.id, rice.id})

    assert percentage == 100.0
    assert missing == []


def test_partial_match_returns_percentage_and_missing_names_in_order(db_session):
    chicken = Ingredient(name="chicken breast")
    rice = Ingredient(name="white rice")
    garlic = Ingredient(name="garlic")
    db_session.add_all([chicken, rice, garlic])
    db_session.flush()

    recipe = Recipe(name="Chicken Fried Rice", instructions="cook it")
    db_session.add(recipe)
    db_session.flush()
    db_session.add_all([
        RecipeIngredient(recipe_id=recipe.id, ingredient_id=chicken.id, quantity=1, unit="lb"),
        RecipeIngredient(recipe_id=recipe.id, ingredient_id=rice.id, quantity=2, unit="cup"),
        RecipeIngredient(recipe_id=recipe.id, ingredient_id=garlic.id, quantity=3, unit="clove"),
    ])
    db_session.commit()
    db_session.refresh(recipe)

    percentage, missing = compute_match(recipe, {rice.id})

    assert percentage == pytest.approx(100 / 3)
    assert missing == ["chicken breast", "garlic"]


def test_recipe_with_no_ingredients_returns_zero_and_no_missing(db_session):
    recipe = Recipe(name="Empty Recipe", instructions="n/a")
    db_session.add(recipe)
    db_session.commit()
    db_session.refresh(recipe)

    percentage, missing = compute_match(recipe, set())

    assert percentage == 0.0
    assert missing == []
