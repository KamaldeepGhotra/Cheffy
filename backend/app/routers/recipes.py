from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.gemini_client import GeminiError, get_recipe_info, suggest_recipes
from app.matching import normalize_ingredient_name, resolve_or_create_ingredient
from app.models import DEFAULT_RECIPE_SERVINGS, Ingredient, InventoryItem, Recipe, RecipeIngredient
from app.recipe_ranking import compute_match
from app.schemas import RankedRecipeOut, RecipeIngredientOut, RecipeSearchRequest, RecipeSuggestRequest
from app.units import normalize_unit

router = APIRouter(prefix="/recipes", tags=["recipes"])

UNAVAILABLE = "Recipe service unavailable, try again"
MAX_SERVINGS = 12


def _clamp_servings(value) -> int:
    try:
        servings = int(value)
    except (TypeError, ValueError):
        return DEFAULT_RECIPE_SERVINGS
    return max(1, min(MAX_SERVINGS, servings))


def _persist_recipe(db: Session, info: dict) -> Recipe:
    recipe = Recipe(
        name=info["name"],
        servings=_clamp_servings(info.get("servings", DEFAULT_RECIPE_SERVINGS)),
        instructions=info["instructions"],
        calories=info.get("calories"),
        protein=info.get("protein"),
        fat=info.get("fat"),
        carbs=info.get("carbs"),
        source="ai_generated",
    )
    db.add(recipe)
    db.flush()
    for raw in info["ingredients"]:
        try:
            ingredient = resolve_or_create_ingredient(db, raw["name"])
        except ValueError as exc:
            raise GeminiError(f"Malformed ingredient name: {raw.get('name')!r}") from exc
        db.add(RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            quantity=raw["quantity"],
            unit=normalize_unit(raw["unit"]),
        ))
    db.commit()
    db.refresh(recipe)
    return recipe


def _on_hand_ids(db: Session, household_id: str | None) -> set[int]:
    if not household_id:
        return set()
    rows = db.query(InventoryItem.ingredient_id).filter_by(household_id=household_id).all()
    return {row[0] for row in rows}


def _on_hand_names(db: Session, household_id: str) -> list[str]:
    rows = (
        db.query(Ingredient.name)
        .join(InventoryItem, InventoryItem.ingredient_id == Ingredient.id)
        .filter(InventoryItem.household_id == household_id)
        .distinct()
        .all()
    )
    return [row[0] for row in rows]


def _to_ranked(recipe: Recipe, on_hand: set[int]) -> RankedRecipeOut:
    percentage, missing = compute_match(recipe, on_hand)
    return RankedRecipeOut(
        id=recipe.id,
        name=recipe.name,
        servings=recipe.servings,
        instructions=recipe.instructions,
        calories=recipe.calories,
        protein=recipe.protein,
        fat=recipe.fat,
        carbs=recipe.carbs,
        ingredients=[
            RecipeIngredientOut(
                ingredient_id=ri.ingredient_id,
                ingredient_name=ri.ingredient.name,
                quantity=ri.quantity,
                unit=ri.unit,
            )
            for ri in recipe.ingredients
        ],
        match_percentage=percentage,
        missing_ingredients=missing,
    )


def _ranked(recipes: list[Recipe], on_hand: set[int]) -> list[RankedRecipeOut]:
    ranked = [_to_ranked(recipe, on_hand) for recipe in recipes]
    ranked.sort(key=lambda r: (-r.match_percentage, -r.id))
    return ranked


@router.post("/search", response_model=RankedRecipeOut, status_code=201)
def search_recipe(payload: RecipeSearchRequest, db: Session = Depends(get_db)):
    try:
        recipe = _persist_recipe(db, get_recipe_info(payload.query))
    except GeminiError:
        db.rollback()
        raise HTTPException(status_code=502, detail=UNAVAILABLE)
    return _to_ranked(recipe, _on_hand_ids(db, payload.household_id))


@router.post("/suggest", response_model=list[RankedRecipeOut], status_code=201)
def suggest(payload: RecipeSuggestRequest, db: Session = Depends(get_db)):
    try:
        infos = suggest_recipes(_on_hand_names(db, payload.household_id), payload.count)
        known = {normalize_ingredient_name(row[0]) for row in db.query(Recipe.name).all()}
        created = []
        for info in infos:
            key = normalize_ingredient_name(info["name"])
            if key in known:
                continue
            known.add(key)
            created.append(_persist_recipe(db, info))
    except GeminiError:
        db.rollback()
        raise HTTPException(status_code=502, detail=UNAVAILABLE)
    return _ranked(created, _on_hand_ids(db, payload.household_id))


@router.get("", response_model=list[RankedRecipeOut])
def list_recipes(household_id: str | None = None, db: Session = Depends(get_db)):
    return _ranked(db.query(Recipe).all(), _on_hand_ids(db, household_id))
