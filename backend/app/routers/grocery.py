from collections import defaultdict
from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import InventoryItem, MealPlanEntry, Recipe, RecipeIngredient
from app.schemas import GroceryListRequest, GroceryListResponse, GroceryLine
from app.units import normalize_unit

router = APIRouter(tags=["grocery"])


def _build_list(db: Session, household_id: str, servings_by_recipe: dict[int, int]) -> GroceryListResponse:
    # Keyed on the normalized unit so "cup" and "cups" from different recipes net out
    # instead of becoming two lines that each look short.
    needed_by_key: dict[tuple[int, str], float] = defaultdict(float)
    recipes_by_key: dict[tuple[int, str], list[str]] = defaultdict(list)
    name_by_ingredient_id: dict[int, str] = {}

    for recipe_id, servings in servings_by_recipe.items():
        recipe = db.query(Recipe).filter_by(id=recipe_id).first()
        if recipe is None:
            continue
        # Recipe quantities cover the whole recipe, so scale by the portions actually wanted.
        scale = servings / recipe.servings
        for ri in db.query(RecipeIngredient).filter_by(recipe_id=recipe_id).all():
            key = (ri.ingredient_id, normalize_unit(ri.unit))
            needed_by_key[key] += ri.quantity * scale
            name_by_ingredient_id[ri.ingredient_id] = ri.ingredient.name
            if recipe.name not in recipes_by_key[key]:
                recipes_by_key[key].append(recipe.name)

    on_hand_by_key: dict[tuple[int, str], float] = defaultdict(float)
    for item in db.query(InventoryItem).filter_by(household_id=household_id).all():
        on_hand_by_key[(item.ingredient_id, normalize_unit(item.unit))] += item.quantity
        name_by_ingredient_id.setdefault(item.ingredient_id, item.ingredient.name)

    have: list[GroceryLine] = []
    need: list[GroceryLine] = []

    for key, needed_qty in needed_by_key.items():
        ingredient_id, unit = key
        on_hand_qty = on_hand_by_key.get(key, 0.0)
        line = GroceryLine(
            ingredient_id=ingredient_id,
            ingredient_name=name_by_ingredient_id[ingredient_id],
            needed=needed_qty if on_hand_qty >= needed_qty else needed_qty - on_hand_qty,
            unit=unit,
            recipes=recipes_by_key[key],
        )
        (have if on_hand_qty >= needed_qty else need).append(line)

    return GroceryListResponse(have=have, need=need)


@router.post("/grocery-list", response_model=GroceryListResponse)
def generate_grocery_list(payload: GroceryListRequest, db: Session = Depends(get_db)):
    servings = {recipe_id: payload.servings.get(recipe_id, 1) for recipe_id in payload.recipe_ids}
    return _build_list(db, payload.household_id, servings)


# Everything the household is cooking this week, whether or not it has a day yet.
@router.get("/grocery-list", response_model=GroceryListResponse)
def week_grocery_list(household_id: str, week_start: date, db: Session = Depends(get_db)):
    entries = db.query(MealPlanEntry).filter_by(household_id=household_id, week_start=week_start).all()

    servings: dict[int, int] = defaultdict(int)
    for entry in entries:
        servings[entry.recipe_id] += entry.servings

    return _build_list(db, household_id, dict(servings))
