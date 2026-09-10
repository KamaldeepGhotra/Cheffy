from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.gemini_client import get_recipe_info
from app.matching import resolve_or_create_ingredient
from app.models import Recipe, RecipeIngredient
from app.schemas import RecipeSearchRequest, RecipeOut, RecipeIngredientOut

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.post("/search", response_model=RecipeOut, status_code=201)
def search_recipe(payload: RecipeSearchRequest, db: Session = Depends(get_db)):
    info = get_recipe_info(payload.query)

    recipe = Recipe(
        name=info["name"],
        instructions=info["instructions"],
        calories=info.get("calories"),
        protein=info.get("protein"),
        fat=info.get("fat"),
        carbs=info.get("carbs"),
        source="ai_generated",
    )
    db.add(recipe)
    db.flush()

    ingredient_outs = []
    for raw_ingredient in info["ingredients"]:
        ingredient = resolve_or_create_ingredient(db, raw_ingredient["name"])
        recipe_ingredient = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            quantity=raw_ingredient["quantity"],
            unit=raw_ingredient["unit"],
        )
        db.add(recipe_ingredient)
        ingredient_outs.append(RecipeIngredientOut(
            ingredient_id=ingredient.id,
            ingredient_name=ingredient.name,
            quantity=raw_ingredient["quantity"],
            unit=raw_ingredient["unit"],
        ))

    db.commit()

    return RecipeOut(
        id=recipe.id,
        name=recipe.name,
        instructions=recipe.instructions,
        calories=recipe.calories,
        protein=recipe.protein,
        fat=recipe.fat,
        carbs=recipe.carbs,
        ingredients=ingredient_outs,
    )
