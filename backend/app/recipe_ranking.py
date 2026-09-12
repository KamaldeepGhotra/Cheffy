from app.models import Recipe


def compute_match(recipe: Recipe, on_hand_ingredient_ids: set[int]) -> tuple[float, list[str]]:
    ingredients = recipe.ingredients
    if not ingredients:
        return (0.0, [])

    missing = [ri.ingredient.name for ri in ingredients if ri.ingredient_id not in on_hand_ingredient_ids]
    have_count = len(ingredients) - len(missing)
    percentage = (have_count / len(ingredients)) * 100
    return (percentage, missing)
