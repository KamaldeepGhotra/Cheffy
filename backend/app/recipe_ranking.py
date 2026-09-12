from sqlalchemy.orm import Session
from app.matching import find_ingredient_matches
from app.models import Recipe

# Same bar resolve_or_create_ingredient uses to call two names the same ingredient.
MATCH_THRESHOLD = 90.0


def compute_match(recipe: Recipe, on_hand_ingredient_ids: set[int]) -> tuple[float, list[str]]:
    ingredients = recipe.ingredients
    if not ingredients:
        return (0.0, [])

    missing = [ri.ingredient.name for ri in ingredients if ri.ingredient_id not in on_hand_ingredient_ids]
    have_count = len(ingredients) - len(missing)
    percentage = (have_count / len(ingredients)) * 100
    return (percentage, missing)


def match_candidate(
    db: Session,
    ingredient_names: list[str],
    on_hand_ingredient_ids: set[int],
) -> tuple[float, list[str]]:
    """Score a recipe that has not been saved, without writing anything.

    Unlike compute_match, there are no ingredient rows to compare ids against yet, so each
    name is resolved read-only against the canonical table. A name that resolves to nothing,
    or to an ingredient that isn't on hand, counts as missing.
    """
    if not ingredient_names:
        return (0.0, [])

    missing = []
    for name in ingredient_names:
        matches = find_ingredient_matches(db, name, limit=1)
        if matches and matches[0][1] >= MATCH_THRESHOLD and matches[0][0].id in on_hand_ingredient_ids:
            continue
        missing.append(name)

    have_count = len(ingredient_names) - len(missing)
    return ((have_count / len(ingredient_names)) * 100, missing)
