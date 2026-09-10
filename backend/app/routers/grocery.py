from collections import defaultdict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import RecipeIngredient, InventoryItem
from app.schemas import GroceryListRequest, GroceryListResponse, GroceryLine

router = APIRouter(tags=["grocery"])


@router.post("/grocery-list", response_model=GroceryListResponse)
def generate_grocery_list(payload: GroceryListRequest, db: Session = Depends(get_db)):
    needed_by_key: dict[tuple[int, str], float] = defaultdict(float)
    name_by_ingredient_id: dict[int, str] = {}

    for recipe_id in payload.recipe_ids:
        servings = payload.servings.get(recipe_id, 1)
        recipe_ingredients = db.query(RecipeIngredient).filter_by(recipe_id=recipe_id).all()
        for ri in recipe_ingredients:
            key = (ri.ingredient_id, ri.unit)
            needed_by_key[key] += ri.quantity * servings
            name_by_ingredient_id[ri.ingredient_id] = ri.ingredient.name

    on_hand_by_key: dict[tuple[int, str], float] = defaultdict(float)
    inventory_items = db.query(InventoryItem).filter_by(household_id=payload.household_id).all()
    for item in inventory_items:
        on_hand_by_key[(item.ingredient_id, item.unit)] += item.quantity
        name_by_ingredient_id.setdefault(item.ingredient_id, item.ingredient.name)

    have: list[GroceryLine] = []
    need: list[GroceryLine] = []

    for key, needed_qty in needed_by_key.items():
        ingredient_id, unit = key
        on_hand_qty = on_hand_by_key.get(key, 0.0)
        name = name_by_ingredient_id[ingredient_id]

        if on_hand_qty >= needed_qty:
            have.append(GroceryLine(ingredient_name=name, needed=needed_qty, unit=unit))
        else:
            remaining = needed_qty - on_hand_qty
            need.append(GroceryLine(ingredient_name=name, needed=remaining, unit=unit))

    return GroceryListResponse(have=have, need=need)
