import pytest
from app.models import Ingredient, InventoryItem, Recipe, RecipeIngredient
from app.recipe_ranking import compute_match, match_candidate


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


def test_match_candidate_counts_on_hand_names_as_had(db_session):
    chicken = Ingredient(name="chicken breast")
    rice = Ingredient(name="white rice")
    db_session.add_all([chicken, rice])
    db_session.flush()
    db_session.add(InventoryItem(ingredient_id=chicken.id, household_id="roommates", quantity=1, unit="lb"))
    db_session.commit()

    percentage, missing = match_candidate(db_session, ["chicken breast", "white rice"], {chicken.id})

    assert percentage == 50.0
    assert missing == ["white rice"]


def test_match_candidate_treats_unknown_names_as_missing_and_writes_nothing(db_session):
    before = db_session.query(Ingredient).count()

    percentage, missing = match_candidate(db_session, ["dragonfruit", "yuzu"], set())

    assert percentage == 0.0
    assert missing == ["dragonfruit", "yuzu"]
    assert db_session.query(Ingredient).count() == before


def test_match_candidate_with_no_ingredients_returns_zero(db_session):
    assert match_candidate(db_session, [], {1, 2}) == (0.0, [])
